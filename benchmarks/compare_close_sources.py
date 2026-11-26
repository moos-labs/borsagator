#!/usr/bin/env python3
"""Cross-source close comparison (INS-IMPROVE-007, Moos round 16 GO).

DESCRIPTIVE ONLY. No keep rule, no verdict, no fit, no CI. Follow-up to
benchmarks/descriptive_close_counts.py (#784), whose egxpy counts the
yahooquery spot check contradicted. Per ticker and source it repeats
the same counts, then compares sources on the dates they share.

Sources, all read from the archive worker-runs tree:
  egxpy   egx-data/egxpy_<t>.csv        OHLC, most rows wins
  yahoo   yahooquery/<T>.CA.csv         OHLC (unadjusted close column)
  capture collected/pandas-ta|talib/indicators.csv of the backtest
          captures, merged by date over every capture of the ticker
          (<= 250 bars before each cutoff; later path wins a date)
  price   price.csv of the captures: close only, merged the same way,
          so it gives flat counts but no high-low test

Counts per source and regime (same definitions as #784): sessions,
pairs, flat_close (close == previous session's close), outside_hl
(close < low or close > high; OHLC sources only), zero_range.
Pairwise on shared dates (both sources hold the date and the same
previous date): close_equal / close_differs (|a-b| <= 1e-6 x |a| is
equal), flat_both / flat_only_first / flat_only_second.

Window rule as #784: only sessions dated <= 2023-12-28, split at
2021-09-05 (pre / post; the straddling pair is dropped). The yahoo
and capture sources start after the break, so only egxpy and price
cover the pre regime. Effective n is the "sessions" and "pairs"
counts; a ticker or pair with no shared dates is listed with n 0.

Usage:
  python3 benchmarks/compare_close_sources.py --archive DIR [--json OUT]
"""
import argparse
import csv
import json
import os
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import descriptive_close_counts as C  # noqa: E402

BREAK_DATE = C.BREAK_DATE
LAST_DATE = C.LAST_DATE
EQ_TOL = 1e-6
SCORED = ("COMI", "ETEL", "TMGH", "NVDA", "SWDY", "HRHO")


def base(t):
    return t.split(".")[0].upper()


def _rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        return [{k.strip().lower(): v for k, v in r.items() if k}
                for r in csv.DictReader(f)]


def read_yahoo(path):
    out = {}
    for r in _rows(path):
        d = str(r.get("date") or "")[:10]
        try:
            out[d] = tuple(float(r[k]) for k in
                           ("open", "high", "low", "close"))
        except (KeyError, TypeError, ValueError):
            continue
    return out


def newest_most_rows(paths):
    best = None
    for p in paths:
        with open(p, encoding="utf-8") as fh:
            n = sum(1 for _ in fh)
        if best is None or (n, p) > best[0]:
            best = ((n, p), p)
    return best[1] if best else None


def discover(archive):
    """{ticker: {source: path-or-list}}."""
    eg = C.find_files(archive)
    yh, caps = {}, {}
    for dp, dn, fn in os.walk(archive):
        if ".tmp-" in dp or ".old-" in dp:
            continue
        if os.path.basename(dp) == "yahooquery":
            for f in fn:
                if f.endswith(".csv") and f != "AAPL.csv":
                    yh.setdefault(base(f[:-4]), []).append(
                        os.path.join(dp, f))
        if "manifest.json" in fn and "realised.json" in fn:
            cutoff = os.path.basename(os.path.dirname(dp))
            if len(cutoff) == 10 and cutoff[4] == "-":
                caps.setdefault(base(os.path.basename(dp)),
                                []).append(dp)
    out = {}
    for t in sorted(set(base(x) for x in eg) | set(yh) | set(caps)):
        out[t] = {"egxpy": eg.get(t) or eg.get(t + ".CA"),
                  "yahoo": newest_most_rows(yh.get(t, [])),
                  "caps": sorted(caps.get(t, []))}
    return out


def read_captures(dirs):
    """(ohlc {date: bar}, close {date: close}) merged over captures."""
    ohlc, close = {}, {}
    for dp in dirs:                      # sorted: later path wins
        for rel in ("collected/pandas-ta/indicators.csv",
                    "collected/talib/indicators.csv"):
            p = os.path.join(dp, rel)
            if not os.path.exists(p):
                continue
            got = 0
            for r in _rows(p):
                d = str(r.get("date") or "")[:10]
                try:
                    ohlc[d] = tuple(float(r[k]) for k in
                                    ("open", "high", "low", "close"))
                    got += 1
                except (KeyError, TypeError, ValueError):
                    continue
            if got:
                break
        p = os.path.join(dp, "price.csv")
        if os.path.exists(p):
            for r in _rows(p):
                d = str(r.get("date") or "")[:10]
                try:
                    close[d] = float(r["close"])
                except (KeyError, TypeError, ValueError):
                    continue
    return ohlc, close


