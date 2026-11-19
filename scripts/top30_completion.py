#!/usr/bin/env python3
"""Evaluation completion gate for the #283 top-30 evaluation (issue #314).

Implements docs/top30-scoring.md §7/§8 as Ins's INS-314 design rules it:
`accepted` (in scripts/top30_scorer.py) is a per-cell THRESHOLD result
only — True/False/None, provisional before completion, never final
acceptance — and this module adds SEPARATE completion state on top of
the UNCHANGED scorer:

- ``complete``: required enumeration/capture and gold/adjudication
  finished, no unresolved in-scope cases. Missing or unknown gate
  inputs fail closed (incomplete, never a pass).
- Final outcome: ``incomplete`` / ``complete-pass`` / ``complete-fail``
  / ``complete-N/A``. A fully adjudicated evaluation can be complete
  even when quality fails (complete-fail). An entirely N/A evaluation
  must not become a vacuous quality pass (complete-N/A).

The unresolved ledger is built from matching records PLUS unresolved
candidate/source-gold decisions, relevant field uncertainty, and
collection/enumeration failures — NOT just ``ambiguous == []`` (a
candidate sits in ``unmatched_predicted``, invisible to an
ambiguity-only gate). Ledger entries get stable IDs tied to the frozen
run/input digests — never array position or a gold-ID list.

Scope/adjudication rules (INS-314 3/4):
- Partial collection names missing documents and blocks completion;
  event FNs are never invented for a missing document whose gold
  events are unknown (collection and event denominators differ).
- Out-of-scope ambiguity blocks only until an evidence-backed scope
  decision exists; the entry is retained with the exclusion reason.
  Scope is the frozen roster + date/document/event rules +
  adjudications, not an arbitrary caller-supplied ``in_scope=False``.
- A resolved wrong field contributes its FP/FN and threshold failure
  (complete-fail), not perpetual incompleteness. An unresolved
  required gold/source-field interpretation blocks completion. A
  documented absent/N/A field follows the frozen N/A policy.
- Adjudication decisions are persisted with evidence, affected stable
  IDs, run/input revisions and superseded decisions. Count-changing
  decisions (pairing) are applied ONLY through the explicit
  adjudication adapter (:func:`apply_adjudication`) and a re-score;
  clearing the ledger without applying the decision is unsound. Frozen
  predictions are never edited into correct answers: a resolved
  candidate cannot gain a TP by status rewriting.

Pure stdlib, no I/O, no network. Fail closed throughout: unknown or
missing gate inputs mean incomplete; malformed inputs raise
ValueError (same convention as the scorer).
"""
import hashlib
import json

from fractions import Fraction

import top30_scorer as S

OUTCOMES = ("incomplete", "complete-pass", "complete-fail", "complete-N/A")
LEDGER_KINDS = ("ambiguity", "candidate", "collection", "field",
                "scope", "gold")
DECISION_KINDS = ("pairing", "reject_event", "duplicate", "scope",
                  "field")
# N/A policy: documented-absent fields are named per cell by the
# frozen policy the caller passes in (dict {(issuer, event_type):
# set(fields)}). No field is absent by default.
COLLECTION_KEYS = ("enumerated", "archived", "missing",
                   "enumeration_closed", "pagination_complete")


def _cell_key(cell):
    """Normalise a cell key to an (issuer, event_type) tuple."""
    if isinstance(cell, tuple) and len(cell) == 2:
        return (str(cell[0]), str(cell[1]))
    if isinstance(cell, str) and "|" in cell:
        issuer, etype = cell.split("|", 1)
        return (issuer, etype)
    raise ValueError("cell key must be (issuer, event_type) or "
                     "'ISSUER|TYPE': %r" % (cell,))


def _cell_label(cell):
    issuer, etype = _cell_key(cell)
    return "%s|%s" % (issuer, etype)


