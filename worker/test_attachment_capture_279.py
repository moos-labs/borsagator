#!/usr/bin/env python3
"""Tests: disclosure attachment capture (issue #279).

Capture-only scope: at harvest, follow each disclosure's attachment
link where offered and store the PDF with a stable pointer (path +
sha256); failures are recorded explicitly, never silently omitted.

Run:  python3 worker/test_attachment_capture_279.py
  or:  python3 -m pytest worker/test_attachment_capture_279.py -q
  or:  python3 -m unittest worker.test_attachment_capture_279 -v
No network, no browser: the fetcher is faked; the harvester's
Playwright wiring is covered by inspection only (live proof needs
the worker's trusted EGX profile — see the PR body).
"""
import hashlib
import importlib.util
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ac = _load("attachment_capture",
           os.path.join(HERE, "attachment_capture.py"))

PDF = b"%PDF-1.4\n% fake pdf\n1 0 obj\n<<>>\nendobj\n%%EOF\n"
NOT_PDF = b"<html><body>challenge</body></html>"


def fake_fetch(mapping, content_type="application/pdf"):
    def fetch(url):
        if url in mapping:
            result = mapping[url]
            if isinstance(result, Exception):
                raise result
            return result, content_type
        raise RuntimeError("HTTP 404")
    return fetch


class TestFindLinks(unittest.TestCase):
    BASE = "https://www.egx.com.eg/ar/NewsDetails.aspx?NewsID=296893"

    def test_absolute_pdf_link(self):
        links = [{"href": "https://www.egx.com.eg/Uploads/a.pdf",
                  "text": "Download"}]
        self.assertEqual(ac.find_attachment_links(links, self.BASE),
                         ["https://www.egx.com.eg/Uploads/a.pdf"])

    def test_relative_link_resolves_against_detail_page(self):
        links = [{"href": "../Uploads/a.pdf?x=1", "text": "PDF"}]
        got = ac.find_attachment_links(links, self.BASE)
        self.assertEqual(
            got, ["https://www.egx.com.eg/Uploads/a.pdf?x=1"])

    def test_pdf_with_query_string_counts(self):
        links = [{"href": "/ar/NewsAttach.aspx?id=5&f=x.pdf&v=2",
                  "text": "attachment"}]
        got = ac.find_attachment_links(links, self.BASE)
        self.assertEqual(len(got), 1)
        self.assertIn("x.pdf", got[0])

    def test_non_pdf_links_rejected(self):
        links = [{"href": "https://www.egx.com.eg/ar/NewsDetails.aspx"
                          "?NewsID=1", "text": "next"},
                 {"href": "https://example.com/page.html",
                  "text": "page"},
                 {"href": "https://example.com/download?id=9",
                  "text": "download"}]
        self.assertEqual(ac.find_attachment_links(links, self.BASE), [])

    def test_dedup_and_cap(self):
        links = [{"href": "https://x.eg/a.pdf", "text": ""},
                 {"href": "https://x.eg/a.pdf", "text": ""},
                 {"href": "https://x.eg/b.pdf", "text": ""},
                 {"href": "https://x.eg/c.pdf", "text": ""},
                 {"href": "https://x.eg/d.pdf", "text": ""}]
        got = ac.find_attachment_links(links, self.BASE)
        self.assertEqual(len(got), ac.MAX_ATTACHMENTS_PER_ITEM)
        self.assertEqual(len(set(got)), len(got))

    def test_attachment_word_link_preferred(self):
        links = [{"href": "https://x.eg/other.pdf", "text": "table"},
                 {"href": "https://x.eg/ann.pdf", "text": "مرفق الإعلان"}]
        got = ac.find_attachment_links(links, self.BASE)
        self.assertEqual(got[0], "https://x.eg/ann.pdf")


class TestOffered(unittest.TestCase):
    def test_arabic_marker(self):
        self.assertTrue(ac.attachment_offered(
            "القاهرة للدواجن\nمرفق الإعلان (214 KB)"))

    def test_no_marker(self):
        self.assertFalse(ac.attachment_offered(
            "القاهرة للدواجن تعلن عن توزيع نقدي"))

    def test_english_marker(self):
        self.assertTrue(ac.attachment_offered(
            "see attachment below", "Board decisions"))


