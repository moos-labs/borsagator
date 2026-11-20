#!/usr/bin/env python3
"""Tests: role-aware PDF-text verification over captured attachments
(issue #301, INS-299 follow-up).

Covers scripts/pdf_verify.py + scripts/pdf_text.py against the
merged #297 plural attachment contract (worker/attachment_capture.py
pointers + verify_attachment hash check). Deterministic, no network,
no live EGX page. Fixture PDFs are built byte-by-byte below:

- make_pdf(): minimal valid PDF 1.4 with a correct xref table, one
  content stream per page (optionally FlateDecode).
- make_pdf_ar(): the same, but Arabic runs are single-byte codes
  mapped to Unicode by an explicit ToUnicode CMap — the mechanism
  real EGX PDFs use for embedded Arabic fonts. (A Helvetica font
  with raw UTF-8 Arabic bytes and no CMap returns mojibake from
  pypdf; that case is tested separately as "unmapped".)

Run: python3 scripts/test_pdf_verify_301.py
  (needs pypdf — pip install -r requirements.txt; PDF-level tests
  skip with a clear message when it is absent, matcher unit tests
  still run)
  or: python3 -m pytest scripts/test_pdf_verify_301.py -q
  or: python3 -m unittest scripts.test_pdf_verify_301 -v

Harness-first: FAILS on pristine main (no pdf_verify/pdf_text
modules) and PASSES on the fixed tree.
"""
import copy
import hashlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_REPO, "worker"))
import _test_tmp  # noqa: E402  (atexit cleanup of scratch dirs, #388)
_TMP = _test_tmp.mkdtemp(prefix="gator301-test-")

try:
    import pypdf  # noqa: F401
    HAVE_PYPDF = True
except ImportError:
    HAVE_PYPDF = False


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


pdf_text = _load("pdf_text_under_test",
                 os.path.join(_HERE, "pdf_text.py"))
pdf_verify = _load("pdf_verify_under_test",
                   os.path.join(_HERE, "pdf_verify.py"))
capture = _load("attachment_capture_under_test",
                os.path.join(_REPO, "worker", "attachment_capture.py"))
disclosure_events = _load(
    "disclosure_events_under_test",
    os.path.join(_HERE, "disclosure_events.py"))
_iso_date_tests = _load(
    "iso_date_tests_under_test",
    os.path.join(_REPO, "worker", "test_egx_harvest_iso_date.py"))
BODY_297291 = _iso_date_tests.BODY_297291
TITLE_297291 = _iso_date_tests.TITLE_297291

DETAIL_URL = "https://www.egx.com.eg/ar/NewsDetails.aspx?NewsID=297291"


# --- Fixture PDF builders -----------------------------------------------

def _pdf_escape(line):
    return line.replace("\\", "\\\\").replace("(", "\\(").replace(
        ")", "\\)")


def _assemble(objs):
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objs, start=1):
        offsets.append(len(out))
        out += ("%d 0 obj\n" % i).encode("ascii") + body + b"\nendobj\n"
    xref_pos = len(out)
    out += ("xref\n0 %d\n" % (len(objs) + 1)).encode("ascii")
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += ("%010d 00000 n \n" % off).encode("ascii")
    out += ("trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
            % (len(objs) + 1, xref_pos)).encode("ascii")
    return bytes(out)


def make_pdf(pages, flate=False):
    """pages: [[line, ...], ...] — ASCII/Latin lines as Tj strings."""
    kids = b" ".join(b"%d 0 R" % (3 + 2 * i)
                     for i in range(len(pages)))
    font_no = 3 + 2 * len(pages)
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [%s] /Count %d >>"
            % (kids, len(pages))]
    for i, lines in enumerate(pages):
        stream = b" ".join(
            ("BT /F1 12 Tf 72 720 Td (%s) Tj ET"
             % _pdf_escape(ln)).encode("utf-8") for ln in lines)
        if flate:
            stream = zlib.compress(stream)
            objs.append(
                b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                b"/Contents %d 0 R /Resources << /Font << /F1 %d 0 R "
                b">> >> >>" % (4 + 2 * i, font_no))
            objs.append(
                b"<< /Length %d /Filter /FlateDecode >>\nstream\n%s\n"
                b"endstream" % (len(stream), stream))
        else:
            objs.append(
                b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                b"/Contents %d 0 R /Resources << /Font << /F1 %d 0 R "
                b">> >> >>" % (4 + 2 * i, font_no))
            objs.append(
                b"<< /Length %d >>\nstream\n%s\nendstream"
                % (len(stream), stream))
    objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    return _assemble(objs)


