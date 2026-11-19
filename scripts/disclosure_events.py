#!/usr/bin/env python3
"""Structured bilingual EGX disclosure events — archive/shadow pilot (#109).

Extracts dividends / earnings / board decisions from already-harvested
Arabic EGX disclosures into timestamped, machine-readable events with
field-level provenance. Archive/shadow only: NOTHING here feeds the live
ensemble or the live report (no #68 model change, no compile_model.py
touch, no worker wiring).

Design (Ins INS-109 review, CONDITIONAL GO, verified by Moos 2026-11-19):
- one record, EN + AR fields; English summaries are deterministic
  templates over structured facts, never generated prose.
- dates kept semantically separate: announcement vs ex-date vs
  entitlement-end vs record date vs payout. A date is only ever read
  next to the wording that gives it its role; the record date is NEVER
  derived by the extractor (no T+2 invention) — when the source does
  not state it, the field is null with a derived_candidate note.
- money/ratios are decimal STRINGS (Decimal), never floats; the raw
  reported text and the unit/scale travel with every amount.
- field-level evidence: every field binds to a verbatim span (offsets
  into the digit-normalised body), the source URL and the document
  revision (sha256 of the retained clipped body — labelled as such, it
  is NOT a full-document hash). Extraction and verification are
  separate states; incomplete/ambiguous output is a CANDIDATE with
  reasons, never a verified event.
- identity: event_id is stable within a pinned document revision
  (source_document_id + type + occurrence + payload identity).
  Cross-document duplicates get an explicit link, never an automatic
  merge (1.89 vs 1.90 vs 1.8999999998 is one coupon per #131, but the
  pilot links, it does not merge).

Sources the pilot reads (all already harvested, no live fetching):
- worker/egx_harvest.py output (disclosures.json): official EGX detail
  pages — PRIMARY. NewsID is the source document id.
- news-disclosure runner feed (disclosures.json/news.json): Mubasher
  republications — discovery/corroboration only, never primary evidence.

Usage:
    disclosure_events.py extract <disclosures.json> [--out events.json]
        [--quarter-start YYYY-MM-DD] [--quarter-end YYYY-MM-DD]
    disclosure_events.py check  (self-check: no floats in any event)
Stdlib only.
"""
import argparse
import hashlib
import json
import re
import sys
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

SCHEMA_VERSION = 1
EXTRACTOR_VERSION = "disclosure-events/1.0.0"
# Config hash input: the role-pattern table + schema version. Any change
# to the extraction rules changes the hash, so two runs with the same
# hash ran the same rules.
CONFIG_TEXT = (
    "schema=1|roles=coupon:رقم الكوبون|amount:قيمة الكوبون|"
    "payout:تاريخ التوزيع|entitlement:تاريخ نهاية الحق|"
    "ex:تاريخ تحريك الحدود السعرية|period:القوائم المالية عن الفترة|"
    "npat:صافي الربح|meeting:بجلسته المنعقدة بتاريخ|"
    "assembly:المقرر انعقادها بتاريخ|announced=standalone-date-line"
)
CONFIG_HASH = hashlib.sha256(CONFIG_TEXT.encode("utf-8")).hexdigest()[:16]

_AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
_AR_SEP = str.maketrans({"٫": ".", "٬": "", "،": "", ",": ""})
_MONTHS = {"يناير": 1, "فبراير": 2, "مارس": 3, "أبريل": 4, "ابريل": 4,
           "مايو": 5, "يونيو": 6, "يوليو": 7, "أغسطس": 8, "اغسطس": 8,
           "سبتمبر": 9, "أكتوبر": 10, "اكتوبر": 10, "نوفمبر": 11,
           "ديسمبر": 12, "january": 1, "february": 2, "march": 3,
           "april": 4, "may": 5, "june": 6, "july": 7, "august": 8,
           "september": 9, "october": 10, "november": 11, "december": 12}

# Quarter window for the pilot (last quarter ending 2026-11-19).
QUARTER_START = date(2026, 8, 19)
QUARTER_END = date(2026, 11, 19)


def norm_digits(s):
    return str(s or "").translate(_AR_DIGITS)


def norm_number(s):
    """Arabic-Indic digits + Arabic separators -> plain ASCII digits."""
    return norm_digits(s).translate(_AR_SEP).strip()


def parse_decimal(raw):
    """Decimal from reported text; None when unparseable. Never float."""
    try:
        return Decimal(norm_number(raw))
    except (InvalidOperation, ValueError, AttributeError):
        return None


