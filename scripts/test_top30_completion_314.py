#!/usr/bin/env python3
"""Negative controls for the #314 evaluation completion gate.

Run directly:  python3 scripts/test_top30_completion_314.py
Also wired into scripts/harness_issue109.py (--scorer). Stdlib only.

Every case is a (name, function) pair returning (ok, detail); the file
exits 0 only when every case passes. These are Ins's 8 required
regression cases (INS-314-COMPLETION-GATE-REVIEW 4/4), implemented
against scripts/top30_completion.py on top of the UNCHANGED scorer
(scripts/top30_scorer.py): in every case the scorer's `accepted`
keeps its main-tip meaning (pure per-cell threshold result) while
`complete` / the final outcome carry the separate completion state.

Case map:
  1. original 40-clean contested group (thresholds pass, both ledger
     entries retained, completion false);
  2. candidate outside `ambiguous`, sometimes-unmatched record with
     one tied gold ID, oversize group diluted by clean events (each
     unresolved case blocks completion);
  3. missing document / unfinished pagination / unknown
     collection-ledger state / omitted required cell (no final pass
     even if every supplied score passes);
  4. evidence-backed out-of-scope entry does not block, unknown scope
     does; changing a flag alone cannot exclude a case;
  5. resolved wrong field = complete-fail, unresolved eligible field
     = incomplete, documented absent field follows the frozen N/A
     policy;
  6. adjudication applied and re-scored vs merely marked resolved;
     stale/wrong-run decision, conflicting decisions, unresolved
     supersession fail closed; a resolved candidate cannot gain a TP
     by status rewriting;
  7. clean complete run passes; one failed cell prevents final pass;
     one blocked cell prevents completion; roll-ups rescue neither;
  8. genuine empty cell is complete-N/A, FN-only cell fails recall,
     all-N/A evaluation is not a quality pass; missing capture cannot
     produce an empty-cell success.

Issue #322 regressions (INS-314-POSTMERGE-REVIEW follow-up):
  9. omitted/empty/truncated ledger never passes while scorer
     outputs carry ambiguities/candidates; a frozen required-cell
     set is mandatory when cells are present;
  10. oversize/identical entries carry distinct IDs (reorder-stable),
      one decision cannot clear them all; identical candidates too;
  11. per-cell blocking reflects global collection failures;
  12. cross-document/issuer/type pairings are refused (same-document
      pairing still applies);
  13. decision/entry-kind compatibility (field/pairing on a candidate,
      scope on an ambiguity, any decision on a collection entry);
  14. negative collection counts and non-domain `accepted` values
      raise; cell_report derives unresolved_candidates from the
      effective ledger and keeps candidate_outputs separately.
"""
import inspect
import os
import sys
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import top30_completion as C
import top30_scorer as S

RUN = "run-314-test"
INP = "input-314-test"
CELL = ("POUL", "dividend")


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


def _gold(ev):
    g = dict(ev)
    g.pop("extraction_status", None)
    g.pop("verification_status", None)
    return g


def clean(n):
    gold, pred = [], []
    for i in range(n):
        gold.append(_gold(div("egx:clean%02d" % i, gold_id="g%d" % i)))
        pred.append(div("egx:clean%02d" % i, gold_id="g%d" % i))
    return gold, pred


def coll(enumerated=1, archived=1, missing=None, closed=True, paged=True):
    return {"enumerated": enumerated, "archived": archived,
            "missing": list(missing or []),
            "enumeration_closed": closed, "pagination_complete": paged}


_MISSING = object()


def gate(cell_results, ledger=(), decisions=(), collection=_MISSING,
         required=None, na_policy=None, adjudicated=None):
    return C.evaluate_completion(
        cell_results, run_digest=RUN, input_digest=INP,
        collection=coll() if collection is _MISSING else collection,
        ledger=ledger, decisions=decisions,
        required_cells=required if required is not None else [CELL],
        na_policy=na_policy, adjudicated=adjudicated)


def ledger_for(cell_results, collection=None, extra=()):
    return C.build_ledger(cell_results, run_digest=RUN, input_digest=INP,
                          collection=collection, extra_entries=extra)


def _entry_for_pred(ledger, pred):
    """Find the ledger entry built from one predicted event."""
    key = C._canonical_event_key(pred)
    for entry in ledger:
        if entry.get("detail", {}).get("predicted") == key:
            return entry
    raise AssertionError("no ledger entry for pred %r" % (pred,))


def _decision(did, kind, entry_ids, evidence="adjudicated vs source",
              supersedes=None, pairing=None):
    d = {"id": did, "kind": kind, "entry_ids": list(entry_ids),
         "run_digest": RUN, "input_digest": INP, "evidence": evidence}
    if supersedes is not None:
        d["supersedes"] = list(supersedes)
    if pairing is not None:
        d["pairing"] = pairing
    return d


def _contested_a3():
    """The faithful 40-clean contested-group construction (Ins probe
    A3): tie in amount_per_share, both preds wrong vs gold."""
    g, p = clean(40)
    g.append(_gold(div("egx:contest", gold_id="g1", coupon="1")))
    p.append(div("egx:contest", gold_id="p1", coupon="1",
                 amount_per_share="2"))
    p.append(div("egx:contest", gold_id="p2", coupon="1",
                 amount_per_share="3"))
    return S.score_cell(g, p)


