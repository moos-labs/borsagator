#!/usr/bin/env python3
"""Regression tests for issue #390 (INS-383 follow-up, #382):
update_checkout_sha() is unguarded — a git timeout/OSError blocks
publish + done.

Gap (issue body): worker/worker.py update_checkout_sha() calls
sh(f"git -C {CODE} rev-parse HEAD", timeout=30) with no try/except;
sh() is subprocess.run(..., timeout=...) which RAISES
subprocess.TimeoutExpired on timeout (and OSError if git is
missing). A raise at the #385 manifest-creation site in
_execute_body — after intent persistence — blocks publish + done,
leaving the job uncertain. Same exposure at the heartbeat manifest
site, the render-arg sites (maybe_merge / compile hook) and
self_update.

Fix under test: update_checkout_sha() guards the lookup and returns
"" on TimeoutExpired/OSError (and on a non-zero exit / empty output,
as before), so publication proceeds with code_sha intact.
checkout_sha is diagnostics only (#382) — a failed diagnostic
lookup must never become a job failure.

Harness-first: FAILS on pristine main (the TimeoutExpired /
OSError escapes update_checkout_sha() out of _execute_body, so no
manifest is published and no done is marked) and PASSES on the
fixed tree. Stdlib only. publish/_mark_done are stubbed at the
worker-module boundary while _execute_body itself runs for real;
git/network are stubbed (fake sh with a switchable failure mode).
Manifest paths covered, per Ins: ordinary (unknown job),
special-dispatch (harvest-egx bad-code, top30-enumerate bad-job)
and invalid-job (non-string job) — each under a simulated git
timeout and (for the ordinary + harvest paths) under missing git.

Run: python3 worker/test_worker_390.py (exit 0 = all pass).
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="gator390-test-"))
os.environ["GATOR_ROOT"] = str(_TMP)

_HERE = Path(os.path.abspath(__file__)).parent
_REPO = _HERE.parent
sys.path.insert(0, str(_HERE))

import worker  # noqa: E402

PASSED = 0
PUBLISH_SEEN = {}
MARK_DONE_SEEN = {}
FAKE_MODE = {"mode": "timeout"}


def check(name, cond):
    global PASSED
    assert cond, name
    PASSED += 1
    print(f"pass: {name}")


class FakeResult:
    def __init__(self, rc=0, out="", err=""):
        self.returncode = rc
        self.stdout = out
        self.stderr = err


def fake_sh(cmd, cwd=None, env=None, timeout=3600):
    """Fake worker.sh: perform `rm -rf` for real; the git checkout
    lookup fails per FAKE_MODE ("timeout": TimeoutExpired,
    "missing-git": FileNotFoundError, "nonzero": exit 1, "ok":
    a SHA); everything else succeeds with empty output."""
    if cmd.startswith("rm -rf "):
        shutil.rmtree(cmd[len("rm -rf "):].strip(), ignore_errors=True)
        return FakeResult(0)
    if "rev-parse HEAD" in cmd:
        mode = FAKE_MODE["mode"]
        if mode == "timeout":
            raise subprocess.TimeoutExpired(cmd, timeout)
        if mode == "missing-git":
            raise FileNotFoundError(2, "No such file or directory",
                                    "git")
        if mode == "nonzero":
            return FakeResult(1, out="", err="fatal: not a git repo")
        if mode == "ok":
            return FakeResult(0, out="abc123def4567890\n")
        raise AssertionError(f"unknown FAKE_MODE {mode!r}")
    return FakeResult(0)


def setup_release():
    """Fake release checkout: a minimal registry with one active
    tool (registry() reads it before parse_job runs)."""
    code = worker.CODE
    (code / "registry").mkdir(parents=True, exist_ok=True)
    (code / "registry" / "tools.json").write_text(json.dumps({
        "tools": [{"id": "vectorbt", "status": "active",
                   "category": "technical", "markets": ["EGX"],
                   "command": "echo {ticker}",
                   "ref": "0" * 40,
                   "repo": "vectorbt-runner"}]}),
        encoding="utf-8")


def stub_publish(job, results_dir, manifest):
    PUBLISH_SEEN.clear()
    PUBLISH_SEEN["job"] = job
    PUBLISH_SEEN["manifest"] = json.loads(json.dumps(manifest))
    return "fake-archive-sha-390"


def stub_mark_done(job, archive_sha):
    MARK_DONE_SEEN.clear()
    MARK_DONE_SEEN["job"] = job
    MARK_DONE_SEEN["archive_sha"] = archive_sha


def run_execute(job):
    PUBLISH_SEEN.clear()
    MARK_DONE_SEEN.clear()
    worker._execute_body(job)
    return PUBLISH_SEEN, MARK_DONE_SEEN


def check_published_with_empty_checkout(pub, done, name):
    """Shared assertions: the run published + marked done, the
    manifest carries an empty checkout_sha (the failed lookup
    degraded, it did not block the job), and code_sha — the
    running-code pin — is intact."""
    manifest = pub.get("manifest", {})
    check(f"{name}: still publishes + marks done-with-failure",
          manifest is not None
          and done.get("archive_sha") == "fake-archive-sha-390")
    check(f"{name}: checkout_sha is empty (failed lookup "
          "degraded, never a job failure)",
          manifest.get("checkout_sha") == "")
    check(f"{name}: code_sha remains the running-code pin",
          manifest.get("code_sha") == worker.running_code_sha()
          and bool(manifest.get("code_sha"))
          and manifest.get("code_sha_kind") == "sha256-running-bytes")


def test_update_checkout_sha_timeout_returns_empty():
    FAKE_MODE["mode"] = "timeout"
    check("update_checkout_sha(): git timeout returns '' instead "
          "of raising TimeoutExpired",
          worker.update_checkout_sha() == "")


def test_update_checkout_sha_missing_git_returns_empty():
    FAKE_MODE["mode"] = "missing-git"
    check("update_checkout_sha(): missing git returns '' instead "
          "of raising OSError",
          worker.update_checkout_sha() == "")


def test_update_checkout_sha_nonzero_returns_empty():
    FAKE_MODE["mode"] = "nonzero"
    check("update_checkout_sha(): non-zero git exit still "
          "returns '' (pre-existing behaviour)",
          worker.update_checkout_sha() == "")


def test_update_checkout_sha_success_still_reports_sha():
    FAKE_MODE["mode"] = "ok"
    check("update_checkout_sha(): a working git still reports "
          "the checkout HEAD, stripped",
          worker.update_checkout_sha() == "abc123def4567890")


def test_ordinary_unknown_job_publishes_on_git_timeout():
    FAKE_MODE["mode"] = "timeout"
    pub, done = run_execute({
        "id": "test-390-unknown",
        "job": "harvest-egx-poul",
        "added": worker.now()})
    check("ordinary unknown job 'harvest-egx-poul' on git "
          "timeout: named unknown-job failure, never a raise "
          "out of _execute_body",
          pub.get("manifest", {}).get("tools")
          == {"unknown-job": "unknown-job"})
    check_published_with_empty_checkout(
        pub, done, "ordinary unknown job 'harvest-egx-poul' on "
        "git timeout")


def test_special_dispatch_harvest_publishes_on_git_timeout():
    FAKE_MODE["mode"] = "timeout"
    pub, done = run_execute({
        "id": "test-390-harvest",
        "job": "harvest-egx",
        "added": worker.now()})
    check("special-dispatch 'harvest-egx' (bad code) on git "
          "timeout: named egx-harvest bad-code failure, never a "
          "raise out of _execute_body",
          pub.get("manifest", {}).get("tools")
          == {"egx-harvest": "bad-code"})
    check_published_with_empty_checkout(
        pub, done, "special-dispatch 'harvest-egx' on git timeout")


def test_special_dispatch_top30_publishes_on_git_timeout():
    FAKE_MODE["mode"] = "timeout"
    pub, done = run_execute({
        "id": "test-390-top30",
        "job": "top30-enumerate --bogus",
        "added": worker.now()})
    check("special-dispatch 'top30-enumerate --bogus' (bad job) "
          "on git timeout: named top30-enumerate bad-job failure, "
          "never a raise out of _execute_body",
          pub.get("manifest", {}).get("tools")
          == {"top30-enumerate": "bad-job"})
    check_published_with_empty_checkout(
        pub, done, "special-dispatch 'top30-enumerate --bogus' on "
        "git timeout")


def test_invalid_job_type_publishes_on_git_timeout():
    FAKE_MODE["mode"] = "timeout"
    pub, done = run_execute({
        "id": "test-390-type",
        "job": 123,
        "added": worker.now()})
    check("invalid-job-type (non-string job 123) on git timeout: "
          "named invalid-job-type failure, never a raise out of "
          "_execute_body",
          pub.get("manifest", {}).get("tools")
          == {"invalid-job-type": "invalid-job-type"})
    check_published_with_empty_checkout(
        pub, done, "invalid-job-type (non-string job 123) on git "
        "timeout")


def test_ordinary_unknown_job_publishes_on_missing_git():
    FAKE_MODE["mode"] = "missing-git"
    pub, done = run_execute({
        "id": "test-390-unknown-nogit",
        "job": "harvest-egx-poul",
        "added": worker.now()})
    check("ordinary unknown job 'harvest-egx-poul' with git "
          "missing: named unknown-job failure, never a raise "
          "out of _execute_body",
          pub.get("manifest", {}).get("tools")
          == {"unknown-job": "unknown-job"})
    check_published_with_empty_checkout(
        pub, done, "ordinary unknown job 'harvest-egx-poul' with "
        "git missing")


def test_special_dispatch_harvest_publishes_on_missing_git():
    FAKE_MODE["mode"] = "missing-git"
    pub, done = run_execute({
        "id": "test-390-harvest-nogit",
        "job": "harvest-egx",
        "added": worker.now()})
    check("special-dispatch 'harvest-egx' (bad code) with git "
          "missing: named egx-harvest bad-code failure, never a "
          "raise out of _execute_body",
          pub.get("manifest", {}).get("tools")
          == {"egx-harvest": "bad-code"})
    check_published_with_empty_checkout(
        pub, done, "special-dispatch 'harvest-egx' with git "
        "missing")


def test_heartbeat_survives_git_timeout():
    """The heartbeat manifest site: a git timeout must not raise
    out of heartbeat() — the heartbeat still lands, with an empty
    checkout_sha and the running-code pin intact."""
    FAKE_MODE["mode"] = "timeout"
    worker.push_bus = lambda message: True
    # The real worker always has BUS (sync_bus clones it); the
    # test's temp GATOR_ROOT does not — create it first.
    worker.BUS.mkdir(parents=True, exist_ok=True)
    worker.heartbeat()
    payload = json.loads(
        (worker.BUS / "queue" / "heartbeat.json").read_text())
    check("heartbeat on git timeout: heartbeat.json is written",
          payload.get("worker") == os.uname().nodename)
    check("heartbeat on git timeout: checkout_sha is empty",
          payload.get("checkout_sha") == "")
    check("heartbeat on git timeout: code_sha remains the "
          "running-code pin",
          payload.get("code_sha") == worker.running_code_sha()
          and payload.get("code_sha_kind") == "sha256-running-bytes")


def main():
    worker.sh = fake_sh
    worker.publish = stub_publish
    worker._mark_done = stub_mark_done
    setup_release()
    test_update_checkout_sha_timeout_returns_empty()
    test_update_checkout_sha_missing_git_returns_empty()
    test_update_checkout_sha_nonzero_returns_empty()
    test_update_checkout_sha_success_still_reports_sha()
    test_ordinary_unknown_job_publishes_on_git_timeout()
    test_special_dispatch_harvest_publishes_on_git_timeout()
    test_special_dispatch_top30_publishes_on_git_timeout()
    test_invalid_job_type_publishes_on_git_timeout()
    test_ordinary_unknown_job_publishes_on_missing_git()
    test_special_dispatch_harvest_publishes_on_missing_git()
    test_heartbeat_survives_git_timeout()
    print(f"\n{PASSED} passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
