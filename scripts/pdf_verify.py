#!/usr/bin/env python3
"""Role-aware PDF-text verification over captured attachments (#301).

Verifies the fields scripts/disclosure_events.py extracted from a
harvested body against the stored source PDF(s) — and reports the
fields ONLY the PDF carries, as candidates with evidence. It never
mutates an event and never upgrades verification_status: a number
that merely appears somewhere in a PDF proves nothing.

What #299 got wrong, fixed here (Ins INS-299 review, verified):
1. Token presence is not field reproduction. Every check binds a
   value to its FIELD ROLE: the value must occur in the window after
   one of the field's own labels (e.g. "صافي الربح" for NPAT,
   "تاريخ تحريك الحدود السعرية" for ex-date), on the same page.
   A value found only next to another field's label is a
   "wrong_role" failure — swapping an event's ex-date/payout date,
   or its current/comparative NPAT, fails verification even though
   both values are still in the PDF.
2. Sign-less numerics. Money matching is sign-aware: a leading
   minus or parentheses around the number means a loss. Positive
   100 never matches the digits inside (100) or -100.
3. Singular `attachment` contract. This consumes #297's merged
   plural contract: item["attachments"], a list of pointer records
   (worker/attachment_capture.py). Each captured file is resolved
   strictly inside the archive root and hash-checked with
   verify_attachment() before it is read.
4. No maintained engine. Text comes from scripts/pdf_text.py
   (pypdf): ToUnicode font mapping, hex strings, FlateDecode.
   Text is read in pypdf layout mode, which returns Arabic in
   logical order (plain mode reverses RTL runs). A font without
   ToUnicode makes Arabic labels INCONCLUSIVE, not missing. A
   scanned (image-only) PDF is inconclusive, never a missing field.

PDF-only fields — the rule: a field is PDF-only when (a) it is in
the known field table for the event type, (b) the event payload has
NO value for it (the body did not state it), and (c) the PDF text
carries it with role evidence (label + value in-window). Such
fields are reported under "pdf_only_fields" as CANDIDATES with
page/quote/label evidence. They are not written into the event and
do not change its status; promoting them is a separate stage.

Tolerances are field-specific, not one global rule: dividend
amount_per_share uses the #131 coupon tolerance (max(0.02, 1%));
earnings money (NPAT, comparative, revenue) requires exact Decimal
equality after sign/scale handling; dates require exact equality;
coupon numbers require exact word-boundary equality.

Statuses: verified (every checkable field role-verified),
partial (some verified, the rest merely absent), mismatch (any
field the PDF actively contradicts — value in the wrong role, the
swap case, or the wrong scale — even when other fields verify),
missing (nothing verified, values absent), inconclusive (the PDF
cannot be read or has no text layer), skipped (no captured
attachment, or the event carries no checkable field). CLI exit
codes: 0 = at least one event verified and none failed; 1 = any
event partial/mismatch/missing/inconclusive; 2 = zero events in
the input, or zero events actually checked (all skipped) — zero
exit is not successful coverage.

Usage:
    pdf_verify.py verify <events.json> --disclosures <file>
        --archive-root <dir> [--out <file>]
    pdf_verify.py check
Requires pypdf (requirements.txt) for reading PDFs; without it
every event reports inconclusive.
"""
import argparse
import hashlib
import json
import os
import re
import sys
from decimal import Decimal

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "..", "worker"))
import disclosure_events  # noqa: E402
import pdf_text  # noqa: E402
import attachment_capture  # noqa: E402

VERIFIER_VERSION = "pdf-verify/1.0.0"
ROLE_WINDOW = 240       # chars after a role label a value may sit in
HEADER_WINDOW = 800     # chars at the top of page 1 (announced date)
SCALE_WINDOW = 80       # chars around a money match scale words may sit in

