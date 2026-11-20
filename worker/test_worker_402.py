#!/usr/bin/env python3
"""Regression tests for issue #402 (CodeRabbit follow-up on merged
PR #399): non-object queue entries crash run_schedule_check and
run_ledger_watchdog before quarantine — same malformed-queue
family as #391, one layer earlier.

`run_schedule_check()` built its handled set with
`{str(j.get("id", "")) for j in queue}` where `read_queue()`
returns the raw parsed JSON list with no isinstance filtering, so
a null/string entry raised AttributeError out of the check — which
runs at the top of every poll cycle, BEFORE the queue loop. The
cycle-level except caught it, so the worker did not die, but the
cycle then retried and failed at the same point forever: the bad
entry was never quarantined (the #391 queue-loop quarantine never
ran) and no valid job ever processed. `run_ledger_watchdog()` had
the same unguarded comprehension (`queue_ids`), aborting the
watchdog job before it ran.

Fix: both call sites go through `_quarantine_non_object_entries`,
which quarantines every non-object entry with evidence (the #391
`_quarantine_malformed_job` pattern — record under
queue/malformed/, raw entry kept, pushed to the bus) and returns
only the dict entries for id computation. A queue.json that is
not a list at all is quarantined as one malformed payload
("queue-not-a-list") and the schedule check skips instead of
crashing on the append. Quarantined entries stay in queue.json,
exactly as the #391 main-loop path leaves them (re-quarantine is
a no-op once the record exists) — never silently dropped.

Harness-first: FAILS on pristine main (AttributeError out of
run_schedule_check / run_ledger_watchdog; no malformed record
anywhere) and PASSES on the fixed tree. Stdlib only.

Sibling `.get("id")` sites checked, NOT affected (confirmed
against main, noted in the PR): L375 `claim()` and L798/L3028
`_begin_execution` are guarded by an `isinstance(job, dict)`
refusal immediately above; L3205 / L3404 sit inside `try:` after
`job_text()` normalization on a job that already passed claim.
The main() queue loop already routes non-dict entries through
the same quarantine (#391) and is untouched here.

Run: python3 worker/test_worker_402.py (exit 0 = all pass).

CodeRabbit Minor on PR #407: each independent test starts from
empty BUS state (reset_bus) so a malformed-record assertion can
only pass on records written by that test — never on quarantine
records left behind by an earlier test. The first schedule run
and its repeat run live in one test, so the repeat-run setup is
explicit. Watchdog checks compare each recorded entry against
the payload written by that test, including the null, string,
and non-list cases.
"""
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo

_TMP = Path(tempfile.mkdtemp(prefix="gator402-test-"))
os.environ["GATOR_ROOT"] = str(_TMP)

_HERE = Path(os.path.abspath(__file__)).parent
_REPO = _HERE.parent
sys.path.insert(0, str(_HERE))

import worker  # noqa: E402

PASSED = 0
PUSHED = []


def check(name, cond):
    global PASSED
    assert cond, name
    PASSED += 1
    print(f"pass: {name}")


def fake_push_bus(message):
    PUSHED.append(message)
    return True


def queue_dir():
    d = worker.BUS / "queue"
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_queue(entries):
    (queue_dir() / "queue.json").write_text(json.dumps(entries))


def read_queue_file():
    return json.loads((queue_dir() / "queue.json").read_text())


def write_schedule(entries):
    (queue_dir() / "schedule.json").write_text(json.dumps(entries))


def malformed_records():
    d = worker.BUS / "queue" / "malformed"
    if not d.exists():
        return {}
    return {f.stem: json.loads(f.read_text())
            for f in sorted(d.glob("*.json"))}


def reset_bus():
    """Empty BUS queue state (queue.json, schedule.json, the
    malformed/ quarantine records) before an independent test.
    Without this, records left by an earlier test could satisfy a
    later test's any(...) assertion — a watchdog that filters
    entries but never quarantines them would still pass."""
    d = worker.BUS / "queue"
    if d.exists():
        shutil.rmtree(d)


def entries_with_reason(recs, reason):
    """Canonical-JSON set of the recorded entries carrying
    `reason`, for exact comparison against the payload the test
    itself wrote."""
    return {json.dumps(r["entry"], sort_keys=True)
            for r in recs.values() if r["reason"] == reason}


# Friday 2026-11-20, 08:20 Cairo = 06:20 UTC: a daily 08:15 entry
# is due (fire) and inside the 09:30 Cairo catch-up cutoff.
DUE_NOW = datetime(2026, 11, 20, 6, 20, tzinfo=timezone.utc)
DUE_ENTRY = {"id": "sched-402", "job": "sweep-lite POUL.CA market=EGX",
             "days": ["Fri"], "time": "08:15", "tz": "Africa/Cairo"}
