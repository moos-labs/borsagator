#!/usr/bin/env python3
"""Tests: attachment capture at harvest (issue #279, capture-only).

Covers worker/attachment_capture.py (pure, deterministic), the
harvester's per-item step through the same function egx_harvest.py
calls, and worker.py's archive copy of the captured PDFs.

Deterministic replay / fixture: no network, no Playwright, no live
EGX page. The fixture PDF is built byte-by-byte below (a minimal
valid PDF 1.4 with a correct xref table) embedding the real COMI
297291 reported strings, so the acceptance property can be checked
for real: re-reading the stored PDF reproduces the fields
disclosure_events extracts from the harvested body. The fixture
embeds the strings as raw UTF-8 bytes in the content stream — a
production PDF may compress or re-encode text, so
fields_present_in_pdf() is a verification aid, not a parser; the
hash check in verify_attachment() is the binding guarantee.

Harness-first: FAILS on pristine main (no attachment_capture module,
no "attachments" key, no _publish_harvest_attachments) and PASSES on
the fixed tree.

Run: python3 worker/test_attachment_capture_279.py
  or: python3 -m pytest worker/test_attachment_capture_279.py -q
  or: python3 -m unittest worker.test_attachment_capture_279 -v
"""
import hashlib
import importlib.util
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _test_tmp  # noqa: E402  (atexit cleanup of scratch dirs, #388)
_TMP = str(_test_tmp.mkdtemp(prefix="gator279-test-"))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


capture = _load("attachment_capture_under_test",
                os.path.join(_HERE, "attachment_capture.py"))
disclosure_events = _load(
    "disclosure_events_under_test",
    os.path.join(_REPO, "scripts", "disclosure_events.py"))
# Real harvested COMI body (harvest 2026-11-18) — same source as
# worker/test_egx_harvest_iso_date.py; reused, not re-typed.
_iso_date_tests = _load(
    "iso_date_tests_under_test",
    os.path.join(_HERE, "test_egx_harvest_iso_date.py"))
BODY_297291 = _iso_date_tests.BODY_297291
TITLE_297291 = _iso_date_tests.TITLE_297291

# worker.py import (for _publish_harvest_attachments) needs a
# GATOR_ROOT, as in worker/test_worker_278.py.
os.environ["GATOR_ROOT"] = _TMP
sys.path.insert(0, _HERE)
import worker  # noqa: E402


def _pdf_escape(line):
    return line.replace("\\", "\\\\").replace("(", "\\(").replace(
        ")", "\\)")


def make_pdf(lines):
    """Minimal valid PDF 1.4 whose content stream holds each line as
    a literal string (raw UTF-8 bytes). Offsets for the xref table
    are computed, so the file is structurally a real PDF, not just a
    %PDF- header."""
    text = " ".join(_pdf_escape(ln) for ln in lines)
    stream = ("BT /F1 12 Tf 72 720 Td (%s) Tj ET" % text).encode("utf-8")
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n%s\nendstream"
        % (len(stream), stream),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
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


# The COMI 297291 fixture PDF: the source document's reported
# strings, exactly as the harvested body states them.
PDF_297291 = make_pdf(["صافي الربح: 63,079,356 (القيمة بالألف)",
                       "10/11/2026",
                       "القوائم المالية المجمعة عن الفترة: من "
                       "01/01/2026 إلى 30/09/2026"])

DETAIL_URL = "https://www.egx.com.eg/ar/NewsDetails.aspx?NewsID=297291"


def fake_fetch_ok(url):
    return 200, PDF_297291


def fake_fetch_404(url):
    return 404, b"not found"


def fake_fetch_html(url):
    return 200, b"<html><body>challenge</body></html>"


def fake_fetch_raises(url):
    raise RuntimeError("connection reset by TSPD wall")