# (field, kind, [role labels], scale-aware?)
# kind: "money" | "date" | "exact". Labels are plain strings; matching
# uses flexible whitespace and tries the logical-order text first,
# the raw pypdf text second. "comparative_exclude" marks a label whose
# occurrences followed by a comparative phrase belong to the
# comparative field, not this one (mirrors the extractor's own rule).
_FIELD_ROLES = {
    "dividend": [
        {"field": "coupon_number", "kind": "exact",
         "labels": ["رقم الكوبون", "coupon number", "coupon no"]},
        {"field": "amount_per_share", "kind": "money",
         "labels": ["قيمة الكوبون", "coupon value", "amount per share",
                    "dividend per share"]},
        {"field": "ex_date", "kind": "date",
         "labels": ["تاريخ تحريك الحدود السعرية", "ex-date", "ex date"]},
        {"field": "entitlement_end", "kind": "date",
         "labels": ["تاريخ نهاية الحق", "نهاية الحق", "entitlement"]},
        {"field": "payout_date", "kind": "date",
         "labels": ["تاريخ التوزيع", "صرف الكوبون", "distribution date",
                    "payment date"]},
        # PDF-only only: the extractor never derives a record date.
        {"field": "record_date", "kind": "date", "pdf_only": True,
         "labels": ["تاريخ التسجيل", "تاريخ القيد", "record date"]},
    ],
    "earnings": [
        {"field": "npat", "kind": "money",
         "labels": ["صافي الربح", "net profit", "net income"],
         "comparative_exclude": True},
        {"field": "npat_comparative", "kind": "money",
         "labels": ["صافي الربح لفترة المقارنة",
                    "net profit for the comparative period",
                    "comparative net profit"]},
        {"field": "revenue", "kind": "money",
         "labels": ["صافي الإيرادات", "الإيرادات", "الايرادات",
                    "revenue", "total revenue"]},
        {"field": "period_start", "kind": "date", "pair": "period"},
        {"field": "period_end", "kind": "date", "pair": "period"},
    ],
    "board_decision": [
        {"field": "meeting_date", "kind": "date",
         "labels": ["بجلسته المنعقدة بتاريخ", "meeting held on"]},
        {"field": "assembly_date", "kind": "date",
         "labels": ["المقرر انعقادها بتاريخ", "scheduled to be held on",
                    "assembly scheduled"]},
    ],
}
# Period dates share one role: the من..إلى range after this label.
# The basis word (المجمعة / غير المجمعة / المستقلة) sits inside the
# label, as in the extractor's own period pattern.
_PERIOD_LABELS = ["القوائم المالية المجمعة عن الفترة",
                  "القوائم المالية غير المجمعة عن الفترة",
                  "القوائم المالية المستقلة عن الفترة",
                  "القوائم المالية عن الفترة",
                  "financial statements for the period",
                  "for the period"]
_ANNOUNCED_LABELS = ["تاريخ النشر", "القاهرة في"]
_CONFIG_TEXT = json.dumps(_FIELD_ROLES, sort_keys=True,
                         ensure_ascii=False) + "|window=%d" % ROLE_WINDOW
CONFIG_HASH = hashlib.sha256(
    _CONFIG_TEXT.encode("utf-8")).hexdigest()[:16]

_SCALE_WORDS = {
    "thousand": ["بالألف", "بالالف", "in thousands", "thousand"],
    "million": ["بالمليون", "in millions", "million"],
}
_AR_SEP = str.maketrans({"٬": ",", "،": ",", "٫": "."})
_NUMBER_RE = re.compile(r"(\()?[\s]*([-\u2212])?[\s]*"
                        r"(\d[\d,]*\.?\d*)[\s]*(\))?")
_PERIOD_SPAN_RE = re.compile(
    r"من\s*(\d{1,2}/\d{1,2}/\d{4})\s*(?:إلى|الى)\s*"
    r"(\d{1,2}/\d{1,2}/\d{4})")


def _label_re(label):
    parts = [re.escape(w) for w in str(label).split()]
    return re.compile(r"\s+".join(parts), re.I)


def _norm(text):
    """Digit-normalise + Arabic separator normalisation for matching."""
    return disclosure_events.norm_digits(text or "").translate(_AR_SEP)


