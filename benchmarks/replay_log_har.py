#!/usr/bin/env python3
"""Shadow challenger C: log-HAR volatility as the band width input.

INS-IMPROVE-006 experiment C (targets T2, T3). Band: centre 0,
  half = k_h x sigma_har_h x sqrt(sessions_h) x RISK_MULT,
where sigma_har_h is a log-HAR forecast of the mean daily Parkinson
variance over the next sessions_h sessions. Frozen v2 is untouched
and is the comparison column.

Spec (fixed here, before any untouched cell is scored):
  Daily variance proxy (--rv park, primary; --rv gk is the
    Garman-Klass variant, fit only, descriptive)  rv_t = ln(H_t/L_t)^2 / (4 ln 2) (Parkinson,
    OHLC only), floored at 5% of the median rv of the usable history
    so a zero-range session cannot send the log to -inf.
  Regressors at session t: log of the mean rv over the last 1 / 5 /
    22 sessions (HAR-D, HAR-W, HAR-M), plus a constant.
  Target at session t for horizon h (sessions 1 / 5 / 21): log of the
    mean rv over sessions t+1..t+h. Only targets that end on or before
    the capture's base date are used (no look-ahead).
  Refit per capture (so per ticker and cutoff) by OLS on that
  capture's own pre-cutoff history (about 250 bars). Fewer than 120
  usable observations -> the row has no sigma_har and is excluded
  (counted and printed).
  Retransform: exp(prediction) x Duan smearing factor (mean of
  exp(residual)), then sigma_har = sqrt of the mean daily variance.
  The smearing choice, the 5% floor and the 1/5/22 lags are stated
  here because the brief did not fix them.
Only the k table is fitted, per horizon, on cells 1-47 by minimising
mean Winkler IS (as P2/P3 and the round 3 challengers), then frozen.

Pre-registered keep rule: the round 3 rule. Untouched cells only
(>= 91 without --descriptive). Per horizon with >= 30 rows over >= 5
tickers and >= 2 cutoffs, RangeSkill (vs naive) cutoff-clustered 95%
CI lower bound > 0 and coverage 0.75-0.85. KEEP on every horizon,
REJECT when the sample is enough and either fails, INSUFFICIENT
otherwise. One scoring of the frozen file, no refit. Also reported:
the LOCO-CV IS/naive ratio on the fit cells for log-HAR vs the s60
control, so a loss to the control is visible before any scoring.

Usage:
  python3 benchmarks/replay_log_har.py fit --captures DIR ...
      [--max-cell 47] --out frozen.json
  python3 benchmarks/replay_log_har.py score --frozen frozen.json
      --captures DIR ... [--min-cell 91] [--descriptive]
      [--reps 5000] [--json OUT]
"""
import argparse
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
import replay_vol_adaptive as V  # noqa: E402
import score_adoption_594 as A  # noqa: E402
import ensemble as ens_mod  # noqa: E402
import backtest_score as bs  # noqa: E402

HORIZONS = A.HORIZONS
LN4 = 4.0 * math.log(2.0)
LAGS = (1, 5, 22)
FLOOR_FRAC = 0.05
MIN_OBS = 120
CLEAN_MIN_CELL = 91
KEY = "sigma_har"


