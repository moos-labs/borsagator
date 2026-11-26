#!/usr/bin/env python3
"""Shadow challenger D: GARCH(1,1) with filtered historical simulation.

INS-IMPROVE-006 experiment D (targets T2, T3). Pre-registration: the
spec and rule below are fixed before any untouched cell is scored.

Band: centre 0, half-width from a simulated cumulative-return
distribution at nominal 0.80 coverage,
  half = (Q90 - Q10) / 2  of the h-session cumulative log return,
h = 1 / 5 / 21 sessions (ledger session counts), in percent. No k is
fitted: the 0.10/0.90 quantiles are the nominal level, so there is
nothing to freeze. RISK_MULT is applied as in v2 (inert today).
Frozen v2 stays the comparison column and is untouched.

Model, per capture (so per ticker and cutoff), stdlib only:
  Data: the capture's own price.csv closes dated <= the base date,
    last 750 daily log returns (>= 400 required, else the row is
    excluded and counted).
  GARCH(1,1) with variance targeting, omega = var x (1 - a - b),
    mean 0, fitted by Gaussian quasi-likelihood on a grid
    a in {0.02..0.30 step 0.02}, b in {0.50..0.98 step 0.02},
    a + b < 0.999. QMLE, so the innovation law is not assumed.
  FHS: standardised residuals z_t = r_t / sigma_t; N_SIM = 2000 paths
    of h steps, each step drawing z from the empirical z with
    replacement and updating the variance recursion; seed fixed
    (SEED = 594). Cumulative path returns give Q10/Q90.
The brief named GARCH-t. The innovation law is bootstrapped (FHS), so
no t density is fitted; this is the standard FHS form. EGARCH is a
named variant and is NOT part of this pre-registration; it needs its
own file if the GARCH arm survives screening.

Pre-registered keep rule (the round 3 / #764 rule): untouched cells
only (>= 91 without --descriptive). Per horizon with >= 30 rows over
>= 5 tickers and >= 2 cutoffs, RangeSkill (vs naive) cutoff-clustered
95% CI lower bound > 0 and coverage 0.75-0.85. KEEP on every
horizon, REJECT when the sample is enough and either fails,
INSUFFICIENT otherwise. One scoring, no refit. Nothing edits
scripts/ensemble.py.

Screening (mode `screen`, descriptive, NEVER a verdict): pseudo-
cutoffs every 21 sessions on each ticker's price.csv closes from the
latest 2023-12-29 capture, with at least 750 sessions of history, and
realised windows that end on or before 2023-12-28. Every capture cell
1-102 has its cutoff on or after 2023-12-29, so no screening window
overlaps a realised window feeding any verdict cell, and no
forward-ledger row is touched. The screen compares the nominal FHS
band against the v2 band (V2_BAND_K x sigma60 x sqrt(h), sigma60
from the same closes) and a naive 1.2816 x sigma60 band on the same
pseudo-windows. Close-only, raw closes (no dividend adjustment), 6
tickers.

Usage:
  python3 benchmarks/replay_garch_fhs.py screen --captures DIR ...
      [--reps 2000] [--json OUT]
  python3 benchmarks/replay_garch_fhs.py score --captures DIR ...
      [--min-cell 91] [--descriptive] [--reps 5000] [--json OUT]
"""
import argparse
import csv
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
import replay_vol_adaptive as V  # noqa: E402
import score_adoption_594 as A  # noqa: E402
import ensemble as ens_mod  # noqa: E402
import backtest_score as bs  # noqa: E402

HORIZONS = A.HORIZONS
N_RET = 750
MIN_RET = 400
N_SIM = 2000
SEED = 594
A_GRID = [round(0.02 * i, 2) for i in range(1, 16)]
B_GRID = [round(0.50 + 0.02 * i, 2) for i in range(25)]
CLEAN_MIN_CELL = 91
keep_verdict = V.keep_verdict
_f = V._f


