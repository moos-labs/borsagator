#!/usr/bin/env python3
"""Regression + entry-point tests for issue #446 (walk-forward
backtest cells: `run backtest <cutoff> <ticker>` jobs, design
#436 §6.4).

The wiring under test (worker/worker.py):
  parse_backtest_job — exactly `run backtest <YYYY-MM-DD>
    <ticker>` parses (canonical date, ticker uppercased);
    anything else (bad/non-canonical date, extra or missing
    tokens, bad ticker) fails closed (None). parse_job (the
    registry grammar) still returns [] for the string — the
    registry has no backtest tool — which is why _execute_body
    dispatches this kind before parse_job, like diag-egx-ab.
  run_backtest — pins first (round 3): every runner checkout is
    prepared and verified against the release registry pin the
    way run_tool does it (clone if missing, fetch + checkout on
    a mismatch, re-verify; ref-unpinned / ref-unavailable /
    ref-mismatch fail closed), and each runner's venv must match
    the checkout's requirements (the .gator-requirements-sha
    marker run_tool maintains; venv-missing / venv-stale fail
    closed). Only then does it invoke scripts/backtest.py from
    the release checkout under the worker's own interpreter,
    with the fleet runner checkouts at RUNNERS/<registry id> and
    each runner's own venv interpreter (VENVS/<id>/bin/python),
    --repeat-kronos, its output root pointed at the run dir; the
    harness runs via sh_group so a timeout kills the whole
    process tree before the named timeout result archives
    (venv-missing / venv-stale / timeout / exit-N / skipped when
    the harness wrote no manifest / manifest-unparseable /
    manifest-invalid). An ok cell's manifest is the deliverable.
  _execute_body backtest branch — publishes via the stubbed
    publish and marks done only on a successful publish, like
    diag-egx-ab (a failed publish records the failure and never
    marks done).

Deterministic replay (no live fetches, no runner execution): the
fake `sh` performs no subprocess work for a backtest.py
invocation; per CELL_MODE it writes the cell manifest the real
harness would write (ok), writes nothing (skipped), or exits 3 —
so the entry point's outcome validation is exercised against
each harness outcome shape. publish/_mark_done are stubbed at
the worker-module boundary while _execute_body itself runs for
real.

Harness-first: FAILS on pristine main (worker has no
parse_backtest_job / run_backtest — AttributeError — and
_execute_body fails the job closed as unknown-job) and PASSES on
the fixed tree. Stdlib only.

Run: python3 worker/test_worker_446_backtest.py (exit 0 = pass).
"""
import hashlib
import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _test_tmp  # noqa: E402  (atexit cleanup of scratch dirs, #388)
_TMP = _test_tmp.mkdtemp(prefix="gator446-backtest-test-")
os.environ["GATOR_ROOT"] = str(_TMP)

_HERE = Path(os.path.abspath(__file__)).parent
_REPO = _HERE.parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_REPO / "scripts"))

import worker  # noqa: E402

PASSED = 0
PUBLISH_SEEN = {}
MARK_DONE_SEEN = {}
BT_INVOKED = {"n": 0, "cmds": []}
CELL_MODE = {"mode": "ok"}  # ok | skipped | exit3 | timeout
PUBLISH_FAILURES = []
GIT_FAIL = {"on": False}
PINS = {"kronos": "a" * 40, "pandas-ta": "b" * 40,
        "talib": "c" * 40}
RUNNER_TOOLS = ("kronos", "pandas-ta", "talib")
REAL_SH_GROUP = worker.sh_group if hasattr(worker, "sh_group") else None


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


