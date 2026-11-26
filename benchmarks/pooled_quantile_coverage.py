#!/usr/bin/env python3
"""Pooled (cross-ticker) empirical-quantile bands, coverage experiment
(INS-IMPROVE-001 round 12; GO and design are Muhammad's, relayed in Moos
Slack 1795725980.697499). DESCRIPTIVE run on untouched cells 48-90: no
verdict key or verdict line in text or JSON, nothing here is an
adoption, scripts/ensemble.py and frozen values are untouched.

Idea. Every existing band is a symmetric k x sigma x sqrt(sessions)
multiple. Here the band is read from the data: per horizon, ONE pair of
quantiles of the standardised move
  z = realised move / scale,   scale = sigma x sqrt(sessions) x 100 (pp)
pooled across all tickers, then band = [Q_lo x scale, Q_hi x scale] for
every row, with (lo, hi) = (0.10, 0.90): an 80% band by construction,
the middle of the coverage target 0.75-0.85. Asymmetric if the pooled
residuals are. Nothing else is fitted: no per-ticker, no per-cell
parameter.

TRAINING ONLY (fit, pre-registered before any scoring):
  (a) long OHLC history: benchmarks pseudo-cutoffs every 21 sessions
      after 120 bars on ohlcv/yahoo/*_CA.csv (the Yahoo close column,
      NOT adjclose and not egxpy: they disagree with each other on most
      closes, so every number here is Yahoo close-to-close), windows
      ending on or before 2023-12-28 (screen_band_models.SCREEN_END), so
      no verdict-cell window is touched; scale = s60 x sqrt(sessions)
      x 100 with s60 the 60-return population stdev about the mean
      (R._sd), as the other screens. Only the POST regime is fitted
      (window lookback starts on or after 2021-09-05, decree 681); pre
      quantiles are printed for context and never used. The long store
      has no Open column; s60 needs closes only.
  (b) capture cells 1-47 (R.build_rows), scale = the capture's naive
      half-width / 1.2816 (its sigma x RISK_MULT).
Cells 48-102 and every ledger row are never fitted: main refuses
--max-cell above 47 for the fit by construction (fit rows are filtered
to numbered cells <= 47) and refuses a scoring window outside
[48, 90]. Unnumbered captures are dropped.

SCORED (descriptive): captures with cells 48-90 (default). Per horizon
it prints raw n, cutoff clusters, tickers; coverage with the cutoff-
clustered CI and its absolute width (the 0.15 cap, R.MAX_CI_WIDTH);
RangeSkill vs the naive band with its cutoff-clustered CI; and the
mean Winkler interval score (alpha 0.2) of the pooled-quantile band,
the naive band, the Parkinson-naive band (1.2816 x park60 x
sqrt(sessions) x RISK_MULT, an interpretation of "Parkinson-naive":
the naive multiplier on the Parkinson sigma) and frozen v2, with
1 - IS(pooled)/IS(Parkinson-naive). The pre-registered loop bar for any
later adoption reading is: RangeSkill CI lower bound > 0 AND coverage CI
overlapping [0.75, 0.85] with width <= 0.15, on ALL horizons, at >= 10
cutoff clusters; at 8 clusters this run states the numbers only.

Usage:
  python3 benchmarks/pooled_quantile_coverage.py --history DIR
      --captures DIR ... [--min-cell 48] [--max-cell 90] [--reps 2000]
      [--json OUT]
"""
import argparse
import csv
import json
import os
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import replay_band_candidates as R  # noqa: E402
import score_adoption_594 as A  # noqa: E402
import screen_band_models as S  # noqa: E402
import ensemble as ens_mod  # noqa: E402
import backtest_score as bs  # noqa: E402

HORIZONS = A.HORIZONS
Q_LO, Q_HI = 0.10, 0.90
NAIVE_K = 1.2816
FIT_MAX_CELL = 47
SCORE_MIN_CELL, SCORE_MAX_CELL = 48, 90
MIN_FIT = 30          # fewer pooled training z on a horizon: undefined
_f = lambda v, nd=3: "n/a" if v is None else "%.*f" % (nd, v)  # noqa: E731


