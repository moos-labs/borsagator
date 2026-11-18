#!/usr/bin/env python3
"""Unit tests for issue #163: digest_watch unreadable claims dir is
reported as missing.

Before the fix, `check()` in scripts/digest_watch_check.py swallowed
any OSError while probing the claim file (`except OSError: pass`) and
fell through to `status=missing`. An unreadable claims directory
therefore read exactly like "the worker never fired": a checker
outage looked like a missed sweep (and vice versa).

The fix returns a separate `claims-unavailable` status carrying the
underlying I/O error when the claim file cannot be inspected for a
reason other than absence, while an absent claims dir (or an absent
claim file) still yields `status=missing` and a readable claims dir
behaves exactly as before.

Stdlib only, no network, no fixtures. Run:
    python3 scripts/test_digest_watch_check_163.py
Exit 0 only when every test passes.
"""
import os
import sys
import tempfile
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)

import digest_watch_check as dwc  # noqa: E402

RESULTS = []
DATE = "2026-11-18"


def check(name, fn):
    try:
        fn()
    except Exception as e:
        RESULTS.append((name, False, f"{type(e).__name__}: {e}"))
        print(f"FAIL {name}: {type(e).__name__}: {e}")
        return
    RESULTS.append((name, True, ""))
    print(f"PASS {name}")


def _archive(tmp):
    """An empty archive dir for DATE (no sweep dirs at all)."""
    day = Path(tmp) / "worker-runs" / DATE
    day.mkdir(parents=True)
    return Path(tmp) / "worker-runs"


def test_unreadable_claims_dir_is_claims_unavailable():
    # The claims dir exists but the claim file cannot be inspected:
    # here claims_dir is a regular FILE, so stat() of the claim path
    # raises NotADirectoryError -- a genuine OSError from the OS,
    # deterministic for any user (unlike chmod, which root ignores).
    # The status must be claims-unavailable and must carry the error,
    # never the missing-sweep signal.
    with tempfile.TemporaryDirectory() as tmp:
        archive = _archive(tmp)
        claims_file = Path(tmp) / "claims"
        claims_file.write_text("not a directory\n")
        code, line = dwc.check(DATE, archive, claims_file)
        assert code == 1, f"expected exit 1, got {code} {line}"
        assert line.startswith("status=claims-unavailable"), line
        assert "error=" in line and len(line.split("error=", 1)[1]) > 0, \
            f"status must carry the I/O error: {line}"


def test_unreadable_claims_dir_chmod():
    # The production shape: a claims dir with no permissions. stat()
    # of the claim raises PermissionError (EACCES). Skipped for root,
    # which bypasses permission bits.
    if os.geteuid() == 0:
        print("SKIP unreadable_claims_dir_chmod (running as root)")
        return
    with tempfile.TemporaryDirectory() as tmp:
        archive = _archive(tmp)
        claims = Path(tmp) / "claims"
        claims.mkdir()
        os.chmod(claims, 0)
        try:
            code, line = dwc.check(DATE, archive, claims)
        finally:
            os.chmod(claims, 0o700)
        assert code == 1, f"expected exit 1, got {code} {line}"
        assert line.startswith("status=claims-unavailable"), line
        assert "error=" in line, f"status must carry the I/O error: {line}"


def test_absent_claims_dir_is_still_missing():
    # A claims dir that does not exist at all: no claim can exist,
    # so this is still the "worker never fired" signal.
    with tempfile.TemporaryDirectory() as tmp:
        archive = _archive(tmp)
        code, line = dwc.check(DATE, archive, Path(tmp) / "no-such-claims")
        assert code == 1 and line == "status=missing", f"{code} {line}"


def test_absent_claim_file_is_still_missing():
    # Readable claims dir, no sched-<date>.json inside: missing.
    with tempfile.TemporaryDirectory() as tmp:
        archive = _archive(tmp)
        claims = Path(tmp) / "claims"
        claims.mkdir()
        code, line = dwc.check(DATE, archive, claims)
        assert code == 1 and line == "status=missing", f"{code} {line}"


def test_present_claim_is_still_running():
    # Readable claims dir holding the claim: unchanged behaviour.
    with tempfile.TemporaryDirectory() as tmp:
        archive = _archive(tmp)
        claims = Path(tmp) / "claims"
        claims.mkdir()
        (claims / f"sched-{DATE}.json").write_text("{}\n")
        code, line = dwc.check(DATE, archive, claims)
        assert code == 1 and line == f"status=running claim=sched-{DATE}", \
            f"{code} {line}"


def test_no_claims_dir_is_still_missing():
    # No --claims-dir at all: missing, as before.
    with tempfile.TemporaryDirectory() as tmp:
        archive = _archive(tmp)
        code, line = dwc.check(DATE, archive, None)
        assert code == 1 and line == "status=missing", f"{code} {line}"


def test_archived_sweep_beats_unreadable_claims():
    # The archive check runs first: a landed sweep still reports
    # archived even when the claims dir cannot be inspected -- the
    # new status must not mask a success.
    with tempfile.TemporaryDirectory() as tmp:
        archive = _archive(tmp)
        import json
        sweep = Path(tmp) / "worker-runs" / DATE / \
            "050559__sweep-lite-poul-ca-market-egx__runx"
        sweep.mkdir()
        (sweep / "manifest.json").write_text(json.dumps(
            {"job": {"id": f"sched-{DATE}", "job": "sweep-lite POUL.CA"},
             "tools": {"yahooquery": "ok"}}))
        claims_file = Path(tmp) / "claims"
        claims_file.write_text("not a directory\n")
        code, line = dwc.check(DATE, archive, claims_file)
        assert code == 0 and line.startswith("status=archived"), \
            f"{code} {line}"


if __name__ == "__main__":
    for name, fn in [
            ("unreadable_claims_dir_is_claims_unavailable",
             test_unreadable_claims_dir_is_claims_unavailable),
            ("unreadable_claims_dir_chmod",
             test_unreadable_claims_dir_chmod),
            ("absent_claims_dir_is_still_missing",
             test_absent_claims_dir_is_still_missing),
            ("absent_claim_file_is_still_missing",
             test_absent_claim_file_is_still_missing),
            ("present_claim_is_still_running",
             test_present_claim_is_still_running),
            ("no_claims_dir_is_still_missing",
             test_no_claims_dir_is_still_missing),
            ("archived_sweep_beats_unreadable_claims",
             test_archived_sweep_beats_unreadable_claims)]:
        check(name, fn)
    failed = [r for r in RESULTS if not r[1]]
    print(f"{len(RESULTS) - len(failed)}/{len(RESULTS)} passed")
    sys.exit(1 if failed else 0)
