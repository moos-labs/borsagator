#!/usr/bin/env python3
"""Blob-parity check for the two-path promotion gap (issue #232).

Main, worker-release and archive each carry a copy of the digest
helper and can drift silently (#219 reached Released without the
verified label; the board-sync gate reopened it). This check fails
when the helper BLOB - not the ref - differs across the compared
refs. Blob comparison is the right scope: the archive branch takes
ordinary worker data commits from orchestrate.yml on top of deploy
commits, so its tip SHA legitimately differs from main even when the
helper content is identical.

Default refs are origin/main and origin/archive. worker-release is
deliberately NOT a default: the frozen-candidate process
(docs/promotion.md) lets worker-release lag main between reviewed
promotions, so comparing it here would be red most of the time for
legitimate reasons. That is a SCOPE choice, not a dropped concern:
pass it explicitly to assert all three paths when a promotion is
expected to have completed:

    python3 scripts/check_helper_blob_parity.py --repo-dir . \
        --refs origin/main origin/worker-release origin/archive

A red result means one of two things, and the output cannot tell
them apart by itself: a helper change on main is pending its guarded
deploy (expected between a helper-landing merge and the next
deploy_archive.py run), or the archive helper was edited outside the
deploy path (never legitimate). The deploy-guard workflow runs this
on pushes to main and archive and hourly; red until the first
guarded deploy after a helper change is the intended alarm, paired
with the board-sync gate that blocks Released without verified.

Stdlib only; requires git on PATH and the refs fetched locally.
Exit 0 when all blobs match, 1 on drift or a missing blob, 2 on
usage error.

Usage:
  python3 scripts/check_helper_blob_parity.py --repo-dir . \
      [--path scripts/worker_digest_issue.py] \
      [--refs origin/main origin/archive]
"""
import argparse
import subprocess
import sys

DEFAULT_PATH = "scripts/worker_digest_issue.py"
DEFAULT_REFS = ["origin/main", "origin/archive"]


def blob_of(repo, ref, path):
    """Blob SHA of path at ref, or None when ref or path is absent."""
    p = subprocess.run(
        ["git", "-C", repo, "rev-parse", "--verify", "--quiet",
         f"{ref}:{path}"], capture_output=True, text=True)
    out = p.stdout.strip()
    return out if p.returncode == 0 and out else None


def parity(repo, refs, path):
    """Map each ref to its helper blob SHA (None when absent)."""
    return {r: blob_of(repo, r, path) for r in refs}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo-dir", default=".")
    ap.add_argument("--path", default=DEFAULT_PATH)
    ap.add_argument("--refs", nargs="+", default=DEFAULT_REFS)
    a = ap.parse_args(argv)
    if len(a.refs) < 2:
        print("parity needs at least two refs", file=sys.stderr)
        return 2
    blobs = parity(a.repo_dir, a.refs, a.path)
    for r in a.refs:
        print(f"{r} {blobs[r] or 'MISSING'}")
    base = blobs[a.refs[0]]
    drift = [r for r in a.refs if blobs[r] != base]
    if base is None or drift:
        detail = "; ".join(
            f"{r} has {blobs[r] or 'MISSING'}"
            for r in [a.refs[0]] + drift)
        print(f"PARITY FAIL: {a.path} blob differs or is missing: "
              f"{detail}. Either a guarded deploy of the helper is "
              f"pending, or the archive helper was edited outside "
              f"scripts/deploy_archive.py. Run the deploy or "
              f"investigate before any release.", file=sys.stderr)
        return 1
    print(f"PARITY OK: {a.path} identical across "
          f"{', '.join(a.refs)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
