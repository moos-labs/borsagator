#!/usr/bin/env python3
"""Regression + entry-point tests for issue #283 (paired A/B EGX
diagnostic probe: `diag-egx-ab` job).

The wiring under test (worker/worker.py):
  parse_diag_egx_ab_job — exactly `diag-egx-ab` parses; anything
    else (arguments, typos, empty) fails closed (None). parse_job
    (the registry grammar) still returns [] for the string — the
    registry has no diag tool — which is why _execute_body
    dispatches this kind before parse_job, like harvest-egx.
  run_diag_egx_ab — runs the REAL scripts/diag_egx_ab.py in the
    egx-harvest playwright venv under xvfb-run, requires the
    persistent Chromium profile, and validates the record
    fail-closed (record-missing / unparseable / invalid). An
    honest record with ANY verdict is "ok": the record is the
    deliverable, not the EGX response.
  _execute_body diag branch — publishes via the stubbed publish
    and marks done only on a successful publish, like harvest-egx.

Deterministic replay (no live EGX, no browser): this VM has no
playwright/Chromium, so the fake `sh` does NOT launch a browser.
For a diag invocation it builds the record with the REAL script's
own pure functions (classify_page / derive_verdict / write_outputs
over the script's SIMULATED fixtures) and writes the real
diag-egx-ab.json + .log into the run dir — so the entry point's
record validation is exercised against a record the script itself
built. The browser legs are covered separately by
scripts/test_diag_egx_ab_283.py's --dry-run subprocess check,
which runs the legs for real where playwright exists. git/venv
are stubbed; publish/_mark_done are stubbed at the worker-module
boundary while _execute_body itself runs for real.

Harness-first: FAILS on pristine main (worker has no
parse_diag_egx_ab_job / run_diag_egx_ab — AttributeError — and
_execute_body publishes an empty run as done) and PASSES on the
fixed tree. Stdlib only.

Run: python3 worker/test_worker_283_diag.py (exit 0 = all pass).
"""
import json
import os
import shlex
import shutil
import sys
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="gator283-diag-test-"))
os.environ["GATOR_ROOT"] = str(_TMP)

_HERE = Path(os.path.abspath(__file__)).parent
_REPO = _HERE.parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_REPO / "scripts"))

import worker  # noqa: E402
import diag_egx_ab as D  # noqa: E402

PASSED = 0
PUBLISH_SEEN = {}
MARK_DONE_SEEN = {}
DIAG_INVOKED = {"n": 0, "cmds": []}
RECORD_MODE = {"mode": "ok"}  # ok | missing | exit3


def check(name, cond):
    global PASSED
    assert cond, name
    PASSED += 1
    print("pass: %s" % name)


class FakeResult:
    def __init__(self, rc=0, out="", err=""):
        self.returncode = rc
        self.stdout = out
        self.stderr = err


def build_stub_record(out_dir, profile_dir):
    """Build a probe record with the REAL script's pure functions:
    leg A sees the simulated results page, leg B resets, leg A
    repeats as results — the config-dependent pattern."""
    a = {"leg": "A", "config": "harvester", "url": D.DIAG_URL,
         "started": D.utcnow(), "nav_error": None,
         "nav_error_kind": None, "status": 200,
         "final_url": D.DIAG_URL,
         "body_chars": 120, "body_sample": "Board meeting results",
         "classification": D.classify_page(
             200, D.DIAG_URL, D.fixture_results_page(),
             "Board meeting results"),
         "egress_ip": None, "finished": D.utcnow()}
    b = dict(a, leg="B", config="enumerator", status=None,
             final_url=None, body_chars=0, body_sample="",
             nav_error="TimeoutError: Page.goto: "
                       "net::ERR_CONNECTION_RESET at " + D.DIAG_URL,
             nav_error_kind="reset", classification="reset")
    record = {"tool": "scripts/diag_egx_ab.py", "issue": 283,
              "url": D.DIAG_URL, "legs": ["A", "B", "A"],
              "profile": str(profile_dir),
              "nav_timeout_ms": D.NAV_TIMEOUT_MS,
              "settle_ms": D.SETTLE_MS, "started": D.utcnow(),
              "legs_records": [a, b, a]}
    record["verdict"], record["verdict_note"] = D.derive_verdict(
        record["legs_records"])
    record["finished"] = D.utcnow()
    D.write_outputs(record, str(out_dir))
    return record