def stable_entry_id(run_digest, input_digest, kind, cell, doc,
                    detail_key):
    """Stable ledger-entry ID tied to the frozen run/input digests.

    The ID is a sha256 over the digests + kind + cell + document +
    a canonical detail key (e.g. the predicted event's canonical
    field values + tied gold IDs) — never array position, never a
    bare gold-ID list, so repeated identical predictions stay
    distinguishable where multiplicity matters.
    """
    payload = {"run": run_digest, "input": input_digest, "kind": kind,
               "cell": list(_cell_key(cell)) if cell is not None else None,
               "doc": doc, "detail": detail_key}
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False,
                      default=repr)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:32]


def _canonical_event_key(ev):
    """Deterministic identity for one event: canonical (field, value)
    pairs + document/type/issuer + statuses. Used only to identify
    which ledger/adjudication record an event is, never as a score."""
    fields = ev.get("fields") or {}
    etype = ev.get("event_type")
    scored = S.SCORED_FIELDS.get(etype, ())
    return tuple(sorted(
        (f, repr(S._norm(f, fields.get(f)))) for f in scored))


def build_ledger(cell_results, *, run_digest, input_digest,
                 collection=None, extra_entries=()):
    """Build the unresolved ledger from scorer results + inputs.

    ``cell_results`` maps cell key -> ``score_cell`` result. Every
    ``ambiguous`` entry becomes a kind=``ambiguity`` entry (including
    ``oversize_group`` and sometimes-unmatched records, even with a
    single tied gold ID); every unmatched predicted event that is a
    candidate (``extraction_status == "candidate"`` or
    ``verification_status != "verified"``) becomes a
    kind=``candidate`` entry. Collection gaps (``missing`` documents)
    become kind=``collection`` entries. ``extra_entries`` are
    caller-supplied records (field uncertainty, scope, gold/source
    decisions) — each must already carry a stable ``id``, a ``kind``
    and a ``scope``; malformed entries raise ValueError.
    """
    if not run_digest or not input_digest:
        raise ValueError("run_digest and input_digest are required")
    ledger = []
    for cell, result in (cell_results or {}).items():
        key = _cell_key(cell)
        if not isinstance(result, dict) or "ambiguous" not in result:
            raise ValueError("not a score_cell result for cell %s" % (key,))
        for entry in result["ambiguous"]:
            pred = entry.get("predicted") or {}
            detail = {"predicted": _canonical_event_key(pred),
                      "tied_gold_ids": list(entry.get("tied_gold_ids") or []),
                      "oversize_group": bool(entry.get("oversize_group")),
                      "unmatched_in_an_optimum": bool(
                          entry.get("unmatched_in_an_optimum"))}
            ledger.append({
                "id": stable_entry_id(
                    run_digest, input_digest, "ambiguity", key,
                    entry.get("source_document_id"), detail),
                "kind": "ambiguity", "cell": key,
                "source_document_id": entry.get("source_document_id"),
                "event_type": entry.get("event_type"),
                "issuer": entry.get("issuer"),
                "scope": "in_scope", "detail": detail})
        for pred in result.get("unmatched_predicted") or []:
            if pred.get("extraction_status") == "candidate" \
                    or pred.get("verification_status") != "verified":
                detail = {"predicted": _canonical_event_key(pred),
                          "extraction_status": pred.get("extraction_status"),
                          "verification_status": pred.get(
                              "verification_status")}
                ledger.append({
                    "id": stable_entry_id(
                        run_digest, input_digest, "candidate", key,
                        pred.get("source_document_id"), detail),
                    "kind": "candidate", "cell": key,
                    "source_document_id": pred.get("source_document_id"),
                    "event_type": pred.get("event_type"),
                    "issuer": pred.get("issuer"),
                    "scope": "in_scope", "detail": detail})
    if collection is not None:
        missing = collection.get("missing")
        if missing is not None:
            if not isinstance(missing, (list, tuple)):
                raise ValueError("collection missing must be a list")
            for doc in missing:
                ledger.append({
                    "id": stable_entry_id(
                        run_digest, input_digest, "collection", None,
                        doc, {"document": doc}),
                    "kind": "collection", "cell": None,
                    "source_document_id": doc, "event_type": None,
                    "issuer": None, "scope": "in_scope",
                    "detail": {"document": doc}})
    for entry in extra_entries or []:
        if not isinstance(entry, dict):
            raise ValueError("ledger entry is not a dict: %r" % (entry,))
        if not entry.get("id") or not isinstance(entry.get("id"), str):
            raise ValueError(
                "ledger entry needs a stable string id: %r" % (entry,))
        if entry.get("kind") not in LEDGER_KINDS:
            raise ValueError("unknown ledger kind: %r" % (entry,))
        if entry.get("scope") not in ("in_scope", "out_of_scope",
                                      "unknown"):
            raise ValueError("unknown ledger scope: %r" % (entry,))
        copied = dict(entry)
        if copied.get("cell") is not None:
            copied["cell"] = _cell_key(copied["cell"])
        ledger.append(copied)
    return ledger


