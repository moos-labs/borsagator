#!/usr/bin/env python3
"""Deterministic regression tests for issue #232: the deploy guard.

Covers scripts/deploy_archive.py and scripts/check_helper_blob_parity.py.
Nineteen checks, T1-T19:

- T1 fresh deploy, pinned source SHA: atomic move, scope, record
  links SHAs, source.pinned true, non-helper paths untouched.
- T2 source pinning is real: a deploy pinned to an OLDER source
  commit deploys that commit's blob, not the current main tip's.
- T3 idempotent re-run: content-based no-op, ref unchanged, zero new
  git objects.
- T4 CAS race, competing CHILD commit: lease rejects, rebuild on the
  new parent, retry lands; exactly one deploy commit.
- T5 CAS exhaustion: red cas-exhausted; each failure classified by
  reachability from the observed tip; every attempt SHA and observed
  head retained in attempts_detail; the remote carries zero deploy
  commits (checked, not assumed). The rejected attempts' built
  commits DO remain temporarily unreachable in the LOCAL clone
  until git gc; that is asserted as expected and is distinct from
  the remote carrying them or from any false success.
- T6 post-assert STRICT equality: a competing DATA commit landing
  after our push is red verify-failed naming the expected SHA and
  the exact observed tip; no repair is attempted.
- T7 a late mover that REWRITES the helper is likewise red, SHAs
  named; the rewriting tip stands.
- T8 verify scope/blob unit asserts: extra path red and named,
  helper-untouched red, wrong blob red with SHAs, correct green.
- T9 rewind race: competitor force-rewinds archive to an ANCESTOR of
  the read value; the lease rejects (a plain non-forced push would
  accept, which is the exact-CAS discriminator); retry lands on the
  rewound parent.
- T10 lost response: push landed but reported failure; reconcile
  finds the commit on the remote; deployed, one attempt, marked
  reconciled, exactly one deploy commit.
- T11 lost response plus late mover: reconcile finds the landed
  commit, then the STRICT assert goes red naming both SHAs.
- T12 non-contention rejection: failure with the ref unmoved and the
  commit not reachable is push-rejected, red, ONE attempt (no retry
  as contention), server message retained.
- T13 probe failure: an unreachable remote is result "error", never
  mislabeled bootstrap-required; record still written; SHA keys
  present and null.
- T14 parity: drift red with captured stderr naming BOTH refs and
  BOTH blob SHAs; green after an unpinned deploy with captured
  PARITY OK; missing blob red with MISSING; opt-in all-three refs
  green when equal and red naming worker-release when it drifts.
- T15 preflight: a locally malformed deploy commit fails as
  preflight-failed BEFORE any push; the push function is never
  called; the remote is unchanged; the record says preflight.
- T16 symbolic source rejected: --main-sha given a branch name,
  short SHA or HEAD is an error before any effect; nothing moves.
- T17 record write failure AFTER landing: the run goes nonzero with
  record_write_failed true, the actual result (deployed) is
  retained, and the landed state on the remote is real.
- T18 push timeout after landing: a timeout whose push actually
  landed is reconciled by re-read; deployed, one attempt.
- T19 lost response + reconciliation read error: the push landed
  but reported failure AND the reconciliation re-read fails; the
  run is nonzero with result "unknown", and the attempted SHA,
  expected OLD and push error are preserved in the record with
  the observed tip null.

All git operations run against REAL git in tmp repos with a file://
bare origin: no fake git, so the lease/CAS semantics under test are
git's own. Races are sequenced deterministically through push_cas
wrappers, no threads. Commit timestamps are pinned for
reproducibility. Stdlib only, no network. Run:
    python3 scripts/test_deploy_archive_232.py
Exit 0 only when every test passes.
"""
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)

import deploy_archive as da  # noqa: E402
import check_helper_blob_parity as bp  # noqa: E402

RESULTS = []
FIXED_ENV = {"GIT_AUTHOR_DATE": "2026-11-19T00:00:00Z",
             "GIT_COMMITTER_DATE": "2026-11-19T00:00:00Z"}


def check(name, fn):
    try:
        fn()
    except Exception as e:
        RESULTS.append((name, False, f"{type(e).__name__}: {e}"))
        print(f"FAIL {name}: {type(e).__name__}: {e}")
        return
    RESULTS.append((name, True, ""))
    print(f"PASS {name}")


