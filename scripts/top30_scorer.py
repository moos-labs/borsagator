#!/usr/bin/env python3
"""Reference scorer for the #283 top-30 evaluation.

Implements docs/top30-scoring.md exactly. Pure stdlib, no I/O, no
network. The spec wins over this module: if they ever disagree, the
spec is right and this file is fixed.

Event shape (gold and predicted share the shape; gold never carries a
verification/extraction status — those are predictions only)::

    {"source_document_id": "egx:296893",
     "event_type": "dividend", "issuer": "POUL",
     "gold_id": "g1",            # gold only: independently assigned
                                 # within-document identity. A predicted
                                 # event's gold_id, if present, is IGNORED.
     "extraction_status": "extracted",      # predicted only
     "verification_status": "verified",     # predicted only
     "fields": {"coupon": "42", "amount_per_share": "1.9",
                "ex_date": "2026-11-16", ...}}

Rules (spec sections in brackets):
- Match within same source document id AND same event type only [§4.1].
- One-to-one pairing; a gold event is used at most once. A duplicate
  predicted event reusing an already-matched gold event is an FP [§4.2].
- A candidate predicted event never grants a TP, even with identical
  fields: it is an FP and its gold counterpart an FN [§3, §4].
- Ambiguous tie (two or more free gold events share the best agreement
  for one predicted event): leave the predicted event unmatched (FP),
  flag the group ambiguous for adjudication, never break the tie
  favourably [§4.4].
- Wrong predicted value = 1 FP + 1 FN; missing gold field = FN;
  unsupported extra = FP [§6]. Field denominators are end-to-end:
  unmatched gold events contribute an FN per present field, unmatched
  predicted events an FP per present field.
- Acceptance uses exact fractions: P >= 95%, R >= 90% per cell; no
  rounding a failure into a pass; zero denominators are N/A [§7].
"""
from decimal import Decimal, InvalidOperation
from fractions import Fraction

SCORED_FIELDS = {
    "dividend": ("coupon", "amount_per_share", "ex_date",
                 "entitlement_end", "payout_date", "record_date",
                 "announced"),
    "earnings": ("period_start", "period_end", "npat", "npat_scale",
                 "npat_comparative", "yoy_npat_pct", "revenue",
                 "announced"),
    "board-decision": ("meeting_date", "assembly_date",
                       "assembly_time", "subtype", "state", "announced"),
}

# A derived record_date candidate is NEVER a scored value (spec §6):
# the extractor's UNVALIDATED derived candidate must not be passed in
# as fields["record_date"]; it lives outside "fields".
PRECISION_MIN = Fraction(95, 100)
RECALL_MIN = Fraction(90, 100)


def _norm(field, value):
    """Normalise one field value before comparison (spec §6).

    Dates to ISO YYYY-MM-DD (accepts ISO and D/M/YYYY); amounts as
    Decimal strings (sign preserved — +100 never equals -100);
    everything else compared as a stripped string. None stays None.
    """
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    if field in ("ex_date", "entitlement_end", "payout_date",
                 "record_date", "announced", "period_start",
                 "period_end", "meeting_date", "assembly_date"):
        if "/" in s:
            d, m, y = s.split("/")
            return "%s-%s-%s" % (y, m.zfill(2), d.zfill(2))
        return s
    if field in ("amount_per_share", "npat", "npat_comparative",
                 "yoy_npat_pct", "revenue"):
        try:
            return Decimal(s)
        except InvalidOperation:
            return s
    return s


def _is_verified_event(ev):
    """Candidate status never grants a TP (spec §3)."""
    return (ev.get("extraction_status", "extracted") != "candidate"
            and ev.get("verification_status", "verified") == "verified")


def _agreement(gold, pred, fields):
    """Count of scored fields equal after normalisation."""
    gf, pf = gold.get("fields") or {}, pred.get("fields") or {}
    return sum(1 for f in fields
               if f in gf and f in pf
               and _norm(f, gf[f]) == _norm(f, pf[f])
               and _norm(f, gf[f]) is not None)


def _field_counts(gold_fields, pred_fields, fields):
    """TP/FP/FN per field for one gold/predicted pair (spec §6).

    `gold_fields`/`pred_fields` may be None (unmatched side): a present
    gold field with no predicted counterpart is an FN; a present
    predicted field with no gold counterpart is an FP.
    """
    out = {}
    for f in fields:
        g = _norm(f, (gold_fields or {}).get(f))
        p = _norm(f, (pred_fields or {}).get(f))
        if g is None and p is None:
            out[f] = {"tp": 0, "fp": 0, "fn": 0}
        elif g is not None and g == p:
            out[f] = {"tp": 1, "fp": 0, "fn": 0}
        elif g is not None and p is not None:
            out[f] = {"tp": 0, "fp": 1, "fn": 1}  # wrong value
        elif g is not None:
            out[f] = {"tp": 0, "fp": 0, "fn": 1}  # missing
        else:
            out[f] = {"tp": 0, "fp": 1, "fn": 0}  # unsupported extra
    return out


def _merge_field_counts(dst, src):
    for f, c in src.items():
        d = dst.setdefault(f, {"tp": 0, "fp": 0, "fn": 0})
        d["tp"] += c["tp"]
        d["fp"] += c["fp"]
        d["fn"] += c["fn"]


