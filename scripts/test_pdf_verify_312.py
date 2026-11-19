#!/usr/bin/env python3
"""Tests: pdf_verify bidirectional association + evidence semantics
(issue #312, follow-up to the #308 live run).

Covers scripts/pdf_verify.py 1.1.0 + scripts/pdf_text.py mode
propagation + disclosure_events.find_dates_explicit_year against
the #301 suite's fixture builders (imported, not duplicated).

The #308 live-run artefacts (/tmp/tick2045-308) were lost when the
VM's tmpfs was wiped mid-day, so the real 297436 extracted page
text could not be retained hash-bound; the 297436 regression PDF
below is rebuilt from the REAL harvested body wording (in-repo
scripts/disclosure_events_fixtures/fixtures.json,
candidate_poul_board) plus the month-name date form the live run
reported ("11 نوفمبر 2026"). It is marked as such.

Run: python3 scripts/test_pdf_verify_312.py
  (needs pypdf — the scratch-312 venv has 7.1.1)
  or: python3 -m pytest scripts/test_pdf_verify_312.py -q
"""
import hashlib
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
_TMP = tempfile.mkdtemp(prefix="gator312-test-")

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


v301 = _load("test_pdf_verify_301_under_test",
             os.path.join(_HERE, "test_pdf_verify_301.py"))
make_pdf = v301.make_pdf
make_pdf_ar = v301.make_pdf_ar
pointer = v301.pointer
loader_for = v301.loader_for


def make_pdf_lines(pages):
    """Arabic PDF like v301.make_pdf_ar, but each line sits at its
    own y (720 - 20*j) so pypdf layout mode emits real line breaks.
    The 301 builders put every line at y=720, so layout mode
    concatenates them with no separator — useless for the row
    discipline these tests pin (one row's value must not satisfy
    the next row's label)."""
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
            b"BT /F1 12 Tf 72 %d Td (" % (720 - 20 * j) + enc(ln)
            + b") Tj ET" for j, ln in enumerate(lines))
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
    return v301._assemble(objs)
pdf_verify = v301.pdf_verify
pdf_text = v301.pdf_text
disclosure_events = v301.disclosure_events
dividend_event = v301.dividend_event
earnings_event = v301.earnings_event
_field = v301._field

FIXTURES = json.loads(
    (Path(_REPO) / "scripts" / "disclosure_events_fixtures"
     / "fixtures.json").read_text(encoding="utf-8"))
CASES = {c["name"]: c["doc"] for c in FIXTURES["cases"]}


def _verify(ev, pdf_bytes, name="297291.pdf"):
    return pdf_verify.verify_event(
        ev, [pointer(pdf_bytes, name)], _TMP,
        loader_for({"attachments/" + name: pdf_bytes}))


def _board_event(meeting="2026-11-11", announced="2026-11-12"):
    return {
        "event_id": "ev_test_board", "event_type": "board_decision",
        "source_document_id": "egx:297436",
        "announced": {"value": announced, "basis": "verbatim",
                      "evidence": None, "derived_candidate": None,
                      "derived_rule": None},
        "payload": {
            "meeting_date": {"value": meeting, "basis": "verbatim",
                             "evidence": None, "derived_candidate": None,
                             "derived_rule": None},
            "assembly_date": {"value": None},
        }}