class TestFindAttachmentLinks(unittest.TestCase):
    def test_pdf_href_is_followed(self):
        links = capture.find_attachment_links(
            [{"href": "/Uploads/Reports/297291.pdf", "text": "تقرير"}],
            DETAIL_URL)
        self.assertEqual(
            links, ["https://www.egx.com.eg/Uploads/Reports/297291.pdf"])

    def test_relative_href_resolves_against_detail_url(self):
        links = capture.find_attachment_links(
            [{"href": "Files/a.pdf?x=1", "text": ""}], DETAIL_URL)
        self.assertEqual(
            links, ["https://www.egx.com.eg/ar/Files/a.pdf?x=1"])

    def test_size_suffix_anchor_is_an_attachment(self):
        # Grounded in real harvested bodies: attachment lines end
        # with "(64 KB)" — e.g. COMI 297291's activity report.
        links = capture.find_attachment_links(
            [{"href": "/ar/Attachment.aspx?id=9",
              "text": " تقرير ممارسة النشاط المجمعة (64 KB)"}],
            DETAIL_URL)
        self.assertEqual(
            links, ["https://www.egx.com.eg/ar/Attachment.aspx?id=9"])

    def test_detail_and_search_pages_are_never_followed(self):
        links = capture.find_attachment_links(
            [{"href": "NewsDetails.aspx?NewsID=297292",
              "text": "next (64 KB)"},
             {"href": "NewsSearch.aspx?isin=EGS60121C018",
              "text": "search (12 KB)"}],
            DETAIL_URL)
        self.assertEqual(links, [])

    def test_javascript_mailto_fragment_never_followed(self):
        links = capture.find_attachment_links(
            [{"href": "javascript:void(0)", "text": "x (64 KB)"},
             {"href": "mailto:a@b.c", "text": "y (64 KB)"},
             {"href": "#top", "text": "z (64 KB)"}],
            DETAIL_URL)
        self.assertEqual(links, [])

    def test_duplicates_deduplicated_order_kept(self):
        links = capture.find_attachment_links(
            [{"href": "/a.pdf", "text": ""},
             {"href": "https://www.egx.com.eg/a.pdf", "text": ""},
             {"href": "/b.pdf", "text": ""}],
            DETAIL_URL)
        self.assertEqual(links, ["https://www.egx.com.eg/a.pdf",
                                 "https://www.egx.com.eg/b.pdf"])

    def test_plain_text_link_without_pdf_or_size_is_ignored(self):
        links = capture.find_attachment_links(
            [{"href": "/ar/News.aspx", "text": "أخبار الشركة"}],
            DETAIL_URL)
        self.assertEqual(links, [])


