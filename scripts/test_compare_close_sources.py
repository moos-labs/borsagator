#!/usr/bin/env python3
"""Fixed synthetic checks for benchmarks/compare_close_sources.py."""
import os
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "benchmarks"))
import compare_close_sources as S  # noqa: E402

PASS = FAIL = 0


def check(name, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
    else:
        FAIL += 1
        print("FAIL", name, detail)


def test_compare():
    a = {"2021-09-06": 10.0, "2021-09-07": 10.0, "2021-09-08": 11.0,
         "2021-09-09": 11.0, "2021-09-12": 12.0, "2024-01-01": 1.0}
    b = {"2021-09-06": 10.0, "2021-09-07": 10.5, "2021-09-08": 11.0,
         "2021-09-09": 11.0, "2021-09-12": 12.0}
    r = S.compare(a, b)["post"]
    check("shared dates", r["shared_dates"] == 5, r)
    check("close differs", r["close_differs"] == 1, r)
    # pairs: 09-07 (a flat, b not), 09-08 (neither), 09-09 (both),
    # 09-12 (neither)
    check("pairs", r["pairs"] == 4, r)
    check("flat both", r["flat_both"] == 1, r)
    check("flat only first", r["flat_only_first"] == 1, r)
    check("flat only second", r["flat_only_second"] == 0, r)
    check("date after window excluded", r["close_equal"] == 4, r)


def test_prev_mismatch_skipped():
    a = {"2021-09-06": 1.0, "2021-09-07": 1.0, "2021-09-08": 2.0}
    b = {"2021-09-06": 1.0, "2021-09-08": 2.0}   # b lacks 09-07
    r = S.compare(a, b)["post"]
    check("different previous date is not a pair", r["pairs"] == 0, r)


def test_close_only():
    r = S.count_close_only({"2021-09-06": 1.0, "2021-09-07": 1.0})
    check("close only flat", r["post"]["flat_close"] == 1, r)
    check("close only no hl", r["post"]["outside_hl"] is None, r)


def main():
    test_compare()
    test_prev_mismatch_skipped()
    test_close_only()
    print("test_compare_close_sources: %d passed, %d failed"
          % (PASS, FAIL))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
