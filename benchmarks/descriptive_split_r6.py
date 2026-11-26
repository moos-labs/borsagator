#!/usr/bin/env python3
"""Descriptive split experiment (INS-IMPROVE-006, Moos round 2 GO).

DESCRIPTIVE ONLY. No keep rule, no verdict, no fit, no CI. It answers
where the frozen v2 band (scripts/ensemble.py V2_BAND_K, unchanged)
behaves differently, by two splits of the scored rows:
  * liquidity proxy: share of zero-range bars (H == L) in the last 60
    pre-cutoff bars (0 vs > 0), and median 60-bar turnover
    (Volume x Close) above / below the sample median. Turnover is in
    each ticker's own currency (NVDA is USD, the rest EGP), so the
    zero-range split is the cleaner one and turnover is a rough guide.
  * limit hits: whether the ticker's pre-cutoff bars (last 250) hold at
    least one day within 0.5 pp of a +/-10% or +/-20% close-to-close
    move.
Metrics (coverage and RangeSkill of frozen v2) print for a bucket only
when it holds >= 30 rows; below that the bucket shows its row count
and nothing else ("counts only"). Counts always print.

The 10% / 20% limits (20% / 10% main board, 10% / 5% SME) are a
research note until a primary source confirms decree 681 of 2021. No
code path depends on them being right: they are two thresholds on
observed returns, and the report shows the counts at both.

"Within 0.5 pp of a limit" is read as |close / prev close - 1| >=
limit - 0.005; the intraday variant uses High or Low against the
previous close. Counts are taken from every bar in the captures'
indicator CSVs (de-duplicated by date per ticker, so they include
bars after some cutoffs; they are counts, not scoring inputs) and,
separately, from the longer price.csv closes (close-to-close only).

Usage:
  python3 benchmarks/descriptive_split_r6.py --captures DIR ...
      [--min-cell 48] [--json OUT]
"""
import argparse
import csv
import json
import os
import statistics
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import replay_band_candidates as R  # noqa: E402
import score_adoption_594 as A  # noqa: E402
import ensemble as ens_mod  # noqa: E402

HORIZONS = A.HORIZONS
MIN_BUCKET = 30
TOL = 0.005
LIMITS = (0.10, 0.20)
LOOKBACK = 250
LIQ_BARS = 60


