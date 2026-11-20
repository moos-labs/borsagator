#!/usr/bin/env python3
"""Regression tests for issue #398 (#390 follow-up): the compile
hook's --archive-sha git call is unguarded — a timeout aborts the
compile (same class as #390).

Gap (issue body): worker/worker.py maybe_compile() calls
subprocess.run(["git", "-C", str(arch), "rev-parse", "HEAD"],
timeout=30) with no try/except. A TimeoutExpired (or OSError)
raises out of maybe_compile before the compile even runs — the
sweep's report-model step fails instead of compiling with
archive-sha-unavailable, which the surrounding comment explicitly
anticipates as the fallback ("omit the flag and let the compiler
record archive-sha-unavailable rather than guess"). #390's fix
covers update_checkout_sha() (--compiler-sha) but not this call.

Fix under test: the archive lookup is guarded the same way as
#390 — on TimeoutExpired/OSError the flag is omitted and the
compiler records archive-sha-unavailable (archive_commit None
plus the archive-sha-unavailable flag in the model). A failed
diagnostic lookup must never abort the compile.

Harness-first: FAILS on pristine main (a simulated git timeout /
missing git makes maybe_compile return False with status "error"
— "compile timed out" / "compile hook failed" — and no model is
written) and PASSES on the fixed tree. Stdlib only. The real
compile_model.py runs (a copy of the repo's scripts/ under the
fake release checkout) against a minimal sweep dir; only the
archive-push rev-parse call is faked (simulated timeout /
missing git / non-zero exit / success), everything else runs
for real. The --compiler-sha lookup is deliberately NOT faked:
it is #390's territory (a separate open PR) and must keep
behaving as on main (empty string: the fake release checkout
is not a git repo).

Run: python3 worker/test_worker_398.py (exit 0 = all pass).
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="gator398-test-"))
os.environ["GATOR_ROOT"] = str(_TMP)

_HERE = Path(os.path.abspath(__file__)).parent
_REPO = _HERE.parent
sys.path.insert(0, str(_HERE))

import worker  # noqa: E402

PASSED = 0
FAKE_MODE = {"mode": "timeout"}
_REAL_RUN = subprocess.run
_FAKE_SHA = "deadbeef" * 5
_NO_SHA_FLAG = ("archive-sha-unavailable: sweep dir is not a git "
                "checkout and no --archive-sha was given")


def check(name, cond):
    global PASSED
    assert cond, name
    PASSED += 1
    print(f"pass: {name}")


def fake_run(cmd, **kw):
    """Fake subprocess.run: only the archive-push rev-parse
    (list argv, exact archive-push path) fails per FAKE_MODE;
    every other call — including the compiler itself, its
    --check-model run and the --compiler-sha lookup (a string
    shell command via sh()) — runs for real."""
    if (isinstance(cmd, list) and len(cmd) == 5
            and cmd[0] == "git" and cmd[1] == "-C"
            and cmd[2] == str(worker.ROOT / "archive-push")
            and cmd[3] == "rev-parse" and cmd[4] == "HEAD"):
        mode = FAKE_MODE["mode"]
        if mode == "timeout":
            raise subprocess.TimeoutExpired(cmd, 30)
        if mode == "missing-git":
            raise FileNotFoundError(2, "No such file or "
                                       "directory", "git")
        if mode == "nonzero":
            return subprocess.CompletedProcess(
                cmd, 1, stdout="", stderr="fatal: not a git repo")
        if mode == "ok":
            return subprocess.CompletedProcess(
                cmd, 0, stdout=_FAKE_SHA + "\n", stderr="")
        raise AssertionError(f"unknown FAKE_MODE {mode!r}")
    return _REAL_RUN(cmd, **kw)


def setup_release():
    """Fake release checkout: the real compiler scripts, so
    maybe_compile runs the real compile_model.py."""
    code = worker.CODE
    shutil.copytree(_REPO / "scripts", code / "scripts")
    (worker.ROOT / "archive-push").mkdir(parents=True, exist_ok=True)


def make_sweep(workdir, rel):
    """Minimal sweep dir: digest + ensemble, the #155 shape —
    enough for the real compiler to write a model."""
    sweep_dir = Path(workdir) / "_merge_out" / rel
    sweep_dir.mkdir(parents=True, exist_ok=True)
    digest = {"job": "run yahooquery POUL.CA market=EGX",
              "ticker": "POUL.CA", "date": "2026-11-18",
              "started": "2026-11-18T06:00:00Z",
              "finished": "2026-11-18T07:00:00Z", "results": []}
    ensemble = {"ticker": "POUL.CA", "base_price": 8.02,
                "base_date": "2026-11-18",
                "base_source": "consensus median",
                "sigma_daily": 0.012,
                "family_scores": {"price": 0.5},
                "horizons": {"week": {"expected_move_pct": 1.5,
                                      "range_low_pct": -2.0,
                                      "range_high_pct": 2.0}},
                "risk": {"note": "x", "value": 0.3},
                "corporate_actions": []}
    (sweep_dir / "digest.json").write_text(json.dumps(digest))
    (sweep_dir / "ensemble.json").write_text(json.dumps(ensemble))
    return sweep_dir


def run_compile(workdir, rel):
    """Run the real maybe_compile against one fresh sweep dir;
    returns (ok, manifest, model-or-None)."""
    job = {"job": "sweep POUL.CA market=EGX"}
    manifest = {"merge": {"status": "complete", "sweep_dir": rel}}
    ok = worker.maybe_compile(job, str(workdir), manifest, ["x"])
    model_path = (Path(workdir) / "_merge_out" / rel
                  / "report-model.json")
    model = (json.loads(model_path.read_text())
             if model_path.is_file() else None)
    return ok, manifest, model


def check_compiled_without_sha(name, ok, manifest, model):
    """Shared assertions: the compile still ran and the model
    records archive-sha-unavailable (archive_commit None +
    the flag), exactly the fallback the hook's comment names."""
    check(f"{name}: maybe_compile returns True (the compile "
          "ran, the lookup failure did not abort it)",
          ok is True)
    check(f"{name}: manifest records status compiled",
          manifest.get("compile", {}).get("status") == "compiled")
    check(f"{name}: report-model.json was written",
          model is not None)
    check(f"{name}: archive_commit is None (no --archive-sha "
          "was passed)", model.get("archive_commit") is None)
    check(f"{name}: model flags record archive-sha-unavailable",
          _NO_SHA_FLAG in (model.get("flags") or []))


