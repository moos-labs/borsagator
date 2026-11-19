#!/usr/bin/env python3
"""Unit tests for issue #161: a refused/failed recompile leaves an
older report-model.json in place, and a stale compile_error.txt is
never cleared on success.

Before the fix, main() wrote only compile_error.txt on a
CompileError and returned 2 -- the previous report-model.json in
that dir was untouched -- and on success it never removed
error_path. A file-presence consumer could therefore use the old
model (or the stale error) as current. The fix quarantines the
previous model before compiling, writes the new model atomically
(temp file + os.replace), and clears the error marker on success.

Drives the real CLI (subprocess) on a minimal probe-shape sweep
dir in a temp dir. Stdlib only, no network, no fixtures. Run:
    python3 scripts/test_compile_model_161.py
Exit 0 only when every test passes.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)

import compile_model  # noqa: E402

RESULTS = []

ARCHIVE_SHA = "0" * 40
COMPILER_SHA = "1" * 40


def check(name, fn):
    try:
        fn()
    except Exception as e:
        RESULTS.append((name, False, f"{type(e).__name__}: {e}"))
        print(f"FAIL {name}: {type(e).__name__}: {e}")
        return
    RESULTS.append((name, True, ""))
    print(f"PASS {name}")


def write_json(path, obj):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(obj, handle, indent=2)
        handle.write("\n")


def make_sweep(base):
    """A minimal probe-shape sweep dir that compiles cleanly."""
    sweep = os.path.join(base, "sweep")
    os.makedirs(sweep)
    write_json(os.path.join(sweep, "digest.json"), {
        "ticker": "POUL.CA", "job": "probe POUL.CA",
        "date": "2026-11-17", "finished": "2026-11-17T10:00:00Z",
        "results": []})
    return sweep


def run_compiler(sweep_dir, extra=()):
    cmd = [sys.executable,
           os.path.join(SCRIPTS, "compile_model.py"),
           sweep_dir, "--repo-root", ROOT,
           "--archive-sha", ARCHIVE_SHA,
           "--compiler-sha", COMPILER_SHA]
    cmd += list(extra)
    proc = subprocess.run(cmd, capture_output=True, text=True,
                          timeout=120)
    return proc.returncode, proc.stdout + proc.stderr


def break_digest(sweep_dir):
    """Mutate the digest so the recompile is refused (no ticker)."""
    path = os.path.join(sweep_dir, "digest.json")
    doc = json.load(open(path, encoding="utf-8"))
    del doc["ticker"]
    write_json(path, doc)


def fix_digest(sweep_dir):
    path = os.path.join(sweep_dir, "digest.json")
    doc = json.load(open(path, encoding="utf-8"))
    doc["ticker"] = "POUL.CA"
    write_json(path, doc)


# --- #161: refused recompile must not leave a stale model --------

def test_refused_recompile_quarantines_old_model():
    base = tempfile.mkdtemp(prefix="test161-")
    try:
        sweep = make_sweep(base)
        model_path = os.path.join(sweep, "report-model.json")
        error_path = os.path.join(sweep, "compile_error.txt")
        quarantined = model_path + ".quarantined"
        code, out = run_compiler(sweep)
        assert code == 0, f"first compile exit={code}: {out[-300:]}"
        assert os.path.isfile(model_path), "first compile: no model"
        first_bytes = open(model_path, "rb").read()

        break_digest(sweep)
        code, out = run_compiler(sweep)
        assert code == 2, f"refused recompile exit={code}: {out[-300:]}"
        assert os.path.isfile(error_path), \
            "refused recompile: no compile_error.txt"
        assert not os.path.isfile(model_path), \
            "STALE model still consumable as current after refusal"
        assert os.path.isfile(quarantined), \
            "previous model was not quarantined for inspection"
        assert open(quarantined, "rb").read() == first_bytes, \
            "quarantined copy is not the previous model"
    finally:
        shutil.rmtree(base, ignore_errors=True)


def test_success_after_failure_clears_stale_error():
    base = tempfile.mkdtemp(prefix="test161-")
    try:
        sweep = make_sweep(base)
        model_path = os.path.join(sweep, "report-model.json")
        error_path = os.path.join(sweep, "compile_error.txt")
        code, out = run_compiler(sweep)
        assert code == 0, f"first compile exit={code}: {out[-300:]}"
        break_digest(sweep)
        code, out = run_compiler(sweep)
        assert code == 2, f"refused recompile exit={code}: {out[-300:]}"
        assert os.path.isfile(error_path), "no error marker to clear"

        fix_digest(sweep)
        code, out = run_compiler(sweep)
        assert code == 0, f"recovery compile exit={code}: {out[-300:]}"
        assert os.path.isfile(model_path), "recovery compile: no model"
        assert not os.path.isfile(error_path), \
            "STALE compile_error.txt survived a successful compile"
        assert not os.path.isfile(model_path + ".tmp"), \
            "temp file left behind after a successful write"
    finally:
        shutil.rmtree(base, ignore_errors=True)


def test_fail_then_success_leaves_no_stale_files():
    """The issue's proof bar, end to end on one sweep dir."""
    base = tempfile.mkdtemp(prefix="test161-")
    try:
        sweep = make_sweep(base)
        model_path = os.path.join(sweep, "report-model.json")
        error_path = os.path.join(sweep, "compile_error.txt")
        code, _ = run_compiler(sweep)
        assert code == 0
        first = json.load(open(model_path, encoding="utf-8"))
        break_digest(sweep)
        code, _ = run_compiler(sweep)
        assert code == 2
        assert not os.path.isfile(model_path)
        fix_digest(sweep)
        code, out = run_compiler(sweep)
        assert code == 0, f"recovery compile: {out[-300:]}"
        assert os.path.isfile(model_path)
        assert not os.path.isfile(error_path)
        second = json.load(open(model_path, encoding="utf-8"))
        assert second["ticker"] == "POUL.CA"
        assert second["schema"] == "borsagator-report-model/2"
        # The recovered model is the current compile's result, not
        # a resurrected copy of the first one.
        assert second["provenance"]["compiler_sha"] == COMPILER_SHA
        assert second["archive_commit"] == ARCHIVE_SHA
        assert first["provenance"]["compiler_sha"] == COMPILER_SHA
    finally:
        shutil.rmtree(base, ignore_errors=True)