def _validate_decisions(decisions, run_digest, input_digest):
    """Validate adjudication decisions; fail closed.

    Returns {"valid", "invalid", "superseded", "conflicts"} where
    valid maps decision id -> decision, invalid maps id -> reason,
    superseded is the set of ids replaced by a valid decision, and
    conflicts maps ledger-entry id -> the conflicting decision ids.
    Malformed decisions (missing id/kind/entry_ids/evidence, unknown
    kind) raise ValueError. A decision is invalid when its digests do
    not match the frozen run/input (stale / wrong run), when it
    supersedes an unknown decision or participates in a supersession
    cycle (unresolved supersession), or when it conflicts with
    another live decision over the same entry.
    """
    by_id = {}
    for d in decisions or []:
        if not isinstance(d, dict):
            raise ValueError("decision is not a dict: %r" % (d,))
        if not d.get("id") or not isinstance(d.get("id"), str):
            raise ValueError("decision needs a string id: %r" % (d,))
        if d["id"] in by_id:
            raise ValueError("duplicate decision id: %r" % (d["id"],))
        if d.get("kind") not in DECISION_KINDS:
            raise ValueError("unknown decision kind: %r" % (d,))
        if not d.get("entry_ids") \
                or not isinstance(d.get("entry_ids"), (list, tuple)) \
                or not all(isinstance(e, str) for e in d["entry_ids"]):
            raise ValueError(
                "decision %s needs a non-empty entry_ids list" % d["id"])
        if not d.get("evidence") or not isinstance(d.get("evidence"), str):
            raise ValueError(
                "decision %s needs non-empty evidence" % d["id"])
        if d.get("kind") == "pairing" and not isinstance(
                d.get("pairing"), dict):
            raise ValueError(
                "pairing decision %s needs a pairing payload" % d["id"])
        by_id[d["id"]] = d
    valid, invalid = {}, {}
    for did, d in by_id.items():
        if d.get("run_digest") != run_digest \
                or d.get("input_digest") != input_digest:
            invalid[did] = ("stale/wrong-run decision: digests do not "
                            "match the frozen run/input")
            continue
        supersedes = d.get("supersedes") or []
        if not isinstance(supersedes, (list, tuple)) \
                or not all(isinstance(s, str) for s in supersedes):
            invalid[did] = "supersedes must be a list of decision ids"
            continue
        if any(s not in by_id for s in supersedes):
            invalid[did] = ("unresolved supersession: supersedes "
                            "unknown decision %r"
                            % ([s for s in supersedes if s not in by_id],))
            continue
        valid[did] = d
    # Supersession cycles among otherwise-valid decisions fail closed.
    graph = {did: [s for s in (d.get("supersedes") or [])
                   if s in valid]
             for did, d in valid.items()}
    cyclic = set()
    for start in graph:
        seen, stack = set(), [start]
        while stack:
            node = stack.pop()
            if node in seen:
                continue
            seen.add(node)
            for nxt in graph.get(node, []):
                if nxt == start:
                    cyclic.add(start)
                stack.append(nxt)
    for did in cyclic:
        invalid[did] = ("unresolved supersession: supersession cycle "
                        "involving %s" % did)
        del valid[did]
    superseded = set()
    for did, d in valid.items():
        for s in (d.get("supersedes") or []):
            if s in valid:
                superseded.add(s)
    live = {did: d for did, d in valid.items() if did not in superseded}
    # Conflicts: two live decisions over the same entry with a
    # different kind, or different pairing targets, disagree.
    conflicts = {}
    by_entry = {}
    for did, d in live.items():
        for eid in d["entry_ids"]:
            by_entry.setdefault(eid, []).append(d)
    for eid, ds in by_entry.items():
        kinds = {d["kind"] for d in ds}
        targets = set()
        for d in ds:
            if d["kind"] == "pairing":
                p = d.get("pairing") or {}
                targets.add(repr((p.get("predicted_event"),
                                  p.get("gold_event"))))
        if len(kinds) > 1 or len(targets) > 1:
            conflicts[eid] = [d["id"] for d in ds]
    for eid, dids in conflicts.items():
        for did in dids:
            invalid[did] = ("conflicting decisions over entry %s: %s"
                            % (eid, dids))
            del live[did]
    return {"valid": live, "invalid": invalid, "superseded": superseded,
            "conflicts": conflicts}


