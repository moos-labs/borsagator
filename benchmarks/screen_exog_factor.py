#!/usr/bin/env python3
"""Proposal B screen: global factors (EEM, Brent, gold) in place of the
EGX equal-weight factor in the market-factor decomposition
(INS-IMPROVE-001 round 26). DESCRIPTIVE ONLY, never a verdict.

Provenance: the GO for proposal B (swap the factor source in
screen_market_factor.py, family 18, Holm, descriptive, no cells scored)
is Muhammad's, relayed in Slack message 1795739487.837839. The
proposal is in docs/proposals-round-25.md.

PRE-REGISTRATION (written before this screen was run):
Data: Yahoo CLOSE (raw) of the EGX tickers as screen_market_factor, and
Yahoo close of EEM, BZ=F (Brent futures), GC=F (gold futures) from
evaluation/external_factors/*.csv, all dated <= 2023-12-28. No cell,
ledger row or 91-102 window is touched. The 2021-09-05 regime split is
mandatory (screen_band_models.regime_of), pre/post evaluated separately.
Factor return: daily log return of the factor's close on its own
calendar of bars. LAG ONE SESSION: for a ticker bar dated d the aligned
factor return is the latest factor return dated strictly before d, so no
same-day or later factor information enters (the US and futures sessions
close after the EGX session). At a cutoff dated D only factor returns
dated strictly before D are used for the volatility estimate.
Per ticker and pseudo-cutoff (every STEP = 21 sessions after MIN_HIST =
120 bars) over the last 60 sessions, as screen_market_factor:
  beta = cov(r, m) / var(m);  idio^2 = var(r) - beta^2 var(m) (>= 0);
  sigma = sqrt(idio^2 + beta^2 x mv^2)   (MF.sigma_from)
with ONE volatility estimator for mv: EWMA 0.94 over the last 250 factor
returns dated before D (replay_band_candidates._ewma, needs >= 25).
Disclosure: this is the standard single estimator and it is also the one
with the smallest Holm p in the round-24 EGX-factor screen
(benchmarks/screen_market_factor_r24.json); it was not chosen blind.
With mv = stdev(m over the ticker's 60) the decomposition reproduces the
frozen s60 exactly (tested). Band centre 0, half = V2_BAND_K[h] x sigma x
sqrt(sessions) x 100; comparison column frozen v2 (s60). Nothing is
fitted; ensemble.py and frozen values are untouched.
Family: 3 factors x 3 horizons x 2 regimes = 18, fixed whatever --regime
selects; one-sided cutoff-clustered bootstrap p for RangeSkill <= 0
(Phipson-Smyth +1), Holm-Bonferroni over 18. Numbers only. Cells 48-90
and 91+ are NOT scored here; a cell scoring needs its own pre-registered
step. EEM, BZ=F and GC=F are market quotes (futures front-month series
with roll gaps), not EGX data.

Usage:
  python3 benchmarks/screen_exog_factor.py --history DIR --factors DIR
      [--regime pre|post] [--reps N] [--json OUT]
"""
import argparse
import bisect
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
import screen_market_factor as MF  # noqa: E402
import ensemble as ens_mod  # noqa: E402
import backtest_score as bs  # noqa: E402

HORIZONS = A.HORIZONS
REGIMES = SB.REGIMES
FACTORS = {"EEM": "EEM.csv", "BZ=F": "BZ_F.csv", "GC=F": "GC_F.csv"}
EW_WINDOW = 250
FAMILY_SIZE = len(FACTORS) * len(HORIZONS) * len(REGIMES)   # 18
_f = SB._f


def read_factor(path):
    """[(date, close)] oldest first, date <= SCREEN_END."""
    import csv
    out = {}
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            d = str(r.get("date") or "")[:10]
            c = A.fnum(r.get("close"))
            if d and d <= SB.SCREEN_END and c and c > 0:
                out[d] = c
    return sorted(out.items())


def factor_returns(bars):
    """([dates], [log returns]) dated on the later bar of each pair."""
    dates = [bars[k][0] for k in range(1, len(bars))]
    vals = [math.log(bars[k][1] / bars[k - 1][1])
            for k in range(1, len(bars))]
    return dates, vals


def lagged(fdates, fvals, d):
    """Latest factor return dated strictly before d, or None."""
    k = bisect.bisect_left(fdates, d)
    return fvals[k - 1] if k > 0 else None


