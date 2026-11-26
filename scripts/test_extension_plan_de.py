#!/usr/bin/env python3
"""Checks backtest/extension_plan_2025-11-14_2025-08-15.json
(INS-IMPROVE-001 round 2, batches D and E).
Standalone, stdlib only: python3 scripts/test_extension_plan_de.py
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
TICKERS = ["COMI.CA", "ETEL.CA", "TMGH.CA", "NVDA", "SWDY.CA", "HRHO.CA"]


def check(name, ok, detail=""):
    CHECKS["pass" if ok else "fail"] += 1
    if not ok:
        print("FAIL %s %s" % (name, detail))


def d(s):
    return datetime.date.fromisoformat(s)


def load(name):
    with open(os.path.join(ROOT, "backtest", name)) as f:
        return json.load(f)


def main():
    plan = load("extension_plan_2025-11-14_2025-08-15.json")
    a = load("extension_plan_2026-08-14.json")
    bc = load("extension_plan_2026-05-15_2026-02-13.json")
    src = open(os.path.join(ROOT, "scripts", "backtest.py")).read()
    qe = re.findall(r'"(\d{4}-\d{2}-\d{2})"',
                    src[src.index("CUTOFFS_V1"):src.index("TICKERS_V1")])
    cells = plan["cells"]
    nums = [c["cell"] for c in cells]
    check("twelve cells", len(cells) == 12, str(len(cells)))
    check("numbered 91..102 in order", nums == list(range(91, 103)),
          str(nums))
    check("cells follow batches B and C",
          nums[0] == max(c["cell"] for c in bc["cells"]) + 1)
    check("cutoff order 2025-11-14 then 2025-08-15",
          [c["cutoff"] for c in cells]
          == ["2025-11-14"] * 6 + ["2025-08-15"] * 6)
    check("ticker order per cutoff",
          [c["ticker"] for c in cells[:6]] == TICKERS
          and [c["ticker"] for c in cells[6:]] == TICKERS)
    check("no ORAS/POUL",
          not {"ORAS.CA", "POUL.CA"} & {c["ticker"] for c in cells})
    check("no duplicate pairs",
          len({(c["ticker"], c["cutoff"]) for c in cells}) == 12)
    check("cutoffs are Fridays",
          all(d(c).weekday() == 4 for c in plan["cutoffs"]))
    others = sorted(set(qe) | {a["cutoff"]} | set(bc["cutoffs"]))
    check("none is an existing cutoff",
          not set(plan["cutoffs"]) & set(others))
    for c in plan["cutoffs"]:
        gap = min(abs((d(c) - d(o)).days) for o in others)
        check("window of %s clears every other cutoff" % c, gap > 31,
              str(gap))
    mid = sorted([a["cutoff"]] + bc["cutoffs"] + plan["cutoffs"])
    check("five mid-quarter cutoffs", len(mid) == 5, str(mid))
    check("mid-quarter cutoffs 91 days apart",
          all((d(y) - d(x)).days == 91 for x, y in zip(mid, mid[1:])),
          str(mid))
    check("five cutoffs x six tickers = 30",
          len(mid) * len(TICKERS) == 30)
    check("exception is documented",
          "mid-quarter" in plan["documented_exception"]["deviation"])
    print("test_extension_plan_de: %d passed, %d failed"
          % (CHECKS["pass"], CHECKS["fail"]))
    return 1 if CHECKS["fail"] else 0


if __name__ == "__main__":
    sys.exit(main())
