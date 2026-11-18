#!/usr/bin/env python3
"""Proof harness for issue #154 (panel round 12, F10):
``resolve_pair`` in scripts/delta.py picked the wrong predecessor
two ways:

(a) ``sort(key=lambda c: (c[0] is None, c[0]))`` sorted
    ``finished=None`` LAST, so an undated sweep became the "most
    recent" baseline;
(b) sweeps are enumerated before worker-runs, and with equal
    ``finished`` timestamps stable sort left the merged worker
    sweep's manifest-only raw twin as ``candidates[-1]`` -- so the
    function returned ``delta_unavailable`` despite an available
    merged ensemble.

The fix sorts None-finished as oldest and deduplicates a merged
sweep with its raw twin (same execution: the merged manifest's
``source_runs`` names the twin, and both carry the same claim id
and the same finished timestamp), preferring the merged
representation. An unmerged worker run, and a same-claim re-run
at a different finished time, are different executions and are
kept.

Fixtures are synthetic archive trees (sweeps/ + worker-runs/
dirs with minimal digest/ensemble/manifest JSON) -- no real
archive checkout is needed. The harness discriminates: on
unmodified main T1, T2 and T4 FAIL (T1 picks the undated sweep,
T2/T4 report delta_unavailable); T3, T5, T6, T7, T8 pass there
too and lock the surrounding behaviour.

Usage: python3 scripts/test_delta154.py
Exit 0 only when every test passes.
"""
import json
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)

import delta

RESULTS = []
JOB = "sweep-lite POUL.CA"
TICKER = "POUL.CA"
SHAPE = "sweep-lite POUL.CA"
CLAIM = "sched-2026-11-16"
TWIN_REL = "worker-runs/2026-11-16/080000__sweep-lite-poul-ca__sched-2026-11-16"


def check(name, fn):
    try:
        fn()
    except Exception as e:
        RESULTS.append((name, False, f"{type(e).__name__}: {e}"))
        print(f"FAIL {name}: {type(e).__name__}: {e}")
        return
    RESULTS.append((name, True, ""))
    print(f"PASS {name}")


def _write(path, doc):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f)


def make_sweep(root, rel, finished, with_ensemble=True, manifest=None,
               date="2026-11-16"):
    """A sweeps/ dir: digest.json (+ ensemble.json) and, when given,
    manifest.json. finished=None writes a digest with no finished
    key (undated sweep)."""
    path = os.path.join(root, rel)
    digest = {"job": JOB, "ticker": TICKER, "date": date, "results": []}
    if finished is not None:
        digest["finished"] = finished
    _write(os.path.join(path, "digest.json"), digest)
    if with_ensemble:
        _write(os.path.join(path, "ensemble.json"),
               {"ticker": TICKER, "base_price": 10.0,
                "base_date": "2026-11-16", "horizons": {},
                "applied_weights": {}, "corporate_actions": [],
                "risk": {}})
    if manifest is not None:
        _write(os.path.join(path, "manifest.json"), manifest)
    return path


def make_worker_run(root, rel, job_id, finished):
    """A worker-runs/ dir: manifest.json only (no digest, no
    ensemble), exactly as the worker publishes it."""
    path = os.path.join(root, rel)
    _write(os.path.join(path, "manifest.json"),
           {"job": {"id": job_id, "job": JOB, "added": finished},
            "worker": "test-worker", "started": finished,
            "finished": finished, "tools": {}})
    return path


def make_current(root):
    return make_sweep(root, "sweeps/2026-11-17/080000__sweep-lite-poul-ca__run999",
                      "2026-11-17T08:00:00+00:00", date="2026-11-17")


def merged_manifest(source_runs=True):
    doc = {"job": JOB, "job_shape": JOB, "ticker": TICKER,
           "claim_id": CLAIM, "run_id": CLAIM, "merged_by": "worker"}
    if source_runs:
        doc["source_runs"] = [TWIN_REL]
    return doc


