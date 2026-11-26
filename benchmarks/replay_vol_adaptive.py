#!/usr/bin/env python3
"""Shadow challenger: volatility-adaptive band width.

INS-IMPROVE-001 round 3, experiment 1 (target T2).

Band: centre 0, half = k_h x sigma_eff x sqrt(sessions_h) x RISK_MULT
with
  sigma_eff = sigma60 x (1 + EPS x (sigma_long / sigma60 - 1)),  EPS = 0.20.
EPS is fixed by the brief and is NOT fitted. Only the k table is
fitted, per horizon, on training cells (1-47) by minimising mean
Winkler interval score over the fit rows, as P2/P3 did
(benchmarks/replay_band_candidates.py, which this imports).

Definitions chosen here (the brief did not fix them, so they are
stated for review):
  sigma60      stdev of the last 60 daily log returns (the v2
               estimator, recomputed from the capture's own
               pre-cutoff OHLC history, nothing after the base date).
  sigma_long   stdev of the last 250 daily log returns from the same
               history (collected/pandas-ta/indicators.csv carries 251
               closes, so 250 returns); None when fewer than 200.
Control for reference: the same fit with EPS = 0 (plain sigma60).
Frozen v2 (scripts/ensemble.py V2_BAND_K) is untouched and is the
comparison column.

Pre-registered keep rule (written by Ins before any untouched cell was
scored; the RangeSkill and coverage conditions are Moos's round 3
brief, the minimum-sample conditions are the #751 ones). Untouched
cells only (cell >= 73). KEEP when, on EVERY horizon, with at least
30 rows over at least 5 tickers and at least 2 cutoffs,
  (1) RangeSkill vs naive has a cutoff-clustered 95% CI lower bound
      > 0, and
  (2) the cutoff-clustered coverage CI overlaps [0.75, 0.85] (round 11
      ruling by Moos; the original wording was point coverage within
      0.75-0.85), same clustering and draws as the RangeSkill CI.
REJECT when the sample is enough on every horizon and either fails
anywhere. INSUFFICIENT when any horizon lacks the sample. One scoring
of the frozen file, no re-fit on scored cells. Cells 48-72 give
descriptive output only (--descriptive). Nothing here edits
scripts/ensemble.py.

Disclosure: before this PR was opened a descriptive run on all cells >= 48
(n = 31 per horizon) included cells 73-78, so those six rows were seen
for this challenger. A valid keep/reject needs cells not in 1-78, i.e.
the batch D/E cells (91-102) once they land.

Usage:
  python3 benchmarks/replay_vol_adaptive.py fit --captures DIR ...
      [--max-cell 47] --out frozen.json
  python3 benchmarks/replay_vol_adaptive.py score --frozen frozen.json
      --captures DIR ... [--min-cell 73] [--descriptive]
      [--reps 5000] [--json OUT]
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
import backtest_score as bs  # noqa: E402

HORIZONS = A.HORIZONS
EPS = 0.20
LONG_N = 250
LONG_MIN = 200
MIN_ROWS, MIN_TICKERS, MIN_CUTOFFS = 30, 5, 2
COV_BAND = (0.75, 0.85)


def sigma_long(closes):
    """Stdev of the last LONG_N log returns; None under LONG_MIN."""
    rets = R._logrets([c for c in closes if c > 0])[-LONG_N:]
    return R._sd(rets) if len(rets) >= LONG_MIN else None


def sigma_eff(s60, s_long, eps=EPS):
    if not s60 or s_long is None:
        return None
    return s60 * (1.0 + eps * (s_long / s60 - 1.0))


def build_rows(capture_dirs, ref_dirs):
    """R.build_rows rows, each with sigma_long and sigma_eff added."""
    out, gaps = [], []
    for cap in capture_dirs:
        rows, g = R.build_rows([cap], ref_dirs)
        gaps.extend(g)
        ens = bs.load_json(os.path.join(cap, "digest", "ensemble.json"))
        bars = R.read_ohlc(cap, str((ens or {}).get("base_date")
                                    or "")[:10])
        sl = sigma_long([c for _, _, _, c in bars])
        for r in rows:
            r["sigma_long"] = sl
            r["sigma_eff"] = sigma_eff(r["sig"].get("s60"), sl)
            out.append(r)
    return out, gaps


def _fit_rows(rows):
    return [r for r in rows if r.get("sigma_eff")]


def fit_k(rows, horizon, key):
    """Grid k minimising mean IS with sigma = row[key]."""
    hp = [r for r in rows if r["horizon"] == horizon and r.get(key)]
    if not hp:
        return None
    best, best_k = None, None
    for k in R.K_GRID:
        m = sum(R.row_is(r, R.half_pct(r[key], horizon, k, r["mult"]))
                for r in hp) / len(hp)
        if best is None or m < best - 1e-12:
            best, best_k = m, k
    return best_k


def loco_cv(rows, key):
    """Leave-one-cutoff-out CV ratio (mean IS / naive mean IS) per
    horizon; None when a horizon has < 2 cutoffs."""
    out = {}
    for h in HORIZONS:
        hp = [r for r in rows if r["horizon"] == h and r.get(key)]
        cuts = sorted({r["as_of"] for r in hp})
        if len(cuts) < 2:
            out[h] = None
            continue
        tot = naive = 0.0
        for c in cuts:
            k = fit_k([r for r in hp if r["as_of"] != c], h, key)
            for r in hp:
                if r["as_of"] == c:
                    tot += R.row_is(r, R.half_pct(r[key], h, k,
                                                  r["mult"]))
                    naive += R.row_is(r, r["naive_half"])
        out[h] = tot / naive if naive > 0 else None
    return out


def fit(rows):
    rows = _fit_rows(rows)
    for r in rows:
        r["s60_plain"] = r["sig"]["s60"]
    cells = sorted({r["cell"] for r in rows if r["cell"] is not None})
    return {"eps": EPS, "long_n": LONG_N,
            "k": {h: fit_k(rows, h, "sigma_eff") for h in HORIZONS},
            "cv_ratio_adaptive": loco_cv(rows, "sigma_eff"),
            "cv_ratio_control_s60": loco_cv(rows, "s60_plain"),
            "k_control_s60": {h: fit_k(rows, h, "s60_plain")
                              for h in HORIZONS},
            "fit_rows": len(rows),
            "fit_cells": [cells[0], cells[-1]] if cells else None}


def score_rows(rows, frozen):
    out = []
    for r in rows:
        s = r.get("sigma_eff")
        if not s or not r["v2_sigma"]:
            continue
        h = r["horizon"]
        ch = R.half_pct(s, h, frozen["k"][h], r["mult"])
        v2 = R.half_pct(r["v2_sigma"], h, ens_mod.V2_BAND_K[h],
                        r["mult"])
        out.append({"ticker": r["ticker"], "as_of": r["as_of"],
                    "horizon": h,
                    "is_naive": R.row_is(r, r["naive_half"]),
                    "is_v2": R.row_is(r, v2), "is_ch": R.row_is(r, ch),
                    "in_v2": abs(r["real"]) <= v2,
                    "in_ch": abs(r["real"]) <= ch})
    return out


def keep_verdict(res):
    """Pre-registered rule (module doc): (verdict, reasons)."""
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
        c = res[h]
        lo = c["ch_ci_cutoff"][0]
        cov = c["ch"]["coverage"]
        if lo is None or lo <= 0:
            bad.append("%s CI lower bound %s not > 0" % (h, _f(lo)))
        if not R.coverage_ci_ok(c["ch_cov_ci_cutoff"], COV_BAND):
            bad.append(R.coverage_ci_reason(h, c["ch_cov_ci_cutoff"], cov,
                                            COV_BAND))
    return ("REJECT" if bad else "KEEP"), bad


def _f(v, nd=3):
    return "n/a" if v is None else ("%.*f" % (nd, v))


def render_fit(fz):
    L = ["Vol-adaptive band fit: EPS %.2f (fixed), fit rows %d, cells %s"
         % (fz["eps"], fz["fit_rows"], fz["fit_cells"]),
         "k (adaptive): %s" % json.dumps(fz["k"]),
         "k (control s60): %s" % json.dumps(fz["k_control_s60"]),
         "LOCO-CV IS/naive adaptive: %s" % json.dumps(
             {h: _f(v) for h, v in fz["cv_ratio_adaptive"].items()}),
         "LOCO-CV IS/naive control : %s" % json.dumps(
             {h: _f(v) for h, v in fz["cv_ratio_control_s60"].items()})]
    return "\n".join(L)


def render_score(res, fz, descriptive):
    L = []
    if descriptive:
        L += ["DESCRIPTIVE ONLY: these cells were seen before the "
              "challenger was frozen. No keep/reject is valid.", ""]
    L.append("Vol-adaptive k %s EPS %.2f vs frozen v2"
             % (json.dumps(fz["k"]), fz["eps"]))
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
    v, why = keep_verdict(res)
    L += ["", "KEEP RULE: %s%s" % (
        v, "" if descriptive else (" (" + "; ".join(why) + ")"
                                   if why else ""))]
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.
                                 RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="mode", required=True)
    f = sub.add_parser("fit")
    f.add_argument("--captures", nargs="+", required=True)
    f.add_argument("--max-cell", type=int, default=47)
    f.add_argument("--out", required=True)
    s = sub.add_parser("score")
    s.add_argument("--frozen", required=True)
    s.add_argument("--captures", nargs="+", required=True)
    s.add_argument("--min-cell", type=int, default=73)
    s.add_argument("--descriptive", action="store_true")
    s.add_argument("--reps", type=int, default=A.DEFAULT_REPS)
    s.add_argument("--seed", type=int, default=A.DEFAULT_SEED)
    s.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    allc = A.find_captures(a.captures, None)
    if a.mode == "fit":
        caps = [c for c in allc if (A.cell_number(c) or 0) <= a.max_cell]
        rows, gaps = build_rows(caps, allc)
        fz = fit(rows)
        print(render_fit(fz))
        for g in gaps:
            print("gap: " + g)
        with open(a.out, "w", encoding="utf-8") as fh:
            json.dump({"frozen": fz}, fh, indent=1)
        return 0
    if a.min_cell < 73 and not a.descriptive:
        print("refusing: cells below 73 were seen; pass --descriptive")
        return 2
    with open(a.frozen, encoding="utf-8") as fh:
        fz = json.load(fh)["frozen"]
    caps = A.find_captures(a.captures, a.min_cell)
    rows, gaps = build_rows(caps, allc)
    res = R.evaluate(score_rows(rows, fz), a.reps, a.seed)
    print(render_score(res, fz, a.descriptive))
    for g in gaps:
        print("gap: " + g)
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump({"frozen": fz, "results": res,
                       "verdict": keep_verdict(res)[0],
                       "descriptive": a.descriptive}, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