# --- Ins case 1 -----------------------------------------------------------
def test_case1_contested_group_blocks():
    r = _contested_a3()
    if not ((r["tp"], r["fp"], r["fn"]) == (40, 2, 1)
            and r["precision"] == Fraction(20, 21)
            and r["recall"] == Fraction(40, 41)
            and r["accepted"] is True and len(r["ambiguous"]) == 2):
        return False, "A3 fixture drifted: %s" % (r,)
    ledger = ledger_for({CELL: r})
    out = gate({CELL: r}, ledger=ledger)
    ok = (out["complete"] is False and out["outcome"] == "incomplete"
          and len(out["unresolved"]) == 2
          and r["accepted"] is True)
    return ok, ("accepted=True thresholds pass, ledger=%d, complete=%r "
                "outcome=%s" % (len(ledger), out["complete"],
                                out["outcome"]))


# --- Ins case 2 -----------------------------------------------------------
def test_case2_candidate_blocks():
    g, p = clean(40)
    cand = div("egx:cand", gold_id="px")
    cand["verification_status"] = "unverified"
    p.append(cand)
    r = S.score_cell(g, p)
    if not ((r["tp"], r["fp"], r["fn"]) == (40, 1, 0)
            and r["accepted"] is True and r["ambiguous"] == []):
        return False, "candidate fixture drifted: %s" % (r,)
    ledger = ledger_for({CELL: r})
    out = gate({CELL: r}, ledger=ledger)
    ok = (len(ledger) == 1 and ledger[0]["kind"] == "candidate"
          and out["complete"] is False
          and out["outcome"] == "incomplete" and r["accepted"] is True)
    return ok, ("candidate outside ambiguous: ledger=%d kind=%s, "
                "accepted=True, complete=%r"
                % (len(ledger), ledger[0]["kind"] if ledger else "?",
                   out["complete"]))


def test_case2_sometimes_unmatched_blocks():
    g, p = clean(40)
    g.append(_gold(div("egx:tie", gold_id="g1", coupon="1")))
    p.append(div("egx:tie", gold_id="p1", coupon="1",
                 amount_per_share="2"))
    p.append(div("egx:tie", gold_id="p2", coupon="2",
                 amount_per_share="1.9"))
    r = S.score_cell(g, p)
    if not ((r["tp"], r["fp"], r["fn"]) == (40, 2, 1)
            and r["accepted"] is True and len(r["ambiguous"]) == 2
            and all(len(a.get("tied_gold_ids") or []) == 1
                    for a in r["ambiguous"])
            and all(a.get("unmatched_in_an_optimum") is True
                    for a in r["ambiguous"])):
        return False, "sometimes-unmatched fixture drifted: %s" % (r,)
    ledger = ledger_for({CELL: r})
    out = gate({CELL: r}, ledger=ledger)
    ok = (len(ledger) == 2 and out["complete"] is False
          and out["outcome"] == "incomplete")
    return ok, ("one tied gold + unmatched-in-an-optimum: ledger=%d, "
                "complete=%r" % (len(ledger), out["complete"]))


def test_case2_oversize_diluted_blocks():
    g, p = clean(400)
    for i in range(16):
        g.append(_gold(div("egx:big", gold_id="g%d" % i)))
        p.append(div("egx:big", gold_id="p%d" % i))
    r = S.score_cell(g, p)
    if not ((r["tp"], r["fp"], r["fn"]) == (400, 16, 16)
            and r["accepted"] is True and len(r["ambiguous"]) == 16
            and all(a.get("oversize_group") is True
                    for a in r["ambiguous"])):
        return False, "oversize fixture drifted: %s" % (r,)
    ledger = ledger_for({CELL: r})
    out = gate({CELL: r}, ledger=ledger)
    ok = (len(ledger) == 16 and out["complete"] is False
          and out["outcome"] == "incomplete")
    return ok, ("oversize diluted by 400 clean: ledger=%d, "
                "complete=%r" % (len(ledger), out["complete"]))


# --- Ins case 3 -----------------------------------------------------------
def test_case3_collection_gaps_block():
    g, p = clean(1)
    r = S.score_cell(g, p)
    if r["accepted"] is not True:
        return False, "clean cell drifted: accepted=%r" % (r["accepted"],)
    variants = [
        ("missing document",
         gate({CELL: r}, collection=coll(missing=["egx:999"]))),
        ("unfinished pagination",
         gate({CELL: r}, collection=coll(paged=False))),
        ("enumeration not closed",
         gate({CELL: r}, collection=coll(closed=False))),
        ("unknown collection state",
         gate({CELL: r}, collection=None)),
        ("omitted required cell",
         gate({CELL: r}, required=[CELL, ("COMI", "earnings")])),
    ]
    bad = [name for name, out in variants
           if out["complete"] is not False
           or out["outcome"] != "incomplete"]
    ok = not bad
    return ok, ("all five gap variants incomplete: %s"
                % ("OK" if ok else "PASSED: %s" % (bad,)))


# --- Ins case 4 -----------------------------------------------------------
def test_case4_out_of_scope():
    g, p = clean(1)
    r = S.score_cell(g, p)
    entry = {"id": "scope-1", "kind": "scope", "cell": CELL,
             "source_document_id": "egx:ooo", "event_type": "dividend",
             "issuer": "POUL", "scope": "out_of_scope",
             "detail": {"reason": "document outside frozen quarter"}}
    dec = _decision("dec-scope-1", "scope", ["scope-1"],
                    evidence="manifest quarter window 2026-08-19.."
                             "2026-11-19 excludes egx:ooo")
    out_ok = gate({CELL: r}, ledger=[entry], decisions=[dec])
    out_nod = gate({CELL: r}, ledger=[entry])
    stale = dict(dec, run_digest="another-run")
    out_stale = gate({CELL: r}, ledger=[entry], decisions=[stale])
    ok = (out_ok["complete"] is True
          and out_ok["outcome"] == "complete-pass"
          and len(out_ok["excluded"]) == 1
          and out_nod["complete"] is False
          and out_stale["complete"] is False)
    return ok, ("evidence-backed exclusion passes (excluded=%d); "
                "flag alone / stale decision block: %r/%r"
                % (len(out_ok["excluded"]), out_nod["complete"],
                   out_stale["complete"]))


