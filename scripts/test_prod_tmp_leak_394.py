#!/usr/bin/env python3
"""Regression tests for issue #394: production tempdir leaks.

Gap 1 — scripts/ledger_publish.py created one
`tempfile.mkdtemp(prefix="ledger-run-")` per publish attempt and
never removed it (no `shutil.rmtree` in the file): every guard
tick leaked a tempdir on the worker. The fix owns the attempt
tempdir with `tempfile.TemporaryDirectory`, so it is removed on
every exit path — success, fail, retry, exception, interrupt.

Gap 2 — scripts/diag_egx_ab.py created one
`tempfile.mkdtemp(prefix="diag-egx-ab-prof-")` per --dry-run and
never removed it. The fix removes the auto-created profile dir
in a `finally`; a user-supplied --profile is never removed.

These tests drive the REAL publish() (with its git / ledger-run
internals stubbed — no network, no real checkout) and the REAL
diag script as a subprocess, and assert no `ledger-run-*` /
`diag-egx-ab-prof-*` residue is left behind.

Stdlib only. Run directly:
    TMPDIR=<scratch>/tmp python3 scripts/test_prod_tmp_leak_394.py
The TMPDIR must point under a scratch dir, never the shared /tmp
(issue #388: worker tests leak hundreds of MB into /tmp).
Exit 0 only when every test passes.
"""
import builtins
import glob
import json
import os
import socket
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import diag_egx_ab as diag  # noqa: E402
import ledger_publish as pub  # noqa: E402

RESULTS = []


def check(name, fn):
    try:
        fn()
    except Exception as e:
        RESULTS.append((name, False, f"{type(e).__name__}: {e}"))
        print(f"FAIL {name}: {type(e).__name__}: {e}")
        return
    RESULTS.append((name, True, ""))
    print(f"PASS {name}")


def _doc():
    return {"source": {"tree_sha": "a" * 40, "commit_sha": "b" * 40},
            "counts": {"forecasts": 5, "matured": 2,
                       "pending": 2, "invalid": 1}}


def _write_fake_ledger(ledger_dir):
    """A committed ledger tree publish() can byte-compare against."""
    os.makedirs(ledger_dir, exist_ok=True)
    files = {
        "ledger.json": json.dumps(_doc()).encode(),
        "ledger.md": b"# ledger\n",
        "weights.json": b"{}\n",
        "benchmark.json": json.dumps(
            {"counts": {"entrant_rows": 0, "matured": 0,
                        "sweeps_with_freeze": 0}}).encode(),
        "benchmark.md": b"# benchmark\n",
    }
    for name, data in files.items():
        with open(os.path.join(ledger_dir, name), "wb") as f:
            f.write(data)
    return files


