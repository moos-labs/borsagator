#!/usr/bin/env python3
"""Checks backtest/extension_plan_2026-08-14.json (INS-IMPROVE-001 P5).
Standalone, stdlib only: python3 scripts/test_extension_plan_2026_08_14.py
"""
import datetime
import json
import os
import re
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CHECKS = {"pass": 0, "fail": 0}


def check(name, ok, detail=""):
    CHECKS["pass" if ok else "fail"] += 1
    if not ok:
        print("FAIL %s %s" % (name, detail))


def main():
    with open(os.path.join(ROOT, "backtest",
                           "extension_plan_2026-08-14.json")) as f:
        plan = json.load(f)
    src = open(os.path.join(ROOT, "scripts", "backtest.py")).read()
    used_cutoffs = set(re.findall(r'"(\d{4}-\d{2}-\d{2})"',
                                  src[src.index("CUTOFFS_V1"):
                                      src.index("TICKERS_V1")]))
    cells = plan["cells"]
    nums = [c["cell"] for c in cells]
    check("six cells", len(cells) == 6, str(len(cells)))
    check("numbered 73..78 in order", nums == list(range(73, 79)), str(nums))
    check("tickers are the six of cells 56-61",
          [c["ticker"] for c in cells]
          == ["COMI.CA", "ETEL.CA", "TMGH.CA", "NVDA", "SWDY.CA",
              "HRHO.CA"])
    check("no ORAS/POUL",
          not {"ORAS.CA", "POUL.CA"} & {c["ticker"] for c in cells})
    check("one cutoff", {c["cutoff"] for c in cells} == {plan["cutoff"]})
    cut = datetime.date.fromisoformat(plan["cutoff"])
    check("cutoff is a Friday (base close is the prior session, as for "
          "cell 1)", cut.weekday() == 4, cut.isoformat())
    check("not a quarter-end of the v1 plan",
          plan["cutoff"] not in used_cutoffs, str(sorted(used_cutoffs)))
    check("window clears neighbouring quarter-ends",
          datetime.date(2026, 7, 30) < cut
          and cut + datetime.timedelta(days=31)
          < datetime.date(2026, 9, 30))
    check("exception is documented",
          "mid-quarter" in plan["documented_exception"]["deviation"])
    print("test_extension_plan_2026_08_14: %d passed, %d failed"
          % (CHECKS["pass"], CHECKS["fail"]))
    return 1 if CHECKS["fail"] else 0


if __name__ == "__main__":
    sys.exit(main())