# --- Ins case 5 -----------------------------------------------------------
def test_case5_fields():
    gold = [_gold(div("egx:296893"))]
    pred = [div("egx:296893", ex_date="2026-11-18",
                payout_date="2026-11-16")]
    r = S.score_cell(gold, pred)
    if r["accepted"] is not False:
        return False, "swapped-date cell drifted: accepted=%r" % (
            r["accepted"],)
    field_entry = {"id": "field-ex-1", "kind": "field", "cell": CELL,
                   "source_document_id": "egx:296893",
                   "event_type": "dividend", "issuer": "POUL",
                   "scope": "in_scope", "field": "ex_date",
                   "detail": {"reason": "swapped ex/payout dates"}}
    dec = _decision("dec-field-1", "field", ["field-ex-1"],
                    evidence="source bulletin shows ex 2026-11-16; "
                             "extractor swapped the two dates")
    out_resolved = gate({CELL: r}, ledger=[field_entry], decisions=[dec])
    out_open = gate({CELL: r}, ledger=[field_entry])
    # Documented absent field follows the frozen N/A policy.
    g2, p2 = clean(1)
    r2 = S.score_cell(g2, p2)
    absent_entry = {"id": "field-rec-1", "kind": "field", "cell": CELL,
                    "source_document_id": "egx:clean00",
                    "event_type": "dividend", "issuer": "POUL",
                    "scope": "in_scope", "field": "record_date",
                    "na_documented": True,
                    "detail": {"reason": "record date not in EGX body"}}
    dec_absent = _decision("dec-field-2", "field", ["field-rec-1"],
                           evidence="spec §6: record date not in EGX "
                                    "body; derived candidate only")
    na_policy = {CELL: {"record_date"}}
    out_absent = gate({CELL: r2}, ledger=[absent_entry],
                      decisions=[dec_absent], na_policy=na_policy)
    out_absent_nopolicy = gate({CELL: r2}, ledger=[absent_entry],
                               decisions=[dec_absent])
    ok = (out_resolved["complete"] is True
          and out_resolved["outcome"] == "complete-fail"
          and out_open["complete"] is False
          and out_absent["complete"] is True
          and out_absent["outcome"] == "complete-pass"
          and len(out_absent["documented_absent"]) == 1
          and out_absent_nopolicy["complete"] is False)
    return ok, ("resolved wrong field -> %s; unresolved -> incomplete; "
                "documented absent -> %s (no policy -> incomplete)"
                % (out_resolved["outcome"], out_absent["outcome"]))


# --- Ins case 6 -----------------------------------------------------------
def test_case6_adjudication_applied_vs_marked():
    r = _contested_a3()
    ledger = ledger_for({CELL: r})
    p1 = [a["predicted"] for a in r["ambiguous"]
          if a["predicted"]["gold_id"] == "p1"][0]
    p2 = [a["predicted"] for a in r["ambiguous"]
          if a["predicted"]["gold_id"] == "p2"][0]
    g1 = [g for g in r["unmatched_gold"]
          if g.get("gold_id") == "g1"][0]
    e1 = _entry_for_pred(ledger, p1)["id"]
    e2 = _entry_for_pred(ledger, p2)["id"]
    pair = _decision("dec-pair-1", "pairing", [e1],
                     pairing={"predicted_event": p1, "gold_event": g1})
    dup = _decision("dec-dup-1", "duplicate", [e2],
                    evidence="p2 is a second claim on the same gold "
                             "event, adjudicated duplicate")
    # (a) applied + re-scored: complete-pass on the adjudicated counts.
    rescored = C.apply_adjudication(r, [pair], run_digest=RUN,
                                    input_digest=INP)
    if not ((rescored["tp"], rescored["fp"], rescored["fn"]) == (41, 1, 0)
            and rescored["accepted"] is True
            and rescored["adjudication_applied"] == ["dec-pair-1"]):
        return False, "adapter re-score drifted: %s" % (rescored,)
    if (r["tp"], r["fp"], r["fn"]) != (40, 2, 1):
        return False, "adapter mutated the original result"
    out_applied = gate({CELL: r}, ledger=ledger, decisions=[pair, dup],
                       adjudicated={CELL: rescored})
    # (b) merely marked resolved (no re-scored result): incomplete.
    out_marked = gate({CELL: r}, ledger=ledger, decisions=[pair, dup])
    # (c) stale decision: incomplete.
    stale = dict(pair, run_digest="another-run")
    out_stale = gate({CELL: r}, ledger=ledger, decisions=[stale, dup])
    # (d) conflicting decisions over the same entry: incomplete.
    rival = _decision("dec-pair-2", "pairing", [e1],
                      pairing={"predicted_event": p2, "gold_event": g1})
    out_conflict = gate({CELL: r}, ledger=ledger,
                        decisions=[pair, rival, dup])
    # (e) unresolved supersession (supersedes unknown id): incomplete.
    orphan = dict(pair, id="dec-pair-9", supersedes=["no-such-decision"])
    out_orphan = gate({CELL: r}, ledger=ledger,
                      decisions=[orphan, dup])
    # (e2) supersession cycle: incomplete.
    cyc_a = _decision("dec-cyc-a", "reject_event", [e1],
                      supersedes=["dec-cyc-b"])
    cyc_b = _decision("dec-cyc-b", "reject_event", [e1],
                      supersedes=["dec-cyc-a"])
    out_cycle = gate({CELL: r}, ledger=ledger,
                     decisions=[cyc_a, cyc_b, dup])
    ok = (out_applied["complete"] is True
          and out_applied["outcome"] == "complete-pass"
          and out_marked["complete"] is False
          and out_stale["complete"] is False
          and out_conflict["complete"] is False
          and out_orphan["complete"] is False
          and out_cycle["complete"] is False)
    return ok, ("applied+rescored -> %s; marked/stale/conflict/orphan/"
                "cycle -> incomplete: %r/%r/%r/%r/%r"
                % (out_applied["outcome"], out_marked["complete"],
                   out_stale["complete"], out_conflict["complete"],
                   out_orphan["complete"], out_cycle["complete"]))


