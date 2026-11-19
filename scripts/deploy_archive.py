#!/usr/bin/env python3
"""Atomic, idempotent archive deploy of the digest helper (issue #232).

The gap (panel round 13, verified): the one-off deploy scripts
(hidden_files/deploy_216_fix.py, deploy_223_fix.py) created the
archive commit object through the Git Data API but never moved the
branch ref atomically. On the #223 deploy the commit 610cbfd
existed while refs/heads/archive still read 2f7248a; only the
read-back assert noticed, and a manual PATCH repaired it. Detection
is not prevention: a create-then-report-success path can leave a
dangling commit and a stale branch while claiming the deploy worked.

This helper is the reusable replacement. The guarantee it gives:

1. EXACT COMPARE-AND-SWAP REF MOVE. The deploy commit is built with
   plumbing (read-tree / update-index --cacheinfo / write-tree /
   commit-tree) with its parent pinned to the ref value OLD read at
   fetch time, then moved with
   git push --force-with-lease=REF:OLD NEW:REF.
   The lease makes the server reject the move unless the ref equals
   OLD at move time. A plain non-forced push is NOT enough: it only
   requires the remote to be an ancestor of NEW, so a remote rewound
   to an ancestor of OLD (or rewritten to share one) would still
   accept NEW while no longer reading OLD. The lease is exact. It is
   also never an actual force here: when the lease matches, NEW is a
   fast-forward of OLD by construction. On rejection the helper
   reconciles (see 2), rebuilds on the new parent and retries,
   bounded by --max-attempts; contention exhaustion is red, never a
   force-push.
2. LOST-RESPONSE RECONCILIATION. A failed push can still have
   LANDED (response lost after the server moved the ref), so a
   nonzero exit proves nothing by itself; a push TIMEOUT is the
   same class and is reconciled identically. After every failed
   push the remote is re-fetched: if NEW is the tip or an ancestor
   of it, the deploy landed and the run proceeds to verification
   instead of retrying. Otherwise all that is known is
   reachability: NEW is not reachable from the OBSERVED tip (it
   could have landed and been rewritten away), and the record says
   exactly that, retaining each attempt's SHA, the server message
   and the last observed head for manual reconciliation. A tip
   that moved since OLD is observed ref contention (retry); a tip
   that still equals OLD is NOT contention (transport, protection
   or auth) and is red without retry. No claim about what a failed
   push did is ever made from the exit code alone. Each attempt is
   recorded BEFORE its push (attempted SHA and expected OLD, then
   the push result), so when the push AND the reconciliation
   re-read both fail, the run is nonzero with result "unknown"
   and the attempted SHA, expected OLD and push error still
   survive in the record with the observed tip null.
3. PREFLIGHT BEFORE EFFECT. The deploy commit's scope and content
   are asserted LOCALLY before any push (verify_commit_scope on the
   built commit), so a malformed deploy commit can never be
   published and then merely detected. The post-deploy assert (4)
   stays: preflight proves what we built, the post-assert proves
   what the remote actually holds.
4. IDEMPOTENCE. The no-op test is CONTENT-based: if the archive
   tip's helper blob already equals the source blob, the deploy is
   a no-op (result "noop", exit 0) and NO commit object is created.
   Worker data commits landing on top of a deploy do not defeat
   this, because blobs are compared, not commit SHAs. The same
   check runs after every lost race: if the competing writer
   already deployed the same blob, the run is a noop, not an error.
5. POST-DEPLOY ASSERT, STRICT EQUALITY. After the move lands,
   the remote is re-fetched and the ref must read EXACTLY NEW;
   git diff OLD..NEW --name-only must be exactly the helper path;
   the helper blob at NEW must equal the source blob. Any other
   observed tip, even a benign data commit landing a second
   later, is red verify-failed naming the expected SHA and the
   exact observed tip. No success is reported on any other
   evidence, and the helper never repairs by force.
6. SOURCE PINNING. The source of the deploy is an immutable
   COMMIT SHA, not a moving branch or rev: --main-sha must be a
   full 40-hex commit SHA (for the #229 helper promotion, the
   reviewed merge SHA) and anything else is rejected before any
   effect. The canonical SHA is resolved once and recorded.
   Without --main-sha the fetched tip of --main-ref is used and
   the record says so (source.pinned false). Either way the record
   carries the exact source SHA deployed; there is no silent
   "whatever main says".
7. DEPLOYMENT RECORD. Every run, including every error path,
   appends one JSON line to --record (default
   hidden_files/deploys.jsonl under --repo-dir; the parent
   directory is created) and prints the same line on stdout for the
   workflow log. The destination is preflighted (created and
   append-opened once) BEFORE any effect, so a missing directory
   or unwritable path fails the run before anything is pushed;
   that early check is not a proof the disk accepts the append
   later. SHA fields are always present and null when unknown.
   Results: deployed, noop, cas-exhausted, push-rejected,
   preflight-failed, verify-failed, bootstrap-required, unknown
   (push and reconciliation re-read both failed; whether the
   deploy landed is undetermined), error. If
   the append itself fails after an effect, the run goes nonzero
   with record_write_failed true on the printed record: the
   actual result is retained and the stdout line is the surviving
   evidence.

Durability limits, stated plainly: the record is a local append
log, not a distributed ledger. A crash between the push landing
and the append can lose that run's line, and disk failure can
lose the file; the post-deploy assert on the next run is the
backstop, because it re-reads the remote rather than trusting the
log.

Bootstrap is PROVEN, not inferred: the remote ref is probed with
git ls-remote --exit-code; exit 2 means the branch genuinely does
not exist (bootstrap-required, exit 2), while any other probe or
fetch failure (network, auth) is result "error" (exit 1) with the
stderr retained, never mislabeled as a missing branch. Every git
call is bounded by a 120-second timeout; a timeout is result
"error", not a hang.

What this does NOT claim: the lease CAS prevents stale-parent and
rewind-overwrite deploys, and reconciliation prevents double
deploys on lost responses, but the archive branch still takes
ordinary worker data commits from orchestrate.yml; the post-deploy
assert and the "moved" classification exist because the ref can
legitimately move again the instant after a landing. Rejected
attempts leave their locally built deploy commits as temporary
unreachable objects in the local clone until git gc; what is
guaranteed is that the remote never carries them and that no run
reports success on unverified evidence.

Stdlib only; requires git on PATH. Exit codes: 0 deployed/noop,
1 red (contention exhaustion, non-contention rejection, preflight
or post-deploy assert failure, operational error), 2 bootstrap
needed.

Usage:
  python3 scripts/deploy_archive.py --repo-dir . \
      --main-sha REVIEWED_SHA [--record hidden_files/deploys.jsonl]
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import time

HELPER_PATH = "scripts/worker_digest_issue.py"
ARCHIVE_REF = "refs/heads/archive"
MAIN_REF = "refs/heads/main"
DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_RECORD = os.path.join("hidden_files", "deploys.jsonl")
GIT_TIMEOUT = 120


class DeployError(Exception):
    """A git operation failed or a deploy precondition is unmet."""


class PostDeployError(DeployError):
    """The post-deploy assert failed after a landed move."""


class PreflightError(DeployError):
    """A local check failed before any remote effect."""


def run_git(repo, *args, env_extra=None, check=True):
    env = dict(os.environ)
    env.setdefault("GIT_AUTHOR_NAME", "borsagator-deploy")
    env.setdefault("GIT_AUTHOR_EMAIL", "<mailto:moos@sherbeeny.com|moos@sherbeeny.com>")
    env.setdefault("GIT_COMMITTER_NAME", "borsagator-deploy")
    env.setdefault("GIT_COMMITTER_EMAIL", "<mailto:moos@sherbeeny.com|moos@sherbeeny.com>")
    if env_extra:
        env.update(env_extra)
    try:
        p = subprocess.run(["git", "-C", repo, *args], env=env,
                           capture_output=True, text=True,
                           timeout=GIT_TIMEOUT)
    except subprocess.TimeoutExpired:
        raise DeployError(
            f"git {' '.join(args)} exceeded {GIT_TIMEOUT}s")
    if check and p.returncode != 0:
        raise DeployError(
            f"git {' '.join(args)} failed: {p.stderr.strip()}")
    return p


def _branch(ref):
    return ref.split("/", 2)[-1]


def _tracking(remote, ref):
    return f"refs/remotes/{remote}/{_branch(ref)}"


def fetch_ref(repo, remote, ref):
    """Fetch one remote branch into its tracking ref."""
    run_git(repo, "fetch", remote,
            f"+{ref}:{_tracking(remote, ref)}")


def remote_ref_exists(repo, remote, ref):
    """True/false only when the probe is conclusive.

    ls-remote --exit-code exits 2 when the ref does not exist; that
    is proof of absence. Any other failure (network, auth, server)
    is inconclusive and raises instead of guessing.
    """
    p = run_git(repo, "ls-remote", "--exit-code", remote, ref,
                check=False)
    if p.returncode == 0:
        return True
    if p.returncode == 2:
        return False
    raise DeployError(
        f"ls-remote probe of {ref} on {remote} failed "
        f"(exit {p.returncode}); cannot prove the branch exists or "
        f"is missing: {p.stderr.strip()}")


def read_ref(repo, refname):
    """Resolve a ref to a SHA, or None when it does not exist."""
    p = run_git(repo, "rev-parse", "--verify", "--quiet", refname,
                check=False)
    out = p.stdout.strip()
    return out if p.returncode == 0 and out else None


def blob_of(repo, committish, path):
    """Blob SHA of path at committish, or None when absent."""
    p = run_git(repo, "rev-parse", "--verify", "--quiet",
                f"{committish}:{path}", check=False)
    out = p.stdout.strip()
    return out if p.returncode == 0 and out else None


def is_ancestor(repo, maybe_ancestor, tip):
    """True when maybe_ancestor is reachable from tip."""
    if not tip:
        return False
    p = run_git(repo, "merge-base", "--is-ancestor", maybe_ancestor,
                tip, check=False)
    return p.returncode == 0


def build_deploy_commit(repo, parent, blob, path, message,
                        env_extra=None):
    """Commit whose tree is parent's tree with path replaced by blob.

    Returns the new commit SHA. Uses a throwaway index so a dirty
    worktree or concurrent git process cannot corrupt the deploy.
    """
    fd, index = tempfile.mkstemp(prefix="deploy-index-")
    os.close(fd)
    os.unlink(index)  # read-tree requires a nonexistent index path
    env = dict(env_extra or {})
    env["GIT_INDEX_FILE"] = index
    try:
        run_git(repo, "read-tree", f"{parent}^{{tree}}",
                env_extra=env)
        run_git(repo, "update-index", "--cacheinfo",
                f"100644,{blob},{path}", env_extra=env)
        tree = run_git(repo, "write-tree",
                       env_extra=env).stdout.strip()
    finally:
        if os.path.exists(index):
            os.unlink(index)
    return run_git(repo, "commit-tree", tree, "-p", parent,
                   "-m", message, env_extra=env_extra).stdout.strip()


def push_cas(repo, remote, new_sha, ref, expected_old):
    """Move the remote ref to new_sha, exact compare-and-swap.

    --force-with-lease=REF:expected_old makes the server reject
    the move unless the ref equals expected_old at move time: exact
    CAS, including against rewinds and rewrites that a plain
    non-forced push (a mere ancestor check) would silently accept.
    When the lease matches, the move is a fast-forward by
    construction, so no actual forcing occurs. Returns
    (accepted, stderr); accepted=False includes lost responses and
    timeouts, so callers MUST reconcile against a fresh read
    before concluding anything.
    """
    try:
        p = run_git(repo, "push",
                    f"--force-with-lease={ref}:{expected_old}",
                    remote, f"{new_sha}:{ref}", check=False)
    except DeployError as e:
        if "exceeded" in str(e):
            # Timeout: the response is unknown, the push may have
            # landed. Same class as a lost response; reconcile.
            return False, str(e)
        raise
    return p.returncode == 0, p.stderr.strip()


def verify_commit_scope(repo, old, new, path, expected_blob):
    """Assert the deploy commit touches exactly path, carrying the
    expected blob. Raises PostDeployError naming expected/actual."""
    changed = run_git(repo, "diff", "--name-only", f"{old}..{new}"
                      ).stdout.split()
    if changed != [path]:
        raise PostDeployError(
            f"deploy commit scope wrong: expected exactly [{path}], "
            f"got {changed}")
    blob = blob_of(repo, new, path)
    if blob != expected_blob:
        raise PostDeployError(
            f"helper blob mismatch at {new}: expected "
            f"{expected_blob}, got {blob}")


def verify_after_push(repo, remote, ref, old, new, path,
                      expected_blob):
    """Re-read the remote and assert the deploy landed as intended.

    STRICT equality: the observed tip must be exactly NEW, the
    commit's scope exactly the helper path, and the blob exactly
    the source blob. Any other observed tip, even a benign data
    commit landing a second later, is red: raises PostDeployError
    naming the expected SHA and the exact observed tip. Never
    repairs; a red assert is operator signal, not a force-push
    trigger.
    """
    fetch_ref(repo, remote, ref)
    actual = read_ref(repo, _tracking(remote, ref))
    verify_commit_scope(repo, old, new, path, expected_blob)
    if actual == new:
        return "ok"
    relation = ("a later commit landed after the deploy"
                if is_ancestor(repo, new, actual)
                else "the branch was rewritten after the deploy")
    raise PostDeployError(
        f"ref does not read the deploy commit: expected {new}, "
        f"observed tip {actual} ({relation}). Investigate before "
        f"any re-run; do not force-push.")


def preflight_record(record_path):
    """Create the record destination and prove it is appendable.

    Runs BEFORE any remote effect so a bad record path fails the
    deploy before anything is pushed. Raises PreflightError.
    """
    try:
        parent = os.path.dirname(record_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(record_path, "a", encoding="utf-8"):
            pass
    except OSError as e:
        raise PreflightError(
            f"record destination {record_path} is not writable "
            f"({e}); refusing to deploy without a durable record")


def deploy(repo_dir, remote, ref, main_ref, path, record_path,
           max_attempts=DEFAULT_MAX_ATTEMPTS, clock=time.time,
           env_extra=None, main_sha=None):
    """Deploy the source commit's helper blob to the archive ref.

    Returns (rc, record). Every exit path appends and prints the
    record; SHA fields are always present and null when unknown.
    """
    rec = {"ts": clock(), "remote": remote, "ref": ref,
           "path": path, "result": None, "attempts": 0,
           "main_sha": None, "main_blob": None,
           "old_archive_sha": None, "new_archive_sha": None,
           "source": {"sha": main_sha, "pinned": main_sha is not None}}
    repo = repo_dir
    if record_path is None:
        record_path = os.path.join(repo, DEFAULT_RECORD)
    elif not os.path.isabs(record_path):
        record_path = os.path.join(repo, record_path)
    try:
        preflight_record(record_path)
        if not remote_ref_exists(repo, remote, ref):
            rec["result"] = "bootstrap-required"
            rec["detail"] = (f"ls-remote proves {ref} does not "
                             f"exist on {remote}; create the branch "
                             f"once by hand, then re-run.")
            return _finish(rec, record_path, 2)
        fetch_ref(repo, remote, main_ref)
        fetch_ref(repo, remote, ref)
        old = read_ref(repo, _tracking(remote, ref))
        if old is None:
            raise DeployError(
                f"{ref} unreadable locally right after a "
                f"successful fetch from {remote}.")
        if main_sha is None:
            main_sha = read_ref(repo, _tracking(remote, main_ref))
            rec["source"]["sha"] = main_sha
        else:
            # A pinned source must be a full 40-hex commit SHA, not
            # a symbolic rev that could resolve differently later.
            canonical = run_git(
                repo, "rev-parse", "--verify", "--quiet",
                f"{main_sha}^{{commit}}", check=False).stdout.strip()
            if canonical != main_sha.lower() or len(main_sha) != 40:
                rec["result"] = "error"
                rec["detail"] = (
                    f"--main-sha must be a full 40-hex commit SHA "
                    f"of a fetched commit; got {main_sha!r}")
                return _finish(rec, record_path, 1)
            # Canonicalize the variable itself, not only the
            # record field: an uppercase 40-hex input is accepted
            # and every later use (record, message, blob lookup)
            # sees the lowercase canonical SHA.
            main_sha = canonical
            rec["source"]["sha"] = canonical
        main_blob = blob_of(repo, main_sha, path)
        if main_blob is None:
            rec["main_sha"] = main_sha
            rec["result"] = "bootstrap-required"
            rec["detail"] = f"{path} absent at source {main_sha}."
            return _finish(rec, record_path, 2)
        rec["main_sha"] = main_sha
        rec["main_blob"] = main_blob
        rec["old_archive_sha"] = old
        if blob_of(repo, old, path) == main_blob:
            # Idempotence: content match means the deploy already
            # happened. No commit object is created, so a re-run
            # can never leave a dangling commit.
            rec["result"] = "noop"
            rec["new_archive_sha"] = old
            return _finish(rec, record_path, 0)
        message = (f"Deploy {path} from {main_sha[:12]} "
                   f"(issue #232)")
        landed = None
        err = ""
        rec["attempts_detail"] = []
        for attempt in range(1, max_attempts + 1):
            rec["attempts"] = attempt
            new = build_deploy_commit(repo, old, main_blob, path,
                                      message, env_extra=env_extra)
            try:
                verify_commit_scope(repo, old, new, path, main_blob)
            except PostDeployError as e:
                # Preflight: THIS attempt's would-be deploy commit
                # is wrong and this attempt has not pushed. On a
                # later attempt, earlier attempts may already have
                # pushed; their SHAs, errors and observed heads
                # stay retained in attempts_detail.
                rec["result"] = "preflight-failed"
                rec["detail"] = (
                    f"local preflight caught a bad deploy commit "
                    f"on attempt {attempt} BEFORE that attempt's "
                    f"push: {e}")
                return _finish(rec, record_path, 1)
            # Record the attempt BEFORE the push: attempted SHA,
            # expected OLD, then the push result, and after the
            # re-read the observed tip. If the push AND the
            # reconciliation re-read both fail below, this
            # metadata still survives in the record, exactly when
            # it is needed most.
            attempt_rec = {"sha": new, "expected_old": old,
                           "push": None, "error": None,
                           "observed_tip": None}
            rec["attempts_detail"].append(attempt_rec)
            ok, err = push_cas(repo, remote, new, ref, old)
            attempt_rec["push"] = "accepted" if ok else "failed"
            attempt_rec["error"] = None if ok else err
            if ok:
                landed = new
                break
            # A failed push may still have landed (lost response
            # or timeout). Re-read before concluding or retrying.
            try:
                fetch_ref(repo, remote, ref)
                tip = read_ref(repo, _tracking(remote, ref))
            except DeployError as e:
                # Push outcome unknown AND the reconciliation
                # re-read failed: the deploy may or may not have
                # landed. Go nonzero with result "unknown"; the
                # attempt record above retains the attempted SHA,
                # expected OLD and push error, observed tip null.
                rec["result"] = "unknown"
                rec["detail"] = (
                    f"push of deploy commit {new} failed ({err}) "
                    f"and the reconciliation re-read of {ref} "
                    f"also failed ({e}); whether the deploy "
                    f"landed is UNKNOWN. Check manually whether "
                    f"{new} is reachable from {ref} on {remote} "
                    f"before any re-run; do not force-push.")
                return _finish(rec, record_path, 1)
            attempt_rec["observed_tip"] = tip
            if tip == new or is_ancestor(repo, new, tip):
                rec["reconciled"] = (
                    "push reported failure but the re-read shows "
                    "the deploy commit landed")
                landed = new
                break
            # All that is known is reachability from the observed
            # tip; the commit could have landed and been rewritten
            # away. The record keeps the attempt SHA and observed
            # head for manual reconciliation.
            if tip == old:
                rec["result"] = "push-rejected"
                rec["detail"] = (
                    f"the re-read observed {ref} still at the "
                    f"expected old value {old} with deploy commit "
                    f"{new} not reachable from it, so this "
                    f"rejection is NOT observed ref contention; "
                    f"treat as transport, branch protection or "
                    f"auth. Server said: {err}")
                return _finish(rec, record_path, 1)
            # Observed contention: the ref moved and our commit is
            # not reachable from the observed tip. Rebuild on the
            # new parent and retry.
            old = tip
            rec["old_archive_sha"] = old
            if blob_of(repo, old, path) == main_blob:
                rec["result"] = "noop"
                rec["detail"] = ("a competing writer deployed the "
                                 "same blob during the race")
                rec["new_archive_sha"] = old
                return _finish(rec, record_path, 0)
        if landed is None:
            rec["result"] = "cas-exhausted"
            rec["detail"] = (
                f"observed ref contention on every one of "
                f"{max_attempts} attempts; each attempt's deploy "
                f"commit was not reachable from the tip observed on "
                f"its re-read (see attempts_detail for the SHAs and "
                f"observed heads). Last server message: {err}. "
                f"Re-run when writers quiesce.")
            return _finish(rec, record_path, 1)
        rec["new_archive_sha"] = landed
        verify_after_push(repo, remote, ref,
                          rec["old_archive_sha"], landed,
                          path, main_blob)
        rec["result"] = "deployed"
        return _finish(rec, record_path, 0)
    except PostDeployError as e:
        rec["result"] = "verify-failed"
        rec["detail"] = str(e)
        return _finish(rec, record_path, 1)
    except PreflightError as e:
        rec["result"] = "preflight-failed"
        rec["detail"] = str(e)
        return _finish(rec, record_path, 1)
    except DeployError as e:
        rec["result"] = "error"
        rec["detail"] = str(e)
        return _finish(rec, record_path, 1)


def _append_record(record_path, line):
    with open(record_path, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def _finish(rec, record_path, rc):
    # The destination was preflighted before any effect, but that
    # early check is not a disk guarantee. If the append fails now,
    # the run must NOT exit clean: mark the record, keep the actual
    # result, and go nonzero. The printed line is the surviving
    # evidence.
    try:
        _append_record(record_path, json.dumps(rec, sort_keys=True))
    except OSError as e:
        rec["record_write_failed"] = True
        print(f"RECORD WRITE FAILED after the run: {e}",
              file=sys.stderr)
        print(json.dumps(rec, sort_keys=True))
        return (rc if rc != 0 else 1), rec
    print(json.dumps(rec, sort_keys=True))
    return rc, rec


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo-dir", default=".")
    ap.add_argument("--remote", default="origin")
    ap.add_argument("--ref", default=ARCHIVE_REF)
    ap.add_argument("--main-ref", default=MAIN_REF)
    ap.add_argument("--main-sha", default=None,
                    help="Immutable source commit SHA (recommended: "
                         "the reviewed merge SHA). Default: the "
                         "fetched tip of --main-ref, recorded with "
                         "source.pinned false.")
    ap.add_argument("--path", default=HELPER_PATH)
    ap.add_argument("--record", default=None,
                    help="JSONL file appended with one record per "
                         "run. Default: hidden_files/deploys.jsonl "
                         "under --repo-dir. The same record is "
                         "always printed on stdout.")
    ap.add_argument("--max-attempts", type=int,
                    default=DEFAULT_MAX_ATTEMPTS)
    a = ap.parse_args(argv)
    rc, _ = deploy(a.repo_dir, a.remote, a.ref, a.main_ref, a.path,
                   a.record, a.max_attempts, main_sha=a.main_sha)
    return rc


if __name__ == "__main__":
    sys.exit(main())
