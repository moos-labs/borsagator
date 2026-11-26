#!/usr/bin/env python3
"""Checks backtest/extension_plan_2026-05-15_2026-02-13.json
(INS-IMPROVE-001 round 2, batches B and C).
Standalone, stdlib only: python3 scripts/test_extension_plan_bc.py
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


def main():
    with open(os.path.join(ROOT, "backtest",
                           "extension_plan_2026-05-15_2026-02-13.json")) as f:
        plan = json.load(f)
    with open(os.path.join(ROOT, "backtest",
                           "extension_plan_2026-08-14.json")) as f:
        batch_a = json.load(f)
    src = open(os.path.join(ROOT, "scripts", "backtest.py")).read()
    qe = re.findall(r'"(\d{4}-\d{2}-\d{2})"',
                    src[src.index("CUTOFFS_V1"):src.index("TICKERS_V1")])
    cells = plan["cells"]
    nums = [c["cell"] for c in cells]
    check("twelve cells", len(cells) == 12, str(len(cells)))
    check("numbered 79..90 in order", nums == list(range(79, 91)),
          str(nums))
    check("cells follow batch A numbering",
          nums[0] == max(c["cell"] for c in batch_a["cells"]) + 1)
    check("cutoff order 2026-05-15 then 2026-02-13",
          [c["cutoff"] for c in cells]
          == ["2026-05-15"] * 6 + ["2026-02-13"] * 6)
    check("ticker order per cutoff",
          [c["ticker"] for c in cells[:6]] == TICKERS
          and [c["ticker"] for c in cells[6:]] == TICKERS)
    check("no ORAS/POUL",
          not {"ORAS.CA", "POUL.CA"} & {c["ticker"] for c in cells})
    pairs = {(c["ticker"], c["cutoff"]) for c in cells}
    check("no duplicate pairs", len(pairs) == 12)
    check("cutoffs are Fridays",
          all(d(c).weekday() == 4 for c in plan["cutoffs"]
              + plan["proposed_further_cutoffs"]["cutoffs"]))
    allc = set(plan["cutoffs"]) | set(
        plan["proposed_further_cutoffs"]["cutoffs"])
    check("none is a v1 quarter-end or batch A cutoff",
          not allc & (set(qe) | {batch_a["cutoff"]}))
    others = sorted(set(qe) | {batch_a["cutoff"]})
    for c in sorted(allc):
        gaps = [abs((d(c) - d(o)).days) for o in others]
        check("window of %s clears every other cutoff" % c,
              min(gaps) > 31, str(min(gaps)))
    pl = sorted(allc)
    check("new cutoffs clear each other",
          all((d(b) - d(a)).days > 31 for a, b in zip(pl, pl[1:])))
    check("proposed further cutoffs are two and not cells",
          len(plan["proposed_further_cutoffs"]["cutoffs"]) == 2
          and not {c["cutoff"] for c in cells}
          & set(plan["proposed_further_cutoffs"]["cutoffs"]))
    check("five cutoffs x six tickers = 30 rows",
          (1 + len(plan["cutoffs"])
           + len(plan["proposed_further_cutoffs"]["cutoffs"])) * 6 == 30)
    check("exception is documented",
          "mid-quarter" in plan["documented_exception"]["deviation"])
    check("tilt note says 18 rows, under 30",
          "18 untouched rows" in plan["tilt_rows_after_this_plan"])
    print("test_extension_plan_bc: %d passed, %d failed"
          % (CHECKS["pass"], CHECKS["fail"]))
    return 1 if CHECKS["fail"] else 0


if __name__ == "__main__":
    sys.exit(main())