def make_pdf_ar(pages):
    """Arabic pages via an explicit ToUnicode CMap (see module
    docstring). pages: [[line, ...], ...]; lines may mix Arabic,
    digits and dates."""
    chars = sorted({ch for pg in pages for ln in pg for ch in ln
                    if ord(ch) > 127})
    code = {ch: 0x80 + i for i, ch in enumerate(chars)}

    def enc(ln):
        out = bytearray()
        for ch in ln:
            o = ord(ch)
            if o > 127:
                out.append(code[ch])
            elif ch in "()\\":
                out += b"\\" + ch.encode()
            else:
                out.append(o)
        return bytes(out)

    bfchar = b"\n".join(b"<%02X> <%04X>" % (code[ch], ord(ch))
                        for ch in chars)
    cmap = (b"/CIDInit /ProcSet findresource begin\n12 dict begin\n"
            b"begincmap\n/CIDSystemInfo << /Registry (Adobe) /Ordering "
            b"(UCS) /Supplement 0 >> def\n/CMapName /Adobe-Identity-UCS "
            b"def\n/CMapType 2 def\n1 begincodespacerange\n<00> <FF>\n"
            b"endcodespacerange\n%d beginbfchar\n%s\nendbfchar\n"
            b"endcmap\nCMapName currentdict /CMap defineresource pop\n"
            b"end\nend" % (len(chars), bfchar))
    kids = b" ".join(b"%d 0 R" % (3 + 2 * i)
                     for i in range(len(pages)))
    font_no = 3 + 2 * len(pages)
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [%s] /Count %d >>"
            % (kids, len(pages))]
    for i, lines in enumerate(pages):
        stream = b" ".join(
            b"BT /F1 12 Tf 72 720 Td (" + enc(ln) + b") Tj ET"
            for ln in lines)
        objs.append(
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Contents %d 0 R /Resources << /Font << /F1 %d 0 R >> "
            b">> >>" % (4 + 2 * i, font_no))
        objs.append(b"<< /Length %d >>\nstream\n%s\nendstream"
                    % (len(stream), stream))
    objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
                b"/Encoding /WinAnsiEncoding /ToUnicode %d 0 R >>"
                % (font_no + 1))
    objs.append(b"<< /Length %d >>\nstream\n%s\nendstream"
                % (len(cmap), cmap))
    return _assemble(objs)


# The COMI 297291 source document, as a ToUnicode Arabic PDF.
PDF_AR_COMI = make_pdf_ar([[
    "صافي الربح: 63,079,356 (القيمة بالألف)",
    "صافي الربح لفترة المقارنة: 62,100,264 (القيمة بالألف)",
    "الإيرادات: 12,600,000,000",
    "القوائم المالية المجمعة عن الفترة: من 01/01/2026 إلى 30/09/2026",
    "10/11/2026"]])
# Same document, Helvetica + raw UTF-8 Arabic, no ToUnicode: pypdf
# returns mojibake for the Arabic — labels are undecodable.
PDF_MOJIBAKE = make_pdf([[
    "صافي الربح: 63,079,356 (القيمة بالألف)",
    "10/11/2026"]])
# English dividend document (coupon 42, POUL-style values).
PDF_EN_DIV = make_pdf([[
    "Coupon number: 42",
    "Coupon value: 1.90 EGP per share",
    "Ex-date: 16/11/2026",
    "Entitlement ends: 17/11/2026",
    "Distribution date: 18/11/2026",
    "Cairo, 10/11/2026"]])
# Same values, ex-date and payout date swapped.
PDF_EN_DIV_SWAPPED = make_pdf([[
    "Coupon number: 42",
    "Coupon value: 1.90 EGP per share",
    "Ex-date: 18/11/2026",
    "Entitlement ends: 17/11/2026",
    "Distribution date: 16/11/2026",
    "Cairo, 10/11/2026"]])
PDF_EN_LOSS_PAREN = make_pdf([["Net profit: (12,500)"]])
PDF_EN_LOSS_MINUS = make_pdf([["Net profit: -12,500"]])
PDF_EN_FLATE = make_pdf([["Net profit: 63,079,356",
                          "Net profit for the comparative period: "
                          "62,100,264"]], flate=True)
