#!/usr/bin/env python3
"""Issue #66: Actions-fallback skip-check for the scheduled sweep.

The worker owns the 08:15 Cairo trigger; the Actions cron at 06:45 UTC
is only a fallback. This script decides whether a scheduled fallback
run must stand down: skip when today's `sched-<date>` job was already
claimed by the worker (queue/claims/sched-<date>.json on the `queue`
branch) or when today's worker sweep already archived
(worker-runs/<date>/ on the `archive` branch). The claim is the single
mutex; the archive dir is the belt-and-braces signal for a claim that
was reclaimed after its publish.

Usage:
    fallback_skip_check.py --date YYYY-MM-DD
        [--claims-dir DIR] [--archive-dir DIR]

Prints `true` or `false` on stdout (the value for the workflow's
`skip` output) and an explanation on stderr. Exit code is always 0:
an unreadable or missing input means "do not skip" — the fallback
exists precisely for worker-down mornings, so a check that cannot
see the bus must let the sweep run. A double sweep in that corner is
visible and recoverable; a skipped morning is silent.
"""
import argparse
import sys
from pathlib import Path


def should_skip(date, claims_dir=None, archive_dir=None):
    """True when the worker already fired for `date` (YYYY-MM-DD)."""
    if claims_dir is not None:
        claim = Path(claims_dir) / f"sched-{date}.json"
        try:
            if claim.is_file():
                print(f"skip: claim {claim} exists (worker fired)",
                      file=sys.stderr)
                return True
        except OSError as e:
            print(f"skip-check: cannot read claims dir: {e}; not skipping",
                  file=sys.stderr)
    if archive_dir is not None:
        day = Path(archive_dir) / date
        try:
            if day.is_dir() and any(day.iterdir()):
                print(f"skip: archive {day} is non-empty (worker sweep "
                      f"archived)", file=sys.stderr)
                return True
        except OSError as e:
            print(f"skip-check: cannot read archive dir: {e}; not skipping",
                  file=sys.stderr)
    print("skip-check: no claim and no archive for today; fallback runs",
          file=sys.stderr)
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
    args = ap.parse_args(argv)
    date = args.date
    parts = date.split("-")
    if len(parts) != 3 or not all(p.isdigit() for p in parts) \
            or len(parts[0]) != 4 or len(parts[1]) != 2 \
            or len(parts[2]) != 2:
        print(f"bad --date {date!r}: want YYYY-MM-DD", file=sys.stderr)
        return 2
    print("true" if should_skip(date, args.claims_dir,
                                args.archive_dir) else "false")
    return 0


if __name__ == "__main__":
    sys.exit(main())