def read_ohlcv(capture, base_date=None):
    """[(date, o, h, l, c, volume)] oldest first, dated <= base_date."""
    for rel in ("collected/pandas-ta/indicators.csv",
                "collected/talib/indicators.csv",
                "pandas-ta/indicators.csv"):
        path = os.path.join(capture, rel)
        if not os.path.exists(path):
            continue
        try:
            with open(path, newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
        except Exception:
            continue
        out = []
        for r in rows:
            r = {k.lower(): v for k, v in r.items()}
            d = str(r.get("date") or "")[:10]
            if not d or (base_date and d > base_date):
                continue
            v = [A.fnum(r.get(k)) for k in
                 ("open", "high", "low", "close")]
            if any(x is None for x in v):
                continue
            vol = A.fnum(r.get("volume"))
            out.append((d, v[0], v[1], v[2], v[3], vol or 0.0))
        if out:
            return out
    return []


def limit_counts(bars):
    """Counts over bars [(date, o, h, l, c, vol)], oldest first."""
    out = {"bars": len(bars),
           "zero_range": sum(1 for b in bars if b[2] == b[3])}
    for lim in LIMITS:
        key = "%d" % round(lim * 100)
        cc = hi = 0
        for prev, cur in zip(bars, bars[1:]):
            p = prev[4]
            if p <= 0:
                continue
            if abs(cur[4] / p - 1) >= lim - TOL:
                cc += 1
            if (cur[2] / p - 1 >= lim - TOL
                    or cur[3] / p - 1 <= -(lim - TOL)):
                hi += 1
        out["near_%s_close" % key] = cc
        out["near_%s_intraday" % key] = hi
    return out


def close_counts(closes):
    out = {"closes": len(closes)}
    for lim in LIMITS:
        key = "%d" % round(lim * 100)
        out["near_%s_close" % key] = sum(
            1 for a, b in zip(closes, closes[1:])
            if a > 0 and abs(b / a - 1) >= lim - TOL)
    return out


def capture_features(bars):
    """Pre-cutoff liquidity and limit features of one capture."""
    last = bars[-LIQ_BARS:]
    if len(last) < 20:
        return None
    zr = sum(1 for b in last if b[2] == b[3]) / len(last)
    tv = [b[4] * b[5] for b in last if b[5]]
    lc = limit_counts(bars[-LOOKBACK:])
    return {"zero_range_share": zr,
            "turnover": statistics.median(tv) if tv else None,
            "near_limit": (lc["near_10_close"] + lc["near_20_close"]) > 0}


def pair(r):
    h = r["horizon"]
    half = R.half_pct(r["v2_sigma"], h, ens_mod.V2_BAND_K[h], r["mult"])
    return {"horizon": h, "ticker": r["ticker"], "as_of": r["as_of"],
            "is_naive": R.row_is(r, r["naive_half"]),
            "is_v2": R.row_is(r, half),
            "in_v2": abs(r["real"]) <= half}


def bucket_stats(ps):
    n = len(ps)
    out = {"n": n, "tickers": len({p["ticker"] for p in ps}),
           "cutoffs": len({p["as_of"] for p in ps})}
    if n >= MIN_BUCKET:
        out["coverage"] = sum(p["in_v2"] for p in ps) / n
        out["range_skill"] = A.range_skill(ps, "v2")
    return out


def collect(capture_dirs, all_dirs, min_cell):
    recs = []
    for cap in capture_dirs:
        num = A.cell_number(cap)
        if num is None or num < min_cell:
            continue
        rows, _g = R.build_rows([cap], all_dirs)
        ens = R.bs.load_json(os.path.join(cap, "digest", "ensemble.json"))
        base = str((ens or {}).get("base_date") or "")[:10]
        feat = capture_features(read_ohlcv(cap, base))
        for r in rows:
            if r["v2_sigma"]:
                recs.append({"pair": pair(r), "feat": feat})
    return recs


def split(recs):
    withf = [x for x in recs if x["feat"]]
    tvs = [x["feat"]["turnover"] for x in withf
           if x["feat"]["turnover"]]
    med = statistics.median(tvs) if tvs else None
    defs = {
        "all rows": lambda f: True,
        "zero-range share = 0": lambda f: f["zero_range_share"] == 0,
        "zero-range share > 0": lambda f: f["zero_range_share"] > 0,
        "turnover >= median": lambda f: (f["turnover"] or 0) >= (med or 0),
        "turnover < median": lambda f: (f["turnover"] or 0) < (med or 0),
        "near-limit day in last 250 bars": lambda f: f["near_limit"],
        "no near-limit day in last 250 bars": lambda f: not f["near_limit"],
    }
    res = {"turnover_median": med}
    for name, fn in defs.items():
        res[name] = {}
        for h in HORIZONS:
            ps = [x["pair"] for x in withf
                  if x["pair"]["horizon"] == h and fn(x["feat"])]
            res[name][h] = bucket_stats(ps)
    return res


def per_ticker_counts(all_dirs):
    bars, closes = {}, {}
    for cap in all_dirs:
        t = os.path.basename(cap).upper()
        for b in read_ohlcv(cap):
            bars.setdefault(t, {})[b[0]] = b
    for t, pts in R.price_reference(all_dirs).items():
        closes[t] = [c for _d, c in pts]
    out = {}
    for t in sorted(set(bars) | set(closes)):
        o = {}
        if t in bars:
            o["ohlc"] = limit_counts([bars[t][d] for d in sorted(bars[t])])
        if t in closes:
            o["price_csv"] = close_counts(closes[t])
        out[t] = o
    return out


def render(res, counts, min_cell):
    L = ["DESCRIPTIVE ONLY, no verdict, no fit. Frozen v2 band, rows from "
         "cells >= %d. Metrics shown only for buckets with >= %d rows."
         % (min_cell, MIN_BUCKET)]
    for name, hs in res.items():
        if name == "turnover_median":
            continue
        L.append(name)
        for h in HORIZONS:
            b = hs[h]
            if "coverage" in b:
                L.append("  %s n=%d (%d tickers, %d cutoffs) coverage %.3f"
                         " RangeSkill %s" % (
                             h, b["n"], b["tickers"], b["cutoffs"],
                             b["coverage"],
                             "n/a" if b["range_skill"] is None
                             else "%+.3f" % b["range_skill"]))
            else:
                L.append("  %s n=%d (%d tickers, %d cutoffs) counts only"
                         % (h, b["n"], b["tickers"], b["cutoffs"]))
    L.append("per-ticker counts (limit values are a research note):")
    L.append("  ticker bars, zero-range (H == L) | OHLC within 0.5pp of "
             "10%: close/intraday, of 20%: close/intraday | price.csv "
             "closes, 10%/20% close")
    for t, o in counts.items():
        a, p = o.get("ohlc"), o.get("price_csv")
        L.append("  %s %s | %s | %s" % (
            t,
            "%d bars, %d zero-range" % (a["bars"], a["zero_range"])
            if a else "no OHLC",
            "%d/%d, %d/%d" % (a["near_10_close"], a["near_10_intraday"],
                              a["near_20_close"], a["near_20_intraday"])
            if a else "-",
            "%d closes, %d/%d" % (p["closes"], p["near_10_close"],
                                  p["near_20_close"]) if p else "-"))
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.
                                 RawDescriptionHelpFormatter)
    ap.add_argument("--captures", nargs="+", required=True)
    ap.add_argument("--min-cell", type=int, default=48)
    ap.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    allc = A.find_captures(a.captures, None)
    caps = [c for c in A.find_captures(a.captures, a.min_cell)
            if A.cell_number(c) is not None]
    res = split(collect(caps, allc, a.min_cell))
    counts = per_ticker_counts(allc)
    print(render(res, counts, a.min_cell))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump({"descriptive": True, "min_cell": a.min_cell,
                       "splits": res, "counts": counts}, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
