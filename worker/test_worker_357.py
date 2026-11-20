#!/usr/bin/env python3
"""Regression tests for issue #357 F2 (INS-353-354 follow-up):
document identity is required on every validated document record.

#352 only tracked source_document_id when it was a string, so a
ledger whose documents omitted the id (or carried a non-string
one) bypassed the within-issuer uniqueness check entirely while
still satisfying the reconciled counts. The fix requires a
non-empty string source_document_id on every validated document
record: a missing, empty, or non-string id is a named validation
failure, never an exception, and the record never enters the
per-issuer identity set. Cross-issuer sharing of one id is still
legitimate and still passes; honest ledgers (the producer always
emits ids) still pass.

Every test below FAILS on base ee0d1b5d and PASSES with the fix.
Stdlib only.

Run: python3 worker/test_worker_357.py (exit 0 = all pass).
"""
import copy
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _test_tmp  # noqa: E402  (atexit cleanup of scratch dirs, #388)
_TMP = _test_tmp.mkdtemp(prefix="gator357-f2-test-")
os.environ["GATOR_ROOT"] = str(_TMP)

_HERE = Path(os.path.abspath(__file__)).parent
_REPO = _HERE.parent
sys.path.insert(0, str(_HERE))

import worker  # noqa: E402

PASSED = 0


def check(name, cond):
    global PASSED
    assert cond, name
    PASSED += 1
    print(f"pass: {name}")


# --- Synthetic manifest/ledger (own shape: 2 issuers + the FAIT
# blocked route, as the real producer writes them) -----------------

MANIFEST = {
    "base_commit": "test357base",
    "frozen_at": "2026-11-19",
    "event_types": ["dividend", "earnings", "board"],
    "issuers": [
        {"issuer": "ORWE",
         "listings": [{"code": "ORWE", "isin": "EGS000000101"}]},
        {"issuer": "CIRA",
         "listings": [{"code": "CIRA", "isin": "EGS000000102"}]},
        {"issuer": "FAIT",
         "listings": [{"code": "FAIT", "isin": "EGS000000003"},
                      {"code": "FAITA", "isin": None}]},
    ],
}


def listing(code, isin=None, status="enumerated", terminal="exhausted",
            failures=None):
    return {"code": code, "isin": isin,
            "enumeration_status": status,
            "terminal_state": terminal, "failures": failures or []}


def doc(doc_id="ABSENT", status="archived", listing_code="ORWE",
        isin="EGS000000101"):
    d = {"corpus": {"status": status, "body_hash_kind": "full",
                    "body_sha256": "c" * 64},
         "listing": listing_code, "isin": isin}
    if doc_id != "ABSENT":
        d["source_document_id"] = doc_id
    return d


def ledger(orwe_docs, enumerated, archived):
    return {
        "schema_version": 1,
        "window": {"start": worker.TOP30_WINDOW_START,
                   "end": worker.TOP30_WINDOW_END},
        "mode": "fixtures",
        "manifest": {"base_commit": "test357base"},
        "collection": {"enumerated": enumerated, "archived": archived,
                       "missing": ["FAITA"], "enumeration_closed": False,
                       "pagination_complete": False},
        "failures": [{"kind": "B-02-missing-isin", "route": "FAITA"}],
        "issuers": [
            {"issuer": "ORWE",
             "listings": [listing("ORWE", "EGS000000101")],
             "documents": orwe_docs},
            {"issuer": "CIRA",
             "listings": [listing("CIRA", "EGS000000102")],
             "documents": [doc("CIRA-1", listing_code="CIRA",
                               isin="EGS000000102")]},
            {"issuer": "FAIT",
             "listings": [listing("FAIT", "EGS000000003"),
                          listing("FAITA", None, status="blocked",
                                  terminal="blocked",
                                  failures=[{"kind":
                                             "B-02-missing-isin"}])],
             "documents": []},
        ],
    }


def validate(led):
    return worker._validate_top30_ledger(
        led, copy.deepcopy(MANIFEST), "fixtures")


def test_f2_identity_required():
    # Honest control: unique string ids, counts reconciled.
    ok, reasons = validate(ledger(
        [doc("ORWE-1"), doc("ORWE-2")], 3, 3))
    check("F2-control: honest ledger with unique string ids passes",
          ok and not reasons)

    # All three ORWE docs omit the id; counts adjusted (3 + 1 CIRA).
    ok, reasons = validate(ledger([doc(), doc(), doc()], 4, 4))
    check("F2a: all ids omitted, counts adjusted, fails",
          not ok)
    check("F2a: the failure names the missing identity",
          any("source_document_id" in r and "non-empty string" in r
              for r in reasons))

    # Non-string ids: int, None, list — same bypass family.
    ok, reasons = validate(ledger(
        [doc(7), doc(None), doc(["egx:1"])], 4, 4))
    check("F2b: non-string ids fail, never raise",
          not ok and isinstance(reasons, list))
    check("F2b: each non-string id gets a named identity reason",
          len([r for r in reasons
               if "source_document_id" in r
               and "non-empty string" in r]) == 3)

    # Empty string is not an identity either.
    ok, reasons = validate(ledger([doc("ORWE-1"), doc("")], 3, 3))
    check("F2c: empty-string id fails with a named reason",
          not ok and any("source_document_id" in r
                         and "non-empty string" in r
                         for r in reasons))

    # Partial bypass: 2 identified + 1 unidentified, counts adjusted.
    ok, reasons = validate(ledger(
        [doc("ORWE-1"), doc("ORWE-2"), doc()], 4, 4))
    check("F2d: mixed identified + unidentified fails",
          not ok and any("source_document_id" in r
                         and "non-empty string" in r
                         for r in reasons))

    # The failure is the named identity reason, not a cascade of
    # count mismatches: the unidentified record still counts
    # toward the totals (same precedent as #352 F5 attribution).
    ok, reasons = validate(ledger([doc(), doc(), doc()], 4, 4))
    check("F2e: no spurious count-mismatch reason on the bypass",
          not any("enumerated=" in r or "archived=" in r
                  for r in reasons))

    # Existing guard intact: duplicate STRING id still fails.
    ok, reasons = validate(ledger(
        [doc("ORWE-1"), doc("ORWE-1"), doc("ORWE-2")], 4, 4))
    check("F2-control: duplicate string id still fails",
          not ok and any("duplicate source_document_id" in r
                         for r in reasons))

    # Cross-issuer sharing preserved: the same id under CIRA as
    # under ORWE is legitimate.
    led = ledger([doc("ORWE-1"), doc("ORWE-2")], 4, 4)
    led["issuers"][1]["documents"].append(
        doc("ORWE-1", listing_code="CIRA", isin="EGS000000102"))
    ok, reasons = validate(led)
    check("F2-control: same id across issuers still passes",
          ok and not reasons)


if __name__ == "__main__":
    test_f2_identity_required()
    print(f"{PASSED} passed")
