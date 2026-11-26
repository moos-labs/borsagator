#!/usr/bin/env python3
"""Fixed synthetic checks for benchmarks/descriptive_close_counts.py."""
import os
import sys
import tempfile

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "benchmarks"))
import descriptive_close_counts as C  # noqa: E402

PASS = FAIL = 0


def check(name, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
    else:
        FAIL += 1
        print("FAIL", name, detail)


def write(d, name, rows):
    with open(os.path.join(d, name), "w", encoding="utf-8") as f:
        f.write("Date,Open,High,Low,Close,Volume\n")
        for r in rows:
            f.write(",".join(str(x) for x in r) + ",1\n")


def test_counts():
    with tempfile.TemporaryDirectory() as d:
        sub = os.path.join(d, "x")
        os.makedirs(sub)
        write(sub, "egxpy_tst.csv", [
            ("2021-09-02", 10, 11, 9, 10),     # pre
            ("2021-09-03", 10, 11, 9, 10),     # pre, flat
            ("2021-09-06", 10, 11, 9, 10),     # post, straddle (prev pre)
            ("2021-09-07", 10, 11, 9, 12),     # post, close > high
            ("2021-09-08", 10, 10, 10, 10),    # post, close < prev, zero range
            ("2021-09-09", 10, 11, 9, 8),      # post, close < low
            ("2021-09-12", 8, 9, 8, 8),        # post, flat
            ("2023-12-28", 8, 9, 8, 8),        # post, flat, last allowed
            ("2023-12-31", 8, 9, 8, 8),        # excluded by date
            ("2024-01-01", 8, 9, 8, 99),       # excluded by date
        ])
        r = C.run(d)["tickers"]["TST"]
        pre, post = r["pre"], r["post"]
        check("pre sessions", pre["sessions"] == 2, pre)
        check("pre pairs and flat", (pre["pairs"], pre["flat_close"])
              == (1, 1), pre)
        check("post sessions", post["sessions"] == 6, post)
        check("straddle dropped", r["straddle_dropped"] == 1, r)
        check("post pairs", post["pairs"] == 5, post)
        check("post flat", post["flat_close"] == 2, post)
        check("post outside", post["outside_hl"] == 2, post)
        check("post zero range", post["zero_range"] == 1, post)
        check("last date", r["last"] == "2023-12-28", r)


def test_best_file_and_bad_rows():
    with tempfile.TemporaryDirectory() as d:
        a = os.path.join(d, "a")
        b = os.path.join(d, "b")
        os.makedirs(a)
        os.makedirs(b)
        write(a, "egxpy_tst.csv", [("2020-01-01", 1, 2, 1, 1)])
        write(b, "egxpy_tst.csv", [("2020-01-01", 1, 2, 1, 1),
                                   ("2020-01-02", 1, 2, 1, "x"),
                                   ("2020-01-03", 1, 2, 1, 1)])
        res = C.run(d)["tickers"]["TST"]
        check("longer file wins", res["source"].startswith("b"), res)
        check("bad row dropped", res["rows_dropped"] == 1, res)
        check("counts after drop", res["pre"]["sessions"] == 2, res)


def main():
    test_counts()
    test_best_file_and_bad_rows()
    print("test_close_counts: %d passed, %d failed" % (PASS, FAIL))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
