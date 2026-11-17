#!/usr/bin/env python3
"""Split-merge digest-issue helper (#67 §4d, route 1).

The worker archives a merged sweep; this script (run by the
worker-digest-issue workflow on `archive`-branch pushes) lists the
merged sweep dirs added by a push, so the workflow can open one
digest issue per merged sweep with the workflow token — the same
credential and the same #113/#120 title/status handling as the
Actions issue step in orchestrate.yml. The worker PAT is never
widened to issues:write (a Muhammad decision, not decided here).

A sweep dir qualifies ONLY when it carries merge-manifest.json —
an archive push for a raw worker-run must never open an issue.
Idempotency is the workflow's job: it checks for an existing issue
with the same title before creating one (claim id + sweep dir are
the identity).

Usage:
    worker_digest_issue.py --before <sha> --after <sha>
        --repo-dir <archive-branch checkout>
Stdout is one line per newly added merged sweep:
    <sweep_dir>\t<title>
Exit 0 always (a listing failure prints nothing, never fails the
workflow step that consumes it — the workflow treats an empty
listing as "nothing to file").
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path


def digest_title_status(text, fallback_job=""):
    """(title, status) from a digest.md text, mirroring the
    orchestrate.yml issue step: title is the first line (headerless
    digests fall back to the job); a running/failed marker appends
    the FAILED flag to the title."""
    lines = (text or "").splitlines()
    title = lines[0].strip() if lines and lines[0].strip() else ""
    if not title:
        job = fallback_job or "unknown job"
        title = f"# 🐊 Borsagator digest — {job}"
    m = re.search(r"borsagator-digest-status: (\w+)", text or "")
    status = m.group(1) if m else None
    if status in ("running", "failed"):
        title = title + " — ⚠️ FAILED"
    return title, status


def added_merge_manifests(before, after, repo_dir):
    """Sweep dirs whose merge-manifest.json was ADDED between
    `before` and `after` (git diff --name-only). A zero `before`
    (first push / rewritten history) lists every merge-manifest at
    `after` instead. Returns sorted sweep-dir paths, archive
    relative (sweeps/<date>/<dir>)."""
    repo_dir = Path(repo_dir)
    if not before or before.startswith("0000"):
        proc = subprocess.run(
            ["git", "-C", str(repo_dir), "ls-tree", "-r", "--name-only",
             after],
            capture_output=True, text=True, timeout=120)
        names = proc.stdout.splitlines() if proc.returncode == 0 \
            else []
    else:
        proc = subprocess.run(
            ["git", "-C", str(repo_dir), "diff", "--name-only",
             "--diff-filter=A", before, after],
            capture_output=True, text=True, timeout=120)
        names = proc.stdout.splitlines() if proc.returncode == 0 \
            else []
    dirs = set()
    for name in names:
        parts = name.split("/")
        if len(parts) >= 3 and parts[0] == "sweeps" and \
                parts[-1] == "merge-manifest.json":
            dirs.add("/".join(parts[:-1]))
    return sorted(dirs)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="List merged sweeps added by an archive push.")
    ap.add_argument("--before", required=True)
    ap.add_argument("--after", required=True)
    ap.add_argument("--repo-dir", required=True)
    args = ap.parse_args(argv)
    try:
        for sweep_dir in added_merge_manifests(args.before, args.after,
                                               args.repo_dir):
            md = Path(args.repo_dir) / sweep_dir / "digest.md"
            try:
                text = md.read_text(encoding="utf-8")
            except OSError:
                text = ""
            title, _status = digest_title_status(text)
            print(f"{sweep_dir}\t{title}")
    except Exception as e:  # noqa: BLE001 - never fail the workflow
        print(f"worker_digest_issue: {type(e).__name__}: {e}",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