def mv_before(fdates, fvals, d):
    """EWMA 0.94 volatility over the last EW_WINDOW factor returns dated
    strictly before d, or None."""
    e = bisect.bisect_left(fdates, d)
    return R._ewma(fvals[max(0, e - EW_WINDOW):e])


def screen_pairs(by_t, factor_bars, step=SB.STEP, min_hist=SB.MIN_HIST,
                 regime=None):
    """{factor: [pair]} (pair shape as screen_band_models)."""
    out = {k: [] for k in factor_bars}
    rets = {t: MF.log_returns(b) for t, b in by_t.items()}
    for fk, fbars in factor_bars.items():
        fd, fv = factor_returns(fbars)
        for t, bars in sorted(by_t.items()):
            if len(bars) < min_hist + 1:
                continue
            closes = [b[1] for b in bars]
            for h in HORIZONS:
                n = R.SESSIONS[h]
                i = min_hist
                while i + n <= len(bars):
                    rg = SB.regime_of(bars, i, n)
                    if rg is None or (regime and rg != regime):
                        i += step
                        continue
                    dts = [bars[k][0] for k in range(i - SB.LOOKBACK, i)]
                    if i - SB.LOOKBACK < 1 or any(
                            d not in rets[t] for d in dts):
                        i += step
                        continue
                    m60 = [lagged(fd, fv, d) for d in dts]
                    if None in m60:
                        i += step
                        continue
                    r60 = [rets[t][d] for d in dts]
                    s60 = R._sd(r60)
                    mv = mv_before(fd, fv, bars[i - 1][0])
                    sig = MF.sigma_from(r60, m60, mv) \
                        if (mv is not None and s60) else None
                    if s60 and sig:
                        real = (closes[i + n - 1] / closes[i - 1] - 1) * 100
                        v2 = R.half_pct(s60, h, ens_mod.V2_BAND_K[h])
                        nv = R.half_pct(s60, h, 1.2816)
                        half = R.half_pct(sig, h, ens_mod.V2_BAND_K[h])
                        out[fk].append({
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
    L = ["SCREEN of global-factor band models on long history (Yahoo "
         "close, windows end <= %s), frozen v2 k, descriptive only%s"
         % (SB.SCREEN_END, title)]
    for k in FACTORS:
        L.append("")
        L.append("factor %s" % k)
        for h in HORIZONS:
            c = results[k][h]
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


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.
                                 RawDescriptionHelpFormatter)
    ap.add_argument("--history", required=True)
    ap.add_argument("--factors", required=True)
    ap.add_argument("--regime", choices=REGIMES, default=None)
    ap.add_argument("--reps", type=int, default=2000)
    ap.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    by_t = MF.load(a.history)
    fb = {k: read_factor(os.path.join(a.factors, fn))
          for k, fn in FACTORS.items()}
    regimes = [a.regime] if a.regime else list(REGIMES)
    allres, readings = {}, {}
    for rg in regimes:
        pairs = screen_pairs(by_t, fb, regime=rg)
        allres[rg] = {k: R.evaluate(pairs[k], a.reps) for k in FACTORS}
        for k in FACTORS:
            for h in HORIZONS:
                readings[(k, h, rg)] = SB.reading_p(
                    [p for p in pairs[k] if p["horizon"] == h], a.reps)
        print(render(allres[rg], ", regime %s" % rg))
        print()
    adj = SB.holm_adjust(readings, m=FAMILY_SIZE)
    rows = [{"factor": k[0], "horizon": k[1], "regime": k[2],
             "p": readings[k], "holm_adj_p": adj.get(k)}
            for k in sorted(readings)]
    print("MULTIPLE TESTING: Holm over %d readings (one-sided p for "
          "RangeSkill <= 0, cutoff-clustered bootstrap); numbers only"
          % FAMILY_SIZE)
    for r in rows:
        print("  %s %s %s: p %s  Holm-adjusted p %s"
              % (r["factor"], r["regime"], r["horizon"], _f(r["p"]),
                 _f(r["holm_adj_p"])))
    print("tickers: %d, factor bars: %s" % (len(by_t), ", ".join(
        "%s %d (last %s)" % (k, len(v), v[-1][0] if v else "n/a")
        for k, v in fb.items())))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump({"descriptive": True,
                       "source": "yahoo close EEM BZ=F GC=F",
                       "estimator": "ewma0.94 over 250 lagged factor "
                                    "returns",
                       "regimes": {rg: dict(rr)
                                   for rg, rr in allres.items()},
                       "holm": {"family_size": FAMILY_SIZE,
                                "readings": rows}}, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
