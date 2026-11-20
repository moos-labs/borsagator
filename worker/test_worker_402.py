#!/usr/bin/env python3
"""Regression tests for issue #402 (CodeRabbit #399 follow-up):
non-object queue entries crash run_schedule_check + the ledger
watchdog before quarantine — same malformed-queue family as #391.

Two gaps in main at the fix tip:

1. `run_schedule_check` did
   `handled = {str(j.get("id", "")) for j in queue}` where `queue`
   came from `read_queue()`, which returned the raw parsed JSON
   list with NO isinstance filtering. A null/string queue entry
   therefore raised AttributeError out of run_schedule_check(),
   which runs at the top of every poll cycle (main() L4452) BEFORE
   the queue loop — so the cycle-level catch retried and failed at
   the same point forever: the bad entry was never quarantined
   (the #391 queue-loop quarantine never ran) and no valid job
   ever processed. Head-of-line stall, one layer earlier than #391.

2. `run_ledger_watchdog` had the same unguarded pattern:
   `queue_ids = [str(j.get("id", "")) for j in read_queue()]` —
   a non-dict entry aborted the watchdog job before it ran.

Fix: filter once in read_queue() with a quarantine pass — a
non-dict entry is quarantined with evidence (the #391
_quarantine_malformed_job pattern, reason "not-an-object") and
dropped from the returned list, so no caller can crash on it.
A non-list queue.json is treated like an unreadable queue
(QUEUE_ERROR, empty list). The main loop's own isinstance guard
(#391) stays as defence in depth.

Harness-first: FAILS on pristine main (AttributeError out of
run_schedule_check / run_ledger_watchdog for a null/string
entry; no malformed record anywhere) and PASSES on the fixed
tree. Stdlib only.

Run: python3 worker/test_worker_402.py (exit 0 = all pass).
"""
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

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


def queue_path():
    return worker.BUS / "queue" / "queue.json"


def write_queue(entries):
    queue_path().parent.mkdir(parents=True, exist_ok=True)
    queue_path().write_text(json.dumps(entries, indent=1))


def malformed_dir():
    return worker.BUS / "queue" / "malformed"


def malformed_records():
    d = malformed_dir()
    if not d.exists():
        return {}
    return {f.stem: json.loads(f.read_text())
            for f in sorted(d.glob("*.json"))}


VALID_JOB = {"id": "test-402-ok", "job": "sweep-lite POUL.CA",
             "added": worker.now()}


def test_read_queue_filters_and_quarantines_non_objects():
    PUSHED.clear()
    bad = [None, "just-a-string", ["sweep-lite", "POUL.CA"], 42, True]
    write_queue(bad + [dict(VALID_JOB)])
    got = worker.read_queue()
    check("read_queue: only the dict entry is returned",
          got == [VALID_JOB])
    recs = malformed_records()
    check("read_queue: every non-dict entry is quarantined",
          len([r for r in recs.values()
               if r["reason"] == "not-an-object"]) == len(bad))
    check("read_queue: quarantined entries keep the raw entry as "
          "evidence",
          all(any(r["entry"] == b for r in recs.values())
              for b in bad))
    check("read_queue: each quarantine is pushed to the bus",
          sum("malformed queue entry skipped" in m for m in PUSHED)
          == len(bad))
    pushes_after_first = len(PUSHED)
    worker.read_queue()
    check("read_queue: a second read does not re-push the skips",
          len(PUSHED) == pushes_after_first)
    check("read_queue: no QUEUE_ERROR for a list with bad entries",
          worker.QUEUE_ERROR is None)


def test_read_queue_rejects_non_list():
    for data in ({"id": "test-402-dict"}, "junk-string", None):
        before = len(malformed_records())
        write_queue(data)
        check(f"read_queue: non-list {data!r} returns an empty list",
              worker.read_queue() == [])
        check(f"read_queue: non-list {data!r} sets QUEUE_ERROR",
              worker.QUEUE_ERROR is not None)
        check(f"read_queue: non-list {data!r} quarantines nothing",
              len(malformed_records()) == before)