def fake_sh(cmd, cwd=None, env=None, timeout=3600):
    """Fake worker.sh: a backtest.py invocation performs the
    harness outcome CELL_MODE names (manifest write / nothing /
    exit 3) without any fetch or runner work; everything else
    (git, etc.) succeeds silently."""
    if cmd.startswith("git -C "):
        parts = shlex.split(cmd)
        repo = Path(parts[2])
        sub = parts[3]
        if sub == "rev-parse":
            head = repo / ".fake-head"
            return subprocess.CompletedProcess(
                cmd, 0, head.read_text().strip() + "\n", "")
        if sub == "fetch":
            return subprocess.CompletedProcess(
                cmd, 1 if GIT_FAIL["on"] else 0, "", "")
        if sub == "checkout":
            (repo / ".fake-head").write_text(parts[4])
            return subprocess.CompletedProcess(cmd, 0, "", "")
        return subprocess.CompletedProcess(cmd, 0, "", "")
    if "backtest.py" in cmd:
        BT_INVOKED["n"] += 1
        BT_INVOKED["cmds"].append(cmd)
        if CELL_MODE["mode"] == "timeout":
            raise subprocess.TimeoutExpired(cmd, 7200)
        parts = shlex.split(cmd)
        out_root = Path(parts[parts.index("--out-root") + 1])
        cutoff = parts[parts.index("--cutoff") + 1]
        ticker = parts[parts.index("--ticker") + 1]
        if CELL_MODE["mode"] == "exit3":
            return FakeResult(3, "", "stubbed harness failure")
        if CELL_MODE["mode"] == "skipped":
            return FakeResult(0, json.dumps(
                {"tool": "backtest-harness", "ticker": ticker,
                 "cutoff": cutoff, "status": "skipped",
                 "reason": "stubbed skip"}) + "\n")
        cell = out_root / cutoff / ticker
        cell.mkdir(parents=True, exist_ok=True)
        (cell / "manifest.json").write_text(json.dumps(
            {"tool": "backtest-harness", "issue": 436,
             "ticker": ticker, "cutoff": cutoff, "status": "ok"}),
            encoding="utf-8")
        return FakeResult(0, json.dumps(
            {"tool": "backtest-harness", "ticker": ticker,
             "cutoff": cutoff, "status": "ok"}) + "\n")
    return FakeResult(0)


def setup_release():
    """Fake release checkout: a registry carrying the three
    runner tools at their pins (registry() reads it before the
    backtest branch runs, and run_backtest verifies against it)."""
    code = worker.CODE
    (code / "scripts").mkdir(parents=True, exist_ok=True)
    (code / "registry").mkdir(parents=True, exist_ok=True)
    (code / "registry" / "tools.json").write_text(json.dumps({
        "tools": [{"id": t, "ref": PINS[t]} for t in RUNNER_TOOLS]}),
        encoding="utf-8")


def setup_runners():
    """Fake fleet checkouts at RUNNERS/<registry id>, each at its
    pin (.fake-head is what fake_sh's git rev-parse reports) with
    a requirements.txt."""
    for tool in RUNNER_TOOLS:
        repo = worker.RUNNERS / tool
        repo.mkdir(parents=True, exist_ok=True)
        (repo / "requirements.txt").write_text(
            "# %s deps\n" % tool, encoding="utf-8")
        (repo / ".fake-head").write_text(PINS[tool],
                                         encoding="utf-8")


def setup_venvs():
    """Fake per-runner venvs: VENVS/<registry id>/bin/python, the
    interpreters run_tool builds for live sweeps, plus the
    .gator-requirements-sha marker matching the checkout's
    requirements.txt, exactly as run_tool maintains it."""
    for tool in RUNNER_TOOLS:
        venv = worker.VENVS / tool
        bindir = venv / "bin"
        bindir.mkdir(parents=True, exist_ok=True)
        (bindir / "python").write_text("#!/bin/sh\n",
                                       encoding="utf-8")
        req = worker.RUNNERS / tool / "requirements.txt"
        (venv / ".gator-requirements-sha").write_text(
            hashlib.sha256(req.read_bytes()).hexdigest(),
            encoding="utf-8")


