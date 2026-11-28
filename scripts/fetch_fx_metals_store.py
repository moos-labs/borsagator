#!/usr/bin/env python3
"""FX / metals daily harvest, phase 1 (INS-IMPROVE-151, #972). LLM-free.

Writes one canonical CSV per asset (date,high,low,close,volume,adjclose,
same header as fetch_ohlcv_store.py) plus FROZEN_DEFINITIONS.json that
records the daily-close definition per asset. SPOT legs only: no futures
proxy (GC=F, SI=F) is ever fetched.

Sources (each verified against the live API on 2026-11-28, see DEFINITIONS):
  FX      Yahoo chart API, 8 verified symbols (no key).
  Metals  Frankfurter v2 XAU / XAG -> USD, PROVISIONAL. Yahoo has no spot
          gold/silver symbol (XAUUSD=X, XAGUSD=X, XAU=X, XAG=X return Not
          Found; GC=F/SI=F are COMEX futures; XAU-USD is a crypto-token
          listing). The frozen metals close is the LBMA AM fixing, which
          is not obtainable without an IBA licence; the Frankfurter series
          is NOT that fixing and is tagged so in the manifest.
Derived: XAUEGP = XAUUSD close x USDEGP close on common dates.

Usage:
  python3 scripts/fetch_fx_metals_store.py --out DIR [--today YYYY-MM-DD]
      [--fx-years 10] [--metal-years 20]
Descriptive tool, no verdict.
"""
import argparse
import csv
import datetime
import json
import os
import sys
import time
import urllib.error
import urllib.request

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fetch_ohlcv_store as Y  # noqa: E402

FRANKFURTER = ("https://api.frankfurter.dev/v2/rates?base=%s&quotes=USD"
               "&from=%s&to=%s")
# name -> Yahoo symbol, verified by chart-API call (instrumentType CURRENCY,
# exchange CCY, history from 2001 to 2026-11-27/28).
FX_SYMBOLS = {
    "USDEGP": "EGP=X", "EUREGP": "EUREGP=X", "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X", "USDJPY": "JPY=X", "USDCHF": "CHF=X",
    "AUDUSD": "AUDUSD=X", "USDCAD": "CAD=X",
}
METALS = {"XAUUSD": "XAU", "XAGUSD": "XAG"}
REJECTED_YAHOO = {
    "XAUUSD=X": "Not Found", "XAGUSD=X": "Not Found", "XAU=X": "Not Found",
    "XAG=X": "Not Found", "GC=F": "COMEX gold FUTURES (excluded)",
    "SI=F": "COMEX silver FUTURES (excluded)",
    "XAU-USD": "crypto-token listing, not spot gold"}
EGP_FLOAT_DATE = "2024-03-06"
WEEK_SESSIONS, MONTH_SESSIONS = 5, 21

FROZEN_DEFINITIONS = {
    "fx_close": "Yahoo chart-API daily bar close (raw close), session date "
                "= API timestamp + gmtoffset (CCY gmtoffset 0 = UTC date).",
    "metals_close_frozen": "LBMA AM fixing (morning London time), USD per "
                           "troy ounce, NOT 00:00 UTC.",
    "metals_close_in_this_store": "PROVISIONAL Frankfurter v2 XAU/XAG->USD "
                                  "daily value; NOT the LBMA AM fixing.",
    "gold_egp": "derived: XAUUSD close x USDEGP close, same date.",
    "egp_regime_split": EGP_FLOAT_DATE + " (float; first close on or after "
                        "this date is the floating regime)",
    "week_sessions": WEEK_SESSIONS, "month_sessions": MONTH_SESSIONS,
}


def years_back(today, years):
    d = datetime.date.fromisoformat(today)
    try:
        return d.replace(year=d.year - years).isoformat()
    except ValueError:                      # 29 Feb
        return d.replace(year=d.year - years, day=28).isoformat()


def parse_frankfurter(payload):
    """(rows, skipped): rows (date,'','',close,'','') sorted, duplicates keep
    the last; entries with a missing or non-positive rate are skipped."""
    if not isinstance(payload, list):
        raise ValueError("unexpected frankfurter payload: %r" % (type(payload),))
    out, skipped = {}, 0
    for it in payload:
        try:
            d, r = it["date"], float(it["rate"])
        except (KeyError, TypeError, ValueError):
            skipped += 1
            continue
        if r <= 0:
            skipped += 1
            continue
        out[d] = (d, "", "", r, "", "")
    return [out[d] for d in sorted(out)], skipped


def fetch_frankfurter(base, start, end, tries=3):
    url = FRANKFURTER % (base, start, end)
    last = None
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as f:
                return json.loads(f.read().decode("utf-8"))
        except (urllib.error.URLError, ValueError, OSError) as e:
            last = e
            time.sleep(2 * (k + 1))
    raise RuntimeError("%s: %s" % (base, last))


def derive_gold_egp(xau_rows, egp_rows):
    """XAUUSD close x USDEGP close on dates present in both; close only."""
    egp = {r[0]: float(r[3]) for r in egp_rows}
    out = []
    for r in xau_rows:
        if r[0] in egp:
            out.append((r[0], "", "", float(r[3]) * egp[r[0]], "", ""))
    return out


def egp_regime(date):
    return "float" if date >= EGP_FLOAT_DATE else "pre-float"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--today", default=datetime.date.today().isoformat())
    ap.add_argument("--fx-years", type=int, default=10)
    ap.add_argument("--metal-years", type=int, default=20)
    a = ap.parse_args(argv)
    if a.fx_years < 5 or a.metal_years < 5:
        print("refused: minimum history is 5 years")
        return 2
    os.makedirs(a.out, exist_ok=True)
    end = int(time.time()) + 86400
    fx_start = years_back(a.today, a.fx_years)
    m_start = years_back(a.today, a.metal_years)
    fails, store = 0, {}
    for name, sym in FX_SYMBOLS.items():
        try:
            rows, skipped = Y.parse_chart(Y.fetch(sym, fx_start, end))
        except (RuntimeError, ValueError) as e:
            print("FAIL %s %s" % (name, e))
            fails += 1
            continue
        store[name] = rows
        Y.write_csv(os.path.join(a.out, name + ".csv"), rows)
        print("%-7s yahoo:%-10s %s .. %s rows %d skipped %d" % (
            name, sym, rows[0][0] if rows else "-", rows[-1][0] if rows else "-",
            len(rows), skipped))
    for name, base in METALS.items():
        try:
            rows, skipped = parse_frankfurter(
                fetch_frankfurter(base, m_start, a.today))
        except (RuntimeError, ValueError) as e:
            print("FAIL %s %s" % (name, e))
            fails += 1
            continue
        store[name] = rows
        Y.write_csv(os.path.join(a.out, name + ".csv"), rows)
        print("%-7s frankfurter:%s (PROVISIONAL, not LBMA AM) %s .. %s rows %d skipped %d" % (
            name, base, rows[0][0] if rows else "-", rows[-1][0] if rows else "-",
            len(rows), skipped))
    if "XAUUSD" in store and "USDEGP" in store:
        rows = derive_gold_egp(store["XAUUSD"], store["USDEGP"])
        Y.write_csv(os.path.join(a.out, "XAUEGP.csv"), rows)
        print("XAUEGP  derived %d rows" % len(rows))
    man = dict(FROZEN_DEFINITIONS)
    man["rejected_yahoo_symbols"] = REJECTED_YAHOO
    man["fx_symbols"] = FX_SYMBOLS
    with open(os.path.join(a.out, "FROZEN_DEFINITIONS.json"), "w") as f:
        json.dump(man, f, indent=2, sort_keys=True)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
