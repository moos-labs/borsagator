#!/usr/bin/env python3
"""Shadow challenger: regime-aware ATR width (round 57).

Round 57 task (Moos, Slack 1795772785.176999, relayed, confirmed at
1795773027.453339, relayed): scale the frozen v2 band width by a
20-day ATR regime factor, daily OHLC only, no external source.
  half = f[regime, horizon] x (k_h x sigma60 x sqrt(sessions_h) x
         RISK_MULT)                      (the frozen v2 half-width)
Regime statistic per capture, from the pre-cutoff bars only:
  x = ATR20 / ATR60, ATR_n = mean true range of the last n bars,
  TR = max(H-L, |H-prevC|, |L-prevC|); needs 61 bars.
Regimes: low x <= t_lo, medium t_lo < x <= t_hi, high x > t_hi, with
t_lo, t_hi the 1/3 and 2/3 nearest-rank percentiles of x over the
TRAINING rows. Factors f[regime, horizon] are the grid value in
[0.50, 2.00] step 0.01 minimising mean Winkler IS on the TRAINING
rows of that regime and horizon; a bucket with fewer than
MIN_FIT_ROWS training rows keeps f = 1.0. Training = cells 1-47 of
the --captures dirs only (--fit-max-cell); thresholds and factors
are refitted from those cells on every run, never from the scored
cells, and are printed. Centre 0, RISK_MULT carried as in v2, the v2
k table is imported from scripts/ensemble.py.

Rows with fewer than 61 pre-cutoff bars have no regime and are
skipped (counted in the output); the same rows would not carry a
60-bar sigma either. Nothing edits scripts/ensemble.py, no Kronos.

Pre-registered keep rule (same as the round 3 challengers), one
scoring, per horizon, >= 30 rows over >= 5 tickers and >= 2 cutoffs:
(1) RangeSkill CI lower bound (cutoff-clustered by as_of) > 0 and
(2) the cutoff-clustered coverage CI overlaps [0.75, 0.85], untouched
cells only (>= 91). Cells 48-90 are scored only with --descriptive,
which prints no verdict and writes no verdict key.

Usage:
  python3 benchmarks/replay_atr_regime_width.py score --captures DIR ...
      [--min-cell 91] [--max-cell N] [--descriptive] [--reps 5000]
      [--json OUT]
  python3 benchmarks/replay_atr_regime_width.py diag --captures DIR ...
      (fit on cells 1-47, descriptive)
"""
import argparse
import json
import os
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import replay_band_candidates as R  # noqa: E402
import replay_parkinson_width as PK  # noqa: E402
import score_adoption_594 as A  # noqa: E402
import ensemble as ens_mod  # noqa: E402

HORIZONS = A.HORIZONS
REGIMES = ("low", "medium", "high")
F_GRID = [round(0.50 + 0.01 * i, 2) for i in range(151)]
MIN_FIT_ROWS = 10
FIT_MAX_CELL = 47
CLEAN_MIN_CELL = 91
keep_verdict = PK.keep_verdict


def _true_ranges(ohlc):
    ok = [b for b in ohlc if min(b) > 0 and b[1] >= b[2]]
    return [max(h - l, abs(h - ok[i][3]), abs(l - ok[i][3]))
            for i, (_o, h, l, _c) in enumerate(ok[1:])]


def atr_ratio(ohlc):
    """ATR20 / ATR60 from bars (oldest first, nothing after the
    cutoff); None under 61 usable bars."""
    tr = _true_ranges(ohlc)
    if len(tr) < 60:
        return None
    a60 = sum(tr[-60:]) / 60.0
    if a60 <= 0:
        return None
    return (sum(tr[-20:]) / 20.0) / a60