PDF_SCANNED = make_pdf([[]])
PDF_EMPTY = make_pdf([[""]])


def pointer(pdf_bytes, name="297291.pdf"):
    return {"status": "captured", "path": "attachments/" + name,
            "sha256": hashlib.sha256(pdf_bytes).hexdigest(),
            "size_bytes": len(pdf_bytes),
            "source_url": "https://www.egx.com.eg/a.pdf",
            "reason": None}


def loader_for(mapping):
    """loader(archive_root, pointer) -> (bytes|None, reason)."""
    def load(root, ptr):
        data = mapping.get(ptr.get("path"))
        if data is None:
            return None, "stored file missing"
        return data, ""
    return load


def _money(value, scale="one"):
    return {"value": value, "currency": "EGP", "scale": scale,
            "raw": value, "evidence": None}


def _date(value):
    return {"value": value, "basis": "verbatim", "evidence": None,
            "derived_candidate": None, "derived_rule": None}


def earnings_event(npat="63079356", npat_scale="thousand",
                   comp="62100264", revenue=None,
                   period_start="2026-01-01", period_end="2026-09-30",
                   announced="2026-11-10"):
    return {
        "event_id": "ev_test_earnings", "event_type": "earnings",
        "source_document_id": "egx:297291",
        "announced": _date(announced) if announced else {"value": None},
        "payload": {
            "period_start": _date(period_start) if period_start
            else {"value": None},
            "period_end": _date(period_end) if period_end
            else {"value": None},
            "basis": "consolidated",
            "npat": _money(npat, npat_scale) if npat else {"value": None},
            "npat_comparative": _money(comp, npat_scale) if comp
            else {"value": None},
            "revenue": _money(revenue) if revenue else {"value": None},
        }}


def dividend_event(ex="2026-11-16", payout="2026-11-18",
                   ent="2026-11-17", amount="1.9", coupon="42",
                   announced="2026-11-10"):
    return {
        "event_id": "ev_test_dividend", "event_type": "dividend",
        "source_document_id": "egx:297291",
        "announced": _date(announced) if announced else {"value": None},
        "payload": {
            "coupon_number": coupon,
            "amount_per_share": _money(amount) if amount
            else {"value": None},
            "ex_date": _date(ex) if ex else {"value": None},
            "entitlement_end": _date(ent) if ent else {"value": None},
            "payout_date": _date(payout) if payout else {"value": None},
            "record_date": {"value": None},
        }}


def _field(result, name):
    for f in result["fields"]:
        if f["field"] == name:
            return f
    raise AssertionError("no field %r in %r" % (name, result["fields"]))


@unittest.skipUnless(HAVE_PYPDF, "pypdf not installed")
class TestPdfTextEngine(unittest.TestCase):
    def test_tounicode_arabic_reads_as_arabic(self):
        res = pdf_text.extract_pages(PDF_AR_COMI)
        self.assertEqual(res["status"], "ok")
        self.assertEqual(res["engine"], "pypdf")
        # Layout mode returns Arabic in logical order already.
        text = "\n".join(p["text"] for p in res["pages"])
        self.assertIn("صافي الربح", text)
        self.assertIn("63,079,356", text)
        self.assertIn("من 01/01/2026 إلى 30/09/2026", text)

    def test_restore_inverts_plain_mode_visual_order(self):
        # Plain-mode pypdf output reverses each RTL run; the
        # restorer inverts exactly that.
        self.assertEqual(pdf_text.restore_logical_order("حبرلا يفاص"),
                         "صافي الربح")

    def test_rtl_restore_is_a_noop_on_latin(self):
        self.assertEqual(pdf_text.restore_logical_order(
            "Net profit: 100"), "Net profit: 100")

    def test_flate_stream_reads(self):
        res = pdf_text.extract_pages(PDF_EN_FLATE)
        self.assertEqual(res["status"], "ok")
        self.assertIn("63,079,356",
                      "\n".join(p["text"] for p in res["pages"]))

    def test_scanned_pdf_is_scanned_not_empty(self):
        res = pdf_text.extract_pages(PDF_SCANNED)
        self.assertEqual(res["status"], "scanned")
        self.assertEqual(res["pages"][0]["text"], "")

    def test_mojibake_pdf_is_partial_unmapped(self):
        res = pdf_text.extract_pages(PDF_MOJIBAKE)
        self.assertEqual(res["status"], "partial")
        self.assertIn("ToUnicode", res["detail"])

    def test_non_pdf_is_unreadable(self):
        res = pdf_text.extract_pages(b"<html>not a pdf</html>")
        self.assertEqual(res["status"], "unreadable")

    def test_oversize_is_unreadable(self):
        old = pdf_text.MAX_PDF_BYTES
        pdf_text.MAX_PDF_BYTES = 10
        try:
            res = pdf_text.extract_pages(PDF_EN_DIV)
        finally:
            pdf_text.MAX_PDF_BYTES = old
        self.assertEqual(res["status"], "unreadable")


