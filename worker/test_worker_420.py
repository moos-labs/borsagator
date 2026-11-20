#!/usr/bin/env python3
"""Regression tests for issue #420: the main loop iterated the raw
read_queue() payload with no top-level list validation.

A queue.json holding a scalar (`42`, `null`) parses fine
(QUEUE_ERROR stays None) and the loop raised TypeError at
iteration; a top-level string/object iterated as chars/keys, so
each char/key was quarantined as its own "missing-or-invalid-id"
record. _quarantine_non_object_entries() already handled non-list
queues ("queue-not-a-list", returns []) but only run_schedule_check
and the ledger watchdog called it — the main loop never did. With
schedule.json absent/empty, run_schedule_check returns before
quarantine, so no diagnostic was recorded at all.

Fix: main() routes its queue through
_quarantine_non_object_entries() before iterating, so a non-list
payload is quarantined as ONE record and the cycle continues.
Deliberate #391 reason update: a non-dict entry inside a list
queue is now quarantined as "not-an-object" (the helper's reason)
instead of the loop's old "missing-or-invalid-id" — the #391
dict-entry reasons (missing-or-invalid-id / missing-job) are
unchanged, and claim() is untouched.

Harness-first: FAILS on pristine main (TypeError out of the loop
for a scalar queue, no malformed record; one record per char/key
for a string/object queue) and PASSES on the fixed tree. Stdlib
only.

Run: python3 worker/test_worker_420.py (exit 0 = all pass).
"""
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest import mock

_TMP = Path(tempfile.mkdtemp(prefix="gator420-test-"))
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


def write_queue_raw(text):
    (queue_dir() / "queue.json").write_text(text)


def write_queue(payload):
    write_queue_raw(json.dumps(payload))


def read_queue_file():
    return json.loads((queue_dir() / "queue.json").read_text())


def malformed_records():
    d = worker.BUS / "queue" / "malformed"
    if not d.exists():
        return {}
    return {f.stem: json.loads(f.read_text())
            for f in sorted(d.glob("*.json"))}


def reset_bus():
    """Empty BUS queue state before an independent test, so a
    malformed-record assertion can only pass on records written
    by that test (CodeRabbit Minor on PR #407)."""
    d = worker.BUS / "queue"
    if d.exists():
        shutil.rmtree(d)


class _StopCycle(Exception):
    pass


def run_one_cycle(real_schedule_check=False):
    """Run main() for exactly one poll cycle (time.sleep raises
    _StopCycle) with the cycle helpers stubbed — except, when
    real_schedule_check is set, the real run_schedule_check, so
    the test proves the diagnostic is recorded even when the
    schedule check returns early on an absent schedule. Returns
    the cycle stderr text."""
    stubs = ["self_update", "sync_bus", "flush_pending_done",
             "reclaim_stale_claims", "prune_out", "heartbeat"]
    if not real_schedule_check:
        stubs.append("run_schedule_check")
    saved = {}
    for name in stubs:
        saved[name] = getattr(worker, name)
        setattr(worker, name, lambda *a, **k: None)
    err = Path(_TMP) / "cycle-stderr.txt"
    try:
        with err.open("w") as err_f, \
                mock.patch("time.sleep",
                           side_effect=_StopCycle), \
                mock.patch.object(sys, "stderr", err_f):
            try:
                worker.main()
            except _StopCycle:
                pass
    finally:
        for name, fn in saved.items():
            setattr(worker, name, fn)
    return err.read_text()


def test_scalar_queue_quarantined_no_type_error():
    """queue.json `42` / `null`: no TypeError, one
    queue-not-a-list record, queue.json untouched, cycle
    continues to a valid queue afterwards."""
    for payload in (42, None):
        reset_bus()
        PUSHED.clear()
        executed = []
        worker.execute = lambda job: executed.append(job["id"])
        write_queue(payload)
        stderr = run_one_cycle()
        recs = malformed_records()
        check(f"scalar queue {payload!r}: no 'worker cycle error' "
              "was raised by the loop",
              "worker cycle error" not in stderr)
        check(f"scalar queue {payload!r}: exactly one malformed "
              "record exists",
              len(recs) == 1)
        check(f"scalar queue {payload!r}: the record carries "
              "reason queue-not-a-list with the raw payload kept",
              any(r["reason"] == "queue-not-a-list"
                  and r["entry"] == payload for r in recs.values()))
        check(f"scalar queue {payload!r}: the skip is pushed to "
              "the bus",
              any("malformed queue entry skipped" in m
                  for m in PUSHED))
        check(f"scalar queue {payload!r}: queue.json is left "
              "untouched (the payload stays for re-quarantine "
              "evidence, never silently dropped)",
              read_queue_file() == payload)
        check(f"scalar queue {payload!r}: nothing executes",
              executed == [])
        # Cycle continues: a valid queue in the next cycle runs.
        PUSHED.clear()
        write_queue([{"id": "test-420-after-scalar",
                      "job": "sweep-lite POUL.CA",
                      "added": worker.now()}])
        stderr = run_one_cycle()
        check(f"scalar queue {payload!r}: the next cycle with a "
              "valid queue executes the job",
              executed == ["test-420-after-scalar"])
        check(f"scalar queue {payload!r}: the follow-up cycle "
              "raises no cycle error",
              "worker cycle error" not in stderr)


