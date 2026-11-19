#!/usr/bin/env python3
"""Tests: attachment pointer on events + PDF re-read verification
(issue #279).

Capture-only scope: the event points at the stored PDF (path +
sha256); ``disclosure_events.py verify`` re-reads the stored PDF
and checks the already-extracted fields reproduce from it. No
PDF-only field extraction is attempted anywhere here.

Run:  python3 scripts/test_disclosure_events_279.py
  or:  python3 -m pytest scripts/test_disclosure_events_279.py -q
No network: the PDFs are built in-test; the harvested items are the
real #109 golden fixtures (harvest/POUL.json, 2026-11-18).
"""
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.join(HERE, "disclosure_events_fixtures",
                        "fixtures.json")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


de = _load("disclosure_events",
           os.path.join(HERE, "disclosure_events.py"))
report_model = _load(
    "report_model", os.path.join(HERE, "report_model.py"))

PDF_BYTES = b"%PDF-1.4\n% fixture\n"


def make_pdf(lines, flate=True):
    """Minimal PDF whose text lines are the given byte strings."""
    content = b"BT /F1 12 Tf 72 720 Td "
    for i, line in enumerate(lines):
        if i:
            content += b"0 -14 Td "
        content += b"(" + line.replace(b"(", b"\\(").replace(
            b")", b"\\)") + b") Tj "
    content += b"ET"
    stream = zlib.compress(content) if flate else content
    filt = b" /Filter /FlateDecode" if flate else b""
    header = (b"%PDF-1.4\n"
              b"4 0 obj << /Length " + str(len(stream)).encode()
              + filt + b" >> stream\n")
    return (header + stream
            + b"\nendstream endobj\n%%EOF\n")


# The POUL coupon-42 announcement, as the stored PDF would carry it
# (Western digits, dd/mm/yyyy — the forms EGX PDFs use).
DIVIDEND_PDF_LINES = [
    b"Cairo Poultry (POUL.CA) cash dividend",
    b"Coupon number 42",
    b"Coupon value 1.9 EGP",
    b"Distribution date 18/11/2026",
    b"Entitlement end 15/11/2026",
    b"Ex-date 16/11/2026",
]

DIVIDEND_PDF_NO_PAYOUT = [l for l in DIVIDEND_PDF_LINES
                          if b"18/11/2026" not in l]


def golden_doc():
    with open(FIXTURES, encoding="utf-8") as f:
        cases = json.load(f)["cases"]
    case = next(c for c in cases
                if c["name"] == "golden_poul_dividend")
    return json.loads(json.dumps(case["doc"]))  # deep copy