@unittest.skipUnless(HAVE_PYPDF, "pypdf not installed")
class TestRoleAwareVerification(unittest.TestCase):
    def test_comi_arabic_event_verified_with_evidence(self):
        ev = earnings_event()
        res = pdf_verify.verify_event(
            ev, [pointer(PDF_AR_COMI)], _TMP,
            loader_for({"attachments/297291.pdf": PDF_AR_COMI}))
        self.assertEqual(res["status"], "verified", res)
        self.assertEqual(_field(res, "npat")["outcome"], "verified")
        self.assertEqual(_field(res, "npat")["page"], 1)
        self.assertIn("63,079,356", _field(res, "npat")["quote"])
        self.assertEqual(_field(res, "npat_comparative")["outcome"],
                         "verified")
        self.assertEqual(_field(res, "period_start")["outcome"],
                         "verified")
        self.assertEqual(_field(res, "period_end")["outcome"], "verified")
        self.assertEqual(_field(res, "announced")["outcome"], "verified")
        self.assertEqual(res["files_checked"][0]["status"], "ok")
        self.assertEqual(res["files_checked"][0]["sha256"],
                         hashlib.sha256(PDF_AR_COMI).hexdigest())

    def test_real_extracted_comi_event_verified(self):
        """End-to-end on the real harvested COMI body: the pilot
        extracts NPAT 63079356 / announced 2026-11-10 from the body,
        and the stored PDF role-verifies them."""
        item = {"id": "297291", "title": TITLE_297291,
                "body": BODY_297291, "date": "2026-11-10",
                "url": DETAIL_URL}
        events = disclosure_events.extract_document(item)
        earnings = [e for e in events if e["event_type"] == "earnings"]
        self.assertEqual(len(earnings), 1)
        ev = earnings[0]
        self.assertEqual(ev["payload"]["npat"]["value"], "63079356")
        res = pdf_verify.verify_event(
            ev, [pointer(PDF_AR_COMI)], _TMP,
            loader_for({"attachments/297291.pdf": PDF_AR_COMI}))
        self.assertEqual(res["status"], "verified", res)

    def test_swapped_dates_are_mismatch_not_verified(self):
        ev = dividend_event()
        res = pdf_verify.verify_event(
            ev, [pointer(PDF_EN_DIV_SWAPPED)], _TMP,
            loader_for({"attachments/297291.pdf": PDF_EN_DIV_SWAPPED}))
        self.assertEqual(res["status"], "mismatch", res)
        ex = _field(res, "ex_date")
        self.assertEqual(ex["outcome"], "wrong_role")
        self.assertEqual(ex["found_in_role"], "payout_date")
        pay = _field(res, "payout_date")
        self.assertEqual(pay["outcome"], "wrong_role")
        self.assertEqual(pay["found_in_role"], "ex_date")
        # The unswapped fields still verify — the swap is localised.
        self.assertEqual(_field(res, "coupon_number")["outcome"],
                         "verified")
        self.assertEqual(_field(res, "entitlement_end")["outcome"],
                         "verified")

    def test_swapped_npat_roles_are_mismatch(self):
        # Event claims the comparative value as the current NPAT
        # (and the current value as the comparative).
        ev = earnings_event(npat="62100264", comp="63079356")
        res = pdf_verify.verify_event(
            ev, [pointer(PDF_AR_COMI)], _TMP,
            loader_for({"attachments/297291.pdf": PDF_AR_COMI}))
        npat = _field(res, "npat")
        self.assertEqual(npat["outcome"], "wrong_role")
        self.assertEqual(npat["found_in_role"], "npat_comparative")
        self.assertEqual(_field(res, "npat_comparative")["outcome"],
                         "wrong_role")

    def test_dividend_unswapped_verifies(self):
        ev = dividend_event()
        res = pdf_verify.verify_event(
            ev, [pointer(PDF_EN_DIV)], _TMP,
            loader_for({"attachments/297291.pdf": PDF_EN_DIV}))
        self.assertEqual(res["status"], "verified", res)
        self.assertEqual(_field(res, "amount_per_share")["outcome"],
                         "verified")

    def test_dividend_amount_tolerance_is_coupon_only(self):
        # #131: 1.89 vs 1.9 is one coupon — amount_per_share only.
        ev = dividend_event(amount="1.89")
        res = pdf_verify.verify_event(
            ev, [pointer(PDF_EN_DIV)], _TMP,
            loader_for({"attachments/297291.pdf": PDF_EN_DIV}))
        self.assertEqual(_field(res, "amount_per_share")["outcome"],
                         "verified")
        # Earnings money has NO such tolerance: 100 != 101.
        ev2 = earnings_event(npat="101", comp=None, revenue=None,
                             period_start=None, period_end=None,
                             announced=None)
        pdf = make_pdf([["Net profit: 100"]])
        res2 = pdf_verify.verify_event(
            ev2, [pointer(pdf)], _TMP,
            loader_for({"attachments/297291.pdf": pdf}))
        self.assertNotEqual(_field(res2, "npat")["outcome"], "verified")

    def test_event_is_not_mutated(self):
        ev = earnings_event()
        before = copy.deepcopy(ev)
        pdf_verify.verify_event(
            ev, [pointer(PDF_AR_COMI)], _TMP,
            loader_for({"attachments/297291.pdf": PDF_AR_COMI}))
        self.assertEqual(ev, before)