def test_case6_candidate_cannot_gain_tp():
    g, p = clean(40)
    cand = div("egx:cand", gold_id="px")
    cand["verification_status"] = "unverified"
    p.append(cand)
    r = S.score_cell(g, p)
    ledger = ledger_for({CELL: r})
    if len(ledger) != 1 or ledger[0]["kind"] != "candidate":
        return False, "candidate ledger drifted: %s" % (ledger,)
    gold_target = r["matches"][0]["gold"]
    pair = _decision("dec-cand-pair", "pairing", [ledger[0]["id"]],
                     pairing={"predicted_event": cand,
                              "gold_event": gold_target})
    try:
        C.apply_adjudication(r, [pair], run_digest=RUN, input_digest=INP)
    except ValueError as e:
        if "candidate" not in str(e):
            return False, "wrong refusal: %r" % (e,)
    else:
        return False, "adapter granted a TP to a candidate"
    out = gate({CELL: r}, ledger=ledger, decisions=[pair])
    ok = out["complete"] is False and out["outcome"] == "incomplete"
    return ok, ("candidate pairing refused by the adapter; gate stays "
                "incomplete: %r" % (out["complete"],))


# --- Ins case 7 -----------------------------------------------------------
def test_case7_rollups_rescue_nothing():
    g, p = clean(1)
    clean_r = S.score_cell(g, p)
    gold = [_gold(div("egx:296893"))]
    pred = [div("egx:296893", ex_date="2026-11-18",
                payout_date="2026-11-16")]
    fail_r = S.score_cell(gold, pred)
    blocked_r = _contested_a3()
    blocked_ledger = ledger_for({CELL: blocked_r})
    cell_b = ("COMI", "earnings")
    out_clean = gate({CELL: clean_r})
    out_fail = gate({CELL: fail_r})
    out_blocked = gate({CELL: blocked_r}, ledger=blocked_ledger)
    out_mixed_fail = gate({CELL: clean_r, cell_b: fail_r},
                          required=[CELL, cell_b])
    out_mixed_blocked = gate({CELL: clean_r, cell_b: blocked_r},
                             ledger=blocked_ledger,
                             required=[CELL, cell_b])
    ok = (out_clean["complete"] is True
          and out_clean["outcome"] == "complete-pass"
          and out_fail["complete"] is True
          and out_fail["outcome"] == "complete-fail"
          and out_blocked["complete"] is False
          and out_mixed_fail["complete"] is True
          and out_mixed_fail["outcome"] == "complete-fail"
          and out_mixed_blocked["complete"] is False
          and out_mixed_blocked["outcome"] == "incomplete")
    return ok, ("clean %s; failed cell %s; blocked %s; mixed fail %s; "
                "mixed blocked %s"
                % (out_clean["outcome"], out_fail["outcome"],
                   out_blocked["outcome"], out_mixed_fail["outcome"],
                   out_mixed_blocked["outcome"]))


# --- Ins case 8 -----------------------------------------------------------
def test_case8_empty_cells():
    empty = S.score_cell([], [])
    if empty["accepted"] is not None:
        return False, "empty cell drifted: accepted=%r" % (
            empty["accepted"],)
    zero_coll = coll(enumerated=0, archived=0)
    out_empty = gate({CELL: empty}, collection=zero_coll)
    fn_gold = [_gold(div("egx:x"))]
    fn_r = S.score_cell(fn_gold, [])
    out_fn = gate({CELL: fn_r})
    out_all_na = gate({CELL: empty, ("COMI", "earnings"): empty},
                      collection=zero_coll,
                      required=[CELL, ("COMI", "earnings")])
    out_no_capture = gate({CELL: empty}, collection=None)
    ok = (out_empty["complete"] is True
          and out_empty["outcome"] == "complete-N/A"
          and out_fn["complete"] is True
          and out_fn["outcome"] == "complete-fail"
          and out_all_na["complete"] is True
          and out_all_na["outcome"] == "complete-N/A"
          and out_no_capture["complete"] is False)
    return ok, ("genuine empty -> %s; FN-only -> %s; all-N/A -> %s "
                "(not a pass); missing capture -> incomplete"
                % (out_empty["outcome"], out_fn["outcome"],
                   out_all_na["outcome"]))


# --- issue #322 regressions --------------------------------------------
# Each test is written from scratch against the fixed gate: the
# fixture is built here (own docs/coupons/counts), the BEFORE
# behaviour is the hole the issue records, and the test asserts the
# AFTER behaviour. Failing-before was verified with the probe run
# in ~/workspace/scratch-322/ (12-claim re-derivation: 10/12
# confirmed as written, F1c confirmed in the issue's thresholds-pass
# form, F5 confirmed as complete=True with outcome complete-fail
# because the single-candidate cell genuinely fails thresholds).