def _add_counts(dst, src, sign):
    for f, c in src.items():
        d = dst.setdefault(f, {"tp": 0, "fp": 0, "fn": 0})
        d["tp"] += sign * c["tp"]
        d["fp"] += sign * c["fp"]
        d["fn"] += sign * c["fn"]


def _recompute_verdict(result):
    """Recompute precision/recall/field verdicts/accepted for an
    adapter-adjusted cell result, using the scorer's own rules."""
    tp, fp, fn = result["tp"], result["fp"], result["fn"]
    precision = Fraction(tp, tp + fp) if tp + fp else None
    recall = Fraction(tp, tp + fn) if tp + fn else None
    field_verdicts = {f: S._field_verdict(c)
                      for f, c in result["field_score"].items()}
    if precision is None and recall is None:
        accepted = None
    else:
        event_ok = ((precision is None or precision >= S.PRECISION_MIN)
                    and (recall is None or recall >= S.RECALL_MIN))
        fields_ok = all(v is not False for v in field_verdicts.values())
        accepted = event_ok and fields_ok
    result["precision"] = precision
    result["recall"] = recall
    result["field_verdicts"] = field_verdicts
    result["accepted"] = accepted
    return result


def apply_adjudication(cell_result, decisions, *, run_digest,
                       input_digest):
    """Apply count-changing (pairing) adjudications and re-score.

    Takes one ``score_cell`` result plus pairing decisions and
    returns a NEW cell result in which each adjudicated pair is
    matched (TP with its field errors scored), with ``matches``,
    ``unmatched_*`` and ``ambiguous`` updated and the verdict
    recomputed by the scorer's own rules. The returned result carries
    ``adjudication_applied`` (decision ids) and the frozen digests,
    so the gate can verify the re-score belongs to this run/input.

    Refuses (ValueError) a pairing whose predicted event is a
    candidate — a resolved candidate cannot gain a TP by status
    rewriting — whose events are not both currently unmatched, or
    whose pair has zero field agreement (not identifiable). The
    original result and the frozen input events are never mutated;
    decisions that do not change counts (scope / field / reject /
    duplicate) need no re-score and are not applied here.
    """
    check = _validate_decisions(decisions, run_digest, input_digest)
    pairing = [d for d in check["valid"].values()
               if d["kind"] == "pairing"]
    if check["invalid"]:
        raise ValueError("cannot apply adjudication: invalid decisions: "
                         "%r" % (check["invalid"],))
    if check["conflicts"]:
        raise ValueError("cannot apply adjudication: conflicting "
                         "decisions: %r" % (check["conflicts"],))
    result = dict(cell_result)
    result["field_score"] = {f: dict(c) for f, c in
                             cell_result["field_score"].items()}
    result["matches"] = list(cell_result.get("matches") or [])
    result["unmatched_gold"] = list(cell_result.get("unmatched_gold") or [])
    result["unmatched_predicted"] = list(
        cell_result.get("unmatched_predicted") or [])
    result["ambiguous"] = list(cell_result.get("ambiguous") or [])
    applied = []
    for d in pairing:
        p = (d.get("pairing") or {}).get("predicted_event")
        g = (d.get("pairing") or {}).get("gold_event")
        if p is None or g is None:
            raise ValueError("pairing decision %s needs predicted_event "
                             "and gold_event" % d["id"])
        if p.get("extraction_status") == "candidate" \
                or p.get("verification_status") != "verified":
            raise ValueError(
                "pairing decision %s cannot grant a TP to a candidate "
                "predicted event (status rewriting)" % d["id"])
        if p not in result["unmatched_predicted"]:
            raise ValueError(
                "pairing decision %s: predicted event is not unmatched "
                "in this cell result" % d["id"])
        if g not in result["unmatched_gold"]:
            raise ValueError(
                "pairing decision %s: gold event is not unmatched in "
                "this cell result" % d["id"])
        fields = S.SCORED_FIELDS.get(p.get("event_type"), ())
        if S._agreement(g, p, fields) < 1:
            raise ValueError(
                "pairing decision %s: pair has zero agreement, not "
                "identifiable" % d["id"])
        _add_counts(result["field_score"],
                    S._field_counts(g.get("fields"), None, fields), -1)
        _add_counts(result["field_score"],
                    S._field_counts(None, p.get("fields"), fields), -1)
        _add_counts(result["field_score"],
                    S._field_counts(g.get("fields"), p.get("fields"),
                                    fields), +1)
        result["unmatched_predicted"].remove(p)
        result["unmatched_gold"].remove(g)
        result["matches"].append({"gold": g, "predicted": p})
        result["ambiguous"] = [a for a in result["ambiguous"]
                               if a.get("predicted") != p]
        result["tp"] += 1
        result["fp"] -= 1
        result["fn"] -= 1
        applied.append(d["id"])
    _recompute_verdict(result)
    result["adjudication_applied"] = applied
    result["run_digest"] = run_digest
    result["input_digest"] = input_digest
    return result


