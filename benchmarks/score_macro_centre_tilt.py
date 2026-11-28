#!/usr/bin/env python3
"""Round 95: macro-proxy centre tilt, descriptive scorer.

Pre-registration: docs/round95_macro_centre_tilt_prereg.md. Centre
c = S x m x v2 half-width, band half-width = frozen v2's. Only
`describe` exists: it refuses any range outside cells 48-90. No
verdict word is printed. Counts come first.
"""
import argparse
import csv
import datetime
import math
import json
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "benchmarks"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import replay_band_candidates as R  # noqa: E402
import score_adoption_594 as A  # noqa: E402
import ensemble as ens_mod  # noqa: E402
import backtest_score as bs  # noqa: E402

HORIZONS = A.HORIZONS
S = 0.10
WINDOW_DAYS = 63
BRENT_LAG_DAYS = 3
SERIES = {  # name: (file, theta, kind, direction d)
    "oil": ("brent_daily.csv", 0.05, "rel", -1),
    "fx": ("usd_egp_interbank_weekly.csv", 0.02, "rel", +1),
    "tbill": ("tbill_91d_weekly.csv", 1.0, "abs", -1),
}
MIN_CELL, MAX_CELL = 48, 90
SERIES_DIR = os.path.join(ROOT, "evaluation", "macro_series")


def d_(s):
    return datetime.date.fromisoformat(str(s)[:10])


def load_series(path):
    out = []
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                row = (d_(r["observed_date"]), d_(r["published_date"]),
                       float(r["value"]))
            except (ValueError, KeyError, TypeError):
                continue  # includes a row that omits the value column (None)
            if not math.isfinite(row[2]):
                continue  # nan / inf are not measurements: same path as unparseable
            out.append(row)
    out.sort()
    return out


def signal(rows, cutoff, theta, kind, window=WINDOW_DAYS, obs_lag_days=0):
    """(x, reason). x in {-1, 0, 1}; 0 with a reason when a value is
    missing. A row is usable at `cutoff` only if published <= cutoff and,
    when obs_lag_days > 0 (Brent: registered lag 3 days), its observed
    date is on or before cutoff minus obs_lag_days."""
    cutoff = d_(cutoff)
    obs_cut = cutoff - datetime.timedelta(days=obs_lag_days)
    usable = [r for r in rows if r[1] <= cutoff and r[0] <= obs_cut]
    if not usable:
        return 0, "no usable value"
    last = max(usable, key=lambda r: r[0])
    refs = [r for r in usable
            if r[0] <= last[0] - datetime.timedelta(days=window)]
    if not refs:
        return 0, "no usable value %d days before %s" % (window, last[0])
    ref = max(refs, key=lambda r: r[0])
    if kind == "rel" and ref[2] == 0:
        # A relative change divides by the reference; a finite zero
        # reference has no defined change. Absolute changes keep zero valid.
        return 0, "zero reference value on %s for a relative change" % ref[0]
    ch = (last[2] / ref[2] - 1.0) if kind == "rel" else (last[2] - ref[2])
    ch = round(ch, 12)  # 105/100 - 1 must equal 0.05 exactly
    if ch > theta:
        return 1, None
    if ch < -theta:
        return -1, None
    return 0, None


def composite(xs, dirs):
    return sum(d * x for d, x in zip(dirs, xs)) / 3.0


