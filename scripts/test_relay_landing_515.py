#!/usr/bin/env python3
"""Functional tests for the relay's landing verification
(INS-REVIEW-093 blocker 2, PR #515).

The structural checks in test_deploy_guard_502.py prove the
checks EXIST in .github/workflows/ledger-publish-relay.yml;
this suite proves they BEHAVE: it extracts the "Verify the
merge on main" step's run block verbatim from the workflow
and executes it against synthetic repositories carrying real
merge commits.

Scenarios:
- a clean landing verifies (exit 0, success wording);
- the reproduced counterexample: the envelope DELETES
  ledger/old.json but the landing merge retains it — the old
  staged-blob loop reported this verified (it iterated the
  staged tree, which no longer lists the deleted path); the
  landing must now be REFUSED;
- a merge whose second parent is not the staged commit is
  refused (the landing is not bound to the expected merge);
- a merge introducing a path outside the frozen manifest is
  refused (introduced paths must be a SUBSET of the manifest);
- freshness is judged against the actual first parent: a
  staged envelope older than the heartbeat its merge actually
  landed on is refused.

Run: python3 scripts/test_relay_landing_515.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RELAY = (ROOT / ".github" / "workflows"
         / "ledger-publish-relay.yml").read_text()
VALIDATOR_SRC = ROOT / "scripts" / "check_relay_envelope.py"

PASSED = 0


def check(name, cond):
    global PASSED
    if not cond:
        print(f"FAIL: {name}")
        sys.exit(1)
    PASSED += 1
    print(f"ok: {name}")


def extract_verify_block():
    """The verbatim bash of the 'Verify the merge on main'
    step, dedented. Fails the suite (not silently) when the
    step cannot be found — a renamed step must update this
    extraction, never bypass it."""
    lines = RELAY.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.strip() == "- name: Verify the merge on main":
            start = i
            break
    if start is None:
        print("FAIL: verify step not found in the relay")
        sys.exit(1)
    run_idx = None
    for i in range(start, len(lines)):
        if lines[i].rstrip() == "        run: |":
            run_idx = i
            break
        if lines[i].strip().startswith("- name:") and i > start:
            break
    if run_idx is None:
        print("FAIL: verify step has no run block")
        sys.exit(1)
    block = []
    for line in lines[run_idx + 1:]:
        if line.strip() == "":
            block.append("")
        elif line.startswith("          "):
            block.append(line[10:])
        else:
            break
    script = "\n".join(block)
    if "Publication verified at the original merge commit" \
            not in script:
        print("FAIL: extracted block does not look like the "
              "verify step")
        sys.exit(1)
    return script


def git(repo, *args, check_rc=True):
    r = subprocess.run(["git", "-C", str(repo), *args],
                       capture_output=True, text=True)
    if check_rc and r.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed: {r.stderr}")
    return r


def heartbeat(run_id, at):
    return json.dumps({"run_id": run_id, "status": "ok",
                       "last_run_utc": at})


def write(repo, rel, content):
    p = Path(repo) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)


def commit_all(repo, msg):
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", msg)
    return git(repo, "rev-parse", "HEAD").stdout.strip()


BASE_HB = ("run-0", "2026-11-22T08:00:00Z")
STAGE_HB = ("run-1", "2026-11-22T09:00:00Z")
BRANCH = "publish/ledger-run-1"


def make_scenario(td):
    """origin (bare) + work clone. main carries the base
    envelope (heartbeat run-0 @08:00, ledger.json v1,
    ledger/old.json present). The staged commit (child of the
    base) carries heartbeat run-1 @09:00, ledger.json v2 and
    DELETES ledger/old.json; it is pushed as the publish
    branch. Returns (work, base_sha, stage_sha)."""
    origin = Path(td) / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", str(origin)],
                   check=True)
    work = Path(td) / "work"
    subprocess.run(["git", "clone", "-q", str(origin),
                    str(work)], check=True)
    git(work, "config", "user.email", "t@example.com")
    git(work, "config", "user.name", "Test")
    git(work, "config", "commit.gpgsign", "false")
    git(work, "checkout", "-q", "-b", "main")
    write(work, "ledger/guard-heartbeat.json",
          heartbeat(*BASE_HB))
    write(work, "ledger/ledger.json", '{"v": 1}')
    write(work, "ledger/old.json", '{"legacy": true}')
    base = commit_all(work, "base envelope")
    git(work, "push", "-q", "origin", "main")
    write(work, "ledger/guard-heartbeat.json",
          heartbeat(*STAGE_HB))
    write(work, "ledger/ledger.json", '{"v": 2}')
    git(work, "rm", "-q", "ledger/old.json")
    stage = commit_all(work, "staged envelope run-1")
    git(work, "push", "-q", "origin",
        f"HEAD:refs/heads/{BRANCH}")
    # The staged commit was built on main's tip; main itself
    # stays at the base — reset the local branch back so the
    # merge scenarios below create true two-parent merges.
    git(work, "checkout", "-q", "main")
    git(work, "reset", "-q", "--hard", base)
    # The verify step invokes the validator from the working
    # tree (as the relay's main checkout provides it live).
    scripts = Path(work) / "scripts"
    scripts.mkdir(exist_ok=True)
    shutil.copy(VALIDATOR_SRC, scripts / VALIDATOR_SRC.name)
    return work, base, stage


def run_verify(work, merge_sha, stage_sha, run_id=STAGE_HB[0]):
    script = extract_verify_block()
    out = Path(work) / "github-output.txt"
    out.write_text("")
    env = dict(os.environ)
    env.update({"MERGE_SHA": merge_sha, "STAGE_SHA": stage_sha,
                "RUN_ID": run_id, "BRANCH": BRANCH,
                "GITHUB_OUTPUT": str(out),
                "GH_TOKEN": "unused-by-this-step"})
    r = subprocess.run(["bash", "-c", script], cwd=work,
                       env=env, capture_output=True, text=True)
    return r


def test_clean_landing_verifies():
    with tempfile.TemporaryDirectory() as td:
        work, base, stage = make_scenario(td)
        git(work, "merge", "-q", "--no-ff", stage,
            "-m", "merge staged envelope")
        merge = git(work, "rev-parse", "HEAD").stdout.strip()
        git(work, "push", "-q", "origin", "main")
        r = run_verify(work, merge, stage)
        check("clean landing: verify step exits 0",
              r.returncode == 0)
        check("clean landing: success wording printed",
              "Publication verified at the original merge "
              "commit" in r.stdout)


def test_deleted_path_retained_refused():
    # The INS-REVIEW-093 counterexample, reproduced: the
    # envelope deletes ledger/old.json; the landing merge
    # restores it before committing. The old staged-blob loop
    # iterated the STAGED tree (old.json already gone there)
    # and reported verified.
    with tempfile.TemporaryDirectory() as td:
        work, base, stage = make_scenario(td)
        git(work, "merge", "--no-ff", "--no-commit", stage)
        git(work, "checkout", base, "--", "ledger/old.json")
        git(work, "commit", "-q", "-m",
            "merge staged envelope (deletion resolved away)")
        merge = git(work, "rev-parse", "HEAD").stdout.strip()
        git(work, "push", "-q", "origin", "main")
        r = run_verify(work, merge, stage)
        check("deletion retained: verify step refuses",
              r.returncode != 0)
        check("deletion retained: refusal names the path",
              "ledger/old.json" in (r.stdout + r.stderr)
              and "still present at merge"
              in (r.stdout + r.stderr))


def test_wrong_second_parent_refused():
    with tempfile.TemporaryDirectory() as td:
        work, base, stage = make_scenario(td)
        # A different commit carrying the same heartbeat but
        # different content; the merge binds IT, not the
        # staged commit the relay assessed. Built detached so
        # main itself does not advance onto it.
        git(work, "checkout", "-q", "--detach", "HEAD")
        write(work, "ledger/guard-heartbeat.json",
              heartbeat(*STAGE_HB))
        write(work, "ledger/ledger.json", '{"v": 3}')
        other = commit_all(work, "other envelope")
        git(work, "checkout", "-q", "main")
        git(work, "merge", "-q", "--no-ff", other,
            "-m", "merge other envelope")
        merge = git(work, "rev-parse", "HEAD").stdout.strip()
        git(work, "push", "-q", "origin", "main")
        r = run_verify(work, merge, stage)
        check("wrong second parent: verify step refuses",
              r.returncode != 0)
        check("wrong second parent: refusal names the binding",
              "second parent" in (r.stdout + r.stderr))


def test_unexpected_introduced_path_refused():
    with tempfile.TemporaryDirectory() as td:
        work, base, stage = make_scenario(td)
        git(work, "merge", "--no-ff", "--no-commit", stage)
        write(work, "unexpected.txt", "not in the manifest")
        git(work, "add", "unexpected.txt")
        git(work, "commit", "-q", "-m",
            "merge staged envelope + extra path")
        merge = git(work, "rev-parse", "HEAD").stdout.strip()
        git(work, "push", "-q", "origin", "main")
        r = run_verify(work, merge, stage)
        check("unexpected path: verify step refuses",
              r.returncode != 0)
        check("unexpected path: refusal names the subset rule",
              "unexpected introduced path"
              in (r.stdout + r.stderr))


def test_stale_against_first_parent_refused():
    with tempfile.TemporaryDirectory() as td:
        work, base, stage = make_scenario(td)
        # Main advances past the staged envelope BEFORE the
        # merge: the merge's actual first parent carries a
        # NEWER heartbeat (run-x @10:00) than the staged one.
        write(work, "ledger/guard-heartbeat.json",
              heartbeat("run-x", "2026-11-22T10:00:00Z"))
        write(work, "ledger/ledger.json", '{"v": "1x"}')
        commit_all(work, "main advances")
        git(work, "merge", "--no-ff", "--no-commit", stage,
            check_rc=False)
        git(work, "checkout", stage, "--",
            "ledger/guard-heartbeat.json", "ledger/ledger.json")
        git(work, "add", "-A")
        git(work, "commit", "-q", "-m",
            "merge staged envelope onto advanced main")
        merge = git(work, "rev-parse", "HEAD").stdout.strip()
        git(work, "push", "-q", "origin", "main")
        r = run_verify(work, merge, stage)
        check("stale vs first parent: verify step refuses",
              r.returncode != 0)
        check("stale vs first parent: freshness refusal named",
              "envelope freshness refused"
              in (r.stdout + r.stderr))


def main():
    test_clean_landing_verifies()
    test_deleted_path_retained_refused()
    test_wrong_second_parent_refused()
    test_unexpected_introduced_path_refused()
    test_stale_against_first_parent_refused()
    print(f"\n{PASSED} checks passed")


if __name__ == "__main__":
    main()
