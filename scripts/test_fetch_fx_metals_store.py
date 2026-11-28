#!/usr/bin/env python3
"""Fixed synthetic checks for scripts/fetch_fx_metals_store.py (no network)."""
import csv
import json
import os
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_fx_metals_store as F  # noqa: E402

PASS = FAIL = 0


def check(name, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
    else:
        FAIL += 1
        print("FAIL", name, detail)


def fut_payload():
    # 2023-06-12 04:00Z (= 00:00 EDT Mon), 2023-01-09 05:00Z (= 00:00 EST Mon),
    # 2023-01-10 14:30Z (= 09:30 EST Tue), one null-close bar, one dup date.
    ts = [1673240400, 1673361000, 1686542400, 1686542460, 1686628800]
    return {"chart": {"result": [{
        "meta": {"gmtoffset": -18000, "exchangeTimezoneName": "America/New_York"},
        "timestamp": ts,
        "indicators": {
            "quote": [{"high": [2.0, 3.0, 4.0, 5.0, None], "low": [1.0, 2.0, 3.0, 4.0, 1.0],
                       "close": [1.5, 2.5, 3.5, 4.5, 2.0], "volume": [10, 0, None, 7, 1]}],
            "adjclose": [{"adjclose": [1.5, 2.5, 3.5, 4.5, 2.0]}]}}]}}


def run():
    syms = list(F.FX_SYMBOLS.values()) + list(F.METAL_PROXY.values())
    check("FX stays spot; metals are exactly GC=F/SI=F and every metal name says FUTURES_PROXY",
          set(F.METAL_PROXY.values()) == {"GC=F", "SI=F"} and all(n.endswith("_FUTURES_PROXY") for n in F.METAL_PROXY)
          and not any(s in ("GC=F", "SI=F") for s in F.FX_SYMBOLS.values()) and len(set(syms)) == 15)
    egp_r = [("2024-03-04", 1, 1, 30.0, 0, 30.0), ("2024-03-05", 1, 1, 45.0, 0, 45.0), ("2024-03-06", 1, 1, 60.0, 0, 60.0), ("2024-03-07", 1, 1, 0.0, 0, 0.0)]
    sar_r = [("2024-03-05", 1, 1, 3.0, 0, 3.0), ("2024-03-06", 1, 1, 4.0, 0, 4.0), ("2024-03-07", 1, 1, 3.0, 0, 3.0), ("2024-03-08", 1, 1, 3.0, 0, 3.0)]
    dr, ne, de = F.derive_cross(egp_r, sar_r)
    check("derive_cross: ratio on common dates only, zero close dropped, one-side dates counted, close only",
          dr == [("2024-03-05", "", "", 15.0, "", ""), ("2024-03-06", "", "", 15.0, "", "")] and ne == 1 and de == 2, str((dr, ne, de)))
    check("derive_cross is numerator over denominator (not inverted)", F.derive_cross([("d", 1, 1, 50.0, 0, 0)], [("d", 1, 1, 4.0, 0, 0)])[0][0][3] == 12.5)
    check("derived spec: SAR/EGP = USDEGP/USDSAR, AED/EGP = USDEGP/USDAED",
          F.DERIVED_CROSS == {"SAREGP_DERIVED": ("USDEGP", "USDSAR"), "AEDEGP_DERIVED": ("USDEGP", "USDAED")})
    rows, sk = F.parse_futures(fut_payload())
    check("session date is the New York date, not the fixed -5h meta offset",
          [r[0] for r in rows] == ["2023-01-09", "2023-01-10", "2023-06-12"], str(rows))
    check("null-high bar skipped and counted; duplicate date keeps last; zero volume kept",
          sk == 1 and rows[2][3] == 4.5 and rows[1][4] == 0, str(rows) + str(sk))
    check("adjclose carried through", rows[0][5] == 1.5)
    r2, d = F.drop_final_partial(rows, "2023-06-12")
    check("score run drops a final bar dated today", d == 1 and len(r2) == 2)
    r3, d = F.drop_final_partial(rows, "2023-06-13")
    check("score run keeps a final bar dated before today", d == 0 and len(r3) == 3)
    check("empty series safe", F.drop_final_partial([], "2023-06-13") == ([], 0))
    gold = [("2024-03-04", "", "", 2000.0, "", ""), ("2024-03-05", "", "", 2100.0, "", "")]
    egp = [("2024-03-05", 1, 1, 50.0, "", ""), ("2024-03-06", 1, 1, 49.0, "", "")]
    check("gold in EGP = proxy close x USDEGP on common dates only",
          F.derive_gold_egp(gold, egp) == [("2024-03-05", "", "", 105000.0, "", "")])
    check("EGP regime split at 2024-03-06",
          F.egp_regime("2024-03-05") == "pre-float" and F.egp_regime("2024-03-06") == "float")
    check("years_back incl. 29 Feb", F.years_back("2024-02-29", 10) == "2014-02-28"
          and F.years_back("2026-11-28", 20) == "2006-11-28")
    d = F.FROZEN_DEFINITIONS
    check("frozen: proxy label, roll not adjusted, New York session date, week 5 / month 21",
          "futures-proxy" in d["metals_proxy_label"] and "NOT back-adjusted" in d["metals_proxy_roll"]
          and "America/New_York" in d["metals_proxy_close"] and d["week_sessions"] == 5 and d["month_sessions"] == 21)
    check("manifest: splice dates not asserted, window rule and holiday limitation recorded",
          "No roll date is asserted" in d["metals_proxy_roll_dates"] and "roll_window=1" in d["metals_proxy_roll_dates"]
          and "NOT sourced" in d["metals_roll_window_rule"] and "ALL 12" in d["metals_roll_window_rule"])
    D = F.datetime.date
    check("last trade = third last weekday (CME rule); matches published GCZ6/GCG7/GCQ6 dates",
          F.last_trade_date(2026, 12) == D(2026, 12, 29) and F.last_trade_date(2027, 2) == D(2027, 2, 24)
          and F.last_trade_date(2026, 8) == D(2026, 8, 27))
    check("first notice = last weekday of the previous month; Dec-2025 = 2025-11-28 (observed splice), GCZ6 = 2026-11-30, January wraps the year",
          F.first_notice_date(2025, 12) == D(2025, 11, 28) and F.first_notice_date(2026, 12) == D(2026, 11, 30)
          and F.first_notice_date(2026, 8) == D(2026, 7, 31) and F.first_notice_date(2026, 1) == D(2025, 12, 31))
    check("silver evidence recorded: monthly splices incl. out-of-cycle Oct/Nov contracts, 12-month windows kept",
          "MONTHLY" in d["metals_roll_silver_evidence"] and "SIX26" in d["metals_roll_silver_evidence"]
          and "12-month" in d["metals_roll_silver_evidence"])
    w26 = F.roll_window_dates(2026, 2026, days=1)
    check("observed silver splice days are covered by the window rule: 2026-10-29 (Oct last trade 10-28 +1) and 2026-11-27",
          F.last_trade_date(2026, 10) == D(2026, 10, 28) and "2026-10-29" in w26
          and F.last_trade_date(2026, 11) == D(2026, 11, 26) and "2026-11-27" in w26)
    ev0 = F.roll_window_dates(2026, 2026, days=0)
    check("days=0 flags exactly event dates (2026-04-28 last trade, 2026-04-30 first notice) and not the day between",
          "2026-04-28" in ev0 and "2026-04-30" in ev0 and "2026-04-29" not in ev0 and "2026-05-01" not in ev0)
    win = F.roll_window_dates(2026, 2026)
    check("default window is +-5 days inclusive: 2026-04-30 +5 = 2026-05-05 flagged, 2026-05-06 not (next event 2026-05-27 -5 = 05-22)",
          "2026-05-05" in win and "2026-05-06" not in win and "2026-04-23" in win)
    check("all 12 delivery months contribute events (January first-notice 2026-01-30, January last-trade 2026-01-28)",
          "2026-01-30" in ev0 and "2026-01-28" in ev0)
    check("the observed Nov-2025 splice day is inside the window", "2025-11-28" in F.roll_window_dates(2025, 2025))
    # end-to-end with stubbed network
    o = F.Y.fetch
    t = 1675339200
    fx = {"chart": {"result": [{"meta": {"gmtoffset": 0}, "timestamp": [t, t + 86400],
        "indicators": {"quote": [{"high": [2.0, 2.0], "low": [1.0, 1.0], "close": [1.5, 1.6], "volume": [0, 0]}]}}]}}
    F.Y.fetch = lambda sym, s, e: fut_payload() if sym in ("GC=F", "SI=F") else fx
    with tempfile.TemporaryDirectory() as d:
        code = F.main(["--out", d, "--today", "2026-11-28"])
        names = sorted(os.listdir(d))
        man = json.load(open(os.path.join(d, "FROZEN_DEFINITIONS.json")))
        gold_rows = list(csv.reader(open(os.path.join(d, "XAUUSD_FUTURES_PROXY.csv"))))
        check("end-to-end: 13 FX + 2 proxy + derived csv, manifest, exit 0",
              code == 0 and len([n for n in names if n.endswith(".csv")]) == 18
              and "XAUEGP_FUTURES_PROXY.csv" in names and "FROZEN_DEFINITIONS.json" in names, str(names))
        check("all 13 named FX series harvested, each from its own Yahoo symbol, and recorded in the manifest",
              len(F.FX_SYMBOLS) == 13 and set(F.FX_SYMBOLS) == {"USDEGP", "EUREGP", "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", "EURGBP", "EURJPY", "GBPEGP", "USDSAR", "USDAED"}
              and F.FX_SYMBOLS["USDSAR"] == "USDSAR=X" and F.FX_SYMBOLS["GBPEGP"] == "GBPEGP=X"
              and all(n + ".csv" in names for n in F.FX_SYMBOLS) and man["fx_symbols"] == F.FX_SYMBOLS)
        sar = list(csv.reader(open(os.path.join(d, "SAREGP_DERIVED.csv"))))
        check("derived files written, labelled DERIVED with formula, in manifest; no unlabelled SAR/AED EGP file",
              sar[0][-2:] == ["derived", "formula"] and len(sar) == 3 and all(r[-2] == F.DERIVED_LABEL and r[-1] == "USDEGP / USDSAR" for r in sar[1:])
              and abs(float(sar[1][3]) - 1.5 / 1.5) < 1e-12 and "AEDEGP_DERIVED.csv" in names
              and set(man["derived_cross_rates"]) == {"SAREGP_DERIVED", "AEDEGP_DERIVED"}
              and not any(n in ("SAREGP.csv", "AEDEGP.csv") for n in names))
        check("every proxy csv row carries the proxy label; header has roll_window and proxy columns",
              gold_rows[0][-2:] == ["roll_window", "proxy"] and all(r[-2] in ("0", "1") for r in gold_rows[1:]) and all(r[-1] == F.PROXY_LABEL for r in gold_rows[1:]) and len(gold_rows) == 4)
        check("no unlabelled metal file is written",
              not any(n.startswith(("XAU", "XAG")) and "FUTURES_PROXY" not in n for n in names)
              and man["metal_proxy_symbols"] == F.METAL_PROXY)
        F.main(["--out", d, "--today", "2023-02-03", "--score-run"])
        usd = list(csv.reader(open(os.path.join(d, "USDEGP.csv"))))
        check("score run drops the FX final bar dated today", len(usd) == 2 and usd[-1][0] == "2023-02-02", str(usd))
        check("short history refused", F.main(["--out", d, "--fx-years", "4"]) == 2)
    F.Y.fetch = o
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    rc = run()
    print("test_fetch_fx_metals_store: %d passed, %d failed" % (PASS, FAIL))
    sys.exit(rc)
