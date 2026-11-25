#!/usr/bin/env python3
"""Regression tests for issue #610 item 4c (T4 spec): skip a late
guard/watch slot when a newer slot of the same kind is already
queued or has already landed — mark superseded (done record, no
execute) instead of running the stale slot (~10.5 min each), which
blocked the lane-1 work behind 42 stale control jobs (guard slots
Nov 21 0047Z -> Nov 25 1747Z + watches).

`_superseded_slot` is pure (no I/O, no globals), so the helper
cases run directly. The `_mark_superseded` integration case runs
the real `_mark_done` with `_publish_done` stubbed to success and
checks the done record validates as a receipt and gates
re-execution via `_done_or_pending` — the property the live
worker relies on so a skipped job is never re-executed.

Harness-first: FAILS on pristine main (no `_superseded_slot` /
`_mark_superseded`; the integration case has no record to gate on)
and PASSES on the fixed tree. Stdlib only.

Run: python3 worker/test_worker_610_4c.py (exit 0 = all pass).
"""
import json
import os
import sys
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="gator610-4c-test-"))
os.environ["GATOR_ROOT"] = str(_TMP)

_HERE = Path(os.path.abspath(__file__)).parent
sys.path.insert(0, str(_HERE))

import worker  # noqa: E402

PASSED = 0


def check(name, cond):
    global PASSED
    assert cond, name
    PASSED += 1
    print(f"pass: {name}")


def guard(slot):
    return {"id": f"guard-{slot}", "job": "ledger-guard"}


def watch(slot):
    return {"id": f"watch-{slot}", "job": "ledger-watchdog"}


# --- pure-helper cases -------------------------------------------------

def test_older_guard_superseded_by_newer_queued_guard():
    queue = [guard("2026-11-21T0047Z"), guard("2026-11-25T1747Z")]
    superseded, by, reason = worker._superseded_slot(
        "guard-2026-11-21T0047Z", "ledger-guard", queue, set())
    check("helper: older guard superseded by newer queued guard",
          superseded is True)
    check("helper: superseded_by is the newer queued guard id",
          by == "guard-2026-11-25T1747Z")
    check("helper: reason names the superseder",
          reason == "superseded by guard-2026-11-25T1747Z")


def test_newest_guard_not_superseded():
    queue = [guard("2026-11-21T0047Z"), guard("2026-11-25T1747Z")]
    superseded, by, _ = worker._superseded_slot(
        "guard-2026-11-25T1747Z", "ledger-guard", queue, set())
    check("helper: newest guard is NOT superseded",
          superseded is False and by is None)


def test_older_guard_superseded_by_newer_done_guard():
    queue = [guard("2026-11-21T0047Z")]
    done = {"guard-2026-11-25T1747Z"}
    superseded, by, _ = worker._superseded_slot(
        "guard-2026-11-21T0047Z", "ledger-guard", queue, done)
    check("helper: older guard superseded by newer done guard",
          superseded is True)
    check("helper: superseded_by is the newer done guard id",
          by == "guard-2026-11-25T1747Z")


def test_superseded_by_is_newest_later_slot():
    queue = [guard("2026-11-21T0047Z"), guard("2026-11-23T0047Z"),
             guard("2026-11-25T1747Z")]
    done = {"guard-2026-11-24T0047Z"}
    superseded, by, _ = worker._superseded_slot(
        "guard-2026-11-21T0047Z", "ledger-guard", queue, done)
    check("helper: superseded_by is the NEWEST later slot, queued "
          "or done", superseded is True
          and by == "guard-2026-11-25T1747Z")


def test_manual_guard_never_superseded():
    queue = [{"id": "manual-guard-2026-11-25", "job": "ledger-guard"},
             guard("2026-11-25T1747Z")]
    superseded, _, _ = worker._superseded_slot(
        "manual-guard-2026-11-25", "ledger-guard", queue, set())
    check("helper: manual-guard job is NEVER superseded",
          superseded is False)


def test_sched_job_never_superseded():
    queue = [{"id": "sched-2026-11-25", "job": "ledger-guard"},
             guard("2026-11-25T1747Z")]
    superseded, _, _ = worker._superseded_slot(
        "sched-2026-11-25", "ledger-guard", queue, set())
    check("helper: sched-* job is NEVER superseded",
          superseded is False)


def test_watch_same_kind_only():
    # A newer GUARD does not supersede a watch, and a newer done
    # guard does not either — kinds supersede only their own.
    queue = [watch("2026-11-21T0047Z"), guard("2026-11-25T1747Z")]
    done = {"guard-2026-11-25T1747Z"}
    superseded, _, _ = worker._superseded_slot(
        "watch-2026-11-21T0047Z", "ledger-watchdog", queue, done)
    check("helper: newer guard (queued or done) does NOT supersede "
          "a watch", superseded is False)
    # ... but a newer queued watch does.
    queue.append(watch("2026-11-25T1747Z"))
    superseded, by, _ = worker._superseded_slot(
        "watch-2026-11-21T0047Z", "ledger-watchdog", queue, done)
    check("helper: newer queued watch DOES supersede an older watch",
          superseded is True and by == "watch-2026-11-25T1747Z")


