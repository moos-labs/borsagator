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

Issue #322 (INS-314-POSTMERGE-REVIEW) hardened the gate further:
- The mandatory ambiguity/candidate/collection ledger is DERIVED
  inside :func:`evaluate_completion` from the scorer outputs and
  the collection state; a caller-supplied ledger that omits any
  derived entry (omitted, empty or truncated) never passes while
  such cases exist. A frozen required-cell set is required whenever
  cells are present — without it, omitted universe members are
  undetectable.
- Ledger IDs are distinct per frozen prediction OCCURRENCE: N
  identical predictions yield N distinct IDs, so one decision over
  one ID can never clear N entries.
- Pairing adjudications require the same source document, issuer
  and event type on both sides (the frozen same-document rule).
- A decision resolves only a ledger entry of a compatible kind
  (see ``DECISION_ENTRY_COMPAT``); collection entries are closed
  only by collection evidence, never by a decision.
- Collection counts must be non-negative; a cell's ``accepted``
  must be exactly True/False/None (by identity).
- ``per_cell.blocked`` reflects global collection failures, not
  only unresolved ledger entries; ``cell_report`` derives
  ``unresolved_candidates`` from the effective ledger and keeps the
  raw candidate-output count separately as ``candidate_outputs``.

Issue #327 (INS-322-POSTMERGE-REVIEW follow-up) hardened the gate
further:
- The mandatory ledger is derived from the ORIGINAL (pre-
  adjudication) scorer results, so original-case coverage survives
  any overlay: a case can leave the denominator only through a live,
  compatible adjudication decision, never by a re-scored result
  dropping it. A caller-supplied entry reusing a derived ID must
  match the derived record on kind/cell/document/event-type/issuer/
  detail — the internally derived content is authoritative; only the
  decision-backed in_scope -> out_of_scope transition may differ.
- An adjudicated overlay is verified by recomputation: its applied
  decision IDs must reconcile with the live pairing decisions for
  the cell in both directions (no ghost IDs, no unapplied live
  decision), and the overlay must equal the re-score of the original
  result under exactly those decisions (counts, matches, unmatched
  lists, ambiguities, verdicts). A hand-stamped overlay with ghost
  adjudication IDs, dropped cases or altered counts cannot pass.
- Exactly one scope policy: an out-of-scope case is excluded by
  marking its own original ledger entry out_of_scope together with
  an evidence-backed scope decision over that entry; the entry is
  retained in ``excluded``. A separate kind=``scope`` entry never
  accounts for original ambiguity/candidate entries. Per-cell
  blocking derives from the authoritative (derived) record, so a
  relabelled supplied entry cannot move blocking to another cell.
