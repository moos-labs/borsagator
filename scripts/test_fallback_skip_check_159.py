#!/usr/bin/env python3
"""Unit tests for issue #159: fallback suppression is tied to
initiation/activity, not a successful sweep.

Before the fix, `should_skip()` in scripts/fallback_skip_check.py
suppressed the 06:45 UTC Actions fallback whenever ANY of these
held, with no outcome check at all:

(a) the archive signal was `day.is_dir() and any(day.iterdir())` --
    ANY non-empty archive dir for the date counted, including
    single-tool harvest/news runs, which land there every morning;
(b) the claim signal was existence-only -- a worker could claim
    `sched-<date>` and then fail or die, and the fallback still
    stood down. The claim proves ownership, not completion, and
    the check never looked at claim age or outcome.

The fix requires a VERIFIED sweep archive before suppressing on
archive activity (the `_is_sweep` identification ported from
digest_watch_check.py: a sweep dir needs a readable manifest whose
job starts with "sweep", or a dir name carrying the sweep slug),
and makes claim suppression lease/outcome-aware: a claim
suppresses only while its `at` timestamp is inside the refresh
lease (25 min -- the worker refreshes a running job's claim every
20 min, worker.py CLAIM_REFRESH_SECONDS), and a `queue/done/`
record (issue #149, written only after a successful publish)
suppresses outright. Anything unparseable or unreadable fails
OPEN: the fallback runs. A double sweep is visible and
recoverable; a skipped morning is silent.

Stdlib only, no network, no fixtures. Run:
    python3 scripts/test_fallback_skip_check_159.py
Exit 0 only when every test passes.
"""
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)

import fallback_skip_check as fsc  # noqa: E402

RESULTS = []
DATE = "2026-11-18"
JOB = "sweep-lite POUL.CA market=EGX"


def check(name, fn):
    try:
        fn()
    except Exception as e:
        RESULTS.append((name, False, f"{type(e).__name__}: {e}"))
        print(f"FAIL {name}: {type(e).__name__}: {e}")
        return
    RESULTS.append((name, True, ""))
    print(f"PASS {name}")


def _now_minus(minutes):
    return (datetime.now(timezone.utc)
            - timedelta(minutes=minutes)).isoformat()


def _claim(claims_dir, age_minutes=None, at=None, raw=None):
    """Write queue/claims/sched-<DATE>.json like worker.claim()."""
    d = Path(claims_dir)
    d.mkdir(parents=True, exist_ok=True)
    if raw is not None:
        (d / f"sched-{DATE}.json").write_text(raw)
        return
    stamp = at if at is not None else _now_minus(age_minutes)
    (d / f"sched-{DATE}.json").write_text(json.dumps(
        {"worker": "w5", "at": stamp, "job": JOB}))


def _done(done_dir):
    """Write queue/done/sched-<DATE>.json like worker._mark_done()."""
    d = Path(done_dir)
    d.mkdir(parents=True, exist_ok=True)
    (d / f"sched-{DATE}.json").write_text(json.dumps(
        {"worker": "w5", "at": _now_minus(5), "job": JOB,
         "archive": "deadbeef"}))


def _arch_sub(archive_dir, name, manifest="sweep"):
    """One subdir under worker-runs/<DATE>/.

    manifest="sweep" -> manifest job "sweep-lite ...";
    "harvest" -> job "harvest-egx ..."; "news" -> job "news ...";
    None -> no manifest.json; "corrupt" -> invalid JSON;
    "nondict" -> valid JSON, not an object; "nojob" -> manifest
    with no job key (identification falls back to the dir name).
    """
    sub = Path(archive_dir) / DATE / name
    sub.mkdir(parents=True, exist_ok=True)
    if manifest is None:
        return sub
    if manifest == "corrupt":
        (sub / "manifest.json").write_text("{not json")
        return sub
    if manifest == "nondict":
        (sub / "manifest.json").write_text(json.dumps(["sweep"]))
        return sub
    if manifest == "nojob":
        (sub / "manifest.json").write_text(json.dumps(
            {"worker": "w5", "tools": {"yahooquery-runner": "ok"}}))
        return sub
    job = {"sweep": JOB, "harvest": "harvest-egx POUL.CA",
           "news": "news-egx POUL.CA"}[manifest]
    (sub / "manifest.json").write_text(json.dumps(
        {"job": {"id": f"sched-{DATE}", "job": job},
         "worker": "w5", "tools": {"yahooquery-runner": "ok"}}))
    return sub