def _contested_322():
    """Own contested construction: 40 clean + one tie. Two preds
    claim one gold with equal agreement (each agrees on coupon +
    one of amount/ex_date, differs on the other), so both stay
    ambiguous and thresholds still pass (tp=40 fp=2 fn=1)."""
    g, p = [], []
    for i in range(40):
        g.append(_gold(div("egx:clean322-%02d" % i, gold_id="g%d" % i,
                           coupon=str(500 + i))))
        p.append(div("egx:clean322-%02d" % i, gold_id="g%d" % i,
                     coupon=str(500 + i)))
    g.append(_gold(div("egx:tie322", gold_id="g-tie", coupon="77")))
    p.append(div("egx:tie322", gold_id="p-a", coupon="77",
                 amount_per_share="2.1"))
    p.append(div("egx:tie322", gold_id="p-b", coupon="77",
                 ex_date="2026-11-17"))
    return S.score_cell(g, p)


def test_322_f1_omitted_ledger_blocks():
    r = _contested_322()
    if not ((r["tp"], r["fp"], r["fn"]) == (40, 2, 1)
            and r["accepted"] is True and len(r["ambiguous"]) == 2):
        return False, "322 contested fixture drifted: %s" % (r,)
    out_none = gate({CELL: r})  # helper passes no ledger
    out_empty = gate({CELL: r}, ledger=[])
    ledger = ledger_for({CELL: r})
    out_full = gate({CELL: r}, ledger=ledger)
    truncated = gate({CELL: r}, ledger=ledger[:1])
    ok = (out_none["complete"] is False
          and out_none["outcome"] == "incomplete"
          and len(out_none["unresolved"]) == 2
          and out_empty["complete"] is False
          and out_full["complete"] is False
          and len(out_full["unresolved"]) == 2
          and truncated["complete"] is False
          and len(truncated["unresolved"]) == 2
          and any("ledger incomplete" in reason
                  for reason in truncated["reasons"]))
    return ok, ("omitted ledger -> %s (unresolved=%d); empty -> %s; "
                "truncated 1/2 -> %s (unresolved=%d, flagged); full "
                "ledger still blocks: %s"
                % (out_none["complete"], len(out_none["unresolved"]),
                   out_empty["complete"], truncated["complete"],
                   len(truncated["unresolved"]),
                   out_full["complete"]))


def test_322_f1_candidate_omitted_ledger_blocks():
    g, p = [], []
    for i in range(40):
        g.append(_gold(div("egx:clean322-%02d" % i, gold_id="g%d" % i,
                           coupon=str(500 + i))))
        p.append(div("egx:clean322-%02d" % i, gold_id="g%d" % i,
                     coupon=str(500 + i)))
    cand = div("egx:cand322", gold_id="px", coupon="77")
    cand["extraction_status"] = "candidate"
    p.append(cand)
    r = S.score_cell(g, p)
    if not ((r["tp"], r["fp"], r["fn"]) == (40, 1, 0)
            and r["accepted"] is True and r["ambiguous"] == []):
        return False, "322 candidate fixture drifted: %s" % (r,)
    out_none = gate({CELL: r})
    out_with = gate({CELL: r}, ledger=ledger_for({CELL: r}))
    ok = (out_none["complete"] is False
          and out_none["outcome"] == "incomplete"
          and len(out_none["unresolved"]) == 1
          and out_none["unresolved"][0]["kind"] == "candidate"
          and out_with["complete"] is False)
    return ok, ("40 clean + 1 candidate, thresholds pass, ledger "
                "omitted -> %s (unresolved=%d, kind=%s)"
                % (out_none["complete"], len(out_none["unresolved"]),
                   out_none["unresolved"][0]["kind"]
                   if out_none["unresolved"] else "?"))


def test_322_f1_required_cells_unverified():
    g, p = clean(1)
    r = S.score_cell(g, p)
    out_no_universe = C.evaluate_completion(
        {CELL: r}, run_digest=RUN, input_digest=INP, collection=coll(),
        ledger=ledger_for({CELL: r}), required_cells=())
    out_frozen = C.evaluate_completion(
        {CELL: r}, run_digest=RUN, input_digest=INP, collection=coll(),
        ledger=ledger_for({CELL: r}), required_cells=[CELL])
    ok = (out_no_universe["complete"] is False
          and out_no_universe["outcome"] == "incomplete"
          and any("required-cell set not supplied" in reason
                  for reason in out_no_universe["reasons"])
          and out_frozen["complete"] is True
          and out_frozen["outcome"] == "complete-pass")
    return ok, ("cells present, no frozen required-cell set -> %s; "
                "same cells with the set -> %s"
                % (out_no_universe["complete"],
                   out_frozen["outcome"]))


def test_322_f2_oversize_distinct_ids():
    g16 = [_gold(div("egx:big322", gold_id="g%d" % i, coupon="9"))
           for i in range(16)]
    p16 = [div("egx:big322", gold_id="p%d" % i, coupon="9")
           for i in range(16)]
    r = S.score_cell(g16, p16)
    if not (len(r["ambiguous"]) == 16
            and all(a.get("oversize_group") is True
                    for a in r["ambiguous"])):
        return False, "322 oversize fixture drifted: %s" % (r,)
    ledger = ledger_for({CELL: r})
    ids = [e["id"] for e in ledger]
    # Reorder stability: the same entries in reverse order give the
    # same ID multiset (identical entries are interchangeable).
    shuffled = dict(r)
    shuffled["ambiguous"] = list(reversed(r["ambiguous"]))
    ledger_rev = C.build_ledger({CELL: shuffled}, run_digest=RUN,
                                input_digest=INP)
    ids_rev = sorted(e["id"] for e in ledger_rev)
    # One decision over ONE id clears one entry, not all sixteen.
    one = _decision("dec-322-one", "duplicate", [ids[0]],
                    evidence="p0 duplicates the p1 claim on g0")
    out_one = gate({CELL: r}, ledger=ledger, decisions=[one])
    ok = (len(ledger) == 16 and len(set(ids)) == 16
          and sorted(ids) == ids_rev
          and out_one["complete"] is False
          and len(out_one["unresolved"]) == 15)
    return ok, ("16 oversize entries -> %d distinct IDs; reorder "
                "keeps the ID multiset; one decision leaves %d "
                "unresolved, complete=%r"
                % (len(set(ids)), len(out_one["unresolved"]),
                   out_one["complete"]))