def test_valid_queue_unchanged():
    write_queue([dict(VALID_JOB),
                 {"id": "test-402-ok2", "job": "sweep-lite POUL.CA"}])
    before = len(malformed_records())
    got = worker.read_queue()
    check("control: a valid queue is returned unchanged",
          [j["id"] for j in got] == ["test-402-ok", "test-402-ok2"])
    check("control: a valid queue quarantines nothing",
          len(malformed_records()) == before)
    check("control: a valid queue sets no QUEUE_ERROR",
          worker.QUEUE_ERROR is None)


def test_schedule_check_runs_with_non_object_entries():
    """End-to-end at run_schedule_check level: a queue holding a
    null and a string entry still enqueues a due scheduled job in
    the same call — the old code raised AttributeError before any
    enqueue or quarantine could happen."""
    PUSHED.clear()
    entry = {"id": "sched-test-402", "job": "sweep-lite POUL.CA",
             "days": ["Fri"], "time": "08:15", "tz": "Africa/Cairo"}
    sched = worker.BUS / worker.SCHEDULE_FILE
    sched.parent.mkdir(parents=True, exist_ok=True)
    sched.write_text(json.dumps([entry], indent=1))
    write_queue([None, "junk-string", dict(VALID_JOB)])
    # Fri 2026-11-20 06:20 UTC == 08:20 Cairo: after the 08:15
    # fire, before the 09:30 catch-up cutoff -> "fire".
    now_override = datetime(2026, 11, 20, 6, 20, tzinfo=timezone.utc)
    worker.run_schedule_check(now_override=now_override)
    after = json.loads(queue_path().read_text())
    ids = [j["id"] for j in after]
    check("schedule check: the due job is enqueued despite the bad "
          "entries",
          "sched-2026-11-20" in ids)
    check("schedule check: the pre-existing valid entry survives "
          "the rewrite",
          "test-402-ok" in ids)
    check("schedule check: the bad entries are gone from the "
          "rewritten queue.json",
          len(after) == 2)
    recs = malformed_records()
    check("schedule check: the null entry is quarantined",
          any(r["reason"] == "not-an-object" and r["entry"] is None
              for r in recs.values()))
    check("schedule check: the string entry is quarantined",
          any(r["reason"] == "not-an-object"
              and r["entry"] == "junk-string" for r in recs.values()))
    check("schedule check: the enqueue is pushed to the bus",
          "schedule sched-2026-11-20" in PUSHED)


def test_watchdog_runs_with_non_object_entries():
    """End-to-end at run_ledger_watchdog level: a queue holding a
    null and a string entry still runs the watchdog to completion
    — the old code raised AttributeError on the queue_ids line
    before the script ever ran."""
    PUSHED.clear()
    write_queue([None, "junk-string", dict(VALID_JOB)])
    job = {"id": "test-402-watch", "job": "ledger-watchdog"}
    fake_checkout = _TMP / "fake-checkout"
    fake_checkout.mkdir(parents=True, exist_ok=True)
    real_checkout = worker._ensure_main_checkout
    real_match = worker.scripts_match
    worker._ensure_main_checkout = lambda: fake_checkout
    worker.scripts_match = lambda *a, **k: True
    completed = subprocess.CompletedProcess(args=[], returncode=0,
                                            stdout="", stderr="")
    try:
        with mock.patch("subprocess.run",
                        return_value=completed) as run_spy:
            result = worker.run_ledger_watchdog(job)
    finally:
        worker._ensure_main_checkout = real_checkout
        worker.scripts_match = real_match
    check("watchdog: returns True (ran to completion) despite the "
          "bad entries",
          result is True)
    check("watchdog: the watch script is still invoked",
          run_spy.call_count == 1)
    recs = malformed_records()
    check("watchdog: the null entry is quarantined",
          any(r["reason"] == "not-an-object" and r["entry"] is None
              for r in recs.values()))
    check("watchdog: the string entry is quarantined",
          any(r["reason"] == "not-an-object"
              and r["entry"] == "junk-string" for r in recs.values()))


def main():
    worker.push_bus = fake_push_bus
    test_read_queue_filters_and_quarantines_non_objects()
    test_read_queue_rejects_non_list()
    test_valid_queue_unchanged()
    test_schedule_check_runs_with_non_object_entries()
    test_watchdog_runs_with_non_object_entries()
    print(f"\n{PASSED} passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
