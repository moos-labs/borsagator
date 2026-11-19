#!/usr/bin/env python3
"""Tests: minimal PDF text extraction (issue #279, verify step).

The extractor is a verification aid: it returns raw text so
``disclosure_events.py verify`` can check that already-extracted
fields reproduce from the stored PDF. It extracts no fields.

Run:  python3 scripts/test_pdf_text_279.py
  or:  python3 -m pytest scripts/test_pdf_text_279.py -q
No network, no fixture files: the PDFs are built in-test.
"""
import importlib.util
import os
import sys
import unittest
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


pdf_text = _load("pdf_text", os.path.join(HERE, "pdf_text.py"))


def make_pdf(content_stream, flate=True):
    """A minimal one-page PDF whose content stream is `content_stream`
    (bytes). Offsets/xref are not valid — the extractor scans streams,
    as it does on real files."""
    if flate:
        stream = zlib.compress(content_stream)
        filt = b" /Filter /FlateDecode"
    else:
        stream = content_stream
        filt = b""
    header = (b"%PDF-1.4\n"
              b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
              b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
              b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox "
              b"[0 0 612 792] /Contents 4 0 R /Resources << /Font "
              b"<< /F1 5 0 R >> >> >> endobj\n"
              b"4 0 obj << /Length " + str(len(stream)).encode()
              + filt + b" >> stream\n")
    return (header + stream
            + b"\nendstream endobj\n"
              b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont "
              b"/Helvetica >> endobj\n"
              b"trailer << /Root 1 0 R >>\n%%EOF\n")


class TestPdfText(unittest.TestCase):
    def test_tj_flate(self):
        pdf = make_pdf(b"BT /F1 12 Tf 72 720 Td "
                       b"(Coupon 42) Tj 0 -14 Td "
                       b"(Value 1.9 EGP) Tj ET")
        text = pdf_text.extract_text(pdf)
        self.assertIn("Coupon 42", text)
        self.assertIn("Value 1.9 EGP", text)

    def test_tj_uncompressed(self):
        pdf = make_pdf(b"BT (18/11/2026) Tj ET", flate=False)
        self.assertIn("18/11/2026", pdf_text.extract_text(pdf))

    def test_tj_array(self):
        pdf = make_pdf(b"BT [(Payout date ) 120 (18/11/2026)] TJ ET")
        text = pdf_text.extract_text(pdf)
        self.assertIn("Payout date", text)
        self.assertIn("18/11/2026", text)

    def test_escapes(self):
        pdf = make_pdf(b"BT (a\\(b\\) c\\053d) Tj ET")
        self.assertIn("a(b) c+d", pdf_text.extract_text(pdf))

    def test_non_pdf_returns_empty(self):
        self.assertEqual(pdf_text.extract_text(b"<html>no</html>"), "")
        self.assertEqual(pdf_text.extract_text(b""), "")
        self.assertEqual(pdf_text.extract_text(None), "")

    def test_no_show_operators_returns_empty(self):
        # A metadata string with no Tj/TJ is not page text.
        pdf = make_pdf(b"/Title (Dividend announcement)")
        self.assertEqual(pdf_text.extract_text(pdf), "")

    def test_truncated_stream_never_raises(self):
        self.assertEqual(pdf_text.extract_text(b"%PDF-1.4\nstream\n("),
                         "")


if __name__ == "__main__":
    unittest.main()