def _page_variants(page):
    """(variant, text) pairs for one extracted page. pdf_text
    extracts in layout mode, which returns Arabic in logical order,
    so the text needs only digit normalisation — no RTL restoration.
    A single "logical" variant is searched; keeping one variant
    means a match cannot silently flip between two readings."""
    return (("logical", _norm(page["text"])),)


def _label_occurrences(text, role):
    """(start, end, label) of each usable label occurrence. For
    comparative_exclude roles, an occurrence followed within 40
    chars by a comparative phrase is not this field's label."""
    out = []
    for label in role.get("labels") or []:
        for m in _label_re(label).finditer(text):
            if role.get("comparative_exclude"):
                after = text[m.end():m.end() + 40]
                if "المقارنة" in after or "comparative" in after.lower():
                    continue
            out.append((m.start(), m.end(), label))
    return out


def _all_label_starts(text, etype):
    """(start, end) of every role label for the event type on this
    text — all fields, the period label and the announced labels.
    A role window ends where the next label begins."""
    starts = []
    for r in _FIELD_ROLES.get(etype, []):
        if r.get("pair"):
            for lab in _PERIOD_LABELS:
                starts += [(m.start(), m.end())
                           for m in _label_re(lab).finditer(text)]
        else:
            starts += [(ls, le)
                       for ls, le, _lab in _label_occurrences(text, r)]
    for lab in _ANNOUNCED_LABELS:
        starts += [(m.start(), m.end())
                   for m in _label_re(lab).finditer(text)]
    return starts


def _role_windows(text, role, etype):
    """[(label, window, label_end)] for one role: each window runs
    from the end of a label occurrence to the next label of any role
    (or ROLE_WINDOW chars, whichever is nearer). A value therefore
    belongs to the nearest preceding label — a window can never leak
    into the next field and launder a swapped date or amount."""
    starts = _all_label_starts(text, etype)
    if role.get("pair"):
        occs = []
        for lab in _PERIOD_LABELS:
            occs += [(m.start(), m.end(), lab)
                     for m in _label_re(lab).finditer(text)]
    else:
        occs = _label_occurrences(text, role)
    out = []
    for ls, le, lab in occs:
        # The next label must begin AFTER this label ends: a bare
        # word inside this label ("date" inside "Ex-date") is not a
        # next label, or the window would be empty.
        nxt = min([s for s, _e in starts if s > le], default=None)
        end = le + ROLE_WINDOW if nxt is None \
            else min(le + ROLE_WINDOW, nxt)
        out.append((lab, text[le:end], le))
    return out


def _clip(text, start, end, margin=60):
    s = max(0, start - margin)
    e = min(len(text), end + margin)
    return text[s:e].replace("\n", " ").strip()


def _parse_signed_number(m):
    """(Decimal|None, is_negative) for a _NUMBER_RE match."""
    try:
        d = Decimal(m.group(3).replace(",", ""))
    except Exception:
        return None, False
    neg = bool(m.group(2)) or (bool(m.group(1)) and bool(m.group(4)))
    return (-d if neg else d), neg


def _detect_scale(text, start, end):
    seg = text[max(0, start - SCALE_WINDOW):end + SCALE_WINDOW]
    low = seg.lower()
    for scale, words in _SCALE_WORDS.items():
        if any(w in seg or w in low for w in words):
            return scale
    return "one"


def _money_equal(want, got, event_type, field):
    """Field-specific tolerance: the #131 coupon rule applies ONLY
    to dividend amount_per_share; earnings money needs exact
    Decimal equality (sign and scale already handled)."""
    if event_type == "dividend" and field == "amount_per_share":
        return disclosure_events._dps_same(got, want)
    return got == want


def _find_money(window, want, event_type, field):
    """First sign-aware number in window equal to want (field
    tolerance). Returns (Decimal, start, end, scale) or None."""
    for m in _NUMBER_RE.finditer(window):
        got, _neg = _parse_signed_number(m)
        if got is None:
            continue
        if _money_equal(want, got, event_type, field):
            return got, m.start(), m.end(), _detect_scale(
                window, m.start(), m.end())
    return None


