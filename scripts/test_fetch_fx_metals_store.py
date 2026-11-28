#!/usr/bin/env python3
"""Fixed synthetic checks for scripts/fetch_fx_metals_store.py (no network)."""
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


def run():
    check("no futures proxy symbol is fetched",
          not any(s in ("GC=F", "SI=F") for s in F.FX_SYMBOLS.values()) and
          set(F.METALS) == {"XAUUSD", "XAGUSD"})
    check("eight verified FX symbols", len(F.FX_SYMBOLS) == 8 and F.FX_SYMBOLS["USDEGP"] == "EGP=X")
    rows, sk = F.parse_frankfurter([
        {"date": "2024-03-05", "rate": 2101.86}, {"date": "2024-03-04", "rate": "2069.5"},
        {"date": "2024-03-04", "rate": 2070.0}, {"date": "2024-03-06", "rate": 0},
        {"date": "2024-03-07"}, {"rate": 1}])
    check("frankfurter: sorted, duplicate keeps last, bad entries counted",
          rows == [("2024-03-04", "", "", 2070.0, "", ""), ("2024-03-05", "", "", 2101.86, "", "")] and sk == 3, str(rows))
    try:
        F.parse_frankfurter({"message": "x"}); ok = False
    except ValueError:
        ok = True
    check("frankfurter: non-list payload rejected", ok)
    gold = [("2024-03-04", "", "", 2000.0, "", ""), ("2024-03-05", "", "", 2100.0, "", "")]
    egp = [("2024-03-05", 1, 1, 50.0, "", ""), ("2024-03-06", 1, 1, 49.0, "", "")]
    check("gold in EGP = XAUUSD x USDEGP on common dates only",
          F.derive_gold_egp(gold, egp) == [("2024-03-05", "", "", 105000.0, "", "")])
    check("EGP regime split at 2024-03-06",
          F.egp_regime("2024-03-05") == "pre-float" and F.egp_regime("2024-03-06") == "float")
    check("years_back incl. 29 Feb", F.years_back("2024-02-29", 10) == "2014-02-28"
          and F.years_back("2026-11-28", 20) == "2006-11-28")
    d = F.FROZEN_DEFINITIONS
    check("frozen constants", d["week_sessions"] == 5 and d["month_sessions"] == 21
          and "LBMA AM" in d["metals_close_frozen"] and "NOT the LBMA" in d["metals_close_in_this_store"])
    # end-to-end with stubbed network
    o = (F.Y.fetch, F.fetch_frankfurter)
    t = 1675339200
    F.Y.fetch = lambda sym, s, e: {"chart": {"result": [{"meta": {"gmtoffset": 0}, "timestamp": [t],
        "indicators": {"quote": [{"high": [2.0], "low": [1.0], "close": [1.5], "volume": [0]}]}}]}}
    F.fetch_frankfurter = lambda b, s, e: [{"date": "2023-02-02", "rate": 1000.0}]
    with tempfile.TemporaryDirectory() as d:
        code = F.main(["--out", d, "--today", "2026-11-28"])
        names = sorted(os.listdir(d))
        txt = open(os.path.join(d, "XAUEGP.csv")).read()
        check("end-to-end: all files, derived row 1500, exit 0",
              code == 0 and "XAUEGP.csv" in names and "FROZEN_DEFINITIONS.json" in names
              and len([n for n in names if n.endswith(".csv")]) == 11 and "1500.0" in txt, str(names) + txt)
        check("short history refused", F.main(["--out", d, "--fx-years", "4"]) == 2)
    F.Y.fetch, F.fetch_frankfurter = o
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    rc = run()
    print("test_fetch_fx_metals_store: %d passed, %d failed" % (PASS, FAIL))
    sys.exit(rc)