def dec_str(d):
    """Decimal -> canonical decimal string (no exponent, no float)."""
    if d is None:
        return None
    return format(d.normalize(), "f") if d == d.to_integral_value() \
        else format(d, "f")


def canonical(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"))


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def find_dates(text):
    """All (date, start, end) in digit-normalised text: d/m/Y and
    '15 نوفمبر 2026' / '15 November 2026' forms. Offsets are into the
    normalised text (evidence spans are measured there; the raw span is
    kept alongside). Precedent: ensemble._find_dates."""
    t = norm_digits(text)
    found = []
    for m in re.finditer(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})", t):
        try:
            found.append((date(int(m.group(3)), int(m.group(2)),
                               int(m.group(1))), m.start(), m.end()))
        except ValueError:
            pass
    low = t.lower()
    for name, mon in _MONTHS.items():
        for m in re.finditer(r"(\d{1,2})\s+" + re.escape(name) +
                             r"(?:\s+(\d{4}))?", low):
            try:
                found.append((date(int(m.group(2) or 2026), mon,
                                   int(m.group(1))), m.start(), m.end()))
            except ValueError:
                pass
        for m in re.finditer(re.escape(name) +
                             r"\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})",
                             low):
            try:
                found.append((date(int(m.group(2)), mon, int(m.group(1))),
                              m.start(), m.end()))
            except ValueError:
                pass
    return found


def _span(text_norm, start, end, raw_text):
    """Evidence object for a span of the normalised text."""
    return {"span": raw_text[start:end] if raw_text else
            text_norm[start:end],
            "start": start, "end": end, "kind": "verbatim"}


def _date_field(value, basis, evidence=None, derived_candidate=None,
                derived_rule=None):
    return {"value": value.isoformat() if value else None,
            "basis": basis, "evidence": evidence,
            "derived_candidate": derived_candidate,
            "derived_rule": derived_rule}


def _money_field(dec, currency, scale, raw, evidence):
    return {"value": dec_str(dec) if dec is not None else None,
            "currency": currency, "scale": scale, "raw": raw,
            "evidence": evidence}


def _signed_decimal(m):
    """Decimal from a regex match, negated when the reported number is
    wrapped in parentheses or preceded by a minus (Arabic loss
    reporting). Returns None when unparseable."""
    raw = m.group(1)
    d = parse_decimal(raw)
    if d is None:
        return None
    before = m.group(0)[:m.group(0).find(raw)] if raw in m.group(0) \
        else ""
    after = m.group(0)[m.group(0).find(raw) + len(raw):]
    if "(" in before and ")" in after:
        return -d
    if before.rstrip().endswith("-"):
        return -d
    return d


def _dps_same(a, b):
    """Issue #131: 1.89 vs 1.9 vs 1.8999999998 for coupon 42 are one
    coupon, not three — tolerate the larger of 0.02 absolute and 1%
    relative. (Same rule as ensemble._dps_same; the pilot LINKS on
    it, it never merges.)"""
    try:
        a, b = Decimal(str(a)), Decimal(str(b))
    except Exception:
        return False
    return abs(a - b) <= max(Decimal("0.02"),
                             Decimal("0.01") * max(abs(a), abs(b)))


def _role_date(norm, raw, label_patterns, default_year=2026):
    """The date whose nearest preceding wording (within 120 chars, no
    other date in between) is one of label_patterns. Returns
    (date, start, end) or (None, None, None). Role-based, never
    positional: a payout date elsewhere in the text can never win."""
    dates = find_dates(norm)
    for pat in label_patterns:
        for m in re.finditer(pat, norm, flags=re.I):
            for d, ds, de in dates:
                if ds < m.start() or ds - m.start() > 120:
                    continue
                if any(ds2 > m.start() and ds2 < ds
                       for _, ds2, _ in dates):
                    continue
                return d, ds, de
    return None, None, None


def _announced(norm, raw, item_date):
    """Announcement date: the standalone dd/mm/yyyy line under the
    title (EGX layout), NOT the first date in the body — the first
    date is often a period start (COMI 297291: 01/01/2026) or a
    comparative date. Falls back to the item date, then null."""
    m = re.search(r"(?m)^\s*(\d{1,2}/\d{1,2}/\d{4})\s*$", norm)
    if m:
        try:
            d = date(int(m.group(1).split("/")[2]),
                     int(m.group(1).split("/")[1]),
                     int(m.group(1).split("/")[0]))
            return d, m.start(1), m.end(1), "standalone-date-line"
        except ValueError:
            pass
    # Fallback: first date NOT inside a من..إلى period range.
    dates = find_dates(norm)
    for d, ds, de in sorted(dates, key=lambda e: e[1]):
        window = norm[max(0, ds - 30):ds]
        if "من" in window and "الى" in window:
            continue
        return d, ds, de, "first-non-period-date"
    if item_date:
        try:
            y, mo, dy = (int(x) for x in str(item_date)[:10].split("-"))
            return date(y, mo, dy), None, None, "item-date-fallback"
        except Exception:
            pass
    return None, None, None, "unavailable"