def score_cell(gold_events, predicted_events):
    """Score one cell (one issuer x one event type).

    Returns {"tp","fp","fn","field_score","matches","unmatched_gold",
    "unmatched_predicted","ambiguous","precision","recall","accepted"}.
    "accepted" is True/False when assessable, None when a denominator
    is zero (N/A — spec §7).
    """
    gold = list(gold_events or [])
    pred = list(predicted_events or [])
    fields = set()
    for ev in gold + pred:
        fields |= set(SCORED_FIELDS.get(ev.get("event_type"), ()))
    fields = sorted(fields)
    tp = fp = fn = 0
    field_score = {}
    matches, ambiguous = [], []
    unmatched_pred, unmatched_gold = [], []

    # Candidates never match: they are unmatched emitted events (FP).
    # Identity-based partition: two equal dicts must not collapse.
    verifiable, candidate_pred = [], []
    for p in pred:
        (verifiable if _is_verified_event(p) else candidate_pred).append(p)
    for p in candidate_pred:
        unmatched_pred.append(p)
        fp += 1

    # Group by (source document, event type); match one-to-one inside.
    groups = {}
    for ev in gold:
        groups.setdefault((ev.get("source_document_id"),
                           ev.get("event_type")), {"gold": [], "pred": []})
    for ev in verifiable:
        groups.setdefault((ev.get("source_document_id"),
                           ev.get("event_type")), {"gold": [], "pred": []})
    for ev in gold:
        groups[(ev.get("source_document_id"),
                ev.get("event_type"))]["gold"].append(ev)
    for ev in verifiable:
        groups[(ev.get("source_document_id"),
                ev.get("event_type"))]["pred"].append(ev)

    for (doc, etype), grp in sorted(groups.items(), key=lambda kv: str(kv[0])):
        free_gold = list(grp["gold"])
        for p in grp["pred"]:
            # Best agreement among still-free gold events.
            scored = sorted(
                (( _agreement(g, p, SCORED_FIELDS.get(etype, ())), i, g)
                 for i, g in enumerate(free_gold)),
                key=lambda t: (-t[0], t[1]))
            if not scored:
                unmatched_pred.append(p)
                fp += 1
                continue
            best = scored[0][0]
            tied = [s for s in scored if s[0] == best]
            if len(tied) > 1:
                # Ambiguous: no favourable automatic match (spec §4.4).
                unmatched_pred.append(p)
                fp += 1
                ambiguous.append({
                    "source_document_id": doc, "event_type": etype,
                    "predicted": p, "tied_gold_ids": [
                        g.get("gold_id") for _, _, g in tied]})
                continue
            g = scored[0][2]
            free_gold.remove(g)
            tp += 1
            matches.append({"gold": g, "predicted": p})
            _merge_field_counts(
                field_score,
                _field_counts(g.get("fields"), p.get("fields"),
                              SCORED_FIELDS.get(etype, ())))
        for g in free_gold:
            unmatched_gold.append(g)
            fn += 1
            _merge_field_counts(
                field_score,
                _field_counts(g.get("fields"), None,
                              SCORED_FIELDS.get(etype, ())))
    for p in unmatched_pred:
        _merge_field_counts(
            field_score,
            _field_counts(None, p.get("fields"),
                          SCORED_FIELDS.get(p.get("event_type"), ())))
    # Field rows for fields never touched stay zeroed but present.
    for f in fields:
        field_score.setdefault(f, {"tp": 0, "fp": 0, "fn": 0})

    precision = (Fraction(tp, tp + fp) if tp + fp else None)
    recall = (Fraction(tp, tp + fn) if tp + fn else None)
    if precision is None and recall is None:
        accepted = None  # fully empty cell (0/0/0): N/A, never a pass
        # and never a fail (spec §7). A cell where one side is N/A
        # but the other is assessable is judged on the assessable
        # side: e.g. TP=0, FP=0, FN=1 fails on recall (R = 0/1).
    else:
        accepted = ((precision is None or precision >= PRECISION_MIN)
                    and (recall is None or recall >= RECALL_MIN))
    return {"tp": tp, "fp": fp, "fn": fn, "field_score": field_score,
            "matches": matches, "unmatched_gold": unmatched_gold,
            "unmatched_predicted": unmatched_pred,
            "ambiguous": ambiguous, "precision": precision,
            "recall": recall, "accepted": accepted}


def acceptance(tp, fp, fn):
    """Exact-fraction acceptance for raw counts (spec §7).

    Returns {"precision","recall","assessable","passed"}; "passed" is
    None when a denominator is zero (N/A).
    """
    precision = Fraction(tp, tp + fp) if tp + fp else None
    recall = Fraction(tp, tp + fn) if tp + fn else None
    assessable = precision is not None or recall is not None
    if not assessable:
        passed = None  # fully empty (0/0/0): N/A
    else:
        passed = ((precision is None or precision >= PRECISION_MIN)
                  and (recall is None or recall >= RECALL_MIN))
    return {"precision": precision, "recall": recall,
            "assessable": assessable, "passed": passed}


def format_pr(value):
    """Display a Fraction or None (N/A) — never rounded into a pass."""
    if value is None:
        return "N/A"
    return "%.4f (%d/%d)" % (float(value), value.numerator,
                             value.denominator)
