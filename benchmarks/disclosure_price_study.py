#!/usr/bin/env python3
"""Disclosure-event price study (INS-IMPROVE-067 item 1B). DESCRIPTIVE
ONLY: no verdict word, no verdict key, no keep rule, not v2-relative.

Question: do announcement windows move more than the trailing
volatility before the announcement implies, and how does that split by
event sign (profit_direction) and type?

Design (fixed before any number was computed; nothing is fitted):
- Events: an events CSV (ticker, announcement_date, period_end, type,
  profit_direction, announce_time, mubasher_id). Events on tickers with
  no price file are counted and dropped.
- Prices: one CSV per ticker (Date,Open,High,Low,Close,Volume), the
  egxpy pack. Bars with volume <= 0 are not sessions and are dropped
  (leading stubs and carried closes). Close is used, as in the pack
  (bonus-adjusted).
- Base: the last session strictly BEFORE the announcement date, so
  the announcement day is always inside the window and nothing on or
  after it enters the trailing estimate. Horizons 1, 5, 21 sessions
  after the base.
- Trailing sigma: standard deviation (n-1) of the last 60 daily log
  returns ending at the base. Fewer than 60 returns before the base,
  or fewer than 21 sessions after it, drops the event.
- Capital actions: an event is dropped if a capital-action effective
  date for the ticker falls after the base date and on or before the
  date of the 21st session after the base. A ticker with no capital
  action file is not screened and is counted.
- Statistic: ratio_h = |ln(P[base+h] / P[base])| / (sigma * sqrt(h)).
  A ratio above 1 means a larger move than the trailing sigma implies.
  In-band means ratio_h <= Z80 (an 80% two-sided normal band built
  from the trailing sigma, centre 0).
- Control: same tickers, windows with base every 21 sessions from the
  60th return on, skipping any window that holds an announcement date
  or a capital-action date. Same statistic.
- Intervals: announcement-date-clustered bootstrap (resample dates
  with replacement), B = 2000, seed 594, percentile 95%.
Stdlib only. Usage:
  python3 benchmarks/disclosure_price_study.py --events E.csv \\
      --prices DIR --ca DIR [--json OUT]
"""
import argparse
import bisect
import csv
import datetime as dt
import json
import math
import os
import random
import statistics
import sys

sys.dont_write_bytecode = True

HORIZONS = (1, 5, 21)
TRAIL = 60
Z80 = 1.2815515655446004
B_DRAWS = 2000
SEED = 594
MONTHS = {m: i + 1 for i, m in enumerate(
    "January February March April May June July August September "
    "October November December".split())}


def load_prices(path):
    """[(date, close)] sorted, volume-0 and non-positive bars dropped."""
    rows = {}
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            try:
                c = float(r["Close"])
                v = float(r["Volume"])
            except (KeyError, ValueError):
                continue
            if v > 0 and c > 0 and math.isfinite(c):
                rows[r["Date"]] = c
    return sorted(rows.items())


def parse_long_date(s):
    try:
        d, m, y = s.split()
        return dt.date(int(y), MONTHS[m], int(d)).isoformat()
    except (ValueError, KeyError, AttributeError):
        return None


def load_ca_dates(path):
    """Effective dates of a ticker's capital actions (ISO), or None
    when there is no file."""
    if not os.path.exists(path):
        return None
    out = []
    for a in json.load(open(path)):
        d = parse_long_date(a.get("effectiveDate", ""))
        if d:
            out.append(d)
    return sorted(out)


def window_stats(series, base_i):
    """{h: ratio} for the base index, or None when history or the
    forward window is too short."""
    if base_i < TRAIL or base_i + max(HORIZONS) >= len(series):
        return None
    cl = [c for _d, c in series]
    rets = [math.log(cl[k] / cl[k - 1])
            for k in range(base_i - TRAIL + 1, base_i + 1)]
    sig = statistics.stdev(rets)
    if not sig > 0:
        return None
    return {h: abs(math.log(cl[base_i + h] / cl[base_i]))
            / (sig * math.sqrt(h)) for h in HORIZONS}


def base_index(series, ann_date):
    """Index of the last session strictly before ann_date, or None."""
    dates = [d for d, _c in series]
    i = bisect.bisect_left(dates, ann_date) - 1
    return i if i >= 0 else None


def ca_hit(ca, lo_date, hi_date):
    return bool(ca) and any(lo_date < d <= hi_date for d in ca)


def event_rows(events, prices, cas):
    """(kept, dropped) where kept rows carry ratios; dropped counts
    by reason."""
    kept = []
    drop = {"no_price_file": 0, "short_history_or_window": 0,
            "capital_action_in_window": 0, "no_ca_file_kept": 0}
    for e in events:
        t = e["ticker"].split(".")[0].upper()
        s = prices.get(t)
        if not s:
            drop["no_price_file"] += 1
            continue
        i = base_index(s, e["announcement_date"])
        st = window_stats(s, i) if i is not None else None
        if st is None:
            drop["short_history_or_window"] += 1
            continue
        ca = cas.get(t)
        if ca is None:
            drop["no_ca_file_kept"] += 1
        elif ca_hit(ca, s[i][0], s[i + max(HORIZONS)][0]):
            drop["capital_action_in_window"] += 1
            continue
        kept.append({"ticker": t, "ann": e["announcement_date"],
                     "dir": e.get("profit_direction", ""),
                     "type": e.get("type", ""), "ratios": st})
    return kept, drop