@unittest.skipUnless(HAVE_PYPDF, "pypdf not installed")
class TestSignAwareNumerics(unittest.TestCase):
    def test_parenthesised_loss_matches_negative_only(self):
        ev_neg = earnings_event(npat="-12500", npat_scale="one",
                                comp=None, revenue=None,
                                period_start=None, period_end=None,
                                announced=None)
        res = pdf_verify.verify_event(
            ev_neg, [pointer(PDF_EN_LOSS_PAREN)], _TMP,
            loader_for({"attachments/297291.pdf": PDF_EN_LOSS_PAREN}))
        self.assertEqual(_field(res, "npat")["outcome"], "verified")
        ev_pos = earnings_event(npat="12500", npat_scale="one",
                                comp=None, revenue=None,
                                period_start=None, period_end=None,
                                announced=None)
        res2 = pdf_verify.verify_event(
            ev_pos, [pointer(PDF_EN_LOSS_PAREN)], _TMP,
            loader_for({"attachments/297291.pdf": PDF_EN_LOSS_PAREN}))
        self.assertNotEqual(_field(res2, "npat")["outcome"], "verified")
        self.assertEqual(res2["status"], "missing")

    def test_leading_minus_matches_negative(self):
        ev = earnings_event(npat="-12500", npat_scale="one",
                            comp=None, revenue=None,
                            period_start=None, period_end=None,
                            announced=None)
        res = pdf_verify.verify_event(
            ev, [pointer(PDF_EN_LOSS_MINUS)], _TMP,
            loader_for({"attachments/297291.pdf": PDF_EN_LOSS_MINUS}))
        self.assertEqual(_field(res, "npat")["outcome"], "verified")

    def test_scale_mismatch_is_not_a_match(self):
        # Same digits, PDF states millions while the event says
        # thousands — a different magnitude, not a verification.
        ev = earnings_event(npat="63079356", npat_scale="thousand",
                            comp=None, revenue=None,
                            period_start=None, period_end=None,
                            announced=None)
        pdf = make_pdf_ar([["صافي الربح: 63,079,356 (القيمة بالمليون)"]])
        res = pdf_verify.verify_event(
            ev, [pointer(pdf)], _TMP,
            loader_for({"attachments/297291.pdf": pdf}))
        self.assertEqual(_field(res, "npat")["outcome"],
                         "scale_mismatch")
        self.assertEqual(res["status"], "mismatch")