def _issuer(title, body, url):
    isin_m = re.search(r"(EGS[0-9A-Z]{9})", norm_digits(title + " " + body))
    ticker_m = re.search(r"\b([A-Z]{3,5}\.CA)\b", title + " " + body)
    name_m = re.search(r"اسم (?:الشركة|البنك)\s*:?\s*([^\n]{2,60})",
                       norm_digits(title + "\n" + body))
    return {"ticker": ticker_m.group(1) if ticker_m else None,
            "isin": isin_m.group(1) if isin_m else None,
            "name_ar": name_m.group(1).strip() if name_m else None,
            "name_en": None}


def _source_kind(url):
    return "primary" if "egx.com.eg" in (url or "") else "republication"


def _event_id(source_doc_id, event_type, subtype, occurrence, identity):
    raw = canonical({"doc": source_doc_id, "type": event_type,
                     "subtype": subtype, "n": occurrence,
                     "identity": identity})
    return "ev_" + _sha(raw)[:20]


def _finish(event, evidence_list):
    """Attach evidence, compute revision id, enforce the no-float rule."""
    event["evidence"] = evidence_list
    body = {k: v for k, v in event.items()
            if k not in ("event_revision_id", "retrieved_at")}
    event["event_revision_id"] = "rev_" + _sha(canonical(body))[:20]
    _assert_no_float(event)
    return event


