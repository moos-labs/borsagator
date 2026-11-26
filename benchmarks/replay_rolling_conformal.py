#!/usr/bin/env python3
"""Shadow challenger: rolling per-ticker conformal recalibration of the
frozen v2 band (INS-IMPROVE-007 item 4, targets T3 and T4).

Distinct from #770 (ACI, pooled across tickers, adaptive alpha). Here
the level is fixed and the calibration set is local and trailing:
  half_RC = q x half_v2,  half_v2 = V2_BAND_K[h] x sigma60 x
  sqrt(sessions_h) x RISK_MULT (frozen, untouched).
Score of a matured row s = |realised move| / half_v2.
For a target cutoff T, ticker i, horizon h:
  1. Eligible = rows of the same ticker and horizon with cutoff
     <= T - 35 days (the month horizon has matured by then).
  2. Take the last W = 6 eligible cutoffs' scores (trailing window).
  3. With at least MIN_HIST = 4 scores, q = the ceil((n+1) x 0.80)/n-th
     smallest (largest if the index exceeds n). Otherwise q = 1
     (the band is v2).
LEVEL 0.80 (middle of 0.75-0.85), W, MIN_HIST and the 35-day guard are
fixed here by the brief and are NOT fitted: no cell is used to choose
them. Because nothing is fitted, any target cell can be scored without
leakage, but cells 48-90 informed earlier decisions, so they stay
descriptive. Calibration history before a target is allowed to come
from any earlier cutoff (it is data the engine would have had).

Screening exclusion rule: descriptive runs use --max-cell 90 by
default so no verdict cell (>= 91) and no ledger row enters a
descriptive run. A clean run (>= 91) is refused unless it is the one
scoring of the final holdout block, and is not run here.

Pre-registered keep rule: the round 3 rule via V.keep_verdict
(RangeSkill cutoff-clustered CI lower bound > 0, coverage leg as
V.keep_verdict states it; #775 changes it to the cutoff-clustered
coverage CI overlapping [0.75, 0.85]). Both the point coverage and the
coverage CI are printed so either reading is visible. Effective n is
printed beside raw n as the number of cutoff clusters. Challengers
tried to date in INS-IMPROVE-006/007 (for multiple-testing reading):
A, B, C, D, E, F, this one is the 7th shadow challenger.

Usage:
  python3 benchmarks/replay_rolling_conformal.py diag --captures DIR ...
      (target cells 1-47, descriptive, no verdict)
  python3 benchmarks/replay_rolling_conformal.py score --captures DIR ...
      [--min-cell 48] [--max-cell 90] [--descriptive] [--reps 5000]
      [--json OUT]    (clean = --min-cell 91, no --descriptive)
"""
import argparse
import datetime as dt
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
import replay_vol_adaptive as V  # noqa: E402
import score_adoption_594 as A  # noqa: E402
import ensemble as ens_mod  # noqa: E402

HORIZONS = A.HORIZONS
LEVEL = 0.80
WINDOW = 6
MIN_HIST = 4
MATURITY_DAYS = 35
CLEAN_MIN_CELL = 91
DESC_MAX_CELL = 90
keep_verdict = V.keep_verdict
_f = V._f


def _date(s):
    return dt.date.fromisoformat(str(s)[:10])


def _half_v2(r):
    h = r["horizon"]
    return R.half_pct(r["v2_sigma"], h, ens_mod.V2_BAND_K[h], r["mult"])


def score_of(r):
    half = _half_v2(r)
    return abs(r["real"]) / half if half > 0 else None


def conformal_q(scores):
    n = len(scores)
    if n < MIN_HIST:
        return 1.0
    idx = math.ceil((n + 1) * LEVEL)
    return sorted(scores)[min(idx, n) - 1]


def q_for(ticker, horizon, target_asof, rows):
    """(q, n_used) from this ticker's matured rows of the horizon."""
    t = _date(target_asof) - dt.timedelta(days=MATURITY_DAYS)
    mine = [r for r in rows if r["ticker"] == ticker
            and r["horizon"] == horizon and _date(r["as_of"]) <= t
            and score_of(r) is not None]
    cutoffs = sorted({r["as_of"] for r in mine})[-WINDOW:]
    scores = [score_of(r) for r in mine if r["as_of"] in cutoffs]
    return conformal_q(scores), len(scores)