def percentile(vals, q):
    """Nearest-rank percentile, q in (0, 1]."""
    s = sorted(vals)
    return s[max(0, int(-(-q * len(s) // 1)) - 1)]


def regime(x, thr):
    if x <= thr[0]:
        return "low"
    return "high" if x > thr[1] else "medium"


def v2_half(r):
    h = r["horizon"]
    return R.half_pct(r["v2_sigma"], h, ens_mod.V2_BAND_K[h], r["mult"])


def fit(rows):
    """(thresholds, factors, counts) from training rows only."""
    seen, xs = set(), []
    for r in rows:
        key = (r["ticker"], r["as_of"])
        if r["sig"].get("atr_x") is not None and key not in seen:
            seen.add(key)
            xs.append(r["sig"]["atr_x"])
    if not xs:
        return None
    thr = (percentile(xs, 1 / 3.0), percentile(xs, 2 / 3.0))
    factors, counts = {}, {}
    for h in HORIZONS:
        for g in REGIMES:
            sub = [r for r in rows if r["horizon"] == h
                   and r["sig"].get("atr_x") is not None
                   and r["v2_sigma"]
                   and regime(r["sig"]["atr_x"], thr) == g]
            counts["%s/%s" % (h, g)] = len(sub)
            best = 1.0
            if len(sub) >= MIN_FIT_ROWS:
                best = min(F_GRID, key=lambda f: (
                    sum(R.row_is(r, f * v2_half(r)) for r in sub), f))
            factors["%s/%s" % (h, g)] = best
    return thr, factors, counts


def score_rows(rows, thr, factors):
    out = []
    for r in rows:
        x = r["sig"].get("atr_x")
        if x is None or not r["v2_sigma"]:
            continue
        g = regime(x, thr)
        v2 = v2_half(r)
        ch = factors["%s/%s" % (r["horizon"], g)] * v2
        out.append({"ticker": r["ticker"], "as_of": r["as_of"],
                    "horizon": r["horizon"], "regime": g,
                    "is_naive": R.row_is(r, r["naive_half"]),
                    "is_v2": R.row_is(r, v2), "is_ch": R.row_is(r, ch),
                    "in_v2": abs(r["real"]) <= v2,
                    "in_ch": abs(r["real"]) <= ch})
    return out


def build_rows(caps, allc):
    """R.build_rows with the ATR regime statistic added to each
    capture's sigma dict."""
    orig = R.sigmas
    ohlc_seen = {}

    def with_atr(ohlc):
        d = orig(ohlc)
        d["atr_x"] = atr_ratio(ohlc)
        ohlc_seen["n"] = ohlc_seen.get("n", 0) + 1
        return d
    R.sigmas = with_atr
    try:
        return R.build_rows(caps, allc)
    finally:
        R.sigmas = orig


def select_caps(allc, lo, hi):
    out = []
    for c in allc:
        n = A.cell_number(c)
        if n is not None and n >= lo and (hi is None or n <= hi):
            out.append(c)
    return out


def _f(v, nd=3):
    return PK._f(v, nd)


def render(res, thr, factors, counts, skipped, descriptive, title):
    L = [title, "ATR20/ATR60 regime width on the v2 band, v2 k = %s"
         % json.dumps(ens_mod.V2_BAND_K),
         "fit (training cells <= %d only): thresholds low<=%s high>%s"
         % (FIT_MAX_CELL, _f(thr[0]), _f(thr[1]))]
    for h in HORIZONS:
        L.append("  %s factors %s (training rows %s)" % (
            h, " ".join("%s %.2f" % (g, factors["%s/%s" % (h, g)])
                        for g in REGIMES),
            "/".join(str(counts["%s/%s" % (h, g)]) for g in REGIMES)))
    L.append("rows skipped, no regime: %d" % skipped)
    for h in HORIZONS:
        c = res[h]
        L.append("%s: n=%d, %d cutoffs, %d tickers"
                 % (h, c["n"], c["cutoffs"], c["tickers"]))
        L.append("  challenger coverage %s  RangeSkill %s  CI cutoff "
                 "[%s, %s]  CI ticker [%s, %s]"
                 % (_f(c["ch"]["coverage"]), _f(c["ch"]["range_skill"]),
                    _f(c["ch_ci_cutoff"][0]), _f(c["ch_ci_cutoff"][1]),
                    _f(c["ch_ci_ticker"][0]), _f(c["ch_ci_ticker"][1])))
        L.append("  frozen v2  coverage %s  RangeSkill %s"
                 % (_f(c["v2"]["coverage"]), _f(c["v2"]["range_skill"])))
    if not descriptive:
        v, why = keep_verdict(res)
        L += ["", "KEEP RULE: %s%s" % (
            v, " (" + "; ".join(why) + ")" if why else "")]
    return "\n".join(L)


def _run(a, lo, hi, descriptive, title):
    allc = A.find_captures(a.captures, None)
    train, _g = build_rows(select_caps(allc, 1, a.fit_max_cell), allc)
    f = fit(train)
    if f is None:
        print("refusing: no training rows (cells 1-%d, 61+ bars)"
              % a.fit_max_cell)
        return 2, None
    thr, factors, counts = f
    rows, _g = build_rows(select_caps(allc, lo, hi), allc)
    pairs = score_rows(rows, thr, factors)
    skipped = len(rows) - len(pairs)
    res = R.evaluate(pairs, a.reps, getattr(a, "seed", A.DEFAULT_SEED))
    print(render(res, thr, factors, counts, skipped, descriptive, title))
    out = {"k": ens_mod.V2_BAND_K, "thresholds": list(thr),
           "factors": factors, "training_rows": counts,
           "skipped_no_regime": skipped, "results": res,
           "descriptive": descriptive}
    if not descriptive:
        out["verdict"] = keep_verdict(res)[0]
    return 0, out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.
                                 RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="mode", required=True)
    d = sub.add_parser("diag")
    d.add_argument("--captures", nargs="+", required=True)
    d.add_argument("--fit-max-cell", type=int, default=FIT_MAX_CELL)
    d.add_argument("--reps", type=int, default=A.DEFAULT_REPS)
    s = sub.add_parser("score")
    s.add_argument("--captures", nargs="+", required=True)
    s.add_argument("--min-cell", type=int, default=CLEAN_MIN_CELL)
    s.add_argument("--max-cell", type=int, default=None)
    s.add_argument("--fit-max-cell", type=int, default=FIT_MAX_CELL)
    s.add_argument("--descriptive", action="store_true")
    s.add_argument("--reps", type=int, default=A.DEFAULT_REPS)
    s.add_argument("--seed", type=int, default=A.DEFAULT_SEED)
    s.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    if a.mode == "diag":
        rc, _o = _run(a, 1, a.fit_max_cell, True,
                      "FIT CELLS 1-%d, descriptive only" % a.fit_max_cell)
        return rc
    if a.min_cell < CLEAN_MIN_CELL and not a.descriptive:
        print("refusing: cells below %d need --descriptive"
              % CLEAN_MIN_CELL)
        return 2
    if a.min_cell <= a.fit_max_cell:
        print("refusing: scored cells overlap the training cells (<= %d)"
              % a.fit_max_cell)
        return 2
    rc, out = _run(a, a.min_cell, a.max_cell, a.descriptive,
                   "DESCRIPTIVE ONLY" if a.descriptive
                   else "CLEAN SCORING, cells >= %d" % a.min_cell)
    if rc == 0 and a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=1)
    return rc


if __name__ == "__main__":
    sys.exit(main())
