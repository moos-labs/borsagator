#!/usr/bin/env python3
"""Regression tests for issue #352 (INS-347-POSTMERGE-REVIEW
residuals on merged PR #347, verified by Moos with executable
probes 11/11, ~/workspace/tick0540_verify347_f5f4.py, main tip
bb279d3):

  F5 — attribution stripping bypass: the #346 fix checked a
    document's listing/ISIN only when the record carried them,
    so stripping listing and/or isin bypassed every provenance
    check while the document still counted toward the validated
    totals. Attribution is now REQUIRED on every validated
    document record (listing + ISIN, matching the frozen
    manifest). The producer always attributes documents
    (top30_enumerate.py emits listing + isin at discovery,
    including not_captured records), so honest ledgers pass.
  F4 — within-issuer duplicate document counting: the #346
    summary reconciliation counted records, not unique
    source_document_ids, so a duplicated id under one issuer
    (with adjusted counts) validated. Uniqueness is now
    enforced WITHIN each issuer only — one announcement may
    legitimately appear through different issuers' searches,
    so cross-issuer sharing still passes.

The collection.missing interface is settled by comment + docs
only (docs/top30-enumeration.md §5): missing holds frozen
ROUTE codes, never document IDs, never manufactured; the
producer emits missing=[] and evidences blocked/failed routes
in listing/failure records. The validator already enforces
frozen-route entries (see test_worker_346.py F4).

Every test below FAILS on base bb279d3 and PASSES with the
fix. Stdlib only.

Run: python3 worker/test_worker_352.py (exit 0 = all pass).
"""
import copy
import os
import sys
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="gator352-test-"))
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


# --- Synthetic manifest/ledger (same shape as test_worker_346.py:
# 3 issuers, listing ISINs + document attribution, as the real
# producer writes them) ---------------------------------------------

