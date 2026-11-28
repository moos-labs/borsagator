#!/usr/bin/env python3
"""Tests for the round 147 crypto harvest and descriptive scorer. Fixed
synthetic inputs only; no network, no real crypto rows."""
import copy
import csv
import datetime as dt
import math
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "benchmarks"))
import fetch_crypto_ohlcv as F  # noqa: E402
import score_crypto_147 as S  # noqa: E402

D = dt.date


def ts(day):
    return int(dt.datetime(day.year, day.month, day.day,
                           tzinfo=dt.timezone.utc).timestamp())


def payload(days, gran="1d", mutate=None):
    """Chart v8 payload with one valid bar per day (open 100, high 102,
    low 98, close 101)."""
    n = len(days)
    p = {"chart": {"error": None, "result": [{
        "meta": {"dataGranularity": gran},
        "timestamp": [ts(d) for d in days],
        "indicators": {"quote": [{"open": [100.0] * n, "high": [102.0] * n,
                                  "low": [98.0] * n, "close": [101.0] * n,
                                  "volume": [5] * n}],
                       "adjclose": [{"adjclose": [101.0] * n}]}}]}}
    if mutate:
        mutate(p["chart"]["result"][0])
    return p


def run(days, today=D(2026, 1, 10), **kw):
    return F.parse_validate(payload(days, **kw), today)


class TestFetch(unittest.TestCase):
    DAYS = [D(2026, 1, 1) + dt.timedelta(days=i) for i in range(5)]

    def test_valid_and_partial_bar_dropped(self):
        rows, dropped = run(self.DAYS + [D(2026, 1, 10)], today=D(2026, 1, 10))
        self.assertEqual(len(rows), 5)
        self.assertEqual(dropped, 1)
        self.assertEqual(rows[-1]["date"], "2026-01-05")
        # a bar the day before today is kept
        rows, dropped = run(self.DAYS, today=D(2026, 1, 6))
        self.assertEqual((len(rows), dropped), (5, 0))
        rows, dropped = run(self.DAYS, today=D(2026, 1, 5))
        self.assertEqual((len(rows), dropped), (4, 1))

    def test_granularity_refused(self):
        with self.assertRaises(F.Refusal) as c:
            run(self.DAYS, gran="1mo")
        self.assertIn("dataGranularity", str(c.exception))

    def test_gap_refused_and_listed(self):
        d = self.DAYS[:2] + self.DAYS[3:]
        with self.assertRaises(F.Refusal) as c:
            run(d)
        self.assertIn("gap: 2026-01-04 follows 2026-01-02", str(c.exception))

    def test_duplicate_and_decreasing_refused(self):
        with self.assertRaises(F.Refusal):
            run([self.DAYS[0], self.DAYS[0], self.DAYS[1]])
        with self.assertRaises(F.Refusal):
            run([self.DAYS[1], self.DAYS[0]])

    def test_null_refused(self):
        def m(r):
            r["indicators"]["quote"][0]["low"][2] = None
        with self.assertRaises(F.Refusal) as c:
            run(self.DAYS, mutate=m)
        self.assertIn("null", str(c.exception))

    def test_bounds_and_nonpositive_close(self):
        def hi(r):
            r["indicators"]["quote"][0]["high"][1] = 100.5  # < close 101
        with self.assertRaises(F.Refusal):
            run(self.DAYS, mutate=hi)

        def lo(r):
            r["indicators"]["quote"][0]["low"][1] = 100.5  # > open 100
        with self.assertRaises(F.Refusal):
            run(self.DAYS, mutate=lo)

        def zero(r):
            q = r["indicators"]["quote"][0]
            q["close"][1] = 0.0
            q["low"][1] = -1.0
        with self.assertRaises(F.Refusal):
            run(self.DAYS, mutate=zero)
        # boundary: high == close and low == open are valid
        def edge(r):
            q = r["indicators"]["quote"][0]
            q["high"][1] = 101.0
            q["low"][1] = 100.0
        rows, _ = run(self.DAYS, mutate=edge)
        self.assertEqual(len(rows), 5)

    def test_timestamp_not_midnight_refused(self):
        def m(r):
            r["timestamp"][1] += 3600
        with self.assertRaises(F.Refusal):
            run(self.DAYS, mutate=m)

    def test_merge_append_only(self):
        rows, _ = run(self.DAYS)
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "x.csv")
            F.write_csv(p, rows)
            more, _ = run(self.DAYS + [D(2026, 1, 6)], today=D(2026, 1, 10))
            merged = F.merge_existing(p, more)
            self.assertEqual(len(merged), 6)
            changed = copy.deepcopy(more)
            changed[1]["close"] = 101.5
            with self.assertRaises(F.Refusal) as c:
                F.merge_existing(p, changed)
            self.assertIn("2026-01-02 close", str(c.exception))
            with open(p, newline="") as f:
                self.assertEqual(len(list(csv.DictReader(f))), 5)  # untouched
            with open(p) as f2:
                self.assertEqual(next(csv.reader(f2)), F.COLUMNS)


