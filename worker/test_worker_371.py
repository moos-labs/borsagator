#!/usr/bin/env python3
"""Regression tests for issue #371 (INS-HARV-003 finding 3):
unknown job strings are silently marked done with an empty run.

Live proof (issue body): job `w5-harvest-poul-diag-002` queued with
the job string `harvest-egx-poul` (single token) was claimed
07:51:53Z, done 07:51:58Z (5s), manifest `tools: {}`, started /
finished 49us apart — the harvester never ran, and the job was
still marked done. Root cause: worker/worker.py dispatches on
`(job["job"] or "").split()[:1] == ["harvest-egx"]`; the malformed
string fails that check, fails the other special dispatches, and
falls through to parse_job, which returns [] — and _execute_body
then publishes the empty run as done. The #348 exact-token fix
closed the startswith hole but left this fall-through open.

Fix under test (worker/worker.py, _execute_body):
  * an empty parse_job plan fails closed: the manifest records a
    named `unknown-job` failure (never an empty `tools: {}`), the
    bad job string stays recorded in manifest["job"], and the run
    is published + marked done-with-failure — "done means executed
    + archived", the exact precedent of the harvest-egx bad-code,
    top30-enumerate bad-job and diag-egx-ab bad-job branches
    (issue #216 central handling in _mark_done; no new marking
    channel, no error file — the failure lives in the published
    manifest, as for those siblings).
  * every manifest pins the running code SHA (running_code_sha(),
    same name/kind as the heartbeat), so the exact code behind any
    run — including a no-op — is proven.

Issue #382 (INS-373-374 F4) extends the manifest provenance: the
manifest also carries `checkout_sha` + `update_branch` as separate
diagnostic fields (mirroring the heartbeat). checkout_sha is a
diagnostic only — the checkout HEAD, not proof of the running code
(issue #160); code_sha remains the running-code pin. The fake sh
stub returns empty stdout, so update_checkout_sha() is "" here;
the check asserts the manifest carries exactly what the worker
reports, and that update_branch names the release branch.

Harness-first: FAILS on pristine main (the unknown job publishes
`tools: {}` and marks done; no code_sha in the manifest) and PASSES
on the fixed tree. Stdlib only. publish/_mark_done are stubbed at
the worker-module boundary while _execute_body itself runs for
real; git/network are stubbed (fake sh).

Run: python3 worker/test_worker_371.py (exit 0 = all pass).
"""
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="gator371-test-"))
os.environ["GATOR_ROOT"] = str(_TMP)

_HERE = Path(os.path.abspath(__file__)).parent
_REPO = _HERE.parent
sys.path.insert(0, str(_HERE))

import worker  # noqa: E402

PASSED = 0
PUBLISH_SEEN = {}
MARK_DONE_SEEN = {}


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
    """Fake worker.sh: perform `rm -rf` for real; everything else
    (git, fetch, merge/compile/render hooks) succeeds with empty
    output — the unknown-job path must never reach a tool anyway."""
    if cmd.startswith("rm -rf "):
        shutil.rmtree(cmd[len("rm -rf "):].strip(), ignore_errors=True)
        return FakeResult(0)
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
    return "fake-archive-sha-371"


def stub_mark_done(job, archive_sha):
    MARK_DONE_SEEN.clear()
    MARK_DONE_SEEN["job"] = job
    MARK_DONE_SEEN["archive_sha"] = archive_sha


def run_execute(job):
    PUBLISH_SEEN.clear()
    MARK_DONE_SEEN.clear()
    worker._execute_body(job)
    return PUBLISH_SEEN, MARK_DONE_SEEN


def test_unknown_harvest_string_fails_closed():
    pub, done = run_execute({
        "id": "test-371-poul",
        "job": "harvest-egx-poul",
        "added": worker.now()})
    check("unknown job 'harvest-egx-poul': named unknown-job "
          "failure in the manifest, never an empty tools success",
          pub.get("manifest", {}).get("tools")
          == {"unknown-job": "unknown-job"})
    check("unknown job 'harvest-egx-poul': bad job string recorded "
          "in the manifest",
          pub.get("manifest", {}).get("job", {}).get("job")
          == "harvest-egx-poul")
    check("unknown job 'harvest-egx-poul': still publishes + marks "
          "done-with-failure (done means executed + archived, as "
          "for harvest-egx bad-code)",
          pub.get("manifest") is not None
          and done.get("archive_sha") == "fake-archive-sha-371")
    check("unknown job 'harvest-egx-poul': manifest pins the "
          "running code SHA",
          pub.get("manifest", {}).get("code_sha")
          == worker.running_code_sha()
          and bool(pub.get("manifest", {}).get("code_sha"))
          and pub.get("manifest", {}).get("code_sha_kind")
          == "sha256-running-bytes")