class LedgerHarness:
    """Drive the real publish() with stubbed side effects.

    The publish attempt tempdirs land in residue_dir (via
    tempfile.tempdir); the harness asserts it is empty afterwards.
    """

    def __init__(self, scratch):
        self.scratch = scratch
        self.residue_dir = os.path.join(scratch, "tmp")
        os.makedirs(self.residue_dir, exist_ok=True)
        self.ledger_dir = os.path.join(scratch, "ledger")
        self.old_files = _write_fake_ledger(self.ledger_dir)
        self.digest = os.path.join(scratch, "digest.md")
        with open(self.digest, "w", encoding="utf-8") as f:
            f.write("# digest\n")
        self.calls = {"run_ledger": 0, "git_publish": 0}
        self.git_publish_results = [True]
        self.run_ledger_mode = "identical"  # identical|changed|raise|omit
        self.omit = None
        self._saved = {}

    def _run_ledger(self, out_dir, committed=None):
        self.calls["run_ledger"] += 1
        if self.run_ledger_mode == "raise":
            raise RuntimeError("simulated ledger.py failure")
        for name in pub.FILES:
            if name == self.omit:
                continue
            data = self.old_files[name]
            if self.run_ledger_mode == "changed" and \
                    name == "ledger.json":
                data = (b"ledger-attempt-%d\n"
                        % self.calls["run_ledger"])
            with open(os.path.join(out_dir, name), "wb") as f:
                f.write(data)
        return _doc()

    def _git_publish(self, new_doc):
        self.calls["git_publish"] += 1
        return self.git_publish_results.pop(0) \
            if self.git_publish_results else True

    def __enter__(self):
        self._saved = {
            "LEDGER_DIR": pub.LEDGER_DIR,
            "RETRY_DELAY_BASE_S": pub.RETRY_DELAY_BASE_S,
            "RETRY_DELAY_JITTER_S": pub.RETRY_DELAY_JITTER_S,
            "ensure_clean_checkout": pub.ensure_clean_checkout,
            "live_archive_commit_sha": pub.live_archive_commit_sha,
            "run_ledger": pub.run_ledger,
            "git_publish": pub.git_publish,
            "git": pub.git,
            "tempdir": tempfile.tempdir,
            "GH_TOKEN": os.environ.pop("GH_TOKEN", None),
            "GITHUB_TOKEN": os.environ.pop("GITHUB_TOKEN", None),
        }
        pub.LEDGER_DIR = self.ledger_dir
        pub.RETRY_DELAY_BASE_S = 0
        pub.RETRY_DELAY_JITTER_S = 0
        pub.ensure_clean_checkout = lambda: (True, "")
        pub.live_archive_commit_sha = lambda: None
        pub.run_ledger = self._run_ledger
        pub.git_publish = self._git_publish
        pub.git = lambda *a: SimpleNamespace(returncode=0,
                                              stdout="", stderr="")
        tempfile.tempdir = self.residue_dir
        return self

    def __exit__(self, *exc):
        pub.LEDGER_DIR = self._saved["LEDGER_DIR"]
        pub.RETRY_DELAY_BASE_S = self._saved["RETRY_DELAY_BASE_S"]
        pub.RETRY_DELAY_JITTER_S = self._saved["RETRY_DELAY_JITTER_S"]
        pub.ensure_clean_checkout = self._saved["ensure_clean_checkout"]
        pub.live_archive_commit_sha = \
            self._saved["live_archive_commit_sha"]
        pub.run_ledger = self._saved["run_ledger"]
        pub.git_publish = self._saved["git_publish"]
        pub.git = self._saved["git"]
        tempfile.tempdir = self._saved["tempdir"]
        for key in ("GH_TOKEN", "GITHUB_TOKEN"):
            if self._saved[key] is not None:
                os.environ[key] = self._saved[key]
        return False

    def residue(self):
        return glob.glob(os.path.join(self.residue_dir,
                                      "ledger-run-*"))


def test_publish_unchanged_no_residue():
    with tempfile.TemporaryDirectory(
            prefix="test-394-ledger-") as scratch:
        with LedgerHarness(scratch) as h:
            rc = pub.publish(False, h.digest, False)
            assert rc == 0, rc
            assert h.residue() == [], h.residue()


def test_publish_changed_no_commit_no_residue():
    with tempfile.TemporaryDirectory(
            prefix="test-394-ledger-") as scratch:
        with LedgerHarness(scratch) as h:
            h.run_ledger_mode = "changed"
            rc = pub.publish(False, h.digest, False)
            assert rc == 0, rc
            assert h.residue() == [], h.residue()
            # The changed path really ran: the new bytes were copied
            # into the (fake) committed ledger dir.
            with open(os.path.join(h.ledger_dir,
                                   "ledger.json"), "rb") as f:
                assert f.read().startswith(b"ledger-attempt-")


def test_publish_run_ledger_raises_no_residue():
    with tempfile.TemporaryDirectory(
            prefix="test-394-ledger-") as scratch:
        with LedgerHarness(scratch) as h:
            h.run_ledger_mode = "raise"
            rc = pub.publish(False, h.digest, False)
            assert rc == 0, rc  # fail() warns-only without --fail-hard
            assert h.residue() == [], h.residue()


def test_publish_missing_output_no_residue():
    with tempfile.TemporaryDirectory(
            prefix="test-394-ledger-") as scratch:
        with LedgerHarness(scratch) as h:
            h.omit = "benchmark.md"
            rc = pub.publish(False, h.digest, False)
            assert rc == 0, rc
            assert h.residue() == [], h.residue()


