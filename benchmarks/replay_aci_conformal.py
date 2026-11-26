#!/usr/bin/env python3
"""Shadow challenger B: adaptive conformal (ACI) layer over frozen v2.

INS-IMPROVE-006 experiment B (target T3, coverage; T2 is not expected
to move, see the TCP evidence below). The frozen v2 band is the base:
  half_v2 = V2_BAND_K[h] x sigma60 x sqrt(sessions_h) x RISK_MULT.
A vol-normalised conformity score per matured row,
  s = |realised move| / half_v2,
(so s <= 1 means v2 covered the row). The layer rescales the v2
half-width by q, a conformal quantile of past scores:
  half_B = q x half_v2.

Walk-forward, nothing fitted, nothing from the future. For a target
cutoff T and horizon h:
  1. Eligible history = rows of the same horizon, all tickers pooled,
     whose cutoff P satisfies P <= T - 35 days (the 21-session month
     horizon has matured by then). Backtest history before the fit
     boundary is used as calibration history only; it is not scored.
  2. ACI level: alpha starts at ALPHA = 0.20 (target coverage 0.80,
     the middle of the 0.75-0.85 band) and is updated once per
     eligible past cutoff P in date order,
       alpha <- clip(alpha + GAMMA x (ALPHA - err_P), 0.02, 0.50),
     GAMMA = 0.05, where err_P is the share of P's rows NOT covered by
     the band q_P x half_v2 that was used at P (the same procedure
     replayed at P). err_P only matures at P + 35 days, so it is
     applied only to cutoffs at least 35 days after P: the alpha behind
     q_P (and q_T) holds the errors matured by that date, nothing newer.
  3. q_T = the ceil((n+1)(1-alpha))/n-th smallest pooled past score
     (the largest score if that index exceeds n). With fewer than
     MIN_HIST = 12 past scores, q = 1 (the band equals v2).
ALPHA, GAMMA, the 0.02-0.50 clip, the 35-day maturity guard, MIN_HIST
and the pooling are fixed here by the brief; none is fitted.

Evidence behind the expectation (read by Ins, abstract/intro): the TCP
paper (arxiv 2507.05470) found conformal intervals reach about 95%
coverage but lost 42 of 52 interval-score tests to volatility models
and won none. So B is run for coverage (T3/T4), and RangeSkill is not
expected to rise.

Pre-registered keep rule (the round 3 rule): untouched cells only
(>= 91 without --descriptive). Per horizon with >= 30 rows over >= 5
tickers and >= 2 cutoffs, RangeSkill (vs naive) cutoff-clustered 95%
CI lower bound > 0 and coverage 0.75-0.85. KEEP on every horizon,
REJECT when the sample is enough and either fails, INSUFFICIENT
otherwise. One scoring, no refit. Nothing edits scripts/ensemble.py.

Usage:
  python3 benchmarks/replay_aci_conformal.py diag --captures DIR ...
      (target cells 1-47, descriptive, no verdict)
  python3 benchmarks/replay_aci_conformal.py score --captures DIR ...
      [--min-cell 91] [--descriptive] [--reps 5000] [--json OUT]
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
ALPHA = 0.20
GAMMA = 0.05
ALPHA_MIN, ALPHA_MAX = 0.02, 0.50
MATURITY_DAYS = 35
MIN_HIST = 12
CLEAN_MIN_CELL = 91
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


def conformal_q(scores, alpha):
    n = len(scores)
    if n < MIN_HIST:
        return 1.0
    idx = math.ceil((n + 1) * (1.0 - alpha))
    srt = sorted(scores)
    return srt[min(idx, n) - 1]


def _eligible(hist_rows, target_date):
    cut = target_date - dt.timedelta(days=MATURITY_DAYS)
    return [r for r in hist_rows if _date(r["as_of"]) <= cut
            and score_of(r) is not None]


def _alpha_step(alpha, err):
    return min(ALPHA_MAX, max(ALPHA_MIN, alpha + GAMMA * (ALPHA - err)))


def _feedback(hist_rows, upto):
    """[(cutoff date, err)] for every cutoff P <= upto - MATURITY_DAYS,
    in date order. err_P is the share of P's rows NOT covered by the
    band q_P x half_v2 that was used at P, where q_P comes from the
    scores eligible at P and the alpha known at P (alpha_known). Each
    err_P only matures at P + MATURITY_DAYS (the month horizon is up to
    ~29 days), so it is applied to a later cutoff only once that date
    has passed."""
    rows = [r for r in hist_rows if score_of(r) is not None
            and _date(r["as_of"]) <= upto - dt.timedelta(
                days=MATURITY_DAYS)]
    fb = []
    for p in sorted({r["as_of"] for r in rows}):
        dp = _date(p)
        alpha = alpha_known(fb, dp)
        q = conformal_q([score_of(r) for r in _eligible(
            [x for x in rows if x["as_of"] < p], dp)], alpha)
        rows_p = [r for r in rows if r["as_of"] == p]
        err = sum(score_of(r) > q for r in rows_p) / len(rows_p)
        fb.append((dp, err))
    return fb


def alpha_known(feedback, at):
    """ACI level at date `at`: only the errors that have matured by
    then (cutoff + MATURITY_DAYS <= at), applied in date order."""
    alpha = ALPHA
    for dp, err in feedback:
        if dp + dt.timedelta(days=MATURITY_DAYS) <= at:
            alpha = _alpha_step(alpha, err)
    return alpha


def alpha_at(target_asof, hist_rows):
    """ACI level a cutoff would use: feedback matured at that date."""
    t = _date(target_asof)
    return alpha_known(_feedback(hist_rows, t), t)


def q_for(target_asof, hist_rows):
    """(q, alpha) for a target cutoff from the past rows of one
    horizon. Only rows and feedback mature at the target date count."""
    t = _date(target_asof)
    alpha = alpha_at(target_asof, hist_rows)
    elig = _eligible(hist_rows, t)
    return conformal_q([score_of(r) for r in elig], alpha), alpha


def score_rows(rows, target_pred):
    """Pairs for target rows only (target_pred(row) -> bool); the
    history is every row of the same horizon."""
    by_h = {h: [r for r in rows if r["horizon"] == h and r["v2_sigma"]]
            for h in HORIZONS}
    qcache, out = {}, []
    for r in rows:
        if not target_pred(r) or not r["v2_sigma"]:
            continue
        h = r["horizon"]
        key = (h, r["as_of"])
        if key not in qcache:
            qcache[key] = q_for(r["as_of"], by_h[h])
        q, _a = qcache[key]
        v2 = _half_v2(r)
        ch = q * v2
        out.append({"ticker": r["ticker"], "as_of": r["as_of"],
                    "horizon": h, "q": q,
                    "is_naive": R.row_is(r, r["naive_half"]),
                    "is_v2": R.row_is(r, v2), "is_ch": R.row_is(r, ch),
                    "in_v2": abs(r["real"]) <= v2,
                    "in_ch": abs(r["real"]) <= ch})
    return out


def render(res, pairs, descriptive, title):
    L = [title, "ACI over frozen v2: alpha %.2f gamma %.2f, maturity "
         "guard %d d, min history %d" % (ALPHA, GAMMA, MATURITY_DAYS,
                                         MIN_HIST)]
    for h in HORIZONS:
        c = res[h]
        qs = [p["q"] for p in pairs if p["horizon"] == h]
        L.append("%s: n=%d, %d cutoffs, %d tickers, q range [%s, %s]"
                 % (h, c["n"], c["cutoffs"], c["tickers"],
                    _f(min(qs)) if qs else "n/a",
                    _f(max(qs)) if qs else "n/a"))
        L.append("  ACI coverage %s  RangeSkill %s  CI cutoff [%s, %s]  "
                 "CI ticker [%s, %s]"
                 % (_f(c["ch"]["coverage"]), _f(c["ch"]["range_skill"]),
                    _f(c["ch_ci_cutoff"][0]), _f(c["ch_ci_cutoff"][1]),
                    _f(c["ch_ci_ticker"][0]), _f(c["ch_ci_ticker"][1])))
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
    allc = A.find_captures(a.captures, None)
    rows, gaps = R.build_rows(allc, allc)
    if a.mode == "diag":
        pairs = score_rows(rows, lambda r: r["cell"] is not None
                        and r["cell"] <= a.max_cell)
        res = R.evaluate(pairs, a.reps)
        print(render(res, pairs, True, "TARGET CELLS 1-%d, descriptive "
                     "only (walk-forward history from all earlier "
                     "cutoffs)" % a.max_cell))
        return 0
    pairs = score_rows(rows, lambda r: r["cell"] is not None
                        and r["cell"] >= a.min_cell)
    res = R.evaluate(pairs, a.reps, a.seed)
    print(render(res, pairs, a.descriptive,
                 "DESCRIPTIVE ONLY, no verdict valid" if a.descriptive
                 else "CLEAN SCORING, target cells >= %d" % a.min_cell))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump({"alpha": ALPHA, "gamma": GAMMA, "results": res,
                       **({} if a.descriptive else {"verdict": keep_verdict(res)[0]}),
                       "descriptive": a.descriptive}, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
