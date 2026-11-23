#!/usr/bin/env python3
"""Tests for issue #443: scripts/ledger_publish.py staging mode.

Staging mode (--publish-branch) runs the same compute / validate
cycle as the direct publish but pushes the commit to a per-run
branch publish/ledger-<run-id> instead of main, where the
ledger-publish relay turns it into a merged PR. A staged publish
is PENDING, not published. Covered here, against a real local
git remote (no GitHub, no credentials):

  - a staged publish lands on the branch (ledger outputs + the
    --guard-heartbeat envelope) and leaves main untouched;
  - re-staging the identical outputs under the same branch
    reconciles as staged (idempotent), even though the heartbeat
    timestamp moved;
  - the same branch with DIFFERENT outputs fails immediately as
    a branch collision (the run id was reused) — including from a
    checkout that still heads the first staged commit, where a
    fast-forward would otherwise skip collision detection;
  - with the ledger already current, staging without a heartbeat
    stages nothing, and staging with one produces the
    heartbeat-only envelope;
  - direct mode (--commit, no branch) still pushes to main.

The ledger itself is a stub scripts/ledger.py writing minimal
valid outputs (variant via LEDGER_STUB_VARIANT). The publisher's
advisory live-archive check calls the real API when reachable
and is ignored on failure — it cannot change any outcome here.

Run: python3 scripts/test_ledger_publish_443.py (exit 0 = pass).
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

_HERE = Path(os.path.abspath(__file__)).parent
PUBLISHER = _HERE / "ledger_publish.py"

PASSED = 0

GIT_ENV = dict(os.environ,
               GIT_AUTHOR_NAME="gator-test",
               GIT_AUTHOR_EMAIL="test@borsagator.local",
               GIT_COMMITTER_NAME="gator-test",
               GIT_COMMITTER_EMAIL="test@borsagator.local")

STUB_LEDGER = '''
import json, os, sys
out = sys.argv[1]
variant = int(os.environ.get("LEDGER_STUB_VARIANT", "1"))
os.makedirs(out, exist_ok=True)
ledger = {
    "source": {"tree_sha": "aaaa1111bbbb2222",
               "commit_sha": "cccc3333dddd4444"},
    "counts": {"sweeps": 2, "forecasts": 2 + variant,
               "matured": 1, "pending": 2, "invalid": 0},
    "forecasts_detail": [],
    "gaps": [],
}
bench = {"tool": "benchmark-ledger", "rows": [], "gaps": [],
         "counts": {"entrant_rows": 0, "matured": 0,
                    "sweeps_with_freeze": 0},
         "by_entrant": {}}
with open(os.path.join(out, "ledger.json"), "w") as f:
    json.dump(ledger, f, indent=2)
with open(os.path.join(out, "benchmark.json"), "w") as f:
    json.dump(bench, f, indent=2)
with open(os.path.join(out, "weights.json"), "w") as f:
    json.dump({"factors": {}}, f)
with open(os.path.join(out, "ledger.md"), "w") as f:
    f.write("# ledger variant %d\\n" % variant)
with open(os.path.join(out, "benchmark.md"), "w") as f:
    f.write("# benchmark\\n")
'''


def check(name, cond):
    global PASSED
    if cond:
        PASSED += 1
        print(f"  ok: {name}")
    else:
        print(f"FAIL: {name}")
        raise SystemExit(1)


def git(*args, cwd=None, check_rc=True):
    r = subprocess.run(["git"] + list(args), cwd=cwd, env=GIT_ENV,
                       capture_output=True, text=True, timeout=120)
    if check_rc and r.returncode != 0:
        raise AssertionError(f"git {args}: {r.stderr}")
    return r


def make_repo(base):
    """Bare remote + a clone holding the publisher and the stub
    ledger, committed to main (no ledger/ published yet)."""
    remote = base / "remote.git"
    git("init", "--bare", "-b", "main", str(remote))
    repo = base / "repo"
    git("clone", str(remote), str(repo))
    git("-C", str(repo), "config", "user.email",
        "test@borsagator.local")
    git("-C", str(repo), "config", "user.name", "gator-test")
    scripts = repo / "scripts"
    scripts.mkdir(parents=True)
    shutil.copy(PUBLISHER, scripts / "ledger_publish.py")
    (scripts / "ledger.py").write_text(STUB_LEDGER)
    git("-C", str(repo), "add", "scripts/")
    git("-C", str(repo), "commit", "-m", "seed scripts")
    git("-C", str(repo), "push", "origin", "HEAD:main")
    return remote, repo


def run_publisher(repo, *args, variant="1", run_id="test-1",
                  extra_env=None):
    env = dict(os.environ)
    env.pop("GH_TOKEN", None)
    env.pop("GITHUB_TOKEN", None)
    env["LEDGER_STUB_VARIANT"] = variant
    env["LEDGER_RUN_ID"] = run_id
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [sys.executable, str(repo / "scripts" / "ledger_publish.py"),
         *args],
        cwd=repo, env=env, capture_output=True, text=True,
        timeout=600)


def remote_show(remote, ref, path):
    r = git("--git-dir", str(remote), "show", f"{ref}:{path}",
            check_rc=False)
    return r.stdout if r.returncode == 0 else None


def remote_ref(remote, ref):
    r = git("--git-dir", str(remote), "rev-parse", ref,
            check_rc=False)
    return r.stdout.strip() if r.returncode == 0 else None


BRANCH = "publish/ledger-test-1"


def test_staging_lands_on_branch_not_main():
    with tempfile.TemporaryDirectory() as td:
        remote, repo = make_repo(Path(td))
        seed_main = remote_ref(remote, "main")
        r = run_publisher(repo, "--commit", "--fail-hard",
                          "--publish-branch", BRANCH,
                          "--guard-heartbeat")
        check("staging: publisher exits 0", r.returncode == 0)
        check("staging: output says staged + PENDING",
              "staged on " + BRANCH in r.stdout
              and "PENDING" in r.stdout)
        check("staging: branch exists on the remote",
              remote_ref(remote, BRANCH) is not None)
        check("staging: main did not move",
              remote_ref(remote, "main") == seed_main)
        doc = json.loads(remote_show(remote, BRANCH,
                                     "ledger/ledger.json"))
        check("staging: branch carries the stub ledger",
              doc["counts"]["forecasts"] == 3)
        hb = json.loads(remote_show(remote, BRANCH,
                                    "ledger/guard-heartbeat.json"))
        check("staging: envelope heartbeat carries the run id",
              hb.get("run_id") == "test-1")
        check("staging: envelope heartbeat status is ok",
              hb.get("status") == "ok")


def test_staging_identical_outputs_reconcile():
    with tempfile.TemporaryDirectory() as td:
        remote, repo = make_repo(Path(td))
        r1 = run_publisher(repo, "--commit", "--fail-hard",
                           "--publish-branch", BRANCH,
                           "--guard-heartbeat")
        check("reconcile: first staging exits 0", r1.returncode == 0)
        # Reset the checkout to main, as the worker does per run,
        # and stage the same run again: the heartbeat timestamp
        # differs, the ledger outputs do not. The sleep forces a
        # distinct heartbeat second — within one second the two
        # envelope commits could be byte-identical, the re-push
        # would report up-to-date, and the reconcile path this
        # test asserts would never run (review finding on #491).
        git("-C", str(repo), "reset", "--hard", "origin/main")
        time.sleep(1.1)
        r2 = run_publisher(repo, "--commit", "--fail-hard",
                           "--publish-branch", BRANCH,
                           "--guard-heartbeat")
        check("reconcile: identical re-staging exits 0",
              r2.returncode == 0)
        check("reconcile: reported as already staged",
              "already carries these exact ledger outputs"
              in r2.stdout)


def test_staging_collision_fails_immediately():
    with tempfile.TemporaryDirectory() as td:
        remote, repo = make_repo(Path(td))
        r1 = run_publisher(repo, "--commit", "--fail-hard",
                           "--publish-branch", BRANCH,
                           "--guard-heartbeat", variant="1")
        check("collision: first staging exits 0", r1.returncode == 0)
        git("-C", str(repo), "reset", "--hard", "origin/main")
        r2 = run_publisher(repo, "--commit", "--fail-hard",
                           "--publish-branch", BRANCH,
                           "--guard-heartbeat", variant="2")
        check("collision: different outputs under the same branch "
              "fail", r2.returncode == 1)
        check("collision: failure names the reused branch",
              "already exists with different ledger content"
              in (r2.stdout + r2.stderr))
        doc = json.loads(remote_show(remote, BRANCH,
                                     "ledger/ledger.json"))
        check("collision: the branch still carries variant 1",
              doc["counts"]["forecasts"] == 3)


def test_staging_no_fast_forward_over_existing_branch():
    # Review finding on #491: if the checkout still HEADS the
    # first staged commit, a second publish with different
    # outputs could fast-forward the same branch, skipping
    # collision detection. Staging is create-only: the existing
    # branch is reconciled by content, never updated.
    with tempfile.TemporaryDirectory() as td:
        remote, repo = make_repo(Path(td))
        r1 = run_publisher(repo, "--commit", "--fail-hard",
                           "--publish-branch", BRANCH,
                           "--guard-heartbeat", variant="1")
        check("no-ff: first staging exits 0", r1.returncode == 0)
        tip = remote_ref(remote, BRANCH)
        # NO reset: HEAD is still the first envelope commit.
        r2 = run_publisher(repo, "--commit", "--fail-hard",
                           "--publish-branch", BRANCH,
                           "--guard-heartbeat", variant="2")
        check("no-ff: different outputs from a dirty checkout "
              "fail as a collision", r2.returncode == 1)
        check("no-ff: the branch tip did not move",
              remote_ref(remote, BRANCH) == tip)
        doc = json.loads(remote_show(remote, BRANCH,
                                     "ledger/ledger.json"))
        check("no-ff: the branch still carries variant 1",
              doc["counts"]["forecasts"] == 3)


def test_staging_unchanged_and_heartbeat_only():
    with tempfile.TemporaryDirectory() as td:
        remote, repo = make_repo(Path(td))
        # Publish directly first so main carries the ledger.
        r0 = run_publisher(repo, "--commit", "--fail-hard")
        check("unchanged: direct publish exits 0", r0.returncode == 0)
        check("unchanged: direct publish moved main",
              remote_show(remote, "main", "ledger/ledger.json")
              is not None)
        git("-C", str(repo), "reset", "--hard", "origin/main")
        # Same outputs, no heartbeat: nothing to stage.
        r1 = run_publisher(repo, "--commit", "--fail-hard",
                           "--publish-branch",
                           "publish/ledger-test-2", run_id="test-2")
        check("unchanged: staging exits 0", r1.returncode == 0)
        check("unchanged: no branch was created",
              remote_ref(remote, "publish/ledger-test-2") is None)
        check("unchanged: output says nothing to publish",
              "nothing to publish" in r1.stdout)
        git("-C", str(repo), "reset", "--hard", "origin/main")
        # Same outputs, with heartbeat: the heartbeat-only envelope.
        r2 = run_publisher(repo, "--commit", "--fail-hard",
                           "--publish-branch",
                           "publish/ledger-test-3",
                           "--guard-heartbeat", run_id="test-3")
        check("heartbeat-only: staging exits 0", r2.returncode == 0)
        check("heartbeat-only: branch was created",
              remote_ref(remote, "publish/ledger-test-3")
              is not None)
        check("heartbeat-only: ledger outputs match main's",
              remote_show(remote, "publish/ledger-test-3",
                          "ledger/ledger.json")
              == remote_show(remote, "main", "ledger/ledger.json"))
        hb = json.loads(remote_show(remote,
                                    "publish/ledger-test-3",
                                    "ledger/guard-heartbeat.json"))
        check("heartbeat-only: heartbeat carries run test-3",
              hb.get("run_id") == "test-3")


def test_staging_branch_lookup_error_fails_closed():
    # Issue #501: an errored ls-remote is UNKNOWN, not absence.
    # The publisher must fail closed and record the error — never
    # push on the strength of a lookup that did not happen.
    with tempfile.TemporaryDirectory() as td:
        remote, repo = make_repo(Path(td))
        seed_main = remote_ref(remote, "main")
        git("-C", str(repo), "remote", "set-url", "origin",
            str(Path(td) / "no-such-remote.git"))
        r = run_publisher(repo, "--commit", "--fail-hard",
                          "--publish-branch", BRANCH,
                          "--guard-heartbeat")
        check("lookup: errored lookup fails the publish",
              r.returncode == 1)
        check("lookup: failure names the lookup, not a push",
              "staging-branch lookup errored"
              in (r.stdout + r.stderr))
        check("lookup: failure states the fail-closed rule",
              "fail-closed" in (r.stdout + r.stderr))
        check("lookup: nothing reached the real remote",
              remote_ref(remote, "main") == seed_main
              and remote_ref(remote, BRANCH) is None)


def test_branch_lookup_timeout_is_a_lookup_error():
    # PR #515 review: an ls-remote TIMEOUT inside
    # _remote_branch_sha used to raise through publish()'s
    # outer wrapper and be recorded as a generic interruption
    # (reset + recompute), instead of the fail-closed
    # branch-lookup error. Unit-level: import the publisher and
    # make its git() raise TimeoutExpired for ls-remote.
    sys.path.insert(0, str(_HERE))
    import ledger_publish as publisher
    orig_git = publisher.git

    def timing_out_git(*args):
        if args and args[0] == "ls-remote":
            raise subprocess.TimeoutExpired(cmd="git ls-remote",
                                            timeout=120)
        return orig_git(*args)

    publisher.git = timing_out_git
    try:
        sha, err = publisher._remote_branch_sha(BRANCH)
    finally:
        publisher.git = orig_git
    check("lookup-timeout: timed-out lookup returns no sha",
          sha is None)
    check("lookup-timeout: timed-out lookup returns a lookup "
          "error (fail-closed), not an exception",
          err is not None and "timed out" in err)


def test_publisher_record_precedes_staging_push():
    # INS-REVIEW-093: the publisher establishes its OWN durable
    # envelope record BEFORE its staging push, in a directory
    # outside the resettable clone (named by the worker via
    # GATOR_PENDING_ENVELOPES). If the publisher then dies before
    # the worker captures the staged envelope, the record still
    # exists. And a required record that cannot be written
    # blocks the push entirely.
    with tempfile.TemporaryDirectory() as td:
        remote, repo = make_repo(Path(td))
        records = Path(td) / "pending-envelopes"
        os.environ["GATOR_PENDING_ENVELOPES"] = str(records)
        try:
            r = run_publisher(repo, "--commit", "--fail-hard",
                              "--publish-branch", BRANCH,
                              "--guard-heartbeat")
        finally:
            os.environ.pop("GATOR_PENDING_ENVELOPES", None)
        check("093: publisher exits 0 with a record dir named",
              r.returncode == 0)
        rec_path = records / "test-1.json"
        check("093: publisher-side record exists after the run "
              "(publisher death before worker capture still "
              "leaves it)", rec_path.exists())
        record = json.loads(rec_path.read_text())
        check("093: record names the staged envelope commit",
              record.get("envelope_commit")
              == remote_ref(remote, BRANCH))
        check("093: record carries the envelope heartbeat",
              record.get("heartbeat", {}).get("run_id")
              == "test-1")
        check("093: record carries the envelope blobs",
              "ledger/guard-heartbeat.json"
              in record.get("blobs", {}))
    with tempfile.TemporaryDirectory() as td:
        remote, repo = make_repo(Path(td))
        blocker = Path(td) / "blocker"
        blocker.write_text("a file, not a directory\n")
        os.environ["GATOR_PENDING_ENVELOPES"] = str(blocker)
        try:
            r = run_publisher(repo, "--commit", "--fail-hard",
                              "--publish-branch", BRANCH,
                              "--guard-heartbeat")
        finally:
            os.environ.pop("GATOR_PENDING_ENVELOPES", None)
        check("093: a failed required record fails the publish",
              r.returncode != 0)
        check("093: no staging push after the record failure",
              remote_ref(remote, BRANCH) is None)


def test_idempotent_adoption_attempt_binding():
    # INS-REVIEW-105: idempotent adoption is bound to the
    # producing attempt. Attempt A stages (its durable record
    # lands before the push); attempt B re-running the same
    # publish must NOT adopt A's branch or rewrite the record
    # under B's identity; attempt A re-running reconciles.
    with tempfile.TemporaryDirectory() as td:
        remote, repo = make_repo(Path(td))
        pending = str(Path(td) / "pending")
        env_a = {"GATOR_PENDING_ENVELOPES": pending,
                 "LEDGER_ATTEMPT_ID":
                 "worker-5@2026-11-22T10:00:00Z"}
        env_b = {"GATOR_PENDING_ENVELOPES": pending,
                 "LEDGER_ATTEMPT_ID":
                 "worker-5@2026-11-22T11:00:00Z"}
        r1 = run_publisher(repo, "--commit", "--fail-hard",
                           "--publish-branch", BRANCH,
                           "--guard-heartbeat", extra_env=env_a)
        check("105: attempt A stages", r1.returncode == 0)
        rec_path = Path(pending) / "test-1.json"
        check("105: A's durable record exists, bound to A",
              rec_path.exists()
              and json.loads(rec_path.read_text())["attempt_id"]
              == "worker-5@2026-11-22T10:00:00Z")
        tip = remote_ref(remote, BRANCH)
        git("-C", str(repo), "reset", "--hard", "origin/main")
        time.sleep(1.1)
        r2 = run_publisher(repo, "--commit", "--fail-hard",
                           "--publish-branch", BRANCH,
                           "--guard-heartbeat", extra_env=env_b)
        check("105: attempt B cannot adopt A's branch",
              r2.returncode == 1)
        check("105: B's refusal names the producing attempt",
              "produced by attempt" in (r2.stdout + r2.stderr))
        check("105: the record still belongs to A",
              json.loads(rec_path.read_text())["attempt_id"]
              == "worker-5@2026-11-22T10:00:00Z")
        check("105: the branch tip is unchanged",
              remote_ref(remote, BRANCH) == tip)
        git("-C", str(repo), "reset", "--hard", "origin/main")
        time.sleep(1.1)
        r3 = run_publisher(repo, "--commit", "--fail-hard",
                           "--publish-branch", BRANCH,
                           "--guard-heartbeat", extra_env=env_a)
        check("105: attempt A re-running reconciles as staged",
              r3.returncode == 0
              and "already carries these exact ledger outputs"
              in r3.stdout)


def main():
    test_idempotent_adoption_attempt_binding()
    test_publisher_record_precedes_staging_push()
    test_branch_lookup_timeout_is_a_lookup_error()
    test_staging_branch_lookup_error_fails_closed()
    test_staging_lands_on_branch_not_main()
    test_staging_identical_outputs_reconcile()
    test_staging_collision_fails_immediately()
    test_staging_no_fast_forward_over_existing_branch()
    test_staging_unchanged_and_heartbeat_only()
    print(f"\n{PASSED} checks passed")


if __name__ == "__main__":
    main()