@unittest.skipUnless(HAVE_PYPDF, "pypdf not installed")
class TestPdfOnlyFields(unittest.TestCase):
    def test_revenue_found_only_in_pdf_is_a_candidate(self):
        ev = earnings_event(revenue=None)
        res = pdf_verify.verify_event(
            ev, [pointer(PDF_AR_COMI)], _TMP,
            loader_for({"attachments/297291.pdf": PDF_AR_COMI}))
        self.assertEqual(res["status"], "verified", res)
        cands = [c for c in res["pdf_only_fields"]
                 if c["field"] == "revenue"]
        self.assertEqual(len(cands), 1)
        self.assertEqual(cands[0]["value"], "12600000000")
        self.assertEqual(cands[0]["page"], 1)
        self.assertIn("12,600,000,000", cands[0]["quote"])
        # Candidates are reported, never promoted into the event.
        self.assertIsNone(ev["payload"]["revenue"]["value"])

    def test_record_date_found_only_in_pdf(self):
        ev = dividend_event()
        pdf = make_pdf([["Coupon number: 42",
                         "Coupon value: 1.90 EGP per share",
                         "Ex-date: 16/11/2026",
                         "Entitlement ends: 17/11/2026",
                         "Distribution date: 18/11/2026",
                         "Record date: 19/11/2026",
                         "Cairo, 10/11/2026"]])
        res = pdf_verify.verify_event(
            ev, [pointer(pdf)], _TMP,
            loader_for({"attachments/297291.pdf": pdf}))
        cands = [c for c in res["pdf_only_fields"]
                 if c["field"] == "record_date"]
        self.assertEqual(len(cands), 1)
        self.assertEqual(cands[0]["value"], "2026-11-19")

    def test_pdf_only_absent_when_body_states_the_field(self):
        ev = earnings_event(revenue="12600000000")
        res = pdf_verify.verify_event(
            ev, [pointer(PDF_AR_COMI)], _TMP,
            loader_for({"attachments/297291.pdf": PDF_AR_COMI}))
        self.assertEqual([c for c in res["pdf_only_fields"]
                          if c["field"] == "revenue"], [])
        self.assertEqual(_field(res, "revenue")["outcome"], "verified")


@unittest.skipUnless(HAVE_PYPDF, "pypdf not installed")
class TestPluralAttachmentsAndHash(unittest.TestCase):
    def test_fields_may_verify_across_two_pdfs(self):
        pdf1 = make_pdf([["Net profit: 63,079,356"]])
        pdf2 = make_pdf([["Revenue: 12,600,000,000"]])
        ev = earnings_event(npat="63079356", npat_scale="one",
                            comp=None, revenue="12600000000",
                            period_start=None, period_end=None,
                            announced=None)
        atts = [pointer(pdf1, "297291.pdf"),
                pointer(pdf2, "297291_2.pdf")]
        res = pdf_verify.verify_event(
            ev, atts, _TMP,
            loader_for({"attachments/297291.pdf": pdf1,
                        "attachments/297291_2.pdf": pdf2}))
        self.assertEqual(res["status"], "verified", res)
        self.assertEqual(len(res["files_checked"]), 2)
        self.assertEqual(_field(res, "npat")["page"], 1)
        self.assertEqual(_field(res, "revenue")["page"], 1)

    def test_mixed_captured_and_failed_still_verifies(self):
        atts = [pointer(PDF_EN_DIV),
                {"status": "fetch_failed", "path": None, "sha256": None,
                 "size_bytes": None,
                 "source_url": "https://www.egx.com.eg/b.pdf",
                 "reason": "HTTP 404"}]
        ev = dividend_event()
        res = pdf_verify.verify_event(
            ev, atts, _TMP,
            loader_for({"attachments/297291.pdf": PDF_EN_DIV}))
        self.assertEqual(res["status"], "verified", res)

    def test_hash_mismatch_is_inconclusive_not_verified(self):
        bad = pointer(PDF_EN_DIV)
        bad["sha256"] = hashlib.sha256(b"other bytes").hexdigest()
        ev = dividend_event()
        res = pdf_verify.verify_event(
            ev, [bad], _TMP,
            loader_for({"attachments/297291.pdf": PDF_EN_DIV}))
        self.assertEqual(res["status"], "inconclusive", res)
        self.assertIn("hash", res["files_checked"][0]["detail"])

    def test_tampered_bytes_fail_the_hash(self):
        ev = dividend_event()
        res = pdf_verify.verify_event(
            ev, [pointer(PDF_EN_DIV)], _TMP,
            loader_for({"attachments/297291.pdf": PDF_EN_DIV + b" "}))
        self.assertEqual(res["status"], "inconclusive", res)

    def test_path_escaping_the_archive_root_is_rejected(self):
        root = Path(tempfile.mkdtemp(dir=_TMP))
        (root / "attachments").mkdir()
        (root / "attachments" / "297291.pdf").write_bytes(PDF_EN_DIV)
        ev = dividend_event()
        for bad_path in ("../outside.pdf", "../../etc/passwd",
                         "/etc/passwd"):
            evil = {"status": "captured", "path": bad_path,
                    "sha256": hashlib.sha256(PDF_EN_DIV).hexdigest(),
                    "size_bytes": len(PDF_EN_DIV),
                    "source_url": "https://www.egx.com.eg/a.pdf",
                    "reason": None}
            res = pdf_verify.verify_event(ev, [evil], str(root))
            self.assertEqual(res["status"], "inconclusive", res)
            self.assertIn("escapes", res["files_checked"][0]["detail"])

    def test_missing_file_is_inconclusive(self):
        ev = dividend_event()
        res = pdf_verify.verify_event(
            ev, [pointer(PDF_EN_DIV)], _TMP,
            loader_for({}))
        self.assertEqual(res["status"], "inconclusive", res)