def _validate_collection(collection):
    """Return (ok, reasons) for a collection state, or None + reasons
    when the state is unknown. Wrong types raise ValueError."""
    if collection is None:
        return None, ["collection state unknown (not supplied)"]
    for key in COLLECTION_KEYS:
        if collection.get(key) is None:
            return None, ["collection state unknown: %s not supplied"
                          % key]
    enumerated, archived = collection["enumerated"], collection["archived"]
    missing = collection["missing"]
    if not isinstance(enumerated, int) or isinstance(enumerated, bool) \
            or not isinstance(archived, int) \
            or isinstance(archived, bool):
        raise ValueError("collection enumerated/archived must be ints")
    if not isinstance(missing, (list, tuple)) \
            or not all(isinstance(m, str) for m in missing):
        raise ValueError("collection missing must be a list of strings")
    if not isinstance(collection["enumeration_closed"], bool) \
            or not isinstance(collection["pagination_complete"], bool):
        raise ValueError(
            "collection enumeration_closed/pagination_complete must "
            "be booleans")
    reasons = []
    if not collection["enumeration_closed"]:
        reasons.append("enumeration not closed: the archived/enumerated "
                       "ratio alone cannot prove completeness")
    if not collection["pagination_complete"]:
        reasons.append("pagination unfinished")
    if archived != enumerated:
        reasons.append("collection incomplete: archived %d of "
                       "enumerated %d" % (archived, enumerated))
    if missing:
        reasons.append("collection incomplete: missing documents: %s"
                       % (", ".join(sorted(missing)),))
    return (not reasons), reasons


