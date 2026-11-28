"""INS-IMPROVE-157. (1) FX-fit challengers: k fitted per series and horizon on the
2019-2025 training block only (sessions before 2026-01-01), then scored on the SAME
hold-out rows as scripts/score_fx_holdout.py. (2) Metals hold-out on the futures proxy
(GC=F / SI=F, research only, never spot) with the roll-window rule. Numbers only.
Stdlib only. Same gates as the 156 run: zero-move falsification first, then counts-only
under 10 fully mature clusters. Reuses the 156 and 155 scorers; frozen v2 k and naive k
are not edited."""
import argparse
import csv
import json
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import score_fx_descriptive as D  # noqa: E402
import score_fx_holdout as H  # noqa: E402

K_GRID = [round(0.50 + 0.05 * i, 2) for i in range(51)]   # 0.50 .. 3.00
MIN_TRAIN_ROWS = 20
METAL_MIN_SIGMA_RETS = 40
METALS = [("GC=F", "XAUUSD_FUTURES_PROXY"), ("SI=F", "XAGUSD_FUTURES_PROXY")]


def train_rows(sessions, h, egp):
    """Non-overlapping training rows (cutoffs every h sessions from index 60 of the
    training sessions) whose realised close is dated before the hold-out."""
    sess = [s for s in sessions if s[0] < H.HOLDOUT_START]
    rows, _ = D.build_rows(sess, h, egp, False)
    return rows


def fit_k(rows, h):
    """Grid k minimising the mean 80% Winkler score of +/- k x sigma60 x sqrt(h) on the
    training rows. Ties go to the smaller k. None when fewer than MIN_TRAIN_ROWS rows."""
    if len(rows) < MIN_TRAIN_ROWS:
        return None
    best, bk = None, None
    for k in K_GRID:
        m = sum(D.winkler(r["real"], -k * r["sigma"] * math.sqrt(h) * 100, k * r["sigma"] * math.sqrt(h) * 100)
                for r in rows) / len(rows)
        if best is None or m < best - 1e-12:
            best, bk = m, k
    return bk


def fill_k(rows, hname, k_ch):
    h = D.HORIZONS[hname]
    for r in rows:
        sq = r["sigma"] * math.sqrt(h) * 100
        r["half_v2"], r["half_naive"], r["half_ch"] = D.V2_K[hname] * sq, D.NAIVE_K * sq, k_ch * sq
        if r["real"] is not None:
            x = r["real"]
            r["is_v2"] = D.winkler(x, -r["half_v2"], r["half_v2"])
            r["is_naive"] = D.winkler(x, -r["half_naive"], r["half_naive"])
            r["is_ch"] = D.winkler(x, -r["half_ch"], r["half_ch"])
            r["is_zero"] = H.zero_is(x)
            r["in_v2"] = abs(x) <= r["half_v2"]
            r["in_ch"] = abs(x) <= r["half_ch"]


def tuples(rows, mature):
    cl = {}
    for r in rows:
        if r["cluster"] in mature:
            c = cl.setdefault(r["cluster"], [0, 0.0, 0.0, 0, 0, 0.0, 0.0, 0])
            c[0] += 1
            c[1] += r["is_ch"]
            c[2] += r["is_naive"]
            c[3] += r["in_ch"]
            c[4] += r["in_v2"]
            c[5] += r["is_zero"]
            c[6] += r["is_v2"]
    return list(cl.values())


def stat(s):
    n = sum(c[0] for c in s)
    isn = sum(c[2] for c in s)
    return {"rs_ch": 1 - sum(c[1] for c in s) / isn, "rs_v2": 1 - sum(c[6] for c in s) / isn,
            "cov_ch": sum(c[3] for c in s) / n, "cov_v2": sum(c[4] for c in s) / n, "n": n}


def pct(v, reps):
    v = sorted(v)
    return [v[int(0.025 * reps)], v[min(reps - 1, int(0.975 * reps))]]