@unittest.skipUnless(HAVE_PYPDF, "pypdf not installed")
class TestStatusesAndCoverage(unittest.TestCase):
    def test_scanned_pdf_is_inconclusive_not_missing(self):
        ev = dividend_event()
        res = pdf_verify.verify_event(
            ev, [pointer(PDF_SCANNED)], _TMP,
            loader_for({"attachments/297291.pdf": PDF_SCANNED}))
        self.assertEqual(res["status"], "inconclusive", res)

    def test_unmapped_arabic_labels_are_inconclusive(self):
        ev = earnings_event()
        res = pdf_verify.verify_event(
            ev, [pointer(PDF_MOJIBAKE)], _TMP,
            loader_for({"attachments/297291.pdf": PDF_MOJIBAKE}))
        # Arabic-label fields are inconclusive (undecodable), never
        # "missing"; the ASCII announced date in the header still
        # verifies, so the event is partial, not wholly inconclusive.
        self.assertEqual(_field(res, "npat")["outcome"], "inconclusive")
        self.assertEqual(_field(res, "period_start")["outcome"],
                         "inconclusive")
        self.assertEqual(_field(res, "announced")["outcome"], "verified")
        self.assertEqual(res["status"], "partial", res)
        self.assertNotIn("missing", [f["outcome"] for f in res["fields"]])

    def test_no_captured_attachment_is_skipped(self):
        ev = dividend_event()
        res = pdf_verify.verify_event(
            ev, [{"status": "no_attachment", "path": None,
                  "sha256": None, "size_bytes": None,
                  "source_url": None, "reason": "none"}], _TMP,
            loader_for({}))
        self.assertEqual(res["status"], "skipped", res)

    def test_no_attachments_key_is_skipped(self):
        ev = dividend_event()
        res = pdf_verify.verify_event(ev, None, _TMP, loader_for({}))
        self.assertEqual(res["status"], "skipped", res)
        self.assertIn("predates", res["detail"])

    def test_event_with_no_checkable_field_is_skipped(self):
        ev = {"event_id": "ev_empty", "event_type": "dividend",
              "source_document_id": "egx:1",
              "announced": {"value": None},
              "payload": {"coupon_number": None,
                          "amount_per_share": {"value": None},
                          "ex_date": {"value": None},
                          "entitlement_end": {"value": None},
                          "payout_date": {"value": None}}}
        res = pdf_verify.verify_event(
            ev, [pointer(PDF_EN_DIV)], _TMP,
            loader_for({"attachments/297291.pdf": PDF_EN_DIV}))
        self.assertEqual(res["status"], "skipped", res)

    def test_missing_value_is_missing_not_verified(self):
        ev = dividend_event(ex="2026-12-25")
        res = pdf_verify.verify_event(
            ev, [pointer(PDF_EN_DIV)], _TMP,
            loader_for({"attachments/297291.pdf": PDF_EN_DIV}))
        self.assertEqual(res["status"], "partial", res)
        self.assertEqual(_field(res, "ex_date")["outcome"], "not_found")

    def test_verify_feed_joins_on_source_document_id(self):
        item = {"id": "297291", "title": TITLE_297291,
                "body": BODY_297291, "date": "2026-11-10",
                "url": DETAIL_URL,
                "attachments": [pointer(PDF_EN_DIV)]}
        results, summary = pdf_verify.verify_feed(
            [dividend_event()], [item], _TMP,
            loader_for({"attachments/297291.pdf": PDF_EN_DIV}))
        self.assertEqual(summary["events"], 1)
        self.assertEqual(summary["verified"], 1)
        self.assertEqual(summary["checked"], 1)
        self.assertEqual(summary["failed"], 0)

    def test_exit_codes(self):
        self.assertEqual(pdf_verify._exit_code(
            {"events": 0, "checked": 0}), 2)
        self.assertEqual(pdf_verify._exit_code(
            {"events": 2, "checked": 0, "skipped": 2}), 2)
        self.assertEqual(pdf_verify._exit_code(
            {"events": 1, "checked": 1, "verified": 1, "failed": 0}), 0)
        self.assertEqual(pdf_verify._exit_code(
            {"events": 1, "checked": 1, "partial": 1, "failed": 1}), 1)