def tilt_rows(rows, series):
    """(pairs, missing-signal lines, v2_sigma exclusion lines). Centre
    c = S x m x v2 half; missing signals become 0 and each affected row
    is listed. A row with missing or zero v2_sigma is dropped and listed
    separately; it is not a missing macro signal."""
    out, listed, dropped = [], [], []
    for r in rows:
        if not r.get("v2_sigma"):
            dropped.append("excluded row %s %s %s: missing or zero v2_sigma"
                           % (r["ticker"], str(r["as_of"])[:10],
                              r["horizon"]))
            continue
        h = r["horizon"]
        v2h = R.half_pct(r["v2_sigma"], h, ens_mod.V2_BAND_K[h], r["mult"])
        xs, miss = [], []
        for name, (_, th, kind, _d) in SERIES.items():
            x, why = signal(series[name], r["as_of"], th, kind,
                            obs_lag_days=BRENT_LAG_DAYS if name == "oil" else 0)
            xs.append(x)
            if why:
                miss.append("%s: %s" % (name, why))
        if miss:
            listed.append("missing signal row %s %s %s: %s (signal set to 0)"
                          % (r["ticker"], str(r["as_of"])[:10], h,
                             "; ".join(miss)))
        m = composite(xs, [v[3] for v in SERIES.values()])
        c = S * m * v2h
        out.append({"ticker": r["ticker"], "as_of": str(r["as_of"])[:10],
                    "horizon": h, "m": m, "centre": c,
                    "missing": bool(miss),
                    "is_naive": R.row_is(r, r["naive_half"]),
                    "is_v2": R.row_is(r, v2h),
                    "is_ch": bs.winkler_is(r["real"], c - v2h, c + v2h),
                    "in_v2": abs(r["real"]) <= v2h,
                    "in_ch": abs(r["real"] - c) <= v2h})
    return out, listed, dropped


def boot(pairs, reps, seed):
    groups = {}
    for p in pairs:
        groups.setdefault(p["as_of"], []).append(p)
    keys = sorted(groups)
    rng = random.Random(seed)
    sk, cov, dl = [], [], []
    for _ in range(reps if keys else 0):
        draw = []
        for _ in keys:
            draw.extend(groups[rng.choice(keys)])
        # coverage is defined whenever the draw has rows; only the skill and
        # skill-difference draws need a defined RangeSkill
        cov.append(sum(p["in_ch"] for p in draw) / len(draw))
        a, b = A.range_skill(draw, "ch"), A.range_skill(draw, "v2")
        if a is None or b is None:
            continue
        sk.append(a)
        dl.append(a - b)
    return sk, cov, dl


def evaluate(pairs, reps, seed):
    res = {}
    for h in HORIZONS:
        hp = [p for p in pairs if p["horizon"] == h]
        n = len(hp)
        sk, cov, dl = boot(hp, reps, seed)
        res[h] = {
            "n": n, "cutoffs": len({p["as_of"] for p in hp}),
            "tickers": len({p["ticker"] for p in hp}),
            "nonzero_tilt_rows": sum(1 for p in hp if p["m"] != 0),
            "cov_tilt": sum(p["in_ch"] for p in hp) / n if n else None,
            "cov_v2": sum(p["in_v2"] for p in hp) / n if n else None,
            "rs_tilt": A.range_skill(hp, "ch"),
            "rs_v2": A.range_skill(hp, "v2"),
            "rs_tilt_ci_cutoff": list(A.percentile_ci(sk)),
            "cov_tilt_ci_cutoff": list(A.percentile_ci(cov)),
            "delta": (A.range_skill(hp, "ch") - A.range_skill(hp, "v2")
                      if n and A.range_skill(hp, "ch") is not None
                      and A.range_skill(hp, "v2") is not None else None),
            "delta_ci_cutoff": list(A.percentile_ci(dl))}
    return res


def f3(v):
    return "n/a" if v is None else "%.3f" % v


