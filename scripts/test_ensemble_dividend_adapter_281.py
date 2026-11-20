#!/usr/bin/env python3
"""Tests for issue #281: feed #109 disclosure events into #26
dividend-aware ensemble scoring.

Unit level: `events_to_corporate_actions` (field mapping + gating)
and `merge_corporate_actions` (event supersedes legacy for the same
distribution) in scripts/ensemble.py.

End to end: the REAL ensemble.py runs in a minimal sweep dir built
from the REAL #109 golden (POUL coupon 42, NewsID 296893) — the REAL
extractor produces the events file, the REAL ensemble consumes it.
Three runs on the same sweep:
  A. no events file — legacy text detection only;
  B. events file present — one event-sourced action, verbatim
     ex-date, same DPS / ex-date / mechanical % as the standalone
     #26 path;
  C. events file present but the collected disclosure body blanked
     (simulating a body the legacy path cannot see — e.g. clipped
     past the coupon facts) — the dividend-aware adjustment is still
     there, identical to B.
Plus a no-dividend control (no event, no dividend text) proving no
regression on non-dividend sweeps: corporate_actions == [].

Stdlib only, no network. Run: python3 scripts/test_ensemble_dividend_adapter_281.py
"""
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import disclosure_events  # noqa: E402
import ensemble  # noqa: E402


def _poul_doc():
    with open(os.path.join(HERE, "disclosure_events_fixtures",
                           "fixtures.json"), encoding="utf-8") as f:
        data = json.load(f)
    for case in data["cases"]:
        if case["name"] == "golden_poul_dividend":
            return copy.deepcopy(case["doc"])
    raise AssertionError("golden_poul_dividend fixture missing")


def _poul_event():
    events, _report = disclosure_events.extract_feed([_poul_doc()])
    assert len(events) == 1, events
    ev = events[0]
    assert ev["event_type"] == "dividend"
    assert ev["verification_status"] == "verified", ev
    return ev


def _sweep_dir(doc, with_events, base_date="2026-11-15"):
    """Minimal sweep dir ensemble.py can score: digest + collected.

    digest date 2026-11-15 is the session before the 2026-11-16
    ex-date, so every horizon spans it. Base 10.00 via the
    pandas-ta digest metric (no price CSVs: sigma falls back to the
    0.02 default, which is fine — the dividend marking does not
    depend on sigma)."""
    tmp = Path(tempfile.mkdtemp(prefix="borsagator-281-"))
    (tmp / "digest").mkdir()
    (tmp / "collected" / "news-disclosure").mkdir(parents=True)
    (tmp / "ledger").mkdir()
    shutil.copy2(os.path.join(ROOT, "ledger", "weights.json"),
                 tmp / "ledger" / "weights.json")
    digest = {
        "ticker": "POUL.CA",
        "date": base_date,
        "job": "sweep-lite POUL.CA market=EGX",
        "results": [
            {"tool": "pandas-ta", "status": "ok",
             "summary": {"metrics": {
                 "ticker": "POUL.CA", "close": 10.0, "rsi_14": 50,
                 "macd_hist": 0.1, "adx_14": 20, "ema_20": 9.5,
                 "stoch_k": 50}}},
            {"tool": "news-disclosure", "status": "ok",
             "summary": {"metrics": {"ticker": "POUL.CA"}}},
        ],
    }
    (tmp / "digest" / "digest.json").write_text(
        json.dumps(digest, indent=1), encoding="utf-8")
    (tmp / "digest" / "digest.md").write_text(
        "# \U0001f40a Borsagator digest — sweep-lite POUL.CA market=EGX\n",
        encoding="utf-8")
    (tmp / "collected" / "news-disclosure" / "disclosures.json").write_text(
        json.dumps({"items": [doc]}, ensure_ascii=False),
        encoding="utf-8")
    (tmp / "collected" / "news-disclosure" / "news.json").write_text(
        json.dumps({"items": []}, ensure_ascii=False), encoding="utf-8")
    if with_events:
        events, _report = disclosure_events.extract_feed([_poul_doc()])
        feed = {"schema_version": disclosure_events.SCHEMA_VERSION,
                "extractor_version": disclosure_events.EXTRACTOR_VERSION,
                "config_hash": disclosure_events.CONFIG_HASH,
                "quarter": {"start": "2026-08-19", "end": "2026-11-19"},
                "report": _report, "events": events}
        dest = tmp / "disclosure-events"
        dest.mkdir()
        (dest / "POUL-events.json").write_text(
            json.dumps(feed, ensure_ascii=False, indent=1, sort_keys=True),
            encoding="utf-8")
    return tmp


