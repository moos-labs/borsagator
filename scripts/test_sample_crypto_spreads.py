#!/usr/bin/env python3
"""Tests for the crypto spread sampler. Fixed synthetic payloads, no network."""
import datetime as dt
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sample_crypto_spreads as S  # noqa: E402

NOW = dt.datetime(2026, 11, 28, 12, 0, 0, tzinfo=dt.timezone.utc)


def fake(url):
    if "coinbase" in url:
        return {"bid": "100.00", "ask": "100.10", "time": "t"}
    return {"error": [], "result": {"XXBTZUSD": {"b": ["200.0", "1", "1"], "a": ["200.2", "1", "1"]}}}


class T(unittest.TestCase):
    def test_spread_math(self):
        r = S.make_row("v", "P", "ts", 100.0, 100.10)
        self.assertAlmostEqual(r["mid"], 100.05)
        self.assertAlmostEqual(r["spread_bp"], 0.10 / 100.05 * 1e4, places=9)
        self.assertIsNone(r["error"])
        z = S.make_row("v", "P", "ts", 100.0, 100.0)   # locked book: valid, 0 bp
        self.assertEqual((z["spread_bp"], z["error"]), (0.0, None))

    def test_invalid_quotes_recorded_not_dropped(self):
        c = S.make_row("v", "P", "ts", 100.1, 100.0)
        self.assertEqual((c["spread_bp"], c["error"]), (None, "crossed book (ask < bid)"))
        n = S.make_row("v", "P", "ts", 0.0, 1.0)
        self.assertEqual(n["error"], "non-positive bid/ask")

    def test_parse_quote(self):
        self.assertEqual(S.parse_quote("coinbase", {"bid": "1", "ask": "2", "time": "t"}), (1.0, 2.0, "t"))
        self.assertEqual(S.parse_quote("kraken", fake("kraken"))[:2], (200.0, 200.2))
        with self.assertRaises(ValueError):
            S.parse_quote("kraken", {"error": ["EQuery:Unknown asset pair"], "result": {}})
        two = {"error": [], "result": {"A": {"b": ["1"], "a": ["2"]}, "B": {"b": ["1"], "a": ["2"]}}}
        with self.assertRaises(ValueError):
            S.parse_quote("kraken", two)
        with self.assertRaises(ValueError):
            S.parse_quote("other", {})

    def test_snapshot_rows_and_failure_listed(self):
        rows = S.snapshot(fake, NOW)
        self.assertEqual(len(rows), 4)
        self.assertEqual({r["ts_utc"] for r in rows}, {"2026-11-28T12:00:00Z"})
        self.assertEqual(sorted((r["venue"], r["pair"]) for r in rows),
                         [("coinbase", "BTC-USD"), ("coinbase", "ETH-USD"), ("kraken", "BTC-USD"), ("kraken", "ETH-USD")])

        def boom(url):
            if "ETH" in url or "pair=ETH" in url:
                raise OSError("down")
            return fake(url)
        rows = S.snapshot(boom, NOW)
        bad = [r for r in rows if r["error"]]
        self.assertEqual(len(rows), 4)
        self.assertEqual(sorted(r["pair"] for r in bad), ["ETH-USD", "ETH-USD"])
        self.assertTrue(all(r["spread_bp"] is None and r["error"].startswith("OSError") for r in bad))

    def test_append_and_summarise_counts_then_percentiles(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "sub", "s.jsonl")
            for i in range(3):
                S.append(p, S.snapshot(fake, NOW + dt.timedelta(hours=i)))
            with open(p) as f:
                self.assertEqual(len(f.readlines()), 12)      # appended, not overwritten
            out = S.summarise(p)
            e = out["coinbase BTC-USD"]
            self.assertEqual((e["n_valid"], e["n_error"]), (3, 0))
            self.assertIn("counts only", e["note"])
            self.assertNotIn("spread_bp_percentiles", e)
            # exactly MIN_SAMPLES valid rows unlock percentiles (boundary)
            q = os.path.join(d, "q.jsonl")
            rows = [S.make_row("v", "P", "t%d" % i, 100.0, 100.0 + (i + 1) * 0.01) for i in range(S.MIN_SAMPLES)]
            S.append(q, rows)
            self.assertIn("spread_bp_percentiles", S.summarise(q)["v P"])
            q2 = os.path.join(d, "q2.jsonl")
            S.append(q2, rows[:-1])
            self.assertNotIn("spread_bp_percentiles", S.summarise(q2)["v P"])

    def test_percentile_nearest_rank(self):
        v = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        self.assertEqual(S.percentile(v, 50), 5)
        self.assertEqual(S.percentile(v, 51), 6)
        self.assertEqual(S.percentile(v, 99), 10)
        self.assertEqual(S.percentile(v, 5), 1)

    def test_fee_json_is_well_formed(self):
        p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "evaluation", "crypto_fee_schedules.json")
        d = json.load(open(p))
        k = d["kraken"]["spot_maker_taker_pct"]
        self.assertEqual(len(k), 17)
        self.assertEqual(k["1 ($0+)"], [0.40, 0.80])
        tk = [v[1] for v in k.values()]
        self.assertEqual(tk, sorted(tk, reverse=True))    # taker falls with tier
        self.assertIn("NOT_OBTAINED", d["coinbase"])


if __name__ == "__main__":
    unittest.main()
