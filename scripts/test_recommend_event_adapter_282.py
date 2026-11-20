#!/usr/bin/env python3
"""Tests for issue #282: feed #109 disclosure events into #32
reaction-profile selection (scripts/recommend.py).

Unit level: `events_to_reaction_triggers` (field mapping + gating)
and `select_reaction_nudge` (verified-first precedence, freshness
window, legacy fallback) in scripts/recommend.py.

End to end: the REAL recommend.main() runs with a stubbed archive
(canned newest ensemble + canned profile/feed fetches) in a temp
cwd, on the REAL #109 golden events (POUL coupon 42 dividend,
9M earnings, EGM call) and the REAL committed POUL profile:
  A. no feed file — legacy keyword path only: the 2026-11-02
     dividend story nudges +1.73 (the baseline the verified path
     must match with better provenance);
  B. feed with the real verified dividend event (announced
     2026-11-02) — the same dividend profile is selected, nudge
     +1.73, now named as a verified event with its event_id;
  C. blind-body proof: a profile whose only fresh event is the
     AGM story keyword-classified "other" (mirroring the real
     2026-10-19 AGM story the classifier left as "other") — legacy
     finds nothing (nudge 0.0); with the feed, the verified
     dividend event selects the profile (+1.73);
  D. feed with the real verified earnings event (announced
     2026-11-12) + a fitted-earnings profile — nudge -1.00;
  E. precedence: a fresher keyword earnings event loses to an older
     VERIFIED dividend event;
  F. feed with the real verified EGM call (announced 2026-11-08) +
     a fitted-governance profile — nudge +0.75; the candidate board
     event in the same feed is ignored;
  G. malformed feed — legacy path unchanged, recommendation still
     produced (a dead feed never loses a recommendation).
Plus a no-event control (no feed, no fresh events) proving no
regression on event-free sweeps: nudge == 0.0.

Stdlib only, no network. Run:
python3 scripts/test_recommend_event_adapter_282.py
"""
import copy
import json
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

REAL_PROFILE = json.load(open(os.path.join(
    ROOT, "profiles", "POUL.CA.json"), encoding="utf-8"))


def _golden_events(name):
    with open(os.path.join(HERE, "disclosure_events_fixtures",
                           "fixtures.json"), encoding="utf-8") as f:
        data = json.load(f)
    for case in data["cases"]:
        if case["name"] == name:
            events, _report = disclosure_events.extract_feed(
                [copy.deepcopy(case["doc"])])
            return events
    raise AssertionError("fixture %s missing" % name)


def _event(name):
    evs = _golden_events(name)
    assert len(evs) == 1, (name, evs)
    return evs[0]


def _canned_ensemble(as_of, expected=1.0):
    return {
        "ticker": "POUL.CA", "date": as_of, "base_price": 10.0,
        "horizons": {"week": {"expected_move_pct": expected,
                              "range_low_pct": -2.0,
                              "range_high_pct": 2.0,
                              "confidence": 0.3}},
        "risk": {"level": "low"}, "weights_source": "builtin",
        "corporate_actions": []}


def _crafted_profile(fitted, events):
    return {"ticker": "POUL.CA",
            "reaction_fit": {"by_type": fitted},
            "events": events,
            "walk_forward": {"hits": None, "baseline_hits": None}}