def fake_sh(cmd, cwd=None, env=None, timeout=3600):
    """Fake worker.sh: perform `rm -rf` for real; `python3 -m venv`
    creates a venv whose python is a symlink to the real
    interpreter; a diag_egx_ab.py invocation builds the stub record
    with the script's own functions (no browser in this VM);
    everything else (pip install, playwright install, git)
    succeeds."""
    if cmd.startswith("rm -rf "):
        shutil.rmtree(cmd[len("rm -rf "):].strip(), ignore_errors=True)
        return FakeResult(0)
    if "diag_egx_ab.py" in cmd:
        DIAG_INVOKED["n"] += 1
        DIAG_INVOKED["cmds"].append(cmd)
        parts = shlex.split(cmd)
        out_dir = Path(parts[parts.index("--out-dir") + 1])
        profile = parts[parts.index("--profile") + 1]
        if RECORD_MODE["mode"] == "exit3":
            return FakeResult(3, "", "stubbed failure")
        if RECORD_MODE["mode"] == "missing":
            return FakeResult(0, "diag stub: no record\n")
        build_stub_record(out_dir, profile)
        return FakeResult(0, "diag stub: record written\n")
    if cmd.startswith("python3 -m venv "):
        venv = Path(cmd[len("python3 -m venv "):].strip())
        (venv / "bin").mkdir(parents=True, exist_ok=True)
        link = venv / "bin" / "python"
        if link.is_symlink() or link.exists():
            link.unlink()
        link.symlink_to(sys.executable)
        return FakeResult(0)
    return FakeResult(0)


def setup_release():
    """Fake release checkout: the REAL diag script, and a minimal
    registry (registry() reads it before the diag branch runs)."""
    code = worker.CODE
    (code / "scripts").mkdir(parents=True, exist_ok=True)
    shutil.copy(_REPO / "scripts" / "diag_egx_ab.py",
                code / "scripts" / "diag_egx_ab.py")
    (code / "registry").mkdir(parents=True, exist_ok=True)
    (code / "registry" / "tools.json").write_text(json.dumps({
        "tools": []}), encoding="utf-8")


def stub_publish(job, results_dir, manifest):
    PUBLISH_SEEN.clear()
    PUBLISH_SEEN["job"] = job
    PUBLISH_SEEN["manifest"] = json.loads(json.dumps(manifest))
    wd = Path(results_dir)
    PUBLISH_SEEN["record"] = (wd / "diag-egx-ab"
                              / "diag-egx-ab.json").is_file()
    PUBLISH_SEEN["log"] = (wd / "diag-egx-ab"
                           / "diag-egx-ab.log").is_file()
    return "fake-archive-sha-283"


def stub_mark_done(job, archive_sha):
    MARK_DONE_SEEN.clear()
    MARK_DONE_SEEN["job"] = job
    MARK_DONE_SEEN["archive_sha"] = archive_sha


def run_execute(job):
    PUBLISH_SEEN.clear()
    MARK_DONE_SEEN.clear()
    worker._execute_body(job)
    return PUBLISH_SEEN, MARK_DONE_SEEN


def test_parse():
    check("parse: bare job parses to a non-empty plan",
          worker.parse_diag_egx_ab_job("diag-egx-ab")
          == {"kind": "diag-egx-ab"})
    check("parse: leading/trailing whitespace still parses",
          worker.parse_diag_egx_ab_job("  diag-egx-ab  ")
          == {"kind": "diag-egx-ab"})
    for bad in ("", "sweep-lite POUL.CA", "diag-egx-ab POUL",
                "diag-egx-ab --mode live", "diag-egx-ab --dry-run",
                "diag-egx-abx", "diag-egx-a", "harvest-egx POUL"):
        check("parse: rejects %r" % bad,
              worker.parse_diag_egx_ab_job(bad) is None)
    check("parse: old parse_job still returns [] (registry has no "
          "diag tool — the _execute_body branch is what dispatches "
          "it)",
          worker.parse_job("diag-egx-ab", {"tools": []}) == [])


def test_entry_point_ok():
    profile = worker._egx_profile_dir()
    profile.mkdir(parents=True, exist_ok=True)
    RECORD_MODE["mode"] = "ok"
    before = DIAG_INVOKED["n"]
    wd = worker.OUT / "test-283-diag-ok"
    res = worker.run_diag_egx_ab(
        {"id": "test-283-diag-ok", "job": "diag-egx-ab"}, wd)
    check("entry point: script actually invoked",
          DIAG_INVOKED["n"] == before + 1)
    check("entry point: invoked under xvfb-run (leg A needs "
          "DISPLAY, like run_harvest)",
          DIAG_INVOKED["cmds"][-1].startswith("xvfb-run"))
    check("entry point: invoked with the persistent profile",
          "--profile %s" % shlex.quote(str(profile))
          in DIAG_INVOKED["cmds"][-1])
    check("entry point: honest record with any verdict is ok",
          res == {"diag-egx-ab": "ok"})
    rec = json.loads((wd / "diag-egx-ab" / "diag-egx-ab.json")
                     .read_text(encoding="utf-8"))
    check("entry point: record verdict is config-dependent "
          "(stub: A results, B reset, A results)",
          rec["verdict"] == "config-dependent")
    check("entry point: record URL is the fixed POUL NewsSearch URL",
          rec["url"] == D.DIAG_URL)
    check("entry point: log written beside the record",
          (wd / "diag-egx-ab" / "diag-egx-ab.log").is_file())


