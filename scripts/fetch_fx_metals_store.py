#!/usr/bin/env python3
"""FX / metals daily harvest, phase 1 (INS-IMPROVE-151, #972). LLM-free.

FX: one canonical CSV per asset (date,high,low,close,volume,adjclose, same
header as fetch_ohlcv_store.py) from the Yahoo chart API, 8 verified spot
symbols.

METALS ARE A LABELLED RESEARCH PROXY, NOT SPOT AND NOT THE LBMA AM FIXING.
They come from Yahoo's COMEX continuous front-month FUTURES GC=F (gold) and
SI=F (silver), for model development only. The product stays spot-only until
a verified spot source exists. Every proxy artefact says so: file names end
_FUTURES_PROXY, a 7th column `proxy` repeats the label on every row, and
FROZEN_DEFINITIONS.json records it. No Frankfurter metal series is used.

Futures facts verified live 2026-11-28 (chart API): instrumentType FUTURE,
exchange COMEX (CMX), exchangeTimezoneName America/New_York, 5,104 daily bars
2006-08-31..2026-11-27, weekday bars only. The chart `meta.gmtoffset` is a
FIXED -18000 (EST) for the whole history, while bar timestamps sit at
00:00 / 07:00 / 09:30 New York local; applying the fixed offset puts some
bars on a Sunday. The proxy session date is therefore the timestamp
converted with America/New_York (zoneinfo), not meta.gmtoffset.

Usage:
  python3 scripts/fetch_fx_metals_store.py --out DIR [--today YYYY-MM-DD]
      [--fx-years 10] [--metal-years 20] [--score-run]
--score-run drops each series' final bar when its date is >= --today (a
live or partial day). Descriptive tool, no verdict.
"""
import argparse
import csv
import datetime
import json
import os
import sys
import time

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fetch_ohlcv_store as Y  # noqa: E402

# name -> Yahoo symbol, verified by chart-API call (instrumentType CURRENCY,
# exchange CCY, history from 2001 to 2026-11-27/28).
FX_SYMBOLS = {
    "USDEGP": "EGP=X", "EUREGP": "EUREGP=X", "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X", "USDJPY": "JPY=X", "USDCHF": "CHF=X",
    "AUDUSD": "AUDUSD=X", "USDCAD": "CAD=X",
}
PROXY_LABEL = "futures-proxy-NOT-spot-NOT-LBMA-AM"
# name -> Yahoo symbol; verified live: FUTURE / COMEX / America/New_York.
METAL_PROXY = {"XAUUSD_FUTURES_PROXY": "GC=F", "XAGUSD_FUTURES_PROXY": "SI=F"}
REJECTED_YAHOO = {
    "XAUUSD=X": "Not Found", "XAGUSD=X": "Not Found", "XAU=X": "Not Found",
    "XAG=X": "Not Found",
    "XAU-USD": "crypto-token listing, not spot gold"}
EGP_FLOAT_DATE = "2024-03-06"
WEEK_SESSIONS, MONTH_SESSIONS = 5, 21