def test_322_f2_identical_candidates_distinct_ids():
    cands = []
    for _ in range(3):
        c = div("egx:dup322", gold_id="px", coupon="77")
        c["extraction_status"] = "candidate"
        cands.append(c)
    r = S.score_cell([], cands)
    ledger = ledger_for({CELL: r})
    cand_ids = [e["id"] for e in ledger if e["kind"] == "candidate"]
    ok = (len(ledger) == 3 and len(set(cand_ids)) == 3)
    return ok, ("3 identical candidates -> %d entries, %d distinct "
                "IDs" % (len(ledger), len(set(cand_ids))))


def test_322_f3_per_cell_blocked_on_collection_failure():
    g, p = clean(1)
    r = S.score_cell(g, p)
    variants = [
        ("missing document, no ledger",
         gate({CELL: r}, collection=coll(missing=["egx:gone322"]))),
        ("unknown collection",
         gate({CELL: r}, collection=None)),
        ("unfinished pagination",
         gate({CELL: r}, collection=coll(paged=False))),
    ]
    bad = []
    for name, out in variants:
        cell = out["per_cell"].get("POUL|dividend", {})
        if out["complete"] is not False or cell.get("blocked") is not True \
                or not any("collection:" in b
                           for b in cell.get("blocking", [])):
            bad.append(name)
    control = gate({CELL: r}, collection=coll())
    ok = (not bad
          and control["per_cell"]["POUL|dividend"]["blocked"] is False)
    return ok, ("missing/unknown/unfinished collection blocks the "
                "cell (blocked=True, collection reason listed): %s; "
                "complete collection leaves it unblocked: %r"
                % ("OK" if not bad else "NOT BLOCKED: %s" % (bad,),
                   control["per_cell"]["POUL|dividend"]["blocked"]))


def test_322_f4_cross_document_pairing_refused():
    def pair_dec(did, pred_ev, gold_ev):
        return _decision(did, "pairing", ["entry-322"],
                         pairing={"predicted_event": pred_ev,
                                  "gold_event": gold_ev})
    # Cross-document: gold in egx:docA322, prediction in egx:docB322.
    ga = _gold(div("egx:docA322", gold_id="gA", coupon="7"))
    pb = div("egx:docB322", gold_id="pB", coupon="7")
    r_doc = S.score_cell([ga], [pb])
    # Cross-issuer: same document, different issuer.
    gc = _gold(div("egx:docC322", gold_id="gC", coupon="7"))
    pi = div("egx:docC322", issuer="COMI", gold_id="pI", coupon="7")
    r_iss = S.score_cell([gc], [pi])
    # Cross-type: dividend gold, earnings prediction, same document.
    gt = _gold(div("egx:docD322", gold_id="gT", coupon="7"))
    pe = {"source_document_id": "egx:docD322", "event_type": "earnings",
          "issuer": "POUL", "extraction_status": "extracted",
          "verification_status": "verified",
          "fields": {"period_start": "2026-01-01",
                     "period_end": "2026-03-31", "npat": "100",
                     "npat_scale": "million", "npat_comparative": "90",
                     "yoy_npat_pct": "11", "revenue": "500",
                     "announced": "2026-04-01"}}
    r_typ = S.score_cell([gt], [pe])
    refused = []
    for name, res, dec in [
            ("document", r_doc, pair_dec("d-322-doc", pb, ga)),
            ("issuer", r_iss, pair_dec("d-322-iss", pi, gc)),
            ("type", r_typ, pair_dec("d-322-typ", pe, gt))]:
        try:
            C.apply_adjudication(res, [dec], run_digest=RUN,
                                 input_digest=INP)
        except ValueError as e:
            if "different" not in str(e):
                return False, "%s pairing refused for the wrong reason: %r" % (name, e)
            refused.append(name)
        else:
            return False, "%s pairing granted a cross-boundary TP" % name
    # Positive control: same document/issuer/type pairing applies.
    g0 = _gold(div("egx:pair322", gold_id="g0", coupon="5"))
    q1 = div("egx:pair322", gold_id="q1", coupon="5",
             amount_per_share="2.1")
    q2 = div("egx:pair322", gold_id="q2", coupon="5",
             ex_date="2026-11-17")
    r_ok = S.score_cell([g0], [q1, q2])
    dec_ok = pair_dec("d-322-ok", q1, g0)
    rescored = C.apply_adjudication(r_ok, [dec_ok], run_digest=RUN,
                                    input_digest=INP)
    ok = (refused == ["document", "issuer", "type"]
          and (rescored["tp"], rescored["fp"], rescored["fn"]) == (1, 1, 0))
    return ok, ("cross-document/issuer/type pairings refused (%s); "
                "same-document pairing applies: tp/fp/fn=%s"
                % ("/".join(refused),
                   (rescored["tp"], rescored["fp"], rescored["fn"])))


