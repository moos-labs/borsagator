#!/usr/bin/env python3
"""Round 85 challenger 1: ACI over frozen v2 with ALPHA as an explicit lever.

Pre-registration: docs/round85_aci_lever_prereg.md (committed before any
number). Reuses replay_aci_conformal.py unchanged; only its ALPHA is
varied over the registered grid. Additive: nothing edits
scripts/ensemble.py or frozen values.

Usage:
  replay_aci_lever.py fit --captures DIR ... --out evaluation/aci_lever_selected.json
      (target cells 1-47: trade-off table and per-horizon selection)
  replay_aci_lever.py describe --captures DIR ... [--min-cell 48 --max-cell 102]
      (all grid values, numbers only, no verdict)
  replay_aci_lever.py score --selected FILE --captures DIR ... [--min-cell 91]
      (one scoring of the frozen selection, loop-bar rule)
"""
import argparse
import json
import os
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import replay_aci_conformal as C  # noqa: E402
import replay_band_candidates as R  # noqa: E402
import score_adoption_594 as A  # noqa: E402
import loop_bar  # noqa: E402

HORIZONS = C.HORIZONS
ALPHA_GRID = (0.15, 0.20, 0.25, 0.30)
COV_BAND = (0.75, 0.85)
CLEAN_MIN_CELL = 91
TRAIN_MAX_CELL = 47


def run_alpha(rows, alpha, pred, reps, seed=A.DEFAULT_SEED):
    """ACI scoring with the module ALPHA set to `alpha`, restored after."""
    old = C.ALPHA
    C.ALPHA = alpha
    try:
        pairs = C.score_rows(rows, pred)
    finally:
        C.ALPHA = old
    return pairs, R.evaluate(pairs, reps, seed)


def select_alpha(table):
    """table: {alpha: {coverage, range_skill}} for one horizon (training).
    In-band coverage and highest RangeSkill, ties to the larger alpha;
    if none in band, coverage closest to 0.80, ties to the larger alpha."""
    inband = [a for a, v in table.items() if v["coverage"] is not None
              and COV_BAND[0] <= v["coverage"] <= COV_BAND[1]
              and v["range_skill"] is not None]
    if inband:
        return max(inband, key=lambda a: (table[a]["range_skill"], a))
    have = [a for a, v in table.items() if v["coverage"] is not None]
    if not have:
        return None
    return min(have, key=lambda a: (round(abs(table[a]["coverage"] - 0.80), 9), -a))


def trade_off(rows, pred, reps, alphas=ALPHA_GRID):
    out = {}
    for a in alphas:
        _p, res = run_alpha(rows, a, pred, reps)
        out[a] = {h: {"n": res[h]["n"], "cutoffs": res[h]["cutoffs"],
                      "coverage": res[h]["ch"]["coverage"],
                      "range_skill": res[h]["ch"]["range_skill"],
                      "ci_cutoff": res[h]["ch_ci_cutoff"],
                      "v2_coverage": res[h]["v2"]["coverage"],
                      "v2_range_skill": res[h]["v2"]["range_skill"]}
                  for h in HORIZONS}
    return out


def render_table(tab, title):
    L = [title]
    for h in HORIZONS:
        for a in sorted(tab):
            c = tab[a][h]
            L.append("%s alpha %.2f: n=%d cutoffs=%d coverage %s RangeSkill %s "
                     "CI cutoff [%s, %s] | v2 coverage %s RangeSkill %s" % (
                         h, a, c["n"], c["cutoffs"], R._f(c["coverage"]),
                         R._f(c["range_skill"]), R._f(c["ci_cutoff"][0]),
                         R._f(c["ci_cutoff"][1]), R._f(c["v2_coverage"]),
                         R._f(c["v2_range_skill"])))
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="mode", required=True)
    f = sub.add_parser("fit")
    f.add_argument("--captures", nargs="+", required=True)
    f.add_argument("--out", required=True)
    f.add_argument("--reps", type=int, default=A.DEFAULT_REPS)
    d = sub.add_parser("describe")
    d.add_argument("--captures", nargs="+", required=True)
    d.add_argument("--min-cell", type=int, default=48)
    d.add_argument("--max-cell", type=int, default=102)
    d.add_argument("--reps", type=int, default=A.DEFAULT_REPS)
    d.add_argument("--json", default=None)
    s = sub.add_parser("score")
    s.add_argument("--selected", required=True)
    s.add_argument("--captures", nargs="+", required=True)
    s.add_argument("--min-cell", type=int, default=CLEAN_MIN_CELL)
    s.add_argument("--reps", type=int, default=A.DEFAULT_REPS)
    s.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    allc = A.find_captures(a.captures, None)
    rows, _gaps = R.build_rows(allc, allc)
    if a.mode == "fit":
        tab = trade_off(rows, lambda r: r["cell"] is not None and r["cell"] <= TRAIN_MAX_CELL, a.reps)
        sel = {h: select_alpha({al: tab[al][h] for al in tab}) for h in HORIZONS}
        print(render_table(tab, "TRAINING CELLS 1-%d (walk-forward)" % TRAIN_MAX_CELL))
        print("selected alpha per horizon:", sel)
        with open(a.out, "w", encoding="utf-8") as fh:
            json.dump({"grid": list(ALPHA_GRID), "selected": sel,
                       "training_max_cell": TRAIN_MAX_CELL,
                       "table": {str(al): tab[al] for al in tab}}, fh, indent=1)
        return 0
    if a.mode == "describe":
        tab = trade_off(rows, lambda r: r["cell"] is not None and a.min_cell <= r["cell"] <= a.max_cell, a.reps)
        print(render_table(tab, "DESCRIPTIVE ONLY cells %d-%d, no verdict" % (a.min_cell, a.max_cell)))
        if a.json:
            with open(a.json, "w", encoding="utf-8") as fh:
                json.dump({"descriptive": True, "cells": [a.min_cell, a.max_cell],
                           "table": {str(al): tab[al] for al in tab}}, fh, indent=1)
        return 0
    if a.min_cell < CLEAN_MIN_CELL:
        print("refusing: score is for cells >= %d only" % CLEAN_MIN_CELL)
        return 2
    sel = json.load(open(a.selected))["selected"]
    res = {}
    for h in HORIZONS:
        al = sel.get(h)
        if al is None:
            print("refusing: no selected alpha for %s" % h)
            return 2
        _p, rs = run_alpha(rows, al, lambda r: r["cell"] is not None and r["cell"] >= a.min_cell, a.reps)
        res[h] = rs[h]
    v, why = loop_bar.loop_bar_verdict(res)
    print("CLEAN SCORING cells >= %d, selected alpha %s" % (a.min_cell, sel))
    for h in HORIZONS:
        c = res[h]
        print("%s: n=%d cutoffs=%d coverage %s RangeSkill %s CI cutoff [%s, %s] | v2 coverage %s RangeSkill %s" % (
            h, c["n"], c["cutoffs"], R._f(c["ch"]["coverage"]), R._f(c["ch"]["range_skill"]),
            R._f(c["ch_ci_cutoff"][0]), R._f(c["ch_ci_cutoff"][1]),
            R._f(c["v2"]["coverage"]), R._f(c["v2"]["range_skill"])))
    print("LOOP BAR: %s%s" % (v, " (" + "; ".join(why) + ")" if why else ""))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump({"selected": sel, "results": res, "verdict": v, "reasons": why}, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