def stub_publish(job, results_dir, manifest):
    PUBLISH_SEEN.clear()
    PUBLISH_SEEN["job"] = job
    PUBLISH_SEEN["manifest"] = json.loads(json.dumps(manifest))
    wd = Path(results_dir)
    PUBLISH_SEEN["cell_manifest"] = (
        wd / "backtest" / "2023-12-29" / "COMI.CA"
        / "manifest.json").is_file()
    PUBLISH_SEEN["log"] = (wd / "backtest"
                           / "backtest-worker.log").is_file()
    return "fake-archive-sha-446"


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
    check("parse: exact job parses",
          worker.parse_backtest_job("run backtest 2023-12-29 COMI.CA")
          == {"kind": "backtest", "cutoff": "2023-12-29",
              "ticker": "COMI.CA"})
    check("parse: leading/trailing whitespace still parses",
          worker.parse_backtest_job(
              "  run backtest 2023-12-29 COMI.CA  ") is not None)
    check("parse: lowercase ticker is uppercased",
          worker.parse_backtest_job(
              "run backtest 2023-12-29 comi.ca")["ticker"]
          == "COMI.CA")
    for bad in ("", "run backtest", "run backtest 2023-12-29",
                "run backtest 2023-12-29 COMI.CA extra",
                "backtest 2023-12-29 COMI.CA",
                "run backtest 2023-13-01 COMI.CA",
                "run backtest 2023-02-30 COMI.CA",
                "run backtest 2023-2-9 COMI.CA",
                "run backtest 29-12-2023 COMI.CA",
                "run backtest 2023-12-29 COMI.CA!",
                "run backtest 2023-12-29 ../COMI",
                "run kronos POUL.CA", "sweep POUL.CA"):
        check("parse: rejects %r" % bad,
              worker.parse_backtest_job(bad) is None)
    check("parse: non-string job fails closed",
          worker.parse_backtest_job(None) is None
          and worker.parse_backtest_job(42) is None)
    check("parse: old parse_job still returns [] (registry has "
          "no backtest tool — the _execute_body branch is what "
          "dispatches it)",
          worker.parse_job("run backtest 2023-12-29 COMI.CA",
                           {"tools": []}) == [])


def test_entry_point_ok():
    CELL_MODE["mode"] = "ok"
    before = BT_INVOKED["n"]
    wd = worker.OUT / "test-446-bt-ok"
    res = worker.run_backtest(
        {"id": "test-446-bt-ok",
         "job": "run backtest 2023-12-29 COMI.CA"}, wd)
    check("entry point: harness actually invoked",
          BT_INVOKED["n"] == before + 1)
    cmd = BT_INVOKED["cmds"][-1]
    check("entry point: invoked from the release checkout",
          str(worker.CODE / "scripts" / "backtest.py") in cmd)
    check("entry point: harness runs under the worker's own "
          "interpreter", cmd.startswith(shlex.quote(sys.executable)))
    check("entry point: invoked with --repeat-kronos (design §6.4)",
          "--repeat-kronos" in cmd)
    check("entry point: output root is the run dir",
          "--out-root %s" % shlex.quote(str(wd / "backtest"))
          in cmd)
    parts = shlex.split(cmd)

    def arg_after(flag):
        return parts[parts.index(flag) + 1]

    check("entry point: runner checkouts are exactly "
          "RUNNERS/<registry id> (run_tool's layout — a repo-name "
          "path like kronos-runner must NOT pass)",
          arg_after("--kronos-runner") == str(worker.RUNNERS
                                              / "kronos")
          and arg_after("--pandas-ta-runner") == str(
              worker.RUNNERS / "pandas-ta")
          and arg_after("--talib-runner") == str(worker.RUNNERS
                                                 / "talib"))
    check("entry point: each runner gets exactly its own venv "
          "interpreter",
          arg_after("--kronos-python") == str(
              worker.VENVS / "kronos" / "bin" / "python")
          and arg_after("--pandas-ta-python") == str(
              worker.VENVS / "pandas-ta" / "bin" / "python")
          and arg_after("--talib-python") == str(
              worker.VENVS / "talib" / "bin" / "python"))
    check("entry point: ok cell with a manifest is ok",
          res == {"backtest": "ok"})
    check("entry point: cell manifest landed under the run dir",
          (wd / "backtest" / "2023-12-29" / "COMI.CA"
           / "manifest.json").is_file())
    check("entry point: log written beside the cell",
          (wd / "backtest" / "backtest-worker.log").is_file())


def test_entry_point_skipped():
    CELL_MODE["mode"] = "skipped"
    wd = worker.OUT / "test-446-bt-skipped"
    res = worker.run_backtest(
        {"id": "test-446-bt-skipped",
         "job": "run backtest 2023-12-29 COMI.CA"}, wd)
    check("entry point: exit 0 without a manifest is the "
          "harness's skipped cell, not a failure",
          res == {"backtest": "skipped"})
    CELL_MODE["mode"] = "ok"


