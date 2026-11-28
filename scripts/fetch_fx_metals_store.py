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
    # added INS-IMPROVE-154 follow-up: the other five of the 13 FX series.
    # SAR=X/AED=X are the pegged controls (Yahoo also serves USDSAR=X, USDAED=X).
    "EURGBP": "EURGBP=X", "EURJPY": "EURJPY=X", "GBPEGP": "GBPEGP=X",
    "USDSAR": "USDSAR=X", "USDAED": "USDAED=X",
}
PROXY_LABEL = "futures-proxy-NOT-spot-NOT-LBMA-AM"
ROLL_WINDOW_DAYS = 5   # calendar days either side of a CME FND / last-trade date
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
    "metals_proxy_roll_dates": "Yahoo's GC=F / SI=F splice dates are NOT "
                               "published and cannot be reconstructed (Yahoo "
                               "keeps only live contracts). No roll date is "
                               "asserted. Instead every bar within "
                               + str(ROLL_WINDOW_DAYS) + " calendar days of "
                               "a CME first-notice or last-trade date is "
                               "flagged roll_window=1 and scorers must drop "
                               "the return ending on a flagged date.",
    "metals_roll_window_rule": "Events for ALL 12 delivery months of both "
                               "metals (more drops, not fewer): last trade "
                               "= third last business day of the delivery "
                               "month (CME COMEX rulebook ch.113 gold, "
                               "ch.112 silver); first notice = last business "
                               "day of the preceding month (third-party "
                               "sources; consistent with GC=F switching "
                               "contract on 2025-11-28, the Nov-2025 first "
                               "notice date). Business day = weekday: the "
                               "CME holiday list is NOT sourced (CME's "
                               "calendar endpoints block scripted access), "
                               "so the +-" + str(ROLL_WINDOW_DAYS) + "-day "
                               "margin absorbs the at most 1-2 day holiday "
                               "shift. Consistency check against published "
                               "dates: GCZ6 last trade 2026-12-29 / first "
                               "notice 2026-11-30; GCG7 last trade "
                               "2027-02-24; GCQ6 last trade 2026-08-27 / "
                               "first notice 2026-07-31 (futuresclock.com, "
                               "rule-calculated, third party).",
    "metals_roll_silver_evidence": "SI=F splices MONTHLY, including months "
                                   "outside silver's Mar/May/Jul/Sep/Dec "
                                   "delivery cycle, so silver keeps the 12-"
                                   "month windows. Evidence (exact close "
                                   "match of SI=F vs Yahoo individual "
                                   "contract tickers, checked 2026-11-28, "
                                   "0 mismatches inside each range): SI=F "
                                   "== SIZ25.CMX 2025-11-26..2025-12-29 (22 "
                                   "bars); == SIX26.CMX (Nov 2026) "
                                   "2026-10-29..2026-11-25 (20 bars); == "
                                   "SIZ26.CMX on 2026-11-27. Each switch "
                                   "falls the business day after the "
                                   "outgoing contract's last trade date "
                                   "(Oct 2026 contract 2026-10-28, Nov "
                                   "2026 contract 2026-11-25, Nov 2025 "
                                   "contract 2025-11-25). Older splices "
                                   "cannot be checked (expired contract "
                                   "tickers are not served).",
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


# Roll-window exclusion (option a, accepted by Moos 2026-11-28).
# Yahoo's splice dates for GC=F / SI=F are not published, so every bar within
# ROLL_WINDOW_DAYS calendar days of a CME first-notice or last-trade date is
# flagged roll_window=1 and its return must be excluded by scorers. All 12
# delivery months are used for both metals (both list every month), which
# drops MORE, not less.


def _weekdays_of(year, month):
    d = datetime.date(year, month, 1)
    out = []
    while d.month == month:
        if d.weekday() < 5:
            out.append(d)
        d += datetime.timedelta(days=1)
    return out


def last_trade_date(year, month):
    """CME rule (COMEX rulebook ch.113 gold / ch.112 silver, Termination of
    Trading): third last business day of the delivery month. Business day =
    weekday here (the CME holiday list is not sourced; see ROLL_WINDOW_DAYS)."""
    return _weekdays_of(year, month)[-3]


def first_notice_date(year, month):
    """Last business day of the month preceding the delivery month (rule
    stated by third-party sources only; consistent with the observed
    GC=F splice on 2025-11-28). Weekday approximation as above."""
    y, m = (year - 1, 12) if month == 1 else (year, month - 1)
    return _weekdays_of(y, m)[-1]


def roll_event_dates(first_year, last_year):
    ev = set()
    for y in range(first_year, last_year + 2):
        for m in range(1, 13):
            ev.add(last_trade_date(y, m))
            ev.add(first_notice_date(y, m))
    return ev


def roll_window_dates(first_year, last_year, days=ROLL_WINDOW_DAYS):
    out = set()
    for e in roll_event_dates(first_year, last_year):
        for k in range(-days, days + 1):
            out.add((e + datetime.timedelta(days=k)).isoformat())
    return out


def write_proxy_csv(path, rows):
    tmp = path + ".tmp"
    if rows:
        win = roll_window_dates(int(rows[0][0][:4]) - 1, int(rows[-1][0][:4]) + 1)
    else:
        win = set()
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "high", "low", "close", "volume", "adjclose",
                    "roll_window", "proxy"])
        for r in rows:
            w.writerow(list(r) + [1 if r[0] in win else 0, PROXY_LABEL])
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
