"""INS-IMPROVE-159: the #966 shrinkage challenger on the FX hold-out, per
evaluation/pre_registration_fx_metals.md section 13. Numbers only. Stdlib only.
The shared weight pair is fit on training sessions (before 2026-01-01) only, then the
SAME hold-out rows as scripts/score_fx_holdout.py are scored. Frozen v2 k, naive k,
5000 reps and seed are fixed constants."""
import argparse
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import score_fx_descriptive as D  # noqa: E402
import score_fx_holdout as H  # noqa: E402
import score_fx_metals_157 as S  # noqa: E402

GRID = [round(0.05 * i, 2) for i in range(21)]
BASE_WINDOW = 250
MIN_MOVES = 125
MIN_FIT_ROWS = 100
STEPS = {"day": 1, "week": 5, "month": 21}
FIT_CELLS = ["EURUSD", "USDJPY", "USDEGP"]


def quantile(sorted_v, p):
    pos = (len(sorted_v) - 1) * p
    lo = int(math.floor(pos))
    hi = min(lo + 1, len(sorted_v) - 1)
    return sorted_v[lo] + (sorted_v[hi] - sorted_v[lo]) * (pos - lo)


def baseline(closes, flags, i, step, drop_flagged):
    """(q10, q90, n_moves) of the last BASE_WINDOW matured moves at cutoff index i, or
    None when under MIN_MOVES usable moves."""
    moves = []
    t = i - step
    while t >= 0 and len(moves) < BASE_WINDOW:
        if not (drop_flagged and any(flags[t + 1:t + step + 1])):
            moves.append(math.log(closes[t + step] / closes[t]) * 100)
        t -= 1
    if len(moves) < MIN_MOVES:
        return None
    moves.sort()
    return quantile(moves, 0.10), quantile(moves, 0.90), len(moves)


def challenger_is(real, half, qlo, qhi, a, b):
    """(interval score, covered, crossed) of the shrunk interval; crossed edges fall back to v2."""
    lo = a * -half + (1 - a) * qlo
    hi = b * half + (1 - b) * qhi
    crossed = lo >= hi
    if crossed:
        lo, hi = -half, half
    return D.winkler(real, lo, hi), lo <= real <= hi, crossed


def fit_pair(rows):
    """rows: dicts with real, half, qlo, qhi. Grid search of one shared (a, b); descending
    order and a strict improvement test send ties to the larger weights. None when fewer
    than MIN_FIT_ROWS rows."""
    if len(rows) < MIN_FIT_ROWS:
        return None
    best, pair = None, None
    for a in reversed(GRID):
        for b in reversed(GRID):
            m = sum(challenger_is(r["real"], r["half"], r["qlo"], r["qhi"], a, b)[0] for r in rows) / len(rows)
            if best is None or m < best - 1e-12:
                best, pair = m, (a, b)
    return pair + (best,)


def series_context(sessions, egp):
    if egp:
        sessions = [s for s in sessions if s[0] >= D.EGP_FLOAT_FIRST and s[0] not in D.EGP_EXCLUDED]
    closes = [s[1] for s in sessions]
    flags = D.jump_flags(closes) if egp else [False] * len(closes)
    return {s[0]: k for k, s in enumerate(sessions)}, closes, flags


def training_fit_rows(sessions, egp, hname):
    h = STEPS[hname]
    idx, closes, flags = series_context(sessions, egp)
    tr = [s for s in sessions if s[0] < H.HOLDOUT_START]
    rows, _ = D.build_rows(tr, h, egp, False)
    out, short = [], 0
    for r in rows:
        bl = baseline(closes, flags, idx[r["cutoff"]], h, False)
        if bl is None:
            short += 1
            continue
        out.append({"real": r["real"], "half": D.V2_K[hname] * r["sigma"] * math.sqrt(h) * 100,
                    "qlo": bl[0], "qhi": bl[1], "cutoff": r["cutoff"]})
    return out, short


def fill_challenger(rows, hname, idx, closes, flags, drop_flagged, pair):
    """Adds is_ch / in_ch to hold-out rows (after H.fill); returns (short-history listing, crossed listing)."""
    h = STEPS[hname]
    short, crossed = [], []
    for r in rows:
        bl = baseline(closes, flags, idx[r["cutoff"]], h, drop_flagged)
        r["usable"] = bl is not None
        if bl is None:
            short.append(r["cutoff"])
            continue
        r["q_lo"], r["q_hi"] = bl[0], bl[1]
        if r["real"] is not None:
            r["is_ch"], r["in_ch"], cr = challenger_is(r["real"], r["half_v2"], bl[0], bl[1], pair[0], pair[1])
            if cr:
                crossed.append(r["cutoff"])
    return short, crossed