def test_entry_point_exit():
    CELL_MODE["mode"] = "exit3"
    wd = worker.OUT / "test-446-bt-exit"
    res = worker.run_backtest(
        {"id": "test-446-bt-exit",
         "job": "run backtest 2023-12-29 COMI.CA"}, wd)
    check("entry point: non-zero harness exit is a named exit-N "
          "failure", res == {"backtest": "exit-3"})
    CELL_MODE["mode"] = "ok"


def test_entry_point_venv_missing():
    py = worker.VENVS / "talib" / "bin" / "python"
    py.unlink()
    try:
        before = BT_INVOKED["n"]
        wd = worker.OUT / "test-446-bt-novenv"
        res = worker.run_backtest(
            {"id": "test-446-bt-novenv",
             "job": "run backtest 2023-12-29 COMI.CA"}, wd)
        check("entry point: a missing runner venv fails closed as "
              "venv-missing", res == {"backtest": "venv-missing"})
        check("entry point: without all venvs the harness never "
              "runs", BT_INVOKED["n"] == before)
    finally:
        py.write_text("#!/bin/sh\n", encoding="utf-8")


def test_entry_point_timeout():
    CELL_MODE["mode"] = "timeout"
    try:
        wd = worker.OUT / "test-446-bt-timeout"
        res = worker.run_backtest(
            {"id": "test-446-bt-timeout",
             "job": "run backtest 2023-12-29 COMI.CA"}, wd)
        check("entry point: a harness timeout archives as a named "
              "timeout failure (never an exception out of "
              "_execute_body)", res == {"backtest": "timeout"})
    finally:
        CELL_MODE["mode"] = "ok"


def test_entry_point_ref_prep():
    head_file = worker.RUNNERS / "kronos" / ".fake-head"
    head_file.write_text("d" * 40, encoding="utf-8")
    try:
        before = BT_INVOKED["n"]
        wd = worker.OUT / "test-446-bt-refprep"
        res = worker.run_backtest(
            {"id": "test-446-bt-refprep",
             "job": "run backtest 2023-12-29 COMI.CA"}, wd)
        check("ref prep: a checkout behind its pin is fetched + "
              "checked out to the pin, then the cell runs",
              res == {"backtest": "ok"}
              and head_file.read_text() == PINS["kronos"]
              and BT_INVOKED["n"] == before + 1)
    finally:
        head_file.write_text(PINS["kronos"], encoding="utf-8")


def test_entry_point_ref_unavailable():
    head_file = worker.RUNNERS / "kronos" / ".fake-head"
    head_file.write_text("d" * 40, encoding="utf-8")
    GIT_FAIL["on"] = True
    try:
        before = BT_INVOKED["n"]
        wd = worker.OUT / "test-446-bt-refunavail"
        res = worker.run_backtest(
            {"id": "test-446-bt-refunavail",
             "job": "run backtest 2023-12-29 COMI.CA"}, wd)
        check("ref prep: an unreachable pin fails closed as "
              "ref-unavailable", res == {"backtest":
                                         "ref-unavailable"})
        check("ref prep: the harness never runs on an unverified "
              "checkout", BT_INVOKED["n"] == before)
    finally:
        GIT_FAIL["on"] = False
        head_file.write_text(PINS["kronos"], encoding="utf-8")


def test_entry_point_venv_stale():
    marker = worker.VENVS / "talib" / ".gator-requirements-sha"
    good = marker.read_text()
    marker.write_text("0" * 64, encoding="utf-8")
    try:
        before = BT_INVOKED["n"]
        wd = worker.OUT / "test-446-bt-venvstale"
        res = worker.run_backtest(
            {"id": "test-446-bt-venvstale",
             "job": "run backtest 2023-12-29 COMI.CA"}, wd)
        check("venv: a requirements marker mismatch fails closed "
              "as venv-stale (the venv was built from another "
              "ref's requirements)",
              res == {"backtest": "venv-stale"})
        check("venv: the harness never runs against stale deps",
              BT_INVOKED["n"] == before)
    finally:
        marker.write_text(good, encoding="utf-8")