def _first_money(window):
    for m in _NUMBER_RE.finditer(window):
        got, _neg = _parse_signed_number(m)
        if got is not None:
            return got, m.start(), m.end(), _detect_scale(
                window, m.start(), m.end())
    return None


def _find_date(window, want):
    """First date in window equal to want (a date object)."""
    for d, s, e in disclosure_events.find_dates(window):
        if d == want:
            return d, s, e
    return None


def _parse_iso(value):
    try:
        y, mo, d = (int(x) for x in str(value).split("-"))
        from datetime import date
        return date(y, mo, d)
    except Exception:
        return None


def _field_value(event, field):
    """(value, scale) the event carries for a field, or (None, None).
    announced lives at top level; the rest in the payload."""
    if field == "announced":
        v = (event.get("announced") or {}).get("value")
        return v, None
    payload = event.get("payload") or {}
    f = payload.get(field)
    if isinstance(f, dict):
        return f.get("value"), f.get("scale")
    if isinstance(f, str):
        return f, None
    return None, None


def _checkable_fields(event):
    """[(role, value, scale)] for every payload/announced field the
    event actually carries a value for."""
    etype = event.get("event_type")
    out = []
    for role in _FIELD_ROLES.get(etype, []):
        if role.get("pdf_only"):
            continue
        value, scale = _field_value(event, role["field"])
        if value is not None:
            out.append((role, value, scale))
    ann = (event.get("announced") or {}).get("value")
    if ann:
        out.append(({"field": "announced", "kind": "date"}, ann, None))
    return out


def _search_field_in_page(page_texts, role, value, event_type):
    """Role-aware search of one field across pages.

    Returns {"outcome", "page", "quote", "label", "text_variant",
    "value_found", "found_in_role", "scale", "detail"}.
    outcome: verified | not_found | wrong_role | scale_mismatch.
    """
    kind = role["kind"]
    if kind == "date":
        want = _parse_iso(value)
        if want is None:
            return {"outcome": "not_found", "detail":
                    "event value %r is not an ISO date" % value}
    elif kind == "money":
        try:
            want = Decimal(str(value))
        except Exception:
            return {"outcome": "not_found", "detail":
                    "event value %r is not a number" % value}
    else:
        want = str(value)
    # Own-role windows first, then other-role windows (swap evidence).
    own = []
    for p in page_texts:
        for variant, text in _page_variants(p):
            windows = _role_windows(text, role, event_type)
            if role["field"] == "announced":
                # The document date: the top of page 1, plus any
                # window after an explicit date label.
                windows = [("header", text[0:HEADER_WINDOW], 0)] + windows
            for lab, window, _le in windows:
                hit = _match_in_window(window, kind, want, event_type,
                                       role["field"], p["page"])
                if hit is not None:
                    own.append((p["page"], variant, lab, window, hit))
    if own:
        page, variant, lab, window, hit = own[0]
        return _hit_result("verified", page, variant, lab, window, hit,
                           kind)
    # Not in its own role: is the value in ANY other field's window?
    etype = event_type
    for other_role in _FIELD_ROLES.get(etype, []):
        if other_role is role or other_role.get("pdf_only"):
            continue
        for p in page_texts:
            for variant, text in _page_variants(p):
                for lab, window, _le in _role_windows(text, other_role,
                                                      etype):
                    hit = _match_in_window(window, kind, want, etype,
                                           other_role["field"],
                                           p["page"])
                    if hit is not None:
                        return {"outcome": "wrong_role",
                                "page": p["page"], "label": lab,
                                "text_variant": variant,
                                "value_found": str(hit[0]),
                                "found_in_role": other_role["field"],
                                "quote": _clip(window, hit[1], hit[2]),
                                "detail": ("value found only next to "
                                           "the %s label, not its own "
                                           "%s label"
                                           % (other_role["field"],
                                              role["field"]))}
    return {"outcome": "not_found",
            "detail": "value not found next to any %s label"
                      % role["field"]}


