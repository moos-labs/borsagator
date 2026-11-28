"""First FX descriptive cell set (INS-IMPROVE-155), per
evaluation/pre_registration_fx_metals.md. Numbers only: no verdict word.
Stdlib only. Reads harvested csv (scripts/fetch_fx_metals_store.py output).
Training block only: sessions dated before HOLDOUT_START are loaded; hold-out
rows are dropped at load time, before any computation, and never read further.
"""
import argparse
import csv
import datetime
import json
import math
import os
import random
import statistics
import sys

HOLDOUT_START = "2026-01-01"
TRAIN_START = "2019-01-01"
EGP_FLOAT_FIRST = "2024-03-07"   # first session of the float regime; 2024-03-06 excluded
EGP_EXCLUDED = {"2024-03-06"}
JUMP_MULT = 5.0
JUMP_WINDOW = 60
SIGMA_WINDOW = 60
HORIZONS = {"day": 1, "week": 5, "month": 21}
V2_K = {"day": 1.15, "week": 1.28, "month": 1.20}   # frozen v2 values (scripts/ensemble.py V2_BAND_K), not refit
NAIVE_K = 1.2816
ALPHA = 0.2
REPS = 5000
SEED = 20261125
CELLS = [("EURUSD", False), ("USDJPY", False), ("USDEGP", True)]


def winkler(real, lo, hi, alpha=ALPHA):
    w = hi - lo
    if lo <= real <= hi:
        return w
    return w + (2 / alpha) * ((lo - real) if real < lo else (real - hi))


def next_monday(d):
    dt = datetime.date.fromisoformat(d)
    return (dt + datetime.timedelta(days=(7 - dt.weekday()) % 7)).isoformat()


def load_sessions(path, holdout=HOLDOUT_START, start=TRAIN_START):
    """Return (sessions, counts). sessions = [(date, close)] ascending.
    Hold-out and pre-start rows dropped first. Sat/Sun bars merge into the
    following Monday: kept only when a Monday bar exists (session close = the
    Monday close); a weekend bar with no Monday bar is dropped and counted."""
    bars = {}
    dropped_holdout = 0
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            d = r["date"]
            if d >= holdout:
                dropped_holdout += 1
                continue
            if d < start or not r["close"]:
                continue
            c = float(r["close"])
            if c > 0:
                bars[d] = c
    sess, merged, orphan = {}, 0, 0
    for d in sorted(bars):
        wd = datetime.date.fromisoformat(d).weekday()
        if wd >= 5:
            m = next_monday(d)
            if m in bars and m < holdout:
                merged += 1
            else:
                orphan += 1
            continue
        sess[d] = bars[d]
    return sorted(sess.items()), {"weekend_bars_merged": merged,
                                   "weekend_bars_dropped_no_monday": orphan,
                                   "holdout_rows_dropped_at_load": dropped_holdout}


def jump_flags(closes):
    """flag[j] True when |ret j| > 5 x median |ret| of the prior 60 returns."""
    rets = [math.log(closes[j] / closes[j - 1]) for j in range(1, len(closes))]
    flags = [False] * len(closes)
    for j in range(1, len(closes)):
        prior = [abs(x) for x in rets[max(0, j - 1 - JUMP_WINDOW):j - 1]]
        if len(prior) >= JUMP_WINDOW and abs(rets[j - 1]) > JUMP_MULT * statistics.median(prior):
            flags[j] = True
    return flags


def build_rows(sessions, h, egp, drop_jumps):
    """Non-overlapping cutoffs every h sessions from index SIGMA_WINDOW."""
    if egp:
        sessions = [s for s in sessions if s[0] >= EGP_FLOAT_FIRST and s[0] not in EGP_EXCLUDED]
    dates = [s[0] for s in sessions]
    closes = [s[1] for s in sessions]
    flags = jump_flags(closes) if egp else [False] * len(closes)
    rows, excluded_jump = [], 0
    i = SIGMA_WINDOW
    while i + h < len(closes):
        rets = [math.log(closes[j] / closes[j - 1]) for j in range(i - SIGMA_WINDOW + 1, i + 1)]
        mean = sum(rets) / len(rets)
        sigma = math.sqrt(sum((x - mean) ** 2 for x in rets) / (len(rets) - 1))
        real = math.log(closes[i + h] / closes[i]) * 100
        if drop_jumps and any(flags[i - SIGMA_WINDOW + 1:i + h + 1]):
            excluded_jump += 1
        else:
            rows.append({"cutoff": dates[i], "cluster": dates[i][:7], "real": real, "sigma": sigma})
        i += h
    return rows, excluded_jump


def score(rows, hname):
    h = HORIZONS[hname]
    clusters = {}
    for r in rows:
        half_n = NAIVE_K * r["sigma"] * math.sqrt(h) * 100
        half_v = V2_K[hname] * r["sigma"] * math.sqrt(h) * 100
        c = clusters.setdefault(r["cluster"], [0, 0.0, 0.0, 0, 0, 0.0, 0])
        c[0] += 1
        c[1] += winkler(r["real"], -half_v, half_v)
        c[2] += winkler(r["real"], -half_n, half_n)
        c[3] += abs(r["real"]) <= half_v
        c[4] += abs(r["real"]) <= half_n
        c[5] += abs(r["real"])
        c[6] += r["real"] > 0
    return list(clusters.values())


