#!/usr/bin/env python3
"""Regression tests for issue #357 F5 + F6 (INS-353-354 follow-up):

F5 — a staged disclosure-events feed repeating one event_id (with
  a shifted announced date) changed selection on the recommend
  path, because scripts/recommend.py never applied
  compile_model._validate_events_feed, which already rejects
  duplicate event_id. The fix validates the staged feed in main()
  before selection (failing feeds fall back to the legacy keyword
  path with the reason named in the notes) and fails closed inside
  events_to_reaction_triggers as well, so a conflicting feed
  yields no triggers for any caller. duplicate_links /
  possible-duplicate annotations on DISTINCT disclosures stay
  eligible — only event_id identity is checked.

F6 — fitted reaction coefficients are validated as finite numbers
  before consumption in select_reaction_nudge (both the verified
  and the legacy path): a non-numeric shrunk value used to raise
  TypeError, and NaN/inf propagated into the recommendation JSON
  as a bare NaN/Infinity literal. An unusable coefficient now
  behaves as unfitted (nudge 0.0, fall through), never a crash.

Every test below FAILS on base ee0d1b5d and PASSES with the fix.
Stdlib only, no network.

Run: python3 scripts/test_recommend_357.py (exit 0 = all pass).
"""
import copy
import json
import math
import os
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import disclosure_events  # noqa: E402
import recommend  # noqa: E402

_TMP = Path(tempfile.mkdtemp(prefix="gator357-test-"))
os.environ.setdefault("GATOR_ROOT", str(_TMP))

REAL_PROFILE = json.load(open(os.path.join(
    ROOT, "profiles", "POUL.CA.json"), encoding="utf-8"))

FITTED = {"dividend": {"shrunk_r5_adj": 3.46}}
ASOF = date(2026, 11, 8)


def _ev(event_id, announced, etype="dividend"):
    return {"event_id": event_id, "event_type": etype,
            "verification_status": "verified",
            "extraction_status": "extracted",
            "issuer": {"ticker": "POUL.CA"},
            "announced": {"value": announced}}


def _golden_event(name):
    with open(os.path.join(HERE, "disclosure_events_fixtures",
                           "fixtures.json"), encoding="utf-8") as f:
        data = json.load(f)
    for case in data["cases"]:
        if case["name"] == name:
            events, _report = disclosure_events.extract_feed(
                [copy.deepcopy(case["doc"])])
            assert len(events) == 1, (name, events)
            return events[0]
    raise AssertionError("fixture %s missing" % name)


class TestF5DuplicateEventId(unittest.TestCase):
    def test_duplicate_id_with_shifted_date_yields_no_triggers(self):
        dup = [_ev("ev-div-1102", "2026-11-02"),
               _ev("ev-div-1102", "2026-11-05")]
        self.assertEqual(
            recommend.events_to_reaction_triggers(dup, "POUL.CA"), [])

    def test_duplicate_id_does_not_change_selection(self):
        dup = [_ev("ev-div-1102", "2026-11-02"),
               _ev("ev-div-1102", "2026-11-05")]
        tr = recommend.events_to_reaction_triggers(dup, "POUL.CA")
        nudge, _note, trig = recommend.select_reaction_nudge(
            tr, [], FITTED, ASOF)
        self.assertEqual(nudge, 0.0)
        self.assertIsNone(trig)

    def test_distinct_ids_still_map(self):
        evs = [_ev("ev-div-1102", "2026-11-02"),
               _ev("ev-earn-1105", "2026-11-05", "earnings")]
        tr = recommend.events_to_reaction_triggers(evs, "POUL.CA")
        self.assertEqual(len(tr), 2)
        self.assertEqual({t["event_id"] for t in tr},
                         {"ev-div-1102", "ev-earn-1105"})

    def test_duplicate_links_annotations_on_distinct_events_stay(self):
        # duplicate_links / possible-duplicate annotations describe
        # DISTINCT disclosures — they must not be merged or dropped.
        first = _ev("ev-div-1102", "2026-11-02")
        first["duplicate_links"] = ["https://example.invalid/x"]
        first["possible_duplicate"] = True
        second = _ev("ev-div-1103", "2026-11-03")
        tr = recommend.events_to_reaction_triggers(
            [first, second], "POUL.CA")
        self.assertEqual(len(tr), 2)

    def test_events_without_ids_are_not_duplicates(self):
        # No identity, no conflict: two id-less events both map.
        first = _ev(None, "2026-11-02")
        del first["event_id"]
        second = _ev(None, "2026-11-03")
        del second["event_id"]
        tr = recommend.events_to_reaction_triggers(
            [first, second], "POUL.CA")
        self.assertEqual(len(tr), 2)

    def test_exact_duplicate_copy_also_rejected(self):
        # Even a byte-identical repeat is a duplicate event_id.
        dup = [_ev("ev-div-1102", "2026-11-02"),
               _ev("ev-div-1102", "2026-11-02")]
        self.assertEqual(
            recommend.events_to_reaction_triggers(dup, "POUL.CA"), [])