def _match_in_window(window, kind, want, event_type, field, page):
    """A match tuple (value, start, end, scale|None) or None."""
    if kind == "money":
        return _find_money(window, want, event_type, field)
    if kind == "date":
        hit = _find_date(window, want)
        if hit is None:
            return None
        return hit[0], hit[1], hit[2], None
    m = re.search(r"(?<!\d)" + re.escape(str(want)) + r"(?!\d)", window)
    if m is None:
        return None
    return want, m.start(), m.end(), None


def _hit_result(outcome, page, variant, lab, window, hit, kind):
    value, s, e, scale = hit
    return {"outcome": outcome, "page": page, "label": lab,
            "text_variant": variant,
            "value_found": str(value),
            "quote": _clip(window, s, e), "scale": scale,
            "detail": ""}


def _check_period_pair(page_texts, start_val, end_val):
    """period_start/period_end share one role: a من..إلى range.
    Returns {"start": result, "end": result} with the same outcome
    shape as _search_field_in_page."""
    want_s, want_e = _parse_iso(start_val), _parse_iso(end_val)
    res = {}
    for field, want in (("period_start", want_s),
                        ("period_end", want_e)):
        res[field] = {"outcome": "not_found", "detail":
                      "no من..إلى period range in the PDF"}
    if want_s is None or want_e is None:
        return res
    first_span = None
    pair_role = {"field": "period", "kind": "date", "pair": "period"}
    for p in page_texts:
        for variant, text in _page_variants(p):
            for lab, window, _le in _role_windows(
                    text, pair_role, "earnings"):
                for pm in _PERIOD_SPAN_RE.finditer(window):
                        try:
                            from datetime import date
                            gs = date(*[int(x) for x in reversed(
                                pm.group(1).split("/"))])
                            ge = date(*[int(x) for x in reversed(
                                pm.group(2).split("/"))])
                        except ValueError:
                            continue
                        if first_span is None:
                            first_span = (gs, ge, p["page"], variant,
                                          lab, _clip(window, pm.start(),
                                                     pm.end()))
                        if gs == want_s and ge == want_e:
                            for field, got in (
                                    ("period_start", gs),
                                    ("period_end", ge)):
                                res[field] = {
                                    "outcome": "verified",
                                    "page": p["page"], "label": lab,
                                    "text_variant": variant,
                                    "value_found": got.isoformat(),
                                    "quote": _clip(window, pm.start(),
                                                   pm.end()),
                                    "detail": ""}
                            return res
    if first_span is not None:
        gs, ge, page, variant, lab, quote = first_span
        detail = ("PDF period range is %s to %s, event says %s to %s"
                  % (gs.isoformat(), ge.isoformat(),
                     want_s.isoformat(), want_e.isoformat()))
        for field in ("period_start", "period_end"):
            res[field] = {"outcome": "wrong_role", "page": page,
                          "label": lab, "text_variant": variant,
                          "value_found": "%s to %s"
                          % (gs.isoformat(), ge.isoformat()),
                          "quote": quote, "detail": detail}
    return res


def _extract_pdf_only(event, page_texts):
    """Fields the body did not state but the PDF carries with role
    evidence. Candidates only — never promoted into the event."""
    etype = event.get("event_type")
    out = []
    for role in _FIELD_ROLES.get(etype, []):
        value, _scale = _field_value(event, role["field"])
        if value is not None:
            continue
        if role.get("pair"):
            continue  # handled as a pair below
        cand = _extract_one_pdf_only(role, page_texts, etype)
        if cand is not None:
            out.append(cand)
    # Period pair: extract both when either is missing.
    ps, pe = _field_value(event, "period_start")[0], \
        _field_value(event, "period_end")[0]
    if etype == "earnings" and (ps is None or pe is None):
        pair = _extract_period_pair(page_texts)
        if pair is not None:
            for field, val in (("period_start", pair[0]),
                               ("period_end", pair[1])):
                if _field_value(event, field)[0] is None:
                    out.append({"field": field, "kind": "date",
                                "value": val, "page": pair[2],
                                "quote": pair[3], "label": pair[4],
                                "text_variant": pair[5],
                                "detail": "PDF-only candidate"})
    return out