def captured_attachment(doc_id, pdf_bytes, tmpdir):
    rel = "attachments/%s/announcement.pdf" % doc_id
    path = os.path.join(tmpdir, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(pdf_bytes)
    return {"status": "captured",
            "files": [{"url": "https://www.egx.com.eg/Uploads/a.pdf",
                       "path": rel,
                       "sha256": hashlib.sha256(pdf_bytes).hexdigest(),
                       "bytes": len(pdf_bytes),
                       "content_type": "application/pdf"}],
            "failures": [], "reason": None,
            "captured_at": "2026-11-19T00:00:00Z"}


class TestAttachmentPointer(unittest.TestCase):
    def test_captured_pointer_carried_to_event(self):
        with tempfile.TemporaryDirectory() as tmp:
            doc = golden_doc()
            pdf = make_pdf(DIVIDEND_PDF_LINES)
            doc["attachment"] = captured_attachment(
                doc["id"], pdf, tmp)
            events = de.extract_document(doc)
            self.assertEqual(len(events), 1)
            att = events[0]["attachment"]
            self.assertEqual(att["status"], "captured")
            self.assertEqual(
                att["files"][0]["path"],
                "attachments/296893/announcement.pdf")
            self.assertEqual(
                att["files"][0]["sha256"],
                hashlib.sha256(pdf).hexdigest())
            # The pointer does not disturb the frozen v2 contract:
            # the validator tolerates the additive top-level key.
            self.assertEqual(
                report_model.validate_event_record(events[0]), [])

    def test_revision_id_unchanged_by_pointer(self):
        doc = golden_doc()
        before = de.extract_document(doc)[0]["event_revision_id"]
        doc["attachment"] = {"status": "captured", "files": [{
            "url": "https://x.eg/a.pdf",
            "path": "attachments/296893/a.pdf",
            "sha256": "0" * 64, "bytes": 10,
            "content_type": "application/pdf"}],
            "failures": [], "reason": None,
            "captured_at": "2026-11-19T00:00:00Z"}
        after = de.extract_document(doc)[0]["event_revision_id"]
        self.assertEqual(before, after)

    def test_failure_statuses_carried(self):
        for status in ("no_attachment", "fetch_failed"):
            doc = golden_doc()
            doc["attachment"] = {"status": status, "files": [],
                                 "failures": [],
                                 "reason": "test",
                                 "captured_at": None}
            ev = de.extract_document(doc)[0]
            self.assertEqual(ev["attachment"]["status"], status)

    def test_legacy_item_gets_explicit_not_recorded(self):
        doc = golden_doc()  # fixtures predate capture: no key
        self.assertNotIn("attachment", doc)
        ev = de.extract_document(doc)[0]
        self.assertEqual(ev["attachment"]["status"], "not_recorded")
        self.assertIn("#279", ev["attachment"]["reason"])

    def test_feed_report_counts_attachments(self):
        doc = golden_doc()
        doc["attachment"] = {"status": "no_attachment", "files": [],
                             "failures": [], "reason": "test",
                             "captured_at": None}
        _, report = de.extract_feed([doc])
        self.assertEqual(report["attachments"], {"no_attachment": 1})

    def test_no_float_in_event_with_attachment(self):
        doc = golden_doc()
        with tempfile.TemporaryDirectory() as tmp:
            doc["attachment"] = captured_attachment(
                doc["id"], make_pdf(DIVIDEND_PDF_LINES), tmp)
            events = de.extract_document(doc)
            de._assert_no_float({"events": events})  # raises on float


class TestVerify(unittest.TestCase):
    def _event_with_pdf(self, tmp, lines, doc_id="296893"):
        doc = golden_doc()
        doc["id"] = doc_id
        doc["url"] = ("https://www.egx.com.eg/ar/NewsDetails.aspx"
                      "?NewsID=%s" % doc_id)
        pdf = make_pdf(lines)
        doc["attachment"] = captured_attachment(doc_id, pdf, tmp)
        return de.extract_document(doc)[0], tmp

    def test_reproduced_from_stored_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            ev, _ = self._event_with_pdf(tmp, DIVIDEND_PDF_LINES)
            res = de.verify_event(ev, tmp)
            self.assertEqual(res["status"], "reproduced")
            self.assertEqual(res["missing_tokens"], [])

    def test_partial_when_pdf_lacks_payout(self):
        with tempfile.TemporaryDirectory() as tmp:
            ev, _ = self._event_with_pdf(tmp, DIVIDEND_PDF_NO_PAYOUT)
            res = de.verify_event(ev, tmp)
            self.assertEqual(res["status"], "partial")
            self.assertEqual(res["missing_tokens"], ["payout_date"])

    def test_skipped_without_stored_pdf(self):
        doc = golden_doc()
        doc["attachment"] = {"status": "no_attachment", "files": [],
                             "failures": [], "reason": "test",
                             "captured_at": None}
        ev = de.extract_document(doc)[0]
        res = de.verify_event(ev, "/nonexistent")
        self.assertEqual(res["status"], "skipped")

    def test_skipped_for_legacy_item(self):
        ev = de.extract_document(golden_doc())[0]
        res = de.verify_event(ev, "/nonexistent")
        self.assertEqual(res["status"], "skipped")
        self.assertIn("not_recorded", res["detail"])

    def test_unreadable_when_file_missing_from_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            doc = golden_doc()
            # Pointer recorded, file never written.
            doc["attachment"] = {"status": "captured", "files": [{
                "url": "https://x.eg/a.pdf",
                "path": "attachments/296893/a.pdf",
                "sha256": "0" * 64, "bytes": 10,
                "content_type": "application/pdf"}],
                "failures": [], "reason": None,
                "captured_at": "2026-11-19T00:00:00Z"}
            ev = de.extract_document(doc)[0]
            res = de.verify_event(ev, tmp)
            self.assertEqual(res["status"], "unreadable")

    def test_verify_cli_exit_codes(self):
        with tempfile.TemporaryDirectory() as tmp:
            ev_ok, _ = self._event_with_pdf(tmp, DIVIDEND_PDF_LINES)
            ev_bad, _ = self._event_with_pdf(
                tmp, DIVIDEND_PDF_NO_PAYOUT, doc_id="296894")
            events_path = os.path.join(tmp, "events.json")
            with open(events_path, "w", encoding="utf-8") as f:
                json.dump({"events": [ev_ok]}, f)
            proc = subprocess.run(
                [sys.executable,
                 os.path.join(HERE, "disclosure_events.py"),
                 "verify", events_path,
                 "--attachments-dir", tmp],
                capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            with open(events_path, "w", encoding="utf-8") as f:
                json.dump({"events": [ev_ok, ev_bad]}, f)
            proc = subprocess.run(
                [sys.executable,
                 os.path.join(HERE, "disclosure_events.py"),
                 "verify", events_path,
                 "--attachments-dir", tmp],
                capture_output=True, text=True)
            self.assertEqual(proc.returncode, 1, proc.stderr)
            self.assertIn("partial=1", proc.stderr)


if __name__ == "__main__":
    unittest.main()
