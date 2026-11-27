"""Round 68 route 2: index-regime flag, DESCRIPTIVE only (stdlib).

Pre-registration: docs/round68_index_regime_prereg.md (committed before
any number was computed). No verdict word or key. Reads the
training block (cells <= 47) first; cells above 47 are read only with
--allow-extend and only when every pre-registered threshold is met.

x = ln(index close at last session <= cutoff / close 21 sessions earlier).
y = ticker realised_move_pct (buy-and-hold row, dividend_gap rows dropped).
.CA tickers use the EGX30 (Mubasher) series, others the S&P 500 (Yahoo).
"""
import argparse
import bisect
import csv
import datetime as dt
import glob
import json
import math
import os
import random
import re

LOOKBACK = 21
MAX_STALE_DAYS = 10
HORIZONS = ("day", "week", "month")
B_DRAWS = 2000
SEED = 68
TRAIN_MAX = 47


def load_series(path):
    out = []
    with open(path) as f:
        for r in csv.DictReader(f):
            out.append((r["date"], float(r["close"])))
    out.sort()
    return out


def index_for(ticker):
    return "EGX30" if ticker.endswith(".CA") else "GSPC"


def trailing_x(series, asof, n=LOOKBACK):
    """ln(c[i]/c[i-n]) with i = last session on or before asof; None if
    the series does not cover asof within 10 days or lacks n prior bars."""
    dates = [d for d, _ in series]
    i = bisect.bisect_right(dates, asof) - 1
    if i < n:
        return None
    gap = (dt.date.fromisoformat(asof) - dt.date.fromisoformat(dates[i])).days
    if gap > MAX_STALE_DAYS:
        return None
    return math.log(series[i][1] / series[i - n][1])


def _ranks(v):
    order = sorted(range(len(v)), key=lambda k: v[k])
    r = [0.0] * len(v)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2.0 + 1.0
        i = j + 1
    return r


def spearman(x, y):
    if len(x) < 3:
        return None
    rx, ry = _ranks(x), _ranks(y)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    sxy = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    sxx = sum((a - mx) ** 2 for a in rx)
    syy = sum((b - my) ** 2 for b in ry)
    if sxx == 0 or syy == 0:
        return None
    return sxy / math.sqrt(sxx * syy)


def boot_ci(rows, draws=B_DRAWS, seed=SEED):
    """Cutoff-clustered bootstrap CI of the Spearman. rows: (cutoff,x,y)."""
    groups = {}
    for c, x, y in rows:
        groups.setdefault(c, []).append((x, y))
    keys = sorted(groups)
    rng = random.Random(seed)
    vals = []
    for _ in range(draws):
        xs, ys = [], []
        for _k in keys:
            for x, y in groups[rng.choice(keys)]:
                xs.append(x)
                ys.append(y)
        s = spearman(xs, ys)
        if s is not None:
            vals.append(s)
    if not vals:
        return None, None
    vals.sort()
    return (vals[int(0.025 * (len(vals) - 1))],
            vals[int(round(0.975 * (len(vals) - 1)))])


def cell_rows(path):
    """Per cell: (cell_no, ticker, as_of, {horizon: realised_move_pct})."""
    n = int(re.search(r"cell(\d+)_", os.path.basename(path)).group(1))
    d = json.load(open(path))
    moves = {}
    ticker = asof = None
    for f in d["forecasts_detail"]:
        ticker, asof = f["ticker"], f["as_of"]
        if (f["entrant"] == "buy-and-hold" and f["status"] == "matured"
                and f.get("dividend_gap") is None
                and f.get("realized_move_pct") is not None):
            moves[f["horizon"]] = f["realized_move_pct"]
    return n, ticker, asof, moves


def build(cells_dir, series, max_cell=TRAIN_MAX, min_cell=1):
    cells, lacking = [], []
    for p in glob.glob(os.path.join(cells_dir, "cell*_score_v2.json")):
        n = int(re.search(r"cell(\d+)_", os.path.basename(p)).group(1))
        if n < min_cell or n > max_cell:
            continue
        n, t, a, mv = cell_rows(p)
        x = trailing_x(series[index_for(t)], a)
        if x is None:
            lacking.append({"cell": n, "ticker": t, "as_of": a})
            continue
        cells.append((n, t, a, x, mv))
    cells.sort()
    lacking.sort(key=lambda r: r["cell"])
    out = {"n_cells_used": len(cells), "cells_without_index": lacking,
           "horizons": {}}
    for h in HORIZONS:
        R = [(a, x, mv[h]) for _n, _t, a, x, mv in cells if h in mv]
        xs, ys = [r[1] for r in R], [r[2] for r in R]
        S = [(x, y) for _c, x, y in R if x != 0 and y != 0]
        agree = sum((x > 0) == (y > 0) for x, y in S)
        lo, hi = boot_ci(R)
        out["horizons"][h] = {
            "n": len(R), "n_cutoffs": len({r[0] for r in R}),
            "spearman": spearman(xs, ys), "spearman_ci95": [lo, hi],
            "sign_n": len(S), "sign_agree": agree,
            "sign_agree_share": (agree / len(S)) if S else None}
    return out, cells


def prereg_thresholds(res):
    """The criteria written in docs/round68_index_regime_prereg.md."""
    out = {}
    for h in ("week", "month"):
        r = res["horizons"][h]
        lo = r["spearman_ci95"][0]
        out[h] = {
            "n_ge_30": r["n"] >= 30,
            "spearman_ge_0.20": r["spearman"] is not None
            and r["spearman"] >= 0.20,
            "sign_agree_ge_0.60": r["sign_agree_share"] is not None
            and r["sign_agree_share"] >= 0.60,
            "ci_lower_gt_0": lo is not None and lo > 0}
    out["all_met"] = all(all(v.values()) for k, v in out.items()
                         if k in ("week", "month"))
    return out


def run(cells_dir, series, max_cell=TRAIN_MAX, allow_extend=False):
    """Training block (cells 1-47) first. Cells above 47 are read only when
    --allow-extend is given AND every pre-registered threshold is met."""
    res, _ = build(cells_dir, series, TRAIN_MAX)
    res["prereg_thresholds"] = prereg_thresholds(res)
    if max_cell > TRAIN_MAX:
        if not allow_extend:
            raise SystemExit("cells above %d need --allow-extend" % TRAIN_MAX)
        if not res["prereg_thresholds"]["all_met"]:
            raise SystemExit("extension refused: training thresholds not all met: "
                             + json.dumps(res["prereg_thresholds"]))
        ext, _ = build(cells_dir, series, max_cell, min_cell=TRAIN_MAX + 1)
        res["extension"] = ext
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cells", default="backtest/cells")
    ap.add_argument("--egx30", default="evaluation/index_regime/EGX30_mubasher_close.csv")
    ap.add_argument("--gspc", default="evaluation/index_regime/GSPC_yahoo_close.csv")
    ap.add_argument("--max-cell", type=int, default=TRAIN_MAX)
    ap.add_argument("--allow-extend", action="store_true")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    series = {"EGX30": load_series(a.egx30), "GSPC": load_series(a.gspc)}
    res = run(a.cells, series, a.max_cell, a.allow_extend)
    txt = json.dumps(res, indent=1)
    if a.json:
        open(a.json, "w").write(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()