def _run_main(as_of, profile, feed, case):
    """Run the REAL recommend.main() with a stubbed archive (the
    #282 pattern): canned ensemble + canned profile/feed fetches,
    temp cwd. Returns the written recommendation JSON as text."""
    tmp = Path(tempfile.mkdtemp(prefix="borsagator-357-"))
    orig_argv, orig_cwd = sys.argv, os.getcwd()
    orig_ens, orig_fetch = (recommend.newest_ensemble,
                            recommend.fetch_text)
    orig_pin = recommend.PINNED_COMMIT
    try:
        os.chdir(tmp)
        recommend.PINNED_COMMIT = "testpin0123456789abcdef"
        recommend.newest_ensemble = lambda ticker: (
            {"ticker": "POUL.CA", "date": as_of, "base_price": 10.0,
             "horizons": {"week": {"expected_move_pct": 1.0,
                                   "range_low_pct": -2.0,
                                   "range_high_pct": 2.0,
                                   "confidence": 0.3}},
             "risk": {"level": "low"}, "weights_source": "builtin",
             "corporate_actions": []},
            "sweeps/2026-11-05-test")

        def _fetch(url, timeout=60):
            if "disclosure-events/POUL-events.json" in url:
                if feed is None:
                    raise RuntimeError("404")
                return json.dumps(feed, ensure_ascii=False)
            if "profiles/POUL.CA.json" in url:
                return json.dumps(profile, ensure_ascii=False)
            raise RuntimeError("unexpected url " + url)

        recommend.fetch_text = _fetch
        sys.argv = ["recommend.py", "POUL.CA"]
        case.assertEqual(recommend.main(), 0)
        out = tmp / "profiles" / "POUL.CA.recommendation.json"
        case.assertTrue(out.is_file(), "recommendation missing")
        return out.read_text(encoding="utf-8")
    finally:
        os.chdir(orig_cwd)
        sys.argv = orig_argv
        recommend.newest_ensemble = orig_ens
        recommend.fetch_text = orig_fetch
        recommend.PINNED_COMMIT = orig_pin


class TestF5EndToEnd(unittest.TestCase):
    """REAL recommend.main() with a stubbed archive, as in #282."""

    def _run(self, as_of, profile, feed):
        return _run_main(as_of, profile, feed, self)

    def _feed(self, *events):
        return {"schema_version": disclosure_events.SCHEMA_VERSION,
                "extractor_version": "test",
                "config_hash": "test",
                "quarter": {"start": "2026-08-19",
                            "end": "2026-11-19"},
                "report": {},
                "events": list(events)}

    def test_duplicate_feed_falls_back_to_legacy_with_named_reason(self):
        div = _golden_event("golden_poul_dividend")
        shifted = copy.deepcopy(div)
        shifted["announced"]["value"] = "2026-11-05"
        raw = self._run("2026-11-05", REAL_PROFILE,
                        self._feed(div, shifted))
        rec = json.loads(raw)
        # Legacy keyword path still nudges on the 2026-11-02 story
        # (age 3, +1.73) — the dead feed never loses a recommendation.
        self.assertEqual(rec["nudge_pct"], 1.73)
        self.assertIsNone(rec["reaction_trigger"])
        self.assertTrue(any("failed validation" in n
                            and "duplicate event_id" in n
                            for n in rec["notes"]))

    def test_valid_feed_still_selects_verified(self):
        div = _golden_event("golden_poul_dividend")
        raw = self._run("2026-11-05", REAL_PROFILE, self._feed(div))
        rec = json.loads(raw)
        self.assertEqual(rec["nudge_pct"], 1.73)
        self.assertEqual(rec["reaction_trigger"]["event_id"],
                         div["event_id"])