def rv_series(bars, rv="park"):
    """Daily variance proxy per bar, floored. rv "park" is Parkinson
    (primary); "gk" is Garman-Klass (variant). Bars without a
    positive high/low get the floor."""
    raw = []
    for o, h, l, c in bars:
        if not (h and l and h >= l > 0):
            raw.append(None)
        elif rv == "gk" and o and c and o > 0 and c > 0:
            raw.append(0.5 * math.log(h / l) ** 2
                       - (2 * math.log(2.0) - 1.0)
                       * math.log(c / o) ** 2)
        else:
            raw.append(math.log(h / l) ** 2 / LN4)
    pos = sorted(x for x in raw if x and x > 0)
    if not pos:
        return []
    floor = FLOOR_FRAC * pos[len(pos) // 2]
    return [max(x if x is not None else 0.0, floor) for x in raw]


RV = {"mode": "park"}


def _mean(xs):
    return sum(xs) / len(xs)


def _solve(a, b):
    """Solve a x = b by Gaussian elimination (small, square)."""
    n = len(b)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(m[r][c]))
        if abs(m[p][c]) < 1e-12:
            return None
        m[c], m[p] = m[p], m[c]
        for r in range(c + 1, n):
            f = m[r][c] / m[c][c]
            for k in range(c, n + 1):
                m[r][k] -= f * m[c][k]
    x = [0.0] * n
    for r in range(n - 1, -1, -1):
        x[r] = (m[r][n] - sum(m[r][k] * x[k]
                              for k in range(r + 1, n))) / m[r][r]
    return x


def _features(rv, t):
    return [1.0] + [math.log(_mean(rv[t - L + 1:t + 1])) for L in LAGS]


def har_daily_sigma(bars, h):
    """Forecast daily sigma over the next h sessions, from bars dated
    on or before the base date. None when under MIN_OBS."""
    rv = rv_series(bars, RV["mode"])
    n = len(rv)
    xs, ys = [], []
    for t in range(LAGS[-1] - 1, n - h):
        xs.append(_features(rv, t))
        ys.append(math.log(_mean(rv[t + 1:t + 1 + h])))
    if len(xs) < MIN_OBS:
        return None
    k = len(xs[0])
    xtx = [[sum(x[i] * x[j] for x in xs) for j in range(k)]
           for i in range(k)]
    xty = [sum(x[i] * y for x, y in zip(xs, ys)) for i in range(k)]
    beta = _solve(xtx, xty)
    if beta is None:
        return None
    res = [y - sum(b * v for b, v in zip(beta, x))
           for x, y in zip(xs, ys)]
    smear = _mean([math.exp(e) for e in res])
    pred = sum(b * v for b, v in zip(beta, _features(rv, n - 1)))
    var = math.exp(pred) * smear
    return math.sqrt(var) if var > 0 else None


def build_rows(capture_dirs, ref_dirs):
    out, gaps = [], []
    for cap in capture_dirs:
        rows, g = R.build_rows([cap], ref_dirs)
        gaps.extend(g)
        ens = bs.load_json(os.path.join(cap, "digest", "ensemble.json"))
        bars = R.read_ohlc(cap, str((ens or {}).get("base_date")
                                    or "")[:10])
        cache = {}
        for r in rows:
            h = r["horizon"]
            if h not in cache:
                cache[h] = har_daily_sigma(bars, R.SESSIONS[h])
            r[KEY] = cache[h]
            r["s60_plain"] = r["sig"].get("s60")
            if r[KEY] is None:
                gaps.append("%s %s: log-HAR under %d obs, row excluded"
                            % (cap, h, MIN_OBS))
            out.append(r)
    return out, gaps


def fit(rows):
    rows = [r for r in rows if r.get(KEY)]
    cells = sorted({r["cell"] for r in rows if r["cell"] is not None})
    return {"spec": {"rv": RV["mode"], "lags": list(LAGS),
                     "floor_frac": FLOOR_FRAC,
                     "min_obs": MIN_OBS},
            "k": {h: V.fit_k(rows, h, KEY) for h in HORIZONS},
            "cv_ratio_har": V.loco_cv(rows, KEY),
            "cv_ratio_control_s60": V.loco_cv(rows, "s60_plain"),
            "k_control_s60": {h: V.fit_k(rows, h, "s60_plain")
                              for h in HORIZONS},
            "fit_rows": len(rows),
            "fit_cells": [cells[0], cells[-1]] if cells else None}


