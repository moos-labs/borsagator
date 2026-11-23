#!/usr/bin/env python3
"""Pre-merge envelope validation for the ledger-publish relay
(issue #500).

The relay used to check only the three-dot diff scope against
main before merging a staged envelope. That under-validates in
both directions the review named: base-tip equality would
over-reject safe changes (an unrelated main commit must not
block an envelope), and a heartbeat timestamp alone
under-validates content. This validator instead checks the
envelope against its own declared structure:

  - the staged commit has exactly one parent — its DECLARED
    BASE — and that parent is in main's history (an ancestor of
    the main ref) and is exactly the merge-base of the staged
    commit and main: the envelope was built on main, not on a
    side line;
  - every path the envelope changes RELATIVE TO ITS DECLARED
    BASE is under ledger/** (the scope that matters — main may
    have moved elsewhere since the base, and that is fine);
  - heartbeat ordering, parsed (never string-guessed beyond the
    fixed ISO-Z format the guard writes): the staged heartbeat
    must not be OLDER than the heartbeat at its declared base
    (a regressive envelope), and must not be OLDER than the
    heartbeat main currently carries (a superseded envelope —
    a newer run has already landed; merging this one would
    regress main's ledger, so it is refused pre-merge and the
    run restages from current main).

The same check runs twice: once in the relay's assess step
(pre-merge) and again in the merge step against the freshly
fetched main (the ACTUAL merge candidate), so a concurrent
update landing between assess and merge cannot slip through.

Usage:
  check_relay_envelope.py --stage <sha> [--main-ref origin/main]
                          [--repo-dir .]

Prints a JSON verdict on stdout. Exit 0 when the envelope is
acceptable, 1 when it is refused (the verdict's "reason" says
why), 2 on usage/setup errors.
"""
import argparse
import json
import subprocess
import sys
from datetime import datetime

HEARTBEAT_REL = "ledger/guard-heartbeat.json"


def git(repo_dir, *args):
    return subprocess.run(["git", "-C", repo_dir, *args],
                          capture_output=True, text=True, timeout=120)


def show_file(repo_dir, ref, path):
    r = git(repo_dir, "show", f"{ref}:{path}")
    return r.stdout if r.returncode == 0 else None


def file_exists(repo_dir, ref, path):
    """True when `path` exists as an object at `ref`, False when
    it is positively absent, None when git cannot answer. The
    distinction matters (PR #515 review): a heartbeat that
    EXISTS but cannot be read must refuse validation — reading
    the read failure as absence silently drops the freshness
    check it feeds.

    Existence is established from the TREE, never from blob
    readability (PR #515 review round 2, INS-REVIEW-093): the
    earlier `cat-file -e ref:path` probe exits non-zero when the
    tree entry exists but its blob is missing from the object
    database, and the old code read that as positive absence —
    a stale envelope then validated ok:true against a baseline
    whose heartbeat was never read. `git ls-tree` lists the
    entry from the tree object itself, blob present or not:
    a listed entry is existence, an empty listing after a
    successful lookup is positive absence, and a failed lookup
    (unreadable ref/tree) stays unknown — the caller fails
    closed on both non-answers."""
    r = git(repo_dir, "ls-tree", "-z", ref, "--", path)
    if r.returncode != 0:
        return None
    return bool(r.stdout.strip())


def parse_ts(value):
    """A timezone-aware datetime for a canonical UTC timestamp
    string, or None when the value is not one. Ordering compares
    parsed instants, never raw strings (PR #515 review): a
    malformed or non-canonical value must not slip past the
    freshness checks by lexical accident."""
    if not isinstance(value, str):
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        return None
    return dt


def heartbeat_at(repo_dir, ref):
    """(last_run_utc or None, error or None) for the heartbeat at
    ref. A missing file is None without error; a file that
    exists but cannot be read, an unparseable file, or a
    present-but-malformed timestamp is an error — an envelope
    whose heartbeat cannot be parsed cannot be ordered."""
    raw = show_file(repo_dir, ref, HEARTBEAT_REL)
    if raw is None:
        exists = file_exists(repo_dir, ref, HEARTBEAT_REL)
        if exists:
            return None, (f"heartbeat at {ref} exists but "
                          "cannot be read — refusing rather "
                          "than treating it as absent")
        if exists is None:
            return None, (f"heartbeat presence at {ref} cannot "
                          "be established — refusing")
        return None, None
    try:
        doc = json.loads(raw)
    except Exception as e:
        return None, f"heartbeat at {ref} is unparseable: {e}"
    if not isinstance(doc, dict):
        return None, f"heartbeat at {ref} is not a JSON object"
    ts = doc.get("last_run_utc")
    if ts is not None and parse_ts(ts) is None:
        return None, (f"heartbeat at {ref} carries a malformed "
                      f"last_run_utc {ts!r} — cannot be ordered")
    return ts, None