def alt_series(start, end):
    """close = 100*exp(0.01*(i % 2)): the 60 log returns alternate
    +0.01 / -0.01, so sigma60 is exactly 0.01."""
    out, i, d = {}, 0, start
    while d <= end:
        out[d] = 100.0 * math.exp(0.01 * (i % 2))
        d += dt.timedelta(days=1)
        i += 1
    return out


class TestScorer(unittest.TestCase):
    def test_cutoffs(self):
        cs = S.cutoffs()
        self.assertEqual(cs[0], D(2024, 1, 1))
        self.assertEqual(cs[1], D(2024, 1, 31))
        self.assertEqual(cs[-1], D(2025, 12, 21))
        self.assertEqual(len(cs), 25)
        self.assertEqual(S.cutoffs(D(2024, 1, 1), D(2024, 1, 31))[-1], D(2024, 1, 31))

    def test_sigma60_exact_and_window(self):
        cl = alt_series(D(2023, 1, 1), D(2026, 3, 1))
        self.assertAlmostEqual(S.sigma60(cl, D(2024, 1, 1)), 0.01, places=12)
        # uses bars <= C-1 only: perturb C itself, sigma unchanged
        cl2 = dict(cl)
        cl2[D(2024, 1, 1)] = 500.0
        self.assertEqual(S.sigma60(cl2, D(2024, 1, 1)), S.sigma60(cl, D(2024, 1, 1)))
        # and the oldest bar in the span (C-61) matters
        cl3 = dict(cl)
        cl3[D(2024, 1, 1) - dt.timedelta(days=61)] = 500.0
        self.assertNotEqual(S.sigma60(cl3, D(2024, 1, 1)), S.sigma60(cl, D(2024, 1, 1)))
        # C-62 is outside the span
        cl4 = dict(cl)
        cl4[D(2024, 1, 1) - dt.timedelta(days=62)] = 500.0
        self.assertEqual(S.sigma60(cl4, D(2024, 1, 1)), S.sigma60(cl, D(2024, 1, 1)))
        # a missing bar in the span -> None
        del cl[D(2023, 12, 15)]
        self.assertIsNone(S.sigma60(cl, D(2024, 1, 1)))

    def test_halves_use_frozen_constants(self):
        self.assertEqual((S.ens.V2_BAND_K["day"], S.ens.V2_BAND_K["week"],
                          S.ens.V2_BAND_K["month"]), (1.15, 1.28, 1.20))
        self.assertEqual(S.ens.V2_NAIVE_K, 1.2816)
        self.assertAlmostEqual(S.v2_half("day", 0.01), 0.0115, places=12)
        self.assertAlmostEqual(S.v2_half("week", 0.01), 0.0128 * math.sqrt(7), places=12)
        self.assertAlmostEqual(S.v2_half("month", 0.01), 0.012 * math.sqrt(30), places=12)
        self.assertAlmostEqual(S.naive_half("month", 0.01), 0.012816 * math.sqrt(30), places=12)

    def test_realised_bar_offsets_and_rows(self):
        cl = alt_series(D(2023, 1, 1), D(2026, 3, 1))
        c = D(2024, 1, 1)
        base = cl[c - dt.timedelta(days=1)]
        cl[c + dt.timedelta(days=0)] = base * 1.10      # day: bar C
        cl[c + dt.timedelta(days=6)] = base * 0.80      # week: bar C+6
        cl[c + dt.timedelta(days=29)] = base * 1.30     # month: bar C+29
        rows, excl = S.build_rows({"X": cl}, [c])
        self.assertEqual(excl, [])
        m = {r["h"]: r for r in rows}
        self.assertAlmostEqual(m["day"]["move"], 10.0, places=9)
        self.assertAlmostEqual(m["week"]["move"], -20.0, places=9)
        self.assertAlmostEqual(m["month"]["move"], 30.0, places=9)
        # day: half 1.15 pp, move 10 -> miss by 8.85, Winkler 2.3 + 10*8.85
        self.assertAlmostEqual(m["day"]["is_v2"], 2.3 + 10 * (10.0 - 1.15), places=9)
        self.assertFalse(m["day"]["in_v2"])
        self.assertAlmostEqual(m["day"]["is_naive"], 2 * 1.2816 + 10 * (10.0 - 1.2816), places=9)

    def test_in_range_boundary(self):
        cl = alt_series(D(2023, 1, 1), D(2026, 3, 1))
        c = D(2024, 1, 1)
        base = cl[c - dt.timedelta(days=1)]
        cl[c] = base * (1 + 0.011499)       # just inside +1.15 pp
        rows, _ = S.build_rows({"X": cl}, [c])
        self.assertTrue([r for r in rows if r["h"] == "day"][0]["in_v2"])
        cl[c] = base * (1 + 0.011501)
        rows, _ = S.build_rows({"X": cl}, [c])
        self.assertFalse([r for r in rows if r["h"] == "day"][0]["in_v2"])

    def test_inside_is_inclusive(self):
        self.assertTrue(S.inside(1.5, 1.5))
        self.assertTrue(S.inside(-1.5, 1.5))
        self.assertFalse(S.inside(1.5000001, 1.5))
        self.assertFalse(S.inside(-1.5000001, 1.5))

    def test_exclusions_listed_individually(self):
        cl = alt_series(D(2023, 1, 1), D(2024, 1, 20))     # ends before C+29
        rows, excl = S.build_rows({"X": cl}, [D(2024, 1, 1)])
        self.assertEqual([(e[2], e[3]) for e in excl], [("month", "no realised close")])
        self.assertEqual(len(rows), 2)
        # history rule: first bar 100 days before C-1 -> all three listed
        short = alt_series(D(2023, 9, 10), D(2024, 3, 1))
        rows, excl = S.build_rows({"X": short}, [D(2024, 1, 1)])
        self.assertEqual(rows, [])
        self.assertEqual(sorted(e[2] for e in excl), ["day", "month", "week"])
        # exactly 120 bars (first bar C-120 .. C-1) is accepted by the 120 rule
        # but still needs the 61-close sigma span, which it has
        ok = alt_series(D(2024, 1, 1) - dt.timedelta(days=120), D(2024, 3, 1))
        rows, excl = S.build_rows({"X": ok}, [D(2024, 1, 1)])
        self.assertEqual(len(rows), 3)
        ok119 = alt_series(D(2024, 1, 1) - dt.timedelta(days=119), D(2024, 3, 1))
        rows, excl = S.build_rows({"X": ok119}, [D(2024, 1, 1)])
        self.assertEqual(rows, [])

    def test_skill_and_coverage(self):
        rs = [{"is_v2": 8.0, "is_naive": 10.0, "in_v2": True, "in_naive": True},
              {"is_v2": 12.0, "is_naive": 10.0, "in_v2": False, "in_naive": True}]
        self.assertAlmostEqual(S.skill(rs), 0.0)
        rs[0]["is_v2"] = 5.0
        self.assertAlmostEqual(S.skill(rs), 1 - 17.0 / 20.0)
        self.assertEqual(S.cover(rs), 0.5)
        self.assertEqual(S.cover(rs, "in_naive"), 1.0)
        self.assertIsNone(S.skill([]))

    def test_bootstrap_clustered_and_deterministic(self):
        # two cutoffs, two assets each; cutoff blocks: draws can only take
        # whole cutoffs, so with distinct per-cutoff skill the draw set is
        # limited to the three possible cutoff mixes.
        rs = []
        for cut, v2 in (("2024-01-01", 5.0), ("2024-01-31", 15.0)):
            for a in ("A", "B"):
                rs.append({"asset": a, "cutoff": cut, "h": "day", "is_v2": v2,
                           "is_naive": 10.0, "in_v2": v2 < 10, "in_naive": True})
        sci, cci, nd = S.boot(rs, reps=400, seed=7)
        self.assertEqual(nd, 400)
        self.assertEqual((sci, cci), S.boot(rs, reps=400, seed=7)[:2])
        self.assertAlmostEqual(sci[0], -0.5)   # both draws pick cutoff 2
        self.assertAlmostEqual(sci[1], 0.5)    # both draws pick cutoff 1
        self.assertEqual(cci, (0.0, 1.0))
        self.assertEqual(S.boot([], 10, 1), ((None, None), (None, None), 0))

    def test_summary_counts_and_pooled_cluster(self):
        cl = alt_series(D(2023, 1, 1), D(2026, 3, 1))
        cuts = S.cutoffs(D(2024, 1, 1), D(2024, 3, 1))   # 3 cutoffs
        rows, _ = S.build_rows({"BTC-USD": cl, "ETH-USD": dict(cl)}, cuts)
        res = S.summarise(rows, reps=50, seed=3)
        self.assertEqual(len(res), 9)
        pooled = [r for r in res if r["asset"] == "BTC+ETH pooled" and r["horizon"] == "day"][0]
        self.assertEqual((pooled["n"], pooled["clusters"]), (6, 3))
        one = [r for r in res if r["asset"] == "BTC-USD" and r["horizon"] == "day"][0]
        self.assertEqual((one["n"], one["clusters"]), (3, 3))
        self.assertEqual(one["launch_gate_target"], 0.10)

    def test_render_has_no_verdict_word(self):
        cl = alt_series(D(2023, 1, 1), D(2026, 3, 1))
        rows, excl = S.build_rows({"BTC-USD": cl, "ETH-USD": dict(cl)},
                                  S.cutoffs(D(2024, 1, 1), D(2024, 3, 1)))
        text = S.render(S.summarise(rows, 20, 1), excl, 20, 1).lower()
        for w in ("keep eligible", "adopt", "pass", "fail", "verdict:", "reject"):
            self.assertNotIn(w, text.replace("no verdict word, no keep", ""))
        self.assertIn("launch-gate target +0.10, point estimate", text)


if __name__ == "__main__":
    unittest.main()