def test_model_binds_to_source_hashes():
    base = tempfile.mkdtemp(prefix="test161-")
    try:
        sweep = make_sweep(base)
        code, out = run_compiler(sweep)
        assert code == 0, f"compile exit={code}: {out[-300:]}"
        model = json.load(open(os.path.join(
            sweep, "report-model.json"), encoding="utf-8"))
        assert model["archive_commit"] == ARCHIVE_SHA
        assert model["provenance"]["compiler_sha"] == COMPILER_SHA
        assert model["provenance"]["compiler"] == \
            compile_model.COMPILER_PATH
    finally:
        shutil.rmtree(base, ignore_errors=True)


def test_check_model_does_not_mutate_dir():
    """--check-model is a read-only consumer check: it must not
    quarantine the model or clear the error marker."""
    base = tempfile.mkdtemp(prefix="test161-")
    try:
        sweep = make_sweep(base)
        model_path = os.path.join(sweep, "report-model.json")
        error_path = os.path.join(sweep, "compile_error.txt")
        code, _ = run_compiler(sweep)
        assert code == 0
        write_json(error_path, "stale marker (planted)\n")
        before = open(model_path, "rb").read()
        proc = subprocess.run(
            [sys.executable, os.path.join(SCRIPTS, "compile_model.py"),
             "--check-model", model_path],
            capture_output=True, text=True, timeout=120)
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert open(model_path, "rb").read() == before, \
            "--check-model moved the model"
        assert os.path.isfile(error_path), \
            "--check-model cleared the error marker"
        assert not os.path.isfile(model_path + ".quarantined"), \
            "--check-model quarantined the model"
    finally:
        shutil.rmtree(base, ignore_errors=True)


def test_dump_model_atomic_no_partial_on_write_failure():
    """dump_model must never leave a partial report-model.json or
    a temp file behind when the move into place fails."""
    base = tempfile.mkdtemp(prefix="test161-")
    try:
        out_path = os.path.join(base, "report-model.json")
        tmp_path = out_path + ".tmp"
        real_replace = os.replace

        def failing_replace(src, dst):
            raise OSError("simulated replace failure")

        os.replace = failing_replace
        try:
            try:
                compile_model.dump_model({"a": 1}, out_path)
            except OSError:
                pass
            else:
                raise AssertionError(
                    "dump_model swallowed the replace failure")
        finally:
            os.replace = real_replace
        assert not os.path.isfile(out_path), \
            "partial model left behind after a failed write"
        assert not os.path.isfile(tmp_path), \
            "temp file left behind after a failed write"

        # And a successful dump leaves no temp file either.
        compile_model.dump_model({"a": 1}, out_path)
        assert os.path.isfile(out_path)
        assert not os.path.isfile(tmp_path)
        assert json.load(open(out_path, encoding="utf-8")) == {"a": 1}
    finally:
        shutil.rmtree(base, ignore_errors=True)


def main():
    check("refused recompile quarantines the old model",
          test_refused_recompile_quarantines_old_model)
    check("success after failure clears the stale error marker",
          test_success_after_failure_clears_stale_error)
    check("fail-then-success leaves no stale model or error",
          test_fail_then_success_leaves_no_stale_files)
    check("compiled model binds to source hashes",
          test_model_binds_to_source_hashes)
    check("--check-model does not mutate the sweep dir",
          test_check_model_does_not_mutate_dir)
    check("dump_model is atomic: no partial file on write failure",
          test_dump_model_atomic_no_partial_on_write_failure)
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    print(f"\ntest_compile_model_161: {passed}/{len(RESULTS)} passed")
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