def _extract_one_pdf_only(role, page_texts, etype):
    for p in page_texts:
        for variant, text in _page_variants(p):
            for lab, window, _le in _role_windows(
                    text, role, etype):
                hit = None
                if role["kind"] == "money":
                    hit = _first_money(window)
                    if hit is not None:
                        got, s, e, scale = hit
                        return {"field": role["field"], "kind": "money",
                                "value": disclosure_events.dec_str(got),
                                "scale": scale, "page": p["page"],
                                "quote": _clip(window, s, e),
                                "label": lab, "text_variant": variant,
                                "detail": "PDF-only candidate"}
                elif role["kind"] == "date":
                    dates = disclosure_events.find_dates(window)
                    if dates:
                        d, s, e = dates[0]
                        return {"field": role["field"], "kind": "date",
                                "value": d.isoformat(), "page": p["page"],
                                "quote": _clip(window, s, e),
                                "label": lab, "text_variant": variant,
                                "detail": "PDF-only candidate"}
                else:
                    m = re.search(r"\d+", window)
                    if m:
                        return {"field": role["field"], "kind": "exact",
                                "value": m.group(0), "page": p["page"],
                                "quote": _clip(window, m.start(),
                                               m.end()),
                                "label": lab, "text_variant": variant,
                                "detail": "PDF-only candidate"}
    return None


def _extract_period_pair(page_texts):
    pair_role = {"field": "period", "kind": "date", "pair": "period"}
    for p in page_texts:
        for variant, text in _page_variants(p):
            for lab, window, _le in _role_windows(
                    text, pair_role, "earnings"):
                pm = _PERIOD_SPAN_RE.search(window)
                if pm:
                    try:
                        from datetime import date
                        gs = date(*[int(x) for x in reversed(
                            pm.group(1).split("/"))])
                        ge = date(*[int(x) for x in reversed(
                            pm.group(2).split("/"))])
                    except ValueError:
                        continue
                    return (gs.isoformat(), ge.isoformat(), p["page"],
                            _clip(window, pm.start(), pm.end()), lab,
                            variant)
    return None


def _resolve_in_root(archive_root, rel_path):
    """Resolve a pointer path strictly inside the archive root.
    Returns the absolute path or None when the path escapes."""
    if not rel_path or os.path.isabs(rel_path):
        return None
    root = os.path.abspath(archive_root or "")
    cand = os.path.normpath(os.path.join(root, rel_path))
    if os.path.commonpath([root, cand]) != root:
        return None
    return cand


def _read_pdf_bytes(archive_root, pointer):
    """(bytes|None, reason) — bounded read of one captured file."""
    path = _resolve_in_root(archive_root, pointer.get("path"))
    if path is None:
        return None, "pointer path escapes the archive root"
    try:
        with open(path, "rb") as fh:
            data = fh.read(attachment_capture.MAX_PDF_BYTES + 1)
    except OSError as exc:
        return None, "stored PDF unreadable: %s" % exc
    if len(data) > attachment_capture.MAX_PDF_BYTES:
        return None, ("stored PDF is over the %d-byte cap"
                      % attachment_capture.MAX_PDF_BYTES)
    return data, ""