class TestEventMapping(unittest.TestCase):
    def test_real_events_map(self):
        div = _event("golden_poul_dividend")
        tr = recommend.events_to_reaction_triggers([div], "POUL.CA")
        self.assertEqual(len(tr), 1)
        self.assertEqual(tr[0]["profile_type"], "dividend")
        self.assertEqual(tr[0]["announced"], "2026-11-02")
        self.assertEqual(tr[0]["event_id"], div["event_id"])
        self.assertEqual(tr[0]["source"], "disclosure-event")

        earn = _event("golden_poul_earnings_consolidated")
        tr = recommend.events_to_reaction_triggers([earn], "POUL.CA")
        self.assertEqual(len(tr), 1)
        self.assertEqual(tr[0]["profile_type"], "earnings")
        self.assertEqual(tr[0]["announced"], "2026-11-12")

        egm = _event("golden_poul_egm_call")
        tr = recommend.events_to_reaction_triggers([egm], "POUL.CA")
        self.assertEqual(len(tr), 1)
        self.assertEqual(tr[0]["profile_type"], "governance")
        self.assertEqual(tr[0]["announced"], "2026-11-08")
        self.assertEqual(tr[0]["subtype"], "egm_call")

    def test_board_decisions_maps_to_management(self):
        egm = _event("golden_poul_egm_call")
        board = copy.deepcopy(egm)
        board["subtype"] = "board_decisions"
        tr = recommend.events_to_reaction_triggers([board], "POUL.CA")
        self.assertEqual(len(tr), 1)
        self.assertEqual(tr[0]["profile_type"], "management")

    def test_gates(self):
        div = _event("golden_poul_dividend")
        # candidate board event: unverified + candidate -> never fed
        cand = _event("candidate_poul_board")
        self.assertEqual(
            recommend.events_to_reaction_triggers([cand], "POUL.CA"),
            [])
        cases = []
        unverified = copy.deepcopy(div)
        unverified["verification_status"] = "unverified"
        cases.append(("unverified", unverified))
        candidate = copy.deepcopy(div)
        candidate["extraction_status"] = "candidate"
        cases.append(("candidate extraction", candidate))
        wrong_ticker = copy.deepcopy(div)
        wrong_ticker["issuer"] = dict(div["issuer"], ticker="COMI.CA")
        cases.append(("wrong ticker", wrong_ticker))
        no_date = copy.deepcopy(div)
        no_date["announced"] = {"value": None}
        cases.append(("no announced date", no_date))
        bad_date = copy.deepcopy(div)
        bad_date["announced"] = {"value": "not-a-date"}
        cases.append(("bad announced date", bad_date))
        unknown = copy.deepcopy(div)
        unknown["event_type"] = "merger"
        cases.append(("unknown event type", unknown))
        board_unknown = copy.deepcopy(div)
        board_unknown["event_type"] = "board_decision"
        board_unknown["subtype"] = "mystery"
        cases.append(("board_decision, unknown subtype", board_unknown))
        for name, ev in cases:
            with self.subTest(name=name):
                self.assertEqual(
                    recommend.events_to_reaction_triggers([ev], "POUL.CA"),
                    [])
        # missing ticker is accepted (feed file is already per-ticker)
        no_ticker = copy.deepcopy(div)
        no_ticker["issuer"] = {}
        self.assertEqual(
            len(recommend.events_to_reaction_triggers([no_ticker],
                                                      "POUL.CA")), 1)
        # non-dict rows are skipped, never raise
        self.assertEqual(
            len(recommend.events_to_reaction_triggers(
                ["junk", None, div], "POUL.CA")), 1)
        self.assertEqual(
            recommend.events_to_reaction_triggers([], "POUL.CA"), [])
        self.assertEqual(
            recommend.events_to_reaction_triggers(None, "POUL.CA"), [])


class TestSelection(unittest.TestCase):
    FITTED = {"dividend": {"shrunk_r5_adj": 3.46},
              "earnings": {"shrunk_r5_adj": -2.0},
              "governance": {"shrunk_r5_adj": 1.5},
              "management": {"shrunk_r5_adj": 0.8}}

    def test_verified_first_over_newer_keyword(self):
        # Keyword earnings (age 2) is NEWER than the verified dividend
        # (age 3) — the verified trigger still wins.
        trig = [{"profile_type": "dividend", "announced": "2026-11-02",
                 "event_id": "ev-div", "event_type": "dividend",
                 "subtype": "cash_dividend", "source": "disclosure-event"}]
        prof = [{"date": "2026-11-03", "type": "earnings"}]
        nudge, note, tr = recommend.select_reaction_nudge(
            trig, prof, self.FITTED, date(2026, 11, 5))
        self.assertEqual(nudge, 1.73)
        self.assertIn("verified dividend disclosure event", note)
        self.assertIn("ev-div", note)
        self.assertEqual(tr["event_id"], "ev-div")

    def test_freshness_window(self):
        trig = [{"profile_type": "dividend", "announced": "2026-11-02",
                 "event_id": "ev-div", "event_type": "dividend",
                 "subtype": "cash_dividend", "source": "disclosure-event"}]
        # age 0 (same day) and age 5 (boundary) both fresh
        for asof in (date(2026, 11, 2), date(2026, 11, 7)):
            nudge, note, _ = recommend.select_reaction_nudge(
                trig, [], self.FITTED, asof)
            self.assertEqual(nudge, 1.73, asof)
        # age 6: stale; future announcement: skipped
        for asof in (date(2026, 11, 8), date(2026, 11, 1)):
            nudge, note, _ = recommend.select_reaction_nudge(
                trig, [], self.FITTED, asof)
            self.assertEqual(nudge, 0.0, asof)
            self.assertIsNone(note)

    def test_unfitted_verified_falls_through_to_legacy(self):
        # Verified earnings, but earnings has no fitted value: the
        # legacy keyword dividend event (age 3) still selects.
        trig = [{"profile_type": "earnings", "announced": "2026-11-03",
                 "event_id": "ev-earn", "event_type": "earnings",
                 "subtype": "results_9m", "source": "disclosure-event"}]
        fitted = {"dividend": {"shrunk_r5_adj": 3.46}}
        prof = [{"date": "2026-11-02", "type": "dividend"}]
        nudge, note, tr = recommend.select_reaction_nudge(
            trig, prof, fitted, date(2026, 11, 5))
        self.assertEqual(nudge, 1.73)
        self.assertIsNone(tr)
        self.assertIn("fresh dividend event", note)

    def test_legacy_path_unchanged(self):
        # No verified triggers: the legacy loop behaves exactly as
        # before, including the note text and the "other" exclusion.
        prof = [{"date": "2026-11-03", "type": "other"},
                {"date": "2026-11-02", "type": "dividend"}]
        nudge, note, tr = recommend.select_reaction_nudge(
            [], prof, self.FITTED, date(2026, 11, 5))
        self.assertEqual(nudge, 1.73)
        self.assertIsNone(tr)
        self.assertEqual(
            note, "fresh dividend event (2026-11-02, 3d before the "
                  "ensemble): shrunk reaction +3.46% x 0.5 decay = "
                  "+1.73% nudge")
        nudge, note, tr = recommend.select_reaction_nudge(
            [], [], self.FITTED, date(2026, 11, 5))
        self.assertEqual((nudge, note, tr), (0.0, None, None))
        nudge, note, tr = recommend.select_reaction_nudge(
            [], prof, self.FITTED, None)
        self.assertEqual((nudge, note, tr), (0.0, None, None))

    def test_verified_newest_wins_within_verified(self):
        trig = [
            {"profile_type": "dividend", "announced": "2026-11-02",
             "event_id": "ev-div", "event_type": "dividend",
             "subtype": "cash_dividend", "source": "disclosure-event"},
            {"profile_type": "earnings", "announced": "2026-11-03",
             "event_id": "ev-earn", "event_type": "earnings",
             "subtype": "results_9m", "source": "disclosure-event"}]
        nudge, note, tr = recommend.select_reaction_nudge(
            trig, [], self.FITTED, date(2026, 11, 5))
        self.assertEqual(nudge, -1.0)
        self.assertEqual(tr["event_id"], "ev-earn")


