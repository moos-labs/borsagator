#!/usr/bin/env python3
"""Canonical OHLCV store backfill (INS-IMPROVE-007 / #768 item 2).

Fetches daily history from the Yahoo chart API (stdlib urllib, no key)
and writes one CSV per ticker: date,high,low,close,volume,adjclose.
Open is NOT stored: Yahoo's EGX open equals the previous close on about
98% of bars (data agent finding), so it is synthetic. Close is the raw
(unadjusted) close; adjclose is kept as a separate column.

Rules: bars with a null high, low or close are skipped and counted;
duplicate dates keep the last; dates are the exchange-local session
date (the API timestamp shifted by the reported gmtoffset); output is
sorted by date and rewritten atomically. A per-ticker summary line
reports first date, last date, rows, skipped. Descriptive tool, no
verdict.

Usage:
  python3 scripts/fetch_ohlcv_store.py --out DIR [--start 2014-01-01]
      [--tickers COMI.CA ETEL.CA ...]   (default: the EGX33 freeze plus
                                         the six scored tickers)
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
ROOT = os.path.dirname(HERE)
URL = ("https://query1.finance.yahoo.com/v8/finance/chart/%s"
       "?period1=%d&period2=%d&interval=1d&events=div%%2Csplit")
SCORED = ["COMI.CA", "ETEL.CA", "TMGH.CA", "SWDY.CA", "HRHO.CA", "NVDA"]
FREEZE = os.path.join(ROOT, "sharia", "benchmark", "sources", "egx33.json")


def epoch(date_s):
    d = datetime.datetime.strptime(date_s, "%Y-%m-%d")
    return int(d.replace(tzinfo=datetime.timezone.utc).timestamp())


def parse_chart(payload):
    """(rows, skipped) from a decoded chart response; rows are
    (date, high, low, close, volume, adjclose) sorted by date."""
    res = (payload.get("chart") or {}).get("result")
    if not res:
        err = (payload.get("chart") or {}).get("error")
        raise ValueError("no result: %s" % (err,))
    r = res[0]
    ts = r.get("timestamp") or []
    off = (r.get("meta") or {}).get("gmtoffset") or 0
    q = ((r.get("indicators") or {}).get("quote") or [{}])[0]
    adj = ((r.get("indicators") or {}).get("adjclose") or [{}])[0] \
        .get("adjclose") or []
    out, skipped = {}, 0
    for i, t in enumerate(ts):
        try:
            h, lo, c = q["high"][i], q["low"][i], q["close"][i]
        except (KeyError, IndexError):
            skipped += 1
            continue
        if h is None or lo is None or c is None:
            skipped += 1
            continue
        d = datetime.datetime.fromtimestamp(
            t + off, datetime.timezone.utc).strftime("%Y-%m-%d")
        v = (q.get("volume") or [None] * (i + 1))[i]
        a = adj[i] if i < len(adj) else None
        out[d] = (d, h, lo, c, "" if v is None else v,
                  "" if a is None else a)
    return [out[d] for d in sorted(out)], skipped


def fetch(ticker, start, end, tries=3):
    url = URL % (ticker, epoch(start), end)
    last = None
    for k in range(tries):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as f:
                return json.loads(f.read().decode("utf-8"))
        except (urllib.error.URLError, ValueError, OSError) as e:
            last = e
            time.sleep(2 * (k + 1))
    raise RuntimeError("%s: %s" % (ticker, last))


def write_csv(path, rows):
    tmp = path + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "high", "low", "close", "volume", "adjclose"])
        w.writerows(rows)
    os.replace(tmp, path)


def default_tickers():
    out = list(SCORED)
    try:
        with open(FREEZE, encoding="utf-8") as f:
            data = json.load(f)
        items = data.get("rows", []) if isinstance(data, dict) else data
        for it in items:
            s = it if isinstance(it, str) else (it.get("ticker")
                                                or it.get("symbol") or "")
            s = s.strip().upper()
            if s and not s.endswith(".CA") and "." not in s:
                s += ".CA"
            if s and s not in out:
                out.append(s)
    except (OSError, ValueError, AttributeError):
        pass
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--start", default="2014-01-01")
    ap.add_argument("--tickers", nargs="*")
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    end = int(time.time()) + 86400
    fails = 0
    for t in (a.tickers or default_tickers()):
        try:
            rows, skipped = parse_chart(fetch(t, a.start, end))
        except (RuntimeError, ValueError) as e:
            print("FAIL %s %s" % (t, e))
            fails += 1
            continue
        write_csv(os.path.join(a.out, t.replace(".", "_") + ".csv"),
                  rows)
        print("%-9s %s .. %s rows %d skipped %d" % (
            t, rows[0][0] if rows else "-", rows[-1][0] if rows else "-",
            len(rows), skipped))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
