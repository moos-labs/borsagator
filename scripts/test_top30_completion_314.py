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