@unittest.skipUnless(HAVE_PYPDF, "pypdf not installed")
class TestValueBeforeLabel(unittest.TestCase):
    def test_value_first_coupon_amount_verifies(self):
        pdf = make_pdf_lines([[
            "1.9 جنيه مصري قيمة الكوبون",
            "42 رقم الكوبون",
            "16/11/2026 تاريخ تحريك الحدود السعرية",
            "17/11/2026 تاريخ نهاية الحق",
            "18/11/2026 تاريخ التوزيع",
            "القاهرة في 10/11/2026"]])
        res = _verify(dividend_event(), pdf)
        self.assertEqual(res["status"], "verified", res)
        amt = _field(res, "amount_per_share")
        self.assertEqual(amt["outcome"], "verified")
        self.assertEqual(amt["label"], "قيمة الكوبون")
        self.assertIn("1.9", amt["quote"])
        self.assertEqual(_field(res, "coupon_number")["outcome"],
                         "verified")

    def test_value_first_ex_date_and_entitlement_verify(self):
        pdf = make_pdf_lines([[
            "قيمة الكوبون 1.9 جنيه مصري",
            "42 رقم الكوبون",
            "16/11/2026 تاريخ تحريك الحدود السعرية",
            "17/11/2026 تاريخ نهاية الحق",
            "18/11/2026 تاريخ التوزيع",
            "القاهرة في 10/11/2026"]])
        res = _verify(dividend_event(), pdf)
        self.assertEqual(res["status"], "verified", res)
        self.assertEqual(_field(res, "ex_date")["outcome"], "verified")
        self.assertEqual(_field(res, "entitlement_end")["outcome"],
                         "verified")

    def test_mixed_arabic_value_first_english_label_first(self):
        pdf = make_pdf_lines([[
            "1.9 جنيه مصري قيمة الكوبون",
            "Coupon number: 42",
            "Ex-date: 16/11/2026",
            "Entitlement ends: 17/11/2026",
            "Distribution date: 18/11/2026",
            "Cairo, 10/11/2026"]])
        res = _verify(dividend_event(), pdf)
        self.assertEqual(res["status"], "verified", res)
        self.assertEqual(_field(res, "amount_per_share")["outcome"],
                         "verified")
        self.assertEqual(_field(res, "ex_date")["outcome"], "verified")

    def test_wrapped_rows_both_directions(self):
        # Label-first wrapped: value on the labelless line below.
        pdf1 = make_pdf_lines([[
            "قيمة الكوبون",
            "1.9 جنيه مصري",
            "رقم الكوبون: 42",
            "تاريخ تحريك الحدود السعرية: 16/11/2026",
            "تاريخ نهاية الحق: 17/11/2026",
            "تاريخ التوزيع: 18/11/2026",
            "القاهرة في 10/11/2026"]])
        res1 = _verify(dividend_event(), pdf1)
        self.assertEqual(_field(res1, "amount_per_share")["outcome"],
                         "verified", res1)
        # Value-first wrapped: value on the labelless line above.
        pdf2 = make_pdf_lines([[
            "1.9 جنيه مصري",
            "قيمة الكوبون",
            "رقم الكوبون: 42",
            "تاريخ تحريك الحدود السعرية: 16/11/2026",
            "تاريخ نهاية الحق: 17/11/2026",
            "تاريخ التوزيع: 18/11/2026",
            "القاهرة في 10/11/2026"]])
        res2 = _verify(dividend_event(), pdf2)
        self.assertEqual(_field(res2, "amount_per_share")["outcome"],
                         "verified", res2)

    def test_multi_column_shared_lines(self):
        pdf = make_pdf_lines([[
            "قيمة الكوبون 1.9    تاريخ التوزيع 18/11/2026",
            "رقم الكوبون 42    تاريخ نهاية الحق 17/11/2026",
            "تاريخ تحريك الحدود السعرية 16/11/2026",
            "القاهرة في 10/11/2026"]])
        res = _verify(dividend_event(), pdf)
        self.assertEqual(res["status"], "verified", res)
        # Value-first columns on one shared line.
        pdf2 = make_pdf_lines([[
            "1.9 قيمة الكوبون    18/11/2026 تاريخ التوزيع",
            "42 رقم الكوبون    17/11/2026 تاريخ نهاية الحق",
            "16/11/2026 تاريخ تحريك الحدود السعرية",
            "القاهرة في 10/11/2026"]])
        res2 = _verify(dividend_event(), pdf2)
        self.assertEqual(res2["status"], "verified", res2)

    def test_repeated_labels_first_occurrence_wins(self):
        pdf = make_pdf_lines([[
            "قيمة الكوبون 1.9",
            "قيمة الكوبون 1.85",
            "رقم الكوبون: 42",
            "تاريخ تحريك الحدود السعرية: 16/11/2026",
            "تاريخ نهاية الحق: 17/11/2026",
            "تاريخ التوزيع: 18/11/2026",
            "القاهرة في 10/11/2026"]])
        res = _verify(dividend_event(), pdf)
        self.assertEqual(_field(res, "amount_per_share")["outcome"],
                         "verified")
        self.assertEqual(_field(res, "amount_per_share")
                         ["value_found"], "1.9")

    def test_value_first_period_range_verifies(self):
        pdf = make_pdf_lines([[
            "صافي الربح: 63,079,356 (القيمة بالألف)",
            "صافي الربح لفترة المقارنة: 62,100,264 (القيمة بالألف)",
            "من 01/01/2026 إلى 30/09/2026 القوائم المالية المجمعة "
            "عن الفترة",
            "10/11/2026"]])
        res = _verify(earnings_event(), pdf)
        self.assertEqual(_field(res, "period_start")["outcome"],
                         "verified", res)
        self.assertEqual(_field(res, "period_end")["outcome"],
                         "verified", res)

    def test_value_first_pdf_only_candidate(self):
        pdf = make_pdf_lines([[
            "صافي الربح: 63,079,356 (القيمة بالألف)",
            "صافي الربح لفترة المقارنة: 62,100,264 (القيمة بالألف)",
            "12,600,000,000 الإيرادات",
            "القوائم المالية المجمعة عن الفترة: من 01/01/2026 إلى "
            "30/09/2026",
            "10/11/2026"]])
        res = _verify(earnings_event(revenue=None), pdf)
        cands = [c for c in res["pdf_only_fields"]
                 if c["field"] == "revenue"]
        self.assertEqual(len(cands), 1)
        self.assertEqual(cands[0]["value"], "12600000000")


