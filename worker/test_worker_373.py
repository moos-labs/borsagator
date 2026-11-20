#!/usr/bin/env python3
"""Regression tests for issue #373: unknown job strings are silently
marked done with an empty run — fail closed + pin code SHA in the
manifest (INS-HARV-003 finding 3).

The defect (verified live): job `w5-harvest-poul-diag-002`
(`harvest-egx-poul`, one token) matched no special dispatch in
_execute_body, fell through to parse_job (which returns [] for
anything outside the registry grammar), ran zero tools, and was
still published and marked done with manifest `tools: {}` and
started/finished 49 microseconds apart.

The fix: when no special dispatch matches and parse_job returns
[], _execute_body records a named failure
(`tools: {"job": "unknown-job"}` + an explicit `error` field),
publishes it, and marks done with `result: "unknown-job"` in the
done record — visible in the manifest and the done record, never
a silent empty `tools: {}` marked done. Secondary: the manifest
pins the running code SHA (`code_sha`, same sha256-running-bytes
as the heartbeat carries).

Every test below FAILS on base e4eef8be and PASSES with the fix.
Fixtures are fresh (own temp root, own fake harvest output, real
top30 enumerator in fixtures mode) — nothing is copied from
test_worker_348.py / test_worker_328.py's fixtures. Stdlib only.
The sweep hooks (maybe_merge / maybe_compile / maybe_render /
extract_disclosure_events) are stubbed at the module boundary:
the unknown-job path must short-circuit before them, and they
are covered by their own tests.

Run: python3 worker/test_worker_373.py (exit 0 = all pass).
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="gator373-test-"))
os.environ["GATOR_ROOT"] = str(_TMP)

_HERE = Path(os.path.abspath(__file__)).parent
_REPO = _HERE.parent
sys.path.insert(0, str(_HERE))

import worker  # noqa: E402

PASSED = 0
PUBLISH_SEEN = {}
MARK_DONE_SEEN = {}
HARVEST_INVOKED = {"n": 0, "codes": []}
ENUMERATOR_INVOKED = {"n": 0}
HOOKS_SEEN = []
PUBLISH_DONE_RECORD = {}
RECORD_PUBLISH_FAILURE_SEEN = {}

FAKE_DISCLOSURES = {"ticker": "POUL", "docs": ["doc-373-a", "doc-373-b"]}


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
    """Stub worker.sh: `rm -rf` for real; `python3 -m venv` creates
    a venv whose python is a symlink to the real interpreter; the
    harvester invocation is intercepted (no EGX contact, no
    playwright) and writes a fake disclosures.json; the REAL
    top30 enumerator runs via subprocess (fixtures mode only);
    everything else succeeds silently."""
    if cmd.startswith("rm -rf "):
        shutil.rmtree(cmd[len("rm -rf "):].strip(), ignore_errors=True)
        return FakeResult(0)
    if cmd.startswith("python3 -m venv "):
        venv = Path(cmd[len("python3 -m venv "):].strip())
        (venv / "bin").mkdir(parents=True, exist_ok=True)
        link = venv / "bin" / "python"
        if link.is_symlink() or link.exists():
            link.unlink()
        link.symlink_to(sys.executable)
        return FakeResult(0)
    if "top30_enumerate.py" in cmd:
        ENUMERATOR_INVOKED["n"] += 1
        proc = subprocess.run(cmd, shell=True, cwd=cwd, env=env,
                              capture_output=True, text=True,
                              timeout=timeout)
        return FakeResult(proc.returncode, proc.stdout, proc.stderr)
    if "egx_harvest.py" in cmd:
        HARVEST_INVOKED["n"] += 1
        code = cmd.split()[-1]
        HARVEST_INVOKED["codes"].append(code)
        results = Path(cwd) / "results"
        results.mkdir(parents=True, exist_ok=True)
        (results / "disclosures.json").write_text(
            json.dumps(FAKE_DISCLOSURES), encoding="utf-8")
        return FakeResult(0)
    return FakeResult(0)


def setup_release():
    """Fake release checkout: a minimal registry (registry() reads
    it before the dispatch runs) + the REAL top30 enumerator and
    manifest, so the fixtures-mode entry point runs for real."""
    code = worker.CODE
    (code / "registry").mkdir(parents=True, exist_ok=True)
    (code / "registry" / "tools.json").write_text(
        json.dumps({"tools": []}), encoding="utf-8")
    (code / "scripts").mkdir(parents=True, exist_ok=True)
    shutil.copy(_REPO / "scripts" / "top30_enumerate.py",
                code / "scripts" / "top30_enumerate.py")
    (code / "evaluation").mkdir(parents=True, exist_ok=True)
    shutil.copy(_REPO / "evaluation" / "top30_manifest.json",
                code / "evaluation" / "top30_manifest.json")


def stub_publish(job, results_dir, manifest):
    PUBLISH_SEEN.clear()
    PUBLISH_SEEN["job"] = job
    PUBLISH_SEEN["manifest"] = json.loads(json.dumps(manifest))
    return "fake-archive-sha-373"


def stub_mark_done(job, archive_sha, result=None):
    MARK_DONE_SEEN.clear()
    MARK_DONE_SEEN["job"] = job
    MARK_DONE_SEEN["archive_sha"] = archive_sha
    MARK_DONE_SEEN["result"] = result


def stub_hook(name):
    def _hook(job, workdir, manifest, plan):
        HOOKS_SEEN.append(name)
        return None
    return _hook


def run_execute(job):
    PUBLISH_SEEN.clear()
    MARK_DONE_SEEN.clear()
    HOOKS_SEEN.clear()
    worker._execute_body(job)
    return PUBLISH_SEEN, MARK_DONE_SEEN


# --- The defect: unknown job strings publish an empty success --------

def test_bogus_job_is_named_unknown_job():
    pub, done = run_execute({
        "id": "test-373-bogus",
        "job": "harvest-egx-poul",  # the exact proven string (diag-002)
        "added": worker.now()})
    check("373: bogus job records a named unknown-job failure, "
          "not an empty tools {}",
          pub.get("manifest", {}).get("tools") == {"job": "unknown-job"})
    check("373: bogus job carries an explicit error naming the "
          "job string",
          "harvest-egx-poul" in pub.get("manifest", {}).get("error", ""))
    check("373: bogus job manifest pins the running code SHA",
          pub.get("manifest", {}).get("code_sha")
          == worker.running_code_sha()
          and len(pub.get("manifest", {}).get("code_sha") or "") == 64)
    check("373: bogus job still publishes + marks done (done "
          "means executed + archived, as for harvest-egx)",
          done.get("archive_sha") == "fake-archive-sha-373")
    check("373: bogus job done record carries the named result",
          done.get("result") == "unknown-job")
    check("373: bogus job never invokes the harvester",
          "harvest-egx-poul" not in HARVEST_INVOKED["codes"])
    check("373: bogus job short-circuits before the sweep hooks",
          HOOKS_SEEN == [])


def test_unknown_job_variants():
    for job_text, job_id in [
            ("", "test-373-empty"),
            ("nonsense", "test-373-nonsense"),
            ("sweep POUL.CA bogus-filter", "test-373-bad-filter"),
            ("run foo", "test-373-short-run")]:
        pub, done = run_execute({
            "id": job_id, "job": job_text, "added": worker.now()})
        check(f"373: {job_text!r} fails closed as unknown-job",
              pub.get("manifest", {}).get("tools")
              == {"job": "unknown-job"}
              and done.get("result") == "unknown-job")


def test_publish_failure_leaves_job_unmarked():
    real_publish = worker.publish
    real_rpf = worker._record_publish_failure
    worker.publish = lambda j, d, m: False  # noqa: E731
    worker._record_publish_failure = lambda j: RECORD_PUBLISH_FAILURE_SEEN.update(  # noqa: E731
        {"job": j})
    try:
        RECORD_PUBLISH_FAILURE_SEEN.clear()
        pub, done = run_execute({
            "id": "test-373-pubfail",
            "job": "harvest-egx-poul",
            "added": worker.now()})
        check("373: publish failure records the failure on the bus",
              RECORD_PUBLISH_FAILURE_SEEN.get("job", {}).get("id")
              == "test-373-pubfail")
        check("373: publish failure leaves the job unmarked",
              done == {})
    finally:
        worker.publish = real_publish
        worker._record_publish_failure = real_rpf


# --- Real jobs unaffected ----------------------------------------------

def test_harvest_still_dispatches():
    before = HARVEST_INVOKED["n"]
    pub, done = run_execute({
        "id": "test-373-harvest",
        "job": "harvest-egx POUL",
        "added": worker.now()})
    check("373-control: harvest-egx POUL still dispatches",
          HARVEST_INVOKED["n"] == before + 1
          and HARVEST_INVOKED["codes"][-1] == "POUL")
    check("373-control: harvest-egx POUL publishes ok",
          pub.get("manifest", {}).get("tools", {}).get(
              "egx-harvest") == "ok")
    check("373-control: harvest manifest also pins the code SHA",
          pub.get("manifest", {}).get("code_sha")
          == worker.running_code_sha())
    check("373-control: harvest job marked done without a "
          "result flag",
          done.get("archive_sha") == "fake-archive-sha-373"
          and done.get("result") is None)


def test_top30_still_dispatches():
    fixtures = str(_REPO / "scripts" / "top30_enumerate_fixtures")
    before = ENUMERATOR_INVOKED["n"]
    pub, done = run_execute({
        "id": "test-373-top30",
        "job": "top30-enumerate --mode fixtures --fixtures "
               + fixtures,
        "added": worker.now()})
    check("373-control: top30-enumerate still dispatches",
          ENUMERATOR_INVOKED["n"] == before + 1)
    check("373-control: top30-enumerate publishes ok",
          pub.get("manifest", {}).get("tools", {}).get(
              "top30-enumerate") == "ok")
    check("373-control: top30 job marked done",
          done.get("archive_sha") == "fake-archive-sha-373")


def test_diag_still_dispatches():
    assert not (worker.ROOT / "egx-profile").exists()
    pub, done = run_execute({
        "id": "test-373-diag",
        "job": "diag-egx-ab",
        "added": worker.now()})
    check("373-control: diag-egx-ab still dispatches to its "
          "runner (profile-missing is its named result here, "
          "not unknown-job)",
          pub.get("manifest", {}).get("tools", {}).get(
              "diag-egx-ab") == "profile-missing")
    check("373-control: diag job marked done",
          done.get("archive_sha") == "fake-archive-sha-373")


# --- The done record itself --------------------------------------------

def test_mark_done_record_carries_result():
    real_pub_done = worker._publish_done
    real_mark_done = REAL_MARK_DONE
    PUBLISH_DONE_RECORD.clear()
    worker._publish_done = lambda jid, rec, attempts=3: (  # noqa: E731
        PUBLISH_DONE_RECORD.update({"job_id": jid, "record": rec}),
        True)[1]
    worker._mark_done = real_mark_done
    try:
        assert real_mark_done(
            {"id": "test-373-done", "job": "harvest-egx-poul"},
            "fake-archive-sha-373", result="unknown-job") is True
        rec = json.loads(PUBLISH_DONE_RECORD["record"])
        check("373: done record carries result unknown-job",
              rec.get("result") == "unknown-job")
        check("373: done record with the extra field still "
              "passes receipt validation",
              worker._valid_receipt(PUBLISH_DONE_RECORD["record"],
                                    "test-373-done") is True)
        check("373: done record still carries the job string "
              "and archive SHA",
              rec.get("job") == "harvest-egx-poul"
              and rec.get("archive") == "fake-archive-sha-373"
              and rec.get("id") == "test-373-done")
        PUBLISH_DONE_RECORD.clear()
        assert real_mark_done(
            {"id": "test-373-done2", "job": "harvest-egx POUL"},
            "fake-archive-sha-373") is True
        rec2 = json.loads(PUBLISH_DONE_RECORD["record"])
        check("373: default _mark_done callers get no result "
              "field (back-compatible)",
              "result" not in rec2)
    finally:
        worker._publish_done = real_pub_done
        worker._mark_done = stub_mark_done


def main():
    global REAL_MARK_DONE
    REAL_MARK_DONE = worker._mark_done
    worker.sh = fake_sh
    worker.publish = stub_publish
    worker._mark_done = stub_mark_done
    worker.maybe_merge = stub_hook("merge")
    worker.maybe_compile = stub_hook("compile")
    worker.maybe_render = stub_hook("render")
    worker.extract_disclosure_events = stub_hook("extract")
    setup_release()
    test_bogus_job_is_named_unknown_job()
    test_unknown_job_variants()
    test_publish_failure_leaves_job_unmarked()
    test_harvest_still_dispatches()
    test_top30_still_dispatches()
    test_diag_still_dispatches()
    test_mark_done_record_carries_result()
    print(f"\n{PASSED} passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