def test_entry_point_record_missing():
    RECORD_MODE["mode"] = "missing"
    wd = worker.OUT / "test-283-diag-missing"
    res = worker.run_diag_egx_ab(
        {"id": "test-283-diag-missing", "job": "diag-egx-ab"}, wd)
    check("entry point: exit 0 without a record fails closed as "
          "record-missing",
          res == {"diag-egx-ab": "record-missing"})
    RECORD_MODE["mode"] = "ok"


def test_entry_point_exit():
    RECORD_MODE["mode"] = "exit3"
    wd = worker.OUT / "test-283-diag-exit"
    res = worker.run_diag_egx_ab(
        {"id": "test-283-diag-exit", "job": "diag-egx-ab"}, wd)
    check("entry point: non-zero script exit is a named exit-N "
          "failure",
          res == {"diag-egx-ab": "exit-3"})
    RECORD_MODE["mode"] = "ok"


def test_profile_missing_fails_closed():
    shutil.rmtree(worker._egx_profile_dir(), ignore_errors=True)
    before = DIAG_INVOKED["n"]
    wd = worker.OUT / "test-283-diag-noprofile"
    res = worker.run_diag_egx_ab(
        {"id": "test-283-diag-noprofile", "job": "diag-egx-ab"}, wd)
    check("entry point: live probe without the profile fails "
          "closed as profile-missing",
          res == {"diag-egx-ab": "profile-missing"})
    check("entry point: without profile the script never runs",
          DIAG_INVOKED["n"] == before)
    check("entry point: without profile no record is written",
          not (wd / "diag-egx-ab" / "diag-egx-ab.json").exists())
    worker._egx_profile_dir().mkdir(parents=True, exist_ok=True)


def test_venv_failed():
    real = worker._ensure_egx_playwright_venv
    worker._ensure_egx_playwright_venv = lambda: (
        Path("/nonexistent/python"), False)
    try:
        wd = worker.OUT / "test-283-diag-novenv"
        res = worker.run_diag_egx_ab(
            {"id": "test-283-diag-novenv", "job": "diag-egx-ab"}, wd)
        check("entry point: venv not ready fails closed as "
              "venv-failed",
              res == {"diag-egx-ab": "venv-failed"})
    finally:
        worker._ensure_egx_playwright_venv = real


def test_bad_job_publishes_failure_manifest():
    pub, done = run_execute({
        "id": "test-283-diag-badjob",
        "job": "diag-egx-ab --bogus",
        "added": worker.now()})
    check("bad job string: named bad-job failure in the manifest",
          pub.get("manifest", {}).get("tools", {}).get(
              "diag-egx-ab") == "bad-job")
    check("bad job string: still publishes + marks done (done "
          "means executed + archived, as for harvest-egx)",
          done.get("archive_sha") == "fake-archive-sha-283")


def test_execute_ok_publishes():
    RECORD_MODE["mode"] = "ok"
    pub, done = run_execute({
        "id": "test-283-diag-exec",
        "job": "diag-egx-ab",
        "added": worker.now()})
    check("execute: manifest tools diag-egx-ab is ok",
          pub.get("manifest", {}).get("tools", {}).get(
              "diag-egx-ab") == "ok")
    check("execute: record + log archived",
          pub.get("record") and pub.get("log"))
    check("execute: done marked only after publish",
          done.get("archive_sha") == "fake-archive-sha-283")


def main():
    worker.sh = fake_sh
    worker.publish = stub_publish
    worker._mark_done = stub_mark_done
    setup_release()
    test_parse()
    test_entry_point_ok()
    test_entry_point_record_missing()
    test_entry_point_exit()
    test_profile_missing_fails_closed()
    test_venv_failed()
    test_bad_job_publishes_failure_manifest()
    test_execute_ok_publishes()
    print("\n%d passed" % PASSED)
    return 0


if __name__ == "__main__":
    sys.exit(main())
