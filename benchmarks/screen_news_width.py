#!/usr/bin/env python3
"""Route 1 harness: GDELT GKG news volume as a band-width input
(INS-IMPROVE-001 round 24 item 3). DESCRIPTIVE ONLY, never a verdict.

STATUS: harness only. It is tested on synthetic fixtures. It has NOT
been run on real GDELT matches (the full 2019-2026 run has not landed),
and no cell is scored by it. Provenance: the GO for the harness against a
synthetic news fixture is Muhammad's, relayed in Slack message
1795737001.782279 (no cells scored until the real matches land and the
point-in-time check is verified).

PRE-REGISTRATION (before any real run):
Input: matches.jsonl from scripts/gdelt_gkg_filter.py (fields used:
date = GKG timestamp YYYYMMDDHHMMSS UTC, tickers = list). Prices: Yahoo
close store, as screen_market_factor.
Point-in-time rule (conservative, DST-independent): a match counts at a
cutoff only if its GKG timestamp is strictly before 00:00:00 UTC of the
cutoff's calendar day, i.e. it was published on an earlier day than the
cutoff session. This is stricter than "before the EGX close" and
replaces it until the exact close time is verified against GKG
timestamps; verifying that is a prerequisite for any real run.
Feature: x = log(1 + matches for the ticker in the 7 calendar days before
the cutoff day, rule above). z = standardised x against the same
ticker's EARLIER pseudo-cutoffs of the same horizon grid (population
mean and stdev, at least 8 earlier cutoffs, else z = 0; sd 0 gives z = 0).
Band: half = V2_BAND_K[h] x s60 x sqrt(sessions) x 100 x
exp(beta x clip(z, -3, 3)); the multiplier is always positive and beta =
0 is exactly frozen v2 (tested). Beta is NOT fitted: the family is the
fixed grid BETAS = (0.10, 0.20) x 3 horizons x 2 regimes = 12 readings,
one-sided cutoff-clustered bootstrap p (Phipson-Smyth +1), Holm over 12.
Windows end <= 2023-12-28, the 2021-09-05 regime split applies (pre and
post evaluated separately), pseudo-cutoffs every 21 sessions after 120
bars, as the other screens. Numbers only: no pass flag, nothing here is
an adoption.

Usage:
  python3 benchmarks/screen_news_width.py --history DIR --matches FILE
      [--reps N] [--json OUT]
"""
import argparse
import bisect
import datetime as dt
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
BETAS = (0.10, 0.20)
REGIMES = SB.REGIMES
FAMILY_SIZE = len(BETAS) * len(HORIZONS) * len(REGIMES)   # 12
WINDOW_DAYS = 7
MIN_PRIOR = 8
Z_CLIP = 3.0
_f = SB._f


def load_matches(path):
    """{ticker: sorted [timestamp str]}; unreadable lines are skipped
    and counted (binary read, per-line decode)."""
    by_t, bad = {}, 0
    with open(path, "rb") as f:
        for raw in f:
            try:
                r = json.loads(raw.decode("utf-8"))
                ts = str(r["date"])
                tickers = list(r["tickers"])
            except (UnicodeDecodeError, ValueError, KeyError, TypeError):
                bad += 1
                continue
            for t in tickers:
                by_t.setdefault(t, []).append(ts)
    return {t: sorted(v) for t, v in by_t.items()}, bad


def window_count(stamps, cutoff_date):
    """Matches with 7 days before the cutoff day <= timestamp < 00:00:00
    UTC of the cutoff day (point-in-time rule)."""
    day = dt.date.fromisoformat(cutoff_date)
    hi = day.strftime("%Y%m%d") + "000000"
    lo = (day - dt.timedelta(days=WINDOW_DAYS)).strftime("%Y%m%d") + "000000"
    return bisect.bisect_left(stamps, hi) - bisect.bisect_left(stamps, lo)


def zscore(x, prior):
    if len(prior) < MIN_PRIOR:
        return 0.0
    mu = sum(prior) / len(prior)
    sd = math.sqrt(sum((v - mu) ** 2 for v in prior) / len(prior))
    return 0.0 if sd == 0 else (x - mu) / sd


def multiplier(beta, z):
    return math.exp(beta * max(-Z_CLIP, min(Z_CLIP, z)))


def ticker_key(t):
    """store file stem 'ABCD_CA' -> match ticker 'ABCD.CA'."""
    return t.replace("_CA", ".CA")


def screen_pairs(by_t, news, step=SB.STEP, min_hist=SB.MIN_HIST,
                 regime=None):
    """{beta: [pair]} (pair shape as screen_band_models)."""
    out = {b: [] for b in BETAS}
    for t, bars in sorted(by_t.items()):
        stamps = news.get(ticker_key(t), [])
        closes = [b[1] for b in bars]
        rets = MF.log_returns(bars)
        for h in HORIZONS:
            n = R.SESSIONS[h]
            prior = []
            i = min_hist
            while i + n <= len(bars):
                d = bars[i - 1][0]
                x = math.log1p(window_count(stamps, d))
                z = zscore(x, prior)
                prior.append(x)       # only AFTER z used it
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
                        half = v2 * multiplier(b, z)
                        out[b].append({
                            "ticker": t, "as_of": d, "horizon": h,
                            "regime": rg, "z_news": z,
                            "is_naive": bs.winkler_is(real, -nv, nv),
                            "is_v2": bs.winkler_is(real, -v2, v2),
                            "is_ch": bs.winkler_is(real, -half, half),
                            "in_v2": abs(real) <= v2,
                            "in_ch": abs(real) <= half})
                i += step
    return out


def render(results, title=""):
    L = ["SCREEN of news-volume band width on long history (Yahoo close, "
         "windows end <= %s), frozen v2 k, descriptive only%s"
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
    ap.add_argument("--matches", required=True)
    ap.add_argument("--regime", choices=REGIMES, default=None)
    ap.add_argument("--reps", type=int, default=2000)
    ap.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    by_t = MF.load(a.history)
    news, bad = load_matches(a.matches)
    regimes = [a.regime] if a.regime else list(REGIMES)
    allres, readings = {}, {}
    for rg in regimes:
        pairs = screen_pairs(by_t, news, regime=rg)
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
    for r in rows:
        print("  beta %.2f %s %s: p %s  Holm-adjusted p %s"
              % (r["beta"], r["regime"], r["horizon"], _f(r["p"]),
                 _f(r["holm_adj_p"])))
    print("tickers: %d, tickers with matches: %d, unreadable match "
          "lines: %d" % (len(by_t), len(news), bad))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump({"descriptive": True, "betas": list(BETAS),
                       "regimes": {rg: {"%.2f" % b: v
                                        for b, v in rr.items()}
                                   for rg, rr in allres.items()},
                       "holm": {"family_size": FAMILY_SIZE, "readings":
                                rows}, "unreadable_match_lines": bad},
                      fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