@unittest.skipUnless(HAVE_PYPDF, "pypdf not installed")
class TestSwapAndRowDiscipline(unittest.TestCase):
    def test_swapped_value_first_dates_never_verify(self):
        pdf = make_pdf_lines([[
            "18/11/2026 تاريخ تحريك الحدود السعرية",
            "16/11/2026 تاريخ التوزيع",
            "17/11/2026 تاريخ نهاية الحق",
            "قيمة الكوبون 1.9",
            "القاهرة في 10/11/2026"]])
        res = _verify(dividend_event(), pdf)
        self.assertEqual(res["status"], "mismatch", res)
        ex = _field(res, "ex_date")
        self.assertEqual(ex["outcome"], "wrong_role")
        self.assertEqual(ex["found_in_role"], "payout_date")
        pay = _field(res, "payout_date")
        self.assertEqual(pay["outcome"], "wrong_role")
        self.assertEqual(pay["found_in_role"], "ex_date")

    def test_previous_row_value_cannot_satisfy_next_label(self):
        pdf = make_pdf_lines([[
            "16/11/2026 تاريخ التوزيع",
            "تاريخ تحريك الحدود السعرية",
            "القاهرة في 10/11/2026"]])
        ev = dividend_event(ex="2026-11-16", payout=None, ent=None,
                            amount=None, coupon=None,
                            announced=None)
        res = _verify(ev, pdf)
        self.assertEqual(_field(res, "ex_date")["outcome"], "not_found",
                         res)
        self.assertNotEqual(res["status"], "mismatch")

    def test_swapped_value_first_npat_roles_are_mismatch(self):
        pdf = make_pdf_lines([[
            "62,100,264 صافي الربح (القيمة بالألف)",
            "63,079,356 صافي الربح لفترة المقارنة (القيمة بالألف)",
            "القوائم المالية المجمعة عن الفترة: من 01/01/2026 إلى "
            "30/09/2026",
            "10/11/2026"]])
        ev = earnings_event()
        res = _verify(ev, pdf)
        npat = _field(res, "npat")
        self.assertEqual(npat["outcome"], "wrong_role", res)
        self.assertEqual(npat["found_in_role"], "npat_comparative")
        self.assertEqual(res["status"], "mismatch", res)

    def test_value_first_npat_keeps_own_values(self):
        pdf = make_pdf_lines([[
            "63,079,356 صافي الربح (القيمة بالألف)",
            "62,100,264 صافي الربح لفترة المقارنة (القيمة بالألف)",
            "القوائم المالية المجمعة عن الفترة: من 01/01/2026 إلى "
            "30/09/2026",
            "10/11/2026"]])
        res = _verify(earnings_event(), pdf)
        self.assertEqual(res["status"], "verified", res)
        self.assertEqual(_field(res, "npat")["outcome"], "verified")
        self.assertEqual(_field(res, "npat_comparative")["outcome"],
                         "verified")


@unittest.skipUnless(HAVE_PYPDF, "pypdf not installed")
class TestConflictAbstention(unittest.TestCase):
    def test_labelless_line_between_two_labels_abstains(self):
        # 16/11 sits on a labelless line between the payout label
        # above and the ex-date label below: genuinely ambiguous.
        pdf = make_pdf_lines([[
            "تاريخ التوزيع",
            "16/11/2026",
            "تاريخ تحريك الحدود السعرية",
            "القاهرة في 10/11/2026"]])
        ev = dividend_event(ex="2026-11-16", payout=None, ent=None,
                            amount=None, coupon=None, announced=None)
        res = _verify(ev, pdf)
        self.assertEqual(_field(res, "ex_date")["outcome"],
                         "unresolved", res)
        self.assertNotEqual(res["status"], "mismatch")

    def test_conflict_resolves_when_next_label_has_own_value(self):
        # Same layout, but the ex-date label carries its own
        # forward value (17/11): 16/11 belongs to payout.
        pdf = make_pdf_lines([[
            "تاريخ التوزيع",
            "16/11/2026",
            "تاريخ تحريك الحدود السعرية 17/11/2026",
            "القاهرة في 10/11/2026"]])
        ev = dividend_event(ex="2026-11-16", payout=None, ent=None,
                            amount=None, coupon=None, announced=None)
        res = _verify(ev, pdf)
        self.assertEqual(_field(res, "ex_date")["outcome"],
                         "wrong_role", res)
        self.assertEqual(_field(res, "ex_date")["found_in_role"],
                         "payout_date")