def read_closes(path):
    """[(date, close)] oldest first, date <= SCREEN_END, Yahoo close."""
    out = []
    try:
        with open(path, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                d = str(r.get("date") or r.get("Date") or "")[:10]
                c = A.fnum(r.get("close") or r.get("Close"))
                if d and d <= S.SCREEN_END and c and c > 0:
                    out.append((d, c))
    except OSError:
        return []
    return sorted(out)


def load_history(history_dir):
    by_t = {}
    for fn in sorted(os.listdir(history_dir)):
        stem, ext = os.path.splitext(fn)
        if ext.lower() == ".csv" and stem.upper().endswith("_CA"):
            by_t[stem.upper()] = read_closes(os.path.join(history_dir, fn))
    return by_t


def history_z(by_t, regime="post", step=S.STEP, min_hist=S.MIN_HIST):
    """{horizon: [z]} pooled over tickers and pseudo-cutoffs; windows
    end on or before SCREEN_END, only the requested regime."""
    out = {h: [] for h in HORIZONS}
    for _t, bars in sorted(by_t.items()):
        closes = [c for _, c in bars]
        for h in HORIZONS:
            n = R.SESSIONS[h]
            i = min_hist
            while i + n <= len(bars):
                if S.regime_of(bars, i, n) == regime:
                    s60 = R._sd(R._logrets(closes[max(0, i - 60 - 1):i])[-60:])
                    if s60:
                        scale = s60 * (n ** 0.5) * 100
                        real = (closes[i + n - 1] / closes[i - 1] - 1) * 100
                        out[h].append(real / scale)
                i += step
    return out


def row_scale(row):
    return row["naive_half"] / NAIVE_K


def usable(row):
    return (row.get("naive_half") or 0) > 0 and row.get("real") is not None


def cell_z(rows):
    out = {h: [] for h in HORIZONS}
    for r in rows:
        if usable(r) and r["horizon"] in out:
            out[r["horizon"]].append(r["real"] / row_scale(r))
    return out


def quantile(xs, q):
    """Linear-interpolated empirical quantile; None when empty."""
    xs = sorted(xs)
    if not xs:
        return None
    pos = q * (len(xs) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def fit(z_hist, z_cells):
    """{horizon: {lo, hi, n_history, n_cells}} from TRAINING z only;
    lo/hi None below MIN_FIT pooled values."""
    out = {}
    for h in HORIZONS:
        z = list(z_hist.get(h, [])) + list(z_cells.get(h, []))
        ok = len(z) >= MIN_FIT
        out[h] = {"lo": quantile(z, Q_LO) if ok else None,
                  "hi": quantile(z, Q_HI) if ok else None,
                  "n_history": len(z_hist.get(h, [])),
                  "n_cells": len(z_cells.get(h, []))}
    return out


def make_pairs(test_rows, fitted):
    pairs = []
    for r in test_rows:
        h = r["horizon"]
        f = fitted.get(h)
        if not usable(r) or not f or f["lo"] is None:
            continue
        sc, real = row_scale(r), r["real"]
        lo, hi = f["lo"] * sc, f["hi"] * sc
        v2 = R.half_pct(r["v2_sigma"], h, ens_mod.V2_BAND_K[h], r["mult"])
        park = r["sig"].get("park60")
        pk = (R.half_pct(park, h, NAIVE_K, r["mult"]) if park else None)
        pairs.append({
            "ticker": r["ticker"], "as_of": r["as_of"], "horizon": h,
            "is_naive": bs.winkler_is(real, -r["naive_half"],
                                      r["naive_half"]),
            "is_v2": bs.winkler_is(real, -v2, v2),
            "is_ch": bs.winkler_is(real, lo, hi),
            "is_park": (bs.winkler_is(real, -pk, pk)
                        if pk is not None else None),
            "in_v2": abs(real) <= v2, "in_ch": lo <= real <= hi})
    return pairs


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else None


def evaluate(pairs, reps, seed=A.DEFAULT_SEED):
    res = R.evaluate(pairs, reps, seed)
    for h in HORIZONS:
        hp = [p for p in pairs if p["horizon"] == h]
        pk = [p for p in hp if p["is_park"] is not None]
        c = res[h]
        ci = c["ch_cov_ci_cutoff"]
        c["cov_ci_width"] = (ci[1] - ci[0]
                             if None not in ci else None)
        c["winkler"] = {"pooled": mean(p["is_ch"] for p in hp),
                        "naive": mean(p["is_naive"] for p in hp),
                        "v2": mean(p["is_v2"] for p in hp),
                        "parkinson_naive": mean(p["is_park"] for p in pk),
                        "n_park": len(pk)}
        w = c["winkler"]
        pkc = mean(p["is_ch"] for p in pk)
        c["vs_parkinson_naive"] = (
            1 - pkc / w["parkinson_naive"]
            if pkc is not None and w["parkinson_naive"] else None)
    return res


def render(fitted, res, pre_q, window):
    L = ["Pooled-quantile coverage experiment (descriptive only): "
         "quantiles (%.2f, %.2f), fit = long history post-regime + "
         "cells <= %d, scored on cells %d-%d"
         % (Q_LO, Q_HI, FIT_MAX_CELL, window[0], window[1])]
    for h in HORIZONS:
        f, c = fitted[h], res[h]
        L.append("%s: fit n history %d + cells %d, Q_lo %s Q_hi %s "
                 "(pre-regime context Q_lo %s Q_hi %s, not used)"
                 % (h, f["n_history"], f["n_cells"], _f(f["lo"]),
                    _f(f["hi"]), _f(pre_q[h][0]), _f(pre_q[h][1])))
        L.append("  scored raw n=%d, cutoff clusters=%d, tickers=%d"
                 % (c["n"], c["cutoffs"], c["tickers"]))
        cc = c["ch_cov_ci_cutoff"]
        sc = c["ch_ci_cutoff"]
        L.append("  coverage %s CI [%s, %s] width %s | RangeSkill %s CI "
                 "[%s, %s] | frozen v2 coverage %s RangeSkill %s"
                 % (_f(c["ch"]["coverage"]), _f(cc[0]), _f(cc[1]),
                    _f(c["cov_ci_width"]), _f(c["ch"]["range_skill"]),
                    _f(sc[0]), _f(sc[1]), _f(c["v2"]["coverage"]),
                    _f(c["v2"]["range_skill"])))
        w = c["winkler"]
        L.append("  mean Winkler: pooled %s, naive %s, Parkinson-naive "
                 "%s (n=%d), frozen v2 %s | 1 - pooled/Parkinson-naive "
                 "%s" % (_f(w["pooled"]), _f(w["naive"]),
                         _f(w["parkinson_naive"]), w["n_park"],
                         _f(w["v2"]), _f(c["vs_parkinson_naive"])))
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.
                                 RawDescriptionHelpFormatter)
    ap.add_argument("--history", required=True)
    ap.add_argument("--captures", nargs="+", required=True)
    ap.add_argument("--min-cell", type=int, default=SCORE_MIN_CELL)
    ap.add_argument("--max-cell", type=int, default=SCORE_MAX_CELL)
    ap.add_argument("--reps", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=A.DEFAULT_SEED)
    ap.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    if a.min_cell < SCORE_MIN_CELL or a.max_cell > SCORE_MAX_CELL:
        print("refusing: scoring window must lie inside cells %d-%d "
              "(cells <= %d are the fit, cells >= %d are verdict cells)"
              % (SCORE_MIN_CELL, SCORE_MAX_CELL, FIT_MAX_CELL,
                 SCORE_MAX_CELL + 1), file=sys.stderr)
        return 2
    allc = [c for c in A.find_captures(a.captures, None)
            if A.cell_number(c) is not None]
    train_caps = [c for c in allc if A.cell_number(c) <= FIT_MAX_CELL]
    test_caps = [c for c in allc
                 if a.min_cell <= A.cell_number(c) <= a.max_cell]
    by_t = load_history(a.history)
    fitted = fit(history_z(by_t, "post"),
                 cell_z(R.build_rows(train_caps, allc)[0]))
    pre = history_z(by_t, "pre")
    pre_q = {h: (quantile(pre[h], Q_LO), quantile(pre[h], Q_HI))
             for h in HORIZONS}
    test_rows, _g = R.build_rows(test_caps, allc)
    pairs = make_pairs(test_rows, fitted)
    res = evaluate(pairs, a.reps, a.seed)
    print(render(fitted, res, pre_q, (a.min_cell, a.max_cell)))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump({"descriptive": True, "q": [Q_LO, Q_HI],
                       "fit_max_cell": FIT_MAX_CELL,
                       "score_cells": [a.min_cell, a.max_cell],
                       "reps": a.reps, "seed": a.seed, "fit": fitted,
                       "pre_regime_context": pre_q, "results": res},
                      fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
