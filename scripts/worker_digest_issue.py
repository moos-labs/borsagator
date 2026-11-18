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

Idempotency (#157): the sweep DIR is the identity, not the title —
titles are `# 🐊 Borsagator digest — {job}` and repeat for every
sweep of a job, so title matching both re-files closed sweeps and
false-skips live ones. Each sweep gets a unique identity label
``digest-<sha256(sweep_dir)[:16]>`` (a hash, because a raw
``digest:<sweep-dir>`` label would exceed GitHub's 50-character
label limit). The issue is created with BOTH the `borsagator`
label (what the digest watch discovers) and its identity label,
and a sweep is skipped whenever ANY issue — open or closed —
already carries its identity label. The label filter is an exact
API filter, not the lagged fuzzy search the old workflow used.
Creation is serialized across workflow runs by the workflow's
`concurrency` group (a per-sweep group is not expressible before
the job runs — the sweep identity is computed inside the step —
so the group serializes whole runs, which strictly includes
per-sweep serialization). There is no blind retry: the issue is
created once; if the create call fails, the identity label is
re-checked once (a create that landed server-side but reported
failure is then recognised as filed), and a genuine failure fails
the step loudly so a re-run retries it — the re-run's label
check then prevents any duplicate.

Usage (listing, unchanged — exit 0 always):
    worker_digest_issue.py --before <sha> --after <sha>
        --repo-dir <archive-branch checkout>
Stdout is one line per newly added merged sweep:
    <sweep_dir>\t<title>
Exit 0 always (a listing failure prints nothing, never fails the
workflow step that consumes it — the workflow treats an empty
listing as "nothing to file").

Usage (filing — what the workflow runs):
    worker_digest_issue.py --before <sha> --after <sha>
        --repo-dir <archive-branch checkout> --file
Files (or skips) one digest issue per listed sweep and exits 0
only when every sweep was filed or already had its issue; exits
1 when any sweep failed, after still filing the others.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

# Green, matching the repo's other automation labels.
IDENTITY_LABEL_COLOR = "0E8A16"
IDENTITY_LABEL_PREFIX = "digest-"


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


def identity_label(sweep_dir):
    """The durable per-sweep identity label for a sweep dir.

    ``digest-<first 16 hex of sha256(sweep_dir)>`` — deterministic,
    distinct per sweep dir (the dir embeds date, finished time and
    job id), 23 chars, well inside GitHub's 50-character label
    limit. The raw ``digest:<sweep-dir>`` form the issue suggests
    does not fit: a real dir is ~60–85 chars on its own."""
    digest = hashlib.sha256(sweep_dir.encode("utf-8")).hexdigest()
    return IDENTITY_LABEL_PREFIX + digest[:16]


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


def run_gh(args):
    """One `gh` call (module-level so tests can monkeypatch it).
    Returns the CompletedProcess; raises only on spawn/timeout."""
    return subprocess.run(["gh"] + list(args), capture_output=True,
                          text=True, timeout=120)


def issue_numbers_with_label(label):
    """Issue numbers carrying `label`, ANY state (open or closed).

    An exact label filter — not the search index — so a closed
    digest issue is found and a replay files no duplicate. Raises
    on an API failure: a failed check must never be read as "no
    issue exists", or the next step would file a duplicate."""
    proc = run_gh(["issue", "list", "--label", label, "--state",
                   "all", "--json", "number"])
    if proc.returncode != 0:
        raise RuntimeError(
            f"gh issue list --label {label} failed: "
            f"{(proc.stderr or proc.stdout or '').strip()[:200]}")
    try:
        return [int(row["number"]) for row in
                json.loads(proc.stdout or "[]")]
    except (ValueError, KeyError, TypeError) as e:
        raise RuntimeError(
            f"gh issue list --label {label} returned unparsable "
            f"output: {e}") from e


def ensure_identity_label(label, sweep_dir):
    """Create the per-sweep identity label if it does not exist yet.

    A failure here is swallowed deliberately: the common case is
    "already exists", and any other failure surfaces loudly one
    call later, when `gh issue create --label <label>` refuses the
    unknown label and the step goes red."""
    desc = f"Digest issue for {sweep_dir}"[:100]
    run_gh(["label", "create", label, "--color",
            IDENTITY_LABEL_COLOR, "--description", desc])


def file_issue(sweep_dir, title, repo_dir):
    """File (or skip) the digest issue for one merged sweep.

    Returns "created" or "exists". Raises on a genuine failure —
    the caller records it and files the remaining sweeps first.
    A missing digest.md is a failure, never a body-less issue."""
    label = identity_label(sweep_dir)
    ensure_identity_label(label, sweep_dir)
    if issue_numbers_with_label(label):
        print(f"issue already exists for {sweep_dir} — skipping")
        return "exists"
    body = Path(repo_dir) / sweep_dir / "digest.md"
    if not body.is_file():
        raise FileNotFoundError(
            f"{sweep_dir}: digest.md missing, refusing to file a "
            f"body-less issue")
    print(f"filing digest issue for {sweep_dir}")
    proc = run_gh(["issue", "create", "--title", title,
                   "--body-file", str(body),
                   "--label", "borsagator", "--label", label])
    if proc.returncode == 0:
        return "created"
    # No blind retry (#157): the create may have landed server-side
    # while the CLI reported failure. Re-check the identity label
    # once — if the issue is there now, it was filed; only a real
    # absence is a failure, and it fails loudly.
    if issue_numbers_with_label(label):
        print(f"issue for {sweep_dir} exists after a failed create "
              f"— treating as filed (create response was lost)")
        return "exists"
    raise RuntimeError(
        f"gh issue create for {sweep_dir} failed and no issue "
        f"carries {label}: "
        f"{(proc.stderr or proc.stdout or '').strip()[:200]}")


def file_issues(before, after, repo_dir):
    """File (or skip) one digest issue per newly merged sweep.

    Returns 0 when every sweep was filed or already had its issue,
    1 when any sweep failed — after still filing the others, so
    one bad sweep never blocks the rest of the push."""
    failures = []
    for sweep_dir in added_merge_manifests(before, after, repo_dir):
        md = Path(repo_dir) / sweep_dir / "digest.md"
        try:
            text = md.read_text(encoding="utf-8")
        except OSError:
            text = ""
        title, _status = digest_title_status(text)
        try:
            file_issue(sweep_dir, title, repo_dir)
        except Exception as e:  # noqa: BLE001 - one sweep must not
            # block the rest; the failure is reported at the end.
            failures.append((sweep_dir, e))
            print(f"worker_digest_issue: FAILED {sweep_dir}: {e}",
                  file=sys.stderr)
    if failures:
        print(f"worker_digest_issue: {len(failures)} sweep(s) failed "
              f"to file; re-run the workflow to retry (the identity "
              f"label check prevents duplicates)",
              file=sys.stderr)
        return 1
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="List merged sweeps added by an archive push.")
    ap.add_argument("--before", required=True)
    ap.add_argument("--after", required=True)
    ap.add_argument("--repo-dir", required=True)
    ap.add_argument("--file", action="store_true",
                    help="file (or skip) one digest issue per listed "
                    "sweep instead of just listing them")
    args = ap.parse_args(argv)
    if args.file:
        try:
            return file_issues(args.before, args.after, args.repo_dir)
        except Exception as e:  # noqa: BLE001 - never fail the
            # workflow on a listing failure, as before
            print(f"worker_digest_issue: {type(e).__name__}: {e}",
                  file=sys.stderr)
            return 0
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
