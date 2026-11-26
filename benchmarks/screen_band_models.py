#!/usr/bin/env python3
"""Long-history rolling-origin screen of cheap band models
(INS-IMPROVE-007 item 1). DESCRIPTIVE ONLY, never a verdict.

Models (all use the frozen v2 k table V2_BAND_K, nothing fitted, so
only the width input differs): s60 (= frozen v2), s20, ewma94,
blend2060, park60, gk60, all from R.sigmas on OHLC bars with nothing
after the pseudo-cutoff. Band centre 0, half = k x sigma x sqrt(sess)
x 100. Comparison column is frozen v2; the naive band is
1.2816 x s60 x sqrt(sess) as in the other screens.

Inputs:
  --history DIR   TICKER.csv files with Date,Open,High,Low,Close
                  (the long-history deliverable from the data lane);
  --captures DIR  capture trees; the longest indicator CSV per ticker
                  (collected/pandas-ta|talib/indicators.csv) is used.
Pseudo-cutoffs every STEP = 21 sessions after MIN_HIST = 120 bars.

Screening exclusion rule: only realised windows that END on or before
2023-12-28 enter the screen (every capture cell 1-102 has its cutoff on
or after 2023-12-29), so no verdict-cell window and no ledger row is
touched, and the 91-102 holdout block stays untouched. Bars after
2023-12-28 are dropped before any window is built.

Effective n: pseudo-cutoff dates are the clusters (names share one
market factor, week/month windows overlap across adjacent cutoffs if
STEP < sessions). Raw n and cutoff clusters are printed together. The
coverage leg is printed as the point value and as the cutoff-clustered
CI (the #775 reading); no keep verdict is produced.
Challengers tried to date: A-F and the item 4 rolling conformal, plus
these six estimators (read any single win against that count).

Usage:
  python3 benchmarks/screen_band_models.py --captures DIR ... [--reps N]
      [--json OUT]
  python3 benchmarks/screen_band_models.py --history DIR [--json OUT]
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
import ensemble as ens_mod  # noqa: E402
import backtest_score as bs  # noqa: E402

HORIZONS = A.HORIZONS
SCREEN_END = "2023-12-28"
STEP = 21
MIN_HIST = 120
MODELS = ("s20", "ewma94", "blend2060", "park60", "gk60")
_f = lambda v: "n/a" if v is None else "%.3f" % v  # noqa: E731


def read_history_csv(path):
    """[(date, o, h, l, c)] with date <= SCREEN_END, oldest first."""
    out = []
    try:
        with open(path, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                d = str(r.get("Date") or r.get("date") or "")[:10]
                v = [A.fnum(r.get(k)) for k in
                     ("Open", "High", "Low", "Close")]
                if d and d <= SCREEN_END and all(x and x > 0 for x in v):
                    out.append((d,) + tuple(v))
    except OSError:
        return []
    return sorted(out)


def read_capture_history(cap):
    for rel in ("collected/pandas-ta/indicators.csv",
                "collected/talib/indicators.csv"):
        p = os.path.join(cap, rel)
        if os.path.exists(p):
            tmp = []
            try:
                with open(p, newline="", encoding="utf-8") as f:
                    for r in csv.DictReader(f):
                        d = str(r.get("Date") or "")[:10]
                        v = [A.fnum(r.get(k)) for k in
                             ("Open", "High", "Low", "Close")]
                        if d and d <= SCREEN_END and all(
                                x and x > 0 for x in v):
                            tmp.append((d,) + tuple(v))
            except OSError:
                continue
            if tmp:
                return sorted(tmp)
    return []


def load(history_dir, capture_dirs):
    by_t = {}
    if history_dir:
        for fn in sorted(os.listdir(history_dir)):
            if fn.lower().endswith(".csv"):
                t = os.path.splitext(fn)[0].upper()
                by_t[t] = read_history_csv(os.path.join(history_dir, fn))
    for cap in capture_dirs:
        if A.cell_number(cap) is None:
            continue  # unnumbered export copies are never captures
        t = os.path.basename(cap).upper()
        bars = read_capture_history(cap)
        if len(bars) > len(by_t.get(t, [])):
            by_t[t] = bars
    return by_t


def screen_pairs(by_t, step=STEP, min_hist=MIN_HIST):
    """{model: [pair]}; each pair carries ch = the model band."""
    out = {m: [] for m in MODELS}
    for t, bars in sorted(by_t.items()):
        bars = [b for b in bars if b[0] <= SCREEN_END]
        closes = [b[4] for b in bars]
        for h in HORIZONS:
            n = R.SESSIONS[h]
            i = min_hist
            while i + n <= len(bars):
                sig = R.sigmas([b[1:] for b in bars[:i]])
                s60 = sig.get("s60")
                real = (closes[i + n - 1] / closes[i - 1] - 1) * 100
                if s60:
                    v2 = R.half_pct(s60, h, ens_mod.V2_BAND_K[h])
                    nv = R.half_pct(s60, h, 1.2816)
                    for m in MODELS:
                        if not sig.get(m):
                            continue
                        half = R.half_pct(sig[m], h, ens_mod.V2_BAND_K[h])
                        out[m].append({
                            "ticker": t, "as_of": bars[i - 1][0],
                            "horizon": h,
                            "is_naive": bs.winkler_is(real, -nv, nv),
                            "is_v2": bs.winkler_is(real, -v2, v2),
                            "is_ch": bs.winkler_is(real, -half, half),
                            "in_v2": abs(real) <= v2,
                            "in_ch": abs(real) <= half})
                i += step
    return out


def render(results):
    L = ["SCREEN of cheap band models on long history (windows end <= "
         "%s), frozen v2 k, descriptive, no verdict" % SCREEN_END]
    for m in MODELS:
        L.append("")
        L.append("model %s" % m)
        for h in HORIZONS:
            c = results[m][h]
            L.append("  %s: raw n=%d, effective n (cutoff clusters)=%d, "
                     "%d tickers" % (h, c["n"], c["cutoffs"],
                                     c["tickers"]))
            L.append("    coverage %s (CI cutoff [%s, %s])  RangeSkill %s "
                     "(CI cutoff [%s, %s])  | v2 coverage %s RangeSkill %s"
                     % (_f(c["ch"]["coverage"]),
                        _f(c["ch_cov_ci_cutoff"][0]),
                        _f(c["ch_cov_ci_cutoff"][1]),
                        _f(c["ch"]["range_skill"]),
                        _f(c["ch_ci_cutoff"][0]), _f(c["ch_ci_cutoff"][1]),
                        _f(c["v2"]["coverage"]),
                        _f(c["v2"]["range_skill"])))
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.
                                 RawDescriptionHelpFormatter)
    ap.add_argument("--captures", nargs="*", default=[])
    ap.add_argument("--history", default=None)
    ap.add_argument("--reps", type=int, default=2000)
    ap.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    if not a.captures and not a.history:
        print("refusing: give --history or --captures")
        return 2
    caps = A.find_captures(a.captures, None) if a.captures else []
    by_t = load(a.history, caps)
    pairs = screen_pairs(by_t)
    results = {m: R.evaluate(pairs[m], a.reps) for m in MODELS}
    print(render(results))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump({"screen_end": SCREEN_END, "step": STEP,
                       "min_hist": MIN_HIST, "descriptive": True,
                       "models": list(MODELS), "results": results},
                      fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
