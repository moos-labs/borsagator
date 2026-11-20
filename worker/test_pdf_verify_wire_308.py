#!/usr/bin/env python3
"""Tests: wire pdf_verify into the worker harvest/verify path (#308).

The wiring under test (worker/worker.py): after
extract_disclosure_events extracts a ticker's events, it runs
scripts/pdf_verify.py over those events against the PDFs this
sweep's phase-1 refresh captured, and records the outcome in
extraction[code]["pdf_verification"] plus
disclosure-events/<CODE>-verification.json in the run dir.

Guarantees pinned here:
- a verified run records status "verified" with the summary, and
  the extraction outcome is unchanged;
- a mismatch / scanned PDF is recorded as "with-failures" and the
  sweep still runs (extraction stays "extracted");
- a ticker with no captured attachments records "no-coverage";
- a cached refresh (no PDFs on disk this sweep) records
  "skipped-no-attachments";
- a missing/crashing verifier records "verification-failed" and
  never fails the extraction.

Deterministic replay (no network, no live EGX page): the fixture
harvest is the #109 golden COMI 297291 earnings document, the
fixture PDFs are the #301 ToUnicode builders
(scripts/test_pdf_verify_301.py), and the REAL extractor and the
REAL verifier run as subprocesses. PDF-level tests skip with a
clear message when pypdf is absent; the no-coverage / cached /
missing-script tests run either way.

Run: python3 worker/test_pdf_verify_wire_308.py
  (for the PDF-level tests: the pypdf venv python, e.g.
  /tmp/tick2027-pypdf-venv/bin/python)
  or: python3 -m pytest worker/test_pdf_verify_wire_308.py -q
  or: python3 -m unittest worker.test_pdf_verify_wire_308 -v

Harness-first: FAILS on pristine main (worker has no
verify_disclosure_events — AttributeError — and extraction
records no pdf_verification) and PASSES on the fixed tree.
"""
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _test_tmp  # noqa: E402  (atexit cleanup of scratch dirs, #388)
_TMP = _test_tmp.mkdtemp(prefix="gator308-test-")
os.environ["GATOR_ROOT"] = str(_TMP)

_HERE = Path(os.path.abspath(__file__)).parent
_REPO = _HERE.parent
sys.path.insert(0, str(_HERE))

import worker  # noqa: E402

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
             os.path.join(_REPO, "scripts", "test_pdf_verify_301.py"))
FIXTURES = json.loads(
    (_REPO / "scripts" / "disclosure_events_fixtures"
     / "fixtures.json").read_text(encoding="utf-8"))
CASES = {c["name"]: c["doc"] for c in FIXTURES["cases"]}


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _now_z():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _comi_doc(pdf_bytes=None):
    """Golden COMI 297291 earnings doc, as harvested (item date is
    the wrong 2026-01-01; the standalone line 10/11/2026 is real),
    optionally carrying a captured-attachment pointer."""
    doc = json.loads(json.dumps(
        CASES["golden_comi_earnings_consolidated"]))
    if pdf_bytes is not None:
        doc["attachments"] = [v301.pointer(pdf_bytes)]
    return doc


def _swapped_comi_pdf():
    """COMI 297291 values with current/comparative NPAT swapped —
    the verifier must call it a mismatch, never a pass."""
    return v301.make_pdf_ar([[
        "صافي الربح: 62,100,264 (القيمة بالألف)",
        "صافي الربح لفترة المقارنة: 63,079,356 (القيمة بالألف)",
        "القوائم المالية المجمعة عن الفترة: من 01/01/2026 إلى 30/09/2026",
        "10/11/2026"]])


