#!/usr/bin/env python3
"""Shadow challenger: residual-bootstrap predictive band (round 61).

Round 61 task (Moos, Slack 1795777254.742129, relayed; panel-33 idea
3). Distinct from the #806 audit (benchmarks/ci_audit_residual_
bootstrap.py), which regenerates untouched-cell returns as a
diagnostic: this one builds a BAND from training residuals and scores
it on the real untouched rows.
  scale_v2 = v2 sigma60 x sqrt(sessions_h) x RISK_MULT x 100 (pp)
  z        = realised move / scale_v2, per TRAINING row (v2 centre 0,
             so the residual is already centred on the frozen v2
             centre)
  q_h      = mean over --draws replicates of the LEVEL-quantile of |z|,
             each replicate drawing the training cutoff clusters of
             horizon h (all tickers at one as_of) whole, with
             replacement; residuals are never drawn individually
  half     = q_h x scale_v2 (centre 0, symmetric)
LEVEL = 0.80 (the nominal coverage the v2 k table targets). The v2 k
table is only used for the frozen v2 comparison. The residuals come
from TRAINING cells 1-47 only (--fit-max-cell, never above 47 and
exactly 47 for a clean run); no cell above it enters q_h, and the
fit's price reference comes from the training captures only (the #914/
#915 pattern). A horizon with fewer than MIN_TRAIN_CLUSTERS training
clusters has no q_h: its rows keep the v2 half-width and are counted.
The JSON records the effective fit window and price-reference
provenance. Nothing edits scripts/ensemble.py, no Kronos, no external
source.

Pre-registered keep rule (loop bar), one scoring, per horizon:
(1) RangeSkill CI lower bound (cutoff-clustered by as_of) > 0 and
(2) the cutoff-clustered coverage CI overlaps [0.75, 0.85] with width
<= 0.15, on all horizons, untouched cells only (>= 91). KEEP needs
>= 10 cutoff clusters, >= 30 rows and >= 5 tickers per horizon;
REJECT when the sample is enough and a leg fails; INSUFFICIENT
otherwise. Cells 48-90 are scored only with --descriptive, which
prints no verdict word and writes no verdict key.

Usage:
  python3 benchmarks/replay_resid_bootstrap_band.py score --captures
      DIR ... [--min-cell 91] [--max-cell N] [--descriptive]
      [--draws 1000] [--reps 5000] [--json OUT]
  python3 benchmarks/replay_resid_bootstrap_band.py diag --captures
      DIR ...
"""
import argparse
import json
import math
import os
import random
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import replay_band_candidates as R  # noqa: E402
import replay_parkinson_width as PK  # noqa: E402
import score_adoption_594 as A  # noqa: E402
import ensemble as ens_mod  # noqa: E402

HORIZONS = A.HORIZONS
LEVEL = 0.80
DRAWS = 1000
MIN_TRAIN_CLUSTERS = 2
MIN_KEEP_CLUSTERS = 10
FIT_MAX_CELL = 47
CLEAN_MIN_CELL = 91
FIT_SEED = 20261127


def scale_pp(r):
    return R.half_pct(r["v2_sigma"], r["horizon"], 1.0, r["mult"])


def usable(r):
    return bool(r["v2_sigma"]) and r["v2_sigma"] > 0 \
        and r.get("real") is not None


def clusters(rows, h):
    """{as_of: [|z|, ...]} for horizon h, one list per cutoff."""
    out = {}
    for r in rows:
        if r["horizon"] == h and usable(r):
            out.setdefault(r["as_of"], []).append(
                abs(r["real"]) / scale_pp(r))
    return out