def boot(cl, reps, seed):
    rng = random.Random(seed)
    k = len(cl)
    a, b, c = [], [], []
    for _ in range(reps):
        s = stat([cl[rng.randrange(k)] for _ in range(k)])
        a.append(s["rs_ch"])
        b.append(s["rs_ch"] - s["rs_v2"])
        c.append(s["cov_ch"])
    return {"range_skill_ch_ci95": pct(a, reps), "delta_vs_v2_ci95": pct(b, reps), "coverage_ch_ci95": pct(c, reps)}


def evaluate(cell, hname, rows, mature, k_ch, n_train, reps, seed, derived):
    """Per cell/horizon result block (after the gate has passed)."""
    scored = [r for r in rows if r["cluster"] in mature]
    info = {"k_fit": k_ch, "k_v2": D.V2_K[hname], "k_naive": D.NAIVE_K, "n_train_rows": n_train,
            "rows_intended": len(rows), "rows_matured": sum(r["matured"] for r in rows),
            "clusters_total": len({r["cluster"] for r in rows}), "clusters_mature": len(mature),
            "n": len(scored)}
    if k_ch is None:
        info["counts_only"] = True
        info["keep_rule"] = "NO FIT (fewer than %d training rows), counts only" % MIN_TRAIN_ROWS
        return info
    cl = tuples(scored, mature)
    info["clusters"] = len(cl)
    if len(cl) < H.MIN_CLUSTERS:
        info["counts_only"] = True
        info["keep_rule"] = "COUNTS ONLY (fewer than %d mature clusters)" % H.MIN_CLUSTERS
        return info
    s = stat(cl)
    info.update({"counts_only": False, "range_skill_ch_vs_naive": s["rs_ch"], "range_skill_v2_vs_naive": s["rs_v2"],
                 "delta_ch_minus_v2": s["rs_ch"] - s["rs_v2"], "coverage_ch": s["cov_ch"], "coverage_v2": s["cov_v2"]})
    info.update(boot(cl, reps, seed))
    lo, hi = info["coverage_ch_ci95"]
    conds = {"range_skill_ge_0.10": s["rs_ch"] >= H.KEEP_SKILL,
             "coverage_ci_overlaps_0.75_0.85": lo <= H.COV_BAND[1] and hi >= H.COV_BAND[0],
             "n_ge_30": s["n"] >= H.MIN_N, "clusters_ge_10": len(cl) >= H.MIN_CLUSTERS,
             "delta_vs_v2_ci_lower_gt_0": info["delta_vs_v2_ci95"][0] > 0}
    info["keep_rule_conditions"] = conds
    info["keep_rule_all_met"] = all(conds.values())
    info["keep_rule"] = ("DESCRIPTIVE ONLY (derived cross-rate)" if derived else
                         "KEEP-ELIGIBLE" if all(conds.values()) else "NOT KEEP-ELIGIBLE")
    return info


