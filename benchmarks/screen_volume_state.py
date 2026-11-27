#!/usr/bin/env python3
"""Proposal B screen: volume state as a band-width input
(INS-IMPROVE-001 round 30, proposal B of docs/proposals-round-26.md).
DESCRIPTIVE ONLY, never a verdict.

Provenance: the GO for this screen (pre-registered, family 12,
descriptive, no cells scored, sequenced after the paired-delta screen,
paired-delta statistic reported next to the existing p) is Muhammad's,
relayed in Slack message 1795742631.225549 (read by the author). The
holiday-bar rule below and the order "pre-register first, then run" are
Moos's rulings as relayed by the parent agent (Slack 1795743522.937609
per the relay; the author could not find that message in the loop thread
or the channel and cites it as relayed, not as read).

PRE-REGISTRATION (written before this screen was run):
Data: ohlcv/yahoo/*_CA.csv Yahoo CLOSE (raw) and VOLUME (daily share
count) of the EGX tickers as screen_market_factor; bars after 2023-12-28
are dropped; the 2021-09-05 regime split is mandatory (pre/post evaluated
separately). Volume is a column of the same bar as the close.
Point-in-time: at a pseudo-cutoff with as_of date D (the date of the
last bar the other screens may use) only bars dated STRICTLY BEFORE D are
used, for eligibility and for the feature.
Eligibility, per cutoff (specified by this document, from the #852
review): a ticker enters a cutoff only if at least 90% of its last 120
bars (SB.MIN_HIST) dated before D have volume > 0. A cutoff that fails
is skipped for that ticker and horizon and contributes nothing to the
ticker's earlier-cutoff history. No bar on or after D qualifies or
disqualifies a cutoff.
Holiday bars (ruling relayed as above): the store carries zero-volume
bars with a carried close on some market holidays. A MARKET-WIDE
ZERO-VOLUME DAY is a date on which at least ZERO_DAY_MIN_NAMES = 10
tickers have a bar and at least ZERO_DAY_SHARE = 90% of those bars have
volume 0 (an unreadable volume counts as 0); the definition uses only
that date's own bars, so it is point in time. These days are EXCLUDED
from the 20-bar mean below and are KEPT in the eligibility count above
(a market-wide zero-volume bar counts as a zero-volume bar there). A
ticker's own zero-volume days that are not market-wide stay in the mean.
If every bar of the 20-bar window is a market-wide zero-volume day, the
cutoff is skipped for that ticker and horizon (specified by this
document).
Feature: x = log(1 + mean volume over the bars of the last 20 bars dated
before D that are not market-wide zero-volume days; the divisor is the
number of bars kept).
z = x standardised against the same ticker's and horizon's EARLIER
eligible cutoffs (population mean and stdev, at least 8 earlier
cutoffs, else z = 0; screen_news_width.zscore, near-constant history
gives z = 0). Band = frozen v2 half-width x exp(beta x clip(z, -3, 3)),
beta in the fixed grid (0.10, 0.20), not fitted; beta 0 is exactly v2
(tested). Family: 2 betas x 3 horizons x 2 regimes = 12, fixed whatever
--regime selects. Per reading: (a) the existing one-sided cutoff-clustered
bootstrap p for RangeSkill <= 0 (Phipson-Smyth +1), Holm over 12; and
(b) the paired delta RangeSkill(candidate) - RangeSkill(v2) on the same
rows with its 95% interval and one-sided p (screen_delta_vs_v2.reading),
Holm over 12. Numbers only, no pass flag, no verdict. Cells 48-90 and
91+ are NOT scored here; a cell scoring needs its own pre-registered
step. Volume is the names' own series, not an outside source; thinly
traded names are removed by the eligibility rule, not by hand.

The EGX holiday calendar is NOT used and no holiday list is assumed;
only the zero-volume rule above is.

Usage:
  python3 benchmarks/screen_volume_state.py --history DIR
      [--regime pre|post] [--reps N] [--json OUT]
"""
import argparse
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
import screen_delta_vs_v2 as D  # noqa: E402
import screen_market_factor as MF  # noqa: E402
import screen_news_width as N  # noqa: E402
import ensemble as ens_mod  # noqa: E402
import backtest_score as bs  # noqa: E402

HORIZONS = A.HORIZONS
BETAS = N.BETAS
REGIMES = SB.REGIMES
FAMILY_SIZE = len(BETAS) * len(HORIZONS) * len(REGIMES)   # 12
VOL_WINDOW = 20
ELIG_BARS = SB.MIN_HIST          # 120
ELIG_SHARE = 0.90
ZERO_DAY_MIN_NAMES = 10
ZERO_DAY_SHARE = 0.90
_f = SB._f


def read_bars(path):
    """[(date, close, volume)] oldest first, date <= SCREEN_END, same
    close filter as MF.read_closes; volume is None when unreadable."""
    out = {}
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            d = str(r.get("date") or "")[:10]
            c = A.fnum(r.get("close"))
            if d and d <= SB.SCREEN_END and c and c > 0:
                v = A.fnum(r.get("volume"))
                out[d] = (c, v if v is not None and v >= 0 else 0.0)
    return [(d, c, v) for d, (c, v) in sorted(out.items())]


def zero_days(vols_by_date):
    """{date} market-wide zero-volume days from {date: [volume, ...]}:
    at least ZERO_DAY_MIN_NAMES bars and >= ZERO_DAY_SHARE of them 0."""
    return {d for d, vs in vols_by_date.items()
            if len(vs) >= ZERO_DAY_MIN_NAMES
            and sum(1 for v in vs if v <= 0) >= ZERO_DAY_SHARE * len(vs)}


