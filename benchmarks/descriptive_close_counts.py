#!/usr/bin/env python3
"""Descriptive close-count audit (INS-IMPROVE-007, Moos round 16 GO).

DESCRIPTIVE ONLY. No keep rule, no verdict, no fit, no CI. Per ticker,
from the archive's egxpy daily OHLC files (Date, Open, High, Low, Close):
  * flat_close: sessions whose close equals the previous session's close
    (exact float equality of the file's values);
  * outside_hl: sessions whose close lies outside that session's own
    [low, high] (close < low or close > high, strict);
  * zero_range: sessions with high == low (reference, as in #773).

Window rule: only sessions dated <= 2023-12-28 are counted, so no
verdict-cell window (cells 91+, and the forward ledger) is touched.
Sessions are split at 2021-09-05 (price-limit regime change): "pre" is
sessions before it, "post" is 2021-09-05 onward. The one session whose
previous session lies before the break is a straddle: it is excluded
from flat_close in both regimes and reported as "straddle_dropped"
(outside_hl uses one session only, so it is assigned by its own date).
Effective n per cell is the "sessions" count (flat_close uses
"pairs" = sessions with a previous session in the same regime).

When a ticker has several egxpy files in the archive, the one with the
most rows wins (ties: lexically latest path); duplicate dates keep the
last row. Rows with a non-numeric field are dropped and counted.

Usage:
  python3 benchmarks/descriptive_close_counts.py --archive DIR
      [--json OUT]
"""
import argparse
import csv
import json
import os
import sys

sys.dont_write_bytecode = True

BREAK_DATE = "2021-09-05"
LAST_DATE = "2023-12-28"   # windows ending <= this are verdict-safe


def read_ohlc(path):
    """({date: (o, h, l, c)}, dropped) from one egxpy csv."""
    out, dropped = {}, 0
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            r = {k.strip().lower(): v for k, v in r.items() if k}
            d = str(r.get("date") or "")[:10]
            try:
                v = tuple(float(r[k]) for k in
                          ("open", "high", "low", "close"))
            except (KeyError, TypeError, ValueError):
                dropped += 1
                continue
            if not d:
                dropped += 1
                continue
            out[d] = v
    return out, dropped


def find_files(archive):
    """{TICKER: path}: most rows wins, ties go to the latest path."""
    best = {}
    for dp, dn, fn in os.walk(archive):
        for f in fn:
            if f.startswith("egxpy_") and f.endswith(".csv"):
                t = f[6:-4].upper()
                p = os.path.join(dp, f)
                with open(p, encoding="utf-8") as fh:
                    n = sum(1 for _ in fh)
                if t not in best or (n, p) > best[t][0]:
                    best[t] = ((n, p), p)
    return {t: v[1] for t, v in sorted(best.items())}


def count(bars):
    """bars: {date: (o, h, l, c)}. Counts per regime, dates <= LAST_DATE."""
    dates = sorted(d for d in bars if d <= LAST_DATE)
    res = {rg: {"sessions": 0, "pairs": 0, "flat_close": 0,
                "outside_hl": 0, "zero_range": 0}
           for rg in ("pre", "post")}
    straddle = 0
    prev = None
    for d in dates:
        rg = "pre" if d < BREAK_DATE else "post"
        o, h, l, c = bars[d]
        r = res[rg]
        r["sessions"] += 1
        if c < l or c > h:
            r["outside_hl"] += 1
        if h == l:
            r["zero_range"] += 1
        if prev is not None:
            if prev[0] < BREAK_DATE <= d:
                straddle += 1
            else:
                r["pairs"] += 1
                if c == prev[1]:
                    r["flat_close"] += 1
        prev = (d, c)
    res["straddle_dropped"] = straddle
    res["first"] = dates[0] if dates else None
    res["last"] = dates[-1] if dates else None
    return res


def run(archive):
    out = {"break_date": BREAK_DATE, "last_date": LAST_DATE,
           "descriptive": True, "tickers": {}}
    for t, p in find_files(archive).items():
        bars, dropped = read_ohlc(p)
        r = count(bars)
        r["rows_dropped"] = dropped
        r["source"] = os.path.relpath(p, archive)
        out["tickers"][t] = r
    return out


def render(res):
    L = ["Descriptive close counts (no verdict). Sessions <= %s, split "
         "at %s." % (res["last_date"], res["break_date"]),
         "%-8s %-5s %8s %7s %6s %6s %6s" % (
             "ticker", "reg", "sessions", "pairs", "flat", "outHL",
             "zeroR")]
    for t, r in res["tickers"].items():
        for rg in ("pre", "post"):
            c = r[rg]
            L.append("%-8s %-5s %8d %7d %6d %6d %6d" % (
                t, rg, c["sessions"], c["pairs"], c["flat_close"],
                c["outside_hl"], c["zero_range"]))
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--archive", required=True)
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    res = run(a.archive)
    print(render(res))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=1, sort_keys=True)
            f.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
