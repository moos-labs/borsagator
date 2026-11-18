#!/usr/bin/env python3
"""Issue #66: Actions-fallback skip-check for the scheduled sweep.

The worker owns the 08:15 Cairo trigger; the Actions cron at 06:45 UTC
is only a fallback. This script decides whether a scheduled fallback
run must stand down. Issue #159: suppression is tied to a VERIFIED
successful sweep, never to initiation or mere activity.

Three signals, in order -- the first that proves the sweep fired
ends the check:

1. Done record (`queue/done/sched-<date>.json` on the `queue`
   branch, `--done-dir`): written by the worker only after a
   successful publish (issue #149). Outcome-proven completion.
2. Verified sweep archive (`worker-runs/<date>/` on the `archive`
   branch, `--archive-dir`): a subdir counts only when it is a
   sweep -- a readable manifest.json whose job starts with
   "sweep", or a dir name carrying the sweep slug. Harvests and
   single-tool runs land in the same day dir every morning, so a
   manifest alone, or any non-empty dir, never proves the sweep
   fired. A sweep dir with no readable manifest is a partial
   publish, not a success.
3. Live claim (`queue/claims/sched-<date>.json`, `--claims-dir`):
   the worker refreshes a running job's claim timestamp every 20
   min (worker.py CLAIM_REFRESH_SECONDS), so a claim suppresses
   only while its `at` is inside the 25-min lease -- the job is
   plausibly still running. A claim older than the lease, or one
   whose timestamp cannot be read, proves ownership, not
   completion: the worker may have claimed and then failed or
   died. It does not suppress.

Usage:
    fallback_skip_check.py --date YYYY-MM-DD
        [--claims-dir DIR] [--archive-dir DIR] [--done-dir DIR]

Prints `true` or `false` on stdout (the value for the workflow's
`skip` output) and an explanation on stderr. Exit code is always 0:
an unreadable or missing input means "do not skip" -- the fallback
exists precisely for worker-down mornings, so a check that cannot
see the bus must let the sweep run. A double sweep in that corner is
visible and recoverable; a skipped morning is silent.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Issue #159: a claim suppresses only while the job is plausibly
# still running. The worker refreshes a running job's claim every
# 20 min (worker.py CLAIM_REFRESH_SECONDS = 1200); a live job's
# bus-visible `at` is therefore at most ~20 min old at check time,
# plus bus-push / branch-checkout / clock lag. 25 min catches a
# claim-and-die at least 25 min before the check -- including the
# winter case (worker fires 08:15 Cairo = 06:15 UTC, fallback
# checks 06:45 UTC: a claim-and-die at fire time is 30 min old).
# A worker that died within the last 25 min before the check is
# indistinguishable from a live one at this refresh cadence; that
# is the residual window, not a silent skip -- the next morning's
# digest watch still reports the sweep missing.
CLAIM_LEASE_SECONDS = 1500  # 25 min


def _is_sweep(sub, manifest):
    """True when an archive dir is a sweep, not a single-tool run.

    Ported from digest_watch_check._is_sweep -- keep the two in
    sync. The worker archives every job under worker-runs/<date>/;
    harvests and single-tool runs land there every morning, so a
    manifest alone never proves the sweep fired. A dir counts as
    the sweep when its manifest's job string starts with "sweep",
    or (the manifest predates / omits the job string) when the dir
    name carries the sweep slug -- publish() slugs the job string
    into the dir name, so "sweep-lite ..." becomes
    "...__sweep-lite-...__...".
    """
    job = manifest.get("job") if isinstance(manifest, dict) else None
    job_str = job.get("job") if isinstance(job, dict) else None
    if isinstance(job_str, str) and job_str.startswith("sweep"):
        return True
    return "sweep" in sub.name


def _claim_age_seconds(claim):
    """Age of a claim file's `at` timestamp, in seconds.

    Returns None when the file cannot be read, is not JSON, or
    carries no parseable timestamp -- such a claim proves nothing
    about liveness, so the caller must not suppress on it. A
    future timestamp (worker clock ahead) counts as age 0.
    """
    try:
        data = json.loads(claim.read_text())
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    stamp = data.get("at")
    if not isinstance(stamp, str):
        return None
    try:
        at = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError:
        return None
    if at.tzinfo is None:
        at = at.replace(tzinfo=timezone.utc)
    age = (datetime.now(timezone.utc) - at).total_seconds()
    return max(age, 0.0)


def _has_verified_sweep_archive(archive_dir, date):
    """True when worker-runs/<date>/ holds a verified sweep dir."""
    day = Path(archive_dir) / date
    try:
        subdirs = [d for d in day.iterdir() if d.is_dir()] \
            if day.is_dir() else []
    except OSError as e:
        print(f"skip-check: cannot read archive dir: {e}; not skipping",
              file=sys.stderr)
        return False
    for sub in subdirs:
        manifest = sub / "manifest.json"
        try:
            data = json.loads(manifest.read_text()) \
                if manifest.is_file() else None
            if not isinstance(data, dict):
                data = None  # missing/corrupt/non-object: not verified
        except (OSError, ValueError):
            data = None
        if isinstance(data, dict) and _is_sweep(sub, data):
            print(f"skip: verified sweep archive {sub} "
                  f"(manifest job is a sweep)", file=sys.stderr)
            return True
    return False


def should_skip(date, claims_dir=None, archive_dir=None, done_dir=None):
    """True when the worker already fired a verified sweep for `date`
    (YYYY-MM-DD), or is provably still running one."""
    if done_dir is not None:
        # Issue #149: the done record exists only after a
        # successful publish -- outcome-proven completion.
        done = Path(done_dir) / f"sched-{date}.json"
        try:
            if done.is_file():
                print(f"skip: done record {done} exists (worker sweep "
                      f"published)", file=sys.stderr)
                return True
        except OSError as e:
            print(f"skip-check: cannot read done dir: {e}; not skipping",
                  file=sys.stderr)
    if archive_dir is not None:
        if _has_verified_sweep_archive(archive_dir, date):
            return True
    if claims_dir is not None:
        claim = Path(claims_dir) / f"sched-{date}.json"
        try:
            age = _claim_age_seconds(claim)
        except OSError as e:
            print(f"skip-check: cannot read claims dir: {e}; not skipping",
                  file=sys.stderr)
            age = None
        if age is not None:
            if age <= CLAIM_LEASE_SECONDS:
                print(f"skip: claim {claim} is live "
                      f"({age:.0f}s old, lease "
                      f"{CLAIM_LEASE_SECONDS}s) -- worker running",
                      file=sys.stderr)
                return True
            print(f"skip-check: claim {claim} is stale ({age:.0f}s old, "
                  f"lease {CLAIM_LEASE_SECONDS}s) -- claimed and died, "
                  f"or ended without publishing; fallback runs",
                  file=sys.stderr)
        else:
            print(f"skip-check: claim {claim} has no readable "
                  f"timestamp; not suppressing on it", file=sys.stderr)
    print("skip-check: no done record, no verified sweep archive, and "
          "no live claim for today; fallback runs", file=sys.stderr)
    return False


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Decide whether the Actions fallback sweep must "
                    "stand down (worker already fired today).")
    ap.add_argument("--date", required=True,
                    help="Cairo date YYYY-MM-DD to check")
    ap.add_argument("--claims-dir",
                    help="queue/claims dir from the queue branch")
    ap.add_argument("--archive-dir",
                    help="worker-runs dir from the archive branch")
    ap.add_argument("--done-dir",
                    help="queue/done dir from the queue branch "
                         "(issue #149 outcome records)")
    args = ap.parse_args(argv)
    date = args.date
    parts = date.split("-")
    if len(parts) != 3 or not all(p.isdigit() for p in parts) \
            or len(parts[0]) != 4 or len(parts[1]) != 2 \
            or len(parts[2]) != 2:
        print(f"bad --date {date!r}: want YYYY-MM-DD", file=sys.stderr)
        return 2
    print("true" if should_skip(date, args.claims_dir,
                                args.archive_dir, args.done_dir)
          else "false")
    return 0


if __name__ == "__main__":
    sys.exit(main())
