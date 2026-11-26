#!/usr/bin/env python3
"""Scorer and pre-registration for a TSFM control arm (Chronos-2 /
TimesFM zero-shot quantiles).

INS-IMPROVE-006 experiment E (control arm only, never adoptable on
backtest alone). This file fixes the capture format, the band and the
rule BEFORE any quantile capture exists. No model runs here: the
review sandbox has no torch, one CPU and about 1 GB of RAM, so
Chronos-2 (120M parameters, https://huggingface.co/amazon/chronos-2)
inference has to be dispatched by the cycle, like the Kronos runs.

Capture format (one file per capture, written by the dispatch step,
LLM-free):
  <capture>/collected/<model>/quantiles.json
  {"model": "chronos-2", "base_date": "YYYY-MM-DD",
   "context_sessions": N,            # closes supplied, all <= base_date
   "horizons": {"day":   {"q10": x, "q50": y, "q90": z},
                "week":  {...}, "month": {...}}}
Values are the cumulative return in PERCENT over 1 / 5 / 21 sessions
from the base close, taken from the model's own quantile outputs at
levels 0.10 / 0.50 / 0.90. The context is the capture's own price.csv
closes dated <= base_date (no covariates, no index, no news).

Band (nominal, nothing fitted): centre 0 like v2, so only the width
is tested,
  half = (q90 - q10) / 2 x RISK_MULT.
Frozen v2 stays the comparison column and is untouched. No recal-
ibration arm is pre-registered here: any recalibration (isotonic or
conformal) must be its own pre-registered item with fit on cells
1-47, so the control stays a clean zero-shot reading.

Pre-registered keep rule (the round 3 / #764 rule): untouched cells
only (>= 91 without --descriptive). Per horizon with >= 30 rows over
>= 5 tickers and >= 2 cutoffs, RangeSkill (vs naive) cutoff-clustered
95% CI lower bound > 0 and coverage 0.75-0.85; KEEP on every horizon,
REJECT when the sample is enough and either fails, INSUFFICIENT
otherwise. One scoring. Because the arm is a control and pretraining
corpora are not documented to exclude EGX or the test window, a KEEP
would not authorise adoption: it would only justify a forward-ledger
test. Kronos stays excluded. Captures missing the file are counted
and excluded.

Disclosure: Chronos-2's model card lists its training data as subsets
of the Chronos Datasets and GIFT-Eval Pretrain plus synthetic data. It
gives no statement about EGX tickers or about 2023-2026 windows.
TimesFM was not checked by Ins.

Usage:
  python3 benchmarks/score_tsfm_control.py score --model chronos-2
      --captures DIR ... [--min-cell 91] [--descriptive]
      [--reps 5000] [--json OUT]
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
import replay_band_candidates as R  # noqa: E402
import replay_vol_adaptive as V  # noqa: E402
import score_adoption_594 as A  # noqa: E402
import ensemble as ens_mod  # noqa: E402
import backtest_score as bs  # noqa: E402

HORIZONS = A.HORIZONS
CLEAN_MIN_CELL = 91
keep_verdict = V.keep_verdict
_f = V._f


def load_quantiles(capture, model):
    """horizons dict from quantiles.json, or None when absent or
    malformed (including q90 <= q10)."""
    path = os.path.join(capture, "collected", model, "quantiles.json")
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        hz = d["horizons"]
        for h in HORIZONS:
            if not hz[h]["q90"] > hz[h]["q10"]:
                return None
        return d
    except (OSError, ValueError, KeyError, TypeError):
        return None


def band_half(q, mult=1.0):
    """Centre-0 half-width in percent from q10/q90."""
    return (q["q90"] - q["q10"]) / 2.0 * mult


def build_rows(capture_dirs, ref_dirs, model):
    out, gaps = [], []
    for cap in capture_dirs:
        rows, g = R.build_rows([cap], ref_dirs)
        gaps.extend(g)
        qd = load_quantiles(cap, model)
        if qd is None:
            gaps.append("%s: no usable %s quantiles, excluded"
                        % (cap, model))
            continue
        for r in rows:
            r["tsfm_half"] = band_half(qd["horizons"][r["horizon"]],
                                       r["mult"])
            out.append(r)
    return out, gaps


def score_rows(rows):
    out = []
    for r in rows:
        ch = r.get("tsfm_half")
        if not ch or not r["v2_sigma"]:
            continue
        h = r["horizon"]
        v2 = R.half_pct(r["v2_sigma"], h, ens_mod.V2_BAND_K[h],
                        r["mult"])
        out.append({"ticker": r["ticker"], "as_of": r["as_of"],
                    "horizon": h,
                    "is_naive": R.row_is(r, r["naive_half"]),
                    "is_v2": R.row_is(r, v2), "is_ch": R.row_is(r, ch),
                    "in_v2": abs(r["real"]) <= v2,
                    "in_ch": abs(r["real"]) <= ch})
    return out


def render(res, model, descriptive, title):
    L = [title, "%s zero-shot quantile band, (q90 - q10)/2 centred at "
         "0, control arm" % model]
    for h in HORIZONS:
        c = res[h]
        L.append("%s: n=%d, %d cutoffs, %d tickers"
                 % (h, c["n"], c["cutoffs"], c["tickers"]))
        L.append("  coverage %s  RangeSkill %s  CI cutoff [%s, %s]  "
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
    s = sub.add_parser("score")
    s.add_argument("--model", default="chronos-2")
    s.add_argument("--captures", nargs="+", required=True)
    s.add_argument("--min-cell", type=int, default=CLEAN_MIN_CELL)
    s.add_argument("--descriptive", action="store_true")
    s.add_argument("--reps", type=int, default=A.DEFAULT_REPS)
    s.add_argument("--seed", type=int, default=A.DEFAULT_SEED)
    s.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    if a.min_cell < CLEAN_MIN_CELL and not a.descriptive:
        print("refusing: cells below %d need --descriptive"
              % CLEAN_MIN_CELL)
        return 2
    allc = A.find_captures(a.captures, None)
    caps = A.find_captures(a.captures, a.min_cell)
    rows, gaps = build_rows(caps, allc, a.model)
    res = R.evaluate(score_rows(rows), a.reps, a.seed)
    print(render(res, a.model, a.descriptive,
                 "DESCRIPTIVE ONLY, no verdict valid" if a.descriptive
                 else "CLEAN SCORING, cells >= %d" % a.min_cell))
    print("captures without usable quantiles: %d"
          % sum("excluded" in g for g in gaps))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump({"model": a.model, "results": res,
                       "verdict": keep_verdict(res)[0],
                       "descriptive": a.descriptive}, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
