#!/usr/bin/env python3
"""Fixed synthetic checks for scripts/fetch_ohlcv_store.py (no network)."""
import os
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_ohlcv_store as F  # noqa: E402

PASS = FAIL = 0


def check(name, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
    else:
        FAIL += 1
        print("FAIL", name, detail)


def payload():
    # 2023-02-02 12:00 UTC, 03 and a duplicate-day bar, one null bar.
    t = 1675339200
    return {"chart": {"result": [{
        "meta": {"gmtoffset": 7200},
        "timestamp": [t, t + 86400, t + 2 * 86400, t + 2 * 86400 + 60],
        "indicators": {
            "quote": [{"high": [2.0, None, 4.0, 5.0],
                       "low": [1.0, 1.0, 3.0, 3.5],
                       "close": [1.5, 1.5, 3.5, 4.5],
                       "open": [9, 9, 9, 9],
                       "volume": [10, 20, None, 40]}],
            "adjclose": [{"adjclose": [1.4, 1.4, 3.4, 4.4]}]}}]}}


def test_parse():
    rows, skipped = F.parse_chart(payload())
    check("skips null bar", skipped == 1, skipped)
    check("duplicate date keeps last", len(rows) == 2, rows)
    check("session date uses gmtoffset", rows[0][0] == "2023-02-02", rows)
    check("last duplicate wins", rows[1][1:4] == (5.0, 3.5, 4.5), rows)
    check("open not stored", len(rows[0]) == 6, rows)
    check("adjclose kept", rows[0][5] == 1.4, rows)


def test_error_and_write():
    try:
        F.parse_chart({"chart": {"result": None,
                                 "error": {"code": "Not Found"}}})
        check("error raises", False)
    except ValueError:
        check("error raises", True)
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "T.csv")
        rows, _ = F.parse_chart(payload())
        F.write_csv(p, rows)
        lines = open(p).read().splitlines()
        check("csv header", lines[0] == "date,high,low,close,volume,adjclose",
              lines[0])
        check("csv rows", len(lines) == 3 and not os.path.exists(p + ".tmp"))


def main():
    test_parse()
    test_error_and_write()
    print("test_fetch_ohlcv_store: %d passed, %d failed" % (PASS, FAIL))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