def _run_ensemble(sweep):
    env = dict(os.environ)
    env["BORSAGATOR_WEIGHTS"] = "ledger/weights.json"
    proc = subprocess.run(
        [sys.executable, os.path.join(HERE, "ensemble.py")],
        cwd=str(sweep), env=env, capture_output=True, text=True,
        timeout=120)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    out = sweep / "digest" / "ensemble.json"
    assert out.is_file(), "ensemble.json missing: " + proc.stdout
    with open(out, encoding="utf-8") as f:
        return json.load(f)


class TestEventMapping(unittest.TestCase):
    def test_real_event_maps_to_26_action(self):
        ev = _poul_event()
        actions = ensemble.events_to_corporate_actions([ev], "POUL.CA", 10.0)
        self.assertEqual(len(actions), 1)
        a = actions[0]
        self.assertEqual(a["type"], "dividend")
        self.assertAlmostEqual(a["dps"], 1.9, places=6)
        self.assertEqual(a["ex_date"], "2026-11-16")
        self.assertEqual(a["entitlement_end"], "2026-11-15")
        self.assertEqual(a["date_basis"], "verbatim:ex-date")
        self.assertEqual(a["mechanical_pct"], -19.0)
        self.assertEqual(a["source"], "disclosure-event")
        self.assertEqual(a["event_id"], ev["event_id"])
        self.assertEqual(a["announced"], "2026-11-02")
        self.assertEqual(a["coupon_number"], "42")

    def test_gates(self):
        ev = _poul_event()
        base = [ev]
        # Candidates and unverified extractions never feed scoring.
        cand = copy.deepcopy(ev)
        cand["verification_status"] = "unverified"
        cand["extraction_status"] = "candidate"
        self.assertEqual(
            ensemble.events_to_corporate_actions([cand], "POUL.CA", 10.0),
            [])
        # Non-dividend events never feed scoring.
        earn = copy.deepcopy(ev)
        earn["event_type"] = "earnings"
        self.assertEqual(
            ensemble.events_to_corporate_actions([earn], "POUL.CA", 10.0),
            [])
        # Another ticker's event never feeds this sweep.
        other = copy.deepcopy(ev)
        other["issuer"] = dict(ev["issuer"], ticker="COMI.CA")
        self.assertEqual(
            ensemble.events_to_corporate_actions([other], "POUL.CA", 10.0),
            [])
        # No verbatim ex-date: nothing to mark a horizon with.
        noex = copy.deepcopy(ev)
        noex["payload"] = dict(ev["payload"])
        noex["payload"]["ex_date"] = {"value": None,
                                      "basis": "not-stated"}
        self.assertEqual(
            ensemble.events_to_corporate_actions([noex], "POUL.CA", 10.0),
            [])
        # Same DPS guard as the legacy path (0 < dps < base).
        self.assertEqual(
            ensemble.events_to_corporate_actions(base, "POUL.CA", 1.0), [])
        self.assertEqual(
            ensemble.events_to_corporate_actions(base, "POUL.CA", 0), [])
        # Non-EGP amount: the #26 guard is dps < base in one currency.
        fx = copy.deepcopy(ev)
        fx["payload"] = copy.deepcopy(ev["payload"])
        fx["payload"]["amount_per_share"] = dict(
            ev["payload"]["amount_per_share"], currency="USD")
        self.assertEqual(
            ensemble.events_to_corporate_actions([fx], "POUL.CA", 10.0), [])
        # A missing issuer ticker is accepted: the feed file is
        # already per-ticker, so absence is not a mismatch.
        noticker = copy.deepcopy(ev)
        noticker["issuer"] = dict(ev["issuer"], ticker=None)
        self.assertEqual(
            len(ensemble.events_to_corporate_actions(
                [noticker], "POUL.CA", 10.0)), 1)

    def test_merge_supersedes_same_distribution(self):
        ev = _poul_event()
        event_actions = ensemble.events_to_corporate_actions(
            [ev], "POUL.CA", 10.0)
        # Legacy finds the same coupon (1.89 vs 1.9 is one coupon
        # under #131) with a DERIVED ex-date — the event wins.
        legacy = ensemble.detect_corporate_actions([_poul_doc()], 10.0, 2026)
        self.assertEqual(len(legacy), 1)
        self.assertEqual(legacy[0]["date_basis"], "entitlement+1")
        merged = ensemble.merge_corporate_actions(legacy, event_actions)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["source"], "disclosure-event")
        self.assertEqual(merged[0]["date_basis"], "verbatim:ex-date")
        self.assertEqual(merged[0]["ex_date"], "2026-11-16")
        # A genuinely different coupon (same DPS, different ex-date)
        # survives alongside the event action.
        other = dict(legacy[0], ex_date="2027-05-16",
                     entitlement_end="2027-05-15")
        merged = ensemble.merge_corporate_actions([other], event_actions)
        self.assertEqual(len(merged), 2)
        # An undated legacy mention of the same amount is superseded.
        undated = dict(legacy[0], ex_date=None, entitlement_end=None,
                       date_basis=None)
        merged = ensemble.merge_corporate_actions([undated], event_actions)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["source"], "disclosure-event")


