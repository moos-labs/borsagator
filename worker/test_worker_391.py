#!/usr/bin/env python3
"""Regression tests for issue #391 (INS-383 follow-up to #381):
claim() KeyError on a malformed queue entry (missing job/id) can
stall the cycle head-of-line.

Two gaps in main at the #392 tip:

1. `claim()` used `job["id"]` / `job["job"]` directly, so a queue
   entry missing the `job` (or `id`) key raised KeyError — before
   `_execute` ever ran, so the #381 `job_text()` normalization never
   got a chance — and the cycle-level catch in main() aborted the
   queue loop, so one malformed entry stalled every later entry
   head-of-line, every cycle. The same unguarded `job["job"]` sat
   in `_begin_execution` (intent write) for the missing-key case.
   Fix: reject at claim time with a recorded skip — a malformed
   entry is quarantined to queue/malformed/<name>.json (named
   failure record, raw entry kept as evidence) and claim() returns
   False, never raises; the main loop moves on to the next entry.
   main() also routes bad-id entries (previously silently skipped,
   and non-dict entries raised AttributeError on job.get) through
   the same quarantine.

2. A `job` key that is present but None/non-string is deliberately
   NOT rejected here: #381 routes those through _execute_body,
   which fails closed with a named unknown-job / invalid-job-type
   failure (pinned by test_worker_381). Only the missing KEY (or
   a missing/invalid id, or a non-dict entry) is quarantined at
   claim time.

Harness-first: FAILS on pristine main (KeyError out of claim() for
a missing-job entry; AttributeError out of the main loop for a
non-dict entry; no malformed record anywhere) and PASSES on the
fixed tree. Stdlib only.

Run: python3 worker/test_worker_391.py (exit 0 = all pass).
"""
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest import mock

_TMP = Path(tempfile.mkdtemp(prefix="gator391-test-"))
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


def malformed_dir():
    return worker.BUS / "queue" / "malformed"


def malformed_records():
    d = malformed_dir()
    if not d.exists():
        return {}
    return {f.stem: json.loads(f.read_text())
            for f in sorted(d.glob("*.json"))}


def claims_dir():
    return worker.BUS / "queue" / "claims"


def test_missing_job_quarantined_not_raised():
    PUSHED.clear()
    job = {"id": "test-391-nojob", "added": worker.now()}
    check("missing-job entry: claim() returns False, never raises",
          worker.claim(job) is False)
    check("missing-job entry: no claim file is written",
          not (claims_dir() / "test-391-nojob.json").exists())
    recs = malformed_records()
    check("missing-job entry: a named malformed record exists",
          "test-391-nojob" in recs)
    check("missing-job entry: reason recorded as missing-job",
          recs["test-391-nojob"]["reason"] == "missing-job")
    check("missing-job entry: raw entry kept as evidence",
          recs["test-391-nojob"]["entry"] == job)
    check("missing-job entry: the skip is pushed to the bus",
          any("malformed queue entry skipped test-391-nojob"
              in m for m in PUSHED))


def test_missing_id_quarantined_not_raised():
    PUSHED.clear()
    job = {"job": "sweep-lite POUL.CA", "added": worker.now()}
    check("missing-id entry: claim() returns False, never raises",
          worker.claim(job) is False)
    recs = malformed_records()
    check("missing-id entry: exactly one no-id-* record exists",
          len([k for k in recs if k.startswith("no-id-")]) == 1)
    name = [k for k in recs if k.startswith("no-id-")][0]
    check("missing-id entry: reason recorded as "
          "missing-or-invalid-id",
          recs[name]["reason"] == "missing-or-invalid-id")
    check("missing-id entry: raw entry kept as evidence",
          recs[name]["entry"] == job)
    check("missing-id entry: the skip is pushed to the bus",
          any(f"malformed queue entry skipped {name}" in m
              for m in PUSHED))


def test_non_dict_and_bad_id_quarantined():
    for entry, reason in (("just-a-string", "not-an-object"),
                          (["sweep-lite", "POUL.CA"], "not-an-object"),
                          ({"id": "bad/id", "job": "sweep-lite POUL.CA"},
                           "missing-or-invalid-id"),
                          ({"id": 123, "job": "sweep-lite POUL.CA"},
                           "missing-or-invalid-id")):
        PUSHED.clear()
        check(f"malformed entry {entry!r}: claim() returns False, "
              "never raises", worker.claim(entry) is False)
        recs = malformed_records()
        check(f"malformed entry {entry!r}: a record with reason "
              f"{reason} exists",
              any(r["reason"] == reason and r["entry"] == entry
                  for r in recs.values()))