def quantile(vals, q):
    """Nearest-rank quantile, q in (0, 1]."""
    s = sorted(vals)
    return s[max(0, int(-(-q * len(s) // 1)) - 1)]


def fit_q(rows, draws=DRAWS, seed=FIT_SEED):
    """({horizon: q or None}, {horizon: training clusters}) from the
    training rows only."""
    q, n = {}, {}
    for h in HORIZONS:
        cl = clusters(rows, h)
        keys = sorted(cl)
        n[h] = len(keys)
        if len(keys) < MIN_TRAIN_CLUSTERS:
            q[h] = None
            continue
        rng = random.Random("%s-%s" % (seed, h))
        qs = []
        for _ in range(draws):
            pool = []
            for _k in keys:
                pool.extend(cl[rng.choice(keys)])
            qs.append(quantile(pool, LEVEL))
        q[h] = sum(qs) / len(qs)
    return q, n


def score_rows(rows, q):
    out = []
    for r in rows:
        if not usable(r):
            continue
        h = r["horizon"]
        sc = scale_pp(r)
        v2 = R.half_pct(r["v2_sigma"], h, ens_mod.V2_BAND_K[h],
                        r["mult"])
        ch = v2 if q.get(h) is None else q[h] * sc
        out.append({"ticker": r["ticker"], "as_of": r["as_of"],
                    "horizon": h,
                    "is_naive": R.row_is(r, r["naive_half"]),
                    "is_v2": R.row_is(r, v2), "is_ch": R.row_is(r, ch),
                    "in_v2": abs(r["real"]) <= v2,
                    "in_ch": abs(r["real"]) <= ch})
    return out


def unfit_rows(rows, q):
    return sum(1 for r in rows if usable(r) and q.get(r["horizon"])
               is None)


def keep_verdict(res):
    short = [h for h in HORIZONS
             if res[h]["cutoffs"] < MIN_KEEP_CLUSTERS]
    if short:
        return "INSUFFICIENT", [
            "%s cutoffs=%d (need >=%d)" % (h, res[h]["cutoffs"],
                                           MIN_KEEP_CLUSTERS)
            for h in short]
    return PK.keep_verdict(res)


def select_caps(allc, lo, hi):
    out = []
    for c in allc:
        n = A.cell_number(c)
        if n is not None and n >= lo and (hi is None or n <= hi):
            out.append(c)
    return out


def count_gaps(gaps, text):
    return sum(1 for g in gaps if text in g)


def provenance(caps, gaps, source):
    return {"price_reference": source, "captures": len(caps),
            "realised_rebuilt": count_gaps(gaps, "realised window "
                                           "rebuilt"),
            "dropped_no_ohlc_captures": count_gaps(
                gaps, "no usable pre-cutoff OHLC")}


def make_report(res, q, counts, unfit, descriptive, fit_max, prov):
    out = {"level": LEVEL, "q": q, "training_clusters": counts,
           "unfit_rows": unfit, "results": res,
           "descriptive": descriptive,
           "fit_window": {"first_cell": 1, "last_cell": fit_max,
                          "registered_last_cell": FIT_MAX_CELL},
           "provenance": prov}
    if not descriptive:
        out["verdict"] = keep_verdict(res)[0]
    return out


def _f(v, nd=3):
    return PK._f(v, nd)


def render(res, q, counts, unfit, descriptive, title,
           fit_max=FIT_MAX_CELL):
    L = [title, "residual-bootstrap band, level %.2f, centre = v2 (0)"
         % LEVEL,
         "fit (training cells <= %d only): q %s (training clusters %s)"
         % (fit_max, " ".join("%s %s" % (h, _f(q[h])) for h in HORIZONS),
            "/".join(str(counts[h]) for h in HORIZONS)),
         "rows without a fitted q (v2 half-width kept): %d" % unfit]
    for h in HORIZONS:
        c = res[h]
        L.append("%s: n=%d, %d cutoffs, %d tickers"
                 % (h, c["n"], c["cutoffs"], c["tickers"]))
        L.append("  challenger coverage %s  RangeSkill %s  CI cutoff "
                 "[%s, %s]  CI ticker [%s, %s]"
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


def _run(a, lo, hi, descriptive, title):
    allc = A.find_captures(a.captures, None)
    train_caps = select_caps(allc, 1, a.fit_max_cell)
    # The fit sees outcomes only through training captures: its price
    # reference is selected from the training captures, never from the
    # held-out ones.
    train, train_gaps = R.build_rows(train_caps, train_caps)
    if not [r for r in train if usable(r)]:
        print("refusing: no training rows (cells 1-%d)" % a.fit_max_cell)
        return 2, None
    q, counts = fit_q(train, getattr(a, "draws", DRAWS))
    score_caps = select_caps(allc, lo, hi)
    rows, gaps = R.build_rows(score_caps, allc)
    pairs = score_rows(rows, q)
    unfit = unfit_rows(rows, q)
    res = R.evaluate(pairs, a.reps, getattr(a, "seed", A.DEFAULT_SEED))
    prov = {"fit": provenance(
                train_caps, train_gaps,
                "training captures only (cells 1-%d)" % a.fit_max_cell),
            "scored": provenance(
                score_caps, gaps,
                "all --captures dirs, latest last date per ticker")}
    print(render(res, q, counts, unfit, descriptive, title,
                 a.fit_max_cell))
    return 0, make_report(res, q, counts, unfit, descriptive,
                          a.fit_max_cell, prov)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.
                                 RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="mode", required=True)
    d = sub.add_parser("diag")
    d.add_argument("--captures", nargs="+", required=True)
    d.add_argument("--fit-max-cell", type=int, default=FIT_MAX_CELL)
    d.add_argument("--draws", type=int, default=DRAWS)
    d.add_argument("--reps", type=int, default=A.DEFAULT_REPS)
    s = sub.add_parser("score")
    s.add_argument("--captures", nargs="+", required=True)
    s.add_argument("--min-cell", type=int, default=CLEAN_MIN_CELL)
    s.add_argument("--max-cell", type=int, default=None)
    s.add_argument("--fit-max-cell", type=int, default=FIT_MAX_CELL)
    s.add_argument("--descriptive", action="store_true")
    s.add_argument("--draws", type=int, default=DRAWS)
    s.add_argument("--reps", type=int, default=A.DEFAULT_REPS)
    s.add_argument("--seed", type=int, default=A.DEFAULT_SEED)
    s.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    if a.fit_max_cell > FIT_MAX_CELL:
        print("refusing: --fit-max-cell above the registered %d"
              % FIT_MAX_CELL)
        return 2
    if a.mode == "diag":
        rc, _o = _run(a, 1, a.fit_max_cell, True,
                      "FIT CELLS 1-%d, descriptive only" % a.fit_max_cell)
        return rc
    if a.min_cell < CLEAN_MIN_CELL and not a.descriptive:
        print("refusing: cells below %d need --descriptive"
              % CLEAN_MIN_CELL)
        return 2
    if not a.descriptive and a.fit_max_cell != FIT_MAX_CELL:
        print("refusing: clean scoring needs --fit-max-cell %d"
              % FIT_MAX_CELL)
        return 2
    if a.min_cell <= a.fit_max_cell:
        print("refusing: scored cells overlap the training cells (<= %d)"
              % a.fit_max_cell)
        return 2
    rc, out = _run(a, a.min_cell, a.max_cell, a.descriptive,
                   "DESCRIPTIVE ONLY" if a.descriptive
                   else "CLEAN SCORING, cells >= %d" % a.min_cell)
    if rc == 0 and a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=1)
    return rc


if __name__ == "__main__":
    sys.exit(main())
