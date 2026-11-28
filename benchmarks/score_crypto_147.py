#!/usr/bin/env python3
"""Round 147 crypto track, first scoring: DESCRIPTIVE run of frozen v2
against the naive range on BTC-USD and ETH-USD
(docs/round147_crypto_track_prereg.md; dispatch INS-IMPROVE-160).
Stdlib only. No verdict word, no KEEP.

"Frozen v2 on crypto" (defined here, before any scoring):
scripts/ensemble.py is an end-to-end pipeline (reads digest/collected
files, HORIZONS and V2_SESSIONS hard-coded 5/21 trading sessions), so it
cannot be run as-is for 1/7/30 sessions. This wrapper does NOT edit it:
it imports its frozen constants V2_BAND_K and V2_NAIVE_K and rebuilds the
same interval rule the horizon loop applies with the centre at 0:
  half = V2_BAND_K[h] x sigma60 x sqrt(sessions_h), range = 0 +/- half
with RISK_MULT 1.0 (no news digest on crypto) and no band calibration
(no ledger rows for crypto). sigma60 is the population stdev of the 60
daily log returns of the 61 closes ending at C-1 (ensemble.realized_sigma
sd()). Naive = 0 +/- V2_NAIVE_K x sigma60 x sqrt(sessions_h).
Sessions: day 1, week 7, month 30 (UTC calendar days, pre-reg s.3).
A row uses bars dated <= C-1; base = close of C-1; the realised close for
horizon h is the close of the bar dated C-1+h; realised move = simple
return in percent. Score = Winkler interval score at 80% (alpha 0.2),
scripts/backtest_score.winkler_is.
"""
import argparse
import csv
import datetime as dt
import json
import math
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import backtest_score as bs  # noqa: E402
import ensemble as ens  # noqa: E402

SESSIONS = {"day": 1, "week": 7, "month": 30}
ASSETS = ("BTC-USD", "ETH-USD")
WINDOW = (dt.date(2024, 1, 1), dt.date(2025, 12, 31))
SPACING = 30
MIN_HISTORY = 120
DEFAULT_SEED = 20261125
DEFAULT_REPS = 5000
LAUNCH_GATE = 0.10


def load(path):
    with open(path, newline="", encoding="utf-8") as f:
        return {dt.date.fromisoformat(r["date"]): float(r["close"])
                for r in csv.DictReader(f)}


def cutoffs(start=WINDOW[0], end=WINDOW[1], spacing=SPACING):
    out, c = [], start
    while c <= end:
        out.append(c)
        c += dt.timedelta(days=spacing)
    return out


def sigma60(closes, c):
    """Population stdev of 60 log returns, closes C-61..C-1. None when a
    bar in that span is missing."""
    d = [c - dt.timedelta(days=k) for k in range(61, 0, -1)]
    if any(x not in closes for x in d):
        return None
    v = [closes[x] for x in d]
    r = [math.log(v[i] / v[i - 1]) for i in range(1, len(v))]
    mu = sum(r) / len(r)
    return math.sqrt(sum((x - mu) ** 2 for x in r) / len(r))


def v2_half(h, s60):
    return ens.V2_BAND_K[h] * s60 * math.sqrt(SESSIONS[h])


def naive_half(h, s60):
    return ens.V2_NAIVE_K * s60 * math.sqrt(SESSIONS[h])


def inside(mv, half):
    return -half <= mv <= half


def build_rows(series, cuts):
    """series: {asset: {date: close}}. Returns (rows, excluded) with every
    excluded row listed individually (asset, cutoff, horizon, reason)."""
    rows, excl = [], []
    for a in sorted(series):
        cl = series[a]
        first = min(cl)
        for c in cuts:
            base_d = c - dt.timedelta(days=1)
            if (base_d - first).days + 1 < MIN_HISTORY:
                for h in SESSIONS:
                    excl.append((a, c.isoformat(), h, "history < 120 bars"))
                continue
            s = sigma60(cl, c)
            if s is None or base_d not in cl:
                for h in SESSIONS:
                    excl.append((a, c.isoformat(), h, "missing bar in sigma60 span"))
                continue
            base = cl[base_d]
            for h, n in SESSIONS.items():
                rd = base_d + dt.timedelta(days=n)
                if rd not in cl:
                    excl.append((a, c.isoformat(), h, "no realised close"))
                    continue
                mv = (cl[rd] / base - 1.0) * 100.0
                hv, hn = v2_half(h, s) * 100.0, naive_half(h, s) * 100.0
                rows.append({
                    "asset": a, "cutoff": c.isoformat(), "h": h,
                    "move": mv, "sigma60": s,
                    "is_v2": bs.winkler_is(mv, -hv, hv),
                    "is_naive": bs.winkler_is(mv, -hn, hn),
                    "in_v2": inside(mv, hv), "in_naive": inside(mv, hn)})
    return rows, excl