def test_harvest_only_archive_does_not_suppress():
    # (a) A harvest run archived this morning must NOT stand the
    # fallback down -- no sweep fired.
    with tempfile.TemporaryDirectory() as tmp:
        arch = Path(tmp) / "worker-runs"
        _arch_sub(arch, "083015__harvest-egx-poul-ca__auto-harvest-x",
                  "harvest")
        assert fsc.should_skip(DATE, None, arch) is False


def test_news_only_archive_does_not_suppress():
    with tempfile.TemporaryDirectory() as tmp:
        arch = Path(tmp) / "worker-runs"
        _arch_sub(arch, "083020__news-egx-poul-ca__auto-news-x", "news")
        assert fsc.should_skip(DATE, None, arch) is False


def test_sweep_archive_suppresses():
    # The proof bar's third leg: a genuinely archived sweep still
    # suppresses the fallback.
    with tempfile.TemporaryDirectory() as tmp:
        arch = Path(tmp) / "worker-runs"
        _arch_sub(arch, "061512__sweep-lite-poul-ca-market-egx__sched-x",
                  "sweep")
        assert fsc.should_skip(DATE, None, arch) is True


def test_sweep_archive_by_name_slug_suppresses():
    # Manifests predate / omit the job string: the dir name carries
    # the sweep slug (publish() slugs the job string into it).
    with tempfile.TemporaryDirectory() as tmp:
        arch = Path(tmp) / "worker-runs"
        _arch_sub(arch, "061512__sweep-lite-poul-ca-market-egx__sched-x",
                  "nojob")
        assert fsc.should_skip(DATE, None, arch) is True


def test_sweep_dir_without_manifest_does_not_suppress():
    # A sweep dir with no readable manifest is a partial publish
    # (digest_watch_check: "partial") -- not a success. Fail open.
    with tempfile.TemporaryDirectory() as tmp:
        arch = Path(tmp) / "worker-runs"
        _arch_sub(arch, "061512__sweep-lite-poul-ca-market-egx__sched-x",
                  None)
        assert fsc.should_skip(DATE, None, arch) is False


def test_sweep_dir_with_corrupt_manifest_does_not_suppress():
    with tempfile.TemporaryDirectory() as tmp:
        arch = Path(tmp) / "worker-runs"
        _arch_sub(arch, "061512__sweep-lite-poul-ca-market-egx__sched-x",
                  "corrupt")
        assert fsc.should_skip(DATE, None, arch) is False


def test_sweep_dir_with_nondict_manifest_does_not_suppress():
    with tempfile.TemporaryDirectory() as tmp:
        arch = Path(tmp) / "worker-runs"
        _arch_sub(arch, "061512__sweep-lite-poul-ca-market-egx__sched-x",
                  "nondict")
        assert fsc.should_skip(DATE, None, arch) is False


def test_fresh_claim_suppresses():
    # A claim refreshed 5 min ago: the worker is running the job
    # right now (execute() refreshes the claim every 20 min).
    with tempfile.TemporaryDirectory() as tmp:
        claims = Path(tmp) / "claims"
        _claim(claims, age_minutes=5)
        assert fsc.should_skip(DATE, claims, None) is True


def test_claim_inside_lease_suppresses():
    # 20 min old: one refresh interval in, still inside the 25-min
    # lease (a live job's bus-visible `at` is at most ~20 min old
    # at check time, plus checkout/push lag).
    with tempfile.TemporaryDirectory() as tmp:
        claims = Path(tmp) / "claims"
        _claim(claims, age_minutes=20)
        assert fsc.should_skip(DATE, claims, None) is True