class TestNoPypdfIsInconclusive(unittest.TestCase):
    def test_unsupported_engine_reports_inconclusive(self):
        # Simulate an environment without pypdf: extraction reports
        # "unsupported" and the verifier refuses to call it a pass
        # or a fail.
        real = pdf_text._engine_version
        real2 = pdf_verify.pdf_text._engine_version
        pdf_text._engine_version = lambda: None
        pdf_verify.pdf_text._engine_version = lambda: None
        try:
            res = pdf_text.extract_pages(PDF_EN_DIV)
            self.assertEqual(res["status"], "unsupported")
            ev = dividend_event()
            out = pdf_verify.verify_event(
                ev, [pointer(PDF_EN_DIV)], _TMP,
                loader_for({"attachments/297291.pdf": PDF_EN_DIV}))
            self.assertEqual(out["status"], "inconclusive", out)
        finally:
            pdf_text._engine_version = real
            pdf_verify.pdf_text._engine_version = real2


@unittest.skipUnless(HAVE_PYPDF, "pypdf not installed")
class TestCli(unittest.TestCase):
    def _write(self, name, obj):
        p = Path(tempfile.mkdtemp(dir=_TMP)) / name
        p.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
        return p

    def test_cli_success_exit_0(self):
        root = Path(tempfile.mkdtemp(dir=_TMP))
        (root / "attachments").mkdir()
        (root / "attachments" / "297291.pdf").write_bytes(PDF_EN_DIV)
        item = {"id": "297291", "url": DETAIL_URL,
                "attachments": [pointer(PDF_EN_DIV)]}
        events = self._write("events.json",
                             {"events": [dividend_event()]})
        disc = self._write("disc.json", {"items": [item]})
        out = root / "out.json"
        rc = pdf_verify.main(["verify", str(events), "--disclosures",
                              str(disc), "--archive-root", str(root),
                              "--out", str(out)])
        self.assertEqual(rc, 0)
        data = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(data["summary"]["verified"], 1)

    def test_cli_all_skipped_exits_2(self):
        root = Path(tempfile.mkdtemp(dir=_TMP))
        item = {"id": "297291", "url": DETAIL_URL,
                "attachments": [{"status": "no_attachment", "path": None,
                                 "sha256": None, "size_bytes": None,
                                 "source_url": None, "reason": "none"}]}
        events = self._write("events.json",
                             {"events": [dividend_event()]})
        disc = self._write("disc.json", {"items": [item]})
        rc = pdf_verify.main(["verify", str(events), "--disclosures",
                              str(disc), "--archive-root", str(root)])
        self.assertEqual(rc, 2)

    def test_cli_zero_events_exits_2(self):
        root = Path(tempfile.mkdtemp(dir=_TMP))
        events = self._write("events.json", {"events": []})
        disc = self._write("disc.json", {"items": []})
        rc = pdf_verify.main(["verify", str(events), "--disclosures",
                              str(disc), "--archive-root", str(root)])
        self.assertEqual(rc, 2)

    def test_cli_mismatch_exits_1(self):
        root = Path(tempfile.mkdtemp(dir=_TMP))
        (root / "attachments").mkdir()
        (root / "attachments" / "297291.pdf").write_bytes(
            PDF_EN_DIV_SWAPPED)
        item = {"id": "297291", "url": DETAIL_URL,
                "attachments": [pointer(PDF_EN_DIV_SWAPPED)]}
        events = self._write("events.json",
                             {"events": [dividend_event()]})
        disc = self._write("disc.json", {"items": [item]})
        rc = pdf_verify.main(["verify", str(events), "--disclosures",
                              str(disc), "--archive-root", str(root)])
        self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
