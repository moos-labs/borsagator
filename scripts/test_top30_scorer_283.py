#!/usr/bin/env python3
"""Negative controls + positive controls for the #283 top-30 scorer.

Run directly:  python3 scripts/test_top30_scorer_283.py
Also wired into scripts/harness_issue109.py (--scorer). Stdlib only.

Every case is a (name, function) pair returning (ok, detail); the file
exits 0 only when every case passes. The four required negative
controls (issue #283 stage 1) are: swapped-date, sign, duplicate-reuse
and candidate-only. Each must FAIL the naive reading (a scorer that
matched on magnitude, reused gold, or counted candidates as TPs would
pass it) and PASS the spec reading.
"""
import os
import sys
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import top30_scorer as S


def div(doc, issuer="POUL", gold_id="g1", **fields):
    base = {"coupon": "42", "amount_per_share": "1.9",
            "ex_date": "2026-11-16", "entitlement_end": "2026-11-15",
            "payout_date": "2026-11-18", "record_date": None,
            "announced": "2026-11-02"}
    base.update(fields)
    return {"source_document_id": doc, "event_type": "dividend",
            "issuer": issuer, "gold_id": gold_id,
            "extraction_status": "extracted",
            "verification_status": "verified", "fields": base}


def earn(doc, issuer="COMI", gold_id="g1", **fields):
    base = {"period_start": "2026-01-01", "period_end": "2026-09-30",
            "npat": "63079356", "npat_scale": "one",
            "npat_comparative": "50000000", "yoy_npat_pct": "26.2",
            "revenue": None, "announced": "2026-11-10"}
    base.update(fields)
    return {"source_document_id": doc, "event_type": "earnings",
            "issuer": issuer, "gold_id": gold_id,
            "extraction_status": "extracted",
            "verification_status": "verified", "fields": base}


def _gold(ev):
    """Strip prediction-only status keys: gold carries no status."""
    g = dict(ev)
    g.pop("extraction_status", None)
    g.pop("verification_status", None)
    return g


def _fs(result, field):
    return result["field_score"].get(field, {"tp": 0, "fp": 0, "fn": 0})


# --- required negative controls -------------------------------------------

def test_swapped_date():
    """Predicted ex-date and payout-date swapped vs gold: the event is
    still identifiable (same doc + type) so it is an event TP, but EACH
    swapped date is a wrong value = 1 FP + 1 FN. A scorer that matched
    dates as a set would miss both errors."""
    gold = [_gold(div("egx:296893"))]
    pred = [div("egx:296893", ex_date="2026-11-18",
                payout_date="2026-11-16")]
    r = S.score_cell(gold, pred)
    ok = (r["tp"] == 1 and r["fp"] == 0 and r["fn"] == 0
          and _fs(r, "ex_date") == {"tp": 0, "fp": 1, "fn": 1}
          and _fs(r, "payout_date") == {"tp": 0, "fp": 1, "fn": 1}
          and _fs(r, "coupon") == {"tp": 1, "fp": 0, "fn": 0})
    return ok, ("tp=%d fp=%d fn=%d ex=%s payout=%s"
                % (r["tp"], r["fp"], r["fn"], _fs(r, "ex_date"),
                   _fs(r, "payout_date")))


def test_sign():
    """Predicted NPAT +100 against gold NPAT -100 (a loss): sign is
    part of the value. Wrong value = 1 FP + 1 FN. A magnitude-only
    comparison would call this a match."""
    gold = [_gold(earn("egx:297291", npat="-100"))]
    pred = [earn("egx:297291", npat="100")]
    r = S.score_cell(gold, pred)
    ok = (r["tp"] == 1 and _fs(r, "npat") == {"tp": 0, "fp": 1, "fn": 1})
    return ok, ("tp=%d npat=%s" % (r["tp"], _fs(r, "npat")))


def test_duplicate_reuse():
    """Two predicted events, one gold event: one TP, the duplicate is
    an FP — a gold event is never reused."""
    gold = [_gold(div("egx:296893"))]
    pred = [div("egx:296893"), div("egx:296893")]
    r = S.score_cell(gold, pred)
    ok = (r["tp"] == 1 and r["fp"] == 1 and r["fn"] == 0
          and len(r["matches"]) == 1)
    return ok, ("tp=%d fp=%d fn=%d" % (r["tp"], r["fp"], r["fn"]))


def test_candidate_only():
    """Predicted event identical to gold on every field but with
    candidate status: NOT a TP. It is an FP; the gold event is an FN;
    end-to-end field counts are FP (predicted fields) + FN (gold
    fields). Candidate status never grants a TP."""
    gold = [_gold(earn("egx:297291"))]
    cand = earn("egx:297291")
    cand["extraction_status"] = "candidate"
    cand["verification_status"] = "unverified"
    r = S.score_cell(gold, [cand])
    ok = (r["tp"] == 0 and r["fp"] == 1 and r["fn"] == 1
          and _fs(r, "npat") == {"tp": 0, "fp": 1, "fn": 1})
    return ok, ("tp=%d fp=%d fn=%d npat=%s"
                % (r["tp"], r["fp"], r["fn"], _fs(r, "npat")))


# --- positive + structural controls ----------------------------------------

def test_exact_match():
    gold = [_gold(div("egx:296893"))]
    pred = [div("egx:296893")]
    r = S.score_cell(gold, pred)
    ok = (r["tp"] == 1 and r["fp"] == 0 and r["fn"] == 0
          and r["precision"] == Fraction(1, 1)
          and r["recall"] == Fraction(1, 1) and r["accepted"] is True)
    return ok, ("tp=%d fp=%d fn=%d" % (r["tp"], r["fp"], r["fn"]))


