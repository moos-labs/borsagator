#!/usr/bin/env python3
"""Regression tests: a failed harvester detail extraction must be
distinguishable from a genuinely empty detail body (issue #389).

Bug (worker/egx_harvest.py): extract_main_text raising was caught
and body = "" substituted; the item was still appended with
body_chars: 0 and no per-item failure field, so disclosures.json
could not tell a failed detail extraction from a genuinely empty
detail body. Same evidence-loss pattern as the #383 enumerator
bug, in the harvester.

Fix: extract_detail_body returns (None, "detail_failed", reason)
on any navigation/extraction failure, and disclosure_item records
body/body_chars unset with detail_status "detail_failed"; a
genuinely empty body stays a captured empty body (body "",
body_chars 0, detail_status "captured"). The item is kept, the
log line is kept, and the publish date still comes from the
search row when the body is missing.

Run:  python3 worker/test_egx_harvest_detail_failed_389.py
  or:  python3 -m pytest worker/test_egx_harvest_detail_failed_389.py -q
  or:  python3 -m unittest worker.test_egx_harvest_detail_failed_389 -v
No network, no browser: fake pages stand in for Playwright.
"""
import importlib.util
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SPEC = importlib.util.spec_from_file_location(
    "egx_harvest_under_test",
    os.path.join(_HERE, "egx_harvest.py"))
egx_harvest = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(egx_harvest)
extract_detail_body = egx_harvest.extract_detail_body
disclosure_item = egx_harvest.disclosure_item

ROW_WITH_DATE = ("Title عن الفترة: من 01/01/2026 إلى 30/09/2026\n"
                 "10/11/2026\n")
BODY_WITH_DATE = ("Title\n10/11/2026\nrest of the disclosure body\n")


class _FakePage:
    """Minimal Playwright page stand-in: goto/wait succeed,
    evaluate returns text or raises, like a real detail page."""

    def __init__(self, text=None, fail=False):
        self._text = text
        self._fail = fail

    def goto(self, *args, **kwargs):
        return None

    def wait_for_timeout(self, *args, **kwargs):
        return None

    def evaluate(self, *args, **kwargs):
        if self._fail:
            raise RuntimeError("simulated extraction failure")
        return self._text


class TestDetailFailed389(unittest.TestCase):
    def test_detail_failure_is_distinguishable(self):
        """A failed extraction records body None / body_chars None
        with detail_status "detail_failed" — never a fabricated
        empty body."""
        body, status, error = extract_detail_body(
            _FakePage(fail=True), "https://www.egx.com.eg/ar/NewsDetails"
            ".aspx?NewsID=297291")
        self.assertIsNone(body)
        self.assertEqual(status, "detail_failed")
        self.assertIn("simulated extraction failure", error)
        item = disclosure_item("297291", body, status, error,
                               ROW_WITH_DATE, "title", "href", [])
        self.assertIsNone(item["body"])
        self.assertIsNone(item["body_chars"])
        self.assertEqual(item["detail_status"], "detail_failed")
        self.assertIn("simulated extraction failure",
                      item["detail_error"])
        # The date still comes from the search row.
        self.assertEqual(item["date"], "2026-11-10")

    def test_goto_failure_is_a_detail_failure(self):
        """A failed navigation is the same failure state, not an
        empty body."""
        class _FailingGoto(_FakePage):
            def goto(self, *args, **kwargs):
                raise RuntimeError("simulated navigation failure")

        body, status, error = extract_detail_body(
            _FailingGoto(), "https://www.egx.com.eg/ar/NewsDetails"
            ".aspx?NewsID=297291")
        self.assertIsNone(body)
        self.assertEqual(status, "detail_failed")
        self.assertIn("simulated navigation failure", error)
        item = disclosure_item("297291", body, status, error,
                               ROW_WITH_DATE, "title", "href", [])
        self.assertIsNone(item["body"])
        self.assertIsNone(item["body_chars"])

    def test_genuinely_empty_body_stays_captured_empty(self):
        """A detail page that really extracts to "" is still a
        captured empty body — body_chars 0, not a failure."""
        body, status, error = extract_detail_body(
            _FakePage(text=""), "https://www.egx.com.eg/ar/NewsDetails"
            ".aspx?NewsID=297291")
        self.assertEqual(body, "")
        self.assertEqual(status, "captured")
        self.assertIsNone(error)
        item = disclosure_item("297291", body, status, error,
                               ROW_WITH_DATE, "title", "href", [])
        self.assertEqual(item["body"], "")
        self.assertEqual(item["body_chars"], 0)
        self.assertEqual(item["detail_status"], "captured")
        self.assertIsNone(item["detail_error"])
        self.assertEqual(item["date"], "2026-11-10")

    def test_successful_body_captured(self):
        """A normal extraction is captured with its real chars and
        its date from the body."""
        body, status, error = extract_detail_body(
            _FakePage(text=BODY_WITH_DATE),
            "https://www.egx.com.eg/ar/NewsDetails.aspx?NewsID=297291")
        self.assertEqual(body, BODY_WITH_DATE)
        self.assertEqual(status, "captured")
        self.assertIsNone(error)
        item = disclosure_item("297291", body, status, error,
                               ROW_WITH_DATE, "title", "href", [])
        self.assertEqual(item["body"], BODY_WITH_DATE)
        self.assertEqual(item["body_chars"], len(BODY_WITH_DATE))
        self.assertEqual(item["detail_status"], "captured")
        self.assertEqual(item["date"], "2026-11-10")


if __name__ == "__main__":
    unittest.main(verbosity=2)
