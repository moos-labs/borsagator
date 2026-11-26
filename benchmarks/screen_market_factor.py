#!/usr/bin/env python3
"""Route 2 screen: market-wide factor as a band-width input
(INS-IMPROVE-001 round 24 item 3). DESCRIPTIVE ONLY, never a verdict.

Provenance: the GO to implement, pre-register and screen Route 2 is
Muhammad's, relayed in Slack message 1795737001.782279. The route is
ranked 2 in docs/next-experiments-round-23.md.

PRE-REGISTRATION (written before this screen was run on the Yahoo store):
Data: ohlcv/yahoo/*.csv Yahoo CLOSE (raw, not adjclose, not egxpy) of the
36 EGX tickers (*.CA); NVDA is excluded. No Open column is used. Bars
after 2023-12-28 are dropped, so no verdict cell, ledger row or 91-102
holdout window is touched. The 2021-09-05 regime split is mandatory:
pairs are tagged pre/post, evaluated separately, never pooled (the same
rule and function as screen_band_models.regime_of).
Market factor: on each date, the equal-weight mean of the daily log
returns of the other tickers that have a return that date (leave-one-out,
so a name never enters its own factor; a date needs >= 10 other names).
Every input at a pseudo-cutoff is dated on or before the cutoff.
Per ticker and pseudo-cutoff (every STEP = 21 sessions after MIN_HIST =
120 bars, as the other screens), over the last 60 sessions:
  beta = cov(r, m) / var(m);  idio^2 = var(r) - beta^2 var(m) (>= 0);
  sigma = sqrt(idio^2 + beta^2 x mv^2),
where mv is the market's daily stdev estimated three ways (the family):
  mkt20  = stdev of the factor's last 20 sessions;
  mktew  = EWMA 0.94 of the factor's last 250 sessions;
  mktbl  = sqrt(0.5 x mkt20^2 + 0.5 x stdev(m over the ticker's 60)^2).
With mv = stdev(m over the ticker's 60) this reproduces the frozen s60
exactly (identity, tested), so any difference comes only from the
market-volatility estimate. Band centre 0, half = V2_BAND_K[h] x sigma x
sqrt(sessions) x 100, comparison column frozen v2 (s60), naive = 1.2816 x
s60. Nothing is fitted; ensemble.py and frozen values are untouched.
Family: 3 models x 3 horizons x 2 regimes = 18, fixed whatever --regime
selects. Each reading gets a one-sided p for RangeSkill <= 0 from the
cutoff-clustered bootstrap draws (Phipson-Smyth +1, as
screen_band_models.reading_p); Holm-Bonferroni over all 18. Numbers
only: no pass flag, no verdict, nothing here is an adoption.
Cells 48-90, then 91+: NOT scored here. This screen is the long-history
fit stage; a cell scoring of any reading needs its own pre-registered
step after this output is read, and cells >= 91 are the only verdict
cells.

Usage:
  python3 benchmarks/screen_market_factor.py --history DIR
      [--reps N] [--json OUT]
"""
import argparse
import bisect
import csv
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
import screen_band_models as SB  # noqa: E402
import ensemble as ens_mod  # noqa: E402
import backtest_score as bs  # noqa: E402

HORIZONS = A.HORIZONS
SCREEN_END = SB.SCREEN_END
LOOKBACK = SB.LOOKBACK
STEP = SB.STEP
MIN_HIST = SB.MIN_HIST
MIN_NAMES = 10
EW_WINDOW = 250
MODELS = ("mkt20", "mktew", "mktbl")
REGIMES = SB.REGIMES
FAMILY_SIZE = len(MODELS) * len(HORIZONS) * len(REGIMES)   # 18
_f = SB._f