def control_rows(events, prices, cas):
    ann = {}
    for e in events:
        ann.setdefault(e["ticker"].split(".")[0].upper(),
                       []).append(e["announcement_date"])
    out = []
    for t in sorted({e["ticker"].split(".")[0].upper()
                     for e in events}):
        s = prices.get(t)
        if not s:
            continue
        i = TRAIL
        while i + max(HORIZONS) < len(s):
            lo, hi = s[i][0], s[i + max(HORIZONS)][0]
            clash = any(lo < a <= hi for a in ann.get(t, [])) \
                or ca_hit(cas.get(t), lo, hi)
            st = None if clash else window_stats(s, i)
            if st is not None:
                out.append({"ticker": t, "ann": lo, "ratios": st})
            i += max(HORIZONS)
    return out


def med(xs):
    return statistics.median(xs) if xs else None


def cov(xs):
    return sum(1 for x in xs if x <= Z80) / len(xs) if xs else None


def pct(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, max(0, int(round(q * (len(xs) - 1)))))]


def boot(rows, h, draws=B_DRAWS, seed=SEED):
    """Clustered (by announcement date) 95% intervals for the median
    ratio and the in-band share."""
    if not rows:
        return None
    cl = {}
    for r in rows:
        cl.setdefault(r["ann"], []).append(r["ratios"][h])
    keys = sorted(cl)
    rng = random.Random(seed)
    ms, cs = [], []
    for _ in range(draws):
        xs = []
        for _k in keys:
            xs.extend(cl[keys[rng.randrange(len(keys))]])
        ms.append(med(xs))
        cs.append(cov(xs))
    return {"median_ci": [pct(ms, .025), pct(ms, .975)],
            "inband_ci": [pct(cs, .025), pct(cs, .975)],
            "clusters": len(keys)}


def summarise(rows, h):
    xs = [r["ratios"][h] for r in rows]
    return {"n": len(xs), "median_ratio": med(xs), "inband": cov(xs),
            "boot": boot(rows, h)}


def build(events, prices, cas):
    kept, drop = event_rows(events, prices, cas)
    ctrl = control_rows(events, prices, cas)
    splits = {"all": kept}
    for key in ("dir", "type"):
        for v in sorted({r[key] for r in kept}):
            splits["%s=%s" % (key, v)] = [r for r in kept if r[key] == v]
    rep = {"design": {"horizons": list(HORIZONS), "trailing_returns":
                      TRAIL, "z80": Z80, "bootstrap_draws": B_DRAWS,
                      "seed": SEED, "events_in": len(events)},
           "dropped": drop, "events_kept": len(kept),
           "event_clusters": len({r["ann"] for r in kept}),
           "control": {str(h): summarise(ctrl, h) for h in HORIZONS},
           "events": {k: {str(h): summarise(v, h) for h in HORIZONS}
                      for k, v in splits.items()}}
    return rep


def _f(v, nd=3):
    return "n/a" if v is None else ("%.*f" % (nd, v))


def render(rep):
    L = ["DESCRIPTIVE ONLY",
         "disclosure-event price study: |ln move| / (trailing sigma "
         "* sqrt(h)), base = last session before the announcement",
         "events in %d, kept %d (%d announcement dates); dropped %s"
         % (rep["design"]["events_in"], rep["events_kept"],
            rep["event_clusters"], json.dumps(rep["dropped"]))]
    for h in HORIZONS:
        c = rep["control"][str(h)]
        L.append("h=%d control: n=%d median ratio %s in-band %s"
                 % (h, c["n"], _f(c["median_ratio"]), _f(c["inband"])))
    for k, v in rep["events"].items():
        for h in HORIZONS:
            s = v[str(h)]
            b = s["boot"]
            ci = ("median CI [%s, %s] in-band CI [%s, %s] clusters %d"
                  % (_f(b["median_ci"][0]), _f(b["median_ci"][1]),
                     _f(b["inband_ci"][0]), _f(b["inband_ci"][1]),
                     b["clusters"])) if b else "no rows"
            L.append("%s h=%d: n=%d median ratio %s in-band %s  %s"
                     % (k, h, s["n"], _f(s["median_ratio"]),
                        _f(s["inband"]), ci))
    return "\n".join(L)


def load_inputs(events_csv, prices_dir, ca_dir):
    events = list(csv.DictReader(open(events_csv, newline="")))
    # The one overlapping ETEL annual event is cleared out by ruling.
    events = [e for e in events if not (
        e["ticker"] == "ETEL.CA"
        and e["announcement_date"] == "2025-02-27")]
    prices, cas = {}, {}
    for e in events:
        t = e["ticker"].split(".")[0].upper()
        if t in prices:
            continue
        p = os.path.join(prices_dir, t.lower() + ".csv")
        prices[t] = load_prices(p) if os.path.exists(p) else None
        cas[t] = load_ca_dates(os.path.join(ca_dir, t + ".json"))
    return events, prices, cas


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", required=True)
    ap.add_argument("--prices", required=True)
    ap.add_argument("--ca", required=True)
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    rep = build(*load_inputs(a.events, a.prices, a.ca))
    print(render(rep))
    if a.json:
        json.dump(rep, open(a.json, "w"), indent=1, sort_keys=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