def skill(rs):
    n = sum(r["is_naive"] for r in rs)
    if not rs or n <= 0:
        return None
    return 1.0 - sum(r["is_v2"] for r in rs) / n


def cover(rs, key="in_v2"):
    return sum(r[key] for r in rs) / len(rs) if rs else None


def pct_ci(draws):
    if not draws:
        return None, None
    d = sorted(draws)
    return d[int(0.025 * len(d))], d[min(len(d) - 1, int(0.975 * len(d)))]


def boot(rs, reps=DEFAULT_REPS, seed=DEFAULT_SEED):
    """Cutoff-clustered percentile bootstrap: whole cutoff dates are
    resampled with replacement; every row of a drawn cutoff travels with
    it. Returns (skill_ci, coverage_ci, n_draws_skill_defined)."""
    by = {}
    for r in rs:
        by.setdefault(r["cutoff"], []).append(r)
    keys = sorted(by)
    if not keys:
        return (None, None), (None, None), 0
    rng = random.Random(seed)
    sk, cv = [], []
    for _ in range(reps):
        draw = []
        for _ in keys:
            draw.extend(by[rng.choice(keys)])
        s = skill(draw)
        if s is not None:
            sk.append(s)
        cv.append(cover(draw))
    return pct_ci(sk), pct_ci(cv), len(sk)


def summarise(rows, reps=DEFAULT_REPS, seed=DEFAULT_SEED):
    out = []
    for h in SESSIONS:
        for a in list(ASSETS) + ["BTC+ETH pooled"]:
            rs = [r for r in rows if r["h"] == h and
                  (a.startswith("BTC+") or r["asset"] == a)]
            if not rs:
                continue
            sci, cci, nd = boot(rs, reps, seed)
            out.append({
                "horizon": h, "sessions": SESSIONS[h], "asset": a,
                "n": len(rs), "clusters": len({r["cutoff"] for r in rs}),
                "rangeskill_v2_vs_naive": skill(rs),
                "rangeskill_ci95": list(sci),
                "coverage_v2": cover(rs), "coverage_ci95": list(cci),
                "coverage_naive": cover(rs, "in_naive"),
                "launch_gate_target": LAUNCH_GATE,
                "boot_draws_defined": nd})
    return out


def fmt(x, d=3):
    return "n/a" if x is None else ("%+.*f" % (d, x))


def render(res, excl, reps, seed):
    L = ["# Crypto round 147, first descriptive run (frozen v2 vs naive)", "",
         "Window: cutoffs %s to %s every %d days; reps %d, seed %d; "
         "cutoff-clustered 95%% percentile CIs. Descriptive: no verdict "
         "word, no KEEP. BTC+ETH pooled counts one cluster per cutoff." %
         (WINDOW[0], WINDOW[1], SPACING, reps, seed), "",
         "| horizon | asset | n | clusters | RangeSkill vs naive | CI95 | "
         "coverage v2 | coverage CI95 |", "|---|---|---|---|---|---|---|---|"]
    for r in res:
        L.append("| %s (%d) | %s | %d | %d | %s | [%s, %s] | %.3f | [%.3f, %.3f] |"
                 % (r["horizon"], r["sessions"], r["asset"], r["n"],
                    r["clusters"], fmt(r["rangeskill_v2_vs_naive"]),
                    fmt(r["rangeskill_ci95"][0]), fmt(r["rangeskill_ci95"][1]),
                    r["coverage_v2"], r["coverage_ci95"][0],
                    r["coverage_ci95"][1]))
    L += ["", "Launch-gate target +0.10, point estimate (reported separately "
          "from the loop CI bar; no label attached):"]
    for r in res:
        L.append("- %s %s: %s" % (r["horizon"], r["asset"],
                                  fmt(r["rangeskill_v2_vs_naive"])))
    L += ["", "Excluded rows (%d):" % len(excl)]
    for e in excl:
        L.append("- %s cutoff %s %s: %s" % e)
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=os.path.join(ROOT, "ohlcv", "yahoo"))
    ap.add_argument("--reps", type=int, default=DEFAULT_REPS)
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--out", default=None, help="prefix for .json/.md")
    a = ap.parse_args(argv)
    series = {s: load(os.path.join(a.data_dir, s + ".csv")) for s in ASSETS}
    rows, excl = build_rows(series, cutoffs())
    res = summarise(rows, a.reps, a.seed)
    text = render(res, excl, a.reps, a.seed)
    print(text)
    if a.out:
        with open(a.out + ".json", "w") as f:
            json.dump({"results": res, "excluded": excl,
                       "reps": a.reps, "seed": a.seed}, f, indent=1)
        with open(a.out + ".md", "w") as f:
            f.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