def test_claim_past_lease_does_not_suppress():
    # (b) Claimed 30 min ago and never refreshed: the worker claimed
    # the sweep and died (or the job ended without publishing).
    # Winter case: fire 06:15 UTC, fallback check 06:45 UTC -- a
    # claim-and-die at fire time is 30 min old at the check.
    with tempfile.TemporaryDirectory() as tmp:
        claims = Path(tmp) / "claims"
        _claim(claims, age_minutes=30)
        assert fsc.should_skip(DATE, claims, None) is False


def test_claim_seven_hours_old_does_not_suppress():
    with tempfile.TemporaryDirectory() as tmp:
        claims = Path(tmp) / "claims"
        _claim(claims, age_minutes=7 * 60)
        assert fsc.should_skip(DATE, claims, None) is False


def test_claim_unparseable_at_does_not_suppress():
    # A claim whose timestamp cannot be read proves nothing about
    # liveness -- fail open.
    with tempfile.TemporaryDirectory() as tmp:
        claims = Path(tmp) / "claims"
        _claim(claims, raw=json.dumps(
            {"worker": "w5", "at": "not-a-timestamp", "job": JOB}))
        assert fsc.should_skip(DATE, claims, None) is False


def test_claim_missing_at_does_not_suppress():
    with tempfile.TemporaryDirectory() as tmp:
        claims = Path(tmp) / "claims"
        _claim(claims, raw=json.dumps({"worker": "w5", "job": JOB}))
        assert fsc.should_skip(DATE, claims, None) is False


def test_done_record_suppresses():
    # Outcome-proven completion (#149: done is written only after
    # a successful publish) suppresses outright -- no claim and no
    # archive needed.
    with tempfile.TemporaryDirectory() as tmp:
        done = Path(tmp) / "done"
        _done(done)
        assert fsc.should_skip(DATE, None, None, done_dir=done) is True


def test_done_record_suppresses_despite_stale_claim():
    # The done record is the outcome; a stale claim beside it is
    # just the leftover mutex, not a reason to run the fallback.
    with tempfile.TemporaryDirectory() as tmp:
        claims = Path(tmp) / "claims"
        _claim(claims, age_minutes=120)
        done = Path(tmp) / "done"
        _done(done)
        assert fsc.should_skip(DATE, claims, None,
                               done_dir=done) is True


def test_nothing_at_all_does_not_suppress():
    with tempfile.TemporaryDirectory() as tmp:
        claims = Path(tmp) / "claims"
        claims.mkdir()
        arch = Path(tmp) / "worker-runs"
        arch.mkdir()
        assert fsc.should_skip(DATE, claims, arch) is False


def test_empty_archive_day_dir_does_not_suppress():
    with tempfile.TemporaryDirectory() as tmp:
        arch = Path(tmp) / "worker-runs" / DATE
        arch.mkdir(parents=True)
        assert fsc.should_skip(DATE, None,
                               Path(tmp) / "worker-runs") is False


def test_fresh_claim_suppresses_despite_harvest_archive():
    # The harvest in the archive is not the sweep; the LIVE claim
    # is what suppresses here.
    with tempfile.TemporaryDirectory() as tmp:
        claims = Path(tmp) / "claims"
        _claim(claims, age_minutes=5)
        arch = Path(tmp) / "worker-runs"
        _arch_sub(arch, "083015__harvest-egx-poul-ca__auto-harvest-x",
                  "harvest")
        assert fsc.should_skip(DATE, claims, arch) is True


def test_stale_claim_plus_harvest_archive_does_not_suppress():
    # Neither signal is valid: a dead claim plus a harvest-only
    # archive is exactly the missed morning of the issue.
    with tempfile.TemporaryDirectory() as tmp:
        claims = Path(tmp) / "claims"
        _claim(claims, age_minutes=60)
        arch = Path(tmp) / "worker-runs"
        _arch_sub(arch, "083015__harvest-egx-poul-ca__auto-harvest-x",
                  "harvest")
        assert fsc.should_skip(DATE, claims, arch) is False