def evaluate_completion(cell_results, *, run_digest, input_digest,
                        collection=None, ledger=(), decisions=(),
                        required_cells=(), na_policy=None,
                        adjudicated=None):
    """Evaluate completion for a whole evaluation run.

    ``cell_results`` maps cell key -> ``score_cell`` result;
    ``adjudicated`` optionally maps cell key -> an
    :func:`apply_adjudication` result for that cell (its digests and
    ``adjudication_applied`` ids are verified). ``na_policy`` maps
    cell key -> set of fields documented absent under the frozen N/A
    policy. Returns ``{"complete", "outcome", "reasons", "unresolved",
    "excluded", "documented_absent", "per_cell"}``. ``complete`` is
    True only when collection is complete, every required cell is
    present, and the unresolved ledger is empty after valid
    adjudications. The outcome is ``incomplete`` while anything
    blocks; once complete it is ``complete-pass`` (every assessable
    cell accepted), ``complete-fail`` (any cell failed) or
    ``complete-N/A`` (every cell N/A — never a quality pass).
    """
    if not run_digest or not input_digest:
        raise ValueError("run_digest and input_digest are required")
    na_policy = na_policy or {}
    reasons, unresolved, excluded, documented = [], [], [], []
    per_cell = {}
    effective = {}
    for cell, result in (cell_results or {}).items():
        key = _cell_key(cell)
        if not isinstance(result, dict) or "accepted" not in result:
            raise ValueError("not a score_cell result for cell %s" % (key,))
        effective[key] = result
    for cell, result in (adjudicated or {}).items():
        key = _cell_key(cell)
        if not isinstance(result, dict) \
                or "adjudication_applied" not in result:
            raise ValueError(
                "adjudicated result for cell %s was not produced by "
                "apply_adjudication" % (key,))
        if result.get("run_digest") != run_digest \
                or result.get("input_digest") != input_digest:
            raise ValueError(
                "adjudicated result for cell %s is stale/wrong-run"
                % (key,))
        effective[key] = result
    # 1. Collection.
    coll_ok, coll_reasons = _validate_collection(collection)
    if coll_ok is not True:
        reasons.extend(coll_reasons)
    # 2. Required cells present.
    for cell in required_cells or []:
        key = _cell_key(cell)
        if key not in effective:
            reasons.append("required cell %s omitted" % _cell_label(key))
    # 3. Ledger, resolved through validated decisions.
    check = _validate_decisions(decisions, run_digest, input_digest)
    covering = {}
    for did, d in check["valid"].items():
        for eid in d["entry_ids"]:
            covering.setdefault(eid, []).append(d)
    for entry in ledger or []:
        if not isinstance(entry, dict) or not entry.get("id") \
                or entry.get("kind") not in LEDGER_KINDS:
            raise ValueError("malformed ledger entry: %r" % (entry,))
        eid = entry["id"]
        scope = entry.get("scope")
        if scope not in ("in_scope", "out_of_scope", "unknown"):
            raise ValueError("unknown ledger scope: %r" % (entry,))
        cell = entry.get("cell")
        key = _cell_key(cell) if cell is not None else None
        # A collection entry is closed when the collection state
        # itself shows its document archived (not in missing).
        if entry["kind"] == "collection" and coll_ok is True \
                and collection is not None \
                and entry.get("source_document_id") \
                not in (collection.get("missing") or []):
            continue
        if scope == "unknown":
            reasons.append("entry %s has unknown scope" % eid)
            unresolved.append(entry)
            continue
        live = covering.get(eid, [])
        if entry["kind"] == "field" and entry.get("na_documented"):
            field = entry.get("field")
            policy = {f for f in (na_policy.get(key) or set())}
            if field is not None and field in policy and live and any(
                    d["kind"] == "field" for d in live):
                documented.append(entry)
                continue
            reasons.append(
                "field entry %s (%s) is not covered by the frozen "
                "N/A policy" % (eid, field))
            unresolved.append(entry)
            continue
        if scope == "out_of_scope":
            if live and any(d["kind"] == "scope" for d in live):
                excluded.append(entry)
                continue
            reasons.append(
                "entry %s claims out-of-scope without an "
                "evidence-backed scope decision" % eid)
            unresolved.append(entry)
            continue
        # In-scope: needs a live, valid decision; a pairing decision
        # additionally needs the re-scored result to have applied it.
        if not live:
            reasons.append("entry %s unresolved (no adjudication)" % eid)
            unresolved.append(entry)
            continue
        blocked = False
        for d in live:
            if d["kind"] == "pairing":
                adj = effective.get(key) if key is not None else None
                applied = (adj or {}).get("adjudication_applied") or []
                if d["id"] not in applied:
                    reasons.append(
                        "entry %s: pairing decision %s merely marked "
                        "resolved, not applied and re-scored"
                        % (eid, d["id"]))
                    blocked = True
        if blocked:
            unresolved.append(entry)
            continue
    for did, why in check["invalid"].items():
        reasons.append("decision %s invalid: %s" % (did, why))
    for eid, dids in check["conflicts"].items():
        reasons.append("conflicting decisions over entry %s: %s"
                       % (eid, dids))
    complete = not reasons
    # Per-cell blocking (a blocked cell prevents completion; a
    # roll-up never rescues a failed, blocked or unproven cell).
    for key, result in effective.items():
        blocking = [e for e in unresolved
                    if e.get("cell") == key or e.get("cell") is None]
        per_cell[_cell_label(key)] = {
            "accepted": result.get("accepted"), "blocked": bool(blocking),
            "blocking": [e["id"] for e in blocking]}
    for cell in required_cells or []:
        label = _cell_label(cell)
        if label not in per_cell:
            per_cell[label] = {"accepted": None, "blocked": True,
                               "blocking": ["required cell omitted"]}
    if not complete:
        outcome = "incomplete"
    else:
        accepted = [r.get("accepted") for r in effective.values()]
        if not accepted or all(a is None for a in accepted):
            # No assessable cell at all (including an evaluation with
            # no cells): complete-N/A, never a vacuous quality pass.
            outcome = "complete-N/A"
        elif any(a is False for a in accepted):
            outcome = "complete-fail"
        else:
            outcome = "complete-pass"
    return {"complete": complete, "outcome": outcome,
            "reasons": reasons, "unresolved": unresolved,
            "excluded": excluded, "documented_absent": documented,
            "per_cell": per_cell}