def verify_event(event, attachments, archive_root, loader=None):
    """Verify one event against its document's captured attachments.

    attachments: the item's item["attachments"] list (plural #297
    contract). loader(archive_root, pointer) -> (bytes|None, reason)
    overrides the disk read (tests inject fixtures). Returns the
    per-event result dict; never raises, never mutates the event.
    """
    load = loader or _read_pdf_bytes
    base = {"event_id": event.get("event_id"),
            "event_type": event.get("event_type"),
            "verifier": VERIFIER_VERSION,
            "config_hash": CONFIG_HASH,
            "status": "skipped", "fields": [], "pdf_only_fields": [],
            "files_checked": [], "detail": ""}
    checkable = _checkable_fields(event)
    if not checkable:
        base["detail"] = "event carries no checkable field"
        return base
    if not isinstance(attachments, list):
        base["detail"] = ("no attachments key on the source document "
                          "(harvest predates #297 capture)")
        return base
    captured = [a for a in attachments
                if isinstance(a, dict) and a.get("status") == "captured"]
    if not captured:
        states = sorted({str(a.get("status")) for a in attachments
                         if isinstance(a, dict)})
        base["detail"] = ("no captured attachment to verify against "
                          "(pointer statuses: %s)"
                          % ", ".join(states))
        return base
    page_texts, files = [], []
    for pointer in captured:
        data, reason = load(archive_root, pointer)
        frec = {"path": pointer.get("path"),
                "sha256": pointer.get("sha256"), "status": "unreadable",
                "detail": reason, "engine": pdf_text.ENGINE_NAME,
                "engine_version": pdf_text._engine_version(),
                "pages": 0}
        files.append(frec)
        if data is None:
            continue
        ok, why = attachment_capture.verify_attachment(pointer, data)
        if not ok:
            frec["detail"] = "hash check failed: %s" % why
            continue
        frec["status"] = "read"
        frec["sha256"] = pointer.get("sha256")
        ext = pdf_text.extract_pages(data)
        frec["status"] = ext["status"]
        frec["detail"] = ext["detail"]
        frec["pages"] = len(ext["pages"])
        if ext["status"] in ("ok", "partial"):
            page_texts.extend(ext["pages"])
    base["files_checked"] = files
    if not page_texts:
        base["status"] = "inconclusive"
        base["detail"] = ("no captured attachment yielded readable "
                          "text: %s"
                          % "; ".join("%s (%s)" % (f["path"], f["detail"])
                                     for f in files))
        return base
    # Unmapped-font pages make Arabic-label fields inconclusive.
    unmapped = any(
        f["status"] == "partial" and "ToUnicode" in (f["detail"] or "")
        for f in files)
    fields = []
    pair_done = {}
    if event.get("event_type") == "earnings":
        ps, pe = _field_value(event, "period_start")[0], \
            _field_value(event, "period_end")[0]
        if ps is not None and pe is not None:
            pair_done = _check_period_pair(page_texts, ps, pe)
    for role, value, scale in checkable:
        field = role["field"]
        if field in pair_done:
            res = dict(pair_done[field])
        else:
            res = _search_field_in_page(page_texts, role, value,
                                        event.get("event_type"))
        res["field"] = field
        res["kind"] = role["kind"]
        res["value_expected"] = str(value)
        # Scale consistency: the PDF's stated scale must agree with
        # the event's, or the match is a different magnitude.
        if res.get("outcome") == "verified" and role["kind"] == "money" \
                and scale and res.get("scale") \
                and res["scale"] != scale:
            res["outcome"] = "scale_mismatch"
            res["detail"] = ("PDF states scale %s, event says %s"
                             % (res["scale"], scale))
        if unmapped and res.get("outcome") in ("not_found", "wrong_role"):
            labels = (_PERIOD_LABELS if role.get("pair")
                      else role.get("labels") or [])
            if any(any(ord(c) > 127 for c in lab) for lab in labels):
                res["outcome"] = "inconclusive"
                res["detail"] = ("Arabic labels undecodable on this "
                                 "PDF (font without ToUnicode)")
        fields.append(res)
    base["fields"] = fields
    base["pdf_only_fields"] = _extract_pdf_only(event, page_texts)
    outcomes = [f["outcome"] for f in fields]
    if all(o == "verified" for o in outcomes):
        base["status"] = "verified"
        base["detail"] = ("%d/%d fields role-verified in the stored "
                          "PDF(s)" % (len(outcomes), len(outcomes)))
    elif any(o in ("wrong_role", "scale_mismatch") for o in outcomes):
        # Any field the PDF actively contradicts (value in the wrong
        # role, or the wrong scale) is a mismatch for the whole
        # event, even when other fields verify.
        base["status"] = "mismatch"
        base["detail"] = ("contradicted by the stored PDF: %s"
                          % "; ".join("%s: %s" % (f["field"], f["detail"])
                                     for f in fields
                                     if f["outcome"] in (
                                         "wrong_role",
                                         "scale_mismatch")))
    elif all(o == "inconclusive" for o in outcomes):
        base["status"] = "inconclusive"
        base["detail"] = "no field could be checked against this PDF"
    elif any(o == "verified" for o in outcomes):
        base["status"] = "partial"
        base["detail"] = ("verified %d/%d fields; failed: %s"
                          % (outcomes.count("verified"), len(outcomes),
                             ", ".join(f["field"] for f in fields
                                       if f["outcome"] != "verified")))
    else:
        base["status"] = "missing"
        base["detail"] = ("no checkable field found in the stored "
                          "PDF(s): %s" % ", ".join(
                              f["field"] for f in fields))
    return base