def score_rows(rows, frozen):
    out = []
    for r in rows:
        s = r.get(KEY)
        if not s or not r["v2_sigma"]:
            continue
        h = r["horizon"]
        ch = R.half_pct(s, h, frozen["k"][h], r["mult"])
        v2 = R.half_pct(r["v2_sigma"], h, ens_mod.V2_BAND_K[h],
                        r["mult"])
        out.append({"ticker": r["ticker"], "as_of": r["as_of"],
                    "horizon": h,
                    "is_naive": R.row_is(r, r["naive_half"]),
                    "is_v2": R.row_is(r, v2), "is_ch": R.row_is(r, ch),
                    "in_v2": abs(r["real"]) <= v2,
                    "in_ch": abs(r["real"]) <= ch})
    return out


keep_verdict = V.keep_verdict
_f = V._f


def render_fit(fz):
    return "\n".join([
        "Log-HAR band fit (%s): lags %s, floor %.2f, fit rows %d, cells %s"
        % (fz["spec"]["rv"], fz["spec"]["lags"], fz["spec"]["floor_frac"], fz["fit_rows"],
           fz["fit_cells"]),
        "k (log-HAR): %s" % json.dumps(fz["k"]),
        "k (control s60): %s" % json.dumps(fz["k_control_s60"]),
        "LOCO-CV IS/naive log-HAR: %s" % json.dumps(
            {h: _f(v) for h, v in fz["cv_ratio_har"].items()}),
        "LOCO-CV IS/naive control: %s" % json.dumps(
            {h: _f(v) for h, v in fz["cv_ratio_control_s60"].items()})])


def render_score(res, fz, descriptive):
    L = []
    if descriptive:
        L += ["DESCRIPTIVE ONLY: no keep/reject is valid.", ""]
    L.append("Log-HAR k %s vs frozen v2" % json.dumps(fz["k"]))
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
    v, why = keep_verdict(res)
    L += ["", "KEEP RULE: %s%s" % (
        v, "" if descriptive else (" (" + "; ".join(why) + ")"
                                   if why else ""))]
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.
                                 RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="mode", required=True)
    f = sub.add_parser("fit")
    f.add_argument("--captures", nargs="+", required=True)
    f.add_argument("--max-cell", type=int, default=47)
    f.add_argument("--out", required=True)
    f.add_argument("--rv", choices=("park", "gk"), default="park")
    s = sub.add_parser("score")
    s.add_argument("--frozen", required=True)
    s.add_argument("--captures", nargs="+", required=True)
    s.add_argument("--min-cell", type=int, default=CLEAN_MIN_CELL)
    s.add_argument("--descriptive", action="store_true")
    s.add_argument("--reps", type=int, default=A.DEFAULT_REPS)
    s.add_argument("--seed", type=int, default=A.DEFAULT_SEED)
    s.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    allc = A.find_captures(a.captures, None)
    if a.mode == "fit":
        RV["mode"] = a.rv
        caps = [c for c in allc if (A.cell_number(c) or 0) <= a.max_cell]
        rows, gaps = build_rows(caps, allc)
        fz = fit(rows)
        print(render_fit(fz))
        print("excluded rows (under %d obs): %d"
              % (MIN_OBS, sum("log-HAR under" in g for g in gaps)))
        with open(a.out, "w", encoding="utf-8") as fh:
            json.dump({"frozen": fz}, fh, indent=1)
        return 0
    if a.min_cell < CLEAN_MIN_CELL and not a.descriptive:
        print("refusing: cells below %d need --descriptive"
              % CLEAN_MIN_CELL)
        return 2
    with open(a.frozen, encoding="utf-8") as fh:
        fz = json.load(fh)["frozen"]
    RV["mode"] = fz["spec"].get("rv", "park")
    caps = A.find_captures(a.captures, a.min_cell)
    rows, gaps = build_rows(caps, allc)
    res = R.evaluate(score_rows(rows, fz), a.reps, a.seed)
    print(render_score(res, fz, a.descriptive))
    print("excluded rows (under %d obs): %d"
          % (MIN_OBS, sum("log-HAR under" in g for g in gaps)))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump({"frozen": fz, "results": res,
                       "verdict": keep_verdict(res)[0],
                       "descriptive": a.descriptive}, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