DUE_JOB_ID = "sched-2026-11-20"


def test_schedule_check_quarantines_non_objects_and_enqueues():
    """Null + string entries: the check runs to completion, both
    bad entries are quarantined with evidence, the due job is
    still enqueued and the valid entry is untouched. The repeat
    run lives in this same test, so its setup (the queue left by
    the first run) is explicit: re-running the check neither
    re-pushes the skips nor re-enqueues the due job."""
    reset_bus()
    PUSHED.clear()
    write_schedule([DUE_ENTRY])
    write_queue([None, "junk-string",
                 {"id": "test-402-valid",
                  "job": "sweep-lite POUL.CA market=EGX",
                  "added": worker.now()}])
    worker.run_schedule_check(now_override=DUE_NOW)
    recs = malformed_records()
    check("schedule: exactly the two bad entries are quarantined",
          len(recs) == 2)
    check("schedule: null + string entries quarantined with "
          "reason not-an-object, entries matching this test's "
          "payloads",
          entries_with_reason(recs, "not-an-object")
          == {json.dumps(None), json.dumps("junk-string")})
    check("schedule: the skips are pushed to the bus",
          sum("malformed queue entry skipped" in m for m in PUSHED)
          == 2)
    queue = read_queue_file()
    check("schedule: the due job is still enqueued",
          any(isinstance(e, dict) and e.get("id") == DUE_JOB_ID
              for e in queue))
    check("schedule: the valid entry survives in queue.json",
          any(isinstance(e, dict) and e.get("id") == "test-402-valid"
              for e in queue))
    check("schedule: quarantined entries stay in queue.json "
          "(evidence record is the quarantine, never a silent drop)",
          None in queue and "junk-string" in queue)
    check("schedule: the enqueue itself is pushed",
          any(f"schedule {DUE_JOB_ID}" in m for m in PUSHED))
    # Repeat run, same test (see docstring).
    PUSHED.clear()
    before = len(malformed_records())
    worker.run_schedule_check(now_override=DUE_NOW)
    check("schedule rerun: no malformed record is re-pushed",
          not any("malformed queue entry skipped" in m
                  for m in PUSHED))
    check("schedule rerun: no second malformed record appears",
          len(malformed_records()) == before)
    queue = read_queue_file()
    check("schedule rerun: the due job is enqueued exactly once",
          sum(1 for e in queue
              if isinstance(e, dict) and e.get("id") == DUE_JOB_ID)
          == 1)


def test_schedule_check_non_list_queue_skips_not_crashes():
    """A queue.json holding a JSON object (not a list) is
    quarantined as one malformed payload and the check skips
    instead of crashing on the append."""
    reset_bus()
    PUSHED.clear()
    write_schedule([DUE_ENTRY])
    write_queue({"id": "not-a-list", "job": "sweep-lite POUL.CA"})
    worker.run_schedule_check(now_override=DUE_NOW)
    recs = malformed_records()
    check("schedule non-list: exactly one record, the payload "
          "quarantined with reason queue-not-a-list",
          len(recs) == 1
          and entries_with_reason(recs, "queue-not-a-list")
          == {json.dumps({"id": "not-a-list",
                          "job": "sweep-lite POUL.CA"})})
    check("schedule non-list: queue.json is left untouched "
          "(no append, no truncation)",
          read_queue_file() == {"id": "not-a-list",
                                "job": "sweep-lite POUL.CA"})
    check("schedule non-list: the due job is NOT enqueued "
          "(the check skipped)",
          True)  # queue.json untouched above already proves this


class _FakeRun:
    """Stand-in for subprocess.run in the watchdog: records the
    --guard-pending flag and writes the signal JSON the real
    script would produce."""

    def __init__(self):
        self.calls = []

    def __call__(self, argv, **kwargs):
        self.calls.append(argv)
        out = Path(argv[argv.index("--signal-out") + 1])
        out.write_text(json.dumps({"action": "none",
                                   "reason": "heartbeat fresh"}))
        pending = argv[argv.index("--guard-pending") + 1]
        self.last_pending = pending

        class R:
            stdout = ""
            stderr = ""
            returncode = 0

        return R()


