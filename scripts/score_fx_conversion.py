"""Conversion-profit scoring (INS-IMPROVE-158), per evaluation/pre_registration_fx_metals.md
section 12. Numbers only. Stdlib only. Training = sessions before 2026-01-01 (direction
only); hold-out = 2026-01-01 to the last matured session. 5000 reps, seed 20261125."""
import argparse
import datetime
import json
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import score_fx_descriptive as D  # noqa: E402

HOLDOUT_START = "2026-01-01"
MAJORS = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", "EURGBP", "EURJPY"]
EGP = ["USDEGP", "EUREGP", "GBPEGP", "SAREGP_DERIVED", "AEDEGP_DERIVED"]
COST_RT = {"major": 0.07, "egp": 0.2}
GRID = [0.1, 0.5, 1.0, 2.0]
MIN_TRAIN = 30
MIN_N = 30
MIN_CLUSTERS = 10
SLOTS = {"day": 1, "week": 5, "month": 21}
# (direct, path numerator legs [+1 multiply / -1 divide])
TRIANGLES = [("EURJPY", [("EURUSD", 1), ("USDJPY", 1)]),
             ("EURGBP", [("EURUSD", 1), ("GBPUSD", -1)]),
             ("EUREGP", [("EURUSD", 1), ("USDEGP", 1)]),
             ("GBPEGP", [("GBPUSD", 1), ("USDEGP", 1)])]


def sign(x):
    return 1 if x > 0 else (-1 if x < 0 else 0)


def boot_lower(vals, reps=D.REPS, seed=D.SEED):
    """2.5th percentile of the bootstrap mean (iid rows)."""
    rng = random.Random(seed)
    n = len(vals)
    means = sorted(sum(vals[rng.randrange(n)] for _ in range(n)) / n for _ in range(reps))
    return means[int(0.025 * reps)]


def load(data_dir, name, asof, egp):
    s, counts = D.load_sessions(os.path.join(data_dir, name + ".csv"), holdout="9999-12-31")
    s = [x for x in s if x[0] < asof]
    if egp:
        s = [x for x in s if x[0] >= D.EGP_FLOAT_FIRST and x[0] not in D.EGP_EXCLUDED]
    return s


def slot_rows(sessions, slot):
    """[(start_date, weekday, month, logret_pct or None)] for every slot start."""
    h = SLOTS[slot]
    rows, prev_month = [], None
    for i, (d, c) in enumerate(sessions):
        dt = datetime.date.fromisoformat(d)
        month = d[:7]
        first_of_month = month != prev_month
        prev_month = month
        if slot == "week" and dt.weekday() != 0:
            continue
        if slot == "month" and not first_of_month:
            continue
        r = math.log(sessions[i + h][1] / c) * 100 if i + h < len(sessions) else None
        rows.append((d, dt.weekday(), dt.month, r))
    return rows


def buckets(rows, slot):
    """bucket label -> rows. day: weekday; week: all; month: all; plus month-of-year."""
    out = {}
    for r in rows:
        if slot == "day":
            out.setdefault("dow%d" % r[1], []).append(r)
        else:
            out.setdefault("all", []).append(r)
            if slot == "month":
                out.setdefault("moy%02d" % r[2], []).append(r)
    return out