def test_sh_group_timeout_kills_tree():
    check("sh_group: worker provides the process-group runner",
          REAL_SH_GROUP is not None)
    if REAL_SH_GROUP is None:
        return
    marker = worker.OUT / "test-446-group-marker"
    if marker.exists():
        marker.unlink()
    cmd = "(sleep 3; touch %s) & sleep 30" % shlex.quote(str(marker))
    t0 = time.time()
    raised = False
    try:
        REAL_SH_GROUP(cmd, timeout=1)
    except subprocess.TimeoutExpired:
        raised = True
    elapsed = time.time() - t0
    check("sh_group: timeout raises TimeoutExpired promptly",
          raised and elapsed < 8)
    time.sleep(4)
    check("sh_group: the whole tree died — the background child "
          "never reached its 3s touch", not marker.exists())


def test_bad_job_publishes_failure_manifest():
    pub, done = run_execute({
        "id": "test-446-bt-badjob",
        "job": "run backtest 2023-13-40 COMI.CA",
        "added": worker.now()})
    check("bad job string: named bad-job failure in the manifest",
          pub.get("manifest", {}).get("tools", {}).get(
              "backtest") == "bad-job")
    check("bad job string: still publishes + marks done (done "
          "means executed + archived, as for diag-egx-ab)",
          done.get("archive_sha") == "fake-archive-sha-446")


def test_execute_ok_publishes():
    CELL_MODE["mode"] = "ok"
    pub, done = run_execute({
        "id": "test-446-bt-exec",
        "job": "run backtest 2023-12-29 COMI.CA",
        "added": worker.now()})
    check("execute: manifest tools backtest is ok",
          pub.get("manifest", {}).get("tools", {}).get(
              "backtest") == "ok")
    check("execute: cell manifest + log archived",
          pub.get("cell_manifest") and pub.get("log"))
    check("execute: done marked only after publish",
          done.get("archive_sha") == "fake-archive-sha-446")


def test_execute_leading_space_dispatches():
    CELL_MODE["mode"] = "ok"
    pub, done = run_execute({
        "id": "test-446-bt-exec-space",
        "job": " run backtest 2023-12-29 COMI.CA",
        "added": worker.now()})
    check("execute: leading-space job dispatches to the backtest "
          "branch (not the #371 unknown-job branch)",
          pub.get("manifest", {}).get("tools", {}).get(
              "backtest") == "ok")


def test_failed_publish_never_marks_done():
    real_publish = worker.publish
    real_record = worker._record_publish_failure
    worker.publish = lambda job, wd, manifest: None
    worker._record_publish_failure = (
        lambda job: PUBLISH_FAILURES.append(job["id"]))
    PUBLISH_FAILURES.clear()
    MARK_DONE_SEEN.clear()
    try:
        worker._execute_body({
            "id": "test-446-bt-pubfail",
            "job": "run backtest 2023-12-29 COMI.CA",
            "added": worker.now()})
    finally:
        worker.publish = real_publish
        worker._record_publish_failure = real_record
    check("failed publish: the failure is recorded",
          PUBLISH_FAILURES == ["test-446-bt-pubfail"])
    check("failed publish: the job is NOT marked done",
          MARK_DONE_SEEN == {})


def main():
    worker.sh = fake_sh
    worker.sh_group = fake_sh
    worker.publish = stub_publish
    worker._mark_done = stub_mark_done
    setup_release()
    setup_runners()
    setup_venvs()
    test_parse()
    test_entry_point_ok()
    test_entry_point_skipped()
    test_entry_point_exit()
    test_entry_point_venv_missing()
    test_entry_point_timeout()
    test_entry_point_ref_prep()
    test_entry_point_ref_unavailable()
    test_entry_point_venv_stale()
    test_sh_group_timeout_kills_tree()
    test_bad_job_publishes_failure_manifest()
    test_execute_ok_publishes()
    test_execute_leading_space_dispatches()
    test_failed_publish_never_marks_done()
    print("\n%d passed" % PASSED)
    return 0


if __name__ == "__main__":
    sys.exit(main())