def test_string_and_object_queue_single_record():
    """A top-level string/object queue is ONE quarantined
    payload — not one record per char/key."""
    for payload in ("sweep-lite", {"id": "not-a-list",
                                    "job": "sweep-lite POUL.CA"}):
        reset_bus()
        PUSHED.clear()
        worker.execute = lambda job: None
        write_queue(payload)
        stderr = run_one_cycle()
        recs = malformed_records()
        check(f"non-list queue {payload!r}: no 'worker cycle "
              "error' was raised by the loop",
              "worker cycle error" not in stderr)
        check(f"non-list queue {payload!r}: exactly one malformed "
              "record exists (not one per char/key)",
              len(recs) == 1)
        check(f"non-list queue {payload!r}: the record carries "
              "reason queue-not-a-list with the raw payload kept",
              any(r["reason"] == "queue-not-a-list"
                  and r["entry"] == payload for r in recs.values()))
        check(f"non-list queue {payload!r}: queue.json is left "
              "untouched",
              read_queue_file() == payload)


def test_no_schedule_case_records_diagnostic():
    """With schedule.json ABSENT, run_schedule_check returns
    before quarantine — the diagnostic must still be recorded,
    by the main loop itself. The real schedule check runs here
    (not a stub), so this pins the #420 gap exactly."""
    reset_bus()
    PUSHED.clear()
    worker.execute = lambda job: None
    write_queue(42)
    check("no-schedule case: schedule.json is absent",
          not (queue_dir() / "schedule.json").exists())
    stderr = run_one_cycle(real_schedule_check=True)
    recs = malformed_records()
    check("no-schedule case: no 'worker cycle error' was raised",
          "worker cycle error" not in stderr)
    check("no-schedule case: the scalar payload is quarantined "
          "as queue-not-a-list even with no schedule",
          len(recs) == 1
          and any(r["reason"] == "queue-not-a-list"
                  and r["entry"] == 42 for r in recs.values()))


def test_list_queue_non_dict_entry_reason_update():
    """Deliberate #391 reason update: a non-dict entry inside a
    list queue is now quarantined as "not-an-object" (the helper's
    reason) instead of the loop's old "missing-or-invalid-id" —
    and the valid entry in the same queue still executes."""
    reset_bus()
    PUSHED.clear()
    executed = []
    worker.execute = lambda job: executed.append(job["id"])
    write_queue([None, "junk-string",
                 {"id": "test-420-valid",
                  "job": "sweep-lite POUL.CA",
                  "added": worker.now()}])
    stderr = run_one_cycle()
    recs = malformed_records()
    check("list queue: the valid entry executes in the same cycle",
          executed == ["test-420-valid"])
    check("list queue: exactly the two bad entries are "
          "quarantined",
          len(recs) == 2)
    check("list queue: null + string entries quarantined with "
          "reason not-an-object, entries matching this test's "
          "payloads",
          {json.dumps(r["entry"], sort_keys=True)
           for r in recs.values()
           if r["reason"] == "not-an-object"}
          == {json.dumps(None), json.dumps("junk-string")})
    check("list queue: no 'worker cycle error' was raised",
          "worker cycle error" not in stderr)


def test_control_clean_queue_unchanged():
    """Control: a clean list queue executes exactly as before and
    creates no malformed record (no behaviour change on the
    happy path)."""
    reset_bus()
    PUSHED.clear()
    executed = []
    worker.execute = lambda job: executed.append(job["id"])
    write_queue([{"id": "test-420-clean",
                  "job": "sweep-lite POUL.CA",
                  "added": worker.now()}])
    stderr = run_one_cycle()
    check("control: the valid entry executes",
          executed == ["test-420-clean"])
    check("control: a clean queue creates no malformed record",
          len(malformed_records()) == 0)
    check("control: no 'worker cycle error' was raised",
          "worker cycle error" not in stderr)


def main():
    worker.push_bus = fake_push_bus
    test_scalar_queue_quarantined_no_type_error()
    test_string_and_object_queue_single_record()
    test_no_schedule_case_records_diagnostic()
    test_list_queue_non_dict_entry_reason_update()
    test_control_clean_queue_unchanged()
    print(f"\n{PASSED} passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
