#!/usr/bin/env python3
"""Regression tests for issue #158: venv deps installed only on first
creation — stale deps on a ref change; venv/pip return codes unchecked.

The bug: worker.run_tool installed requirements.txt only inside
`if not py.exists()` — i.e. only when the venv was first created. A
promoted ref that changes requirements.txt reused the old venv's deps,
and the venv/pip return codes were unchecked, so a failed install
still ran the tool against stale/missing deps.

The fix:
  1. The venv records the sha256 of the pinned ref's requirements.txt
     (marker `.gator-requirements-sha` inside the venv); when the hash
     differs the venv is recreated and deps reinstalled, so the venv
     always matches the pinned ref's requirements.
  2. `python3 -m venv` and pip install return codes are checked:
     venv failure -> "venv-failed", pip failure -> "deps-failed", and
     the tool is NOT run in either case (the failure is loud in the
     manifest + <tool>.log via _execute).
  3. A failed install leaves no marker, so the next run retries.

Harness-first: FAILS on the pristine HEAD (no reinstall on a
requirements bump; a failed pip install still runs the tool and
returns ok) and PASSES on the fixed tree. Stdlib only, no network —
git is stubbed, the runner clones are plain directories under a temp
GATOR_ROOT.

Run: python3 worker/test_worker_158.py (exit 0 = all pass).
"""
import hashlib
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _test_tmp  # noqa: E402  (atexit cleanup of scratch dirs, #388)
_TMP = _test_tmp.mkdtemp(prefix="gator158-test-")
os.environ["GATOR_ROOT"] = str(_TMP)

_HERE = Path(os.path.abspath(__file__)).parent
sys.path.insert(0, str(_HERE))

import worker  # noqa: E402

HEX40 = "a" * 40
TOOL = "yahooquery"
REQ_V1 = "requests==2.31.0\n"
REQ_V2 = "requests==2.32.0\n"
PASSED = 0
TOTAL = 0


def check(name, cond):
    global PASSED, TOTAL
    TOTAL += 1
    if cond:
        PASSED += 1
        print(f"pass: {name}")
    else:
        print(f"FAIL: {name}")


class FakeResult:
    def __init__(self, rc=0, out="", err=""):
        self.returncode = rc
        self.stdout = out
        self.stderr = err


class FakeShell:
    """Fake worker.sh: perform `rm -rf` for real (so recreates are
    observable), simulate venv creation + pip install, succeed git
    fetch/checkout, record tool runs. pip/venv failures on demand."""

    def __init__(self, pip_rc=0, venv_rc=0, venv_no_py=False):
        self.calls = []
        self.pip_rc = pip_rc
        self.venv_rc = venv_rc
        self.venv_no_py = venv_no_py
        self.pip_runs = []      # (tool, requirements bytes) per install
        self.tool_runs = []     # tool commands actually executed
        self.venv_runs = 0

    def __call__(self, cmd, cwd=None, env=None, timeout=3600):
        self.calls.append(cmd)
        if cmd.startswith("rm -rf "):
            shutil.rmtree(cmd[len("rm -rf "):].strip(),
                          ignore_errors=True)
            return FakeResult(0)
        if cmd.startswith("python3 -m venv "):
            self.venv_runs += 1
            if self.venv_rc != 0:
                return FakeResult(self.venv_rc, "",
                                  "venv creation failed: boom")
            if self.venv_no_py:
                # A lying rc 0: the command "succeeds" but yields no
                # interpreter — run_tool must still fail loudly.
                return FakeResult(0)
            venv = Path(cmd[len("python3 -m venv "):].strip())
            (venv / "bin").mkdir(parents=True, exist_ok=True)
            (venv / "bin" / "python").write_text("#!/bin/sh\n")
            return FakeResult(0)
        if "/bin/pip install" in cmd:
            parts = cmd.split()
            req = Path(parts[parts.index("-r") + 1])
            venv = Path(parts[0]).parent.parent
            tool = venv.name
            if self.pip_rc != 0:
                return FakeResult(self.pip_rc, "",
                                  "ERROR: Could not install "
                                  "requests==9.9.9 (no such version)")
            self.pip_runs.append((tool, req.read_bytes()))
            return FakeResult(0)
        if "git -C" in cmd and ("fetch" in cmd or "checkout" in cmd):
            return FakeResult(0)
        if cmd.startswith("bash -c "):
            self.tool_runs.append(cmd)
            return FakeResult(0)
        return FakeResult(0)