def score_rows(rows, target_pred):
    usable = [r for r in rows if r["v2_sigma"]]
    out = []
    for r in usable:
        if not target_pred(r):
            continue
        q, n_used = q_for(r["ticker"], r["horizon"], r["as_of"], usable)
        v2 = _half_v2(r)
        ch = q * v2
        out.append({"ticker": r["ticker"], "as_of": r["as_of"],
                    "horizon": r["horizon"], "q": q, "n_used": n_used,
                    "is_naive": R.row_is(r, r["naive_half"]),
                    "is_v2": R.row_is(r, v2), "is_ch": R.row_is(r, ch),
                    "in_v2": abs(r["real"]) <= v2,
                    "in_ch": abs(r["real"]) <= ch})
    return out


def render(res, pairs, descriptive, title):
    L = [title, "rolling per-ticker conformal over frozen v2: level "
         "%.2f, window %d cutoffs, min history %d, maturity guard %d d"
         % (LEVEL, WINDOW, MIN_HIST, MATURITY_DAYS)]
    for h in HORIZONS:
        c = res[h]
        hp = [p for p in pairs if p["horizon"] == h]
        live = sum(p["n_used"] >= MIN_HIST for p in hp)
        L.append("%s: raw n=%d, effective n (cutoff clusters)=%d, %d "
                 "tickers, rows recalibrated %d (q != 1 possible)"
                 % (h, c["n"], c["cutoffs"], c["tickers"], live))
        L.append("  RC coverage %s  coverage CI cutoff [%s, %s]  "
                 "RangeSkill %s  CI cutoff [%s, %s]  CI ticker [%s, %s]"
                 % (_f(c["ch"]["coverage"]), _f(c["ch_cov_ci_cutoff"][0]),
                    _f(c["ch_cov_ci_cutoff"][1]),
                    _f(c["ch"]["range_skill"]), _f(c["ch_ci_cutoff"][0]),
                    _f(c["ch_ci_cutoff"][1]), _f(c["ch_ci_ticker"][0]),
                    _f(c["ch_ci_ticker"][1])))
        L.append("  frozen v2  coverage %s  RangeSkill %s"
                 % (_f(c["v2"]["coverage"]), _f(c["v2"]["range_skill"])))
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
    s.add_argument("--max-cell", type=int, default=None)
    s.add_argument("--descriptive", action="store_true")
    s.add_argument("--reps", type=int, default=A.DEFAULT_REPS)
    s.add_argument("--seed", type=int, default=A.DEFAULT_SEED)
    s.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    if (a.mode == "score" and a.min_cell < CLEAN_MIN_CELL
            and not a.descriptive):
        print("refusing: cells below %d need --descriptive"
              % CLEAN_MIN_CELL)
        return 2
    if a.mode == "score" and a.descriptive and a.max_cell is None:
        a.max_cell = DESC_MAX_CELL
    if (a.mode == "score" and a.descriptive
            and a.max_cell >= CLEAN_MIN_CELL):
        print("refusing: descriptive runs must stay below cell %d "
              "(holdout block)" % CLEAN_MIN_CELL)
        return 2
    allc = A.find_captures(a.captures, None)
    rows, gaps = R.build_rows(allc, allc)
    if a.mode == "diag":
        pairs = score_rows(rows, lambda r: r["cell"] is not None
                           and r["cell"] <= a.max_cell)
        res = R.evaluate(pairs, a.reps)
        print(render(res, pairs, True, "TARGET CELLS 1-%d, descriptive "
                     "only" % a.max_cell))
        return 0
    hi = a.max_cell if a.max_cell is not None else 10 ** 9
    pairs = score_rows(rows, lambda r: r["cell"] is not None
                       and a.min_cell <= r["cell"] <= hi)
    res = R.evaluate(pairs, a.reps, a.seed)
    print(render(res, pairs, a.descriptive,
                 "DESCRIPTIVE ONLY, cells %d-%d, no verdict valid"
                 % (a.min_cell, hi) if a.descriptive
                 else "CLEAN SCORING, target cells >= %d" % a.min_cell))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump({"level": LEVEL, "window": WINDOW,
                       "min_hist": MIN_HIST, "results": res,
                       **({} if a.descriptive
                          else {"verdict": keep_verdict(res)[0]}),
                       "descriptive": a.descriptive}, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