def test_quarantine_is_idempotent():
    PUSHED.clear()
    job = {"id": "test-391-dup", "added": worker.now()}
    worker.claim(job)
    pushes_after_first = len(PUSHED)
    check("second claim() of the same malformed entry does not "
          "re-push the skip",
          worker.claim(job) is False
          and len(PUSHED) == pushes_after_first)
    check("second claim() still leaves exactly one record",
          len([k for k in malformed_records()
               if k == "test-391-dup"]) == 1)


def test_valid_entry_still_claims():
    PUSHED.clear()
    job = {"id": "test-391-ok", "job": "sweep-lite POUL.CA",
           "added": worker.now()}
    check("control: a valid entry still claims (returns True)",
          worker.claim(job) is True)
    claim_file = claims_dir() / "test-391-ok.json"
    check("control: the claim file is written with the job text",
          json.loads(claim_file.read_text())["job"]
          == "sweep-lite POUL.CA")
    check("control: the claim is pushed to the bus",
          "claim test-391-ok" in PUSHED)
    check("control: no malformed record for the valid entry",
          "test-391-ok" not in malformed_records())


def test_begin_execution_missing_job_refuses_without_intent():
    job = {"id": "test-391-intent", "added": worker.now()}
    check("_begin_execution with a missing job key: returns False, "
          "never raises",
          worker._begin_execution(job) is False)
    check("_begin_execution with a missing job key: no intent file "
          "is written",
          not (worker.JOB_STATE / "test-391-intent.intent").exists())
    check("_begin_execution with a non-dict job: returns False, "
          "never raises",
          worker._begin_execution("not-a-dict") is False)


def test_begin_execution_valid_still_writes_intent():
    job = {"id": "test-391-intent-ok", "job": "sweep-lite POUL.CA",
           "added": worker.now()}
    check("control: _begin_execution still writes the intent for "
          "a valid entry",
          worker._begin_execution(job) is True)
    intent = worker.JOB_STATE / "test-391-intent-ok.intent"
    check("control: the intent carries the job text",
          json.loads(intent.read_text())["job"]
          == "sweep-lite POUL.CA")


def test_heartbeat_surfaces_malformed():
    worker.update_checkout_sha = lambda: "test-sha-391"
    worker.heartbeat()
    payload = json.loads(
        (worker.BUS / "queue" / "heartbeat.json").read_text())
    check("heartbeat: malformed entries are surfaced",
          "test-391-nojob" in payload.get("malformed_queue", [])
          and "test-391-dup" in payload.get("malformed_queue", []))


class _StopCycle(Exception):
    pass


def test_cycle_does_not_stall_head_of_line():
    """End-to-end at the main() loop level: a queue whose first two
    entries are malformed (missing id, then missing job) still
    reaches and executes the valid third entry in the same cycle —
    no KeyError/AttributeError aborts the loop."""
    queue = [{"job": "sweep-lite POUL.CA", "added": worker.now()},
             {"id": "test-391-cycle-bad", "added": worker.now()},
             {"id": "test-391-cycle-ok", "job": "sweep-lite POUL.CA",
              "added": worker.now()}]
    executed = []
    worker.read_queue = lambda: list(queue)
    worker.execute = lambda job: executed.append(job["id"])
    for name in ("self_update", "sync_bus", "flush_pending_done",
                 "run_schedule_check", "reclaim_stale_claims",
                 "prune_out", "heartbeat"):
        setattr(worker, name, lambda *a, **k: None)
    err = Path(_TMP) / "cycle-stderr.txt"
    with err.open("w") as err_f, \
            mock.patch("time.sleep",
                       side_effect=_StopCycle), \
            mock.patch.object(sys, "stderr", err_f):
        try:
            worker.main()
        except _StopCycle:
            pass
    check("cycle: the valid entry after two malformed ones is "
          "executed in the same cycle",
          executed == ["test-391-cycle-ok"])
    recs = malformed_records()
    check("cycle: the missing-id entry is quarantined",
          any(r["reason"] == "missing-or-invalid-id"
              for r in recs.values()))
    check("cycle: the missing-job entry is quarantined",
          recs.get("test-391-cycle-bad", {}).get("reason")
          == "missing-job")
    check("cycle: no 'worker cycle error' was raised by the loop",
          "worker cycle error" not in err.read_text())


def main():
    worker.push_bus = fake_push_bus
    test_missing_job_quarantined_not_raised()
    test_missing_id_quarantined_not_raised()
    test_non_dict_and_bad_id_quarantined()
    test_quarantine_is_idempotent()
    test_valid_entry_still_claims()
    test_begin_execution_missing_job_refuses_without_intent()
    test_begin_execution_valid_still_writes_intent()
    test_heartbeat_surfaces_malformed()
    test_cycle_does_not_stall_head_of_line()
    print(f"\n{PASSED} passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
