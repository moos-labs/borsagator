#!/usr/bin/env python3
"""Diagnostic: effect of market-wide zero-volume days on the 60-session
sigma (s60) that frozen v2 uses (INS-IMPROVE-001 round 30, item 2).
DESCRIPTIVE ONLY: it measures a number, it scores no cell and fits
nothing.

Provenance: the order to measure this difference as a number (not assume
it) is Moos's ruling as relayed by the parent agent (Slack
1795743522.937609 per the relay; the author could not find that message
in the loop thread or the channel and cites it as relayed, not as read).

PRE-REGISTRATION (written before this diagnostic was run):
Data: ohlcv/yahoo/*_CA.csv Yahoo close (raw) and volume, bars after
2023-12-28 dropped, the 2021-09-05 regime split applied (pre/post
reported separately), pseudo-cutoffs on the same grid as the screens
(first at MIN_HIST = 120 bars, every STEP = 21 sessions, one grid per
horizon as screen_band_models.screen_pairs, regime by
screen_band_models.regime_of).
Market-wide zero-volume day (same rule as benchmarks/screen_volume_state.py):
a date with >= 10 tickers having a bar and >= 90% of those bars with
volume 0 (unreadable volume counts as 0).
s60 WITH: the screens' own s60 = population stdev of the 60 log returns
of the bars dated before as_of (screen_band_models.LOOKBACK, same series
and same _sd as replay_band_candidates), a cutoff needs all 60 returns.
s60 WITHOUT: the same 60-return window with the returns dated on a
market-wide zero-volume day removed, stdev of the rest; at least 30
returns must remain, else the cutoff is counted as undefined and left
out of the without-comparison. (The return on the first session after a
zero-volume day is kept: it carries the move across the closure.)
Statistic: per cutoff ratio = s60 WITHOUT / s60 WITH - 1. Reported per
horizon and regime: number of cutoffs, share of cutoffs whose window
contains at least one market-wide zero-volume day, mean and median of the
ratio over ALL cutoffs, mean and median over the AFFECTED cutoffs only,
min and max. The v2 half-width is k x s60, so the width changes by the
same ratio. No expectation is encoded and no threshold is applied.

Usage:
  python3 benchmarks/diag_s60_zero_volume_days.py --history DIR
      [--json OUT]
"""
import argparse
import csv
import json
import os
import statistics
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

HORIZONS = A.HORIZONS
REGIMES = SB.REGIMES
ZERO_DAY_MIN_NAMES = 10
ZERO_DAY_SHARE = 0.90
MIN_KEPT = 30
_f = lambda v: "n/a" if v is None else "%+.4f" % v  # noqa: E731


def read_volumes(path):
    """{date: volume} on the bars MF.read_closes keeps (close > 0, date
    <= SCREEN_END); unreadable volume is 0."""
    out = {}
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            d = str(r.get("date") or "")[:10]
            c = A.fnum(r.get("close"))
            if d and d <= SB.SCREEN_END and c and c > 0:
                v = A.fnum(r.get("volume"))
                out[d] = v if v is not None and v >= 0 else 0.0
    return out


def zero_days(vols_by_date):
    """{date} from {date: [volume, ...]}."""
    return {d for d, vs in vols_by_date.items()
            if len(vs) >= ZERO_DAY_MIN_NAMES
            and sum(1 for v in vs if v <= 0) >= ZERO_DAY_SHARE * len(vs)}


def load(history_dir):
    by_t, per_date = {}, {}
    for fn in sorted(os.listdir(history_dir)):
        if fn.upper().endswith("_CA.CSV"):
            t = os.path.splitext(fn)[0].upper()
            p = os.path.join(history_dir, fn)
            by_t[t] = MF.read_closes(p)
            for d, v in read_volumes(p).items():
                per_date.setdefault(d, []).append(v)
    return by_t, zero_days(per_date)


