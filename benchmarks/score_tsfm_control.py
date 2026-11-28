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

Keep rule (round 93, docs/round93_chronos2_prereg.md): the loop bar in
benchmarks/loop_bar.py on cells >= 91 only, origins strictly after
2025-10-20 only. Fewer than 10 cutoff clusters on any horizon prints COUNTS
ONLY and no coverage, skill or CI. `describe` is limited to cells 48-90.
A KEEP would not authorise adoption: it would only justify a forward-ledger
test. Kronos stays excluded. Captures missing the file are counted and
listed.

Disclosure: Chronos-2's model card lists its training data as subsets
of the Chronos Datasets and GIFT-Eval Pretrain plus synthetic data. It
gives no statement about EGX tickers or about 2023-2026 windows.
TimesFM was not checked by Ins.

Usage:
  python3 benchmarks/score_tsfm_control.py describe --captures DIR ... 
      [--centre zero|q50] [--min-cell 48 --max-cell 90] [--reps 5000]
  python3 benchmarks/score_tsfm_control.py score --captures DIR ...
      [--centre zero|q50] [--min-cell 91] [--reps 5000] [--json OUT]
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
TRAIN_MAX_CELL = 47
DESC_MAX_CELL = 90
MIN_ORIGIN = "2025-10-20"
import loop_bar  # noqa: E402
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


def build_rows(capture_dirs, ref_dirs, model, centre="zero"):
    """Rows with the TSFM band. centre "zero" is the nominal arm
    (centre 0), "q50" the second arm (centre = the model's q50,
    same half-width). Captures without usable quantiles (for the q50
    arm: q50 outside [q10, q90] too) are excluded and listed."""
    out, gaps = [], []
    for cap in capture_dirs:
        rows, g = R.build_rows([cap], ref_dirs)
        gaps.extend(g)
        qd = load_quantiles(cap, model)
        if qd is not None and centre == "q50":
            hz = qd["horizons"]
            if not all(isinstance(hz[h].get("q50"), (int, float))
                       and hz[h]["q10"] <= hz[h]["q50"] <= hz[h]["q90"]
                       for h in HORIZONS):
                qd = None
        if qd is None:
            gaps.append("%s: no usable %s quantiles for the %s arm, excluded"
                        % (cap, model, centre))
            continue
        for r in rows:
            q = qd["horizons"][r["horizon"]]
            r["tsfm_half"] = band_half(q, r["mult"])
            r["tsfm_centre"] = q["q50"] * r["mult"] if centre == "q50" else 0.0
            out.append(r)
    return out, gaps


def score_rows(rows):
    out = []
    for r in rows:
        ch = r.get("tsfm_half")
        if not ch or not r["v2_sigma"]:
            continue
        h = r["horizon"]
        c0 = r.get("tsfm_centre", 0.0)
        v2 = R.half_pct(r["v2_sigma"], h, ens_mod.V2_BAND_K[h],
                        r["mult"])
        out.append({"ticker": r["ticker"], "as_of": r["as_of"],
                    "horizon": h,
                    "is_naive": R.row_is(r, r["naive_half"]),
                    "is_v2": R.row_is(r, v2),
                    "is_ch": bs.winkler_is(r["real"], c0 - ch, c0 + ch),
                    "in_v2": abs(r["real"]) <= v2,
                    "in_ch": abs(r["real"] - c0) <= ch})
    return out


def row_id(r):
    return "%s %s %s" % (r.get("ticker"), str(r.get("as_of"))[:10],
                         r.get("horizon"))


def origin_filter(rows, min_origin):
    """Keep rows whose origin is strictly after min_origin; return the
    kept rows and one exclusion line per dropped row."""
    keep, lines = [], []
    for r in rows:
        if str(r["as_of"])[:10] > min_origin:
            keep.append(r)
        else:
            lines.append("excluded: row %s: origin not after %s "
                         "(possible pretraining overlap)"
                         % (row_id(r), min_origin))
    return keep, lines


def exclusion_lines(gaps, origin_lines, unnumbered):
    drops = [g for g in gaps if "excluded" in g]
    notes = [g for g in gaps if "excluded" not in g]
    L = ["EXCLUDED: %d capture(s) without usable quantiles or dropped by "
         "build_rows, %d row(s) before the origin rule, %d unnumbered "
         "capture(s) never scored; %d note(s)"
         % (len(drops), len(origin_lines), len(unnumbered), len(notes))]
    L.extend("excluded: %s" % g for g in drops)
    L.extend(origin_lines)
    L.extend("excluded: capture %s: no cell number, never scored" % x
             for x in unnumbered)
    L.extend("note: %s" % g for g in notes)
    return L