def test_unknown_enumerate_typo_fails_closed():
    pub, done = run_execute({
        "id": "test-371-typo",
        "job": "top30-enumerate-typo",
        "added": worker.now()})
    check("unknown job 'top30-enumerate-typo': named unknown-job "
          "failure in the manifest, never an empty tools success",
          pub.get("manifest", {}).get("tools")
          == {"unknown-job": "unknown-job"})
    check("unknown job 'top30-enumerate-typo': bad job string "
          "recorded in the manifest",
          pub.get("manifest", {}).get("job", {}).get("job")
          == "top30-enumerate-typo")
    check("unknown job 'top30-enumerate-typo': still publishes + "
          "marks done-with-failure",
          done.get("archive_sha") == "fake-archive-sha-371")


def test_empty_job_string_fails_closed():
    pub, done = run_execute({
        "id": "test-371-empty",
        "job": "",
        "added": worker.now()})
    check("empty job string: named unknown-job failure, never an "
          "empty tools success",
          pub.get("manifest", {}).get("tools")
          == {"unknown-job": "unknown-job"})
    check("empty job string: still publishes + marks "
          "done-with-failure",
          done.get("archive_sha") == "fake-archive-sha-371")


def test_unknown_sweep_filter_fails_closed():
    pub, done = run_execute({
        "id": "test-371-filter",
        "job": "sweep-lite POUL market=XX",
        "added": worker.now()})
    check("sweep-lite with an unknown market filter: named "
          "unknown-job failure, never an empty tools success "
          "(parse_job already fails the filter closed; the empty "
          "plan must not publish as done)",
          pub.get("manifest", {}).get("tools")
          == {"unknown-job": "unknown-job"})
    check("sweep-lite with an unknown market filter: still "
          "publishes + marks done-with-failure",
          done.get("archive_sha") == "fake-archive-sha-371")


def test_manifest_carries_checkout_provenance():
    """Issue #382: every manifest carries checkout_sha +
    update_branch alongside code_sha/code_sha_kind (heartbeat
    fields, diagnostics — not the running-code proof)."""
    pub, done = run_execute({
        "id": "test-382-prov",
        "job": "harvest-egx-poul",
        "added": worker.now()})
    manifest = pub.get("manifest", {})
    check("issue #382: manifest carries checkout_sha (same value "
          "the worker reports for the release checkout)",
          "checkout_sha" in manifest
          and manifest.get("checkout_sha")
          == worker.update_checkout_sha())
    check("issue #382: manifest carries update_branch (the "
          "release branch the worker updates from)",
          manifest.get("update_branch") == worker.UPDATE_BRANCH)
    check("issue #382: code_sha remains the running-code pin "
          "alongside the diagnostics",
          manifest.get("code_sha") == worker.running_code_sha()
          and manifest.get("code_sha_kind") == "sha256-running-bytes")


def test_valid_jobs_still_parse():
    """Control: the gate is the EMPTY plan only — valid job strings
    must still parse to a non-empty plan (parse_job level; no tool
    is executed here)."""
    reg = worker.registry()
    check("control: 'run vectorbt POUL' still parses to a plan",
          worker.parse_job("run vectorbt POUL", reg)
          == [("vectorbt", "POUL")])
    check("control: 'sweep-lite POUL market=EGX' still parses to "
          "a plan",
          worker.parse_job("sweep-lite POUL market=EGX", reg)
          == [("vectorbt", "POUL")])


def main():
    worker.sh = fake_sh
    worker.publish = stub_publish
    worker._mark_done = stub_mark_done
    setup_release()
    test_unknown_harvest_string_fails_closed()
    test_unknown_enumerate_typo_fails_closed()
    test_empty_job_string_fails_closed()
    test_unknown_sweep_filter_fails_closed()
    test_manifest_carries_checkout_provenance()
    test_valid_jobs_still_parse()
    print(f"\n{PASSED} passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