class TestEndToEnd(unittest.TestCase):
    """REAL recommend.main() with a stubbed archive: canned newest
    ensemble + canned profile/feed fetches, temp cwd."""

    def _run(self, as_of, profile, feed):
        tmp = Path(tempfile.mkdtemp(prefix="borsagator-282-"))
        orig_argv, orig_cwd = sys.argv, os.getcwd()
        orig_ens, orig_fetch = (recommend.newest_ensemble,
                                recommend.fetch_text)
        orig_pin = recommend.PINNED_COMMIT
        try:
            os.chdir(tmp)
            recommend.PINNED_COMMIT = "testpin0123456789abcdef"
            recommend.newest_ensemble = lambda ticker: (
                _canned_ensemble(as_of), "sweeps/2026-11-05-test")

            def _fetch(url, timeout=60):
                if "disclosure-events/POUL-events.json" in url:
                    if feed is None:
                        raise RuntimeError("404")
                    if isinstance(feed, str):
                        return feed  # malformed feed case
                    return json.dumps(feed, ensure_ascii=False)
                if "profiles/POUL.CA.json" in url:
                    return json.dumps(profile, ensure_ascii=False)
                raise RuntimeError("unexpected url " + url)

            recommend.fetch_text = _fetch
            sys.argv = ["recommend.py", "POUL.CA"]
            self.assertEqual(recommend.main(), 0)
            out = tmp / "profiles" / "POUL.CA.recommendation.json"
            self.assertTrue(out.is_file(), "recommendation missing")
            with open(out, encoding="utf-8") as f:
                return json.load(f)
        finally:
            os.chdir(orig_cwd)
            sys.argv = orig_argv
            recommend.newest_ensemble = orig_ens
            recommend.fetch_text = orig_fetch
            recommend.PINNED_COMMIT = orig_pin

    def _feed(self, *events):
        return {"schema_version": disclosure_events.SCHEMA_VERSION,
                "events": list(events)}

    def test_A_no_feed_legacy_only(self):
        # Baseline: the legacy keyword path nudges on the 2026-11-02
        # dividend story (age 3) — the verified path must match this
        # value in run B, with authoritative provenance.
        rec = self._run("2026-11-05", REAL_PROFILE, None)
        self.assertEqual(rec["nudge_pct"], 1.73)
        self.assertEqual(rec["expected_week_adj_pct"], 2.73)
        self.assertIsNone(rec["reaction_trigger"])
        self.assertTrue(any("fresh dividend event (2026-11-02, 3d "
                            in n for n in rec["notes"]))
        self.assertNotIn("verified", " ".join(rec["notes"]))

    def test_B_verified_dividend_selects_profile(self):
        div = _event("golden_poul_dividend")
        rec = self._run("2026-11-05", REAL_PROFILE,
                        self._feed(div))
        self.assertEqual(rec["nudge_pct"], 1.73)
        self.assertEqual(rec["expected_week_adj_pct"], 2.73)
        trig = rec["reaction_trigger"]
        self.assertEqual(trig["profile_type"], "dividend")
        self.assertEqual(trig["event_id"], div["event_id"])
        self.assertTrue(any("verified dividend disclosure event" in n
                            and div["event_id"] in n
                            for n in rec["notes"]))
        # no buy/sell/hold wording in the notes (compile_model R-10)
        import re
        self.assertFalse(any(
            re.search(r"\b(buy|sell|hold)\b", n, re.IGNORECASE)
            for n in rec["notes"]))

    def test_C_blind_body_verified_sees_what_legacy_misses(self):
        # The AGM story keyword-classified "other" mirrors the real
        # 2026-10-19 AGM story in the committed profile, which the
        # classifier left as "other" (never nudges). With only that
        # event fresh, legacy finds nothing.
        other_agm = {
            "date": "2026-11-02", "type": "other",
            "title": "العنوان: القاهرة للدواجن (POUL.CA) - ملخص "
                     "قرارات الجمعية العامة العادية"}
        prof = _crafted_profile(
            {"dividend": {"n": 5, "median_r5_adj": 5.93,
                          "shrunk_r5_adj": 3.46}}, [other_agm])
        rec = self._run("2026-11-05", prof, None)
        self.assertEqual(rec["nudge_pct"], 0.0)
        self.assertIsNone(rec["reaction_trigger"])
        div = _event("golden_poul_dividend")
        rec = self._run("2026-11-05", prof, self._feed(div))
        self.assertEqual(rec["nudge_pct"], 1.73)
        self.assertEqual(rec["reaction_trigger"]["event_id"],
                         div["event_id"])

    def test_D_verified_earnings_with_fitted_profile(self):
        earn = _event("golden_poul_earnings_consolidated")
        prof = _crafted_profile(
            {"earnings": {"n": 4, "median_r5_adj": -2.5,
                          "shrunk_r5_adj": -2.0}}, [])
        rec = self._run("2026-11-13", prof, self._feed(earn))
        self.assertEqual(rec["nudge_pct"], -1.0)
        self.assertEqual(rec["expected_week_adj_pct"], 0.0)
        self.assertEqual(rec["reaction_trigger"]["profile_type"],
                         "earnings")

    def test_E_precedence_verified_beats_fresher_keyword(self):
        div = _event("golden_poul_dividend")
        prof = _crafted_profile(
            {"dividend": {"n": 5, "median_r5_adj": 5.93,
                          "shrunk_r5_adj": 3.46},
             "earnings": {"n": 4, "median_r5_adj": -2.5,
                          "shrunk_r5_adj": -2.0}},
            [{"date": "2026-11-03", "type": "earnings"}])
        rec = self._run("2026-11-05", prof, self._feed(div))
        self.assertEqual(rec["nudge_pct"], 1.73)
        self.assertEqual(rec["reaction_trigger"]["event_id"],
                         div["event_id"])

    def test_F_egm_call_selects_governance(self):
        egm = _event("golden_poul_egm_call")
        cand = _event("candidate_poul_board")
        prof = _crafted_profile(
            {"governance": {"n": 3, "median_r5_adj": 2.0,
                            "shrunk_r5_adj": 1.5}}, [])
        rec = self._run("2026-11-09", prof, self._feed(egm, cand))
        self.assertEqual(rec["nudge_pct"], 0.75)
        self.assertEqual(rec["reaction_trigger"]["profile_type"],
                         "governance")
        self.assertEqual(rec["reaction_trigger"]["event_id"],
                         egm["event_id"])

    def test_G_malformed_feed_legacy_unchanged(self):
        rec = self._run("2026-11-05", REAL_PROFILE, "not json{{{")
        self.assertEqual(rec["nudge_pct"], 1.73)
        self.assertIsNone(rec["reaction_trigger"])
        rec = self._run("2026-11-05", REAL_PROFILE,
                        {"events": "not-a-list"})
        self.assertEqual(rec["nudge_pct"], 1.73)

    def test_control_no_event_no_feed(self):
        prof = _crafted_profile({}, [])
        rec = self._run("2026-11-05", prof, None)
        self.assertEqual(rec["nudge_pct"], 0.0)
        self.assertEqual(rec["action"], "hold")


if __name__ == "__main__":
    unittest.main(verbosity=2)