def count_lines(rows):
    """Counts of the rows that enter a scoring, per horizon."""
    L = []
    for h in HORIZONS:
        hr = [r for r in rows if r["horizon"] == h]
        L.append("%s: rows=%d cutoff clusters=%d tickers=%d" % (
            h, len(hr), len({r["as_of"] for r in hr}),
            len({r["ticker"] for r in hr})))
    return L


def render(res, model, centre, title):
    L = [title, "%s zero-shot quantile band, half = (q90 - q10)/2, centre "
         "%s, control arm" % (model, "0" if centre == "zero" else "q50")]
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
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.
                                 RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="mode", required=True)
    for name in ("describe", "score"):
        s = sub.add_parser(name)
        s.add_argument("--model", default="chronos-2")
        s.add_argument("--centre", choices=("zero", "q50"), default="zero")
        s.add_argument("--captures", nargs="+", required=True)
        s.add_argument("--min-origin", default=MIN_ORIGIN)
        s.add_argument("--reps", type=int, default=A.DEFAULT_REPS)
        s.add_argument("--seed", type=int, default=A.DEFAULT_SEED)
        s.add_argument("--json", default=None)
        if name == "describe":
            s.add_argument("--min-cell", type=int, default=TRAIN_MAX_CELL + 1)
            s.add_argument("--max-cell", type=int, default=DESC_MAX_CELL)
        else:
            s.add_argument("--min-cell", type=int, default=CLEAN_MIN_CELL)
    a = ap.parse_args(argv)
    if a.mode == "describe" and not (
            TRAIN_MAX_CELL < a.min_cell <= a.max_cell <= DESC_MAX_CELL):
        print("refusing: describe needs %d <= min-cell <= max-cell <= %d "
              "(cells %d+ go through score)" % (
                  TRAIN_MAX_CELL + 1, DESC_MAX_CELL, CLEAN_MIN_CELL))
        return 2
    if a.mode == "score" and a.min_cell < CLEAN_MIN_CELL:
        print("refusing: score is for cells >= %d only" % CLEAN_MIN_CELL)
        return 2
    if a.min_origin < MIN_ORIGIN:
        print("refusing: min-origin cannot be before %s" % MIN_ORIGIN)
        return 2
    allc = A.find_captures(a.captures, None)
    unnumbered = [c for c in allc if A.cell_number(c) is None]
    hi = a.max_cell if a.mode == "describe" else 10 ** 9
    caps = [c for c in allc if A.cell_number(c) is not None
            and a.min_cell <= A.cell_number(c) <= hi]
    rows, gaps = build_rows(caps, allc, a.model, a.centre)
    rows, olines = origin_filter(rows, a.min_origin)
    ex = exclusion_lines(gaps, olines, unnumbered)
    counts = count_lines(rows)
    res = R.evaluate(score_rows(rows), a.reps, a.seed)
    if a.mode == "describe":
        print("COUNTS (printed before the descriptive read), cells %d-%d, "
              "origin after %s, centre %s" % (a.min_cell, a.max_cell,
                                              a.min_origin, a.centre))
        print("\n".join(counts))
        print(render(res, a.model, a.centre,
                     "DESCRIPTIVE ONLY cells %d-%d, no verdict" % (
                         a.min_cell, a.max_cell)))
        print("\n".join(ex))
        if a.json:
            with open(a.json, "w", encoding="utf-8") as fh:
                json.dump({"model": a.model, "centre": a.centre,
                           "descriptive": True, "counts": counts,
                           "results": res, "excluded": ex}, fh, indent=1)
        return 0
    v, why = loop_bar.loop_bar_verdict(res)
    if v == "COUNTS ONLY":
        # Fewer than MIN_CLUSTERS cutoff clusters: counts and reasons
        # only. No coverage, skill or CI is printed or written.
        print("CLEAN SCORING, cells >= %d: COUNTS ONLY" % a.min_cell)
        print("\n".join(counts))
        print("\n".join("reason: " + w for w in why))
        print("\n".join(ex))
        if a.json:
            with open(a.json, "w", encoding="utf-8") as fh:
                json.dump({"model": a.model, "centre": a.centre,
                           "verdict": v, "counts": counts, "reasons": why,
                           "excluded": ex}, fh, indent=1)
        return 0
    print(render(res, a.model, a.centre,
                 "CLEAN SCORING, cells >= %d" % a.min_cell))
    print("KEEP RULE: %s%s" % (v, " (" + "; ".join(why) + ")" if why else ""))
    print("\n".join(counts))
    print("\n".join(ex))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump({"model": a.model, "centre": a.centre, "verdict": v,
                       "results": res, "counts": counts, "excluded": ex,
                       "descriptive": False}, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
