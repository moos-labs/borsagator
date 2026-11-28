#!/usr/bin/env python3
"""Round 147 crypto track: Yahoo chart v8 daily harvest for BTC-USD and
ETH-USD (docs/round147_crypto_track_prereg.md section 2). Stdlib only,
LLM-free. Writes ohlcv/yahoo/<SYMBOL>.csv with columns
date,high,low,close,volume,adjclose,open (EGX readers keep their own
column order). A validation failure is a listed refusal and nothing is
written. Re-runs are append-only: stored dates are re-fetched and must
match; a changed historical bar is listed and refuses the write.

Usage: python3 scripts/fetch_crypto_ohlcv.py [--out-dir ohlcv/yahoo]
"""
import csv
import datetime as dt
import json
import os
import sys
import time
import urllib.request

SYMBOLS = ("BTC-USD", "ETH-USD")
URL = ("https://query1.finance.yahoo.com/v8/finance/chart/%s"
       "?period1=%d&period2=%d&interval=1d&events=history")
COLUMNS = ["date", "high", "low", "close", "volume", "adjclose", "open"]
P1 = 1410000000  # 2014-09-06 UTC, before the first BTC-USD bar


class Refusal(Exception):
    """A listed validation refusal; nothing is written."""


def fetch(symbol, p1, p2):
    req = urllib.request.Request(URL % (symbol, p1, p2),
                                 headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def parse_validate(payload, today):
    """payload: parsed chart v8 JSON. today: current UTC date (the
    partial bar of that date and anything later is dropped). Returns
    (rows, dropped_partial) with rows as dicts keyed by COLUMNS. Raises
    Refusal listing every failure found."""
    errs = []
    chart = (payload or {}).get("chart") or {}
    if chart.get("error"):
        raise Refusal("api error: %s" % chart["error"])
    res = (chart.get("result") or [None])[0]
    if not res:
        raise Refusal("no result")
    gran = (res.get("meta") or {}).get("dataGranularity")
    if gran != "1d":
        raise Refusal("dataGranularity is %r, not '1d'" % (gran,))
    ts = res.get("timestamp") or []
    q = ((res.get("indicators") or {}).get("quote") or [{}])[0]
    adj = (((res.get("indicators") or {}).get("adjclose") or [{}])[0]
           or {}).get("adjclose")
    cols = {k: q.get(k) or [] for k in ("open", "high", "low", "close",
                                         "volume")}
    n = len(ts)
    for k, v in cols.items():
        if len(v) != n:
            errs.append("%s length %d != timestamps %d" % (k, len(v), n))
    if adj is None or len(adj) != n:
        errs.append("adjclose missing or wrong length")
    if errs:
        raise Refusal("; ".join(errs))
    rows, prev, dropped = [], None, 0
    for i, t in enumerate(ts):
        d = dt.datetime.fromtimestamp(t, dt.timezone.utc)
        if (d.hour, d.minute, d.second) != (0, 0, 0):
            errs.append("%s not stamped 00:00:00 UTC" % d.isoformat())
            continue
        day = d.date()
        if day >= today:
            dropped += 1  # partial current-day bar (or later): dropped
            continue
        o, h, l, c = (cols[k][i] for k in ("open", "high", "low", "close"))
        if None in (o, h, l, c):
            errs.append("%s null in open/high/low/close" % day)
            continue
        if not (h >= max(o, c) and l <= min(o, c)):
            errs.append("%s high/low bounds violated" % day)
        if not c > 0:
            errs.append("%s close not > 0" % day)
        if prev is not None:
            if day <= prev:
                errs.append("%s not strictly increasing after %s" % (day, prev))
            elif (day - prev).days != 1:
                errs.append("gap: %s follows %s (listed, never filled)"
                            % (day, prev))
        prev = day
        rows.append({"date": day.isoformat(), "high": h, "low": l, "close": c,
                     "volume": cols["volume"][i], "adjclose": adj[i],
                     "open": o})
    if errs:
        raise Refusal("; ".join(errs[:50]) + (
            " (+%d more)" % (len(errs) - 50) if len(errs) > 50 else ""))
    return rows, dropped


def merge_existing(path, rows):
    """Append-only merge. Stored dates must match the re-fetch; returns
    the merged list or raises Refusal listing changed bars."""
    if not os.path.exists(path):
        return rows
    with open(path, newline="", encoding="utf-8") as f:
        old = {r["date"]: r for r in csv.DictReader(f)}
    changed = []
    new_by_date = {r["date"]: r for r in rows}
    for d, o in old.items():
        n = new_by_date.get(d)
        if n is None:
            changed.append("%s stored but not re-fetched" % d)
            continue
        for k in COLUMNS[1:]:
            if o[k] in ("", None):
                continue
            if float(o[k]) != float(n[k]):
                changed.append("%s %s stored %s != fetched %s"
                               % (d, k, o[k], n[k]))
                break
    if changed:
        raise Refusal("changed historical bars (listed, not overwritten): "
                      + "; ".join(changed[:50]))
    return rows


def write_csv(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        for r in rows:
            w.writerow([r[c] for c in COLUMNS])


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    out_dir = "ohlcv/yahoo"
    if "--out-dir" in argv:
        out_dir = argv[argv.index("--out-dir") + 1]
    now = int(time.time())
    today = dt.datetime.fromtimestamp(now, dt.timezone.utc).date()
    rc = 0
    for sym in SYMBOLS:
        try:
            rows, dropped = parse_validate(fetch(sym, P1, now + 86400), today)
            rows = merge_existing(os.path.join(out_dir, sym + ".csv"), rows)
            write_csv(os.path.join(out_dir, sym + ".csv"), rows)
            print("%s: %d bars %s..%s, dropped %d partial/future bar(s), "
                  "fetched %s UTC" % (sym, len(rows), rows[0]["date"],
                                      rows[-1]["date"], dropped,
                                      dt.datetime.fromtimestamp(
                                          now, dt.timezone.utc).isoformat()))
        except Refusal as e:
            print("%s: REFUSED, nothing written: %s" % (sym, e))
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