def test_322_f5_kind_mismatch_refused():
    cand = div("egx:cand322", gold_id="px", coupon="77")
    cand["extraction_status"] = "candidate"
    r = S.score_cell([_gold(div("egx:cand322", gold_id="g1",
                                coupon="77"))], [cand])
    ledger = ledger_for({CELL: r})
    if len(ledger) != 1 or ledger[0]["kind"] != "candidate":
        return False, "322 candidate ledger drifted: %s" % (ledger,)
    eid = ledger[0]["id"]
    field_dec = _decision("d-322-field", "field", [eid],
                          evidence="resolved as not an event")
    out_field = gate({CELL: r}, ledger=ledger, decisions=[field_dec])
    # A pairing decision over the candidate entry: the adapter
    # refuses the TP and the gate stays incomplete.
    pair_dec = _decision(
        "d-322-pair", "pairing", [eid],
        pairing={"predicted_event": cand,
                 "gold_event": r["unmatched_gold"][0]})
    try:
        C.apply_adjudication(r, [pair_dec], run_digest=RUN,
                             input_digest=INP)
    except ValueError:
        adapter_refused = True
    else:
        adapter_refused = False
    out_pair = gate({CELL: r}, ledger=ledger, decisions=[pair_dec])
    # A scope decision over an ambiguity entry is likewise not a
    # resolution (out-of-scope goes through a scope ledger entry).
    r_amb = _contested_322()
    ledger_amb = ledger_for({CELL: r_amb})
    scope_dec = _decision("d-322-scope", "scope",
                          [ledger_amb[0]["id"]],
                          evidence="document outside the frozen window")
    out_scope = gate({CELL: r_amb}, ledger=ledger_amb,
                     decisions=[scope_dec])
    # Positive control: reject_event resolves the candidate entry
    # (the cell still fails thresholds, so complete-fail).
    rej_dec = _decision("d-322-rej", "reject_event", [eid],
                        evidence="candidate is not an event per source")
    out_rej = gate({CELL: r}, ledger=ledger, decisions=[rej_dec])
    ok = (out_field["complete"] is False
          and any("cannot resolve" in reason
                  for reason in out_field["reasons"])
          and adapter_refused
          and out_pair["complete"] is False
          and out_scope["complete"] is False
          and out_rej["complete"] is True
          and out_rej["outcome"] == "complete-fail")
    return ok, ("field/pairing decisions on a candidate entry and a "
                "scope decision on an ambiguity entry all leave the "
                "gate incomplete (adapter refused the pairing: %r); "
                "reject_event resolves it -> %s"
                % (adapter_refused, out_rej["outcome"]))


def test_322_f5_collection_entry_not_decision_closed():
    g, p = clean(1)
    r = S.score_cell(g, p)
    missing = coll(missing=["egx:gone322"])
    ledger = ledger_for({CELL: r}, collection=missing)
    coll_entries = [e for e in ledger if e["kind"] == "collection"]
    if len(coll_entries) != 1:
        return False, "322 collection ledger drifted: %s" % (ledger,)
    dec = _decision("d-322-coll", "field", [coll_entries[0]["id"]],
                    evidence="document judged irrelevant")
    out_dec = gate({CELL: r}, ledger=ledger, decisions=[dec],
                   collection=missing)
    # Control: the same entry closes when the collection state shows
    # the document archived (evidence, not a decision).
    out_evidence = gate({CELL: r}, ledger=ledger, collection=coll())
    # The entry-level check matters, not just the gate outcome: the
    # global collection reason blocks completion either way, so the
    # test pins that the entry itself stays UNRESOLVED under a
    # decision (on the old code it was wrongly resolved and
    # unresolved was empty).
    ok = (out_dec["complete"] is False
          and out_dec["outcome"] == "incomplete"
          and coll_entries[0]["id"] in [e["id"] for e in
                                         out_dec["unresolved"]]
          and out_evidence["complete"] is True
          and out_evidence["outcome"] == "complete-pass")
    return ok, ("decision cannot close a missing-document entry "
                "(%s, entry unresolved: %r); collection evidence "
                "closes it (%s)"
                % (out_dec["complete"],
                   coll_entries[0]["id"] in [e["id"] for e in
                                             out_dec["unresolved"]],
                   out_evidence["outcome"]))


def test_322_f6_negative_counts_raise():
    for name, c in [
            ("enumerated=-5/archived=-5",
             coll(enumerated=-5, archived=-5)),
            ("archived=-1", coll(enumerated=3, archived=-1)),
            ("enumerated=-1", coll(enumerated=-1, archived=0))]:
        try:
            gate({CELL: S.score_cell(*clean(1))}, collection=c)
        except ValueError as e:
            if "non-negative" not in str(e):
                return False, "%s raised the wrong error: %r" % (name, e)
        else:
            return False, "%s did not raise" % name
    return True, "negative enumerated/archived counts raise ValueError"


def test_322_f7_bogus_accepted_raises():
    for name, acc in [("bogus string", "bogus"),
                      ("int 1 (== True)", 1), ("int 0 (== False)", 0),
                      ("string 'True'", "True")]:
        fake = {"accepted": acc, "tp": 0, "fp": 0, "fn": 0}
        try:
            C.evaluate_completion(
                {CELL: fake}, run_digest=RUN, input_digest=INP,
                collection=coll(), required_cells=[CELL])
        except ValueError as e:
            if "accepted" not in str(e):
                return False, "%s raised the wrong error: %r" % (name, e)
        else:
            return False, "%s accepted=%r did not raise" % (name, acc)
    control = gate({CELL: S.score_cell(*clean(1))})
    ok = control["complete"] is True \
        and control["outcome"] == "complete-pass"
    return ok, ("non-domain accepted values raise ValueError; "
                "True still passes (%s)" % (control["outcome"],))


