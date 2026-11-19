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
- Match within same source document id AND same event type AND same
  issuer only [§4.1, §4.5]; issuer/type cell membership is enforced by
  the grouping key, not assumed from prepartitioning.
- One-to-one pairing; a gold event is used at most once. A duplicate
  predicted event reusing an already-matched gold event is an FP [§4.2].
- Matching is order-independent [§4.2, issue #305]: within a group the
  scorer takes a maximum-total-agreement one-to-one assignment
  (agreement = count of scored fields equal after normalisation; a
  pair needs agreement >= 1 to be identifiable). A predicted event is
  matched only when it is paired to the SAME gold event in EVERY
  maximum-agreement assignment (a forced pair) — being paired to one
  gold in some optima and unmatched in others is NOT forced either;
  otherwise it is left unmatched (FP) and the group is flagged
  ambiguous for adjudication [§4.4]. Groups over 7 events use the
  same rule computed exactly via the assignment problem (up to 15
  events per side); larger groups are rejected into adjudication,
  never greedily approximated [§4.3, §4.4, issue #313]. The scorer
  never breaks a tie in the direction that raises the score, and the
  result never depends on predicted input order.
- A candidate predicted event never grants a TP, even with identical
  fields: it is an FP and its gold counterpart an FN [§3, §4].
- Wrong predicted value = 1 FP + 1 FN; missing gold field = FN;
  unsupported extra = FP [§6]. Field denominators are end-to-end:
  unmatched gold events contribute an FN per present field, unmatched
  predicted events an FP per present field.
- Acceptance is the full §7 verdict: event P >= 0.95 / R >= 0.90 AND
  field P >= 0.95 / R >= 0.90 per scored field, AND zero unresolved
  in-scope ambiguities, AND zero unresolved candidates, AND
  collection 100% when collection status is supplied. A field whose
  denominators are both zero in the cell is N/A for that field and
  does not gate acceptance; a fully empty cell (0/0/0) is N/A, never
  a pass [§7, issue #314]. `accepted` is a threshold result only
  when collection status is not supplied — the `completion`
  breakdown records the collection gate as not assessed, and a
  completion claim requires the report runner to supply it.
- Input boundaries fail closed: a predicted event with a missing or
  unknown status, an event with a missing/unknown event type or a
  missing issuer, or a gold event carrying a prediction-only status
  is rejected with ValueError — never defaulted, never silently
  scored [issue #305 §4]. Contradictory collection status is
  likewise rejected [issue #314].
- Canonicalisation is a typed contract [§6]: dates to ISO YYYY-MM-DD
  (ISO, D/M/YYYY, D-M-YYYY, YYYY/MM/DD; Arabic-Indic digits
  normalised); money as (Decimal in base units, currency) with scale
  one/thousand/million/billion applied and currency compared as part
  of the value (bare numbers read as EGP); the extractor's nested
  date/money objects are flattened by an explicit adapter (a nested
  value of None stays None — a derived candidate is never a value).
  Tolerances are zero for every field: exact equality after
  canonicalisation. Any future tolerance is a spec change, not a
  scorer change.
"""
from datetime import date
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from itertools import permutations

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

# Status vocabularies — mirrors scripts/report_model.py:114-115, the
# source of truth for the extractor's statuses. Unknown values are
# rejected, never defaulted.
EXTRACTION_STATUSES = ("extracted", "candidate")
VERIFICATION_STATUSES = ("verified", "unverified")

# A derived record_date candidate is NEVER a scored value (spec §6):
# the extractor's UNVALIDATED derived candidate must not be passed in
# as fields["record_date"]; it lives outside "fields".
PRECISION_MIN = Fraction(95, 100)
RECALL_MIN = Fraction(90, 100)

DATE_FIELDS = ("ex_date", "entitlement_end", "payout_date",
               "record_date", "announced", "period_start",
               "period_end", "meeting_date", "assembly_date")
MONEY_FIELDS = ("amount_per_share", "npat", "npat_comparative",
                "revenue")
NUMBER_FIELDS = ("yoy_npat_pct",)
TIME_FIELDS = ("assembly_time",)
TOKEN_FIELDS = ("subtype", "state", "npat_scale")

SCALE_FACTORS = {"one": 1, "thousand": 10 ** 3, "million": 10 ** 6,
                 "billion": 10 ** 9}
# Arabic-Indic digits (U+0660-0669) and Extended Arabic-Indic digits
# (U+06F0-06F9) both normalise to ASCII 0-9 (spec §6).
_ARABIC_DIGITS = str.maketrans(
    "٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")

# Groups up to this size are enumerated exhaustively. Groups up to
# _MAX_EXACT_GROUP use the exact assignment-problem method
# (_forced_pairs_exact); larger groups are rejected into adjudication
# (_match_group_oversize) — never greedily approximated (issue #313).
# Realistic groups are 1-3 events.
_MAX_ENUMERATED_GROUP = 7
_MAX_EXACT_GROUP = 15


def _clean_digits(s):
    """Arabic-Indic digits -> ASCII; strip commas/spaces used as
    thousands separators and surrounding whitespace."""
    return (s.translate(_ARABIC_DIGITS).replace(",", "").replace(" ", "")
            .replace("\u00a0", "").replace("\u2009", "").strip())


def _canonical_date(value):
    """Date -> ISO YYYY-MM-DD, or the cleaned string when the value is
    not a recognisable date (identical garbage still equals identical
    garbage; it never equals a valid date)."""
    s = str(value).strip().translate(_ARABIC_DIGITS)
    if not s:
        return None
    for sep in ("-", "/"):
        parts = s.split(sep)
        if len(parts) == 3 and all(p.isdigit() for p in parts):
            if len(parts[0]) == 4:  # YYYY-MM-DD or YYYY/MM/DD
                y, m, d = (int(p) for p in parts)
            else:                   # D/M/YYYY or D-M-YYYY
                d, m, y = (int(p) for p in parts)
            try:
                return date(y, m, d).isoformat()
            except ValueError:
                return s
    return s


def _canonical_number(value):
    """Number -> Decimal (sign preserved; parentheses mean negative,
    Arabic loss reporting), or the cleaned string when unparseable."""
    s = str(value).strip()
    if not s:
        return None
    neg = False
    if s.startswith("(") and s.endswith(")"):
        neg, s = True, s[1:-1]
    s = _clean_digits(s)
    if s.startswith("-"):
        neg, s = True, s[1:]
    elif s.startswith("+"):
        s = s[1:]
    try:
        d = Decimal(s)
    except InvalidOperation:
        return str(value).strip()
    return -d if neg else d


def _canonical_money(value):
    """Money -> (Decimal in base units, currency).

    Accepts a flat scalar (gold, or a flat predicted value: scale
    "one", currency defaults to EGP — the evaluation is
    EGP-denominated) or the extractor's nested money object
    {"value", "currency", "scale"} (scripts/disclosure_events.py
    _money_field). Scale multiplies the value into base units;
    currency is part of the value, so EGP never equals USD.
    Unparseable values fall back to the cleaned string, which never
    equals a parsed (Decimal, currency) pair.
    """
    currency, scale = "EGP", "one"
    if isinstance(value, dict):
        currency = value.get("currency") or "EGP"
        scale = (value.get("scale") or "one")
        value = value.get("value")
        if value is None:
            return None
    num = _canonical_number(value)
    if not isinstance(num, Decimal):
        return num
    factor = SCALE_FACTORS.get(str(scale).strip().lower())
    if factor is None:
        return str(value).strip()
    return (num * factor, str(currency).strip().upper())


def _canonical_time(value):
    """Time -> HH:MM (24h). Accepts HH:MM, HH:MM:SS, HH:MM AM/PM."""
    s = str(value).strip().translate(_ARABIC_DIGITS)
    if not s:
        return None
    upper = s.upper()
    pm = upper.endswith("PM")
    am = upper.endswith("AM")
    if pm or am:
        s = s[:-2].strip()
    parts = s.split(":")
    if len(parts) in (2, 3) and all(p.isdigit() for p in parts):
        h, m = int(parts[0]), int(parts[1])
        if pm and h < 12:
            h += 12
        if am and h == 12:
            h = 0
        if 0 <= h <= 23 and 0 <= m <= 59:
            return "%02d:%02d" % (h, m)
    return s


def _norm(field, value):
    """Normalise one field value before comparison (spec §6, typed
    contract). None stays None; empty stays None. Nested extractor
    objects are flattened here: money dicts keep currency/scale
    (_canonical_money), other dicts contribute their scalar "value"
    (a None value stays None — a derived candidate is never a value).
    """
    if value is None:
        return None
    if isinstance(value, dict):
        if field in MONEY_FIELDS:
            return _canonical_money(value)
        value = value.get("value")
        if value is None:
            return None
    if isinstance(value, str) and not value.strip():
        return None
    if field in DATE_FIELDS:
        return _canonical_date(value)
    if field in MONEY_FIELDS:
        return _canonical_money(value)
    if field in NUMBER_FIELDS:
        return _canonical_number(value)
    if field in TIME_FIELDS:
        return _canonical_time(value)
    if field in TOKEN_FIELDS:
        return " ".join(str(value).split()).lower()
    return str(value).strip()


def _validate_event(ev, is_gold):
    """Fail-closed input validation (issue #305 §4). Raises ValueError
    on a missing/unknown event type, a missing issuer or document id,
    a non-dict fields mapping, a gold event carrying a prediction-only
    status, or (predicted only) a missing/unknown status."""
    if not isinstance(ev, dict):
        raise ValueError("event is not a dict: %r" % (ev,))
    etype = ev.get("event_type")
    if etype not in SCORED_FIELDS:
        raise ValueError("unknown or missing event_type: %r" % (etype,))
    for key in ("source_document_id", "issuer"):
        if not ev.get(key):
            raise ValueError("missing %s in event: %r" % (key, ev))
    fields = ev.get("fields")
    if fields is not None and not isinstance(fields, dict):
        raise ValueError("fields is not a dict: %r" % (fields,))
    if is_gold:
        for key in ("extraction_status", "verification_status"):
            if key in ev:
                raise ValueError(
                    "gold event carries prediction-only %s" % key)
    else:
        es = ev.get("extraction_status")
        if es not in EXTRACTION_STATUSES:
            raise ValueError(
                "missing or unknown extraction_status: %r" % (es,))
        vs = ev.get("verification_status")
        if vs not in VERIFICATION_STATUSES:
            raise ValueError(
                "missing or unknown verification_status: %r" % (vs,))


def _is_verified_event(ev):
    """Candidate status never grants a TP (spec §3). Statuses are
    validated before this is called, so no defaults are needed."""
    return (ev["extraction_status"] != "candidate"
            and ev["verification_status"] == "verified")


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


def _canonical_key(ev, fields):
    """Deterministic sort key for one event: the sorted normalised
    (field, value) pairs. Used to sort events into canonical
    (input-order-independent) order and to test whether duplicate
    claimants of one gold are identical."""
    gf = ev.get("fields") or {}
    return tuple(sorted((f, repr(_norm(f, gf.get(f)))) for f in fields))


def _resolve_forced_pairs(gold_list, pred_list, fields, partners,
                          unmatched_opt, gold_taken_every):
    """Turn per-pred partner sets across all maximum-total-agreement
    assignments into matches (spec §4.3/§4.4).

    `partners[i]` is the set of gold indices pred i is paired to in
    some optimum; `unmatched_opt[i]` says pred i is unmatched in at
    least one optimum; `gold_taken_every[j]` says gold j is used in
    every optimum. A predicted event is matched only when it is
    paired to the SAME gold event in EVERY optimum (a forced pair) —
    being paired to one gold in some optima and unmatched in others
    is NOT forced: the event is left unmatched (FP) and flagged
    ambiguous, with `unmatched_in_an_optimum` set so adjudication
    knows the event may equally be no event at all, not just the
    other gold. Identical duplicate predicted events are
    interchangeable (spec §4.2): when they are the only claimants of
    a gold that is taken in every optimum, the canonically-first
    takes the gold and the rest are unmatched FPs, with no flag.
    """
    claimants = {}
    for i, ps in enumerate(partners):
        if len(ps) == 1:
            claimants.setdefault(next(iter(ps)), []).append(i)
    matched_pair = {}   # pred index -> gold index
    ambiguous_idx = set()
    for j, cs in claimants.items():
        if len(cs) == 1:
            if unmatched_opt[cs[0]]:
                # Paired to j in some optima, unmatched in others:
                # not a forced pair — ambiguous, never matched on a
                # favourable pick.
                ambiguous_idx.add(cs[0])
            else:
                matched_pair[cs[0]] = j
        elif len({_canonical_key(pred_list[i], fields) for i in cs}) == 1 \
                and gold_taken_every[j] \
                and not any(j in partners[k]
                            for k in range(len(pred_list))
                            if len(partners[k]) > 1):
            # Identical duplicates (spec §4.2): the canonically-first
            # takes the gold; the rest are unmatched FPs, no flag —
            # swapping identical events changes nothing.
            matched_pair[cs[0]] = j
        else:
            # Contested gold, differing claimants: matching any one
            # would be a favourable, order-dependent choice.
            ambiguous_idx.update(cs)
    for i, ps in enumerate(partners):
        if len(ps) > 1:
            ambiguous_idx.add(i)
    matches, unmatched_pred, ambiguous = [], [], []
    used_gold = set()
    for i, p in enumerate(pred_list):
        if i in matched_pair:
            j = matched_pair[i]
            used_gold.add(j)
            matches.append((gold_list[j], p))
        elif i in ambiguous_idx:
            unmatched_pred.append(p)
            entry = {
                "predicted": p,
                "tied_gold_ids": sorted(
                    str(gold_list[j].get("gold_id", "?%d" % j))
                    for j in partners[i])}
            if unmatched_opt[i]:
                entry["unmatched_in_an_optimum"] = True
            ambiguous.append(entry)
        else:
            # Matched in no optimum: genuinely unmatched, not ambiguous.
            unmatched_pred.append(p)
    unmatched_gold = [g for j, g in enumerate(gold_list)
                      if j not in used_gold]
    return matches, unmatched_pred, unmatched_gold, ambiguous


def _match_group(gold_list, pred_list, fields):
    """Order-independent one-to-one matching for one group (spec §4).

    Returns (matches, unmatched_pred, unmatched_gold, ambiguous) where
    matches is a list of (gold, pred) forced pairs. Events are first
    sorted by canonical key, so the result depends only on the event
    multisets, never on predicted input order. A pair is eligible only
    with agreement >= 1 (spec §4.3: the event must be identifiable);
    among all maximum-total-agreement assignments, a predicted event
    is matched only when paired to the SAME gold event in every
    optimum. A predicted event paired to two or more different golds
    across optima — or paired to one gold in some optima and
    unmatched in others — is ambiguous: left unmatched (FP) and
    flagged [§4.4]. Groups over 7 events use the same rule computed
    exactly via the assignment problem (up to 15 events per side);
    larger groups are rejected into adjudication, never greedily
    approximated (issue #313).
    Several predicted events claiming one gold are duplicates when
    identical (spec §4.2: one matches, the rest are FPs) and a
    contested tie when they differ (all left unmatched and flagged —
    matching any one would be a favourable, order-dependent choice).
    The scorer never breaks a tie in the direction that raises the
    score.
    """
    gold_list = sorted(gold_list, key=lambda g: _canonical_key(g, fields))
    pred_list = sorted(pred_list, key=lambda p: _canonical_key(p, fields))
    n_g, n_p = len(gold_list), len(pred_list)
    agree = [[_agreement(g, p, fields) for g in gold_list]
             for p in pred_list]
    eligible = [[agree[i][j] >= 1 for j in range(n_g)]
                for i in range(n_p)]

    if n_p > _MAX_EXACT_GROUP or n_g > _MAX_EXACT_GROUP:
        return _match_group_oversize(gold_list, pred_list)

    if n_p > _MAX_ENUMERATED_GROUP or n_g > _MAX_ENUMERATED_GROUP:
        partners, unmatched_opt, gold_taken_every = _forced_pairs_exact(
            agree, eligible)
        return _resolve_forced_pairs(
            gold_list, pred_list, fields, partners, unmatched_opt,
            gold_taken_every)

    # Enumerate every partial injective assignment; track the maximum
    # total agreement, then (second pass) each predicted event's
    # partner set across all optima — including the possibility of
    # being UNMATCHED in an optimum (spec §4.3: a pred paired to one
    # gold in some optima and unmatched in others is not a forced
    # pair) — and whether each gold is taken in every optimum.
    best = [0]

    def walk(i, used, total):
        if total > best[0]:
            best[0] = total
        if i == n_p:
            return
        walk(i + 1, used, total)  # leave pred i unmatched
        for j in range(n_g):
            if j not in used and eligible[i][j]:
                used.add(j)
                walk(i + 1, used, total + agree[i][j])
                used.discard(j)

    walk(0, set(), 0)
    optimum = best[0]
    partners = [set() for _ in range(n_p)]
    unmatched_opt = [False] * n_p
    gold_used = [0] * n_g
    optima_count = [0]

    def collect(i, used, total, pairing):
        if i == n_p:
            if total == optimum:
                optima_count[0] += 1
                paired = {k for k, _ in pairing}
                for k, j in pairing:
                    partners[k].add(j)
                    gold_used[j] += 1
                for k in range(n_p):
                    if k not in paired:
                        unmatched_opt[k] = True
            return
        collect(i + 1, used, total, pairing)
        for j in range(n_g):
            if j not in used and eligible[i][j]:
                used.add(j)
                pairing.append((i, j))
                collect(i + 1, used, total + agree[i][j], pairing)
                pairing.pop()
                used.discard(j)

    collect(0, set(), 0, [])
    gold_taken_every = [gold_used[j] == optima_count[0]
                        for j in range(n_g)]
    return _resolve_forced_pairs(
        gold_list, pred_list, fields, partners, unmatched_opt,
        gold_taken_every)


def _hungarian(cost):
    """Minimum-cost square assignment (e-maxx O(n^3) Hungarian).

    `cost` is a 1-indexed (n+1)x(n+1) matrix of non-negative integer
    costs. Returns (min_total_cost, assignment) with assignment[i] =
    the column assigned to row i (1-indexed). Only the total is used
    by the scorer; forced pairs come from re-solving reduced
    problems, never from one arbitrary optimal assignment.
    """
    n = len(cost) - 1
    inf = 10 ** 18
    u = [0] * (n + 1)
    v = [0] * (n + 1)
    p = [0] * (n + 1)    # p[j] = row currently matched to column j
    way = [0] * (n + 1)
    for i in range(1, n + 1):
        p[0] = i
        j0 = 0
        minv = [inf] * (n + 1)
        used = [False] * (n + 1)
        while True:
            used[j0] = True
            i0 = p[j0]
            delta, j1 = inf, 0
            for j in range(1, n + 1):
                if used[j]:
                    continue
                cur = cost[i0][j] - u[i0] - v[j]
                if cur < minv[j]:
                    minv[j] = cur
                    way[j] = j0
                if minv[j] < delta:
                    delta, j1 = minv[j], j
            for j in range(n + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while True:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
            if j0 == 0:
                break
    assignment = [0] * (n + 1)
    for j in range(1, n + 1):
        if p[j]:
            assignment[p[j]] = j
    return -v[0], assignment


def _max_total(agree, eligible):
    """Maximum total agreement over all partial one-to-one
    assignments (spec §4.3), via the assignment problem: rows are
    predicted events, columns gold events, padded with dummy rows /
    columns so any event may stay unmatched. Every square entry
    costs MAXA except an eligible real pair, which costs
    MAXA - agreement, and an ineligible real pair, which costs a
    prohibitive BIG and is never chosen. The minimum-cost total is
    then N*MAXA minus the maximum total agreement, so the returned
    value is exactly the optimum the enumeration computes for small
    groups — no greedy approximation anywhere.
    """
    n_p = len(agree)
    n_g = len(agree[0]) if n_p else 0
    if n_p == 0 or n_g == 0:
        return 0
    if not any(eligible[i][j] for i in range(n_p) for j in range(n_g)):
        return 0
    maxa = max(max(row) for row in agree)
    n = n_p + n_g
    big = n * maxa + 1
    cost = [[maxa] * (n + 1) for _ in range(n + 1)]
    for i in range(n_p):
        for j in range(n_g):
            cost[i + 1][j + 1] = (maxa - agree[i][j]) \
                if eligible[i][j] else big
    total, _ = _hungarian(cost)
    return n * maxa - total


def _forced_pairs_exact(agree, eligible):
    """Partner sets across ALL maximum-total-agreement assignments
    for a group too large to enumerate (spec §4.3), without
    enumerating them: a pair is in some optimum iff its agreement
    plus the optimum of the problem without that pred and gold
    equals the full optimum; a pred is unmatched in some optimum
    iff the optimum without it equals the full optimum; a gold is
    taken in every optimum iff the optimum without it is strictly
    smaller. Each reduced optimum is one assignment-problem solve.
    Returns (partners, unmatched_opt, gold_taken_every) in the same
    shape the enumeration produces, so both paths share
    _resolve_forced_pairs and cannot drift apart.
    """
    n_p = len(agree)
    n_g = len(agree[0]) if n_p else 0
    optimum = _max_total(agree, eligible)
    partners = [set() for _ in range(n_p)]
    unmatched_opt = [False] * n_p
    for i in range(n_p):
        sub = [row[:] for k, row in enumerate(agree) if k != i]
        sub_e = [row[:] for k, row in enumerate(eligible) if k != i]
        if _max_total(sub, sub_e) == optimum:
            unmatched_opt[i] = True
    gold_taken_every = [True] * n_g
    for j in range(n_g):
        sub = [[v for k, v in enumerate(row) if k != j]
               for row in agree]
        sub_e = [[v for k, v in enumerate(row) if k != j]
                 for row in eligible]
        if _max_total(sub, sub_e) == optimum:
            gold_taken_every[j] = False
    for i in range(n_p):
        for j in range(n_g):
            if not eligible[i][j]:
                continue
            sub = [[v for k, v in enumerate(row) if k != j]
                   for kk, row in enumerate(agree) if kk != i]
            sub_e = [[v for k, v in enumerate(row) if k != j]
                     for kk, row in enumerate(eligible) if kk != i]
            if agree[i][j] + _max_total(sub, sub_e) == optimum:
                partners[i].add(j)
    return partners, unmatched_opt, gold_taken_every


def _match_group_oversize(gold_list, pred_list):
    """Groups over _MAX_EXACT_GROUP are rejected into adjudication
    (spec §4.4) instead of being silently approximated: no pair is
    matched, every predicted event is an FP, every gold event an
    FN, and every predicted event is flagged ambiguous with
    oversize_group set. Realistic groups are 1-3 events (the
    extractor emits at most one event per type per document, spec
    §2); a group this large is a pathological input, and the honest
    answer is a human decision, not a greedy guess."""
    all_ids = sorted(str(g.get("gold_id", "?%d" % j))
                     for j, g in enumerate(gold_list))
    ambiguous = [{"predicted": p, "tied_gold_ids": list(all_ids),
                  "oversize_group": True} for p in pred_list]
    return [], list(pred_list), list(gold_list), ambiguous


def _validate_collection(collection, gold_events, pred_events):
    """Validate the optional collection status (spec §7/§8, issue
    #314). Returns a normalised {"enumerated", "archived", "missing"}
    dict, or None when collection was not supplied — the collection
    gate is then not assessed (see score_cell). Raises ValueError on
    contradictory input, fail closed: counts must be non-negative
    ints with archived <= enumerated; `missing` must name exactly
    enumerated - archived documents; a missing document cannot also
    be a scored document, and the enumeration must cover every
    distinct scored document (a document that produced a gold or
    predicted event was necessarily archived, hence enumerated)."""
    if collection is None:
        return None
    if not isinstance(collection, dict):
        raise ValueError("collection must be a mapping or None: %r"
                         % (collection,))
    enumerated = collection.get("enumerated")
    archived = collection.get("archived")
    for name, value in (("enumerated", enumerated),
                        ("archived", archived)):
        if (isinstance(value, bool) or not isinstance(value, int)
                or value < 0):
            raise ValueError(
                "collection %s must be a non-negative int: %r"
                % (name, value))
    if archived > enumerated:
        raise ValueError("collection archived %d > enumerated %d"
                         % (archived, enumerated))
    missing = collection.get("missing", [])
    if isinstance(missing, (str, bytes)) \
            or not hasattr(missing, "__iter__"):
        raise ValueError(
            "collection missing must be an iterable of document ids: "
            "%r" % (missing,))
    missing = [str(m) for m in missing]
    if len(missing) != enumerated - archived:
        raise ValueError(
            "collection missing names %d documents but "
            "enumerated - archived is %d"
            % (len(missing), enumerated - archived))
    docs = {ev.get("source_document_id") for ev in gold_events} | \
        {ev.get("source_document_id") for ev in pred_events}
    if len(docs) > enumerated:
        raise ValueError(
            "collection enumerated %d but %d distinct scored documents"
            % (enumerated, len(docs)))
    if set(missing) & docs:
        raise ValueError(
            "collection missing names scored documents: %s"
            % sorted(set(missing) & docs))
    return {"enumerated": enumerated, "archived": archived,
            "missing": missing}


def _field_verdict(counts):
    """Full §7 verdict for one field's counts. None when the field is
    N/A in this cell (both denominators zero)."""
    tp, fp, fn = counts["tp"], counts["fp"], counts["fn"]
    precision = Fraction(tp, tp + fp) if tp + fp else None
    recall = Fraction(tp, tp + fn) if tp + fn else None
    if precision is None and recall is None:
        return None
    return ((precision is None or precision >= PRECISION_MIN)
            and (recall is None or recall >= RECALL_MIN))


def score_cell(gold_events, predicted_events, collection=None):
    """Score one cell (one issuer x one event type).

    Returns {"tp","fp","fn","field_score","field_verdicts","matches",
    "unmatched_gold","unmatched_predicted","ambiguous","precision",
    "recall","accepted","completion"}.
    "accepted" is the full §7 verdict — True/False when assessable,
    None when every denominator is zero (N/A — spec §7): event P >=
    0.95 / R >= 0.90 AND field P >= 0.95 / R >= 0.90 per scored field
    (fields N/A in this cell do not gate), AND zero unresolved
    in-scope ambiguities (every entry in "ambiguous" blocks — issue
    #314), AND zero unresolved candidates (a candidate that could be
    an event blocks — spec §7), AND collection 100% when collection
    status is supplied. A fully empty cell is N/A, never a pass.
    "completion" breaks the verdict down: {"thresholds_pass",
    "unresolved_ambiguities", "unresolved_candidates",
    "collection_complete", "collection", "complete"} — "complete" is
    the same value as "accepted". When `collection` is not supplied,
    "collection_complete" is None (gate not assessed): the verdict
    then covers thresholds + ambiguity + candidates only and is NOT
    a completion claim — the report runner must supply collection
    status for any completion claim (spec §8). There is no way to
    waive an ambiguity or a candidate: resolution is by adjudication
    plus re-scoring the adjudicated input, never by dropping the case
    (spec §7).
    `collection` is a mapping {"enumerated", "archived", "missing"}
    (see _validate_collection); contradictory input raises ValueError.
    Raises ValueError on fail-closed input violations (see
    _validate_event).
    """
    gold = list(gold_events or [])
    pred = list(predicted_events or [])
    for ev in gold:
        _validate_event(ev, is_gold=True)
    for ev in pred:
        _validate_event(ev, is_gold=False)
    collection = _validate_collection(collection, gold, pred)
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

    # Group by (source document, event type, issuer); match one-to-one
    # inside each group. Issuer is part of the key (spec §4.5): a
    # predicted event attributed to the wrong issuer cannot match that
    # issuer's gold — it lands in its own group and is an FP.
    groups = {}
    for ev in gold:
        groups.setdefault((ev.get("source_document_id"),
                           ev.get("event_type"), ev.get("issuer")),
                          {"gold": [], "pred": []})
    for ev in verifiable:
        groups.setdefault((ev.get("source_document_id"),
                           ev.get("event_type"), ev.get("issuer")),
                          {"gold": [], "pred": []})
    for ev in gold:
        groups[(ev.get("source_document_id"),
                ev.get("event_type"), ev.get("issuer"))]["gold"].append(ev)
    for ev in verifiable:
        groups[(ev.get("source_document_id"),
                ev.get("event_type"),
                ev.get("issuer"))]["pred"].append(ev)

    for (doc, etype, issuer), grp in sorted(
            groups.items(), key=lambda kv: str(kv[0])):
        gm, up, ug, amb = _match_group(
            grp["gold"], grp["pred"], SCORED_FIELDS.get(etype, ()))
        for g, p in gm:
            tp += 1
            matches.append({"gold": g, "predicted": p})
            _merge_field_counts(
                field_score,
                _field_counts(g.get("fields"), p.get("fields"),
                              SCORED_FIELDS.get(etype, ())))
        for p in up:
            unmatched_pred.append(p)
            fp += 1
        for g in ug:
            unmatched_gold.append(g)
            fn += 1
            _merge_field_counts(
                field_score,
                _field_counts(g.get("fields"), None,
                              SCORED_FIELDS.get(etype, ())))
        ambiguous.extend({
            "source_document_id": doc, "event_type": etype,
            "issuer": issuer, **a} for a in amb)
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
    field_verdicts = {f: _field_verdict(c)
                      for f, c in field_score.items()}
    # Evaluation-wide gates (spec §7, issue #314): an ambiguity or a
    # candidate that remains in the scored input is unresolved — it
    # blocks acceptance no matter how the thresholds come out — and a
    # supplied collection status below 100% blocks it too. The
    # completion breakdown keeps each gate visible so a report can
    # never mistake a threshold pass for a completed evaluation.
    unresolved_ambiguities = len(ambiguous)
    unresolved_candidates = len(candidate_pred)
    if collection is None:
        collection_complete = None  # not assessed, not a completion claim
    else:
        collection_complete = (collection["archived"]
                               == collection["enumerated"]
                               and not collection["missing"])
    if precision is None and recall is None:
        accepted = None  # fully empty cell (0/0/0): N/A, never a pass
        # and never a fail (spec §7). A cell where one side is N/A
        # but the other is assessable is judged on the assessable
        # side: e.g. TP=0, FP=0, FN=1 fails on recall (R = 0/1).
        thresholds_pass = None
    else:
        event_ok = ((precision is None or precision >= PRECISION_MIN)
                    and (recall is None or recall >= RECALL_MIN))
        # Full §7 verdict: every assessable scored field must pass too.
        fields_ok = all(v is not False for v in field_verdicts.values())
        thresholds_pass = event_ok and fields_ok
        accepted = (thresholds_pass
                    and unresolved_ambiguities == 0
                    and unresolved_candidates == 0
                    and collection_complete is not False)
    completion = {"thresholds_pass": thresholds_pass,
                  "unresolved_ambiguities": unresolved_ambiguities,
                  "unresolved_candidates": unresolved_candidates,
                  "collection_complete": collection_complete,
                  "collection": collection,
                  "complete": accepted}
    return {"tp": tp, "fp": fp, "fn": fn, "field_score": field_score,
            "field_verdicts": field_verdicts,
            "matches": matches, "unmatched_gold": unmatched_gold,
            "unmatched_predicted": unmatched_pred,
            "ambiguous": ambiguous, "precision": precision,
            "recall": recall, "accepted": accepted,
            "completion": completion}


def acceptance(tp, fp, fn):
    """Exact-fraction acceptance for raw EVENT counts only (spec §7).

    Returns {"precision","recall","assessable","passed"}; "passed" is
    None when a denominator is zero (N/A). This is the event-level
    verdict only — the full per-cell verdict in score_cell also gates
    on every scored field (see score_cell / _field_verdict).
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
