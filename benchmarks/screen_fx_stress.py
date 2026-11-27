#!/usr/bin/env python3
"""Proposal A screen: USD/EGP stress as a band-width input
(INS-IMPROVE-001 round 26). DESCRIPTIVE ONLY, never a verdict.

Provenance: the GO for proposal A (implement, pre-register, screen,
descriptive, no cells scored, Holm over betas x horizons x regimes) is
Muhammad's, relayed in Slack message 1795739487.837839. Proposal text:
docs/proposals-round-25.md.

PRE-REGISTRATION (written before this screen was run):
Source: Yahoo close of EGP=X (USD/EGP market quote, not the CBE official
rate), evaluation/external_factors/EGP_X.csv, cut at 2023-12-28. Tickers:
the 36 EGX Yahoo closes (screen_market_factor.load), NVDA excluded.
Feature: s_t = population stdev of the 20 most recent EGP=X daily log
returns, using only EGP=X closes dated STRICTLY BEFORE the cutoff date D
(the latest bar dated < D is the last one used). x = log(s_t). z =
standardised x against the same ticker's EARLIER pseudo-cutoffs of the same
horizon grid (population mean and stdev, >= 8 earlier, else z = 0; sd 0
gives z = 0), exactly as screen_news_width. Band: half = V2_BAND_K[h] x
s60 x sqrt(sessions) x 100 x exp(beta x clip(z, -3, 3)). beta is a fixed
grid BETAS = (0.10, 0.20), directional (stress widens), NOT fitted; beta
= 0 is frozen v2 (tested). Family: 2 betas x 3 horizons x 2 regimes = 12,
one-sided cutoff-clustered bootstrap p (Phipson-Smyth +1), Holm over 12.
Windows end <= 2023-12-28, pseudo-cutoffs every 21 sessions after 120
bars, 2021-09-05 regime split (pre and post separate), frozen v2 k.
Numbers only: no pass flag, nothing here is an adoption, no cell is
scored. Cell scoring of any reading needs its own pre-registered step.

Usage:
  python3 benchmarks/screen_fx_stress.py --history DIR --fx FILE
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
import screen_market_factor as MF  # noqa: E402
import screen_news_width as N  # noqa: E402
import ensemble as ens_mod  # noqa: E402
import backtest_score as bs  # noqa: E402

HORIZONS = A.HORIZONS
BETAS = N.BETAS
REGIMES = SB.REGIMES
FAMILY_SIZE = len(BETAS) * len(HORIZONS) * len(REGIMES)   # 12
STRESS_WINDOW = 20
_f = SB._f


def read_close_csv(path):
    """[(date, close)] oldest first, date <= SCREEN_END; columns date,
    close (the evaluation/external_factors layout)."""
    out = {}
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            d = str(r.get("date") or "")[:10]
            c = A.fnum(r.get("close"))
            if d and d <= SB.SCREEN_END and c and c > 0:
                out[d] = c
    return sorted(out.items())


def stress_series(bars):
    """([dates], [s]) where s[k] is the stdev of the STRESS_WINDOW log
    returns ending at bars[k] (needs STRESS_WINDOW returns)."""
    dates, vals = [], []
    rets = [math.log(bars[k][1] / bars[k - 1][1])
            for k in range(1, len(bars))]
    for k in range(STRESS_WINDOW, len(rets) + 1):
        s = R._sd(rets[k - STRESS_WINDOW:k])
        if s is not None and s > 0:
            dates.append(bars[k][0])
            vals.append(s)
    return dates, vals


def stress_before(dates, vals, d):
    """Latest stress value from a bar dated strictly before d, or None."""
    k = bisect.bisect_left(dates, d)
    return vals[k - 1] if k > 0 else None


def screen_pairs(by_t, fx_bars, step=SB.STEP, min_hist=SB.MIN_HIST,
                 regime=None):
    """{beta: [pair]} (pair shape as screen_band_models)."""
    sd, sv = stress_series(fx_bars)
    out = {b: [] for b in BETAS}
    for t, bars in sorted(by_t.items()):
        closes = [b[1] for b in bars]
        rets = MF.log_returns(bars)
        for h in HORIZONS:
            n = R.SESSIONS[h]
            prior = []
            i = min_hist
            while i + n <= len(bars):
                d = bars[i - 1][0]
                s = stress_before(sd, sv, d)
                z = 0.0
                if s is not None:
                    x = math.log(s)
                    z = N.zscore(x, prior)
                    prior.append(x)   # only AFTER z used it
                rg = SB.regime_of(bars, i, n)
                if rg is None or (regime and rg != regime):
                    i += step
                    continue
                r60 = [rets[bars[k][0]] for k in range(i - SB.LOOKBACK, i)
                       if bars[k][0] in rets]
                s60 = R._sd(r60) if len(r60) == SB.LOOKBACK else None
                if s60:
                    real = (closes[i + n - 1] / closes[i - 1] - 1) * 100
                    v2 = R.half_pct(s60, h, ens_mod.V2_BAND_K[h])
                    nv = R.half_pct(s60, h, 1.2816)
                    for b in BETAS:
                        half = v2 * N.multiplier(b, z)
                        out[b].append({
                            "ticker": t, "as_of": d, "horizon": h,
                            "regime": rg, "z_fx": z,
                            "is_naive": bs.winkler_is(real, -nv, nv),
                            "is_v2": bs.winkler_is(real, -v2, v2),
                            "is_ch": bs.winkler_is(real, -half, half),
                            "in_v2": abs(real) <= v2,
                            "in_ch": abs(real) <= half})
                i += step
    return out


def render(results, title=""):
    L = ["SCREEN of USD/EGP stress band width on long history (Yahoo "
         "close, windows end <= %s), frozen v2 k, descriptive only%s"
         % (SB.SCREEN_END, title)]
    for b in BETAS:
        L.append("")
        L.append("beta %.2f" % b)
        for h in HORIZONS:
            c = results[b][h]
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
    ap.add_argument("--fx", required=True)
    ap.add_argument("--regime", choices=REGIMES, default=None)
    ap.add_argument("--reps", type=int, default=2000)
    ap.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    by_t = MF.load(a.history)
    fx = read_close_csv(a.fx)
    regimes = [a.regime] if a.regime else list(REGIMES)
    allres, readings = {}, {}
    for rg in regimes:
        pairs = screen_pairs(by_t, fx, regime=rg)
        allres[rg] = {b: R.evaluate(pairs[b], a.reps) for b in BETAS}
        for b in BETAS:
            for h in HORIZONS:
                readings[(b, h, rg)] = SB.reading_p(
                    [p for p in pairs[b] if p["horizon"] == h], a.reps)
        print(render(allres[rg], ", regime %s" % rg))
        print()
    adj = SB.holm_adjust(readings, m=FAMILY_SIZE)
    rows = [{"beta": k[0], "horizon": k[1], "regime": k[2],
             "p": readings[k], "holm_adj_p": adj.get(k)}
            for k in sorted(readings)]
    print("MULTIPLE TESTING: Holm over %d readings (one-sided p for "
          "RangeSkill <= 0, cutoff-clustered bootstrap); numbers only"
          % FAMILY_SIZE)
    for r in rows:
        print("  beta %.2f %s %s: p %s  Holm-adjusted p %s"
              % (r["beta"], r["regime"], r["horizon"], _f(r["p"]),
                 _f(r["holm_adj_p"])))
    print("tickers: %d, EGP=X bars: %d (last %s)"
          % (len(by_t), len(fx), fx[-1][0] if fx else "n/a"))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump({"descriptive": True, "source": "yahoo close EGP=X",
                       "betas": list(BETAS), "stress_window": STRESS_WINDOW,
                       "regimes": {rg: {"%.2f" % b: v
                                        for b, v in rr.items()}
                                   for rg, rr in allres.items()},
                       "holm": {"family_size": FAMILY_SIZE,
                                "readings": rows}}, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