MANIFEST = {
    "base_commit": "testbase123",
    "frozen_at": "2026-11-19",
    "event_types": ["dividend", "earnings", "board"],
    "issuers": [
        {"issuer": "TMGH",
         "listings": [{"code": "TMGH", "isin": "EGS000000001"}]},
        {"issuer": "ETEL",
         "listings": [{"code": "ETEL", "isin": "EGS000000002"}]},
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


def doc(doc_id, status="archived", kind="full", sha="a" * 64,
        listing_code=None, isin=None, attachments=None):
    corpus = {"status": status, "body_hash_kind": kind,
              "body_sha256": sha}
    if attachments is not None:
        corpus["attachments"] = attachments
    d = {"source_document_id": doc_id, "corpus": corpus}
    if listing_code:
        d["listing"] = listing_code
    if isin:
        d["isin"] = isin
    return d


def baseline():
    """Honest incomplete ledger: 2 documents enumerated + archived,
    FAITA named as the missing (blocked) route. Must PASS."""
    return {
        "schema_version": 1,
        "window": {"start": worker.TOP30_WINDOW_START,
                   "end": worker.TOP30_WINDOW_END},
        "mode": "fixtures",
        "manifest": {"base_commit": "testbase123"},
        "collection": {"enumerated": 2, "archived": 2,
                       "missing": ["FAITA"],
                       "enumeration_closed": False,
                       "pagination_complete": False},
        "failures": [{"kind": "B-02-missing-isin", "route": "FAITA"}],
        "issuers": [
            {"issuer": "TMGH",
             "listings": [listing("TMGH", "EGS000000001")],
             "documents": [doc("TMGH-doc-1", listing_code="TMGH",
                               isin="EGS000000001")]},
            {"issuer": "ETEL",
             "listings": [listing("ETEL", "EGS000000002")],
             "documents": [doc("ETEL-doc-1", listing_code="ETEL",
                               isin="EGS000000002")]},
            {"issuer": "FAIT",
             "listings": [listing("FAIT", "EGS000000003"),
                          listing("FAITA", None, status="blocked",
                                  terminal="blocked",
                                  failures=[{"kind":
                                             "B-02-missing-isin"}])],
             "documents": []},
        ],
    }


def validate(led, manifest=None, mode="fixtures"):
    return worker._validate_top30_ledger(
        led, manifest if manifest is not None else MANIFEST, mode)


# --- F5: attribution required ------------------------------------------

def test_f5_attribution_required():
    led = baseline()
    d = led["issuers"][0]["documents"][0]
    del d["listing"]
    del d["isin"]
    ok, reasons = validate(led)
    check("F5a: stripped listing+isin, counts unchanged, fails",
          not ok and any("no listing attribution" in r
                         for r in reasons))

    led = baseline()
    d = led["issuers"][0]["documents"][0]
    del d["isin"]
    ok, reasons = validate(led)
    check("F5b: isin removed (listing valid), fails",
          not ok and any("no ISIN" in r for r in reasons))

    led = baseline()
    led["issuers"][2]["documents"] = [
        doc("FAIT-doc-1", listing_code="FAITA")]
    led["collection"]["enumerated"] = 3
    led["collection"]["archived"] = 3
    ok, reasons = validate(led)
    check("F5c pre-strip: doc claiming blocked FAITA fails",
          not ok and any("blocked route" in r for r in reasons))
    del led["issuers"][2]["documents"][0]["listing"]
    ok, reasons = validate(led)
    check("F5c: listing removed from the FAITA claim, still fails",
          not ok and any("no listing attribution" in r
                         for r in reasons))

    led = baseline()
    d = led["issuers"][0]["documents"][0]
    del d["listing"]
    del d["isin"]
    ok, reasons = validate(led)
    check("F5d: stripped doc is not vouched in the archived total",
          not ok and any("attribution" in r for r in reasons)
          and not any("archived=" in r for r in reasons))

    led = baseline()
    ok, reasons = validate(led)
    check("F5-control: honest fully-attributed ledger passes",
          ok and not reasons)

    led = baseline()
    led["issuers"][0]["documents"] = [
        doc("TMGH-doc-1", listing_code="TMGH",
            isin="EGS000000002")]
    ok, reasons = validate(led)
    check("F5-control: wrong ISIN present still fails",
          not ok and any("ISIN" in r for r in reasons))

    led = baseline()
    led["issuers"][0]["documents"] = [
        doc("TMGH-doc-1", status="not_captured", kind=None,
            sha=None, listing_code="TMGH",
            isin="EGS000000001")]
    led["collection"]["archived"] = 1
    ok, reasons = validate(led)
    check("F5-control: attributed not_captured doc still passes",
          ok and not reasons)


# --- F4: within-issuer uniqueness ----------------------------------------

def test_f4_within_issuer_uniqueness():
    led = baseline()
    tm = led["issuers"][0]
    tm["documents"].append(copy.deepcopy(tm["documents"][0]))
    led["collection"]["enumerated"] = 3
    led["collection"]["archived"] = 3
    ok, reasons = validate(led)
    check("F4a: duplicate id within issuer, counts adjusted, fails",
          not ok and any("duplicate source_document_id" in r
                         for r in reasons))

    led = baseline()
    tm = led["issuers"][0]
    tm["documents"].append(copy.deepcopy(tm["documents"][0]))
    ok, reasons = validate(led)
    check("F4b: duplicate id, counts NOT adjusted, still fails",
          not ok)

    led = baseline()
    tm = led["issuers"][0]
    et = led["issuers"][1]
    shared = copy.deepcopy(tm["documents"][0])
    shared["listing"] = "ETEL"
    shared["isin"] = "EGS000000002"
    et["documents"].append(shared)
    led["collection"]["enumerated"] = 3
    led["collection"]["archived"] = 3
    ok, reasons = validate(led)
    check("F4c: same id across issuers still passes",
          ok and not reasons)

    led = baseline()
    tm = led["issuers"][0]
    for doc_id in (None, 123, ["not", "a", "string"]):
        d = copy.deepcopy(tm["documents"][0])
        d["source_document_id"] = doc_id
        tm["documents"].append(d)
    led["collection"]["enumerated"] = 5
    led["collection"]["archived"] = 5
    ok, reasons = validate(led)
    check("F4-control: missing/non-string ids never raise",
          isinstance(ok, bool) and isinstance(reasons, list))
    check("F4-control: missing/non-string ids are not treated as "
          "duplicates (they cannot collide)",
          ok and not reasons)

    led = baseline()
    ok, reasons = validate(led)
    check("F4-control: honest ledger passes",
          ok and not reasons)


def main():
    test_f5_attribution_required()
    test_f4_within_issuer_uniqueness()
    print(f"\n{PASSED} passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