def run_fx(data_dir, asof, reps=D.REPS, seed=D.SEED):
    out = {"mode": "fx_fit_challenger", "holdout_start": H.HOLDOUT_START, "asof_utc_date": asof, "reps": reps,
           "seed": seed, "k_grid": [K_GRID[0], K_GRID[-1], 0.05], "gate": {"zero_move": []}, "cells": {}, "rows": []}
    prepared = []
    for name, egp in H.CELLS:
        sessions, counts = H.load_all(os.path.join(data_dir, name + ".csv"), asof)
        cell = {"load_counts": counts, "horizons": {}}
        out["cells"][name] = cell
        for hname, h in D.HORIZONS.items():
            tr = train_rows(sessions, h, egp)
            k = fit_k(tr, h)
            rows, _ = H.build_rows(sessions, h, egp, False)
            fill_k(rows, hname, k if k is not None else D.V2_K[hname])
            mature = H.mature_clusters(rows)
            prepared.append((name, hname, rows, mature, k, len(tr), cell))
    failed = False
    for name, hname, rows, mature, k, ntr, cell in prepared:
        scored = [r for r in rows if r["cluster"] in mature]
        if not scored:
            continue
        z, fires = H.zero_move_check(tuples(scored, mature_clusters_dummy(mature)))
        failed = failed or fires
        out["gate"]["zero_move"].append({"cell": name, "horizon": hname, "n": len(scored),
                                         "range_skill_zero_move_vs_naive": z, "positive_skill": fires})
    out["gate"]["stop_positive_skill"] = failed
    if failed:
        return out
    for name, hname, rows, mature, k, ntr, cell in prepared:
        cell["horizons"][hname] = evaluate(name, hname, rows, mature, k, ntr, reps, seed, name in H.CROSS)
        for r in rows:
            out["rows"].append(dict(r, cell=name, horizon=hname, in_mature_cluster=r["cluster"] in mature))
    return out


def mature_clusters_dummy(m):
    return m


# ---------------------------------------------------------------- metals
def load_metal(path, asof):
    """[(date, close, roll_flag)] Mon-Fri sessions, positive closes, bars on or after asof dropped."""
    out, null = [], 0
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            if r["date"] >= asof:
                continue
            if not r["close"] or float(r["close"]) <= 0:
                null += 1
                continue
            out.append((r["date"], float(r["close"]), r["roll_window"] == "1"))
    out.sort()
    return out, {"null_close_dropped": null}


def metal_rows(sess, h, sigma_mode="last60_unflagged"):
    """Cutoffs: first session >= HOLDOUT_START then every h sessions. The return ending on a
    flagged roll date is never used. sigma_mode 'last60_unflagged' (primary, DESIGN CHOICE):
    sample std of the 60 most recent unflagged returns ending at or before the cutoff;
    'window60_strict': unflagged returns inside the last 60 sessions only, row dropped when fewer
    than METAL_MIN_SIGMA_RETS remain. A row whose realised window (i, i+h] holds a flagged return is
    dropped. Dropped rows are counted by reason, not scored."""
    dates = [s[0] for s in sess]
    cl = [s[1] for s in sess]
    fl = [s[2] for s in sess]
    i0 = next((k for k, d in enumerate(dates) if d >= H.HOLDOUT_START), None)
    rows, drop = [], {"sigma_window_too_few_unflagged_returns": 0, "roll_flag_in_realised_window": 0}
    if i0 is None:
        return rows, drop
    i = i0
    while i < len(cl):
        if sigma_mode == "last60_unflagged":
            rets, j = [], i
            while j >= 1 and len(rets) < D.SIGMA_WINDOW:
                if not fl[j]:
                    rets.append(math.log(cl[j] / cl[j - 1]))
                j -= 1
        else:
            rets = [math.log(cl[j] / cl[j - 1]) for j in range(i - D.SIGMA_WINDOW + 1, i + 1) if not fl[j]]
        matured = i + h < len(cl)
        if len(rets) < (D.SIGMA_WINDOW if sigma_mode == "last60_unflagged" else METAL_MIN_SIGMA_RETS):
            drop["sigma_window_too_few_unflagged_returns"] += 1
        elif matured and any(fl[i + 1:i + h + 1]):
            drop["roll_flag_in_realised_window"] += 1
        else:
            m = sum(rets) / len(rets)
            sigma = math.sqrt(sum((x - m) ** 2 for x in rets) / (len(rets) - 1))
            real = math.log(cl[i + h] / cl[i]) * 100 if matured else None
            rows.append({"cutoff": dates[i], "cluster": dates[i][:7], "real": real, "sigma": sigma, "matured": matured})
        i += h
    return rows, drop