def read_closes(path):
    """[(date, close)] oldest first, Yahoo close, date <= SCREEN_END."""
    out = {}
    try:
        with open(path, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                d = str(r.get("date") or "")[:10]
                c = A.fnum(r.get("close"))
                if d and d <= SCREEN_END and c and c > 0:
                    out[d] = c
    except OSError:
        return []
    return sorted(out.items())


def load(history_dir):
    by_t = {}
    for fn in sorted(os.listdir(history_dir)):
        if fn.upper().endswith("_CA.CSV"):
            t = os.path.splitext(fn)[0].upper()
            by_t[t] = read_closes(os.path.join(history_dir, fn))
    return by_t


def log_returns(bars):
    """{date: log return vs the previous bar of the same ticker}."""
    return {bars[k][0]: math.log(bars[k][1] / bars[k - 1][1])
            for k in range(1, len(bars))}


def market_sums(rets_by_t):
    """{date: (sum of returns, count)} over all tickers."""
    tot = {}
    for r in rets_by_t.values():
        for d, v in r.items():
            s, c = tot.get(d, (0.0, 0))
            tot[d] = (s + v, c + 1)
    return tot


def factor_ex(tot, own):
    """Leave-one-out factor for one ticker: ([dates], [values]) sorted,
    dates with >= MIN_NAMES other names only."""
    dates, vals = [], []
    for d in sorted(tot):
        s, c = tot[d]
        if d in own:
            s, c = s - own[d], c - 1
        if c >= MIN_NAMES:
            dates.append(d)
            vals.append(s / c)
    return dates, vals


def _cov(a, b):
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / len(a)


def sigma_from(r, m, mv):
    """sqrt(idio^2 + beta^2 mv^2) from the ticker's returns r and the
    aligned factor m. mv = population stdev of m gives stdev(r)."""
    vm = _cov(m, m)
    if vm <= 0:
        return None
    beta = _cov(r, m) / vm
    idio = max(_cov(r, r) - beta * beta * vm, 0.0)
    return math.sqrt(idio + beta * beta * mv * mv)


def model_sigmas(r60, m60, fdates, fvals, d):
    """{model: sigma, 's60': stdev(r60)} at cutoff date d, inputs <= d."""
    e = bisect.bisect_right(fdates, d)
    s60 = R._sd(r60)
    mv60 = R._sd(m60)
    mv20 = R._sd(fvals[max(0, e - 20):e])
    mvew = R._ewma(fvals[max(0, e - EW_WINDOW):e])
    out = {"s60": s60}
    if None in (mv60, mv20):
        return out
    mvs = {"mkt20": mv20, "mktew": mvew,
           "mktbl": math.sqrt(0.5 * mv20 ** 2 + 0.5 * mv60 ** 2)}
    for k, v in mvs.items():
        out[k] = sigma_from(r60, m60, v) if v is not None else None
    return out


def screen_pairs(by_t, step=STEP, min_hist=MIN_HIST, regime=None):
    """{model: [pair]} with the same pair shape as screen_band_models."""
    rets = {t: log_returns(b) for t, b in by_t.items()}
    tot = market_sums(rets)
    out = {m: [] for m in MODELS}
    for t, bars in sorted(by_t.items()):
        if len(bars) < min_hist + 1:
            continue
        fdates, fvals = factor_ex(tot, rets[t])
        fpos = {d: i for i, d in enumerate(fdates)}
        closes = [b[1] for b in bars]
        for h in HORIZONS:
            n = R.SESSIONS[h]
            i = min_hist
            while i + n <= len(bars):
                rg = SB.regime_of(bars, i, n)
                if rg is None or (regime and rg != regime):
                    i += step
                    continue
                dts = [bars[k][0] for k in range(i - LOOKBACK, i)]
                if i - LOOKBACK < 1 or any(d not in fpos for d in dts):
                    i += step
                    continue
                r60 = [rets[t][d] for d in dts]
                m60 = [fvals[fpos[d]] for d in dts]
                sig = model_sigmas(r60, m60, fdates, fvals, bars[i - 1][0])
                s60 = sig.get("s60")
                if s60:
                    real = (closes[i + n - 1] / closes[i - 1] - 1) * 100
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


def render(results, title=""):
    L = ["SCREEN of market-factor band models on long history (Yahoo "
         "close, windows end <= %s), frozen v2 k, descriptive only"
         "%s" % (SCREEN_END, title)]
    for m in MODELS:
        L.append("")
        L.append("model %s" % m)
        for h in HORIZONS:
            c = results[m][h]
            L.append("  %s: raw n=%d, effective n (cutoff clusters)=%d, "
                     "%d tickers" % (h, c["n"], c["cutoffs"], c["tickers"]))
            L.append("    coverage %s (CI cutoff [%s, %s])  RangeSkill %s "
                     "(CI cutoff [%s, %s])  | v2 coverage %s RangeSkill %s"
                     % (_f(c["ch"]["coverage"]),
                        _f(c["ch_cov_ci_cutoff"][0]),
                        _f(c["ch_cov_ci_cutoff"][1]),
                        _f(c["ch"]["range_skill"]),
                        _f(c["ch_ci_cutoff"][0]), _f(c["ch_ci_cutoff"][1]),
                        _f(c["v2"]["coverage"]), _f(c["v2"]["range_skill"])))
    return "\n".join(L)


def holm_rows(readings):
    adj = SB.holm_adjust(readings, m=FAMILY_SIZE)
    return [{"model": k[0], "horizon": k[1], "regime": k[2],
             "p": readings[k], "holm_adj_p": adj.get(k)}
            for k in sorted(readings)]


def render_holm(rows):
    L = ["", "MULTIPLE TESTING: Holm-Bonferroni over the screen's %d "
         "readings (one-sided p for RangeSkill <= 0, cutoff-clustered "
         "bootstrap); numbers only" % FAMILY_SIZE]
    for r in rows:
        L.append("  %s %s %s: p %s  Holm-adjusted p %s"
                 % (r["model"], r["regime"], r["horizon"], _f(r["p"]),
                    _f(r["holm_adj_p"])))
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.
                                 RawDescriptionHelpFormatter)
    ap.add_argument("--history", required=True)
    ap.add_argument("--regime", choices=REGIMES, default=None)
    ap.add_argument("--reps", type=int, default=2000)
    ap.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    by_t = load(a.history)
    regimes = [a.regime] if a.regime else list(REGIMES)
    allres, readings = {}, {}
    for rg in regimes:
        pairs = screen_pairs(by_t, regime=rg)
        allres[rg] = {m: R.evaluate(pairs[m], a.reps) for m in MODELS}
        for m in MODELS:
            for h in HORIZONS:
                readings[(m, h, rg)] = SB.reading_p(
                    [p for p in pairs[m] if p["horizon"] == h], a.reps)
        print(render(allres[rg], ", regime %s (break %s)"
                     % (rg, SB.BREAK_DATE)))
        print()
    holm = holm_rows(readings)
    print(render_holm(holm))
    print("tickers loaded: %d" % len(by_t))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump({"descriptive": True, "source": "yahoo close",
                       "screen_end": SCREEN_END, "tickers": sorted(by_t),
                       "models": list(MODELS), "regimes": allres,
                       "holm": {"family_size": FAMILY_SIZE,
                                "method": "Holm-Bonferroni",
                                "readings": holm}}, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