def score_bucket(train, hold, cost, reps=D.REPS, seed=D.SEED):
    tr = [r[3] for r in train if r[3] is not None]
    rec = {"train_n": len(tr)}
    if len(tr) < MIN_TRAIN:
        rec["abstain"] = "train_n_under_%d" % MIN_TRAIN
        return rec
    d = sign(sum(tr) / len(tr))
    if d == 0:
        rec["abstain"] = "zero_training_mean"
        return rec
    mature = [r for r in hold if r[3] is not None]
    clusters = {r[0][:7] for r in mature}
    unmatured = len(hold) - len(mature)
    rec.update({"direction": d, "n": len(mature), "unmatured": unmatured, "clusters": len(clusters)})
    if len(mature) < MIN_N or len(clusters) < MIN_CLUSTERS:
        rec["counts_only"] = True
        return rec
    gains = [d * r[3] for r in mature]
    rec["mean_gain_pct"] = sum(gains) / len(gains)
    rec["conservative_edge_pct"] = boot_lower(gains, reps, seed)
    rec["long_base_mean_pct"] = sum(r[3] for r in mature) / len(mature)
    rec["short_base_mean_pct"] = -rec["long_base_mean_pct"]
    rec["cost_rt_pct"] = cost
    rec["lower_gt_cost"] = rec["conservative_edge_pct"] > cost
    rec["lower_gt_grid"] = {("%g" % g): rec["conservative_edge_pct"] > g for g in GRID}
    return rec


def triangle_resid(series, direct, legs):
    dates = set(dict(series[direct]))
    for n, _ in legs:
        dates &= set(dict(series[n]))
    out = []
    for d in sorted(dates):
        v = math.log(dict(series[direct])[d])
        for n, s in legs:
            v -= s * math.log(dict(series[n])[d])
        out.append((d, v * 100))
    return out


def score_triangle(resid, cost_rt, reps=D.REPS, seed=D.SEED):
    tr = [v for d, v in resid if d < HOLDOUT_START]
    hold = [(d, v) for d, v in resid if d >= HOLDOUT_START]
    rec = {"train_n": len(tr), "n": len(hold), "clusters": len({d[:7] for d, _ in hold})}
    if len(tr) < MIN_TRAIN or not tr:
        rec["abstain"] = "train_n_under_%d" % MIN_TRAIN
        return rec
    d = sign(sum(tr) / len(tr))
    if d == 0:
        rec["abstain"] = "zero_training_mean"
        return rec
    rec["direction"] = d
    cycle_cost = 1.5 * cost_rt
    rec["cycle_cost_pct"] = cycle_cost
    if rec["n"] < MIN_N or rec["clusters"] < MIN_CLUSTERS:
        rec["counts_only"] = True
        return rec
    gains = [d * v for _, v in hold]
    rec["mean_residual_gain_pct"] = sum(gains) / len(gains)
    rec["conservative_edge_pct"] = boot_lower(gains, reps, seed)
    rec["lower_gt_cost"] = rec["conservative_edge_pct"] > cycle_cost
    return rec


def run(data_dir, asof, reps=D.REPS, seed=D.SEED):
    series = {}
    for n in MAJORS:
        series[n] = load(data_dir, n, asof, False)
    for n in EGP:
        series[n] = load(data_dir, n, asof, True)
    out = {"asof": asof, "holdout_start": HOLDOUT_START, "reps": reps, "seed": seed,
           "cost_rt_pct": COST_RT, "grid_pct": GRID, "cells": {}, "triangles": {}}
    for n, s in series.items():
        cls = "egp" if n in EGP else "major"
        for slot in SLOTS:
            rows = slot_rows(s, slot)
            tr = [r for r in rows if r[0] < HOLDOUT_START]
            ho = [r for r in rows if r[0] >= HOLDOUT_START]
            for b, brows in buckets(tr, slot).items():
                hb = buckets(ho, slot).get(b, [])
                out["cells"]["%s|%s|%s" % (n, slot, b)] = score_bucket(brows, hb, COST_RT[cls], reps, seed)
    for direct, legs in TRIANGLES:
        cls = "egp" if direct in EGP or any(l[0] in EGP for l in legs) else "major"
        out["triangles"][direct] = score_triangle(triangle_resid(series, direct, legs), COST_RT[cls], reps, seed)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--asof", required=True)
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--reps", type=int, default=D.REPS)
    a = ap.parse_args(argv)
    if a.reps != D.REPS:
        print("refusing: --reps must be the registered %d" % D.REPS)
        return 2
    res = run(a.data, a.asof, a.reps)
    with open(a.out_json, "w") as f:
        json.dump(res, f, indent=1, sort_keys=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
