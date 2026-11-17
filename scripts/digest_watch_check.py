#!/usr/bin/env python3
"""Issue #66: digest-watch check for worker sweeps.

The 08:55 digest watch used to look only for digest issues; worker
sweeps produce none until #67, so the unadapted watch cannot tell a
worker success from a worker miss. This script checks the `archive`
branch for today's worker sweep instead — worker-runs/<date>/ must
hold a sweep dir with a manifest.json — and optionally the `queue`
branch claim, to distinguish "claimed but not yet archived" (still
running) from "never fired".

Usage:
    digest_watch_check.py --date YYYY-MM-DD --archive-dir DIR
        [--claims-dir DIR]

Exit codes: 0 = archived (manifest present); 1 = missing, partial,
or still running (see the status line); 2 = usage error.
Stdout is one machine-readable line:
    status=archived tools=<n> dir=<name>
    status=running claim=sched-<date>      (trigger confirmed, no archive yet)
    status=partial dir=<name>              (dir present, manifest missing/unreadable)
    status=missing                         (no claim, no archive — page)
A `running` result means re-check later, not a page: a sequential
worker sweep is still running at 08:55. A `missing` result is the
missed-morning signal.

Only a sweep counts as archived: worker-runs/<date>/ also holds
single-tool runs (harvests, news) every morning, so a dir counts
only when its manifest's job starts with "sweep" or its name
carries the sweep slug (publish() slugs the job string into the
dir name). A non-sweep dir never produces `archived` or `partial`.
"""
import argparse
import json
import sys
from pathlib import Path


def _is_sweep(sub, manifest):
    """True when an archive dir is a sweep, not a single-tool run.

    The worker archives every job under worker-runs/<date>/ —
    harvests and single-tool runs land there every morning, so a
    manifest alone never proves the sweep fired. A dir counts as
    the sweep when its manifest's job string starts with "sweep",
    or (the manifest predates / omits the job string) when the dir
    name carries the sweep slug — publish() slugs the job string
    into the dir name, so "sweep-lite ..." becomes
    "...__sweep-lite-...__...".
    """
    job = manifest.get("job") if isinstance(manifest, dict) else None
    job_str = job.get("job") if isinstance(job, dict) else None
    if isinstance(job_str, str) and job_str.startswith("sweep"):
        return True
    return "sweep" in sub.name


def check(date, archive_dir, claims_dir=None):
    """Return (exit_code, status_line) for one Cairo date."""
    day = Path(archive_dir) / date
    try:
        subdirs = sorted(d for d in day.iterdir() if d.is_dir()) \
            if day.is_dir() else []
    except OSError:
        subdirs = []
    partial = None
    for sub in subdirs:
        manifest = sub / "manifest.json"
        try:
            data = json.loads(manifest.read_text()) \
                if manifest.is_file() else None
            if not isinstance(data, dict):
                data = None  # a non-object manifest is corrupt
        except (OSError, ValueError):
            data = None
        if isinstance(data, dict):
            if _is_sweep(sub, data):
                tools = data.get("tools", {})
                n = len(tools) if isinstance(tools, dict) else 0
                return 0, (f"status=archived tools={n} dir={sub.name}")
        elif partial is None and "sweep" in sub.name:
            # A sweep dir with no readable manifest: the publish
            # never completed (or landed corrupt) — not a miss, but
            # not a success either; a human looks. A non-sweep dir
            # without a manifest is not the sweep's problem.
            partial = sub.name
    if partial is not None:
        return 1, f"status=partial dir={partial}"
    if claims_dir is not None:
        claim = Path(claims_dir) / f"sched-{date}.json"
        try:
            if claim.is_file():
                return 1, f"status=running claim=sched-{date}"
        except OSError:
            pass
    return 1, "status=missing"


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Check the archive branch for today's worker sweep.")
    ap.add_argument("--date", required=True,
                    help="Cairo date YYYY-MM-DD to check")
    ap.add_argument("--archive-dir", required=True,
                    help="worker-runs dir from the archive branch")
    ap.add_argument("--claims-dir",
                    help="queue/claims dir from the queue branch")
    args = ap.parse_args(argv)
    date = args.date
    parts = date.split("-")
    if len(parts) != 3 or not all(p.isdigit() for p in parts) \
            or len(parts[0]) != 4 or len(parts[1]) != 2 \
            or len(parts[2]) != 2:
        print(f"bad --date {date!r}: want YYYY-MM-DD", file=sys.stderr)
        return 2
    code, line = check(date, args.archive_dir, args.claims_dir)
    print(line)
    return code


if __name__ == "__main__":
    sys.exit(main())