def validate(repo_dir, stage, main_ref):
    v = {"ok": False, "stage": stage, "main_ref": main_ref}
    r = git(repo_dir, "rev-list", "--parents", "-n", "1", stage)
    if r.returncode != 0:
        v["reason"] = f"staged commit {stage} cannot be read"
        return v
    parts = r.stdout.split()
    if len(parts) != 2:
        v["reason"] = ("staged commit must have exactly one "
                       "parent (its declared base); found "
                       f"{len(parts) - 1}")
        return v
    base = parts[1]
    v["base_sha"] = base
    if git(repo_dir, "merge-base", "--is-ancestor", base,
           main_ref).returncode != 0:
        v["reason"] = (f"declared base {base} is not an ancestor "
                       f"of {main_ref} — the envelope was not "
                       "built on main's history")
        return v
    mb = git(repo_dir, "merge-base", main_ref, stage)
    if mb.returncode != 0 or mb.stdout.strip() != base:
        v["reason"] = (f"merge-base of {main_ref} and the staged "
                       f"commit is {mb.stdout.strip() or '?'}, "
                       f"not the declared base {base}")
        return v
    # --no-renames: a rename shows as a delete plus an add, so
    # BOTH sides of it face the scope check — with rename
    # detection, `git diff --name-only` lists only the
    # destination, and renaming a file OUT of scope into
    # ledger/** (or the reverse) would hide the out-of-scope
    # side (PR #515 review). -z: paths arrive unquoted and
    # NUL-separated, so a non-ASCII ledger path is checked as
    # the path it is, not as a quoted string that fails the
    # prefix test.
    r = git(repo_dir, "diff", "--no-renames", "--name-only",
            "-z", base, stage)
    if r.returncode != 0:
        v["reason"] = "diff against the declared base failed"
        return v
    paths = [p for p in r.stdout.split("\0") if p]
    v["paths"] = paths
    bad = [p for p in paths if not p.startswith("ledger/")]
    if bad:
        v["reason"] = ("envelope changes paths outside ledger/** "
                       "relative to its declared base: "
                       + ", ".join(bad))
        return v
    if not paths:
        v["reason"] = "envelope changes nothing vs its declared base"
        return v
    staged_at, err = heartbeat_at(repo_dir, stage)
    if err:
        v["reason"] = err
        return v
    base_at, err = heartbeat_at(repo_dir, base)
    if err:
        v["reason"] = err
        return v
    main_at, err = heartbeat_at(repo_dir, main_ref)
    if err:
        v["reason"] = err
        return v
    v["staged_at"] = staged_at
    v["base_at"] = base_at
    v["main_at"] = main_at
    # Fail closed on the staged side (PR #515 review): an
    # envelope with NO heartbeat, or a heartbeat carrying no
    # timestamp, cannot be ordered — the old code skipped both
    # ordering checks and approved it. (A first publish is safe:
    # its staged heartbeat exists and is timestamped; only the
    # BASE/main side may legitimately be absent.)
    staged_dt = parse_ts(staged_at)
    if staged_dt is None:
        v["reason"] = ("staged envelope carries no readable "
                       "heartbeat timestamp — refusing: its "
                       "freshness cannot be established")
        return v
    base_dt = parse_ts(base_at)
    if base_dt is not None and staged_dt <= base_dt:
        v["reason"] = (f"not strictly newer than its base: staged "
                       f"heartbeat {staged_at} is not newer than its "
                       f"declared base's {base_at} (equal-to-base "
                       "is refused) — restage from current main")
        return v
    main_dt = parse_ts(main_at)
    if main_dt is not None and main_dt >= staged_dt:
        v["reason"] = (f"not strictly newer than main: staged "
                       f"heartbeat {staged_at} is equal to or older "
                       f"than main's current heartbeat {main_at} — "
                       "refusing pre-merge; restage from current main")
        return v
    v["ok"] = True
    return v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True)
    ap.add_argument("--main-ref", default="origin/main")
    ap.add_argument("--repo-dir", default=".")
    args = ap.parse_args()
    try:
        v = validate(args.repo_dir, args.stage, args.main_ref)
    except (subprocess.TimeoutExpired, OSError) as e:
        # Setup error, not a verdict on the candidate (PR #515
        # review): git itself could not run, so print the
        # documented JSON verdict shape and return the
        # setup-error status 2 — never a traceback that the
        # relay would misread as a refusal (exit 1).
        print(json.dumps(
            {"ok": False, "stage": args.stage,
             "main_ref": args.main_ref,
             "setup_error": f"{type(e).__name__}: {e}"},
            indent=1))
        return 2
    print(json.dumps(v, indent=1))
    return 0 if v["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