class TestCaptureOne(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(dir=_TMP)

    def test_captured_pointer_and_file(self):
        rec = capture.capture_one(fake_fetch_ok,
                                  "https://www.egx.com.eg/a.pdf",
                                  self.dir, "297291")
        self.assertEqual(rec["status"], "captured")
        self.assertEqual(rec["path"], "attachments/297291.pdf")
        self.assertEqual(rec["sha256"],
                         hashlib.sha256(PDF_297291).hexdigest())
        self.assertEqual(rec["size_bytes"], len(PDF_297291))
        self.assertEqual(rec["source_url"],
                         "https://www.egx.com.eg/a.pdf")
        self.assertIsNone(rec["reason"])
        stored = Path(self.dir, "297291.pdf").read_bytes()
        self.assertEqual(stored, PDF_297291)
        ok, why = capture.verify_attachment(rec, stored)
        self.assertTrue(ok, why)

    def test_fetch_failure_is_a_record_not_an_exception(self):
        rec = capture.capture_one(fake_fetch_raises,
                                  "https://www.egx.com.eg/a.pdf",
                                  self.dir, "297291")
        self.assertEqual(rec["status"], "fetch_failed")
        self.assertIsNone(rec["path"])
        self.assertIsNone(rec["sha256"])
        self.assertIn("TSPD", rec["reason"])
        self.assertEqual(os.listdir(self.dir), [])

    def test_http_error_is_fetch_failed(self):
        rec = capture.capture_one(fake_fetch_404,
                                  "https://www.egx.com.eg/a.pdf",
                                  self.dir, "297291")
        self.assertEqual(rec["status"], "fetch_failed")
        self.assertIn("404", rec["reason"])
        self.assertEqual(os.listdir(self.dir), [])

    def test_non_pdf_bytes_are_not_pdf(self):
        rec = capture.capture_one(fake_fetch_html,
                                  "https://www.egx.com.eg/a.pdf",
                                  self.dir, "297291")
        self.assertEqual(rec["status"], "not_pdf")
        self.assertIsNone(rec["path"])
        self.assertEqual(os.listdir(self.dir), [])

    def test_oversize_pdf_is_too_large(self):
        old = capture.MAX_PDF_BYTES
        capture.MAX_PDF_BYTES = 100
        try:
            rec = capture.capture_one(fake_fetch_ok,
                                      "https://www.egx.com.eg/a.pdf",
                                      self.dir, "297291")
        finally:
            capture.MAX_PDF_BYTES = old
        self.assertEqual(rec["status"], "too_large")
        self.assertEqual(os.listdir(self.dir), [])


class TestCaptureItemAttachments(unittest.TestCase):
    def setUp(self):
        self.results = tempfile.mkdtemp(dir=_TMP)

    def test_no_links_is_marked_no_attachment(self):
        """Acceptance: a disclosure with no attachment is marked as
        such — never silently dateless, never an empty list."""
        recs = capture.capture_item_attachments(
            "297291", [], DETAIL_URL, fake_fetch_ok, self.results)
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["status"], "no_attachment")
        self.assertIsNone(recs[0]["path"])
        self.assertFalse(
            os.path.exists(os.path.join(self.results, "attachments")))

    def test_failed_link_scan_is_marked(self):
        recs = capture.capture_item_attachments(
            "297291", None, DETAIL_URL, fake_fetch_ok, self.results)
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["status"], "link_scan_failed")

    def test_multiple_attachments_get_distinct_files(self):
        anchors = [{"href": "/a.pdf", "text": ""},
                   {"href": "/b.pdf", "text": ""}]
        recs = capture.capture_item_attachments(
            "297291", anchors, DETAIL_URL, fake_fetch_ok, self.results)
        self.assertEqual([r["status"] for r in recs],
                         ["captured", "captured"])
        self.assertEqual([r["path"] for r in recs],
                         ["attachments/297291.pdf",
                          "attachments/297291_2.pdf"])
        self.assertTrue(Path(self.results, "attachments",
                             "297291.pdf").exists())
        self.assertTrue(Path(self.results, "attachments",
                             "297291_2.pdf").exists())

    def test_mixed_success_and_failure(self):
        def fetch(url):
            return (200, PDF_297291) if url.endswith("/a.pdf") \
                else (404, b"")
        anchors = [{"href": "/a.pdf", "text": ""},
                   {"href": "/b.pdf", "text": ""}]
        recs = capture.capture_item_attachments(
            "297291", anchors, DETAIL_URL, fetch, self.results)
        self.assertEqual([r["status"] for r in recs],
                         ["captured", "fetch_failed"])
        self.assertTrue(Path(self.results, "attachments",
                             "297291.pdf").exists())
        self.assertFalse(Path(self.results, "attachments",
                              "297291_2.pdf").exists())

    def test_attachment_cap_is_five(self):
        anchors = [{"href": "/%d.pdf" % i, "text": ""}
                   for i in range(7)]
        recs = capture.capture_item_attachments(
            "297291", anchors, DETAIL_URL, fake_fetch_ok, self.results)
        self.assertEqual(len(recs), 5)
        self.assertEqual(len(os.listdir(
            os.path.join(self.results, "attachments"))), 5)