def test_publish_retry_no_residue():
    with tempfile.TemporaryDirectory(
            prefix="test-394-ledger-") as scratch:
        with LedgerHarness(scratch) as h:
            h.run_ledger_mode = "changed"
            h.git_publish_results = [False, True]
            rc = pub.publish(True, h.digest, False)
            assert rc == 0, rc
            assert h.calls["run_ledger"] == 2, h.calls
            assert h.calls["git_publish"] == 2, h.calls
            assert h.residue() == [], h.residue()


def test_publish_unexpected_exception_no_residue():
    with tempfile.TemporaryDirectory(
            prefix="test-394-ledger-") as scratch:
        with LedgerHarness(scratch) as h:
            def _boom():
                raise RuntimeError("simulated archive lookup failure")
            pub.live_archive_commit_sha = _boom
            try:
                pub.publish(False, h.digest, False)
            except RuntimeError:
                pass
            else:
                raise AssertionError("expected the exception to escape")
            assert h.residue() == [], h.residue()


def _diag_residue(tmpdir):
    return glob.glob(os.path.join(tmpdir, "diag-egx-ab-prof-*"))


def test_dry_run_no_profile_residue():
    with tempfile.TemporaryDirectory(
            prefix="test-394-diag-") as scratch:
        tmpdir = os.path.join(scratch, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        out = os.path.join(scratch, "out")
        env = dict(os.environ, TMPDIR=tmpdir)
        proc = subprocess.run(
            [sys.executable, os.path.join(HERE, "diag_egx_ab.py"),
             "--dry-run", "--out-dir", out],
            capture_output=True, text=True, timeout=120,
            env=env, cwd=scratch)
        try:
            import playwright  # noqa: F401
            have_pw = True
        except ImportError:
            have_pw = False
        if not have_pw:
            assert proc.returncode != 0, proc.stdout + proc.stderr
            assert "playwright" in (proc.stderr + proc.stdout).lower(), \
                proc.stdout + proc.stderr
        else:
            assert proc.returncode == 0, proc.stdout + proc.stderr
            rec = json.loads(open(os.path.join(
                out, "diag-egx-ab.json"), encoding="utf-8").read())
            assert rec["verdict"] == "not-reproduced", rec["verdict"]
        assert _diag_residue(tmpdir) == [], _diag_residue(tmpdir)


def test_dry_run_keeps_explicit_profile():
    with tempfile.TemporaryDirectory(
            prefix="test-394-diag-") as scratch:
        tmpdir = os.path.join(scratch, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        profile = os.path.join(scratch, "explicit-prof")
        os.makedirs(profile)
        marker = os.path.join(profile, "keep-me.txt")
        with open(marker, "w", encoding="utf-8") as f:
            f.write("user-supplied profile\n")
        out = os.path.join(scratch, "out")
        env = dict(os.environ, TMPDIR=tmpdir)
        proc = subprocess.run(
            [sys.executable, os.path.join(HERE, "diag_egx_ab.py"),
             "--dry-run", "--profile", profile, "--out-dir", out],
            capture_output=True, text=True, timeout=120,
            env=env, cwd=scratch)
        assert os.path.isdir(profile), \
            "explicit --profile must never be removed"
        assert os.path.exists(marker), "explicit profile contents kept"
        assert _diag_residue(tmpdir) == [], _diag_residue(tmpdir)


def _run_main_with_stub_print_failure(argv, tmpdir):
    """Run the REAL diag main() with the dry-run stub print raising
    BrokenPipeError (closed-pipe stdout). Returns (srv, base, error):
    the stub server that was started and the BrokenPipeError main()
    raised (or None if it did not raise). The auto-created profile
    dir lands in tmpdir (via tempfile.tempdir)."""
    saved_tempdir = tempfile.tempdir
    saved_print = builtins.print
    saved_start = diag.start_stub_server
    seen = {}

    def _start_stub_server():
        srv, base = saved_start()
        seen["srv"] = srv
        seen["base"] = base
        return srv, base

    def _failing_print(*args, **kwargs):
        if args and isinstance(args[0], str) and \
                args[0].startswith("dry-run: stub at"):
            raise BrokenPipeError("simulated closed-pipe stdout")
        return saved_print(*args, **kwargs)

    tempfile.tempdir = tmpdir
    builtins.print = _failing_print
    diag.start_stub_server = _start_stub_server
    error = None
    try:
        diag.main(argv)
    except BrokenPipeError as e:
        error = e
    finally:
        builtins.print = saved_print
        diag.start_stub_server = saved_start
        tempfile.tempdir = saved_tempdir
    return seen.get("srv"), seen.get("base"), error


def _assert_stub_server_down(base):
    port = urlparse(base).port
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=2):
            raise AssertionError(
                "stub server on port %d still accepting after "
                "setup failure" % port)
    except (ConnectionRefusedError, OSError):
        pass


def test_dry_run_stub_print_failure_removes_auto_profile():
    """CodeRabbit Minor on PR #397: the stub print used to run before
    the cleanup try/finally, so a BrokenPipeError there leaked the
    auto-created profile dir. It must now be removed, and the stub
    server shut down."""
    with tempfile.TemporaryDirectory(
            prefix="test-394-diag-") as scratch:
        tmpdir = os.path.join(scratch, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        out = os.path.join(scratch, "out")
        _srv, base, err = _run_main_with_stub_print_failure(
            ["--dry-run", "--out-dir", out], tmpdir)
        assert isinstance(err, BrokenPipeError), \
            "expected BrokenPipeError from the stub print, got %r" % err
        assert base is not None, "stub server was never started"
        assert _diag_residue(tmpdir) == [], _diag_residue(tmpdir)
        _assert_stub_server_down(base)


def test_dry_run_stub_print_failure_keeps_explicit_profile():
    """Same setup failure, but with a user-supplied --profile: the
    explicit profile must survive untouched."""
    with tempfile.TemporaryDirectory(
            prefix="test-394-diag-") as scratch:
        tmpdir = os.path.join(scratch, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        profile = os.path.join(scratch, "explicit-prof")
        os.makedirs(profile)
        marker = os.path.join(profile, "keep-me.txt")
        with open(marker, "w", encoding="utf-8") as f:
            f.write("user-supplied profile\n")
        out = os.path.join(scratch, "out")
        _srv, base, err = _run_main_with_stub_print_failure(
            ["--dry-run", "--profile", profile, "--out-dir", out],
            tmpdir)
        assert isinstance(err, BrokenPipeError), \
            "expected BrokenPipeError from the stub print, got %r" % err
        assert os.path.isdir(profile), \
            "explicit --profile must never be removed"
        assert os.path.exists(marker), "explicit profile contents kept"
        assert _diag_residue(tmpdir) == [], _diag_residue(tmpdir)


TESTS = [
    ("publish unchanged leaves no ledger-run-* residue",
     test_publish_unchanged_no_residue),
    ("publish changed (no commit) leaves no residue",
     test_publish_changed_no_commit_no_residue),
    ("publish run_ledger raises leaves no residue",
     test_publish_run_ledger_raises_no_residue),
    ("publish missing output leaves no residue",
     test_publish_missing_output_no_residue),
    ("publish retry (fail then succeed) leaves no residue",
     test_publish_retry_no_residue),
    ("publish unexpected exception leaves no residue",
     test_publish_unexpected_exception_no_residue),
    ("dry-run leaves no diag-egx-ab-prof-* residue",
     test_dry_run_no_profile_residue),
    ("dry-run keeps an explicit --profile",
     test_dry_run_keeps_explicit_profile),
    ("dry-run stub print failure removes auto-created profile",
     test_dry_run_stub_print_failure_removes_auto_profile),
    ("dry-run stub print failure keeps an explicit --profile",
     test_dry_run_stub_print_failure_keeps_explicit_profile),
]


def main():
    for name, fn in TESTS:
        check(name, fn)
    failed = [n for n, ok, _ in RESULTS if not ok]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} passed")
    if failed:
        for name, _ok, detail in RESULTS:
            if not _ok:
                print(f"  FAILED: {name}: {detail}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