def seed_repo(requirements=None):
    repo = worker.RUNNERS / TOOL
    repo.mkdir(parents=True, exist_ok=True)
    if requirements is not None:
        (repo / "requirements.txt").write_text(requirements)
    elif (repo / "requirements.txt").exists():
        (repo / "requirements.txt").unlink()
    return repo


def sha(b):
    return hashlib.sha256(b).hexdigest()


def marker_sha():
    """Recorded requirements hash, or '' when the marker is absent
    (the pre-fix code never writes one)."""
    p = worker.VENVS / TOOL / ".gator-requirements-sha"
    return p.read_text().strip() if p.is_file() else ""


def main():
    real_sh = worker.sh
    try:
        # --- 1. First run installs the pinned ref's deps ---
        fake = FakeShell()
        worker.sh = fake
        seed_repo(REQ_V1)
        status, _ = worker.run_tool(TOOL, "POUL.CA", "true",
                                    HEX40, "yahooquery-runner")
        check("first run returns ok", status == "ok")
        check("first run installs requirements v1",
              fake.pip_runs == [(TOOL, REQ_V1.encode())])
        check("first run creates the venv python",
              (worker.VENVS / TOOL / "bin" / "python").is_file())
        check("first run records the requirements hash",
              marker_sha() == sha(REQ_V1.encode()))
        check("first run executes the tool once",
              len(fake.tool_runs) == 1)

        # --- 2. Same requirements: no reinstall, tool still runs ---
        before = len(fake.pip_runs)
        status, _ = worker.run_tool(TOOL, "POUL.CA", "true",
                                    HEX40, "yahooquery-runner")
        check("unchanged requirements still return ok", status == "ok")
        check("unchanged requirements are not reinstalled",
              len(fake.pip_runs) == before)
        check("unchanged requirements still run the tool",
              len(fake.tool_runs) == 2)

        # --- 3. Ref bumps a requirement: deps are reinstalled ---
        # (THE defect: pristine HEAD never calls pip again here.)
        seed_repo(REQ_V2)
        status, _ = worker.run_tool(TOOL, "POUL.CA", "true",
                                    "b" * 40, "yahooquery-runner")
        check("requirements bump still returns ok", status == "ok")
        check("requirements bump reinstalls the new deps",
              fake.pip_runs[-1] == (TOOL, REQ_V2.encode()))
        check("requirements bump updates the recorded hash",
              marker_sha() == sha(REQ_V2.encode()))
        check("requirements bump recreates the venv",
              fake.venv_runs == 2)

        # --- 4. A failed pip install fails the tool LOUDLY ---
        # (THE defect: pristine HEAD ignores the rc, runs the tool
        # against stale deps and returns ok.)
        shutil.rmtree(worker.VENVS / TOOL, ignore_errors=True)
        fake = FakeShell(pip_rc=1)
        worker.sh = fake
        seed_repo(REQ_V1)
        status, log = worker.run_tool(TOOL, "POUL.CA", "true",
                                      HEX40, "yahooquery-runner")
        check("failed pip install returns deps-failed",
              status == "deps-failed")
        check("failed pip install does not run the tool",
              len(fake.tool_runs) == 0)
        check("failed pip install surfaces the pip error",
              "Could not install" in log)
        check("failed pip install leaves no marker (retry next run)",
              not (worker.VENVS / TOOL
                   / ".gator-requirements-sha").exists())
        # Retry with pip working: the install is retried and succeeds
        # (the failed attempt was never recorded as an install).
        fake.pip_rc = 0
        status, _ = worker.run_tool(TOOL, "POUL.CA", "true",
                                    HEX40, "yahooquery-runner")
        check("retry after pip failure installs and runs ok",
              status == "ok" and len(fake.pip_runs) == 1
              and len(fake.tool_runs) == 1)

        # --- 5. A failed venv creation fails the tool LOUDLY ---
        shutil.rmtree(worker.VENVS / TOOL, ignore_errors=True)
        fake = FakeShell(venv_rc=1)
        worker.sh = fake
        seed_repo(REQ_V1)
        status, _ = worker.run_tool(TOOL, "POUL.CA", "true",
                                    HEX40, "yahooquery-runner")
        check("failed venv creation returns venv-failed",
              status == "venv-failed")
        check("failed venv creation does not run pip",
              len(fake.pip_runs) == 0)
        check("failed venv creation does not run the tool",
              len(fake.tool_runs) == 0)

        # --- 5b. A venv command that returns 0 but yields no
        # interpreter is a failed venv too ---
        shutil.rmtree(worker.VENVS / TOOL, ignore_errors=True)
        fake = FakeShell(venv_no_py=True)
        worker.sh = fake
        seed_repo(REQ_V1)
        status, log = worker.run_tool(TOOL, "POUL.CA", "true",
                                      HEX40, "yahooquery-runner")
        check("venv with no interpreter returns venv-failed",
              status == "venv-failed")
        check("venv with no interpreter does not run the tool",
              len(fake.tool_runs) == 0)

        # --- 6. No requirements.txt: no pip call, tool still runs ---
        shutil.rmtree(worker.VENVS / TOOL, ignore_errors=True)
        fake = FakeShell()
        worker.sh = fake
        seed_repo(None)
        status, _ = worker.run_tool(TOOL, "POUL.CA", "true",
                                    HEX40, "yahooquery-runner")
        check("no requirements.txt still returns ok", status == "ok")
        check("no requirements.txt means no pip call",
              len(fake.pip_runs) == 0)
        check("no requirements.txt still runs the tool",
              len(fake.tool_runs) == 1)
        status, _ = worker.run_tool(TOOL, "POUL.CA", "true",
                                    HEX40, "yahooquery-runner")
        check("no requirements.txt is not reinstalled either",
              len(fake.pip_runs) == 0 and fake.venv_runs == 1)

        # --- 7. A pre-fix venv (python, no marker) is rebuilt ---
        # Simulates the live case: a venv created by the old code,
        # whose deps predate the current requirements.
        shutil.rmtree(worker.VENVS / TOOL, ignore_errors=True)
        fake = FakeShell()
        worker.sh = fake
        seed_repo(REQ_V2)
        venv = worker.VENVS / TOOL
        (venv / "bin").mkdir(parents=True, exist_ok=True)
        (venv / "bin" / "python").write_text("#!/bin/sh\n")
        status, _ = worker.run_tool(TOOL, "POUL.CA", "true",
                                    HEX40, "yahooquery-runner")
        check("pre-fix venv without a marker is rebuilt",
              status == "ok" and len(fake.pip_runs) == 1
              and fake.pip_runs[0][1] == REQ_V2.encode())
    finally:
        worker.sh = real_sh

    # _TMP is tracked by _test_tmp (#388): the shared atexit handler
    # removes it on normal exit and preserves it when
    # GATOR_TEST_KEEP_TMP=1. Do not delete it here (#405, same
    # retention defeat as #147 fixed by #401).
    print(f"\n{PASSED}/{TOTAL} passed")
    return 0 if PASSED == TOTAL else 1


if __name__ == "__main__":
    sys.exit(main())