def git(repo, *args):
    env = dict(os.environ)
    env.update({"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL":
                "t@t"})
    env.update(FIXED_ENV)
    p = subprocess.run(["git", "-C", repo, *args], env=env,
                       capture_output=True, text=True)
    assert p.returncode == 0, f"git {args}: {p.stderr}"
    return p.stdout.strip()


def commit_file(repo, path, content, message):
    full = os.path.join(repo, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w") as f:
        f.write(content)
    git(repo, "add", path)
    # --allow-empty: crafted-commit tests rewrite identical content
    git(repo, "commit", "--allow-empty", "-m", message)


def make_repos(tmp, with_archive=True):
    """origin (bare) + work clone.

    main: README, helper v1 (commit A), helper v1b (commit B, tip).
    worker-release: pinned at A (helper v1), as a frozen candidate.
    archive: helper v0 plus a data file, so a deploy is pending.
    Returns (origin, work, sha_a, blob_v1, blob_v1b).
    """
    origin = os.path.join(tmp, "origin.git")
    git(tmp, "init", "--bare", "--initial-branch=main", origin)
    seed = os.path.join(tmp, "seed")
    git(tmp, "clone", origin, seed)
    commit_file(seed, "README.md", "seed\n", "readme")
    commit_file(seed, da.HELPER_PATH, "helper v1\n", "helper v1")
    sha_a = git(seed, "rev-parse", "HEAD")
    blob_v1 = git(seed, "rev-parse", f"HEAD:{da.HELPER_PATH}")
    git(seed, "branch", "worker-release", sha_a)
    commit_file(seed, da.HELPER_PATH, "helper v1b\n", "helper v1b")
    blob_v1b = git(seed, "rev-parse", f"HEAD:{da.HELPER_PATH}")
    git(seed, "push", "origin", "main", "worker-release")
    if with_archive:
        git(seed, "checkout", "-b", "archive")
        commit_file(seed, da.HELPER_PATH, "helper v0\n", "helper v0")
        commit_file(seed, "data/run.json", "{}\n", "data")
        git(seed, "push", "origin", "archive")
    work = os.path.join(tmp, "work")
    git(tmp, "clone", origin, work)
    return origin, work, sha_a, blob_v1, blob_v1b


def competitor_commit(tmp, origin, tag, path=None, content="{}\n"):
    """A competing writer lands a commit on archive."""
    comp = os.path.join(tmp, f"comp-{tag}")
    git(tmp, "clone", origin, comp)
    git(comp, "checkout", "archive")
    commit_file(comp, path or f"data/{tag}.json", content,
                f"data {tag}")
    git(comp, "push", "origin", "archive")
    return git(comp, "rev-parse", "archive")


def competitor_rewind(tmp, origin, tag):
    """A competing writer force-rewinds archive to its parent."""
    comp = os.path.join(tmp, f"comp-{tag}")
    git(tmp, "clone", origin, comp)
    git(comp, "checkout", "archive")
    rewound = git(comp, "rev-parse", "archive~1")
    git(comp, "reset", "--hard", rewound)
    git(comp, "push", "--force", "origin", "archive")
    return rewound


def remote_tip(origin, branch="archive"):
    return git(origin, "rev-parse", branch)


def count_objects(repo):
    p = subprocess.run(["git", "-C", repo, "cat-file",
                        "--batch-all-objects", "--batch-check"],
                       capture_output=True, text=True)
    return len(p.stdout.splitlines())


def run_deploy(work, record, main_sha=None):
    return da.deploy(work, "origin", da.ARCHIVE_REF, da.MAIN_REF,
                     da.HELPER_PATH, record, env_extra=FIXED_ENV,
                     clock=lambda: 1.0, main_sha=main_sha)


def wrap_push(fn):
    real = da.push_cas
    state = {"n": 0}

    def wrapper(repo, remote, new_sha, ref, expected_old):
        state["n"] += 1
        return fn(state, real, repo, remote, new_sha, ref,
                  expected_old)
    return wrapper, real, state


def read_record(record):
    return [json.loads(l) for l in open(record)]


def test_fresh_deploy_pinned():
    tmp = tempfile.mkdtemp()
    try:
        origin, work, sha_a, blob_v1, _ = make_repos(tmp)
        record = os.path.join(tmp, "deploys.jsonl")
        old = remote_tip(origin)
        rc, rec = run_deploy(work, record, main_sha=sha_a)
        assert rc == 0 and rec["result"] == "deployed", rec
        assert rec["attempts"] == 1, rec
        assert rec["source"] == {"sha": sha_a, "pinned": True}, rec
        new = rec["new_archive_sha"]
        assert remote_tip(origin) == new, "remote ref not moved"
        assert git(origin, "rev-parse", f"{new}^") == old
        changed = git(origin, "diff", "--name-only",
                      f"{old}..{new}").split()
        assert changed == [da.HELPER_PATH], changed
        assert git(origin, "rev-parse",
                   f"{new}:{da.HELPER_PATH}") == blob_v1
        # every other path untouched
        assert git(origin, "rev-parse", f"{new}:data/run.json") == \
            git(origin, "rev-parse", f"{old}:data/run.json")
        # record links all SHAs and matches the returned record
        lines = read_record(record)
        assert len(lines) == 1 and lines[0] == rec, lines
        for k in ("main_sha", "main_blob", "old_archive_sha",
                  "new_archive_sha"):
            assert rec.get(k), rec
        assert rec["main_sha"] == sha_a
        assert rec["main_blob"] == blob_v1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_pinned_source_not_main_tip():
    tmp = tempfile.mkdtemp()
    try:
        origin, work, sha_a, blob_v1, blob_v1b = make_repos(tmp)
        assert blob_v1 != blob_v1b, "fixture needs drift on main"
        record = os.path.join(tmp, "deploys.jsonl")
        rc, rec = run_deploy(work, record, main_sha=sha_a)
        assert rc == 0, rec
        tip_blob = git(origin, "rev-parse",
                       f"archive:{da.HELPER_PATH}")
        assert tip_blob == blob_v1, (
            f"pinned deploy must ship the pinned blob, got {tip_blob}")
        assert tip_blob != blob_v1b
        assert rec["main_blob"] == blob_v1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_idempotent_rerun():
    tmp = tempfile.mkdtemp()
    try:
        origin, work, sha_a, _, _ = make_repos(tmp)
        record = os.path.join(tmp, "deploys.jsonl")
        rc1, rec1 = run_deploy(work, record, main_sha=sha_a)
        assert rc1 == 0 and rec1["result"] == "deployed", rec1
        tip = remote_tip(origin)
        objs = count_objects(work)
        rc2, rec2 = run_deploy(work, record, main_sha=sha_a)
        assert rc2 == 0 and rec2["result"] == "noop", rec2
        assert rec2["attempts"] == 0, rec2
        assert remote_tip(origin) == tip, "noop moved the ref"
        assert count_objects(work) == objs, \
            "noop created a commit object"
        assert len(read_record(record)) == 2
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_cas_race_child_retry_lands():
    tmp = tempfile.mkdtemp()
    try:
        origin, work, sha_a, _, _ = make_repos(tmp)
        record = os.path.join(tmp, "deploys.jsonl")

        def race(state, real, repo, remote, new_sha, ref, exp_old):
            if state["n"] == 1:
                competitor_commit(tmp, origin, "t4")
            return real(repo, remote, new_sha, ref, exp_old)
        da.push_cas, real, _ = (lambda w: (w, da.push_cas, None))(
            wrap_push(race)[0])
        try:
            rc, rec = run_deploy(work, record, main_sha=sha_a)
        finally:
            da.push_cas = real
        assert rc == 0 and rec["result"] == "deployed", rec
        assert rec["attempts"] == 2, rec
        tip = remote_tip(origin)
        assert tip == rec["new_archive_sha"]
        comp = git(origin, "rev-parse", f"{tip}^")
        assert git(origin, "diff", "--name-only",
                   f"{comp}..{tip}").split() == [da.HELPER_PATH]
        log = git(origin, "log", "--format=%an %s", "archive")
        assert log.count("borsagator-deploy") == 1, log
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_cas_exhaustion_reconciled_red():
    tmp = tempfile.mkdtemp()
    try:
        origin, work, sha_a, _, _ = make_repos(tmp)
        record = os.path.join(tmp, "deploys.jsonl")

        def race(state, real, repo, remote, new_sha, ref, exp_old):
            competitor_commit(tmp, origin, f"t5-{state['n']}")
            return real(repo, remote, new_sha, ref, exp_old)
        wrapper, real, _ = wrap_push(race)
        da.push_cas = wrapper
        try:
            rc, rec = run_deploy(work, record, main_sha=sha_a)
        finally:
            da.push_cas = real
        assert rc == 1 and rec["result"] == "cas-exhausted", rec
        assert rec["attempts"] == 3, rec
        assert "not reachable from the tip observed" in \
            rec["detail"], rec["detail"]
        # every attempt SHA and observed head is retained for
        # manual reconciliation
        assert len(rec["attempts_detail"]) == 3, rec
        assert all(d["sha"] and d["observed_tip"] for d in
                   rec["attempts_detail"]), rec
        # factual, not assumed, in both directions. The rejected
        # attempts' built commits exist only as temporary
        # unreachable objects in the LOCAL clone (expected; git gc
        # collects them), while the REMOTE carries none of them and
        # no success was reported. Preventing false success is not
        # a claim that no local dangling object is ever created.
        remote_log = git(origin, "log", "--format=%H %an", "archive")
        assert "borsagator-deploy" not in remote_log, remote_log
        for d in rec["attempts_detail"]:
            git(work, "cat-file", "-e", d["sha"])
            assert d["sha"] not in remote_log.split(), d
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_late_mover_after_landing_is_red():
    tmp = tempfile.mkdtemp()
    try:
        origin, work, sha_a, blob_v1, _ = make_repos(tmp)
        record = os.path.join(tmp, "deploys.jsonl")
        held = {}

        def race(state, real, repo, remote, new_sha, ref, exp_old):
            out = real(repo, remote, new_sha, ref, exp_old)
            if state["n"] == 1 and out[0]:
                held["tip"] = competitor_commit(tmp, origin, "t6")
            return out
        wrapper, real, _ = wrap_push(race)
        da.push_cas = wrapper
        try:
            rc, rec = run_deploy(work, record, main_sha=sha_a)
        finally:
            da.push_cas = real
        # strict equality: even a benign data-only late mover is red
        assert rc == 1 and rec["result"] == "verify-failed", rec
        assert rec["new_archive_sha"] in rec["detail"] and \
            held["tip"] in rec["detail"], rec["detail"]
        assert "later commit landed" in rec["detail"], rec["detail"]
        # detected, not repaired: the observed tip stands
        assert remote_tip(origin) == held["tip"]
        assert git(origin, "rev-parse",
                   f"{held['tip']}:{da.HELPER_PATH}") == blob_v1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_late_mover_rewriting_helper_is_red():
    tmp = tempfile.mkdtemp()
    try:
        origin, work, sha_a, blob_v1, _ = make_repos(tmp)
        record = os.path.join(tmp, "deploys.jsonl")

        def race(state, real, repo, remote, new_sha, ref, exp_old):
            out = real(repo, remote, new_sha, ref, exp_old)
            if state["n"] == 1 and out[0]:
                competitor_commit(tmp, origin, "t7",
                                  path=da.HELPER_PATH,
                                  content="evil rewrite\n")
            return out
        wrapper, real, _ = wrap_push(race)
        da.push_cas = wrapper
        try:
            rc, rec = run_deploy(work, record, main_sha=sha_a)
        finally:
            da.push_cas = real
        assert rc == 1 and rec["result"] == "verify-failed", rec
        assert "expected" in rec["detail"] and \
            rec["new_archive_sha"] in rec["detail"], rec["detail"]
        # detected, not repaired: the rewriting tip stands
        assert git(origin, "rev-parse",
                   f"archive:{da.HELPER_PATH}") != blob_v1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_verify_scope_and_blob():
    tmp = tempfile.mkdtemp()
    try:
        origin = os.path.join(tmp, "origin.git")
        git(tmp, "init", "--bare", "--initial-branch=main", origin)
        repo = os.path.join(tmp, "r")
        git(tmp, "clone", origin, repo)

        def craft(extra=None, wrong=False, skip_helper=False):
            commit_file(repo, da.HELPER_PATH, "v0\n", "v0")
            commit_file(repo, "data/a.json", "{}\n", "data")
            old = git(repo, "rev-parse", "HEAD")
            if not skip_helper:
                commit_file(repo, da.HELPER_PATH,
                            "v0-wrong\n" if wrong else "v1\n",
                            "deploy")
            if extra:
                commit_file(repo, extra, "x\n", "extra")
            new = git(repo, "rev-parse", "HEAD")
            expected = git(repo, "rev-parse",
                           f"{old}:{da.HELPER_PATH}")
            # land the crafted tip so verify's fetch sees it (force
            # is test setup, never the helper's path)
            git(repo, "push", "-f", "origin", "main")
            return old, new, expected

        def verify(old, new, blob):
            return da.verify_after_push(repo, "origin",
                                        "refs/heads/main", old, new,
                                        da.HELPER_PATH, blob)

        old, new, blob = craft(extra="README.md")
        try:
            verify(old, new, blob)
            raise AssertionError("extra path accepted")
        except da.PostDeployError as e:
            assert "README.md" in str(e), e
        git(repo, "reset", "--hard", old)
        old2, new2, blob2 = craft(skip_helper=True)
        try:
            verify(old2, new2, blob2)
            raise AssertionError("empty deploy accepted")
        except da.PostDeployError as e:
            assert "scope" in str(e), e
        git(repo, "reset", "--hard", old)
        old3, new3, want = craft(wrong=True)
        try:
            verify(old3, new3, want)
            raise AssertionError("wrong blob accepted")
        except da.PostDeployError as e:
            assert "mismatch" in str(e) and want in str(e), e
        git(repo, "reset", "--hard", old)
        old4, new4, _ = craft()
        good = git(repo, "rev-parse", f"{new4}:{da.HELPER_PATH}")
        assert verify(old4, new4, good) == "ok"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_bootstrap_proven_missing():
    tmp = tempfile.mkdtemp()
    try:
        origin, work, sha_a, _, _ = make_repos(tmp, with_archive=False)
        record = os.path.join(tmp, "deploys.jsonl")
        objs = count_objects(work)
        rc, rec = run_deploy(work, record, main_sha=sha_a)
        assert rc == 2 and rec["result"] == "bootstrap-required", rec
        assert "ls-remote proves" in rec["detail"], rec["detail"]
        assert count_objects(work) == objs, \
            "bootstrap path created a commit object"
        assert rec["new_archive_sha"] is None, rec
        assert len(read_record(record)) == 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_rewind_race_lease_rejects():
    tmp = tempfile.mkdtemp()
    try:
        origin, work, sha_a, _, _ = make_repos(tmp)
        record = os.path.join(tmp, "deploys.jsonl")
        held = {}

        def race(state, real, repo, remote, new_sha, ref, exp_old):
            if state["n"] == 1:
                held["rewound"] = competitor_rewind(tmp, origin,
                                                    "t10")
            return real(repo, remote, new_sha, ref, exp_old)
        wrapper, real, _ = wrap_push(race)
        da.push_cas = wrapper
        try:
            rc, rec = run_deploy(work, record, main_sha=sha_a)
        finally:
            da.push_cas = real
        assert rc == 0 and rec["result"] == "deployed", rec
        assert rec["attempts"] == 2, rec
        tip = remote_tip(origin)
        # the landing was rebuilt on the REWOUND parent, not the
        # originally read value
        assert git(origin, "rev-parse", f"{tip}^") == held["rewound"]
        log = git(origin, "log", "--format=%an", "archive")
        assert log.count("borsagator-deploy") == 1, log
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_lost_response_reconciled():
    tmp = tempfile.mkdtemp()
    try:
        origin, work, sha_a, _, _ = make_repos(tmp)
        record = os.path.join(tmp, "deploys.jsonl")

        def lost(state, real, repo, remote, new_sha, ref, exp_old):
            out = real(repo, remote, new_sha, ref, exp_old)
            assert out[0], "test setup: the push must actually land"
            return False, "simulated lost response"
        wrapper, real, _ = wrap_push(lost)
        da.push_cas = wrapper
        try:
            rc, rec = run_deploy(work, record, main_sha=sha_a)
        finally:
            da.push_cas = real
        assert rc == 0 and rec["result"] == "deployed", rec
        assert rec["attempts"] == 1, rec
        assert "reconciled" in rec, rec
        assert remote_tip(origin) == rec["new_archive_sha"]
        log = git(origin, "log", "--format=%an", "archive")
        assert log.count("borsagator-deploy") == 1, log
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_lost_response_plus_late_mover():
    tmp = tempfile.mkdtemp()
    try:
        origin, work, sha_a, blob_v1, _ = make_repos(tmp)
        record = os.path.join(tmp, "deploys.jsonl")

        def lost(state, real, repo, remote, new_sha, ref, exp_old):
            out = real(repo, remote, new_sha, ref, exp_old)
            assert out[0]
            competitor_commit(tmp, origin, "t12")
            return False, "simulated lost response"
        wrapper, real, _ = wrap_push(lost)
        da.push_cas = wrapper
        try:
            rc, rec = run_deploy(work, record, main_sha=sha_a)
        finally:
            da.push_cas = real
        # reconcile finds the landed commit, then the STRICT
        # assert goes red on the late mover, naming the observed tip
        assert rc == 1 and rec["result"] == "verify-failed", rec
        assert "reconciled" in rec, rec
        tip = remote_tip(origin)
        assert tip in rec["detail"] and \
            rec["new_archive_sha"] in rec["detail"], rec["detail"]
        assert git(origin, "rev-parse",
                   f"{tip}:{da.HELPER_PATH}") == blob_v1
        log = git(origin, "log", "--format=%an", "archive")
        assert log.count("borsagator-deploy") == 1, log
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_non_contention_rejection_no_retry():
    tmp = tempfile.mkdtemp()
    try:
        origin, work, sha_a, _, _ = make_repos(tmp)
        record = os.path.join(tmp, "deploys.jsonl")

        def reject(state, real, repo, remote, new_sha, ref, exp_old):
            return False, "simulated protected-branch rejection"
        wrapper, real, state = wrap_push(reject)
        da.push_cas = wrapper
        try:
            rc, rec = run_deploy(work, record, main_sha=sha_a)
        finally:
            da.push_cas = real
        assert rc == 1 and rec["result"] == "push-rejected", rec
        assert rec["attempts"] == 1, rec
        assert state["n"] == 1, "non-contention must not retry"
        assert "NOT observed ref contention" in rec["detail"] and \
            "protected-branch rejection" in rec["detail"], \
            rec["detail"]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_unreachable_remote_is_error_not_bootstrap():
    tmp = tempfile.mkdtemp()
    try:
        origin, work, sha_a, _, _ = make_repos(tmp)
        git(work, "remote", "set-url", "origin",
            os.path.join(tmp, "does-not-exist.git"))
        record = os.path.join(tmp, "deploys.jsonl")
        rc, rec = run_deploy(work, record, main_sha=sha_a)
        assert rc == 1 and rec["result"] == "error", rec
        assert "ls-remote probe" in rec["detail"], rec["detail"]
        # error records still carry the SHA keys, null when unknown
        for k in ("main_sha", "main_blob", "old_archive_sha",
                  "new_archive_sha"):
            assert k in rec and rec[k] is None, rec
        assert len(read_record(record)) == 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def run_parity(work, *args):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), \
            contextlib.redirect_stderr(err):
        rc = bp.main(["--repo-dir", work, *args])
    return rc, out.getvalue(), err.getvalue()