def cell_report(cell_result, cell, *, run_digest, input_digest,
                collection=None, ledger=(), decisions=(),
                na_policy=None, adjudicated=None):
    """The §8 per-cell report: collection status, event/field counts,
    verified vs candidate counts, the unresolved ledger for this
    cell, and the separate completion state (``complete`` +
    ``outcome``) alongside the scorer's provisional ``accepted``."""
    key = _cell_key(cell)
    gate = evaluate_completion(
        {key: cell_result}, run_digest=run_digest,
        input_digest=input_digest, collection=collection, ledger=ledger,
        decisions=decisions, required_cells=[key], na_policy=na_policy,
        adjudicated=adjudicated)
    result = None
    if adjudicated:
        norm_adj = {_cell_key(k): v for k, v in adjudicated.items()}
        result = norm_adj.get(key)
    if result is None:
        result = cell_result
    verified = sum(1 for m in result.get("matches") or [])
    candidates = sum(
        1 for p in result.get("unmatched_predicted") or []
        if p.get("extraction_status") == "candidate"
        or p.get("verification_status") != "verified")
    return {"cell": _cell_label(key),
            "collection": collection,
            "tp": result["tp"], "fp": result["fp"], "fn": result["fn"],
            "precision": result["precision"], "recall": result["recall"],
            "field_score": result["field_score"],
            "field_verdicts": result["field_verdicts"],
            "accepted": result["accepted"],
            "verified_matches": verified,
            "unresolved_candidates": candidates,
            "unresolved_ledger": gate["unresolved"],
            "excluded": gate["excluded"],
            "complete": gate["complete"], "outcome": gate["outcome"],
            "reasons": gate["reasons"]}