def verify_feed(events, items, archive_root, loader=None):
    """Verify a whole events file. items: the harvest disclosures
    (joined to events by source_document_id). Returns
    (results, summary). Never raises on bad rows — a row that cannot
    be joined is reported skipped, not dropped."""
    by_doc = {}
    for item in items or []:
        try:
            by_doc[disclosure_events._doc_id(item)] = item
        except Exception:
            continue
    results = []
    for ev in events or []:
        doc_id = ev.get("source_document_id")
        item = by_doc.get(doc_id) or {}
        atts = item.get("attachments") if isinstance(item, dict) else None
        try:
            results.append(verify_event(ev, atts, archive_root, loader))
        except Exception as exc:  # noqa: BLE001 - one bad event
            results.append({"event_id": ev.get("event_id"),
                            "event_type": ev.get("event_type"),
                            "verifier": VERIFIER_VERSION,
                            "config_hash": CONFIG_HASH,
                            "status": "inconclusive", "fields": [],
                            "pdf_only_fields": [], "files_checked": [],
                            "detail": "verifier raised: %s" % exc})
    summary = {"events": len(results), "checked": 0}
    for r in results:
        summary[r["status"]] = summary.get(r["status"], 0) + 1
        if r["status"] != "skipped":
            summary["checked"] += 1
    summary["failed"] = sum(summary.get(s, 0) for s in
                            ("partial", "mismatch", "missing",
                             "inconclusive"))
    summary["pdf_only_fields"] = sum(
        len(r.get("pdf_only_fields") or []) for r in results)
    return results, summary


def _exit_code(summary):
    if summary["events"] == 0 or summary["checked"] == 0:
        return 2  # zero coverage is a refusal, not a pass
    return 1 if summary.get("failed") else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser(
        "verify",
        help="role-aware verification of events against the captured "
             "PDFs (#301)")
    v.add_argument("input", help="events file (extract --out output)")
    v.add_argument("--disclosures", required=True,
                   help="harvest disclosures.json — items carry the "
                        "plural attachments pointers")
    v.add_argument("--archive-root", required=True,
                   help="directory the attachment paths resolve under")
    v.add_argument("--out", default=None)
    sub.add_parser("check")
    args = ap.parse_args(argv)
    if args.cmd == "check":
        print("verifier=%s config_hash=%s engine=%s"
              % (VERIFIER_VERSION, CONFIG_HASH, pdf_text.ENGINE_NAME))
        return 0
    with open(args.input, encoding="utf-8") as f:
        data = json.load(f)
    events = data.get("events", data) \
        if isinstance(data, dict) else data
    with open(args.disclosures, encoding="utf-8") as f:
        ddata = json.load(f)
    items = ddata.get("items", ddata) \
        if isinstance(ddata, dict) else ddata
    results, summary = verify_feed(events, items, args.archive_root)
    out = {"verifier": VERIFIER_VERSION, "config_hash": CONFIG_HASH,
           "summary": summary, "results": results}
    text = json.dumps(out, ensure_ascii=False, indent=1,
                      sort_keys=True) + "\n"
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
    else:
        sys.stdout.write(text)
    print("verified %d events (%d checked): %s"
          % (summary["events"], summary["checked"],
             ", ".join("%s=%d" % (k, v)
                       for k, v in sorted(summary.items())
                       if k not in ("events", "checked"))),
          file=sys.stderr)
    return _exit_code(summary)


if __name__ == "__main__":
    sys.exit(main())