class TestCapture(unittest.TestCase):
    def test_captured_pdf_pointer(self):
        with tempfile.TemporaryDirectory() as tmp:
            url = "https://www.egx.com.eg/Uploads/ann.pdf"
            rec = ac.capture_attachments(
                "296893", [url], True, fake_fetch({url: PDF}), tmp)
            self.assertEqual(rec["status"], "captured")
            self.assertEqual(len(rec["files"]), 1)
            f = rec["files"][0]
            self.assertEqual(f["path"],
                             "attachments/296893/ann.pdf")
            self.assertEqual(f["sha256"],
                             hashlib.sha256(PDF).hexdigest())
            self.assertEqual(f["bytes"], len(PDF))
            self.assertEqual(f["url"], url)
            self.assertTrue(os.path.isfile(
                os.path.join(tmp, f["path"])))
            with open(os.path.join(tmp, f["path"]), "rb") as fh:
                self.assertEqual(fh.read(), PDF)
            # No floats anywhere in the record (Decimal rule).
            json.dumps(rec)
            self.assertNotIn("float", str(type(rec["files"][0]["bytes"])))

    def test_no_attachment(self):
        with tempfile.TemporaryDirectory() as tmp:
            rec = ac.capture_attachments(
                "1", [], False, fake_fetch({}), tmp)
            self.assertEqual(rec["status"], "no_attachment")
            self.assertEqual(rec["files"], [])
            self.assertIn("no attachment offered", rec["reason"])

    def test_offered_but_no_link_is_fetch_failed(self):
        with tempfile.TemporaryDirectory() as tmp:
            rec = ac.capture_attachments(
                "1", [], True, fake_fetch({}), tmp)
            self.assertEqual(rec["status"], "fetch_failed")
            self.assertIn("no PDF link found", rec["reason"])

    def test_download_error_recorded(self):
        with tempfile.TemporaryDirectory() as tmp:
            url = "https://www.egx.com.eg/Uploads/a.pdf"
            rec = ac.capture_attachments(
                "1", [url], True,
                fake_fetch({url: RuntimeError("HTTP 500")}), tmp)
            self.assertEqual(rec["status"], "fetch_failed")
            self.assertEqual(len(rec["failures"]), 1)
            self.assertIn("HTTP 500", rec["reason"])
            self.assertFalse(os.path.exists(
                os.path.join(tmp, "attachments")))

    def test_non_pdf_response_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            url = "https://www.egx.com.eg/Uploads/a.pdf"
            rec = ac.capture_attachments(
                "1", [url], True, fake_fetch({url: NOT_PDF}), tmp)
            self.assertEqual(rec["status"], "fetch_failed")
            self.assertIn("not a PDF", rec["reason"])

    def test_oversize_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            url = "https://www.egx.com.eg/Uploads/a.pdf"
            big = b"%PDF" + b"x" * (ac.MAX_ATTACHMENT_BYTES + 1)
            rec = ac.capture_attachments(
                "1", [url], True, fake_fetch({url: big}), tmp)
            self.assertEqual(rec["status"], "fetch_failed")
            self.assertIn("too large", rec["reason"])

    def test_partial_success_is_captured_with_failures(self):
        with tempfile.TemporaryDirectory() as tmp:
            good = "https://x.eg/good.pdf"
            bad = "https://x.eg/bad.pdf"
            rec = ac.capture_attachments(
                "7", [good, bad], True,
                fake_fetch({good: PDF,
                            bad: RuntimeError("HTTP 404")}), tmp)
            self.assertEqual(rec["status"], "captured")
            self.assertEqual(len(rec["files"]), 1)
            self.assertEqual(len(rec["failures"]), 1)
            self.assertIn("1 of 2", rec["reason"])

    def test_legacy_record_is_explicit(self):
        rec = ac.legacy_attachment_record()
        self.assertEqual(rec["status"], "not_recorded")
        self.assertIn("#279", rec["reason"])


class TestSafeFilename(unittest.TestCase):
    def test_query_stripped(self):
        self.assertEqual(
            ac.safe_filename("https://x.eg/a.pdf?v=2", "1"),
            "a.pdf")

    def test_fallback_to_news_id(self):
        self.assertEqual(
            ac.safe_filename("https://x.eg/download?id=9", "296893"),
            "download.pdf")

    def test_unsafe_chars_sanitised(self):
        name = ac.safe_filename("https://x.eg/a b%c.pdf", "1")
        self.assertNotIn(" ", name)
        self.assertTrue(name.endswith(".pdf"))


if __name__ == "__main__":
    unittest.main()
