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

Issue #305 adds the full-verdict and boundary controls: swapped-date
and sign must also yield `accepted is False`; candidate+verified and
extracted+unverified are separate controls; missing/unknown statuses
are rejected; multi-event permutation tests prove order independence;
issuer/schema/currency/scale controls prove the typed input contract.
"""
import itertools
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
          and _fs(r, "coupon") == {"tp": 1, "fp": 0, "fn": 0}
          # Full §7 verdict (#305 §1): the event passes but both
          # swapped dates fail, so the cell must NOT be accepted.
          and r["accepted"] is False
          and r["field_verdicts"]["ex_date"] is False
          and r["field_verdicts"]["payout_date"] is False)
    return ok, ("tp=%d fp=%d fn=%d ex=%s payout=%s accepted=%s"
                % (r["tp"], r["fp"], r["fn"], _fs(r, "ex_date"),
                   _fs(r, "payout_date"), r["accepted"]))


def test_sign():
    """Predicted NPAT +100 against gold NPAT -100 (a loss): sign is
    part of the value. Wrong value = 1 FP + 1 FN. A magnitude-only
    comparison would call this a match."""
    gold = [_gold(earn("egx:297291", npat="-100"))]
    pred = [earn("egx:297291", npat="100")]
    r = S.score_cell(gold, pred)
    ok = (r["tp"] == 1 and _fs(r, "npat") == {"tp": 0, "fp": 1, "fn": 1}
          # Full §7 verdict (#305 §1): the event passes but the NPAT
          # sign is wrong, so the cell must NOT be accepted.
          and r["accepted"] is False
          and r["field_verdicts"]["npat"] is False)
    return ok, ("tp=%d npat=%s accepted=%s"
                % (r["tp"], _fs(r, "npat"), r["accepted"]))


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


# --- #305: full verdict, order independence, boundaries, contract ---

def _perm_case():
    """The #305 §2 proof case: gold (coupon41, amount1) + (coupon42,
    amount2); predictions A=(41, 2), B=(41, 1). Greedy matching is
    order-dependent here (A-first TP=1/FP=1/FN=1, B-first TP=2); the
    maximum-agreement assignment gives TP=2 in both orders."""
    def g(coupon, amount, gid):
        e = div("egx:1", coupon=coupon, amount_per_share=amount,
                gold_id=gid)
        return _gold(e)
    gold = [g("41", "1", "g1"), g("42", "2", "g2")]
    a = div("egx:1", coupon="41", amount_per_share="2")
    b = div("egx:1", coupon="41", amount_per_share="1")
    return gold, a, b


def test_order_permutation():
    gold, a, b = _perm_case()
    r1 = S.score_cell(gold, [a, b])
    r2 = S.score_cell(gold, [b, a])
    # Identical counts and field scores in both orders. `accepted` is
    # False in both: A is paired to g2, so coupon is a wrong value
    # (field P = 1/2) — the point here is order independence, not a pass.
    ok = (r1["tp"] == 2 and r1["fp"] == 0 and r1["fn"] == 0
          and (r2["tp"], r2["fp"], r2["fn"]) == (2, 0, 0)
          and r1["field_score"] == r2["field_score"]
          and r1["accepted"] is False and r2["accepted"] is False)
    return ok, ("A-first tp=%d fp=%d fn=%d accepted=%s; "
                "B-first tp=%d fp=%d fn=%d accepted=%s"
                % (r1["tp"], r1["fp"], r1["fn"], r1["accepted"],
                   r2["tp"], r2["fp"], r2["fn"], r2["accepted"]))


def test_order_permutation_three_events():
    """Three events where greedy order changes the result: X=(41,2)
    ties g1/g2 on agreement, so greedy X-first flags X ambiguous
    (TP=2), while Y-first/Z-first give TP=3. Maximum agreement gives
    TP=3 in every input order."""
    def g(coupon, amount, gid):
        return _gold(div("egx:1", coupon=coupon,
                         amount_per_share=amount, gold_id=gid))
    gold = [g("41", "1", "g1"), g("42", "2", "g2"), g("43", "3", "g3")]
    x = div("egx:1", coupon="41", amount_per_share="2")
    y = div("egx:1", coupon="42", amount_per_share="2")
    z = div("egx:1", coupon="43", amount_per_share="3")
    results = []
    for order in itertools.permutations([x, y, z]):
        r = S.score_cell(gold, list(order))
        results.append((r["tp"], r["fp"], r["fn"], r["accepted"]))
    # All six orders identical. `accepted` is False in all of them:
    # X is paired to g1, so amount_per_share is a wrong value
    # (field P = 2/3) — the point is order independence, not a pass.
    ok = (len(set(results)) == 1
          and results[0] == (3, 0, 0, False))
    return ok, ("6 orders -> %s" % (set(results),))


def test_candidate_verified():
    """Candidate extraction + VERIFIED status: still never a TP. The
    candidate-only fixture changes both statuses, so each guard needs
    its own control (#305 §5)."""
    gold = [_gold(earn("egx:297291"))]
    cand = earn("egx:297291")
    cand["extraction_status"] = "candidate"
    cand["verification_status"] = "verified"
    r = S.score_cell(gold, [cand])
    ok = (r["tp"] == 0 and r["fp"] == 1 and r["fn"] == 1
          and r["accepted"] is False)
    return ok, ("tp=%d fp=%d fn=%d accepted=%s"
                % (r["tp"], r["fp"], r["fn"], r["accepted"]))


def test_extracted_unverified():
    """Extracted + UNVERIFIED status: still never a TP."""
    gold = [_gold(earn("egx:297291"))]
    unv = earn("egx:297291")
    unv["extraction_status"] = "extracted"
    unv["verification_status"] = "unverified"
    r = S.score_cell(gold, [unv])
    ok = (r["tp"] == 0 and r["fp"] == 1 and r["fn"] == 1
          and r["accepted"] is False)
    return ok, ("tp=%d fp=%d fn=%d accepted=%s"
                % (r["tp"], r["fp"], r["fn"], r["accepted"]))


def _expect_reject(gold, pred):
    try:
        S.score_cell(gold, pred)
    except ValueError:
        return True
    return False


def test_missing_extraction_status():
    """A predicted event with no extraction_status is rejected, never
    defaulted to "extracted" (#305 §4)."""
    gold = [_gold(div("egx:296893"))]
    pred = div("egx:296893")
    del pred["extraction_status"]
    ok = _expect_reject(gold, [pred])
    return ok, ("rejected=%s" % ok)


def test_missing_verification_status():
    """A predicted event with no verification_status is rejected, never
    defaulted to "verified"."""
    gold = [_gold(div("egx:296893"))]
    pred = div("egx:296893")
    del pred["verification_status"]
    ok = _expect_reject(gold, [pred])
    return ok, ("rejected=%s" % ok)


def test_unknown_status():
    """Unknown status values are rejected on both axes."""
    gold = [_gold(div("egx:296893"))]
    bad_ext = div("egx:296893")
    bad_ext["extraction_status"] = "draft"
    bad_ver = div("egx:296893")
    bad_ver["verification_status"] = "pending"
    ok = (_expect_reject(gold, [bad_ext])
          and _expect_reject(gold, [bad_ver]))
    return ok, ("both-rejected=%s" % ok)


def test_gold_with_status_rejected():
    """Gold never carries a prediction-only status; a gold event that
    does is a caller error, rejected, not silently scored."""
    gold = [div("egx:296893")]  # statuses still present: not gold
    ok = _expect_reject(gold, [div("egx:296893")])
    return ok, ("rejected=%s" % ok)


def test_unknown_event_type():
    """An event with an unknown event_type is rejected (schema)."""
    gold = [_gold(div("egx:296893"))]
    pred = div("egx:296893")
    pred["event_type"] = "split"
    ok = _expect_reject(gold, [pred])
    return ok, ("rejected=%s" % ok)


def test_missing_issuer():
    """An event with no issuer is rejected (cell membership)."""
    gold = [_gold(div("egx:296893"))]
    pred = div("egx:296893")
    del pred["issuer"]
    ok = _expect_reject(gold, [pred])
    return ok, ("rejected=%s" % ok)


def test_issuer_mismatch():
    """A predicted event attributed to the wrong issuer cannot match
    that issuer's gold (spec §4.5): FP + FN, and the cell is not
    accepted — even with identical fields."""
    gold = [_gold(div("egx:296893", issuer="POUL"))]
    pred = [div("egx:296893", issuer="COMI")]
    r = S.score_cell(gold, pred)
    ok = (r["tp"] == 0 and r["fp"] == 1 and r["fn"] == 1
          and r["accepted"] is False)
    return ok, ("tp=%d fp=%d fn=%d accepted=%s"
                % (r["tp"], r["fp"], r["fn"], r["accepted"]))


def test_nested_extractor_adapter():
    """Extractor-shaped nested date/money objects score as TPs when
    the values agree; the derived record_date candidate (value None)
    is never a value, so record_date stays 0/0/0 and does not fail
    the cell (#305 §3)."""
    gold = [_gold(div("egx:296893"))]
    pred = div("egx:296893")
    pred["fields"]["amount_per_share"] = {
        "value": "1.9", "currency": "EGP", "scale": "one",
        "raw": "1.9", "evidence": None}
    pred["fields"]["ex_date"] = {
        "value": "2026-11-16",
        "basis": "verbatim:تاريخ تحريك الحدود السعرية",
        "evidence": None, "derived_candidate": None,
        "derived_rule": None}
    pred["fields"]["record_date"] = {
        "value": None, "basis": "not-stated-in-source",
        "evidence": None, "derived_candidate": "2026-11-18",
        "derived_rule": "T+2 settlement from entitlement_end "
                        "(UNVALIDATED — candidate only, not a fact)"}
    r = S.score_cell(gold, [pred])
    ok = (r["tp"] == 1 and r["fp"] == 0 and r["fn"] == 0
          and _fs(r, "amount_per_share") == {"tp": 1, "fp": 0, "fn": 0}
          and _fs(r, "ex_date") == {"tp": 1, "fp": 0, "fn": 0}
          and _fs(r, "record_date") == {"tp": 0, "fp": 0, "fn": 0}
          and r["accepted"] is True)
    return ok, ("tp=%d fp=%d fn=%d amount=%s record=%s accepted=%s"
                % (r["tp"], r["fp"], r["fn"],
                   _fs(r, "amount_per_share"), _fs(r, "record_date"),
                   r["accepted"]))


def test_currency_mismatch():
    """Money in USD never equals money in EGP: currency is part of
    the value, so the amount is a wrong value (1 FP + 1 FN) and the
    cell is not accepted."""
    gold = [_gold(div("egx:296893"))]
    pred = div("egx:296893")
    pred["fields"]["amount_per_share"] = {
        "value": "1.9", "currency": "USD", "scale": "one"}
    r = S.score_cell(gold, [pred])
    ok = (_fs(r, "amount_per_share") == {"tp": 0, "fp": 1, "fn": 1}
          and r["accepted"] is False)
    return ok, ("amount=%s accepted=%s"
                % (_fs(r, "amount_per_share"), r["accepted"]))


def test_scale_canonicalisation():
    """Scale is canonicalised into base units: 0.0019 thousand ==
    1.9 one, and 63.079356 million == 63079356 one. A value in the
    wrong scale is a wrong value."""
    gold = [_gold(div("egx:296893"))]
    pred = div("egx:296893")
    pred["fields"]["amount_per_share"] = {
        "value": "0.0019", "currency": "EGP", "scale": "thousand"}
    r = S.score_cell(gold, [pred])
    ok_amount = (_fs(r, "amount_per_share")
                 == {"tp": 1, "fp": 0, "fn": 0} and r["accepted"] is True)
    gold2 = [_gold(earn("egx:297291", npat="63079356"))]
    pred2 = earn("egx:297291")
    pred2["fields"]["npat"] = {
        "value": "63.079356", "currency": "EGP", "scale": "million"}
    r2 = S.score_cell(gold2, [pred2])
    ok_npat = (_fs(r2, "npat") == {"tp": 1, "fp": 0, "fn": 0}
               and r2["accepted"] is True)
    gold3 = [_gold(earn("egx:297291", npat="63079356"))]
    pred3 = earn("egx:297291")
    pred3["fields"]["npat"] = {
        "value": "63.079356", "currency": "EGP", "scale": "thousand"}
    r3 = S.score_cell(gold3, [pred3])
    ok_wrong = (_fs(r3, "npat") == {"tp": 0, "fp": 1, "fn": 1}
                and r3["accepted"] is False)
    ok = ok_amount and ok_npat and ok_wrong
    return ok, ("amount-ok=%s npat-ok=%s wrong-scale=%s"
                % (ok_amount, ok_npat, ok_wrong))


def test_arabic_indic_digits():
    """Arabic-Indic digits normalise: D/M/YYYY in Eastern digits and
    an amount in Eastern digits equal their ASCII gold values."""
    gold = [_gold(div("egx:296893"))]
    pred = div("egx:296893", ex_date="١٦/١١/٢٠٢٦",
               amount_per_share="١.٩")
    r = S.score_cell(gold, [pred])
    ok = (_fs(r, "ex_date") == {"tp": 1, "fp": 0, "fn": 0}
          and _fs(r, "amount_per_share") == {"tp": 1, "fp": 0, "fn": 0}
          and r["accepted"] is True)
    return ok, ("ex=%s amount=%s accepted=%s"
                % (_fs(r, "ex_date"), _fs(r, "amount_per_share"),
                   r["accepted"]))


def test_zero_agreement_no_match():
    """A predicted event agreeing with gold on no scored field is not
    an identifiable event (spec §4.3): FP + FN, not a TP with all
    field errors."""
    gold = [_gold(div("egx:296893", coupon="41",
                      amount_per_share="1",
                      ex_date="2026-11-16",
                      entitlement_end="2026-11-15",
                      payout_date="2026-11-18",
                      announced="2026-11-02"))]
    pred = [div("egx:296893", coupon="42", amount_per_share="2",
                ex_date="2026-12-01", entitlement_end="2026-11-30",
                payout_date="2026-12-05", announced="2026-11-20")]
    r = S.score_cell(gold, pred)
    ok = (r["tp"] == 0 and r["fp"] == 1 and r["fn"] == 1
          and r["accepted"] is False and len(r["ambiguous"]) == 0)
    return ok, ("tp=%d fp=%d fn=%d ambiguous=%d"
                % (r["tp"], r["fp"], r["fn"], len(r["ambiguous"])))


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
    # --- #305 ---
    ("order-permutation", test_order_permutation),
    ("order-permutation-three-events", test_order_permutation_three_events),
    ("candidate-verified", test_candidate_verified),
    ("extracted-unverified", test_extracted_unverified),
    ("missing-extraction-status", test_missing_extraction_status),
    ("missing-verification-status", test_missing_verification_status),
    ("unknown-status", test_unknown_status),
    ("gold-with-status-rejected", test_gold_with_status_rejected),
    ("unknown-event-type", test_unknown_event_type),
    ("missing-issuer", test_missing_issuer),
    ("issuer-mismatch", test_issuer_mismatch),
    ("nested-extractor-adapter", test_nested_extractor_adapter),
    ("currency-mismatch", test_currency_mismatch),
    ("scale-canonicalisation", test_scale_canonicalisation),
    ("arabic-indic-digits", test_arabic_indic_digits),
    ("zero-agreement-no-match", test_zero_agreement_no_match),
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