def test_322_f8_report_candidates_from_ledger():
    cand = div("egx:cand322", gold_id="px", coupon="77")
    cand["extraction_status"] = "candidate"
    r = S.score_cell([_gold(div("egx:cand322", gold_id="g1",
                                coupon="77"))], [cand])
    ledger = ledger_for({CELL: r})
    rej = _decision("d-322-rej8", "reject_event", [ledger[0]["id"]],
                    evidence="candidate is not an event per source")
    rep_resolved = C.cell_report(
        r, CELL, run_digest=RUN, input_digest=INP, collection=coll(),
        ledger=ledger, decisions=[rej])
    rep_open = C.cell_report(
        r, CELL, run_digest=RUN, input_digest=INP, collection=coll(),
        ledger=ledger)
    ok = (rep_resolved["complete"] is True
          and rep_resolved["unresolved_candidates"] == 0
          and rep_resolved["candidate_outputs"] == 1
          and rep_open["complete"] is False
          and rep_open["unresolved_candidates"] == 1
          and rep_open["candidate_outputs"] == 1)
    return ok, ("resolved candidate: complete=%r, "
                "unresolved_candidates=%d, candidate_outputs=%d; "
                "unresolved: complete=%r, unresolved_candidates=%d"
                % (rep_resolved["complete"],
                   rep_resolved["unresolved_candidates"],
                   rep_resolved["candidate_outputs"],
                   rep_open["complete"],
                   rep_open["unresolved_candidates"]))


# --- accepted semantics unchanged -----------------------------------------
def test_accepted_unchanged():
    """The scorer's `accepted` is the pure threshold result at this
    pin: the A3/B/C probes score accepted=True with open cases, and
    score_cell takes no collection evidence (Ins Q1)."""
    params = list(inspect.signature(S.score_cell).parameters)
    if params != ["gold_events", "predicted_events"]:
        return False, "score_cell signature changed: %r" % (params,)
    g, p = clean(40)
    cand = div("egx:cand", gold_id="px")
    cand["verification_status"] = "unverified"
    p.append(cand)
    r_b = S.score_cell(g, p)
    ok = (_contested_a3()["accepted"] is True
          and r_b["accepted"] is True and r_b["ambiguous"] == [])
    return ok, ("score_cell(gold, predicted) only; A3 accepted=True, "
                "candidate case accepted=True with ambiguous=[]")


def test_cell_report_shape():
    """§8 per-cell report: collection, counts, verified vs candidate
    counts, unresolved ledger, and completion kept separate from the
    provisional `accepted`."""
    r = _contested_a3()
    ledger = ledger_for({CELL: r})
    rep = C.cell_report(r, CELL, run_digest=RUN, input_digest=INP,
                       collection=coll(enumerated=41, archived=41),
                       ledger=ledger)
    ok = (rep["accepted"] is True and rep["complete"] is False
          and rep["outcome"] == "incomplete"
          and (rep["tp"], rep["fp"], rep["fn"]) == (40, 2, 1)
          and rep["verified_matches"] == 40
          and len(rep["unresolved_ledger"]) == 2)
    return ok, ("report: accepted=True (provisional), complete=False, "
                "outcome=incomplete, verified=%d, unresolved=%d"
                % (rep["verified_matches"],
                   len(rep["unresolved_ledger"])))


CASES = [
    ("314-case1-contested-group-blocks", test_case1_contested_group_blocks),
    ("314-case2-candidate-blocks", test_case2_candidate_blocks),
    ("314-case2-sometimes-unmatched-blocks",
     test_case2_sometimes_unmatched_blocks),
    ("314-case2-oversize-diluted-blocks",
     test_case2_oversize_diluted_blocks),
    ("314-case3-collection-gaps-block", test_case3_collection_gaps_block),
    ("314-case4-out-of-scope", test_case4_out_of_scope),
    ("314-case5-fields", test_case5_fields),
    ("314-case6-adjudication-applied-vs-marked",
     test_case6_adjudication_applied_vs_marked),
    ("314-case6-candidate-cannot-gain-tp",
     test_case6_candidate_cannot_gain_tp),
    ("314-case7-rollups-rescue-nothing",
     test_case7_rollups_rescue_nothing),
    ("314-case8-empty-cells", test_case8_empty_cells),
    ("314-accepted-unchanged", test_accepted_unchanged),
    ("314-cell-report-shape", test_cell_report_shape),
    ("322-f1-omitted-ledger-blocks", test_322_f1_omitted_ledger_blocks),
    ("322-f1-candidate-omitted-ledger-blocks",
     test_322_f1_candidate_omitted_ledger_blocks),
    ("322-f1-required-cells-unverified",
     test_322_f1_required_cells_unverified),
    ("322-f2-oversize-distinct-ids", test_322_f2_oversize_distinct_ids),
    ("322-f2-identical-candidates-distinct-ids",
     test_322_f2_identical_candidates_distinct_ids),
    ("322-f3-per-cell-blocked-on-collection-failure",
     test_322_f3_per_cell_blocked_on_collection_failure),
    ("322-f4-cross-document-pairing-refused",
     test_322_f4_cross_document_pairing_refused),
    ("322-f5-kind-mismatch-refused", test_322_f5_kind_mismatch_refused),
    ("322-f5-collection-entry-not-decision-closed",
     test_322_f5_collection_entry_not_decision_closed),
    ("322-f6-negative-counts-raise", test_322_f6_negative_counts_raise),
    ("322-f7-bogus-accepted-raises", test_322_f7_bogus_accepted_raises),
    ("322-f8-report-candidates-from-ledger",
     test_322_f8_report_candidates_from_ledger),
]


def main():
    failed = 0
    for name, fn in CASES:
        try:
            ok, detail = fn()
        except Exception as e:  # a crashing case is a failed case
            ok, detail = False, "raised %r" % (e,)
        print("%s: %s — %s" % ("PASS" if ok else "FAIL", name, detail))
        failed += 0 if ok else 1
    print("%d/%d passed" % (len(CASES) - failed, len(CASES)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