def run(data_dir, asof, reps=D.REPS, seed=D.SEED):
    out = {"mode": "shrinkage_966_on_fx", "holdout_start": H.HOLDOUT_START, "asof_utc_date": asof, "reps": reps,
           "seed": seed, "grid": [GRID[0], GRID[-1], 0.05], "fit_cells": FIT_CELLS, "cells": {}, "rows": [],
           "gate": {"zero_move": []}}
    ctx = {}
    fit_rows, fit_counts = [], {}
    for name, egp in H.CELLS:
        sessions, counts = H.load_all(os.path.join(data_dir, name + ".csv"), asof)
        ctx[name] = (sessions, egp)
        out["cells"][name] = {"load_counts": counts, "horizons": {}}
        if name in FIT_CELLS:
            for hname in STEPS:
                rows, short = training_fit_rows(sessions, egp, hname)
                fit_rows += rows
                fit_counts["%s/%s" % (name, hname)] = {"covered": len(rows), "short_history": short}
    out["fit"] = {"covered_rows_pooled": len(fit_rows), "per_cell_horizon": fit_counts}
    fitted = fit_pair(fit_rows)
    if fitted is None:
        out["fit"]["result"] = "NO FIT (fewer than %d pooled covered rows), counts only" % MIN_FIT_ROWS
        return out
    pair = fitted[:2]
    out["fit"].update({"a": pair[0], "b": pair[1], "mean_is_train": fitted[2],
                       "mean_is_train_v2_pair_1_1": sum(challenger_is(r["real"], r["half"], r["qlo"], r["qhi"], 1.0, 1.0)[0]
                                                        for r in fit_rows) / len(fit_rows)})
    prepared = []
    for name, (sessions, egp) in ctx.items():
        idx, closes, flags = series_context(sessions, egp)
        variants = [("all_rows", False), ("jump_days_excluded", True)] if egp else [("all_rows", False)]
        for hname, h in STEPS.items():
            for vname, dj in variants:
                rows, dropped = H.build_rows(sessions, h, egp, dj)
                H.fill(rows, hname)
                short, crossed = fill_challenger(rows, hname, idx, closes, flags, dj, pair)
                usable = [r for r in rows if r["usable"]]
                mature = H.mature_clusters(rows)
                # a cluster with an unusable (short history) intended row is not mature
                bad = {r["cluster"] for r in rows if not r["usable"]}
                mature = {c for c in mature if c not in bad}
                prepared.append((name, hname, vname, rows, mature, dropped, short, crossed))
    failed = False
    for name, hname, vname, rows, mature, dropped, short, crossed in prepared:
        scored = [r for r in rows if r["cluster"] in mature]
        if not scored:
            continue
        z, fires = H.zero_move_check(S.tuples(scored, mature))
        failed = failed or fires
        out["gate"]["zero_move"].append({"cell": name, "horizon": hname, "rows": vname, "n": len(scored),
                                         "range_skill_zero_move_vs_naive": z, "positive_skill": fires})
    out["gate"]["stop_positive_skill"] = failed
    if failed:
        return out
    for name, hname, vname, rows, mature, dropped, short, crossed in prepared:
        scored = [r for r in rows if r["cluster"] in mature]
        info = {"rows_intended": len(rows), "rows_matured": sum(r["matured"] for r in rows),
                "clusters_total": len({r["cluster"] for r in rows}), "clusters_mature": len(mature),
                "rows_dropped_for_jump_days": dropped, "short_history_rows": short, "crossed_edge_rows": crossed,
                "n": len(scored)}
        cl = S.tuples(scored, mature) if scored else []
        info["clusters"] = len(cl)
        if len(cl) < H.MIN_CLUSTERS:
            info["counts_only"] = True
            info["keep_rule"] = "COUNTS ONLY (fewer than %d mature clusters)" % H.MIN_CLUSTERS
        else:
            s = S.stat(cl)
            info.update({"counts_only": False, "range_skill_ch_vs_naive": s["rs_ch"], "range_skill_v2_vs_naive": s["rs_v2"],
                         "delta_ch_minus_v2": s["rs_ch"] - s["rs_v2"], "coverage_ch": s["cov_ch"], "coverage_v2": s["cov_v2"]})
            info.update(S.boot(cl, reps, seed))
            lo, hi = info["coverage_ch_ci95"]
            conds = {"range_skill_ge_0.10": s["rs_ch"] >= H.KEEP_SKILL,
                     "coverage_ci_overlaps_0.75_0.85": lo <= H.COV_BAND[1] and hi >= H.COV_BAND[0],
                     "n_ge_30": s["n"] >= H.MIN_N, "clusters_ge_10": len(cl) >= H.MIN_CLUSTERS,
                     "delta_vs_v2_ci_lower_gt_0": info["delta_vs_v2_ci95"][0] > 0}
            info["keep_rule_conditions"] = conds
            info["keep_rule_all_met"] = all(conds.values())
            info["keep_rule"] = ("DESCRIPTIVE ONLY (derived cross-rate)" if name in H.CROSS else
                                 "KEEP-ELIGIBLE" if all(conds.values()) else "NOT KEEP-ELIGIBLE")
        out["cells"][name]["horizons"]["%s/%s" % (hname, vname)] = info
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
    if res["gate"]["stop_positive_skill"]:
        print("STOP: zero-move band shows positive skill on the hold-out; treat as leakage/bug")
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
