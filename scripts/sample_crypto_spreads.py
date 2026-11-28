#!/usr/bin/env python3
"""Round 147 s.6: spread sampler for BTC-USD and ETH-USD top of book on
Coinbase Exchange and Kraken (public tickers, no key). Stdlib only.
One run = one snapshot: appends one JSON line per venue/pair to a JSONL
file (default evaluation/crypto_spread_samples.jsonl). A failed or
invalid quote is recorded as a row with "error" and no spread, never
dropped and never imputed. Run hourly for 7+ days (see
docs/round147_crypto_cost_sourcing.md).

  python3 scripts/sample_crypto_spreads.py [--out PATH]      # snapshot
  python3 scripts/sample_crypto_spreads.py --summarise PATH  # counts, and
      percentiles only once a series holds >= MIN_SAMPLES valid samples

Descriptive only. No conversion edge is computed anywhere here.
"""
import datetime as dt
import json
import math
import os
import sys
import urllib.request

SOURCES = [  # (venue, pair, url)
    ("coinbase", "BTC-USD", "https://api.exchange.coinbase.com/products/BTC-USD/ticker"),
    ("coinbase", "ETH-USD", "https://api.exchange.coinbase.com/products/ETH-USD/ticker"),
    ("kraken", "BTC-USD", "https://api.kraken.com/0/public/Ticker?pair=XBTUSD"),
    ("kraken", "ETH-USD", "https://api.kraken.com/0/public/Ticker?pair=ETHUSD"),
]
MIN_SAMPLES = 168  # 7 days hourly
PCTS = (5, 25, 50, 75, 95, 99)


def http_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def parse_quote(venue, payload):
    """Returns (bid, ask, venue_time_or_None). Raises ValueError."""
    if venue == "coinbase":
        return float(payload["bid"]), float(payload["ask"]), payload.get("time")
    if venue == "kraken":
        if payload.get("error"):
            raise ValueError("kraken error: %s" % payload["error"])
        res = payload["result"]
        if len(res) != 1:
            raise ValueError("kraken result has %d keys" % len(res))
        t = next(iter(res.values()))
        return float(t["b"][0]), float(t["a"][0]), None
    raise ValueError("unknown venue %r" % venue)


def make_row(venue, pair, ts, bid=None, ask=None, vtime=None, error=None):
    row = {"ts_utc": ts, "venue": venue, "pair": pair, "bid": bid,
           "ask": ask, "venue_time": vtime}
    if error is None:
        if not (bid > 0 and ask > 0):
            error = "non-positive bid/ask"
        elif ask < bid:
            error = "crossed book (ask < bid)"
    if error:
        row.update(mid=None, spread_bp=None, error=error)
    else:
        mid = (bid + ask) / 2.0
        row.update(mid=mid, spread_bp=(ask - bid) / mid * 1e4, error=None)
    return row


def snapshot(fetch=http_json, now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    ts = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = []
    for venue, pair, url in SOURCES:
        try:
            bid, ask, vt = parse_quote(venue, fetch(url))
            rows.append(make_row(venue, pair, ts, bid, ask, vt))
        except Exception as e:  # recorded, not dropped
            rows.append(make_row(venue, pair, ts, error="%s: %s" % (type(e).__name__, e)))
    return rows


def append(path, rows):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, sort_keys=True) + "\n")


def percentile(sorted_vals, p):
    """Nearest-rank percentile of an ascending list."""
    k = max(1, math.ceil(p / 100.0 * len(sorted_vals)))
    return sorted_vals[k - 1]


def summarise(path):
    series = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            s = series.setdefault((r["venue"], r["pair"]), {"valid": [], "errors": 0, "first": r["ts_utc"], "last": r["ts_utc"]})
            s["last"] = r["ts_utc"]
            if r.get("error"):
                s["errors"] += 1
            else:
                s["valid"].append(r["spread_bp"])
    out = {}
    for k in sorted(series):
        s = series[k]
        v = sorted(s["valid"])
        e = {"n_valid": len(v), "n_error": s["errors"], "first": s["first"], "last": s["last"]}
        if len(v) >= MIN_SAMPLES:
            e["spread_bp_percentiles"] = {str(p): percentile(v, p) for p in PCTS}
        else:
            e["note"] = "counts only: %d of %d valid samples" % (len(v), MIN_SAMPLES)
        out["%s %s" % k] = e
    return out


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--summarise" in argv:
        print(json.dumps(summarise(argv[argv.index("--summarise") + 1]), indent=1))
        return 0
    out = "evaluation/crypto_spread_samples.jsonl"
    if "--out" in argv:
        out = argv[argv.index("--out") + 1]
    rows = snapshot()
    append(out, rows)
    for r in rows:
        print("%s %s %s bid=%s ask=%s spread_bp=%s %s" % (
            r["ts_utc"], r["venue"], r["pair"], r["bid"], r["ask"],
            "n/a" if r["spread_bp"] is None else "%.4f" % r["spread_bp"],
            r["error"] or ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