def count_close_only(closes):
    """count() for a close-only series: no high-low, zero_range n/a."""
    bars = {d: (c, c, c, c) for d, c in closes.items()}
    r = C.count(bars)
    for rg in ("pre", "post"):
        r[rg]["outside_hl"] = None
        r[rg]["zero_range"] = None
    return r


def prev_map(dates):
    return {d: p for p, d in zip(dates, dates[1:])}


def compare(a, b):
    """a, b: {date: close}. Shared-date comparison, post and pre."""
    out = {}
    da = sorted(d for d in a if d <= LAST_DATE)
    db = sorted(d for d in b if d <= LAST_DATE)
    pa, pb = prev_map(da), prev_map(db)
    for rg in ("pre", "post"):
        sh = [d for d in da if d in b and (d < BREAK_DATE) == (rg == "pre")]
        r = {"shared_dates": len(sh), "close_equal": 0, "close_differs": 0,
             "pairs": 0, "flat_both": 0, "flat_only_first": 0,
             "flat_only_second": 0}
        for d in sh:
            x, y = a[d], b[d]
            if abs(x - y) <= EQ_TOL * abs(x):
                r["close_equal"] += 1
            else:
                r["close_differs"] += 1
            p = pa.get(d)
            if p is None or p != pb.get(d) or p not in a or p not in b:
                continue
            if p < BREAK_DATE <= d:
                continue
            r["pairs"] += 1
            fa, fb = a[d] == a[p], b[d] == b[p]
            if fa and fb:
                r["flat_both"] += 1
            elif fa:
                r["flat_only_first"] += 1
            elif fb:
                r["flat_only_second"] += 1
        out[rg] = r
    return out


def run(archive):
    res = {"break_date": BREAK_DATE, "last_date": LAST_DATE,
           "descriptive": True, "tickers": {}}
    for t, src in discover(archive).items():
        series, counts, srcs = {}, {}, {}
        if src["egxpy"]:
            bars, _ = C.read_ohlc(src["egxpy"])
            series["egxpy"] = bars
            srcs["egxpy"] = os.path.relpath(src["egxpy"], archive)
        if src["yahoo"]:
            series["yahoo"] = read_yahoo(src["yahoo"])
            srcs["yahoo"] = os.path.relpath(src["yahoo"], archive)
        ohlc, close = read_captures(src["caps"])
        if ohlc:
            series["capture"] = ohlc
            srcs["capture"] = "%d capture dirs" % len(src["caps"])
        closes = {s: {d: v[3] for d, v in b.items()}
                  for s, b in series.items()}
        if close:
            closes["price"] = close
        for s, b in series.items():
            counts[s] = C.count(b)
        if "price" in closes:
            counts["price"] = count_close_only(closes["price"])
        if not counts:
            continue
        pairs = {}
        names = sorted(closes)
        for i, x in enumerate(names):
            for y in names[i + 1:]:
                pairs["%s|%s" % (x, y)] = compare(closes[x], closes[y])
        res["tickers"][t] = {"sources": srcs, "counts": counts,
                             "pairs": pairs}
    return res


def render(res):
    L = ["Cross-source close counts (no verdict). Sessions <= %s, split "
         "at %s." % (res["last_date"], res["break_date"]),
         "%-6s %-8s %-4s %8s %6s %6s %6s %6s" % (
             "ticker", "source", "reg", "sessions", "pairs", "flat",
             "outHL", "zeroR")]
    for t, r in res["tickers"].items():
        for s, c in sorted(r["counts"].items()):
            for rg in ("pre", "post"):
                x = c[rg]
                if not x["sessions"]:
                    continue
                L.append("%-6s %-8s %-4s %8d %6d %6d %6s %6s" % (
                    t, s, rg, x["sessions"], x["pairs"], x["flat_close"],
                    x["outside_hl"], x["zero_range"]))
    L.append("")
    L.append("Shared-date comparison, post regime: pair, shared dates, "
             "close differs, flat both / only first / only second")
    for t, r in res["tickers"].items():
        for k, v in sorted(r["pairs"].items()):
            x = v["post"]
            if x["shared_dates"]:
                L.append("%-6s %-16s %5d %5d  %4d / %4d / %4d" % (
                    t, k, x["shared_dates"], x["close_differs"],
                    x["flat_both"], x["flat_only_first"],
                    x["flat_only_second"]))
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