def run_metals(data_dir, asof, reps=D.REPS, seed=D.SEED, sigma_mode="last60_unflagged"):
    out = {"mode": "metals_futures_proxy_holdout", "label": "futures research proxy, NOT tradeable spot", "holdout_start": H.HOLDOUT_START,
           "asof_utc_date": asof, "reps": reps, "seed": seed, "sigma_mode": sigma_mode, "gate": {"zero_move": []}, "cells": {}, "rows": []}
    prepared = []
    for sym, fn in METALS:
        sess, counts = load_metal(os.path.join(data_dir, fn + ".csv"), asof)
        cell = {"symbol": sym, "load_counts": counts, "sessions": len(sess),
                "flagged_sessions_in_holdout": sum(1 for s in sess if s[0] >= H.HOLDOUT_START and s[2]),
                "sessions_in_holdout": sum(1 for s in sess if s[0] >= H.HOLDOUT_START), "horizons": {}}
        out["cells"][sym] = cell
        for hname, h in D.HORIZONS.items():
            rows, drop = metal_rows(sess, h, sigma_mode)
            H.fill(rows, hname)
            mature = H.mature_clusters(rows)
            prepared.append((sym, hname, rows, mature, drop, cell))
    failed = False
    for sym, hname, rows, mature, drop, cell in prepared:
        scored = [r for r in rows if r["cluster"] in mature]
        if not scored:
            continue
        z, fires = H.zero_move_check(H.cluster_tuples(scored, mature))
        failed = failed or fires
        out["gate"]["zero_move"].append({"cell": sym, "horizon": hname, "n": len(scored),
                                         "range_skill_zero_move_vs_naive": z, "positive_skill": fires})
    out["gate"]["stop_positive_skill"] = failed
    if failed:
        return out
    for sym, hname, rows, mature, drop, cell in prepared:
        scored = [r for r in rows if r["cluster"] in mature]
        info = {"rows_dropped_by_reason": drop, "rows_intended": len(rows), "rows_matured": sum(r["matured"] for r in rows),
                "clusters_total": len({r["cluster"] for r in rows}), "clusters_mature": len(mature), "n": len(scored)}
        cl = H.cluster_tuples(scored, mature) if scored else []
        info["clusters"] = len(cl)
        if len(cl) < H.MIN_CLUSTERS:
            info["counts_only"] = True
            info["keep_rule"] = "COUNTS ONLY (fewer than %d mature clusters)" % H.MIN_CLUSTERS
        else:
            n = info["n"]
            info.update({"counts_only": False, "mean_is_v2": sum(c[1] for c in cl) / n, "mean_is_naive": sum(c[2] for c in cl) / n,
                         "range_skill_v2_vs_naive": H.skill(cl), "coverage_v2": sum(c[3] for c in cl) / n,
                         "coverage_naive": sum(c[4] for c in cl) / n})
            info.update(H.boot(cl, reps, seed))
            kb = H.keep_block(info)
            info["keep_rule_conditions"], info["keep_rule_all_met"] = kb["conditions"], kb["all_met"]
            info["keep_rule"] = "RESEARCH PROXY: " + ("KEEP-ELIGIBLE" if kb["all_met"] else "NOT KEEP-ELIGIBLE")
        cell["horizons"][hname] = info
        for r in rows:
            out["rows"].append(dict(r, cell=sym, horizon=hname, in_mature_cluster=r["cluster"] in mature))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("fx", "metals"))
    ap.add_argument("--data", required=True)
    ap.add_argument("--asof", required=True)
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--sigma-mode", default="last60_unflagged", choices=("last60_unflagged", "window60_strict"))
    a = ap.parse_args(argv)
    res = run_fx(a.data, a.asof) if a.mode == "fx" else run_metals(a.data, a.asof, sigma_mode=a.sigma_mode)
    with open(a.out_json, "w") as f:
        json.dump(res, f, indent=1, sort_keys=True)
    if res["gate"]["stop_positive_skill"]:
        print("STOP: zero-move band shows positive skill; treat as leakage/bug")
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