FROZEN_DEFINITIONS = {
    "fx_close": "Yahoo chart-API daily bar close (raw close), session date "
                "= API timestamp + gmtoffset (CCY gmtoffset 0 = UTC date).",
    "metals_proxy_label": PROXY_LABEL + ": research proxy for model "
                          "development only; the product stays spot-only "
                          "until a verified spot source exists.",
    "metals_proxy_close": "Yahoo GC=F / SI=F continuous front-month COMEX "
                          "future, raw daily close as served (adjclose "
                          "equals close; verified 0 differences). USD per "
                          "troy ounce. Session date = bar timestamp in "
                          "America/New_York (NOT meta.gmtoffset). Bars with "
                          "a null high/low/close are skipped; zero-volume "
                          "bars are kept.",
    "metals_proxy_roll": "NOT back-adjusted. Yahoo splices contracts at "
                         "roll with no adjustment and publishes no roll "
                         "dates, so a return on a roll day includes the "
                         "calendar spread. Treat roll-day returns as "
                         "contaminated until roll dates are sourced.",
    "metals_proxy_roll_dates": "NOT SOURCED (2026-11-28). CME publishes "
                               "contract rules (COMEX rulebook ch.113 gold, "
                               "ch.112 silver: last trade = third last "
                               "business day of the delivery month) and an "
                               "expiration calendar, but no free source "
                               "publishes the dates Yahoo splices GC=F / "
                               "SI=F. Yahoo keeps individual contracts only "
                               "while live, so historical splices cannot be "
                               "reconstructed from it. One splice observed: "
                               "GC=F equalled GCZ25 through 2025-11-26 and "
                               "was a different contract from 2025-11-28. "
                               "No roll date is asserted; roll-day returns "
                               "stay unexcluded and flagged.",
    "metals_close_frozen_for_product": "LBMA AM fixing (morning London "
                                       "time), spot; NOT available in this "
                                       "store.",
    "gold_egp_proxy": "derived: XAUUSD_FUTURES_PROXY close x USDEGP close, "
                      "same date; also a futures proxy.",
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


def parse_futures(payload):
    """(rows, skipped) for a futures chart response: like fetch_ohlcv_store
    parse_chart, but the session date is the timestamp in the exchange's own
    timezone (meta.exchangeTimezoneName), and a 7th `proxy` field is added."""
    from zoneinfo import ZoneInfo
    res = (payload.get("chart") or {}).get("result")
    if not res:
        raise ValueError("no result: %s" % ((payload.get("chart") or {}).get("error"),))
    r = res[0]
    tz = ZoneInfo((r.get("meta") or {}).get("exchangeTimezoneName") or "America/New_York")
    q = ((r.get("indicators") or {}).get("quote") or [{}])[0]
    adj = ((r.get("indicators") or {}).get("adjclose") or [{}])[0].get("adjclose") or []
    out, skipped = {}, 0
    for i, t in enumerate(r.get("timestamp") or []):
        try:
            h, lo, c = q["high"][i], q["low"][i], q["close"][i]
        except (KeyError, IndexError):
            skipped += 1
            continue
        if h is None or lo is None or c is None:
            skipped += 1
            continue
        d = datetime.datetime.fromtimestamp(t, tz).strftime("%Y-%m-%d")
        v = (q.get("volume") or [None] * (i + 1))[i]
        a = adj[i] if i < len(adj) else None
        out[d] = (d, h, lo, c, "" if v is None else v, "" if a is None else a)
    return [out[d] for d in sorted(out)], skipped


def drop_final_partial(rows, today):
    """Score runs: drop the last bar when its date is >= today."""
    if rows and rows[-1][0] >= today:
        return rows[:-1], 1
    return rows, 0


def write_proxy_csv(path, rows):
    tmp = path + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "high", "low", "close", "volume", "adjclose", "proxy"])
        for r in rows:
            w.writerow(list(r) + [PROXY_LABEL])
    os.replace(tmp, path)


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
    ap.add_argument("--score-run", action="store_true")
    a = ap.parse_args(argv)
    if a.fx_years < 5 or a.metal_years < 5:
        print("refused: minimum history is 5 years")
        return 2
    os.makedirs(a.out, exist_ok=True)
    end = int(time.time()) + 86400
    fx_start = years_back(a.today, a.fx_years)
    m_start = years_back(a.today, a.metal_years)
    fails, store = 0, {}

    def finish(rows):
        return drop_final_partial(rows, a.today) if a.score_run else (rows, 0)

    for name, sym in FX_SYMBOLS.items():
        try:
            rows, skipped = Y.parse_chart(Y.fetch(sym, fx_start, end))
        except (RuntimeError, ValueError) as e:
            print("FAIL %s %s" % (name, e))
            fails += 1
            continue
        rows, dropped = finish(rows)
        store[name] = rows
        Y.write_csv(os.path.join(a.out, name + ".csv"), rows)
        print("%-22s yahoo:%-10s %s .. %s rows %d skipped %d dropped_final %d" % (
            name, sym, rows[0][0] if rows else "-", rows[-1][0] if rows else "-",
            len(rows), skipped, dropped))
    for name, sym in METAL_PROXY.items():
        try:
            rows, skipped = parse_futures(Y.fetch(sym, m_start, end))
        except (RuntimeError, ValueError) as e:
            print("FAIL %s %s" % (name, e))
            fails += 1
            continue
        rows, dropped = finish(rows)
        store[name] = rows
        write_proxy_csv(os.path.join(a.out, name + ".csv"), rows)
        print("%-22s yahoo:%-10s [%s] %s .. %s rows %d skipped %d dropped_final %d" % (
            name, sym, PROXY_LABEL, rows[0][0] if rows else "-",
            rows[-1][0] if rows else "-", len(rows), skipped, dropped))
    if "XAUUSD_FUTURES_PROXY" in store and "USDEGP" in store:
        rows = derive_gold_egp(store["XAUUSD_FUTURES_PROXY"], store["USDEGP"])
        write_proxy_csv(os.path.join(a.out, "XAUEGP_FUTURES_PROXY.csv"), rows)
        print("XAUEGP_FUTURES_PROXY   derived %d rows [%s]" % (len(rows), PROXY_LABEL))
    man = dict(FROZEN_DEFINITIONS)
    man["rejected_yahoo_spot_metal_symbols"] = REJECTED_YAHOO
    man["fx_symbols"] = FX_SYMBOLS
    man["metal_proxy_symbols"] = METAL_PROXY
    man["score_run_drops_final_bar_dated_on_or_after_today"] = True
    with open(os.path.join(a.out, "FROZEN_DEFINITIONS.json"), "w") as f:
        json.dump(man, f, indent=2, sort_keys=True)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