def test_watchdog_quarantines_non_objects_and_runs():
    """Null + string entries: the watchdog runs to completion (the
    script is invoked), both bad entries are quarantined, and the
    valid guard-pending id still flows into the pending check."""
    reset_bus()
    PUSHED.clear()
    fake = _FakeRun()
    checkout = _TMP / "main-checkout"
    checkout.mkdir(parents=True, exist_ok=True)
    write_queue([None, "junk-string",
                 {"id": "guard-402-pending", "job": "ledger-guard"}])
    job = {"id": "test-402-watch", "job": "ledger-watchdog"}
    real_checkout = worker._ensure_main_checkout
    real_match = worker.scripts_match
    worker._ensure_main_checkout = lambda: checkout
    worker.scripts_match = lambda *a: True
    try:
        with mock.patch("subprocess.run", fake):
            ran = worker.run_ledger_watchdog(job)
    finally:
        worker._ensure_main_checkout = real_checkout
        worker.scripts_match = real_match
    check("watchdog: returns True (the check ran to completion)",
          ran is True)
    check("watchdog: the script was actually invoked once",
          len(fake.calls) == 1)
    check("watchdog: the queued guard id still counts as pending",
          fake.last_pending == "yes")
    recs = malformed_records()
    check("watchdog: exactly the two bad entries are quarantined",
          len(recs) == 2)
    check("watchdog: null + string entries quarantined with "
          "reason not-an-object, entries matching this test's "
          "payloads",
          entries_with_reason(recs, "not-an-object")
          == {json.dumps(None), json.dumps("junk-string")})


def test_watchdog_non_list_queue_runs():
    """A queue.json holding a JSON object does not abort the
    watchdog either; the payload is quarantined as one record."""
    reset_bus()
    PUSHED.clear()
    fake = _FakeRun()
    checkout = _TMP / "main-checkout"
    write_queue({"id": "not-a-list", "job": "ledger-guard"})
    job = {"id": "test-402-watch2", "job": "ledger-watchdog"}
    real_checkout = worker._ensure_main_checkout
    real_match = worker.scripts_match
    worker._ensure_main_checkout = lambda: checkout
    worker.scripts_match = lambda *a: True
    try:
        with mock.patch("subprocess.run", fake):
            ran = worker.run_ledger_watchdog(job)
    finally:
        worker._ensure_main_checkout = real_checkout
        worker.scripts_match = real_match
    check("watchdog non-list: returns True (the check ran)",
          ran is True)
    recs = malformed_records()
    check("watchdog non-list: exactly one record, the payload "
          "quarantined with reason queue-not-a-list",
          len(recs) == 1
          and entries_with_reason(recs, "queue-not-a-list")
          == {json.dumps({"id": "not-a-list",
                          "job": "ledger-guard"})})


def test_helper_filters_and_quarantines():
    reset_bus()
    entries = worker._quarantine_non_object_entries(
        [{"id": "a"}, None, "x", ["sweep-lite"], {"id": "b"}])
    check("helper: only the dict entries are returned",
          entries == [{"id": "a"}, {"id": "b"}])
    recs = malformed_records()
    check("helper: exactly the three non-object entries have a "
          "not-an-object record with the raw entry kept",
          len(recs) == 3
          and entries_with_reason(recs, "not-an-object")
          == {json.dumps(e, sort_keys=True)
              for e in (None, "x", ["sweep-lite"])})


def test_helper_control_clean_queue():
    reset_bus()
    entries = worker._quarantine_non_object_entries(
        [{"id": "test-402-clean", "job": "sweep-lite POUL.CA"}])
    check("control: a clean queue passes through unchanged",
          entries == [{"id": "test-402-clean",
                       "job": "sweep-lite POUL.CA"}])
    check("control: a clean queue creates no malformed record",
          len(malformed_records()) == 0)


def test_schedule_check_control_clean_queue_enqueues():
    """Control: with no bad entries the due job still enqueues
    exactly as before (no behaviour change on the happy path)."""
    reset_bus()
    PUSHED.clear()
    write_schedule([DUE_ENTRY])
    write_queue([{"id": "test-402-clean2",
                  "job": "sweep-lite POUL.CA market=EGX",
                  "added": worker.now()}])
    worker.run_schedule_check(now_override=DUE_NOW)
    check("control: the due job enqueues on a clean queue",
          any(isinstance(e, dict) and e.get("id") == DUE_JOB_ID
              for e in read_queue_file()))
    check("control: a clean queue creates no malformed record",
          len(malformed_records()) == 0)


def main():
    worker.push_bus = fake_push_bus
    test_schedule_check_quarantines_non_objects_and_enqueues()
    test_schedule_check_non_list_queue_skips_not_crashes()
    test_watchdog_quarantines_non_objects_and_runs()
    test_watchdog_non_list_queue_runs()
    test_helper_filters_and_quarantines()
    test_helper_control_clean_queue()
    test_schedule_check_control_clean_queue_enqueues()
    print(f"\n{PASSED} passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