class Wire308(unittest.TestCase):
    def setUp(self):
        self.workdir = Path(tempfile.mkdtemp(dir=_TMP))
        self.job_id = "test-308-001"
        self.job = {"id": self.job_id,
                    "job": "sweep-lite COMI.CA market=EGX",
                    "added": worker.now()}
        self.plan = [("news-disclosure", "COMI.CA")]
        self._setup_release()

    def _setup_release(self):
        """Fake release checkout: the REAL extractor + verifier +
        their imports, as the worker's CODE checkout carries them."""
        code = worker.CODE
        (code / "scripts").mkdir(parents=True, exist_ok=True)
        for name in ("disclosure_events.py", "pdf_verify.py",
                     "pdf_text.py"):
            shutil.copy(_REPO / "scripts" / name,
                        code / "scripts" / name)
        (code / "worker").mkdir(parents=True, exist_ok=True)
        shutil.copy(_REPO / "worker" / "attachment_capture.py",
                    code / "worker" / "attachment_capture.py")

    def _seed(self, doc, refresh="refreshed", with_refresh_dir=False,
              pdf_bytes=None):
        """Write the harvest cache + (optionally) the phase-1 refresh
        results dir with the PDF on disk; return the manifest."""
        harvested_at = _now_z()
        harvest = {"ticker": "COMI.CA",
                   "company_ar": "البنك التجاري الدولي",
                   "isin": "EGS60121C018",
                   "harvested_at": harvested_at, "count": 1,
                   "items": [doc]}
        cache_dir = worker.ROOT / "harvest"
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / "COMI.json").write_text(
            json.dumps(harvest, ensure_ascii=False, indent=1),
            encoding="utf-8")
        if with_refresh_dir:
            att = worker._refresh_results_dir(self.workdir, "COMI") \
                / "attachments"
            att.mkdir(parents=True, exist_ok=True)
            if pdf_bytes is not None:
                (att / "297291.pdf").write_bytes(pdf_bytes)
        started = _now_iso()
        return {"started": started,
                "disclosure_feed": {
                    "sweep_id": self.job_id, "started": started,
                    "tickers": {"COMI": {
                        "refresh": refresh,
                        "harvested_at": harvested_at, "items": 1}}}}

    def _extract(self, manifest):
        return worker.extract_disclosure_events(
            self.job, self.workdir, manifest, self.plan)

    def _verification(self, manifest):
        ext = manifest["disclosure_feed"]["extraction"]["COMI"]
        self.assertEqual(ext["status"], "extracted", ext)
        return ext["pdf_verification"]

    @unittest.skipUnless(HAVE_PYPDF, "pypdf not installed")
    def test_verified_end_to_end(self):
        manifest = self._seed(_comi_doc(v301.PDF_AR_COMI),
                              with_refresh_dir=True,
                              pdf_bytes=v301.PDF_AR_COMI)
        self._extract(manifest)
        ver = self._verification(manifest)
        self.assertEqual(ver["status"], "verified", ver)
        self.assertEqual(ver["summary"].get("verified"), 1, ver)
        self.assertEqual(ver["summary"].get("checked"), 1, ver)
        self.assertEqual(
            ver["verification_file"],
            "disclosure-events/COMI-verification.json")
        data = json.loads(
            (self.workdir / "disclosure-events"
             / "COMI-verification.json").read_text(encoding="utf-8"))
        self.assertEqual(data["summary"]["verified"], 1)
        self.assertEqual(
            data["results"][0]["event_id"] is not None, True)

    def test_no_captured_attachments_is_no_coverage(self):
        # Attachments dir exists (fresh refresh) but the harvest
        # carries no attachment pointer: zero events checked.
        manifest = self._seed(_comi_doc(), with_refresh_dir=True)
        self._extract(manifest)
        ver = self._verification(manifest)
        self.assertEqual(ver["status"], "no-coverage", ver)
        self.assertEqual(ver["summary"].get("checked"), 0, ver)

    def test_cached_refresh_skips_verification(self):
        # Cached refresh: extraction runs from the cache, but no
        # PDFs are on disk this sweep — verification skips, the
        # sweep is unaffected.
        manifest = self._seed(_comi_doc(v301.PDF_AR_COMI),
                              refresh="cached", with_refresh_dir=False)
        self._extract(manifest)
        ver = self._verification(manifest)
        self.assertEqual(ver["status"], "skipped-no-attachments", ver)

    def test_missing_verifier_script_is_recorded_not_fatal(self):
        manifest = self._seed(_comi_doc(v301.PDF_AR_COMI),
                              with_refresh_dir=True,
                              pdf_bytes=v301.PDF_AR_COMI)
        script = worker.CODE / "scripts" / "pdf_verify.py"
        script.unlink()
        try:
            self._extract(manifest)
        finally:
            shutil.copy(_REPO / "scripts" / "pdf_verify.py", script)
        ver = self._verification(manifest)
        self.assertEqual(ver["status"], "verification-failed", ver)
        self.assertIn("missing", ver["detail"])

    @unittest.skipUnless(HAVE_PYPDF, "pypdf not installed")
    def test_mismatch_is_recorded_not_fatal(self):
        pdf = _swapped_comi_pdf()
        manifest = self._seed(_comi_doc(pdf), with_refresh_dir=True,
                              pdf_bytes=pdf)
        self._extract(manifest)
        ver = self._verification(manifest)
        self.assertEqual(ver["status"], "with-failures", ver)
        self.assertEqual(ver["summary"].get("mismatch"), 1, ver)

    @unittest.skipUnless(HAVE_PYPDF, "pypdf not installed")
    def test_scanned_pdf_is_inconclusive_not_fatal(self):
        manifest = self._seed(_comi_doc(v301.PDF_SCANNED),
                              with_refresh_dir=True,
                              pdf_bytes=v301.PDF_SCANNED)
        self._extract(manifest)
        ver = self._verification(manifest)
        self.assertEqual(ver["status"], "with-failures", ver)
        self.assertEqual(ver["summary"].get("inconclusive"), 1, ver)


if __name__ == "__main__":
    unittest.main(verbosity=2)