def test_git_timeout_still_compiles():
    FAKE_MODE["mode"] = "timeout"
    workdir = _TMP / "w-timeout"
    sweep = make_sweep(workdir, "sweep-timeout")
    ok, manifest, model = run_compile(workdir, "sweep-timeout")
    check_compiled_without_sha(
        "git timeout in the archive-push clone", ok, manifest, model)


def test_missing_git_still_compiles():
    FAKE_MODE["mode"] = "missing-git"
    workdir = _TMP / "w-nogit"
    make_sweep(workdir, "sweep-nogit")
    ok, manifest, model = run_compile(workdir, "sweep-nogit")
    check_compiled_without_sha(
        "missing git in the archive-push clone", ok, manifest, model)


def test_nonzero_exit_still_compiles():
    # Pre-existing fallback (non-zero exit / empty output omits
    # the flag); the guard must not change it.
    FAKE_MODE["mode"] = "nonzero"
    workdir = _TMP / "w-nonzero"
    make_sweep(workdir, "sweep-nonzero")
    ok, manifest, model = run_compile(workdir, "sweep-nonzero")
    check_compiled_without_sha(
        "non-zero git exit in the archive-push clone",
        ok, manifest, model)


def test_successful_lookup_still_passes_sha():
    FAKE_MODE["mode"] = "ok"
    workdir = _TMP / "w-ok"
    make_sweep(workdir, "sweep-ok")
    ok, manifest, model = run_compile(workdir, "sweep-ok")
    check("working git: maybe_compile returns True", ok is True)
    check("working git: manifest records status compiled",
          manifest.get("compile", {}).get("status") == "compiled")
    check("working git: report-model.json was written",
          model is not None)
    check("working git: --archive-sha is still passed through "
          "when the lookup succeeds",
          model.get("archive_commit") == _FAKE_SHA)
    check("working git: no archive-sha-unavailable flag",
          _NO_SHA_FLAG not in (model.get("flags") or []))


def test_no_archive_push_dir_still_compiles():
    # Pre-existing behaviour: with no archive-push clone at all
    # the flag is omitted and the compiler records unavailable.
    FAKE_MODE["mode"] = "ok"
    shutil.rmtree(worker.ROOT / "archive-push")
    workdir = _TMP / "w-nodir"
    make_sweep(workdir, "sweep-nodir")
    ok, manifest, model = run_compile(workdir, "sweep-nodir")
    check_compiled_without_sha(
        "no archive-push clone at all", ok, manifest, model)


def main():
    setup_release()
    subprocess.run = fake_run
    try:
        test_git_timeout_still_compiles()
        test_missing_git_still_compiles()
        test_nonzero_exit_still_compiles()
        test_successful_lookup_still_passes_sha()
        test_no_archive_push_dir_still_compiles()
    finally:
        subprocess.run = _REAL_RUN
    print(f"\n{PASSED} passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
