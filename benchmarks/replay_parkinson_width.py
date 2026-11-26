#!/usr/bin/env python3
"""Shadow challenger A: Parkinson range-based width, k unchanged.

INS-IMPROVE-006 experiment A (targets T2, T3). The frozen v2 band is
  half = k_h x sigma60 x sqrt(sessions_h) x RISK_MULT,
  k = V2_BAND_K = {day 1.15, week 1.28, month 1.20}.
This challenger replaces ONLY sigma60 (stdev of the last 60 close-to-
close log returns) with the Parkinson high-low estimator over the last
60 pre-cutoff bars,
  sigma_P = sqrt( mean( ln(H/L)^2 ) / (4 ln 2) ),
from the capture's own OHLC history (rows dated <= the base date,
replay_band_candidates.read_ohlc / sigmas). k is NOT refitted and the
V2 table is imported from scripts/ensemble.py, so there is nothing to
fit and nothing to freeze. Centre 0, RISK_MULT carried as in v2.

Disclosure, stated up front: Parkinson (park60) was already a round 1
(P2/P3) candidate in benchmarks/replay_band_candidates.py, with k
FITTED on cells 1-47. In that fit its leave-one-cutoff-out IS/naive
ratio lost to s60 (0.956/1.094/1.010 vs 0.962/1.028/0.971, day/week/
month). This item differs only in using the v2 k table unchanged. No
park60 band was ever scored on cells >= 48, so those cells are
unseen for this challenger.

Skill definitions: RangeSkill vs naive is the loop definition
(naive = 0 +/- 1.2816 x sigma60 x sqrt(sessions)). Also reported:
IS ratio vs a Parkinson-naive band (0 +/- 1.2816 x sigma_P x
sqrt(sessions)), so the width estimator is separated from k.

Pre-registered keep rule (same as the round 3 challengers), one
scoring, per horizon, with >= 30 rows over >= 5 tickers and >= 2
cutoffs: (1) RangeSkill CI lower bound (cutoff-clustered by as_of)
> 0 and (2) coverage within 0.75-0.85. KEEP when both hold on every
horizon, REJECT when the sample is enough and either fails,
INSUFFICIENT otherwise. Scoring refuses cells below --min-cell
(default 91, the cells no challenger has seen); lower cells need
--descriptive and carry no verdict. Nothing edits scripts/ensemble.py.

Usage:
  python3 benchmarks/replay_parkinson_width.py diag --captures DIR ...
      (fit cells 1-47, descriptive, no verdict)
  python3 benchmarks/replay_parkinson_width.py score --captures DIR ...
      [--min-cell 91] [--descriptive] [--reps 5000] [--json OUT]
"""
import argparse
import json
import math
import os
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import replay_band_candidates as R  # noqa: E402
import score_adoption_594 as A  # noqa: E402
import ensemble as ens_mod  # noqa: E402

HORIZONS = A.HORIZONS
MIN_ROWS, MIN_TICKERS, MIN_CUTOFFS = 30, 5, 2
COV_BAND = (0.75, 0.85)
NAIVE_K = 1.2816
CLEAN_MIN_CELL = 91


def score_rows(rows):
    out = []
    for r in rows:
        sp = r["sig"].get("park60")
        if not sp or not r["v2_sigma"]:
            continue
        h = r["horizon"]
        ch = R.half_pct(sp, h, ens_mod.V2_BAND_K[h], r["mult"])
        v2 = R.half_pct(r["v2_sigma"], h, ens_mod.V2_BAND_K[h],
                        r["mult"])
        pn = R.half_pct(sp, h, NAIVE_K, r["mult"])
        out.append({"ticker": r["ticker"], "as_of": r["as_of"],
                    "horizon": h,
                    "is_naive": R.row_is(r, r["naive_half"]),
                    "is_v2": R.row_is(r, v2), "is_ch": R.row_is(r, ch),
                    "is_pnaive": R.row_is(r, pn),
                    "in_v2": abs(r["real"]) <= v2,
                    "in_ch": abs(r["real"]) <= ch})
    return out


def pnaive_ratio(pairs):
    out = {}
    for h in HORIZONS:
        hp = [p for p in pairs if p["horizon"] == h]
        d = sum(p["is_pnaive"] for p in hp)
        out[h] = (sum(p["is_ch"] for p in hp) / d) if d else None
    return out


