#!/usr/bin/env python3
"""Regression tests for issue #421 (#406 follow-up): the archive
lookup loses diagnostic state on UnicodeDecodeError from
git rev-parse.

Gap (issue body, Ins INS-REVIEW-005): in maybe_compile the
archive `git rev-parse HEAD` subprocess call (text=True) catches
only (subprocess.TimeoutExpired, OSError). A UnicodeDecodeError
from undecodable git output escapes the local catch: the outer
handler aborts compilation with status error and no
archive_lookup field, although the lookup was attempted. This
requires abnormal undecodable git output.

Fix under test: a decode error from the rev-parse call is
handled locally as a lookup failure — archive_lookup records
"lookup-failed", the compile continues without --archive-sha
(the #398 behaviour), and genuine compiler failures stay
fail-closed with the lookup outcome still carried on the
fail-closed record.

Harness-first: FAILS on the pre-fix tree (the UnicodeDecodeError
escapes maybe_compile, so no compile record is written at all)
and PASSES on the fixed tree. Stdlib only. The real
compile_model.py runs (a copy of the repo's scripts/ under the
fake release checkout) against a minimal sweep dir; only the
archive-push rev-parse call is faked, everything else runs for
real — except the second test, which also fakes a failing
compiler to exercise the fail-closed tail.

Run: python3 worker/test_worker_421.py (exit 0 = all pass).
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="gator421-test-"))
os.environ["GATOR_ROOT"] = str(_TMP)

_HERE = Path(os.path.abspath(__file__)).parent
_REPO = _HERE.parent
sys.path.insert(0, str(_HERE))

import worker  # noqa: E402

PASSED = 0
FAKE_MODE = {"mode": "decode-error"}
_REAL_RUN = subprocess.run
_NO_SHA_FLAG = ("archive-sha-unavailable: sweep dir is not a git "
                "checkout and no --archive-sha was given")


def check(name, cond):
    global PASSED
    assert cond, name
    PASSED += 1
    print(f"pass: {name}")


def fake_run(cmd, **kw):
    """Fake subprocess.run: the archive-push rev-parse (list argv,
    exact archive-push path) raises UnicodeDecodeError per
    FAKE_MODE; the compiler call fails per FAKE_MODE in the
    fail-closed test; every other call runs for real."""
    if (isinstance(cmd, list) and len(cmd) == 5
            and cmd[0] == "git" and cmd[1] == "-C"
            and cmd[2] == str(worker.ROOT / "archive-push")
            and cmd[3] == "rev-parse" and cmd[4] == "HEAD"):
        mode = FAKE_MODE["mode"]
        if mode in ("decode-error", "decode-error-compiler-fails"):
            raise UnicodeDecodeError(
                "utf-8", b"\xff\xfe", 0, 1,
                "invalid start byte")
        raise AssertionError(f"unknown FAKE_MODE {mode!r}")
    if (FAKE_MODE["mode"] == "decode-error-compiler-fails"
            and isinstance(cmd, list) and len(cmd) >= 2
            and cmd[1].endswith("compile_model.py")
            and "--check-model" not in cmd):
        return subprocess.CompletedProcess(
            cmd, 1, stdout="", stderr="boom")
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


def test_decode_error_is_lookup_failed():
    # The decode error must not escape maybe_compile: the compile
    # runs, the model records the #398 fallback, and the manifest
    # distinguishes this lookup outcome as "lookup-failed".
    FAKE_MODE["mode"] = "decode-error"
    workdir = _TMP / "w-decode"
    make_sweep(workdir, "sweep-decode")
    ok, manifest, model = run_compile(workdir, "sweep-decode")
    check("decode error: maybe_compile returns True (the "
          "compile ran, the lookup outcome did not abort it)",
          ok is True)
    check("decode error: manifest records status compiled",
          manifest.get("compile", {}).get("status") == "compiled")
    check("decode error: report-model.json was written",
          model is not None)
    check("decode error: archive_commit is None (no "
          "--archive-sha was passed)",
          model.get("archive_commit") is None)
    check("decode error: model flags record "
          "archive-sha-unavailable",
          _NO_SHA_FLAG in (model.get("flags") or []))
    check("decode error: manifest records archive_lookup "
          "'lookup-failed' (distinct from the other cases)",
          manifest.get("compile", {}).get("archive_lookup")
          == "lookup-failed")


def test_decode_error_fail_closed_keeps_lookup():
    # A genuine compiler failure after a decode-error lookup
    # must stay fail-closed AND keep the lookup outcome on the
    # fail-closed record — the diagnostic must not be lost.
    FAKE_MODE["mode"] = "decode-error-compiler-fails"
    workdir = _TMP / "w-decode-fail"
    make_sweep(workdir, "sweep-decode-fail")
    ok, manifest, model = run_compile(workdir, "sweep-decode-fail")
    check("decode error + compiler failure: maybe_compile "
          "returns False (fail-closed, no unvalidated model)",
          ok is False)
    check("decode error + compiler failure: manifest records "
          "status error",
          manifest.get("compile", {}).get("status") == "error")
    check("decode error + compiler failure: no "
          "report-model.json survives",
          model is None)
    check("decode error + compiler failure: fail-closed record "
          "still carries archive_lookup 'lookup-failed'",
          manifest.get("compile", {}).get("archive_lookup")
          == "lookup-failed")


def main():
    setup_release()
    subprocess.run = fake_run
    try:
        test_decode_error_is_lookup_failed()
        test_decode_error_fail_closed_keeps_lookup()
    finally:
        subprocess.run = _REAL_RUN
    print(f"\n{PASSED} passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