class TestF6FiniteCoefficients(unittest.TestCase):
    def test_non_numeric_shrunk_never_raises_verified_path(self):
        tr = recommend.events_to_reaction_triggers(
            [_ev("ev-div-1105", "2026-11-05")], "POUL.CA")
        for bad in ("3.46", None, [3.46], {"v": 3.46}):
            fitted = {"dividend": {"shrunk_r5_adj": bad}}
            nudge, note, trig = recommend.select_reaction_nudge(
                tr, [], fitted, ASOF)
            self.assertEqual(nudge, 0.0)
            self.assertIsNone(note)
            self.assertIsNone(trig)

    def test_nan_and_inf_never_propagate_verified_path(self):
        tr = recommend.events_to_reaction_triggers(
            [_ev("ev-div-1105", "2026-11-05")], "POUL.CA")
        for bad in (float("nan"), float("inf"), float("-inf")):
            fitted = {"dividend": {"shrunk_r5_adj": bad}}
            nudge, _note, trig = recommend.select_reaction_nudge(
                tr, [], fitted, ASOF)
            self.assertEqual(nudge, 0.0)
            self.assertTrue(math.isfinite(nudge))
            self.assertIsNone(trig)

    def test_bool_is_not_a_coefficient(self):
        tr = recommend.events_to_reaction_triggers(
            [_ev("ev-div-1105", "2026-11-05")], "POUL.CA")
        nudge, _note, trig = recommend.select_reaction_nudge(
            tr, [], {"dividend": {"shrunk_r5_adj": True}}, ASOF)
        self.assertEqual(nudge, 0.0)
        self.assertIsNone(trig)

    def test_non_numeric_shrunk_never_raises_legacy_path(self):
        legacy = [{"date": "2026-11-05", "type": "dividend"}]
        for bad in ("3.46", float("nan"), float("inf")):
            fitted = {"dividend": {"shrunk_r5_adj": bad}}
            nudge, note, trig = recommend.select_reaction_nudge(
                [], legacy, fitted, ASOF)
            self.assertEqual(nudge, 0.0)
            self.assertIsNone(trig)

    def test_valid_coefficients_still_nudge_both_paths(self):
        tr = recommend.events_to_reaction_triggers(
            [_ev("ev-div-1105", "2026-11-05")], "POUL.CA")
        nudge, _note, trig = recommend.select_reaction_nudge(
            tr, [], FITTED, ASOF)
        self.assertEqual(nudge, 1.73)
        self.assertIsNotNone(trig)
        legacy = [{"date": "2026-11-05", "type": "dividend"}]
        nudge, _note, trig = recommend.select_reaction_nudge(
            [], legacy, FITTED, ASOF)
        self.assertEqual(nudge, 1.73)
        self.assertIsNone(trig)

    def test_nan_coefficient_never_reaches_recommendation_json(self):
        # End to end: a NaN shrunk in the profile must not surface
        # as a bare NaN literal in the written recommendation.
        prof = {"ticker": "POUL.CA",
                "reaction_fit": {"by_type": {
                    "dividend": {"n": 5, "median_r5_adj": 5.93,
                                 "shrunk_r5_adj": float("nan")}}},
                "events": [{"date": "2026-11-02",
                            "type": "dividend"}],
                "walk_forward": {"hits": None, "baseline_hits": None}}
        feed = {"schema_version": disclosure_events.SCHEMA_VERSION,
                "extractor_version": "test", "config_hash": "test",
                "quarter": {"start": "2026-08-19",
                            "end": "2026-11-19"},
                "report": {}, "events": []}
        raw = _run_main("2026-11-05", prof, feed, self)
        self.assertNotIn("NaN", raw)
        self.assertNotIn("Infinity", raw)
        self.assertEqual(json.loads(raw)["nudge_pct"], 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