def test_missing_gold_event():
    """No prediction for a gold event: FN at event level and an FN per
    present gold field (end-to-end denominator, not matched-only)."""
    gold = [_gold(earn("egx:297291"))]
    r = S.score_cell(gold, [])
    ok = (r["tp"] == 0 and r["fp"] == 0 and r["fn"] == 1
          and _fs(r, "npat") == {"tp": 0, "fp": 0, "fn": 1}
          and _fs(r, "revenue") == {"tp": 0, "fp": 0, "fn": 0})
    return ok, ("fn=%d npat=%s" % (r["fn"], _fs(r, "npat")))


def test_extra_predicted():
    """Predicted event with no gold counterpart: FP at event level and
    an FP per present predicted field."""
    gold = []
    pred = [div("egx:999999")]
    r = S.score_cell(gold, pred)
    ok = (r["tp"] == 0 and r["fp"] == 1 and r["fn"] == 0
          and _fs(r, "coupon") == {"tp": 0, "fp": 1, "fn": 0})
    return ok, ("fp=%d coupon=%s" % (r["fp"], _fs(r, "coupon")))


def test_ambiguous_tie_not_favourable():
    """Two gold events in one document, one predicted event agreeing
    equally with both: no favourable automatic match — predicted is FP,
    both golds FN, group flagged ambiguous for adjudication."""
    g1 = _gold(div("egx:111", gold_id="g1", coupon="41"))
    g2 = _gold(div("egx:111", gold_id="g2", coupon="42"))
    p = div("egx:111", coupon="43")  # agrees with both on amount only
    r = S.score_cell([g1, g2], [p])
    ok = (r["tp"] == 0 and r["fp"] == 1 and r["fn"] == 2
          and len(r["ambiguous"]) == 1
          and r["ambiguous"][0]["tied_gold_ids"] == ["g1", "g2"])
    return ok, ("tp=%d fp=%d fn=%d ambiguous=%d"
                % (r["tp"], r["fp"], r["fn"], len(r["ambiguous"])))


def test_cross_document_no_match():
    """Same payload, different source document: no match (FP + FN)."""
    gold = [_gold(div("egx:296893"))]
    pred = [div("egx:296894")]
    r = S.score_cell(gold, pred)
    ok = r["tp"] == 0 and r["fp"] == 1 and r["fn"] == 1
    return ok, ("tp=%d fp=%d fn=%d" % (r["tp"], r["fp"], r["fn"]))


def test_acceptance_no_rounding():
    """19/20 precision is exactly 0.95 (pass); 18/19 is below 0.95
    (fail) — no rounding a failure into a pass. Zero denominators
    are N/A, never a pass."""
    a = S.acceptance(19, 1, 0)
    b = S.acceptance(18, 1, 0)
    c = S.acceptance(0, 0, 0)
    ok = (a["passed"] is True and a["precision"] == Fraction(19, 20)
          and b["passed"] is False
          and b["precision"] == Fraction(18, 19)
          and c["assessable"] is False and c["passed"] is None)
    return ok, ("19/20=%s 18/19=%s 0/0=%s"
                % (a["passed"], b["passed"], c["passed"]))


def test_small_cell_no_exemption():
    """A 1-event cell that misses is a failed cell (R = 0/1)."""
    r = S.score_cell([_gold(div("egx:1"))], [])
    ok = r["recall"] == Fraction(0, 1) and r["accepted"] is False
    return ok, ("recall=%s accepted=%s" % (r["recall"], r["accepted"]))


def test_zero_denominator_na():
    """Empty cell: P/R are N/A with counts shown, not 0 and not 1."""
    r = S.score_cell([], [])
    ok = (r["precision"] is None and r["recall"] is None
          and r["accepted"] is None
          and (r["tp"], r["fp"], r["fn"]) == (0, 0, 0))
    return ok, ("P=%s R=%s accepted=%s"
                % (r["precision"], r["recall"], r["accepted"]))


CASES = [
    ("swapped-date", test_swapped_date),
    ("sign", test_sign),
    ("duplicate-reuse", test_duplicate_reuse),
    ("candidate-only", test_candidate_only),
    ("exact-match", test_exact_match),
    ("missing-gold-event", test_missing_gold_event),
    ("extra-predicted", test_extra_predicted),
    ("ambiguous-tie-not-favourable", test_ambiguous_tie_not_favourable),
    ("cross-document-no-match", test_cross_document_no_match),
    ("acceptance-no-rounding", test_acceptance_no_rounding),
    ("small-cell-no-exemption", test_small_cell_no_exemption),
    ("zero-denominator-na", test_zero_denominator_na),
]


def run_all(verbose=True):
    """Run every case; return (n_pass, n_fail, [failed names])."""
    n_pass = n_fail = 0
    failed = []
    for name, fn in CASES:
        try:
            ok, detail = fn()
        except Exception as e:  # a crashing case is a failed case
            ok, detail = False, "raised %r" % (e,)
        if ok:
            n_pass += 1
        else:
            n_fail += 1
            failed.append(name)
        if verbose:
            print("  %s scorer-283: %s %s"
                  % ("PASS" if ok else "FAIL", name, detail))
    return n_pass, n_fail, failed


def main():
    n_pass, n_fail, failed = run_all()
    print("SCORER-283 pass=%d fail=%d" % (n_pass, n_fail))
    if failed:
        print("FAILURES: %s" % ", ".join(failed))
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