def count_lines(pairs):
    L = []
    for h in HORIZONS:
        hp = [p for p in pairs if p["horizon"] == h]
        miss = sum(1 for p in hp if p.get("missing"))
        L.append("%s: rows=%d cutoff clusters=%d tickers=%d "
                 "rows all signals usable=%d rows with missing signals=%d"
                 % (h, len(hp), len({p["as_of"] for p in hp}),
                    len({p["ticker"] for p in hp}), len(hp) - miss, miss))
    return L


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mode", choices=("describe",))
    ap.add_argument("--captures", nargs="+", required=True)
    ap.add_argument("--min-cell", type=int, default=MIN_CELL)
    ap.add_argument("--max-cell", type=int, default=MAX_CELL)
    ap.add_argument("--reps", type=int, default=A.DEFAULT_REPS)
    ap.add_argument("--seed", type=int, default=A.DEFAULT_SEED)
    ap.add_argument("--series-dir", default=SERIES_DIR)
    ap.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    if a.min_cell < MIN_CELL or a.max_cell > MAX_CELL:
        print("refusing: describe covers cells %d-%d only" % (MIN_CELL,
                                                              MAX_CELL))
        return 2
    if a.reps != A.DEFAULT_REPS:
        print("refusing: --reps must be the registered %d, got %d"
              % (A.DEFAULT_REPS, a.reps))
        return 2
    if a.seed != A.DEFAULT_SEED:
        print("refusing: --seed must be the registered %d, got %d"
              % (A.DEFAULT_SEED, a.seed))
        return 2
    series = {k: load_series(os.path.join(a.series_dir, v[0]))
              for k, v in SERIES.items()}
    allc = A.find_captures(a.captures, None)
    # Cell bounds are applied BEFORE the per-(cutoff, ticker) dedup so a
    # capture outside the cells cannot displace an eligible one; the
    # unbounded list stays the price-reference set.
    disc_rejects = []
    caps = [c for c in A.find_captures(a.captures, a.min_cell, a.max_cell,
                                       rejects=disc_rejects)
            if A.cell_number(c) is not None]
    repairs, info = [], []
    rows, gaps = R.build_rows(caps, allc, repairs, info)
    pairs, listed, dropped = tilt_rows(rows, series)
    counts = count_lines(pairs)
    # Scored rows with a zero-valued signal are NOT exclusions: they are
    # reported under their own heading and JSON key.
    ex = (["excluded: %s" % g for g in gaps] + dropped
          + ["excluded: %s" % g for g in sorted(disc_rejects)])
    print("COUNTS (printed before the descriptive read), cells %d-%d, "
          "%d missing-signal rows, %d v2_sigma exclusions, "
          "%d incomplete captures"
          % (a.min_cell, a.max_cell, len(listed), len(dropped),
             len(disc_rejects)))
    print("\n".join(counts))
    print("REPAIRED (scored, not excluded)")
    print("\n".join(repairs))
    print("INFO (per-capture notes on scored captures, not exclusions)")
    print("\n".join(info))
    print("MISSING-SIGNAL ROWS (scored with the signal set to 0, not exclusions)")
    print("\n".join(listed))
    print("EXCLUSIONS (every one listed, before any statistic)")
    print("\n".join(ex))
    res = evaluate(pairs, a.reps, a.seed)
    print("DESCRIPTIVE ONLY cells %d-%d, centre tilt S=%.2f, v2 width, "
          "%d reps seed %d" % (a.min_cell, a.max_cell, S, a.reps, a.seed))
    for h in HORIZONS:
        c = res[h]
        print("%s: n=%d, %d cutoffs, %d tickers, %d rows with a nonzero tilt"
              % (h, c["n"], c["cutoffs"], c["tickers"], c["nonzero_tilt_rows"]))
        print("  tilt: coverage %s RangeSkill %s CI cutoff [%s, %s] coverage "
              "CI cutoff [%s, %s]" % (
                  f3(c["cov_tilt"]), f3(c["rs_tilt"]),
                  f3(c["rs_tilt_ci_cutoff"][0]), f3(c["rs_tilt_ci_cutoff"][1]),
                  f3(c["cov_tilt_ci_cutoff"][0]), f3(c["cov_tilt_ci_cutoff"][1])))
        print("  frozen v2: coverage %s RangeSkill %s" % (
            f3(c["cov_v2"]), f3(c["rs_v2"])))
        print("  tilt minus v2: %s CI cutoff [%s, %s]" % (
            f3(c["delta"]), f3(c["delta_ci_cutoff"][0]),
            f3(c["delta_ci_cutoff"][1])))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump({"descriptive": True, "counts": counts, "results": res,
                       "repaired": repairs, "info": info,
                       "missing_signal_rows": listed,
                       "excluded": ex}, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
