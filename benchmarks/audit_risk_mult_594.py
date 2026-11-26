#!/usr/bin/env python3
"""Diagnostic: does RISK_MULT confound the v2-vs-naive comparison?

INS-IMPROVE-001 round 1, proposal P0. Read-only, no scoring, no
fitting, no verdict.

The frozen v2 band is k x sigma60 x sqrt(sessions) x RISK_MULT[level]
(scripts/ensemble.py). The naive baseline carries NO multiplier. If
backtest captures carry a risk level other than "none", the v2 band
is wider than naive by that factor and RangeSkill / coverage differ
for a reason that has nothing to do with k. This script reports the
risk-level mix per capture group so the question is answered with
data instead of an assumption.

It also reports whether each capture has sigma60_daily. Captures
without it make both v2 and naive fall back to sigma_daily
(max(sigma60, sigma10)), which is a proxy, not the frozen formula.

Usage:
  python3 benchmarks/audit_risk_mult_594.py --captures DIR [DIR ...]
      [--min-cell 48] [--json OUT]
Same capture discovery as benchmarks/score_adoption_594.py.
"""
import argparse
import collections
import json
import os
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import score_adoption_594 as A  # noqa: E402
import ensemble as ens_mod  # noqa: E402
import backtest_score as bs  # noqa: E402


def audit(capture_dirs):
    """Per-capture facts + group summaries. Pure over the dirs."""
    rows = []
    for cap in capture_dirs:
        ens = bs.load_json(os.path.join(cap, "digest", "ensemble.json"))
        if not isinstance(ens, dict):
            continue
        risk = ens.get("risk") or {}
        level = risk.get("level")
        rows.append({
            "capture": cap,
            "cell": A.cell_number(cap),
            "cutoff": os.path.basename(os.path.dirname(cap)),
            "ticker": os.path.basename(cap).upper(),
            "risk_level": level,
            "risk_mult": ens_mod.RISK_MULT.get(level, 1.0),
            "risk_level_known": level in ens_mod.RISK_MULT,
            "has_sigma60": A.fnum(ens.get("sigma60_daily")) is not None,
        })
    summary = {"captures": len(rows),
               "risk_level_counts": dict(collections.Counter(
                   str(r["risk_level"]) for r in rows)),
               "mult_counts": dict(collections.Counter(
                   "%.2f" % r["risk_mult"] for r in rows)),
               "unknown_level_labels": sorted({
                   str(r["risk_level"]) for r in rows
                   if not r["risk_level_known"]}),
               "no_sigma60": sum(1 for r in rows if not r["has_sigma60"]),
               "confounded": sum(1 for r in rows if r["risk_mult"] != 1.0)}
    return rows, summary


def render(summary):
    L = ["RISK_MULT audit (P0, INS-IMPROVE-001): diagnostic only",
         "captures: %d" % summary["captures"],
         "risk level counts: %s" % json.dumps(
             summary["risk_level_counts"], sort_keys=True),
         "RISK_MULT applied to v2 band: %s" % json.dumps(
             summary["mult_counts"], sort_keys=True),
         "captures where v2 band != naive-width because of RISK_MULT: "
         "%d of %d" % (summary["confounded"], summary["captures"]),
         "captures without sigma60_daily (both bands use the "
         "sigma_daily proxy): %d" % summary["no_sigma60"]]
    if summary["unknown_level_labels"]:
        L.append("level labels not in RISK_MULT (scored as x1.0): %s"
                 % summary["unknown_level_labels"])
    L.append("READING: confounded == 0 means v2 vs naive differs only "
             "by k; anything above 0 means part of the gap is the "
             "multiplier.")
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.
                                 RawDescriptionHelpFormatter)
    ap.add_argument("--captures", nargs="+", required=True)
    ap.add_argument("--min-cell", type=int, default=48)
    ap.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    rows, summary = audit(A.find_captures(a.captures, a.min_cell))
    print(render(summary))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump({"summary": summary, "rows": rows}, f, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