def read_closes(capture, base_date=None):
    """[(date, close)] from capture/price.csv, dated <= base_date."""
    path = os.path.join(capture, "price.csv")
    out = []
    try:
        with open(path, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                d = str(r.get("date") or "")[:10]
                c = A.fnum(r.get("close"))
                if d and c and c > 0 and (not base_date
                                          or d <= base_date):
                    out.append((d, c))
    except OSError:
        return []
    return out


def logrets(closes):
    return [math.log(closes[i] / closes[i - 1])
            for i in range(1, len(closes))]


def _nll(rets, var0, omega, a, b):
    s2, tot = var0, 0.0
    for r in rets:
        tot += math.log(s2) + r * r / s2
        s2 = omega + a * r * r + b * s2
    return tot


def fit_garch(rets):
    """(omega, a, b) by grid QMLE with variance targeting; None when
    the series is too short or degenerate."""
    if len(rets) < MIN_RET:
        return None
    var = sum(r * r for r in rets) / len(rets)
    if var <= 0:
        return None
    best, best_p = None, None
    for a in A_GRID:
        for b in B_GRID:
            if a + b >= 0.999:
                continue
            omega = var * (1.0 - a - b)
            v = _nll(rets, var, omega, a, b)
            if best is None or v < best:
                best, best_p = v, (omega, a, b)
    return best_p


def fhs_band(rets, h, seed=SEED, n_sim=N_SIM):
    """Half-width in percent from simulated cumulative returns;
    None when the model cannot be fitted."""
    rets = rets[-N_RET:]
    p = fit_garch(rets)
    if p is None:
        return None
    omega, a, b = p
    var = sum(r * r for r in rets) / len(rets)
    s2, z = var, []
    for r in rets:
        z.append(r / math.sqrt(s2))
        s2 = omega + a * r * r + b * s2
    rng = random.Random(seed)
    sims = []
    for _ in range(n_sim):
        v, cum = s2, 0.0
        for _s in range(h):
            e = rng.choice(z) * math.sqrt(v)
            cum += e
            v = omega + a * e * e + b * v
        sims.append(cum)
    sims.sort()
    q10 = sims[int(0.10 * n_sim)]
    q90 = sims[int(0.90 * n_sim) - 1]
    return (math.exp(q90) - math.exp(q10)) / 2.0 * 100.0


def build_rows(capture_dirs, ref_dirs):
    out, gaps = [], []
    for cap in capture_dirs:
        rows, g = R.build_rows([cap], ref_dirs)
        gaps.extend(g)
        ens = bs.load_json(os.path.join(cap, "digest", "ensemble.json"))
        bd = str((ens or {}).get("base_date") or "")[:10]
        rets = logrets([c for _, c in read_closes(cap, bd)])
        cache = {}
        for r in rows:
            h = r["horizon"]
            if h not in cache:
                cache[h] = fhs_band(rets, R.SESSIONS[h])
            r["fhs_half"] = (cache[h] * r["mult"]
                             if cache[h] is not None else None)
            if r["fhs_half"] is None:
                gaps.append("%s %s: under %d returns, excluded"
                            % (cap, h, MIN_RET))
            out.append(r)
    return out, gaps


def score_rows(rows):
    out = []
    for r in rows:
        ch = r.get("fhs_half")
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


def screen_pairs(capture_dirs, step=21, min_hist=N_RET + 1):
    """Pseudo-window pairs from each ticker's longest price.csv, with
    realised windows ending on or before 2023-12-28."""
    by_t = {}
    for cap in capture_dirs:
        t = os.path.basename(cap).upper()
        cl = read_closes(cap, "2023-12-28")
        if len(cl) > len(by_t.get(t, [])):
            by_t[t] = cl
    pairs = []
    for t, cl in sorted(by_t.items()):
        closes = [c for _, c in cl]
        dates = [d for d, _ in cl]
        for h in HORIZONS:
            n = R.SESSIONS[h]
            i = min_hist
            while i + n < len(closes):
                hist = closes[:i]
                rets = logrets(hist)
                half = fhs_band(rets, n)
                s60 = R._sd(rets[-60:])
                if half and s60:
                    real = (closes[i + n - 1] / closes[i - 1] - 1) * 100
                    v2 = R.half_pct(s60, h, ens_mod.V2_BAND_K[h])
                    nv = R.half_pct(s60, h, 1.2816)
                    pairs.append({
                        "ticker": t, "as_of": dates[i - 1], "horizon": h,
                        "is_naive": bs.winkler_is(real, -nv, nv),
                        "is_v2": bs.winkler_is(real, -v2, v2),
                        "is_ch": bs.winkler_is(real, -half, half),
                        "in_v2": abs(real) <= v2,
                        "in_ch": abs(real) <= half})
                i += step
    return pairs


def render(res, descriptive, title):
    L = [title, "GARCH(1,1) FHS, nominal 0.80 band (Q10/Q90), no k"]
    for h in HORIZONS:
        c = res[h]
        L.append("%s: n=%d, %d cutoffs, %d tickers"
                 % (h, c["n"], c["cutoffs"], c["tickers"]))
        L.append("  FHS coverage %s  RangeSkill %s  CI cutoff [%s, %s]  "
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
    sc = sub.add_parser("screen")
    sc.add_argument("--captures", nargs="+", required=True)
    sc.add_argument("--reps", type=int, default=2000)
    sc.add_argument("--json", default=None)
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
    if a.mode == "screen":
        pairs = screen_pairs(allc)
        res = R.evaluate(pairs, a.reps)
        print(render(res, True, "SCREEN (pseudo-windows ending <= "
                     "2023-12-28, no verdict cell touched), descriptive"))
        if a.json:
            with open(a.json, "w", encoding="utf-8") as fh:
                json.dump({"results": res}, fh, indent=1)
        return 0
    caps = A.find_captures(a.captures, a.min_cell)
    rows, gaps = build_rows(caps, allc)
    res = R.evaluate(score_rows(rows), a.reps, a.seed)
    print(render(res, a.descriptive,
                 "DESCRIPTIVE ONLY, no verdict valid" if a.descriptive
                 else "CLEAN SCORING, cells >= %d" % a.min_cell))
    print("excluded rows (under %d returns): %d"
          % (MIN_RET, sum("excluded" in g for g in gaps)))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump({"results": res, "verdict": keep_verdict(res)[0],
                       "descriptive": a.descriptive}, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