class TestEndToEnd(unittest.TestCase):
    def test_legacy_only_then_event_then_blind_body(self):
        doc = _poul_doc()
        # A: legacy text detection only (no events file).
        sweep_a = _sweep_dir(doc, with_events=False)
        try:
            out_a = _run_ensemble(sweep_a)
        finally:
            shutil.rmtree(sweep_a, ignore_errors=True)
        self.assertEqual(len(out_a["corporate_actions"]), 1)
        a = out_a["corporate_actions"][0]
        self.assertEqual(a["date_basis"], "entitlement+1")
        self.assertNotIn("source", a)
        # B: the events file flows in — one action, verbatim basis,
        # same DPS / ex-date / mechanical % as the standalone #26 path.
        sweep_b = _sweep_dir(doc, with_events=True)
        try:
            out_b = _run_ensemble(sweep_b)
        finally:
            shutil.rmtree(sweep_b, ignore_errors=True)
        self.assertEqual(len(out_b["corporate_actions"]), 1)
        b = out_b["corporate_actions"][0]
        self.assertEqual(b["source"], "disclosure-event")
        self.assertEqual(b["date_basis"], "verbatim:ex-date")
        for key in ("dps", "ex_date", "entitlement_end", "mechanical_pct"):
            self.assertEqual(b[key], a[key], key)
        for horizon in ("day", "week", "month"):
            mark = out_b["horizons"][horizon].get("corporate_action")
            self.assertIsNotNone(mark, horizon)
            self.assertEqual(mark["ex_date"], "2026-11-16")
            self.assertEqual(mark["mechanical_pct"], -19.0)
            self.assertEqual(mark, out_a["horizons"][horizon]
                             .get("corporate_action"), horizon)
        # C: collected body blanked — legacy is blind, the event
        # still drives the identical dividend-aware adjustment.
        blind = copy.deepcopy(doc)
        blind["body"] = ""
        sweep_c = _sweep_dir(blind, with_events=True)
        try:
            out_c = _run_ensemble(sweep_c)
        finally:
            shutil.rmtree(sweep_c, ignore_errors=True)
        self.assertEqual(len(out_c["corporate_actions"]), 1)
        c = out_c["corporate_actions"][0]
        self.assertEqual(c["source"], "disclosure-event")
        for key in ("dps", "ex_date", "entitlement_end", "mechanical_pct"):
            self.assertEqual(c[key], b[key], key)
        for horizon in ("day", "week", "month"):
            self.assertEqual(
                out_c["horizons"][horizon].get("corporate_action"),
                out_b["horizons"][horizon].get("corporate_action"),
                horizon)

    def test_no_dividend_control(self):
        # No event, no dividend text anywhere: no actions, horizons
        # unmarked — the adapter changes nothing on a non-dividend
        # sweep.
        doc = _poul_doc()
        doc["title"] = "القاهرة للدواجن (POUL.CA) تعلن عن نتائج أعمال"
        doc["body"] = "اجتماع مجلس الإدارة وافق على القوائم المالية."
        sweep = _sweep_dir(doc, with_events=False)
        try:
            out = _run_ensemble(sweep)
        finally:
            shutil.rmtree(sweep, ignore_errors=True)
        self.assertEqual(out["corporate_actions"], [])
        for horizon in ("day", "week", "month"):
            self.assertNotIn("corporate_action",
                             out["horizons"][horizon])


if __name__ == "__main__":
    unittest.main(verbosity=2)