def load(history_dir):
    """({ticker: [(date, close)]}, {ticker: [volume]} aligned by index,
    {market-wide zero-volume dates})."""
    by_t, vols, per_date = {}, {}, {}
    for fn in sorted(os.listdir(history_dir)):
        if fn.upper().endswith("_CA.CSV"):
            t = os.path.splitext(fn)[0].upper()
            rows = read_bars(os.path.join(history_dir, fn))
            by_t[t] = [(d, c) for d, c, _ in rows]
            vols[t] = [v for _, _, v in rows]
            for d, _, v in rows:
                per_date.setdefault(d, []).append(v)
    return by_t, vols, zero_days(per_date)


def volume_state(vols, dates, zero, i):
    """(eligible, x) at a cutoff whose as_of bar is index i-1: only bars
    0 .. i-2 (dated strictly before as_of) are used. Eligibility counts
    the 120 bars ending at i-2 (market-wide zero days included); the
    feature is log1p of the mean of the last 20 of those bars that are
    not market-wide zero-volume days."""
    hi = i - 1
    lo = hi - ELIG_BARS
    if lo < 0:
        return False, None
    if sum(1 for v in vols[lo:hi] if v > 0) < ELIG_SHARE * ELIG_BARS:
        return False, None
    kept = [vols[k] for k in range(hi - VOL_WINDOW, hi)
            if dates[k] not in zero]
    if not kept:
        return False, None
    return True, math.log1p(sum(kept) / len(kept))


def screen_pairs(by_t, vols, zero, step=SB.STEP, min_hist=SB.MIN_HIST,
                 regime=None):
    """{beta: [pair]} (pair shape as screen_band_models)."""
    out = {b: [] for b in BETAS}
    for t, bars in sorted(by_t.items()):
        closes = [b[1] for b in bars]
        rets = MF.log_returns(bars)
        tv = vols[t]
        dates = [b[0] for b in bars]
        for h in HORIZONS:
            n = R.SESSIONS[h]
            prior = []
            i = min_hist
            while i + n <= len(bars):
                d = bars[i - 1][0]
                ok, x = volume_state(tv, dates, zero, i)
                if not ok:
                    i += step
                    continue
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
                            "regime": rg, "z_vol": z,
                            "is_naive": bs.winkler_is(real, -nv, nv),
                            "is_v2": bs.winkler_is(real, -v2, v2),
                            "is_ch": bs.winkler_is(real, -half, half),
                            "in_v2": abs(real) <= v2,
                            "in_ch": abs(real) <= half})
                i += step
    return out


def render(results, deltas, title=""):
    L = ["SCREEN of volume-state band width on long history (Yahoo close "
         "and volume, windows end <= %s), frozen v2 k, descriptive only%s"
         % (SB.SCREEN_END, title)]
    for b in BETAS:
        L.append("")
        L.append("beta %.2f" % b)
        for h in HORIZONS:
            c, d = results[b][h], deltas[(b, h)]
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
            L.append("    delta vs v2 %s (CI cutoff [%s, %s])"
                     % (_f(d["delta"]), _f(d["ci"][0]), _f(d["ci"][1])))
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
    by_t, vols, zero = load(a.history)
    regimes = [a.regime] if a.regime else list(REGIMES)
    allres, p_exist, deltas = {}, {}, {}
    for rg in regimes:
        pairs = screen_pairs(by_t, vols, zero, regime=rg)
        allres[rg] = {b: R.evaluate(pairs[b], a.reps) for b in BETAS}
        dl = {}
        for b in BETAS:
            for h in HORIZONS:
                hp = [p for p in pairs[b] if p["horizon"] == h]
                p_exist[(b, h, rg)] = SB.reading_p(hp, a.reps)
                dl[(b, h)] = D.reading(hp, a.reps)
                deltas[(b, h, rg)] = dl[(b, h)]
        print(render(allres[rg], dl, ", regime %s" % rg))
        print()
    adj = SB.holm_adjust(p_exist, m=FAMILY_SIZE)
    adj_d = SB.holm_adjust({k: v["p"] for k, v in deltas.items()},
                           m=FAMILY_SIZE)
    rows = [{"beta": k[0], "horizon": k[1], "regime": k[2],
             "p": p_exist[k], "holm_adj_p": adj.get(k),
             "delta": deltas[k]["delta"], "delta_ci": deltas[k]["ci"],
             "delta_p": deltas[k]["p"], "delta_holm_adj_p": adj_d.get(k)}
            for k in sorted(p_exist)]
    print("MULTIPLE TESTING: Holm over %d readings; p = RangeSkill <= 0, "
          "delta p = delta vs v2 <= 0 (cutoff-clustered bootstrap); "
          "numbers only" % FAMILY_SIZE)
    for r in rows:
        print("  beta %.2f %s %s: p %s Holm %s | delta %s p %s Holm %s"
              % (r["beta"], r["regime"], r["horizon"], _f(r["p"]),
                 _f(r["holm_adj_p"]), _f(r["delta"]), _f(r["delta_p"]),
                 _f(r["delta_holm_adj_p"])))
    print("tickers loaded: %d, market-wide zero-volume days: %d"
          % (len(by_t), len(zero)))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump({"descriptive": True,
                       "source": "yahoo close and volume",
                       "betas": list(BETAS), "vol_window": VOL_WINDOW,
                       "eligibility": {"bars": ELIG_BARS,
                                       "min_share": ELIG_SHARE},
                       "zero_days": {"count": len(zero),
                                     "min_names": ZERO_DAY_MIN_NAMES,
                                     "share": ZERO_DAY_SHARE},
                       "regimes": {rg: {"%.2f" % b: v
                                        for b, v in rr.items()}
                                   for rg, rr in allres.items()},
                       "holm": {"family_size": FAMILY_SIZE,
                                "readings": rows}}, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