def _assert_no_float(obj, path=""):
    if isinstance(obj, float):
        raise ValueError("float leaked into event at %s" % path)
    if isinstance(obj, dict):
        for k, v in obj.items():
            _assert_no_float(v, path + "/" + str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _assert_no_float(v, "%s[%d]" % (path, i))


def _base(source_doc_id, doc_rev, url, issuer, announced, event_type,
          subtype, occurrence, identity, summary_ar, summary_en,
          extraction_status, verification_status, reasons):
    return {
        "schema_version": SCHEMA_VERSION,
        "event_id": _event_id(source_doc_id, event_type, subtype,
                              occurrence, identity),
        "event_revision_id": None,
        "event_type": event_type,
        "subtype": subtype,
        "issuer": issuer,
        "source_document_id": source_doc_id,
        "document_revision_id": doc_rev,
        "source_url": url,
        "source_kind": _source_kind(url),
        "announced": announced,
        "summary_ar": summary_ar,
        "summary_en": summary_en,
        "summary_meta": {"origin": "derived-from-facts",
                         "language": "en",
                         "generator": "template-v1"},
        "payload": {},
        "evidence": [],
        "extraction_status": extraction_status,
        "verification_status": verification_status,
        "candidate_reasons": reasons,
        "duplicate_links": [],
        "stale": False,
        "extractor_version": EXTRACTOR_VERSION,
        "config_hash": CONFIG_HASH,
    }


# --- Dividend -------------------------------------------------------------
_DIV_TRIGGERS = ("كوبون", "توزيع نقدي", "توزيع", "dividend", "coupon")


def _extract_dividend(item, norm, raw, issuer, announced, doc_id, doc_rev,
                      url, evidence):
    reasons = []
    coupon_m = re.search(r"رقم الكوبون\s*:?\s*(\d+)", norm)
    coupon = coupon_m.group(1) if coupon_m else None
    coupon_ev = None
    if coupon_m:
        coupon_ev = {"field": "payload.coupon_number",
                     **_span(norm, *coupon_m.span(1), raw)}
        evidence.append(coupon_ev)
    amt_m = re.search(r"قيمة الكوبون\s*:?\s*([0-9.,٫٬٠-٩]+)\s*(?:جنيه|EGP)?",
                      norm)
    amount = parse_decimal(amt_m.group(1)) if amt_m else None
    amt_ev = None
    if amt_m:
        amt_ev = {"field": "payload.amount_per_share",
                  **_span(norm, *amt_m.span(1), raw)}
        evidence.append(amt_ev)
    if amount is None:
        reasons.append("amount_per_share not stated in source body")
    payout, ps, pe = _role_date(
        norm, raw, [r"تاريخ التوزيع", r"distribution date", r"صرف الكوبون"])
    pay_ev = None
    if payout:
        pay_ev = {"field": "payload.payout_date",
                  **_span(norm, ps, pe, raw)}
        evidence.append(pay_ev)
    else:
        reasons.append("payout_date not stated in source body")
    ent, es, ee = _role_date(
        norm, raw, [r"تاريخ نهاية الحق", r"نهاية الحق", r"entitlement"])
    ent_ev = None
    if ent:
        ent_ev = {"field": "payload.entitlement_end",
                  **_span(norm, es, ee, raw)}
        evidence.append(ent_ev)
    else:
        reasons.append("entitlement_end not stated in source body")
    exd, xs, xe = _role_date(
        norm, raw, [r"تاريخ تحريك الحدود السعرية", r"ex-date", r"ex date"])
    ex_ev = None
    if exd:
        ex_ev = {"field": "payload.ex_date",
                 **_span(norm, xs, xe, raw)}
        evidence.append(ex_ev)
    else:
        reasons.append("ex_date not stated in source body")
    # Record date: NEVER derived by the extractor. The EGX body does
    # not state one; the T+2 settlement candidate is recorded as a
    # candidate only, with the rule named and marked unvalidated.
    rec_candidate = None
    if ent is not None:
        rec_candidate = (ent + timedelta(days=2)).isoformat()
    if coupon is None:
        reasons.append("coupon_number not stated in source body")
    complete = (coupon is not None and amount is not None and payout
                and ent and exd)
    status = "extracted" if complete else "candidate"
    verified = "verified" if (complete and _source_kind(url) == "primary") \
        else "unverified"
    summary_ar = (item.get("title") or "").strip() or None
    summary_en = None
    if complete:
        summary_en = (
            "%s cash dividend: coupon %s, EGP %s per share; "
            "entitlement ends %s; ex-date %s; payout %s." % (
                issuer.get("ticker") or "?", coupon, dec_str(amount),
                ent.isoformat(), exd.isoformat(), payout.isoformat()))
    ev = _base(doc_id, doc_rev, url, issuer, announced, "dividend",
               "cash_dividend", 0,
               {"coupon": coupon, "amount": dec_str(amount),
                "ex_date": exd.isoformat() if exd else None},
               summary_ar, summary_en, status, verified, reasons)
    ev["payload"] = {
        "coupon_number": coupon,
        "amount_per_share": _money_field(
            amount, "EGP", "one",
            amt_m.group(0) if amt_m else None, amt_ev),
        "currency": "EGP",
        "ex_date": _date_field(exd, "verbatim:تاريخ تحريك الحدود السعرية"
                             if exd else "not-stated", ex_ev),
        "entitlement_end": _date_field(
            ent, "verbatim:تاريخ نهاية الحق" if ent else "not-stated",
            ent_ev),
        "record_date": _date_field(
            None, "not-stated-in-source",
            derived_candidate=rec_candidate,
            derived_rule="T+2 settlement from entitlement_end "
                         "(UNVALIDATED — candidate only, not a fact)"),
        "payout_date": _date_field(
            payout, "verbatim:تاريخ التوزيع" if payout else "not-stated",
            pay_ev),
    }
    return _finish(ev, evidence)


# --- Earnings -------------------------------------------------------------
_EARN_TRIGGERS = ("نتائج أعمال", "نتائج الاعمال", "صافي الربح",
                  "earnings", "results")


def _scale_of(norm, start):
    window = norm[start:start + 120]
    if "بالألف" in window or "بالالف" in window:
        return "thousand"
    if "بالمليون" in window:
        return "million"
    return "one"


def _extract_earnings(item, norm, raw, issuer, announced, doc_id, doc_rev,
                      url, evidence):
    reasons = []
    consolidated = "مجمعة" in norm
    standalone = ("غير المجمعة" in norm or "المستقلة" in norm
                  or "غير مجمعة" in norm)
    # Standalone first: "غير المجمعة" contains "مجمعة" as a substring.
    basis = "standalone" if standalone else (
        "consolidated" if consolidated else None)
    if basis is None:
        reasons.append("consolidated/standalone basis not stated")
    per_m = re.search(
        r"القوائم المالية (?:المجمعة|غير المجمعة|المستقلة)?\s*عن الفترة"
        r"\s*:?\s*من\s*(\d{1,2}/\d{1,2}/\d{4})\s*(?:إلى|الى)\s*"
        r"(\d{1,2}/\d{1,2}/\d{4})", norm)
    p_start = p_end = None
    if per_m:
        try:
            p_start = date(*[int(x) for x in
                             reversed(per_m.group(1).split("/"))])
            p_end = date(*[int(x) for x in
                           reversed(per_m.group(2).split("/"))])
        except ValueError:
            reasons.append("period dates unparseable")
        evidence.append({"field": "payload.period",
                         **_span(norm, *per_m.span(0), raw)})
    else:
        reasons.append("reporting period not stated in source body")
    npat_m = re.search(r"صافي الربح\s*:?\s*\(?([0-9,٫٬٠-٩]+)\)?", norm)
    # Prefer the FIRST صافي الربح that is not the comparative line.
    npat = None
    if npat_m:
        before = norm[max(0, npat_m.start() - 40):npat_m.start()]
        if "المقارنة" not in before:
            npat = _signed_decimal(npat_m)
    if npat is None:
        # Scan all occurrences; take the one outside a comparative line.
        for m in re.finditer(r"صافي الربح\s*:?\s*\(?([0-9,٫٬٠-٩]+)\)?",
                             norm):
            before = norm[max(0, m.start() - 40):m.start()]
            if "المقارنة" in before:
                continue
            npat = _signed_decimal(m)
            npat_m = m
            break
    npat_scale = _scale_of(norm, npat_m.start()) if npat_m else "one"
    npat_ev = None
    if npat_m and npat is not None:
        npat_ev = {"field": "payload.npat",
                   **_span(norm, *npat_m.span(1), raw)}
        evidence.append(npat_ev)
    comp_m = re.search(
        r"صافي الربح لفترة المقارنة\s*:?\s*\(?([0-9,٫٬٠-٩]+)\)?", norm)
    comp = _signed_decimal(comp_m) if comp_m else None
    comp_ev = None
    if comp_m:
        comp_ev = {"field": "payload.npat_comparative",
                   **_span(norm, *comp_m.span(1), raw)}
        evidence.append(comp_ev)
    rev_m = re.search(
        r"(?:الإيرادات|صافي الإيرادات|الايرادات)\s*:?\s*\(?"
        r"([0-9,٫٬٠-٩]+)\)?", norm)
    revenue = parse_decimal(rev_m.group(1)) if rev_m else None
    rev_ev = None
    if rev_m:
        rev_ev = {"field": "payload.revenue",
                  **_span(norm, *rev_m.span(1), raw)}
        evidence.append(rev_ev)
    if revenue is None:
        reasons.append("revenue not stated in source body "
                       "(in attachment, not harvested)")
    yoy = None
    if npat is not None and comp not in (None, Decimal(0)):
        yoy = ((npat - comp) / comp * Decimal(100)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP)
    if npat is None:
        reasons.append("NPAT not stated in source body")
    complete = (basis is not None and p_start and p_end
                and (npat is not None or revenue is not None))
    status = "extracted" if complete else "candidate"
    verified = "verified" if (complete and _source_kind(url) == "primary") \
        else "unverified"
    fy = p_end.year if p_end else None
    fq = None
    if p_end:
        fq = "Q%d" % ((p_end.month - 1) // 3 + 1)
    summary_ar = (item.get("title") or "").strip() or None
    summary_en = None
    if complete:
        summary_en = "%s %s %s results %s-%s: NPAT EGP %s%s." % (
            issuer.get("ticker") or "?", basis,
            (fq + " " + str(fy)) if fy else "",
            p_start.isoformat() if p_start else "?",
            p_end.isoformat() if p_end else "?",
            dec_str(npat) if npat is not None else "n/a",
            " (in thousands)" if npat_scale == "thousand" else "")
    ev = _base(doc_id, doc_rev, url, issuer, announced, "earnings",
               "results_9m" if p_end and p_end.month == 9 else "results",
               0, {"basis": basis,
                   "period_end": p_end.isoformat() if p_end else None,
                   "npat": dec_str(npat)},
               summary_ar, summary_en, status, verified, reasons)
    ev["payload"] = {
        "period_start": _date_field(
            p_start, "verbatim:القوائم المالية عن الفترة"
            if p_start else "not-stated"),
        "period_end": _date_field(
            p_end, "verbatim:القوائم المالية عن الفترة"
            if p_end else "not-stated"),
        "fiscal_year": str(fy) if fy else None,
        "fiscal_quarter": fq,
        "basis": basis,
        "npat": _money_field(npat, "EGP", npat_scale,
                             npat_m.group(0) if npat_m else None, npat_ev),
        "npat_comparative": _money_field(
            comp, "EGP", npat_scale,
            comp_m.group(0) if comp_m else None, comp_ev),
        "revenue": _money_field(revenue, "EGP", "one",
                                rev_m.group(0) if rev_m else None, rev_ev),
        "yoy_npat_pct": {"value": dec_str(yoy) if yoy is not None else None,
                         "basis": "derived: NPAT vs comparative NPAT"
                         if yoy is not None else "not-computable",
                         "evidence": None},
    }
    return _finish(ev, evidence)


# EGX writes "مجلس إدارة" (no ال on إدارة) — both forms are triggers.
_BOARD_TRIGGERS = ("مجلس الإدارة", "مجلس الادارة", "مجلس إدارة",
                   "مجلس ادارة", "جمعية عامة", "الجمعية العامة",
                   "board of directors", "general assembly")


def _extract_board(item, norm, raw, issuer, announced, doc_id, doc_rev,
                   url, evidence):
    """Board decisions / assembly calls. Returns None for documents
    that merely MENTION a board or an assembly: minutes of a past
    assembly (محضر) are not a call, and a regulator's statement about
    a board decision (قرار مجلس, singular) is not the board's own
    announcement of its decisions (قرارات مجلس, plural)."""
    reasons = []
    is_call = "دعوة" in norm and "جمعية" in norm
    is_decisions = "قرارات مجلس" in norm
    if not is_call and not is_decisions:
        return None
    egm = "غير العادية" in norm and "جمعية" in norm
    agm = ("العادية" in norm and "جمعية" in norm) and not egm
    meet_m = re.search(r"بجلسته المنعقدة بتاريخ\s*(\d{1,2}/\d{1,2}/\d{4})",
                       norm)
    asm_m = re.search(
        r"المقرر انعقادها بتاريخ\s*(\d{1,2}/\d{1,2}/\d{4})", norm)
    asm_time_m = re.search(r"الساعة\s*(\d{1,2}:\d{2})", norm)
    meet_date = None
    if meet_m:
        try:
            meet_date = date(*[int(x) for x in
                               reversed(meet_m.group(1).split("/"))])
        except ValueError:
            pass
        evidence.append({"field": "payload.meeting_date",
                         **_span(norm, *meet_m.span(1), raw)})
    asm_date = None
    if asm_m:
        try:
            asm_date = date(*[int(x) for x in
                              reversed(asm_m.group(1).split("/"))])
        except ValueError:
            pass
        evidence.append({"field": "payload.assembly_date",
                         **_span(norm, *asm_m.span(1), raw)})
    if is_call:
        subtype = "egm_call" if egm else "agm_call"
        state = "proposed"  # a call is a proposal, not an executed action
        if asm_date is None:
            reasons.append("assembly date not stated in source body")
        complete = asm_date is not None
    else:
        subtype = "board_decisions"
        # Details live in the attachment, which the harvest does not
        # retain: the meeting date is a fact, the decisions are not.
        state = "unknown"
        reasons.append("decision details in attachment, not harvested")
        complete = False
    status = "extracted" if complete else "candidate"
    verified = "verified" if (complete and _source_kind(url) == "primary") \
        else "unverified"
    summary_ar = (item.get("title") or "").strip() or None
    summary_en = None
    if complete and subtype in ("egm_call", "agm_call"):
        summary_en = "%s %s called for %s%s." % (
            issuer.get("ticker") or "?",
            "extraordinary general assembly" if egm
            else "annual general assembly",
            asm_date.isoformat(),
            (" at " + asm_time_m.group(1)) if asm_time_m else "")
    ev = _base(doc_id, doc_rev, url, issuer, announced, "board_decision",
               subtype, 0,
               {"subtype": subtype,
                "date": (asm_date or meet_date).isoformat()
                if (asm_date or meet_date) else None},
               summary_ar, summary_en, status, verified, reasons)
    ev["payload"] = {
        "meeting_date": _date_field(
            meet_date, "verbatim:بجلسته المنعقدة بتاريخ"
            if meet_date else "not-stated"),
        "decision_subtype": subtype,
        "state": state,
        "subject_ar": None,
        "subject_en": None,
        "assembly_date": _date_field(
            asm_date, "verbatim:المقرر انعقادها بتاريخ"
            if asm_date else "not-stated"),
        "assembly_time": asm_time_m.group(1) if asm_time_m else None,
    }
    return _finish(ev, evidence)


# --- Document dispatch ----------------------------------------------------
def _doc_id(item):
    """Stable source-document id. EGX disclosures are keyed by NewsID
    whether it arrives as the `id` field (harvest) or inside the URL
    (news-disclosure feed items carry no `id`), so the harvest copy
    and the sweep copy of one disclosure share one id."""
    raw_id = str(item.get("id") or item.get("NewsID") or "")
    url = item.get("url") or item.get("resolved_url") or ""
    if not raw_id:
        m = re.search(r"NewsID=(\d+)", url)
        raw_id = m.group(1) if m else ""
    if raw_id and ("egx.com.eg" in url or not url):
        return "egx:" + raw_id
    if url:
        return "url:" + _sha(url)[:16]
    return "notitle:" + _sha(
        (item.get("title") or "") + (item.get("date") or ""))[:16]


def extract_document(item, quarter_start=QUARTER_START,
                     quarter_end=QUARTER_END):
    """One harvested disclosure item -> list of events (0..n).

    Returns [] for non-events. A document whose figures live only in
    an unharvested attachment yields a CANDIDATE, never a verified
    event and never silence about the gap.
    """
    title = str(item.get("title") or "")
    body = str(item.get("body") or "")
    raw = title + "\n" + body
    norm = norm_digits(raw)
    url = item.get("url") or item.get("resolved_url") or ""
    doc_id = _doc_id(item)
    doc_rev = "clipped-body-sha256:" + _sha(body)
    issuer = _issuer(title, body, url)
    ann_val, ann_s, ann_e, ann_basis = _announced(
        norm, raw, item.get("date"))
    ann_ev = (_span(norm, ann_s, ann_e, raw)
              if ann_s is not None else None)
    if ann_ev:
        ann_ev["field"] = "announced"
    announced = _date_field(ann_val, ann_basis, ann_ev)
    evidence = []
    if ann_ev:
        evidence.append(ann_ev)
    low = norm.lower()
    events = []
    if any(w in low for w in _DIV_TRIGGERS):
        ev = _extract_dividend(item, norm, raw, issuer, announced,
                               doc_id, doc_rev, url, list(evidence))
        events.append(ev)
    if any(w in low for w in _EARN_TRIGGERS):
        ev = _extract_earnings(item, norm, raw, issuer, announced,
                               doc_id, doc_rev, url, list(evidence))
        events.append(ev)
    if any(w in low for w in _BOARD_TRIGGERS):
        ev = _extract_board(item, norm, raw, issuer, announced,
                            doc_id, doc_rev, url, list(evidence))
        if ev is not None:
            events.append(ev)
    for ev in events:
        ann = ev["announced"]["value"]
        if ann:
            try:
                d = date(*[int(x) for x in ann.split("-")])
                ev["stale"] = d < quarter_start or d > quarter_end
            except ValueError:
                ev["stale"] = True
    # Issuer guard: a title naming one ticker with a body naming
    # another is a mismatch, not an event for either — downgrade every
    # event from this document to candidate.
    title_ticker_m = re.search(r"\b([A-Z]{3,5}\.CA)\b", title)
    body_ticker_m = re.search(r"\b([A-Z]{3,5}\.CA)\b", body)
    if (title_ticker_m and body_ticker_m
            and title_ticker_m.group(1) != body_ticker_m.group(1)):
        for ev in events:
            ev["issuer_mismatch"] = {
                "title_ticker": title_ticker_m.group(1),
                "body_ticker": body_ticker_m.group(1)}
            ev["candidate_reasons"].append(
                "issuer mismatch: title %s vs body %s"
                % (title_ticker_m.group(1), body_ticker_m.group(1)))
            ev["extraction_status"] = "candidate"
            ev["verification_status"] = "unverified"
    return events


def extract_feed(items, quarter_start=QUARTER_START,
                 quarter_end=QUARTER_END):
    """A feed (harvest disclosures.json items) -> events + run report.

    Dedup: a second document with the same source_document_id is a
    duplicate of the first (same harvest re-posted); a different
    document describing the same payload gets an explicit
    possible_duplicate link on the later event — never merged.
    """
    events, seen_docs, seen_payloads = [], {}, {}
    n_docs = n_dup_docs = 0
    for item in items or []:
        n_docs += 1
        doc_id = _doc_id(item)
        if doc_id in seen_docs:
            n_dup_docs += 1
            continue
        seen_docs[doc_id] = True
        for ev in extract_document(item, quarter_start, quarter_end):
            ident = None
            if ev["event_type"] == "dividend":
                # #131 tolerance: 1.89 / 1.9 / 1.8999999998 is one
                # coupon — link on (ticker, coupon, amount-within-
                # noise), not on the exact reported string.
                cpn = ev["payload"].get("coupon_number")
                amt = ev["payload"]["amount_per_share"]["value"]
                if cpn and amt:
                    for seen in seen_payloads.get("dividend", []):
                        if (seen[0] == ev["issuer"].get("ticker")
                                and seen[1] == cpn
                                and _dps_same(seen[2], amt)):
                            ev["duplicate_links"].append({
                                "type": "possible_duplicate",
                                "of_event_id": seen[3],
                                "basis": "same issuer/coupon, amount "
                                         "within #131 reporting noise; "
                                         "not merged"})
                            break
                    else:
                        seen_payloads.setdefault("dividend", []).append(
                            (ev["issuer"].get("ticker"), cpn, amt,
                             ev["event_id"]))
            elif ev["event_type"] == "earnings":
                bas = ev["payload"].get("basis")
                pend = ev["payload"]["period_end"]["value"]
                if bas and pend:
                    ident = (ev["issuer"].get("ticker"), "earnings",
                             bas, pend)
            else:
                dsub = ev["payload"].get("decision_subtype")
                dval = (ev["payload"]["meeting_date"]["value"]
                        or ev["payload"]["assembly_date"]["value"])
                if dsub and dval:
                    ident = (ev["issuer"].get("ticker"), "board_decision",
                             dsub, dval)
            # Incomplete identity never links: two dateless candidates
            # are not the same event.
            if ident is not None and ident in seen_payloads:
                ev["duplicate_links"].append({
                    "type": "possible_duplicate",
                    "of_event_id": seen_payloads[ident],
                    "basis": "same issuer/type/payload-identity, "
                             "different source document; not merged"})
            elif ident is not None:
                seen_payloads[ident] = ev["event_id"]
            events.append(ev)
    by_status = {}
    for ev in events:
        by_status[ev["extraction_status"]] = \
            by_status.get(ev["extraction_status"], 0) + 1
    report = {"documents": n_docs, "duplicate_documents": n_dup_docs,
              "events": len(events),
              "by_type": {}, "by_extraction_status": by_status,
              "by_verification_status": {}, "stale": 0,
              "duplicate_links": 0,
              "candidates": by_status.get("candidate", 0),
              "with_reasons": 0}
    for ev in events:
        report["by_type"][ev["event_type"]] = \
            report["by_type"].get(ev["event_type"], 0) + 1
        report["by_verification_status"][ev["verification_status"]] = \
            report["by_verification_status"].get(
                ev["verification_status"], 0) + 1
        report["stale"] += 1 if ev["stale"] else 0
        report["duplicate_links"] += len(ev["duplicate_links"])
        report["with_reasons"] += 1 if ev["candidate_reasons"] else 0
    return events, report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("extract")
    p.add_argument("input")
    p.add_argument("--out", default=None)
    p.add_argument("--quarter-start", default=QUARTER_START.isoformat())
    p.add_argument("--quarter-end", default=QUARTER_END.isoformat())
    sub.add_parser("check")
    args = ap.parse_args(argv)
    if args.cmd == "check":
        print("schema_version=%d extractor=%s config_hash=%s"
              % (SCHEMA_VERSION, EXTRACTOR_VERSION, CONFIG_HASH))
        return 0
    qs = date(*[int(x) for x in args.quarter_start.split("-")])
    qe = date(*[int(x) for x in args.quarter_end.split("-")])
    with open(args.input, encoding="utf-8") as f:
        data = json.load(f)
    items = data.get("items", data) if isinstance(data, dict) else data
    events, report = extract_feed(items, qs, qe)
    out = {"schema_version": SCHEMA_VERSION,
           "extractor_version": EXTRACTOR_VERSION,
           "config_hash": CONFIG_HASH,
           "quarter": {"start": qs.isoformat(), "end": qe.isoformat()},
           "report": report, "events": events}
    _assert_no_float(out)
    text = json.dumps(out, ensure_ascii=False, indent=1,
                      sort_keys=True) + "\n"
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
    else:
        sys.stdout.write(text)
    print("extracted %d events from %d documents "
          "(%d duplicate documents skipped)"
          % (report["events"], report["documents"],
             report["duplicate_documents"]), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