class TestVerifyAttachment(unittest.TestCase):
    def test_tampered_bytes_fail_the_hash(self):
        rec = {"status": "captured",
               "sha256": hashlib.sha256(PDF_297291).hexdigest()}
        ok, why = capture.verify_attachment(rec, PDF_297291 + b" ")
        self.assertFalse(ok)
        self.assertIn("sha256", why)

    def test_missing_file_fails(self):
        rec = {"status": "captured",
               "sha256": hashlib.sha256(PDF_297291).hexdigest()}
        ok, why = capture.verify_attachment(rec, None)
        self.assertFalse(ok)
        self.assertIn("missing", why)

    def test_non_captured_record_fails(self):
        ok, _ = capture.verify_attachment({"status": "no_attachment"},
                                          PDF_297291)
        self.assertFalse(ok)


class TestAcceptanceReReadingReproducesFields(unittest.TestCase):
    """Acceptance property: re-reading the stored PDF reproduces the
    extracted event fields. The pilot extracts from the harvested
    body; the stored PDF is the same source document, so the field
    strings it reports must be present in the stored bytes."""

    def test_comi_297291_fields_are_in_the_stored_pdf(self):
        item = {"id": "297291", "title": TITLE_297291,
                "body": BODY_297291, "date": "2026-11-10",
                "url": DETAIL_URL}
        events = disclosure_events.extract_document(item)
        earnings = [e for e in events if e["event_type"] == "earnings"]
        self.assertEqual(len(earnings), 1)
        ev = earnings[0]
        # Fields the pilot extracts from the body text.
        self.assertEqual(ev["payload"]["npat"]["value"], "63079356")
        self.assertEqual(ev["announced"]["value"], "2026-11-10")
        # Capture the fixture PDF (the source document's reported
        # strings) exactly as the harvester would.
        results = tempfile.mkdtemp(dir=_TMP)
        recs = capture.capture_item_attachments(
            "297291", [{"href": "/a.pdf", "text": ""}], DETAIL_URL,
            fake_fetch_ok, results)
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["status"], "captured")
        stored = Path(results, recs[0]["path"]).read_bytes()
        # Re-reading the stored PDF reproduces the extraction: the
        # hash matches the pointer, and the reported strings behind
        # the extracted fields are in the stored document (NPAT
        # "63,079,356" as reported, announced date "10/11/2026" as
        # reported — the event carries the canonical forms).
        ok, why = capture.verify_attachment(recs[0], stored)
        self.assertTrue(ok, why)
        missing = capture.fields_present_in_pdf(
            stored, ["63,079,356", "10/11/2026"])
        self.assertEqual(missing, [])

    def test_fields_present_reports_the_missing_ones(self):
        missing = capture.fields_present_in_pdf(
            PDF_297291, ["63,079,356", "no-such-field"])
        self.assertEqual(missing, ["no-such-field"])


class TestPublishHarvestAttachments(unittest.TestCase):
    def test_copies_only_pdfs_with_safe_names(self):
        results = Path(tempfile.mkdtemp(dir=_TMP))
        att = results / "egx-harvest" / "results" / "attachments"
        att.mkdir(parents=True)
        (att / "297291.pdf").write_bytes(PDF_297291)
        (att / "297289_2.pdf").write_bytes(PDF_297291)
        (att / "notes.txt").write_text("not a pdf")
        (att / "bad name.pdf").write_bytes(PDF_297291)
        arch = Path(tempfile.mkdtemp(dir=_TMP))
        n = worker._publish_harvest_attachments(results, arch)
        self.assertEqual(n, 2)
        dest = arch / "harvest" / "attachments"
        self.assertEqual(sorted(p.name for p in dest.iterdir()),
                         ["297289_2.pdf", "297291.pdf"])
        self.assertEqual((dest / "297291.pdf").read_bytes(), PDF_297291)

    def test_no_attachments_dir_copies_nothing(self):
        results = Path(tempfile.mkdtemp(dir=_TMP))
        arch = Path(tempfile.mkdtemp(dir=_TMP))
        self.assertEqual(
            worker._publish_harvest_attachments(results, arch), 0)
        self.assertFalse((arch / "harvest").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