def test_cli_harvest_false_sweep_true_bad_date():
    # The exact workflow invocation shape (minus --done-dir, which
    # is optional): harvest-only prints "false", a sweep "true".
    script = os.path.join(SCRIPTS, "fallback_skip_check.py")
    with tempfile.TemporaryDirectory() as tmp:
        arch = Path(tmp) / "worker-runs"
        _arch_sub(arch, "083015__harvest-egx-poul-ca__auto-harvest-x",
                  "harvest")
        r = subprocess.run(
            [sys.executable, script, "--date", DATE,
             "--archive-dir", str(arch)],
            capture_output=True, text=True, timeout=60)
        assert r.returncode == 0, r.stderr
        assert r.stdout.strip() == "false", r.stdout
        _arch_sub(arch, "061512__sweep-lite-poul-ca-market-egx__sched-x",
                  "sweep")
        r = subprocess.run(
            [sys.executable, script, "--date", DATE,
             "--archive-dir", str(arch)],
            capture_output=True, text=True, timeout=60)
        assert r.returncode == 0, r.stderr
        assert r.stdout.strip() == "true", r.stdout
        r = subprocess.run(
            [sys.executable, script, "--date", "18-11-2026",
             "--archive-dir", str(arch)],
            capture_output=True, text=True, timeout=60)
        assert r.returncode == 2, r.returncode


TESTS = [
    ("T1 harvest-only archive does not suppress",
     test_harvest_only_archive_does_not_suppress),
    ("T2 news-only archive does not suppress",
     test_news_only_archive_does_not_suppress),
    ("T3 sweep archive suppresses", test_sweep_archive_suppresses),
    ("T4 sweep archive by name slug suppresses",
     test_sweep_archive_by_name_slug_suppresses),
    ("T5 sweep dir without manifest does not suppress",
     test_sweep_dir_without_manifest_does_not_suppress),
    ("T6 sweep dir with corrupt manifest does not suppress",
     test_sweep_dir_with_corrupt_manifest_does_not_suppress),
    ("T7 sweep dir with non-dict manifest does not suppress",
     test_sweep_dir_with_nondict_manifest_does_not_suppress),
    ("T8 fresh claim suppresses", test_fresh_claim_suppresses),
    ("T9 claim inside lease suppresses",
     test_claim_inside_lease_suppresses),
    ("T10 claim past lease does not suppress",
     test_claim_past_lease_does_not_suppress),
    ("T11 claim 7h old does not suppress",
     test_claim_seven_hours_old_does_not_suppress),
    ("T12 claim unparseable at does not suppress",
     test_claim_unparseable_at_does_not_suppress),
    ("T13 claim missing at does not suppress",
     test_claim_missing_at_does_not_suppress),
    ("T14 done record suppresses", test_done_record_suppresses),
    ("T15 done record suppresses despite stale claim",
     test_done_record_suppresses_despite_stale_claim),
    ("T16 nothing at all does not suppress",
     test_nothing_at_all_does_not_suppress),
    ("T17 empty archive day dir does not suppress",
     test_empty_archive_day_dir_does_not_suppress),
    ("T18 fresh claim suppresses despite harvest archive",
     test_fresh_claim_suppresses_despite_harvest_archive),
    ("T19 stale claim + harvest archive does not suppress",
     test_stale_claim_plus_harvest_archive_does_not_suppress),
    ("T20 CLI harvest false / sweep true / bad date",
     test_cli_harvest_false_sweep_true_bad_date),
]


def main():
    for name, fn in TESTS:
        check(name, fn)
    failed = [r for r in RESULTS if not r[1]]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} pass")
    if failed:
        print("failed:", ", ".join(r[0] for r in failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