def test_t1_undated_never_wins():
    tmp = tempfile.mkdtemp(prefix="d154-t1-")
    try:
        dated = make_sweep(
            tmp, "sweeps/2026-11-16/080000__sweep-lite-poul-ca__run111",
            "2026-11-16T08:00:00+00:00")
        undated = make_sweep(
            tmp, "sweeps/2026-11-16/120000__sweep-lite-poul-ca__run222",
            None)
        cur = make_current(tmp)
        previous, status, note = delta.resolve_pair(
            tmp, TICKER, SHAPE, cur)
        assert status == "paired", f"{status}: {note}"
        assert previous is not None
        assert os.path.basename(previous).startswith("080000"), \
            f"undated sweep won as baseline: {previous}"
        assert os.path.normpath(previous) == os.path.normpath(dated), \
            previous
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_t2_merged_twin_preferred():
    tmp = tempfile.mkdtemp(prefix="d154-t2-")
    try:
        merged = make_sweep(
            tmp, "sweeps/2026-11-16/080000__sweep-lite-poul-ca__runsched-2026-11-16",
            "2026-11-16T08:00:00+00:00",
            manifest=merged_manifest(source_runs=True))
        make_worker_run(tmp, TWIN_REL, CLAIM,
                        "2026-11-16T08:00:00+00:00")
        cur = make_current(tmp)
        previous, status, note = delta.resolve_pair(
            tmp, TICKER, SHAPE, cur)
        assert status == "paired", f"{status}: {note}"
        assert previous is not None
        assert os.path.normpath(previous) == os.path.normpath(merged), \
            f"raw twin shadowed the merged sweep: {previous} ({note})"
        assert "preferred over its manifest-only worker-run twin" in note, \
            note
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_t3_unmerged_worker_run_still_unavailable():
    # Harness #70 section 5, re-locked: a worker run with NO merged
    # twin is still the latest sweep and still means
    # delta_unavailable -- the dedup must not swallow it.
    tmp = tempfile.mkdtemp(prefix="d154-t3-")
    try:
        make_worker_run(tmp, TWIN_REL, CLAIM,
                        "2026-11-16T08:00:00+00:00")
        cur = make_current(tmp)
        previous, status, note = delta.resolve_pair(
            tmp, TICKER, SHAPE, cur)
        assert status == "delta_unavailable", f"{status}: {note}"
        assert previous is None
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_t4_twin_dedup_without_source_runs():
    # Same as T2, but the merged manifest carries no source_runs:
    # the claim-id + equal-finished fallback must still dedup.
    tmp = tempfile.mkdtemp(prefix="d154-t4-")
    try:
        merged = make_sweep(
            tmp, "sweeps/2026-11-16/080000__sweep-lite-poul-ca__runsched-2026-11-16",
            "2026-11-16T08:00:00+00:00",
            manifest=merged_manifest(source_runs=False))
        make_worker_run(tmp, TWIN_REL, CLAIM,
                        "2026-11-16T08:00:00+00:00")
        cur = make_current(tmp)
        previous, status, note = delta.resolve_pair(
            tmp, TICKER, SHAPE, cur)
        assert status == "paired", f"{status}: {note}"
        assert previous is not None
        assert os.path.normpath(previous) == os.path.normpath(merged), \
            f"raw twin shadowed the merged sweep: {previous} ({note})"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_t5_first_sweep():
    tmp = tempfile.mkdtemp(prefix="d154-t5-")
    try:
        cur = make_current(tmp)
        previous, status, note = delta.resolve_pair(
            tmp, TICKER, SHAPE, cur)
        assert status == "first_sweep", f"{status}: {note}"
        assert previous is None
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_t6_later_dated_sweep_wins():
    tmp = tempfile.mkdtemp(prefix="d154-t6-")
    try:
        make_sweep(tmp, "sweeps/2026-11-15/080000__sweep-lite-poul-ca__run111",
                   "2026-11-15T08:00:00+00:00", date="2026-11-15")
        later = make_sweep(
            tmp, "sweeps/2026-11-16/080000__sweep-lite-poul-ca__run222",
            "2026-11-16T08:00:00+00:00")
        cur = make_current(tmp)
        previous, status, note = delta.resolve_pair(
            tmp, TICKER, SHAPE, cur)
        assert status == "paired", f"{status}: {note}"
        assert os.path.normpath(previous) == os.path.normpath(later), \
            previous
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_t7_undated_only_candidate_still_pairs():
    # Sorting None as oldest does not exclude undated sweeps: when
    # it is the ONLY previous sweep it still pairs (there is
    # nothing better); it just never outranks a dated one.
    tmp = tempfile.mkdtemp(prefix="d154-t7-")
    try:
        only = make_sweep(
            tmp, "sweeps/2026-11-16/120000__sweep-lite-poul-ca__run222",
            None)
        cur = make_current(tmp)
        previous, status, note = delta.resolve_pair(
            tmp, TICKER, SHAPE, cur)
        assert status == "paired", f"{status}: {note}"
        assert os.path.normpath(previous) == os.path.normpath(only), \
            previous
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_t8_same_claim_rerun_at_later_time_kept():
    # A same-claim worker run at a LATER finished time is a
    # different execution, not the merged sweep's twin: it is kept,
    # and as the latest sweep it still means delta_unavailable.
    tmp = tempfile.mkdtemp(prefix="d154-t8-")
    try:
        make_sweep(
            tmp, "sweeps/2026-11-16/080000__sweep-lite-poul-ca__runsched-2026-11-16",
            "2026-11-16T08:00:00+00:00",
            manifest=merged_manifest(source_runs=True))
        make_worker_run(
            tmp, "worker-runs/2026-11-16/090000__sweep-lite-poul-ca__sched-2026-11-16",
            CLAIM, "2026-11-16T09:00:00+00:00")
        cur = make_sweep(
            tmp, "sweeps/2026-11-17/100000__sweep-lite-poul-ca__run999",
            "2026-11-17T10:00:00+00:00", date="2026-11-17")
        previous, status, note = delta.resolve_pair(
            tmp, TICKER, SHAPE, cur)
        assert status == "delta_unavailable", f"{status}: {note}"
        assert previous is None
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    for name, fn in [
        ("T1 undated sweep never wins as baseline",
         test_t1_undated_never_wins),
        ("T2 merged sweep preferred over raw twin (source_runs)",
         test_t2_merged_twin_preferred),
        ("T3 unmerged worker run still delta_unavailable",
         test_t3_unmerged_worker_run_still_unavailable),
        ("T4 twin dedup via claim id without source_runs",
         test_t4_twin_dedup_without_source_runs),
        ("T5 first sweep", test_t5_first_sweep),
        ("T6 later dated sweep wins",
         test_t6_later_dated_sweep_wins),
        ("T7 undated-only candidate still pairs",
         test_t7_undated_only_candidate_still_pairs),
        ("T8 same-claim re-run at later time kept",
         test_t8_same_claim_rerun_at_later_time_kept),
    ]:
        check(name, fn)
    failed = [r for r in RESULTS if not r[1]]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} passed")
    if failed:
        for name, _ok, detail in failed:
            print(f"  FAILED: {name}: {detail}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