@unittest.skipUnless(HAVE_PYPDF, "pypdf not installed")
class TestEvidenceSemantics(unittest.TestCase):
    def test_unprinted_ex_date_is_partial_not_mismatch(self):
        # 296893 bulletin: value date + distribution printed, the
        # ex-date (market mechanics) nowhere in the PDF.
        pdf = make_pdf_lines([[
            "قيمة الكوبون 1.9 جنيه",
            "رقم الكوبون 42",
            "تاريخ التوزيع 18/11/2026",
            "تاريخ نهاية الحق 17/11/2026",
            "القاهرة في 02/11/2026"]])
        res = _verify(dividend_event(), pdf)
        self.assertEqual(_field(res, "ex_date")["outcome"], "not_found",
                         res)
        self.assertEqual(res["status"], "partial", res)

    def test_same_date_under_another_role_is_not_a_contradiction(self):
        # The ex-date value sits only in the payout window and the
        # ex-date label states nothing: uncorroborated, not a
        # mismatch.
        pdf = make_pdf_lines([[
            "قيمة الكوبون 1.9 جنيه",
            "رقم الكوبون 42",
            "تاريخ التوزيع 16/11/2026",
            "تاريخ نهاية الحق 17/11/2026",
            "القاهرة في 02/11/2026"]])
        ev = dividend_event(ex="2026-11-16", payout="2026-11-18",
                            ent="2026-11-15", amount="1.9",
                            coupon="42", announced="2026-11-02")
        res = _verify(ev, pdf)
        self.assertEqual(_field(res, "ex_date")["outcome"], "not_found",
                         res)
        self.assertNotEqual(res["status"], "mismatch", res)

    def test_announced_date_on_page_2_does_not_verify(self):
        # No announced label anywhere: the date sits bare on page 2.
        pdf = make_pdf_lines([
            ["نص طويل بدون تاريخ معلن " + "x " * 200],
            ["تقرير آخر بتاريخ 10/11/2026"]])
        ev = dividend_event(ex=None, payout=None, ent=None,
                            amount=None, coupon=None,
                            announced="2026-11-10")
        res = _verify(ev, pdf)
        self.assertEqual(_field(res, "announced")["outcome"],
                         "not_found", res)

    def test_bare_date_on_page_2_top_does_not_verify_announced(self):
        pdf = make_pdf_lines([
            ["نص " * 100],
            ["10/11/2026 " + "نص " * 100]])
        ev = dividend_event(ex=None, payout=None, ent=None,
                            amount=None, coupon=None,
                            announced="2026-11-10")
        res = _verify(ev, pdf)
        self.assertEqual(_field(res, "announced")["outcome"],
                         "not_found", res)

    def test_announced_date_on_page_1_still_verifies(self):
        pdf = make_pdf_lines([
            ["القاهرة في 10/11/2026 تقرير"],
            ["نص آخر 11/11/2026"]])
        ev = dividend_event(ex=None, payout=None, ent=None,
                            amount=None, coupon=None,
                            announced="2026-11-10")
        res = _verify(ev, pdf)
        self.assertEqual(_field(res, "announced")["outcome"],
                         "verified", res)
        # The genuine date label wins over the header heuristic.
        self.assertEqual(_field(res, "announced")["label"],
                         "القاهرة في")


