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
Regime break: price limits changed on 2021-09-05 (decree 681, research
note, not relied on by code beyond this split). Each pair is tagged
"pre" when its realised window ends before BREAK_DATE, or "post" when
the first sigma lookback bar (as_of minus LOOKBACK sessions) is on or
after BREAK_DATE. Pairs whose window or lookback straddles the break
are dropped, and the two regimes are evaluated and printed SEPARATELY,
never pooled. Use --regime post to start after the last break.
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

Multiple testing (round 9, Muhammad's call (d)): the family is the
readings this screen makes, FAMILY_SIZE = models x horizons x regimes
= 5 x 3 x 2 = 30, fixed whatever --regime selects (an unrun reading
counts as p = 1, so a one-regime run is never less strict). Each reading
gets a one-sided p for H0 "RangeSkill <= 0" from the same cutoff-
clustered bootstrap draws as its CI, p = (draws <= 0, plus 1) / (draws
+ 1). Holm-Bonferroni is applied across all 30; the PRIMARY reading is
Arm 1 (park60, three horizons x two regimes) and its Holm-adjusted p is
printed and written to the JSON beside the raw p. These are numbers
only: no pass flag, no verdict, nothing here is an adoption.

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
BREAK_DATE = "2021-09-05"   # price-limit regime change (decree 681)
LOOKBACK = 60               # sessions behind a sigma estimate
STEP = 21
MIN_HIST = 120
MODELS = ("s20", "ewma94", "blend2060", "park60", "gk60")
REGIMES = ("pre", "post")
PRIMARY = "park60"          # Arm 1
FAMILY_SIZE = len(MODELS) * len(HORIZONS) * len(REGIMES)   # 30
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


def regime_of(bars, i, n):
    """'pre' | 'post' | None for the pair cut at bar index i (the base
    bar is bars[i - 1]) with a realised window of n sessions."""
    end_date = bars[i + n - 1][0]
    start_look = bars[max(0, i - LOOKBACK)][0]
    if end_date < BREAK_DATE:
        return "pre"
    if start_look >= BREAK_DATE:
        return "post"
    return None


def screen_pairs(by_t, step=STEP, min_hist=MIN_HIST, regime=None):
    """{model: [pair]}; each pair carries ch = the model band and a
    regime tag. regime = 'pre' | 'post' keeps only that regime."""
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
                rg = regime_of(bars, i, n)
                if rg is None or (regime and rg != regime):
                    i += step
                    continue
                if s60:
                    v2 = R.half_pct(s60, h, ens_mod.V2_BAND_K[h])
                    nv = R.half_pct(s60, h, 1.2816)
                    for m in MODELS:
                        if not sig.get(m):
                            continue
                        half = R.half_pct(sig[m], h, ens_mod.V2_BAND_K[h])
                        out[m].append({
                            "ticker": t, "as_of": bars[i - 1][0],
                            "horizon": h, "regime": rg,
                            "is_naive": bs.winkler_is(real, -nv, nv),
                            "is_v2": bs.winkler_is(real, -v2, v2),
                            "is_ch": bs.winkler_is(real, -half, half),
                            "in_v2": abs(real) <= v2,
                            "in_ch": abs(real) <= half})
                i += step
    return out


def reading_p(pairs, reps, seed=A.DEFAULT_SEED):
    """One-sided p for H0 RangeSkill <= 0 from the cutoff-clustered
    bootstrap draws; None when there are no draws."""
    skill, _ = R._boot(pairs, "as_of", reps, seed)
    if not skill:
        return None
    return (sum(1 for x in skill if x <= 0) + 1.0) / (len(skill) + 1.0)


def holm_adjust(pvals, m=FAMILY_SIZE):
    """Holm-Bonferroni over a family of m readings. pvals is
    {key: p or None}; None readings are skipped (they count as p = 1 in
    the family of m, which is what m already assumes). Returns
    {key: adjusted p}, monotone, capped at 1."""
    items = sorted((p, k) for k, p in pvals.items() if p is not None)
    out, run = {}, 0.0
    for i, (p, k) in enumerate(items):
        run = max(run, min(1.0, (m - i) * p))
        out[k] = run
    return out


def holm_table(readings):
    """readings {(model, horizon, regime): p}. Rows for every reading
    with raw and Holm-adjusted p; no pass flag."""
    adj = holm_adjust(readings)
    rows = []
    for k in sorted(readings):
        rows.append({"model": k[0], "horizon": k[1], "regime": k[2],
                     "primary": k[0] == PRIMARY, "p": readings[k],
                     "holm_adj_p": adj.get(k)})
    return rows


def render_holm(rows):
    L = ["", "MULTIPLE TESTING: Holm-Bonferroni over the screen's %d "
         "readings (one-sided p for RangeSkill <= 0, cutoff-clustered "
         "bootstrap); numbers only, no verdict" % FAMILY_SIZE,
         "Arm 1 (%s), the primary reading:" % PRIMARY]
    for r in rows:
        if r["primary"]:
            L.append("  %s %s: p %s  Holm-adjusted p %s"
                     % (r["regime"], r["horizon"], _f(r["p"]),
                        _f(r["holm_adj_p"])))
    return "\n".join(L)


def render(results, title=""):
    L = ["SCREEN of cheap band models on long history (windows end <= "
         "%s), frozen v2 k, descriptive, no verdict%s"
         % (SCREEN_END, title)]
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
    ap.add_argument("--regime", choices=("pre", "post"), default=None,
                    help="evaluate one regime only (default: both, "
                    "separately)")
    ap.add_argument("--reps", type=int, default=2000)
    ap.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    if not a.captures and not a.history:
        print("refusing: give --history or --captures")
        return 2
    caps = A.find_captures(a.captures, None) if a.captures else []
    by_t = load(a.history, caps)
    regimes = [a.regime] if a.regime else list(REGIMES)
    allres = {}
    readings = {}
    for rg in regimes:
        pairs = screen_pairs(by_t, regime=rg)
        allres[rg] = {m: R.evaluate(pairs[m], a.reps) for m in MODELS}
        for m in MODELS:
            for h in HORIZONS:
                readings[(m, h, rg)] = reading_p(
                    [p for p in pairs[m] if p["horizon"] == h], a.reps)
        print(render(allres[rg], ", regime %s (break %s)"
                     % (rg, BREAK_DATE)))
        print()
    holm = holm_table(readings)
    print(render_holm(holm))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump({"screen_end": SCREEN_END, "step": STEP,
                       "min_hist": MIN_HIST, "break_date": BREAK_DATE,
                       "lookback": LOOKBACK, "descriptive": True,
                       "models": list(MODELS), "regimes": allres,
                       "holm": {"family_size": FAMILY_SIZE,
                                "primary_model": PRIMARY,
                                "method": "Holm-Bonferroni",
                                "readings": holm}},
                      fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