def keep_verdict(res):
    short = [h for h in HORIZONS
             if res[h]["n"] < MIN_ROWS
             or res[h]["tickers"] < MIN_TICKERS
             or res[h]["cutoffs"] < MIN_CUTOFFS]
    if short:
        return "INSUFFICIENT", [
            "%s n=%d tickers=%d cutoffs=%d (need >=%d, >=%d, >=%d)"
            % (h, res[h]["n"], res[h]["tickers"], res[h]["cutoffs"],
               MIN_ROWS, MIN_TICKERS, MIN_CUTOFFS) for h in short]
    bad = []
    for h in HORIZONS:
        lo = res[h]["ch_ci_cutoff"][0]
        cov = res[h]["ch"]["coverage"]
        if lo is None or lo <= 0:
            bad.append("%s CI lower bound %s not > 0" % (h, _f(lo)))
        if cov is None or not COV_BAND[0] <= cov <= COV_BAND[1]:
            bad.append("%s coverage %s outside [%.2f, %.2f]"
                       % (h, _f(cov), COV_BAND[0], COV_BAND[1]))
    return ("REJECT" if bad else "KEEP"), bad


def _f(v, nd=3):
    return "n/a" if v is None else ("%.*f" % (nd, v))


def render(res, pr, descriptive, title):
    L = [title, "Parkinson-60 width, k = %s (v2 table, unchanged)"
         % json.dumps(ens_mod.V2_BAND_K)]
    for h in HORIZONS:
        c = res[h]
        L.append("%s: n=%d, %d cutoffs, %d tickers"
                 % (h, c["n"], c["cutoffs"], c["tickers"]))
        L.append("  challenger coverage %s  RangeSkill %s  CI cutoff "
                 "[%s, %s]  CI ticker [%s, %s]"
                 % (_f(c["ch"]["coverage"]), _f(c["ch"]["range_skill"]),
                    _f(c["ch_ci_cutoff"][0]), _f(c["ch_ci_cutoff"][1]),
                    _f(c["ch_ci_ticker"][0]), _f(c["ch_ci_ticker"][1])))
        L.append("  frozen v2  coverage %s  RangeSkill %s  |  IS ratio "
                 "vs Parkinson-naive %s"
                 % (_f(c["v2"]["coverage"]), _f(c["v2"]["range_skill"]),
                    _f(pr[h])))
    if not descriptive:
        v, why = keep_verdict(res)
        L += ["", "KEEP RULE: %s%s" % (
            v, " (" + "; ".join(why) + ")" if why else "")]
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.
                                 RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="mode", required=True)
    d = sub.add_parser("diag")
    d.add_argument("--captures", nargs="+", required=True)
    d.add_argument("--max-cell", type=int, default=47)
    d.add_argument("--reps", type=int, default=A.DEFAULT_REPS)
    s = sub.add_parser("score")
    s.add_argument("--captures", nargs="+", required=True)
    s.add_argument("--min-cell", type=int, default=CLEAN_MIN_CELL)
    s.add_argument("--descriptive", action="store_true")
    s.add_argument("--reps", type=int, default=A.DEFAULT_REPS)
    s.add_argument("--seed", type=int, default=A.DEFAULT_SEED)
    s.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    allc = A.find_captures(a.captures, None)
    if a.mode == "diag":
        caps = [c for c in allc if A.cell_number(c) is not None
                and A.cell_number(c) <= a.max_cell]
        rows, gaps = R.build_rows(caps, allc)
        pairs = score_rows(rows)
        res = R.evaluate(pairs, a.reps)
        print(render(res, pnaive_ratio(pairs), True,
                     "FIT CELLS 1-%d, descriptive only" % a.max_cell))
        return 0
    if a.min_cell < CLEAN_MIN_CELL and not a.descriptive:
        print("refusing: cells below %d need --descriptive"
              % CLEAN_MIN_CELL)
        return 2
    # Unnumbered captures cannot be placed relative to the clean-cell
    # boundary, so they never enter a scoring.
    caps = [c for c in A.find_captures(a.captures, a.min_cell)
            if A.cell_number(c) is not None]
    rows, gaps = R.build_rows(caps, allc)
    pairs = score_rows(rows)
    res = R.evaluate(pairs, a.reps, a.seed)
    print(render(res, pnaive_ratio(pairs), a.descriptive,
                 "DESCRIPTIVE ONLY, no verdict valid" if a.descriptive
                 else "CLEAN SCORING, cells >= %d" % a.min_cell))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            out = {"k": ens_mod.V2_BAND_K, "results": res,
                   "descriptive": a.descriptive}
            if not a.descriptive:
                out["verdict"] = keep_verdict(res)[0]
            json.dump(out, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