@unittest.skipUnless(HAVE_PYPDF, "pypdf not installed")
class TestMonthNameDates(unittest.TestCase):
    def test_yearless_month_name_date_does_not_verify(self):
        pdf = make_pdf_lines([[
            "قرارات مجلس إدارة الشركة بجلسته المنعقدة بتاريخ "
            "11 نوفمبر",
            "القاهرة في 12/11/2026"]])
        res = _verify(_board_event(), pdf)
        self.assertEqual(_field(res, "meeting_date")["outcome"],
                         "not_found", res)
        self.assertEqual(_field(res, "announced")["outcome"],
                         "verified", res)

    def test_month_name_date_with_year_verifies(self):
        pdf = make_pdf_lines([[
            "قرارات مجلس إدارة الشركة بجلسته المنعقدة بتاريخ "
            "11 نوفمبر 2026",
            "القاهرة في 12/11/2026"]])
        res = _verify(_board_event(), pdf)
        self.assertEqual(res["status"], "verified", res)
        self.assertEqual(_field(res, "meeting_date")["outcome"],
                         "verified")

    def test_english_month_name_date_with_year_verifies(self):
        pdf = make_pdf([[
            "Board meeting held on 11 November 2026",
            "Cairo, 12/11/2026"]])
        res = _verify(_board_event(), pdf)
        self.assertEqual(_field(res, "meeting_date")["outcome"],
                         "verified", res)

    def test_real_297436_body_extracts_and_pdf_verifies(self):
        # Real harvested body (fixtures.json, candidate_poul_board)
        # extracts the meeting date; the regression PDF is rebuilt
        # from the body's wording with the month-name date form
        # the #308 live run reported on the real bulletin.
        doc = CASES["candidate_poul_board"]
        events = disclosure_events.extract_document(doc)
        boards = [e for e in events
                  if e["event_type"] == "board_decision"]
        self.assertEqual(len(boards), 1)
        ev = boards[0]
        self.assertEqual(ev["payload"]["meeting_date"]["value"],
                         "2026-11-11")
        pdf = make_pdf_lines([[
            "القاهرة للدواجن",
            "قرارات مجلس إدارة الشركة بجلسته المنعقدة بتاريخ "
            "11 نوفمبر 2026",
            "القاهرة في 12/11/2026"]])
        res = _verify(ev, pdf, name="297436.pdf")
        self.assertEqual(res["status"], "verified", res)
        self.assertEqual(_field(res, "meeting_date")["outcome"],
                         "verified")


class TestYearlessPolicy(unittest.TestCase):
    def test_extractor_keeps_default_year(self):
        # Body extraction is unchanged: the 2026 default is a
        # convenience for the extractor, not verification evidence.
        found = disclosure_events.find_dates("اجتماع 15 نوفمبر")
        self.assertTrue(any(d.isoformat() == "2026-11-15"
                            for d, _, _ in found))

    def test_explicit_year_finder_excludes_yearless(self):
        self.assertEqual(
            disclosure_events.find_dates_explicit_year(
                "اجتماع 15 نوفمبر"), [])
        found = disclosure_events.find_dates_explicit_year(
            "اجتماع 15 نوفمبر 2026")
        self.assertTrue(any(d.isoformat() == "2026-11-15"
                            for d, _, _ in found))
        found2 = disclosure_events.find_dates_explicit_year(
            "November 15, 2026")
        self.assertTrue(any(d.isoformat() == "2026-11-15"
                            for d, _, _ in found2))


@unittest.skipUnless(HAVE_PYPDF, "pypdf not installed")
class TestModeAndConfig(unittest.TestCase):
    def test_extraction_mode_recorded_on_pages_and_results(self):
        res = pdf_text.extract_pages(v301.PDF_AR_COMI)
        self.assertEqual(res["status"], "ok")
        self.assertEqual(res["pages"][0]["mode"], "layout")
        out = _verify(earnings_event(), v301.PDF_AR_COMI)
        self.assertEqual(_field(out, "npat")["extraction_mode"],
                         "layout")
        self.assertEqual(_field(out, "npat")["text_variant"], "logical")

    def test_plain_mode_variants_restore_logical_order(self):
        page = {"page": 1, "text": "حبرلا يفاص", "mode": "plain"}
        variants = dict(pdf_verify._page_variants(page))
        self.assertEqual(variants["logical-restored"], "صافي الربح")
        self.assertEqual(variants["raw"], "حبرلا يفاص")

    def test_verifier_version_and_config_hash(self):
        self.assertEqual(pdf_verify.VERIFIER_VERSION,
                         "pdf-verify/1.1.0")
        # The 1.0.0 hash covered only the role table + ROLE_WINDOW;
        # the 1.1.0 hash must differ (association, header, scale,
        # period/announced labels all feed it now).
        old_text = json.dumps(pdf_verify._FIELD_ROLES, sort_keys=True,
                              ensure_ascii=False) \
            + "|window=%d" % pdf_verify.ROLE_WINDOW
        old_hash = hashlib.sha256(
            old_text.encode("utf-8")).hexdigest()[:16]
        self.assertNotEqual(pdf_verify.CONFIG_HASH, old_hash)
        self.assertEqual(len(pdf_verify.CONFIG_HASH), 16)


if __name__ == "__main__":
    unittest.main(verbosity=2)