def s60_pair(bars, rets, zero, i):
    """(with, without) s60 at a cutoff whose as_of bar is index i-1, or
    (None, None) when the with-window is incomplete; without is None
    when fewer than MIN_KEPT returns remain."""
    ds = [bars[k][0] for k in range(i - SB.LOOKBACK, i)]
    r60 = [rets[d] for d in ds if d in rets]
    if len(r60) != SB.LOOKBACK:
        return None, None
    kept = [rets[d] for d in ds if d not in zero]
    wo = R._sd(kept) if len(kept) >= MIN_KEPT else None
    return R._sd(r60), wo


def cutoff_ratios(by_t, zero, step=SB.STEP, min_hist=SB.MIN_HIST):
    """[{horizon, regime, ratio|None, affected}] over every cutoff."""
    out = []
    for t, bars in sorted(by_t.items()):
        rets = MF.log_returns(bars)
        for h in HORIZONS:
            n = R.SESSIONS[h]
            i = min_hist
            while i + n <= len(bars):
                rg = SB.regime_of(bars, i, n)
                w, wo = s60_pair(bars, rets, zero, i)
                if rg is not None and w:
                    aff = any(bars[k][0] in zero
                              for k in range(i - SB.LOOKBACK, i))
                    out.append({"horizon": h, "regime": rg,
                                "affected": aff,
                                "ratio": (wo / w - 1.0) if wo is not None
                                else None})
                i += step
    return out


def summarize(rows):
    """{(horizon, regime): stats} from cutoff_ratios rows."""
    res = {}
    for h in HORIZONS:
        for rg in REGIMES:
            sub = [r for r in rows if r["horizon"] == h
                   and r["regime"] == rg]
            defined = [r["ratio"] for r in sub if r["ratio"] is not None]
            aff = [r["ratio"] for r in sub
                   if r["affected"] and r["ratio"] is not None]
            res[(h, rg)] = {
                "cutoffs": len(sub),
                "undefined_without": len(sub) - len(defined),
                "affected_share": (sum(1 for r in sub if r["affected"])
                                   / len(sub)) if sub else None,
                "mean_all": statistics.fmean(defined) if defined else None,
                "median_all": statistics.median(defined) if defined
                else None,
                "affected_n": len(aff),
                "mean_affected": statistics.fmean(aff) if aff else None,
                "median_affected": statistics.median(aff) if aff
                else None,
                "min": min(defined) if defined else None,
                "max": max(defined) if defined else None}
    return res


def render(res, nzero):
    L = ["s60 WITHOUT market-wide zero-volume days relative to s60 WITH "
         "(ratio - 1; Yahoo close and volume, windows end <= %s), "
         "descriptive only; %d market-wide zero-volume days"
         % (SB.SCREEN_END, nzero)]
    for (h, rg), s in sorted(res.items()):
        L.append("  %s %s: cutoffs=%d (without undefined %d) affected "
                 "share %s | all: mean %s median %s | affected (n=%d): "
                 "mean %s median %s | min %s max %s"
                 % (h, rg, s["cutoffs"], s["undefined_without"],
                    _f(s["affected_share"]), _f(s["mean_all"]),
                    _f(s["median_all"]), s["affected_n"],
                    _f(s["mean_affected"]), _f(s["median_affected"]),
                    _f(s["min"]), _f(s["max"])))
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.
                                 RawDescriptionHelpFormatter)
    ap.add_argument("--history", required=True)
    ap.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    by_t, zero = load(a.history)
    res = summarize(cutoff_ratios(by_t, zero))
    print(render(res, len(zero)))
    print("tickers loaded: %d" % len(by_t))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump({"descriptive": True,
                       "source": "yahoo close and volume",
                       "zero_days": {"count": len(zero),
                                     "min_names": ZERO_DAY_MIN_NAMES,
                                     "share": ZERO_DAY_SHARE},
                       "min_kept": MIN_KEPT,
                       "readings": [dict(horizon=h, regime=rg, **s)
                                    for (h, rg), s in sorted(res.items())]},
                      fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