def test_parity_output_and_all_three():
    tmp = tempfile.mkdtemp()
    try:
        origin, work, sha_a, blob_v1, blob_v1b = make_repos(tmp)
        # drift: main tip v1b vs archive v0; captured diagnostics
        rc, out, err = run_parity(work)
        assert rc == 1, (rc, out, err)
        b_arch = git(work, "rev-parse", f"origin/archive:"
                                        f"{da.HELPER_PATH}")
        assert "origin/main" in err and "origin/archive" in err, err
        assert blob_v1b in err and b_arch in err, err
        # green after an unpinned deploy (source selection recorded)
        record = os.path.join(tmp, "deploys.jsonl")
        rc2, rec = run_deploy(work, record)
        assert rc2 == 0 and rec["source"]["pinned"] is False, rec
        main_tip = git(work, "rev-parse", "origin/main")
        assert rec["source"]["sha"] == main_tip, rec
        rc3, out3, err3 = run_parity(work)
        assert rc3 == 0 and "PARITY OK" in out3, (rc3, out3, err3)
        # missing blob is red and says MISSING
        rc4, out4, err4 = run_parity(work, "--path",
                                     "scripts/nope.py")
        assert rc4 == 1 and "MISSING" in out4, (rc4, out4, err4)
        # opt-in all-three: worker-release (v1) now drifts from the
        # deployed v1b, so red and names worker-release
        rc5, out5, err5 = run_parity(
            work, "--refs", "origin/main", "origin/worker-release",
            "origin/archive")
        assert rc5 == 1 and "origin/worker-release" in err5, \
            (rc5, out5, err5)
        assert blob_v1 in out5 and blob_v1b in out5, out5
        # all-three green when worker-release matches again
        git(work, "push", "-f", "origin",
            f"{main_tip}:refs/heads/worker-release")
        da.fetch_ref(work, "origin", "refs/heads/worker-release")
        rc6, out6, err6 = run_parity(
            work, "--refs", "origin/main", "origin/worker-release",
            "origin/archive")
        assert rc6 == 0, (rc6, out6, err6)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_preflight_blocks_bad_commit_before_push():
    tmp = tempfile.mkdtemp()
    try:
        origin, work, sha_a, _, _ = make_repos(tmp)
        record = os.path.join(tmp, "deploys.jsonl")
        tip_before = remote_tip(origin)
        calls = {"push": 0}
        real_verify = da.verify_commit_scope
        real_push = da.push_cas

        def bad_verify(repo, old, new, path, expected_blob):
            raise da.PostDeployError("injected malformed commit")
        def counting_push(*a, **k):
            calls["push"] += 1
            return real_push(*a, **k)
        da.verify_commit_scope = bad_verify
        da.push_cas = counting_push
        try:
            rc, rec = run_deploy(work, record, main_sha=sha_a)
        finally:
            da.verify_commit_scope = real_verify
            da.push_cas = real_push
        assert rc == 1 and rec["result"] == "preflight-failed", rec
        assert "on attempt 1 BEFORE that attempt's push" in \
            rec["detail"], rec["detail"]
        assert calls["push"] == 0, "preflight must precede any push"
        assert remote_tip(origin) == tip_before, \
            "preflight failure changed the remote"
        assert len(read_record(record)) == 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_symbolic_main_sha_rejected():
    tmp = tempfile.mkdtemp()
    try:
        origin, work, sha_a, _, _ = make_repos(tmp)
        record = os.path.join(tmp, "deploys.jsonl")
        tip_before = remote_tip(origin)
        for bad in ("main", sha_a[:12], "HEAD"):
            rc, rec = run_deploy(work, record, main_sha=bad)
            assert rc == 1 and rec["result"] == "error", (bad, rec)
            assert "full 40-hex" in rec["detail"], (bad, rec)
        assert remote_tip(origin) == tip_before, \
            "a symbolic source caused an effect"
        # exactly the 3 error runs were recorded
        assert len(read_record(record)) == 3
        # an uppercase full 40-hex is accepted and canonicalized:
        # the main_sha variable itself, not only source.sha
        rc, rec = run_deploy(work, record, main_sha=sha_a.upper())
        assert rc == 0 and rec["result"] == "deployed", rec
        assert rec["main_sha"] == sha_a, rec
        assert rec["source"]["sha"] == sha_a, rec
        assert len(read_record(record)) == 4
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_record_write_failure_after_landing():
    tmp = tempfile.mkdtemp()
    try:
        origin, work, sha_a, _, _ = make_repos(tmp)
        record = os.path.join(tmp, "deploys.jsonl")

        def boom(path, line):
            raise OSError("simulated disk full")
        real = da._append_record
        da._append_record = boom
        try:
            rc, rec = run_deploy(work, record, main_sha=sha_a)
        finally:
            da._append_record = real
        # nonzero, actual result retained, landed state real
        assert rc == 1, rec
        assert rec["result"] == "deployed", rec
        assert rec["record_write_failed"] is True, rec
        assert remote_tip(origin) == rec["new_archive_sha"], \
            "the deploy really landed; only the record failed"
        assert not os.path.exists(record) or \
            len(read_record(record)) == 0, "append must have failed"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_push_timeout_after_landing_reconciled():
    tmp = tempfile.mkdtemp()
    try:
        origin, work, sha_a, _, _ = make_repos(tmp)
        record = os.path.join(tmp, "deploys.jsonl")

        def timeout_landed(state, real, repo, remote, new_sha, ref,
                           exp_old):
            # the push really lands (direct call, no wrapper
            # semantics), but the caller hears a timeout
            p = subprocess.run(
                ["git", "-C", repo, "push",
                 f"--force-with-lease={ref}:{exp_old}",
                 remote, f"{new_sha}:{ref}"],
                capture_output=True, text=True)
            assert p.returncode == 0, p.stderr
            return False, "git push exceeded 120s"
        wrapper, real, _ = wrap_push(timeout_landed)
        da.push_cas = wrapper
        try:
            rc, rec = run_deploy(work, record, main_sha=sha_a)
        finally:
            da.push_cas = real
        assert rc == 0 and rec["result"] == "deployed", rec
        assert rec["attempts"] == 1 and "reconciled" in rec, rec
        assert remote_tip(origin) == rec["new_archive_sha"]
        log = git(origin, "log", "--format=%an", "archive")
        assert log.count("borsagator-deploy") == 1, log
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_lost_response_plus_read_error_unknown():
    tmp = tempfile.mkdtemp()
    try:
        origin, work, sha_a, _, _ = make_repos(tmp)
        record = os.path.join(tmp, "deploys.jsonl")

        def lost(state, real, repo, remote, new_sha, ref, exp_old):
            out = real(repo, remote, new_sha, ref, exp_old)
            assert out[0], "test setup: the push must actually land"
            return False, "simulated lost response"
        wrapper, real_push, _ = wrap_push(lost)
        da.push_cas = wrapper
        real_fetch = da.fetch_ref
        calls = {"n": 0}

        def flaky_fetch(repo, remote, ref):
            # the pre-attempt fetches of main and archive succeed;
            # the reconciliation re-read after the push fails
            calls["n"] += 1
            if calls["n"] > 2:
                raise da.DeployError("simulated re-read failure")
            return real_fetch(repo, remote, ref)
        da.fetch_ref = flaky_fetch
        try:
            rc, rec = run_deploy(work, record, main_sha=sha_a)
        finally:
            da.push_cas = real_push
            da.fetch_ref = real_fetch
        # nonzero unknown; the attempt metadata survives even though
        # the reconciliation re-read failed
        assert rc == 1 and rec["result"] == "unknown", rec
        assert rec["new_archive_sha"] is None, rec
        assert len(rec["attempts_detail"]) == 1, rec
        att = rec["attempts_detail"][0]
        assert att["push"] == "failed" and att["error"], att
        assert att["expected_old"], att
        assert att["observed_tip"] is None, att
        attempted = att["sha"]
        assert attempted, att
        # test setup check: the commit whose fate is unknown in the
        # record is the one that really landed on the remote
        assert remote_tip(origin) == attempted
        lines = read_record(record)
        assert len(lines) == 1 and \
            lines[0]["attempts_detail"][0]["sha"] == attempted, lines
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    check("T1 fresh deploy, pinned source: atomic move, scope, "
          "record links SHAs", test_fresh_deploy_pinned)
    check("T2 pinned source ships the pinned blob, not main tip",
          test_pinned_source_not_main_tip)
    check("T3 idempotent re-run: content noop, zero new objects",
          test_idempotent_rerun)
    check("T4 CAS race vs child commit: rejected, rebuilt, one "
          "deploy commit, green", test_cas_race_child_retry_lands)
    check("T5 CAS exhaustion: red, reconciled each time, remote "
          "checked empty of deploys",
          test_cas_exhaustion_reconciled_red)
    check("T6 late mover after landing: STRICT red naming "
          "expected and observed tip, no repair",
          test_late_mover_after_landing_is_red)
    check("T7 late mover rewriting helper: verify-failed, SHAs "
          "named, no repair", test_late_mover_rewriting_helper_is_red)
    check("T8 verify scope + blob content asserts",
          test_verify_scope_and_blob)
    check("T9 rewind race: lease rejects a plain-push-acceptable "
          "rewind, retry lands on rewound parent",
          test_rewind_race_lease_rejects)
    check("T10 lost response: reconcile finds the landed commit, "
          "deployed, one attempt", test_lost_response_reconciled)
    check("T11 lost response + late mover: reconciled, then "
          "STRICT red naming both SHAs",
          test_lost_response_plus_late_mover)
    check("T12 non-contention rejection: red, one attempt, server "
          "message retained", test_non_contention_rejection_no_retry)
    check("T13 unreachable remote: error, never bootstrap, null-SHA "
          "record written",
          test_unreachable_remote_is_error_not_bootstrap)
    check("T14 parity: captured diagnostics name refs and blobs; "
          "opt-in all-three both ways", test_parity_output_and_all_three)
    check("T15 preflight: bad commit blocked before any push, "
          "remote unchanged", test_preflight_blocks_bad_commit_before_push)
    check("T16 symbolic --main-sha rejected before any effect",
          test_symbolic_main_sha_rejected)
    check("T17 record write failure after landing: nonzero, result "
          "retained, landed state real",
          test_record_write_failure_after_landing)
    check("T18 push timeout after landing: reconciled, deployed, "
          "one attempt", test_push_timeout_after_landing_reconciled)
    check("T19 lost response + reconciliation read error: nonzero "
          "unknown, attempt SHA preserved",
          test_lost_response_plus_read_error_unknown)
    failed = [r for r in RESULTS if not r[1]]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