def stats(cl):
    n = sum(c[0] for c in cl)
    isv = sum(c[1] for c in cl) / n
    isn = sum(c[2] for c in cl) / n
    return {"n": n, "clusters": len(cl), "mean_is_v2": isv, "mean_is_naive": isn,
            "range_skill_v2_vs_naive": 1 - isv / isn,
            "coverage_v2": sum(c[3] for c in cl) / n, "coverage_naive": sum(c[4] for c in cl) / n,
            "rw_mean_abs_move_pp": sum(c[5] for c in cl) / n,
            "share_up": sum(c[6] for c in cl) / n}


def boot(cl, reps=REPS, seed=SEED):
    rng = random.Random(seed)
    k = len(cl)
    rs, cv, cn = [], [], []
    for _ in range(reps):
        s = [cl[rng.randrange(k)] for _ in range(k)]
        n = sum(c[0] for c in s)
        isv, isn = sum(c[1] for c in s), sum(c[2] for c in s)
        rs.append(1 - isv / isn)
        cv.append(sum(c[3] for c in s) / n)
        cn.append(sum(c[4] for c in s) / n)
    out = {}
    for name, v in (("range_skill_ci95", rs), ("coverage_v2_ci95", cv), ("coverage_naive_ci95", cn)):
        v.sort()
        out[name] = [v[int(0.025 * reps)], v[min(reps - 1, int(0.975 * reps))]]
    return out


def run(data_dir, reps=REPS):
    out = {"holdout_start": HOLDOUT_START, "train_start": TRAIN_START, "reps": reps, "seed": SEED,
           "v2_k": V2_K, "naive_k": NAIVE_K, "cells": {}}
    for name, egp in CELLS:
        sessions, counts = load_sessions(os.path.join(data_dir, name + ".csv"))
        variants = [("all_rows", False), ("jump_days_excluded", True)] if egp else [("all_rows", False)]
        cell = {"load_counts": counts, "sessions": len(sessions), "horizons": {}}
        for hname, h in HORIZONS.items():
            for vname, dj in variants:
                rows, exj = build_rows(sessions, h, egp, dj)
                if not rows:
                    cell["horizons"]["%s/%s" % (hname, vname)] = {"n": 0}
                    continue
                cl = score(rows, hname)
                s = stats(cl)
                s.update(boot(cl, reps))
                s["rows_dropped_for_jump_days"] = exj
                s["first_cutoff"], s["last_cutoff"] = rows[0]["cutoff"], rows[-1]["cutoff"]
                cell["horizons"]["%s/%s" % (hname, vname)] = s
        out["cells"][name] = cell
    return out


def render(res):
    L = ["# FX first descriptive cell set (numbers only)", "",
         "Training block only (sessions %s to before %s; EGP from %s, 2024-03-06 excluded). "
         "Cutoffs every h sessions (non-overlapping), cluster = calendar month of the cutoff. "
         "Bands are +/- k x sigma60 x sqrt(h) on the h-session log close-to-close move (pp); "
         "v2 k = frozen EGX values %s, not refit; naive k = %s. Bootstrap: %d reps, seed %d, "
         "whole-cluster resampling." % (res["train_start"], res["holdout_start"], EGP_FLOAT_FIRST,
                                        res["v2_k"], res["naive_k"], res["reps"], res["seed"]), "",
         "| Cell | Horizon / rows | n | clusters | v2 IS | naive IS | RangeSkill v2 vs naive [95% CI] | cov v2 [CI] | cov naive [CI] | RW mean abs move pp | share up |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    for cn, cell in res["cells"].items():
        for hk, s in cell["horizons"].items():
            if not s.get("n"):
                L.append("| %s | %s | 0 | | | | | | | | |" % (cn, hk))
                continue
            L.append("| %s | %s | %d | %d | %.4f | %.4f | %.4f [%.4f, %.4f] | %.3f [%.3f, %.3f] | %.3f [%.3f, %.3f] | %.4f | %.3f |" % (
                cn, hk, s["n"], s["clusters"], s["mean_is_v2"], s["mean_is_naive"],
                s["range_skill_v2_vs_naive"], *s["range_skill_ci95"],
                s["coverage_v2"], *s["coverage_v2_ci95"], s["coverage_naive"], *s["coverage_naive_ci95"],
                s["rw_mean_abs_move_pp"], s["share_up"]))
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--out-md", required=True)
    a = ap.parse_args(argv)
    res = run(a.data)
    with open(a.out_json, "w") as f:
        json.dump(res, f, indent=2, sort_keys=True)
    with open(a.out_md, "w") as f:
        f.write(render(res))
    return 0


if __name__ == "__main__":
    sys.exit(main())