def test_guard_done_does_not_supersede_watch_done_branch():
    # Cross-kind in the done branch alone: only a done guard exists.
    superseded, _, _ = worker._superseded_slot(
        "watch-2026-11-21T0047Z", "ledger-watchdog", [], 
        {"guard-2026-11-25T1747Z"})
    check("helper: newer done guard alone does NOT supersede a watch",
          superseded is False)


def test_unparseable_id_never_superseded():
    queue = [guard("2026-11-25T1747Z")]
    for bad_id in ("guard-not-a-date", "guard-2026-13-45T9967Z",
                   "guard-2026-11-25T1747", "guard2026-11-25T1747Z"):
        superseded, _, _ = worker._superseded_slot(
            bad_id, "ledger-guard", queue, set())
        check(f"helper: unparseable id {bad_id} is NEVER superseded "
              "(fail closed)", superseded is False)


def test_non_slot_job_never_superseded():
    queue = [guard("2026-11-25T1747Z"),
             {"id": "sweep-1", "job": "sweep-lite POUL.CA market=EGX"}]
    superseded, _, _ = worker._superseded_slot(
        "sweep-1", "sweep-lite POUL.CA market=EGX", queue, set())
    check("helper: non-slot job text is NEVER superseded",
          superseded is False)
    # A guard id with a non-guard job text is not a guard slot.
    superseded, _, _ = worker._superseded_slot(
        "guard-2026-11-21T0047Z", "sweep-lite POUL.CA market=EGX",
        queue, set())
    check("helper: guard id with non-guard job text is NEVER "
          "superseded", superseded is False)


def test_done_same_id_does_not_supersede_itself():
    # Its own done record (same slot) is not "strictly later".
    superseded, _, _ = worker._superseded_slot(
        "guard-2026-11-21T0047Z", "ledger-guard",
        [guard("2026-11-21T0047Z")], {"guard-2026-11-21T0047Z"})
    check("helper: a done record for the SAME slot does not "
          "supersede it", superseded is False)


def test_done_newer_queued_older_ignored():
    # A queued job with an EARLIER slot than this one is not a
    # superseder, even when this job has no newer slot anywhere.
    queue = [guard("2026-11-20T0047Z"), guard("2026-11-21T0047Z")]
    superseded, _, _ = worker._superseded_slot(
        "guard-2026-11-21T0047Z", "ledger-guard", queue, set())
    check("helper: an older queued slot does not supersede",
          superseded is False)


# --- _mark_superseded integration --------------------------------------

def test_mark_superseded_record_validates_and_gates():
    """The real _mark_done path with _publish_done stubbed to
    success: the superseded record keeps all five RECEIPT_KEYS as
    strings (so _valid_receipt accepts it), carries the superseded
    markers, and afterwards _done_or_pending blocks re-execution
    of the skipped slot."""
    job = guard("2026-11-21T0047Z")
    published = {}
    real_publish = worker._publish_done

    def stub_publish(job_id, record, attempts=5):
        published["job_id"] = job_id
        published["record"] = record
        return True

    worker._publish_done = stub_publish
    try:
        rc = worker._mark_superseded(
            job, "ledger-guard", "guard-2026-11-25T1747Z",
            "superseded by guard-2026-11-25T1747Z")
    finally:
        worker._publish_done = real_publish
    check("mark_superseded: _mark_done reports success", rc is True)
    rec = json.loads(published["record"])
    check("mark_superseded: all five RECEIPT_KEYS present as strings",
          all(isinstance(rec.get(k), str) for k in worker.RECEIPT_KEYS)
          and set(worker.RECEIPT_KEYS) <= set(rec))
    check("mark_superseded: record shape matches a live done record "
          "(job text, archive label, id)",
          rec["job"] == "ledger-guard"
          and rec["archive"] == "ledger-guard"
          and rec["id"] == "guard-2026-11-21T0047Z")
    check("mark_superseded: record validates as a receipt",
          worker._valid_receipt(published["record"], job["id"]))
    check("mark_superseded: superseded markers carried",
          rec.get("superseded") is True
          and rec.get("superseded_by") == "guard-2026-11-25T1747Z"
          and rec.get("reason")
          == "superseded by guard-2026-11-25T1747Z")
    check("mark_superseded: skipped job is gated from re-execution",
          worker._done_or_pending(job["id"]))


def main():
    test_older_guard_superseded_by_newer_queued_guard()
    test_newest_guard_not_superseded()
    test_older_guard_superseded_by_newer_done_guard()
    test_superseded_by_is_newest_later_slot()
    test_manual_guard_never_superseded()
    test_sched_job_never_superseded()
    test_watch_same_kind_only()
    test_guard_done_does_not_supersede_watch_done_branch()
    test_unparseable_id_never_superseded()
    test_non_slot_job_never_superseded()
    test_done_same_id_does_not_supersede_itself()
    test_done_newer_queued_older_ignored()
    test_mark_superseded_record_validates_and_gates()
    print(f"\n{PASSED} passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