- The pairing adapter revalidates nonempty identity (source
  document, issuer, event type) on both events, so a document-less
  pair cannot pass on ``None == None``.
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
# Permitted decision/entry-kind combinations (issue #322 finding 5).
# A decision resolves only a ledger entry whose kind it is listed
# under; a kind-mismatched decision leaves the entry unresolved.
# Collection entries are closed only by collection evidence (the
# document showing archived), never by any decision.
# Scope policy (issue #327 — exactly one): an out-of-scope case is
# excluded by marking its OWN original ledger entry out_of_scope
# together with an evidence-backed scope decision over that entry
# (see evaluate_completion: the out_of_scope branch); the entry is
# retained in ``excluded``. A separate kind="scope" entry records an
# out-of-scope case that has no ambiguity/candidate entry of its own
# (e.g. a document outside the frozen window) and never accounts for
# original ambiguity/candidate entries — a scope entry plus a scope
# decision leaves the original entries unresolved.
DECISION_ENTRY_COMPAT = {
    "ambiguity": ("pairing", "reject_event", "duplicate"),
    "candidate": ("reject_event", "duplicate"),
    "field": ("field",),
    "scope": ("scope",),
    "gold": ("field", "scope"),
    "collection": (),
}
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
    bare gold-ID list. Identical predictions still need an occurrence
    discriminator to stay distinct (see :func:`_distinct_entry_id`);
    this function alone does NOT distinguish them.
    """
    payload = {"run": run_digest, "input": input_digest, "kind": kind,
               "cell": list(_cell_key(cell)) if cell is not None else None,
               "doc": doc, "detail": detail_key}
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False,
                      default=repr)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:32]


def _distinct_entry_id(run_digest, input_digest, kind, cell, doc,
                       detail, seen):
    """Stable ID for one ledger entry, distinct per occurrence.

    ``seen`` counts prior entries with the same canonical base
    detail (same kind/cell/document/detail); the occurrence index
    (0-based among identical entries) is folded into the hashed
    detail and stored on the entry, so N identical predictions yield
    N distinct IDs (issue #322 finding 2: one decision over one ID
    can never clear N entries). Reordering identical entries leaves
    the ID multiset unchanged, because identical entries are
    interchangeable. Returns (id, detail-with-occurrence).
    """
    key = (kind, repr(_cell_key(cell)) if cell is not None else None,
           doc, json.dumps(detail, sort_keys=True, ensure_ascii=False,
                           default=repr))
    occurrence = seen.get(key, 0)
    seen[key] = occurrence + 1
    detail = dict(detail)
    detail["occurrence"] = occurrence
    return stable_entry_id(run_digest, input_digest, kind, cell, doc,
                           detail), detail


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
    seen = {}
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
            eid, detail = _distinct_entry_id(
                run_digest, input_digest, "ambiguity", key,
                entry.get("source_document_id"), detail, seen)
            ledger.append({
                "id": eid,
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
                eid, detail = _distinct_entry_id(
                    run_digest, input_digest, "candidate", key,
                    pred.get("source_document_id"), detail, seen)
                ledger.append({
                    "id": eid,
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
                eid, detail = _distinct_entry_id(
                    run_digest, input_digest, "collection", None,
                    doc, {"document": doc}, seen)
                ledger.append({
                    "id": eid,
                    "kind": "collection", "cell": None,
                    "source_document_id": doc, "event_type": None,
                    "issuer": None, "scope": "in_scope",
                    "detail": detail})
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


def _apply_pairings(cell_result, pairing_decisions):
    """Apply pairing decisions to a ``score_cell`` result.

    Shared core of :func:`apply_adjudication` and the gate's overlay
    verification in :func:`evaluate_completion`: both paths must
    compute exactly the same re-score from the same original result
    and the same decisions, so a hand-stamped overlay cannot differ
    from what the adapter produces. Assumes the decisions are
    already validated (live, same run/input); raises ValueError for
    any pair the adapter refuses. Returns (new_result, applied_ids);
    the envelope fields (``adjudication_applied``, digests) are the
    caller's job. The original result is never mutated.
    """
    result = dict(cell_result)
    result["field_score"] = {f: dict(c) for f, c in
                             cell_result["field_score"].items()}
    result["matches"] = list(cell_result.get("matches") or [])
    result["unmatched_gold"] = list(cell_result.get("unmatched_gold") or [])
    result["unmatched_predicted"] = list(
        cell_result.get("unmatched_predicted") or [])
    result["ambiguous"] = list(cell_result.get("ambiguous") or [])
    applied = []
    for d in pairing_decisions:
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
        # Nonempty identity (issue #327 finding 4): the adapter is a
        # standalone fail-closed boundary, so each event must carry a
        # real source document, issuer and event type. Without this,
        # ``None == None`` lets a document-less pair through the
        # same-document check below. The scorer itself refuses
        # document-less events, so scorer-produced inputs always
        # carry all three — this only bites hand-built pairs.
        for field in ("source_document_id", "issuer", "event_type"):
            if not p.get(field) or not g.get(field):
                raise ValueError(
                    "pairing decision %s: predicted and gold events "
                    "must both carry a nonempty %s (got %r vs %r)"
                    % (d["id"], field, p.get(field), g.get(field)))
        # Frozen same-document matching rule (issue #322 finding 4):
        # a pairing may only join events from the same source
        # document, issuer and event type. Membership in the
        # unmatched lists plus field agreement is not enough — a
        # cross-document pair would otherwise mint a TP across the
        # document boundary the scorer never crosses.
        if p.get("source_document_id") != g.get("source_document_id"):
            raise ValueError(
                "pairing decision %s: predicted and gold events are "
                "from different source documents (%r vs %r)"
                % (d["id"], p.get("source_document_id"),
                   g.get("source_document_id")))
        if p.get("issuer") != g.get("issuer"):
            raise ValueError(
                "pairing decision %s: predicted and gold events have "
                "different issuers (%r vs %r)"
                % (d["id"], p.get("issuer"), g.get("issuer")))
        if p.get("event_type") != g.get("event_type"):
            raise ValueError(
                "pairing decision %s: predicted and gold events have "
                "different event types (%r vs %r)"
                % (d["id"], p.get("event_type"), g.get("event_type")))
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
    return result, applied


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
    whose pair has zero field agreement (not identifiable), whose
    events come from different documents/issuers/types, or whose
    events lack a nonempty source document, issuer or event type
    (issue #327 finding 4: ``None == None`` must not pass the
    same-document check). The original result and the frozen input
    events are never mutated; decisions that do not change counts
    (scope / field / reject / duplicate) need no re-score and are
    not applied here.
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
    result, applied = _apply_pairings(cell_result, pairing)
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
    if enumerated < 0 or archived < 0:
        raise ValueError(
            "collection enumerated/archived must be non-negative: "
            "enumerated=%r archived=%r" % (enumerated, archived))
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


def _canonical_json(value):
    """Canonical JSON for content comparison: tuples and lists
    serialise identically, so a ledger entry that went through a
    JSON round-trip still matches the in-process derived record."""
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      default=repr)


def _derived_content_diffs(supplied, derived):
    """Diff a caller-supplied ledger entry against the internally
    derived record with the same ID (issue #327 finding 1).

    The derived kind/cell/document/event-type/issuer/detail are
    authoritative: any difference is tampering (e.g. re-kinding an
    ambiguity to ``field`` while keeping its ID), not a new case.
    Returns a list of human-readable differences (empty = match).
    ``scope`` is deliberately NOT compared here: the single
    decision-backed scope transition (in_scope -> out_of_scope) is
    judged by the resolution loop, which requires a live scope
    decision; any other scope value leaves the entry unresolved
    there.
    """
    diffs = []
    if supplied.get("kind") != derived.get("kind"):
        diffs.append("kind: supplied %r vs derived %r"
                     % (supplied.get("kind"), derived.get("kind")))
    sup_cell = supplied.get("cell")
    der_cell = derived.get("cell")
    if (sup_cell is None) != (der_cell is None):
        diffs.append("cell: supplied %r vs derived %r"
                     % (sup_cell, der_cell))
    elif sup_cell is not None and _cell_key(sup_cell) != _cell_key(der_cell):
        diffs.append("cell: supplied %r vs derived %r"
                     % (sup_cell, der_cell))
    for field in ("source_document_id", "event_type", "issuer"):
        if supplied.get(field) != derived.get(field):
            diffs.append("%s: supplied %r vs derived %r"
                         % (field, supplied.get(field),
                            derived.get(field)))
    if _canonical_json(supplied.get("detail")) != _canonical_json(
            derived.get("detail")):
        diffs.append("detail differs from the derived record")
    return diffs


def _canon_multiset(items):
    """Canonical multiset of JSON-able items (order-insensitive)."""
    return sorted(_canonical_json(x) for x in (items or []))


def _overlay_matches_recomputed(overlay, recomputed):
    """True when an adjudicated overlay equals the re-score of the
    original result under the live pairing decisions (issue #327
    finding 1/2). Compares every semantic field: counts, exact
    precision/recall/accepted, field scores and verdicts, matches
    and unmatched lists and ambiguities as multisets (pairing order
    is irrelevant), and the applied-decision set. Extra keys on the
    overlay are ignored — they carry no gate meaning."""
    if overlay.get("tp") != recomputed["tp"]:
        return False
    if overlay.get("fp") != recomputed["fp"]:
        return False
    if overlay.get("fn") != recomputed["fn"]:
        return False
    if overlay.get("precision") != recomputed["precision"]:
        return False
    if overlay.get("recall") != recomputed["recall"]:
        return False
    if overlay.get("accepted") != recomputed["accepted"]:
        return False
    if overlay.get("field_score") != recomputed["field_score"]:
        return False
    if overlay.get("field_verdicts") != recomputed["field_verdicts"]:
        return False
    if _canon_multiset(overlay.get("matches")) != _canon_multiset(
            recomputed["matches"]):
        return False
    if _canon_multiset(overlay.get("unmatched_gold")) != _canon_multiset(
            recomputed["unmatched_gold"]):
        return False
    if _canon_multiset(overlay.get("unmatched_predicted")) != \
            _canon_multiset(recomputed["unmatched_predicted"]):
        return False
    if _canon_multiset(overlay.get("ambiguous")) != _canon_multiset(
            recomputed["ambiguous"]):
        return False
    if set(overlay.get("adjudication_applied") or []) != set(
            recomputed["adjudication_applied"]):
        return False
    return True


def evaluate_completion(cell_results, *, run_digest, input_digest,
                        collection=None, ledger=(), decisions=(),
                        required_cells=(), na_policy=None,
                        adjudicated=None):
    """Evaluate completion for a whole evaluation run.

    ``cell_results`` maps cell key -> ``score_cell`` result (the
    ORIGINAL pre-adjudication results); ``adjudicated`` optionally
    maps cell key -> an :func:`apply_adjudication` result for that
    cell (its digests and ``adjudication_applied`` ids are verified,
    and the overlay itself is verified by recomputation against the
    original result and the live pairing decisions). ``na_policy``
    maps cell key -> set of fields documented absent under the
    frozen N/A policy. Returns ``{"complete", "outcome", "reasons",
    "unresolved", "excluded", "documented_absent", "per_cell"}``.
    ``complete`` is True only when collection is complete, every
    required cell is present, and the unresolved ledger is empty
    after valid adjudications. The outcome is ``incomplete`` while
    anything blocks; once complete it is ``complete-pass`` (every
    assessable cell accepted), ``complete-fail`` (any cell failed)
    or ``complete-N/A`` (every cell N/A — never a quality pass).

    Fail-closed coverage (issue #322): the mandatory
    ambiguity/candidate/collection ledger is derived internally
    from the scorer outputs, so an omitted, empty or truncated
    caller ledger never passes while such cases exist; a frozen
    ``required_cells`` set must be supplied whenever cells are
    present; each cell's ``accepted`` must be exactly True/False/
    None; decisions resolve only compatible-kind entries
    (``DECISION_ENTRY_COMPAT``); collection entries close only on
    collection evidence; and ``per_cell.blocked`` reflects global
    collection failures as well as unresolved ledger entries.

    Fail-closed coverage (issue #327): the mandatory ledger is
    derived from the ORIGINAL results, so an overlay can never drop
    a case from the denominator; a supplied entry reusing a derived
    ID must match the derived record on kind/cell/document/
    event-type/issuer/detail (only the decision-backed
    in_scope -> out_of_scope transition may differ); an adjudicated
    overlay is verified by recomputation (its applied IDs reconcile
    with the live pairing decisions both ways and the re-score must
    match the original under exactly those decisions); per-cell
    blocking derives from the authoritative derived record, so a
    relabelled supplied entry cannot move blocking to another cell.
    """
    if not run_digest or not input_digest:
        raise ValueError("run_digest and input_digest are required")
    na_policy = na_policy or {}
    reasons, unresolved, excluded, documented = [], [], [], []
    per_cell = {}
    originals = {}
    for cell, result in (cell_results or {}).items():
        key = _cell_key(cell)
        if not isinstance(result, dict) or "accepted" not in result:
            raise ValueError("not a score_cell result for cell %s" % (key,))
        originals[key] = result
    effective = dict(originals)
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
        if key not in originals:
            raise ValueError(
                "adjudicated result for cell %s has no original "
                "score_cell result to verify it against" % (key,))
        if not isinstance(result.get("adjudication_applied"), list) \
                or not all(isinstance(a, str)
                           for a in result["adjudication_applied"]):
            raise ValueError(
                "adjudicated result for cell %s: adjudication_applied "
                "must be a list of decision ids" % (key,))
        effective[key] = result
    # 0. Threshold verdicts must be exactly in-domain (issue #322
    # finding 7): True/False/None by identity. Identity (not ==)
    # matters: 1 == True and 0 == False in Python, so an equality
    # test would let 1/0 through as verdicts. A non-domain value
    # raises instead of silently becoming a pass in the outcome
    # branch below.
    for key, result in effective.items():
        acc = result.get("accepted")
        if acc is not True and acc is not False and acc is not None:
            raise ValueError(
                "cell %s: accepted must be True, False or None, got "
                "%r" % (_cell_label(key), acc))
    supplied_ledger = list(ledger or [])
    # 1. Collection.
    coll_ok, coll_reasons = _validate_collection(collection)
    if coll_ok is not True:
        reasons.extend(coll_reasons)
    # 2. Required cells present. A frozen required-cell set is
    # mandatory whenever cells are present (issue #322 finding 1):
    # with an empty default, omitted universe members are
    # undetectable, so an unverified universe fails closed. (An
    # evaluation with no cells at all keeps the existing
    # complete-N/A semantics — see the outcome branch below.)
    if not required_cells and effective:
        reasons.append(
            "required-cell set not supplied: the frozen universe is "
            "unverified, so omitted cells are undetectable")
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
    # 3a. Mandatory ledger derived internally (issue #322 finding 1,
    # issue #327 finding 1): every ambiguity/candidate/collection
    # entry the scorer outputs and the collection state imply MUST
    # appear in the caller-supplied ledger. An omitted, empty or
    # truncated ledger never passes while such cases exist — the
    # caller forgetting build_ledger is not a pass. Extra caller
    # entries (field / scope / gold) are not derivable and are judged
    # on their own below; only the derivable minimum is enforced
    # here. Derivation reads the ORIGINAL results (issue #327):
    # an adjudicated overlay can never drop a case from the
    # denominator — a case leaves only through a live, compatible
    # decision below.
    derived = build_ledger(originals, run_digest=run_digest,
                           input_digest=input_digest,
                           collection=collection)
    derived_by_id = {e["id"]: e for e in derived}
    derived_ids_by_cell = {}
    for entry in derived:
        derived_ids_by_cell.setdefault(entry.get("cell"), set()).add(
            entry["id"])
    supplied_ids = {e["id"] for e in supplied_ledger
                    if isinstance(e, dict) and e.get("id")}
    for entry in derived:
        if entry["id"] not in supplied_ids:
            reasons.append(
                "ledger incomplete: missing %s entry %s for cell %s "
                "(caller ledger omits a case the scorer outputs imply)"
                % (entry["kind"], entry["id"],
                   _cell_label(entry["cell"])
                   if entry.get("cell") is not None else "-"))
            unresolved.append(entry)
    # 3b. Overlay verification (issue #327 findings 1/2): an
    # adjudicated result must be exactly what the adapter produces
    # from the ORIGINAL result under the live pairing decisions for
    # the cell. Applied IDs reconcile with the supplied live pairing
    # decisions in both directions — a ghost ID (applied but never
    # supplied as a live pairing decision) or a live pairing decision
    # never applied both fail — and the re-score must match the
    # original under exactly those decisions (counts, matches,
    # unmatched lists, ambiguities, verdicts). A hand-stamped overlay
    # with a ghost adjudication ID, dropped ambiguities or boosted
    # counts cannot pass, and neither can an honest adapter
    # regression that drops a case: the derived ledger above still
    # holds the original case.
    live_pairing_ids = {did for did, d in check["valid"].items()
                        if d["kind"] == "pairing"}
    for cell, overlay in (adjudicated or {}).items():
        key = _cell_key(cell)
        label = _cell_label(key)
        original = originals[key]
        applied = overlay.get("adjudication_applied") or []
        cell_pairing = [d for d in check["valid"].values()
                        if d["kind"] == "pairing" and any(
                            eid in derived_ids_by_cell.get(key, set())
                            for eid in d["entry_ids"])]
        cell_pairing_ids = {d["id"] for d in cell_pairing}
        ghosts = [a for a in applied if a not in live_pairing_ids]
        if ghosts:
            reasons.append(
                "adjudicated result for cell %s claims applied "
                "decision(s) %s which are not live supplied pairing "
                "decisions (ghost adjudication)"
                % (label, ", ".join(sorted(ghosts))))
            continue
        missing = sorted(cell_pairing_ids - set(applied))
        if missing:
            reasons.append(
                "adjudicated result for cell %s does not apply live "
                "pairing decision(s) %s for this cell"
                % (label, ", ".join(missing)))
            continue
        try:
            recomputed, _ = _apply_pairings(original, cell_pairing)
        except ValueError as e:
            reasons.append(
                "adjudicated result for cell %s cannot be reproduced "
                "from the original result and the live pairing "
                "decisions: %s" % (label, e))
            continue
        recomputed["adjudication_applied"] = [d["id"]
                                              for d in cell_pairing]
        recomputed["run_digest"] = run_digest
        recomputed["input_digest"] = input_digest
        if not _overlay_matches_recomputed(overlay, recomputed):
            reasons.append(
                "adjudicated result for cell %s does not match the "
                "re-score of the original result under the live "
                "pairing decisions (counts, matches, unmatched lists, "
                "ambiguities or verdicts differ)" % label)
    # 3c. Supplied-ledger content validation (issue #327 finding 1):
    # the internally derived record is authoritative. A supplied
    # entry reusing a derived ID must match the derived record on
    # kind/cell/document/event-type/issuer/detail — re-kinding an
    # ambiguity to ``field`` (or ``scope``) while keeping its ID, or
    # changing its detail, does not replace the mandatory entry.
    # The mismatched supplied entry is ignored (never judged under
    # its claimed kind) and the derived record stays unresolved.
    # ``scope`` is not part of this comparison: the single
    # decision-backed in_scope -> out_of_scope transition is judged
    # by the resolution loop below, which requires a live scope
    # decision.
    tainted = set()
    for entry in supplied_ledger:
        if not isinstance(entry, dict) or not entry.get("id"):
            continue  # malformed entries raise in the loop below
        derived_rec = derived_by_id.get(entry["id"])
        if derived_rec is None:
            continue  # extra entry: judged on its own below
        diffs = _derived_content_diffs(entry, derived_rec)
        if diffs:
            reasons.append(
                "ledger entry %s does not match the derived %s record "
                "(%s); the derived record stays unresolved"
                % (entry["id"], derived_rec["kind"],
                   "; ".join(diffs)))
            unresolved.append(derived_rec)
            tainted.add(entry["id"])
    seen_supplied = set()
    for entry in supplied_ledger:
        if not isinstance(entry, dict) or not entry.get("id") \
                or entry.get("kind") not in LEDGER_KINDS:
            raise ValueError("malformed ledger entry: %r" % (entry,))
        eid = entry["id"]
        if eid in seen_supplied:
            continue  # a duplicate supplied copy adds no new case
        seen_supplied.add(eid)
        if eid in tainted:
            # Content mismatch vs the derived record (§3c): the
            # derived record already stands unresolved above; the
            # supplied copy is never judged under its claimed kind.
            continue
        scope = entry.get("scope")
        if scope not in ("in_scope", "out_of_scope", "unknown"):
            raise ValueError("unknown ledger scope: %r" % (entry,))
        cell = entry.get("cell")
        key = _cell_key(cell) if cell is not None else None
        # Normalise the cell to the authoritative tuple form (issue
        # #327 finding 2): per-cell blocking and the excluded /
        # documented outputs must use the derived attribution, not a
        # caller-supplied replacement label. For entries matching a
        # derived record the cell was already validated equal above;
        # for extra entries this keeps a "POUL|dividend" string from
        # silently escaping the per-cell blocking comparison.
        entry = dict(entry)
        if key is not None:
            entry["cell"] = key
        # A collection entry is closed when the collection state
        # itself shows its document archived (not in missing).
        if entry["kind"] == "collection" and coll_ok is True \
                and collection is not None \
                and entry.get("source_document_id") \
                not in (collection.get("missing") or []):
            continue
        if entry["kind"] == "collection":
            # Collection entries are closed ONLY by collection
            # evidence (issue #322 finding 1/3): no decision of any
            # kind can adjudicate a missing document away.
            reasons.append(
                "collection entry %s unresolved: document %s is not "
                "shown archived by the collection state"
                % (eid, entry.get("source_document_id")))
            unresolved.append(entry)
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
        # Out of scope (issue #327 — the single scope policy): the
        # entry itself is marked out_of_scope and an evidence-backed
        # scope decision over its own ID excludes it; the entry is
        # retained in ``excluded``. A scope decision over an
        # in-scope entry does NOT exclude it (it falls through to
        # the compatibility check below and is refused), and a
        # separate kind="scope" entry never accounts for original
        # ambiguity/candidate entries.
        if scope == "out_of_scope":
            if live and any(d["kind"] == "scope" for d in live):
                excluded.append(entry)
                continue
            reasons.append(
                "entry %s claims out-of-scope without an "
                "evidence-backed scope decision" % eid)
            unresolved.append(entry)
            continue
        # In-scope: needs a live, valid decision OF A COMPATIBLE
        # KIND (issue #322 finding 5 — see DECISION_ENTRY_COMPAT);
        # a kind-mismatched decision does not resolve the entry. A
        # pairing decision additionally needs the re-scored result to
        # have applied it.
        if not live:
            reasons.append("entry %s unresolved (no adjudication)" % eid)
            unresolved.append(entry)
            continue
        permitted = DECISION_ENTRY_COMPAT.get(entry["kind"], ())
        compatible = [d for d in live if d["kind"] in permitted]
        for d in live:
            if d["kind"] not in permitted:
                reasons.append(
                    "decision %s (kind %s) cannot resolve %s entry "
                    "%s (permitted: %s)"
                    % (d["id"], d["kind"], entry["kind"], eid,
                       ", ".join(permitted) or "none"))
        if not compatible:
            unresolved.append(entry)
            continue
        blocked = False
        for d in compatible:
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
    # Blocking reflects the GLOBAL collection state too (issue #322
    # finding 3): an unknown, unfinished or partial collection
    # blocks every cell, not only cells with an unresolved ledger
    # entry — report truth must not depend on whether the caller
    # remembered build_ledger.
    global_blocking = [] if coll_ok is True \
        else ["collection: " + r for r in coll_reasons]
    for key, result in effective.items():
        blocking = [e for e in unresolved
                    if e.get("cell") == key or e.get("cell") is None]
        per_cell[_cell_label(key)] = {
            "accepted": result.get("accepted"),
            "blocked": bool(blocking) or bool(global_blocking),
            "blocking": [e["id"] for e in blocking] + global_blocking}
    for cell in required_cells or []:
        label = _cell_label(cell)
        if label not in per_cell:
            per_cell[label] = {"accepted": None, "blocked": True,
                               "blocking": ["required cell omitted"]
                               + global_blocking}
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
    # unresolved_candidates is derived from the EFFECTIVE ledger
    # (issue #322 finding 8): a candidate resolved by a valid
    # decision is no longer unresolved, even though it remains a
    # candidate output. The raw output count is kept separately as
    # candidate_outputs so the report never overclaims resolution.
    unresolved_candidates = sum(
        1 for e in gate["unresolved"] if e.get("kind") == "candidate")
    return {"cell": _cell_label(key),
            "collection": collection,
            "tp": result["tp"], "fp": result["fp"], "fn": result["fn"],
            "precision": result["precision"], "recall": result["recall"],
            "field_score": result["field_score"],
            "field_verdicts": result["field_verdicts"],
            "accepted": result["accepted"],
            "verified_matches": verified,
            "unresolved_candidates": unresolved_candidates,
            "candidate_outputs": candidates,
            "unresolved_ledger": gate["unresolved"],
            "excluded": gate["excluded"],
            "complete": gate["complete"], "outcome": gate["outcome"],
            "reasons": gate["reasons"]}
