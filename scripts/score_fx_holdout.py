"""FX hold-out scoring run (INS-IMPROVE-156), per evaluation/pre_registration_fx_metals.md
(sections 2, 3, 7, 8). Numbers only. Stdlib only. Scores ONLY the hold-out block:
cutoffs dated HOLDOUT_START to the last matured session. Frozen v2 k, naive k,
5000 reps and seed are fixed constants; nothing is refit. Metals are not in this run.

Gate 1 (runs first, per cell/horizon/variant): zero-move falsification. A band
collapsed to [0, 0] has interval score 10 x |real| (alpha 0.2). If its RangeSkill
against the naive band is > 0 on any hold-out set, the run STOPS with exit code 3
and writes only the gate block: no v2 number is produced.

Gate 2 (pre-reg section 8): under MIN_CLUSTERS fully mature cutoff clusters for a
cell/horizon/variant the output is COUNTS ONLY (no skill, coverage or CI).
"""
import argparse
import csv
import datetime
import json
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import score_fx_descriptive as D  # noqa: E402

HOLDOUT_START = "2026-01-01"
MIN_CLUSTERS = 10
MIN_N = 30
KEEP_SKILL = 0.10
COV_BAND = (0.75, 0.85)
CELLS = [("EURUSD", False), ("USDJPY", False), ("USDEGP", True),
         ("SAREGP_DERIVED", True), ("AEDEGP_DERIVED", True)]
CROSS = {"SAREGP_DERIVED": "USDSAR", "AEDEGP_DERIVED": "USDAED"}


def gate_positive(skill_value):
    """The falsification gate fires on any positive zero-move skill."""
    return skill_value > 0


def zero_move_check(cl):
    """(RangeSkill of the [0,0] band vs naive, gate fires). Single call site
    for the falsification threshold: a positive value stops the run."""
    z = skill(cl, col=5)
    return z, gate_positive(z)


def zero_is(real):
    return D.winkler(real, 0.0, 0.0)


def load_all(path, asof):
    """Sessions for the whole history (training bars are only the point-in-time
    sigma warm-up). Bars dated on or after asof (UTC date of the run) are the
    partial day and are dropped (pre-reg section 3)."""
    s, counts = D.load_sessions(path, holdout="9999-12-31")
    n0 = len(s)
    s = [x for x in s if x[0] < asof]
    counts = dict(counts)
    counts["partial_day_sessions_dropped"] = n0 - len(s)
    counts.pop("holdout_rows_dropped_at_load", None)
    return s, counts


def build_rows(sessions, h, egp, drop_jumps):
    """(rows, intended, dropped_jump). Cutoffs: the first session dated >=
    HOLDOUT_START, then every h sessions. A cutoff whose realised close (index
    + h) does not exist yet is an INTENDED row that is not matured."""
    if egp:
        sessions = [s for s in sessions if s[0] >= D.EGP_FLOAT_FIRST and s[0] not in D.EGP_EXCLUDED]
    dates = [s[0] for s in sessions]
    closes = [s[1] for s in sessions]
    flags = D.jump_flags(closes) if egp else [False] * len(closes)
    i0 = next((k for k, d in enumerate(dates) if d >= HOLDOUT_START), None)
    rows, dropped = [], 0
    if i0 is None or i0 < D.SIGMA_WINDOW:
        return rows, dropped
    i = i0
    while i < len(closes):
        rets = [math.log(closes[j] / closes[j - 1]) for j in range(i - D.SIGMA_WINDOW + 1, i + 1)]
        mean = sum(rets) / len(rets)
        sigma = math.sqrt(sum((x - mean) ** 2 for x in rets) / (len(rets) - 1))
        matured = i + h < len(closes)
        end = min(i + h, len(closes) - 1)
        if drop_jumps and any(flags[i - D.SIGMA_WINDOW + 1:end + 1]):
            dropped += 1
        else:
            real = math.log(closes[i + h] / closes[i]) * 100 if matured else None
            rows.append({"cutoff": dates[i], "cluster": dates[i][:7], "real": real,
                         "sigma": sigma, "matured": matured})
        i += h
    return rows, dropped


def mature_clusters(rows):
    """Clusters whose every intended row has a realised close."""
    by = {}
    for r in rows:
        by.setdefault(r["cluster"], []).append(r["matured"])
    return {k for k, v in by.items() if all(v)}


def fill(rows, hname):
    h = D.HORIZONS[hname]
    for r in rows:
        r["half_v2"] = D.V2_K[hname] * r["sigma"] * math.sqrt(h) * 100
        r["half_naive"] = D.NAIVE_K * r["sigma"] * math.sqrt(h) * 100
        if r["real"] is not None:
            x = r["real"]
            r["is_v2"] = D.winkler(x, -r["half_v2"], r["half_v2"])
            r["is_naive"] = D.winkler(x, -r["half_naive"], r["half_naive"])
            r["is_zero"] = zero_is(x)
            r["in_v2"] = abs(x) <= r["half_v2"]
            r["in_naive"] = abs(x) <= r["half_naive"]


def cluster_tuples(rows, mature):
    cl = {}
    for r in rows:
        if r["cluster"] in mature:
            c = cl.setdefault(r["cluster"], [0, 0.0, 0.0, 0, 0, 0.0])
            c[0] += 1
            c[1] += r["is_v2"]
            c[2] += r["is_naive"]
            c[3] += r["in_v2"]
            c[4] += r["in_naive"]
            c[5] += r["is_zero"]
    return list(cl.values())


def skill(cl, col=1):
    return 1 - sum(c[col] for c in cl) / sum(c[2] for c in cl)


def boot(cl, reps, seed):
    rng = random.Random(seed)
    k = len(cl)
    rs, cv, cn = [], [], []
    for _ in range(reps):
        s = [cl[rng.randrange(k)] for _ in range(k)]
        n = sum(c[0] for c in s)
        rs.append(skill(s))
        cv.append(sum(c[3] for c in s) / n)
        cn.append(sum(c[4] for c in s) / n)
    out = {}
    for name, v in (("range_skill_ci95", rs), ("coverage_v2_ci95", cv), ("coverage_naive_ci95", cn)):
        v.sort()
        out[name] = [v[int(0.025 * reps)], v[min(reps - 1, int(0.975 * reps))]]
    return out


def keep_block(s):
    lo, hi = s["coverage_v2_ci95"]
    conds = {"range_skill_ge_0.10": s["range_skill_v2_vs_naive"] >= KEEP_SKILL,
             "coverage_ci_overlaps_0.75_0.85": lo <= COV_BAND[1] and hi >= COV_BAND[0],
             "n_ge_30": s["n"] >= MIN_N,
             "clusters_ge_10": s["clusters"] >= MIN_CLUSTERS}
    return {"conditions": conds, "all_met": all(conds.values())}


def cross_counts(data_dir, name, asof):
    """Dropped-date counts and overlap rate for a derived cross-rate, hold-out
    window [HOLDOUT_START, asof) on the raw input files (dates with a positive close)."""
    other = CROSS[name]

    def dates(fn):
        out = set()
        with open(os.path.join(data_dir, fn + ".csv"), newline="") as f:
            for r in csv.DictReader(f):
                d = r["date"]
                if HOLDOUT_START <= d < asof and r["close"] and float(r["close"]) > 0:
                    out.add(d)
        return out
    e, o = dates("USDEGP"), dates(other)
    common, union = e & o, e | o
    return {"window": [HOLDOUT_START, "before " + asof], "usdegp_dates": len(e), other.lower() + "_dates": len(o),
            "common_dates_kept": len(common), "dropped_usdegp_only": len(e - o),
            "dropped_%s_only" % other.lower(): len(o - e), "dropped_total": len(union - common),
            "overlap_rate_common_over_union": len(common) / len(union) if union else None,
            "overlap_rate_common_over_usdegp": len(common) / len(e) if e else None}


def run(data_dir, asof, reps=D.REPS, seed=D.SEED):
    out = {"holdout_start": HOLDOUT_START, "asof_utc_date": asof, "reps": reps, "seed": seed,
           "v2_k": D.V2_K, "naive_k": D.NAIVE_K, "min_clusters": MIN_CLUSTERS,
           "cells": {}, "rows": [], "gate": {"zero_move": []}}
    prepared = []
    for name, egp in CELLS:
        sessions, counts = load_all(os.path.join(data_dir, name + ".csv"), asof)
        cell = {"load_counts": counts, "sessions": len(sessions), "horizons": {}}
        if name in CROSS:
            cell["cross_rate_counts"] = cross_counts(data_dir, name, asof)
        variants = [("all_rows", False), ("jump_days_excluded", True)] if egp else [("all_rows", False)]
        for hname, h in D.HORIZONS.items():
            for vname, dj in variants:
                rows, dropped = build_rows(sessions, h, egp, dj)
                fill(rows, hname)
                mature = mature_clusters(rows)
                scored = [r for r in rows if r["cluster"] in mature]
                prepared.append((name, hname, vname, rows, scored, mature, dropped, cell))
                out["cells"][name] = cell
    # Gate 1 first: nothing else is computed until every zero-move check is done.
    failed = False
    for name, hname, vname, rows, scored, mature, dropped, cell in prepared:
        if not scored:
            continue
        cl = cluster_tuples(scored, mature)
        z, fires = zero_move_check(cl)
        ok = not fires
        failed = failed or not ok
        out["gate"]["zero_move"].append({"cell": name, "horizon": hname, "rows": vname, "n": len(scored),
                                         "range_skill_zero_move_vs_naive": z, "positive_skill": not ok})
    out["gate"]["stop_positive_skill"] = failed
    if failed:
        return out
    for name, hname, vname, rows, scored, mature, dropped, cell in prepared:
        key = "%s/%s" % (hname, vname)
        info = {"rows_intended": len(rows), "rows_matured": sum(r["matured"] for r in rows),
                "rows_in_mature_clusters": len(scored), "clusters_total": len({r["cluster"] for r in rows}),
                "clusters_mature": len(mature), "rows_dropped_for_jump_days": dropped}
        if not scored:
            info["n"] = 0
            cell["horizons"][key] = info
            continue
        cl = cluster_tuples(scored, mature)
        n = sum(c[0] for c in cl)
        info.update({"n": n, "clusters": len(cl), "first_cutoff": min(r["cutoff"] for r in rows),
                     "last_cutoff": max(r["cutoff"] for r in rows)})
        if len(cl) < MIN_CLUSTERS:
            info["counts_only"] = True
            info["keep_rule"] = "COUNTS ONLY (fewer than %d mature clusters)" % MIN_CLUSTERS
        else:
            info["counts_only"] = False
            info.update({"mean_is_v2": sum(c[1] for c in cl) / n, "mean_is_naive": sum(c[2] for c in cl) / n,
                         "range_skill_v2_vs_naive": skill(cl),
                         "coverage_v2": sum(c[3] for c in cl) / n, "coverage_naive": sum(c[4] for c in cl) / n})
            info.update(boot(cl, reps, seed))
            kb = keep_block(info)
            info["keep_rule_conditions"] = kb["conditions"]
            info["keep_rule_all_met"] = kb["all_met"]
            if name in CROSS:
                info["keep_rule"] = "DESCRIPTIVE ONLY (derived cross-rate)"
            else:
                info["keep_rule"] = "KEEP-ELIGIBLE" if kb["all_met"] else "NOT KEEP-ELIGIBLE"
        cell["horizons"][key] = info
        for r in rows:
            out["rows"].append(dict(r, cell=name, horizon=hname, variant=vname,
                                    in_mature_cluster=r["cluster"] in mature))
    return out


def render(res):
    L = ["# FX hold-out run (numbers only)", "",
         "Hold-out sessions %s to the last matured session (asof UTC date %s, partial day dropped). v2 k %s (frozen, not refit), "
         "naive k %s, %d reps, seed %d, whole-cluster resampling, cluster = calendar month of the cutoff." % (
             res["holdout_start"], res["asof_utc_date"], res["v2_k"], res["naive_k"], res["reps"], res["seed"]), "",
         "Zero-move gate (RangeSkill of a [0,0] band vs naive; positive = stop):", ""]
    for g in res["gate"]["zero_move"]:
        L.append("- %s %s %s n=%d: %.4f" % (g["cell"], g["horizon"], g["rows"], g["n"], g["range_skill_zero_move_vs_naive"]))
    if res["gate"]["stop_positive_skill"]:
        L += ["", "STOPPED: positive zero-move skill; no v2 numbers produced."]
        return "\n".join(L) + "\n"
    L += ["", "| Cell | Horizon/rows | n | mature clusters | RangeSkill [CI] | cov v2 [CI] | rule |", "|---|---|---|---|---|---|---|"]
    for cn, cell in res["cells"].items():
        for hk, s in cell["horizons"].items():
            if s.get("counts_only") is False:
                L.append("| %s | %s | %d | %d | %.4f [%.4f, %.4f] | %.3f [%.3f, %.3f] | %s |" % (
                    cn, hk, s["n"], s["clusters"], s["range_skill_v2_vs_naive"], *s["range_skill_ci95"],
                    s["coverage_v2"], *s["coverage_v2_ci95"], s["keep_rule"]))
            else:
                L.append("| %s | %s | %s | %s | counts only | counts only | %s |" % (
                    cn, hk, s.get("n", 0), s.get("clusters", 0), s.get("keep_rule", "no matured rows")))
    for cn, cell in res["cells"].items():
        if "cross_rate_counts" in cell:
            L += ["", "%s: %s" % (cn, json.dumps(cell["cross_rate_counts"], sort_keys=True))]
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--asof", required=True, help="UTC date of the run; bars on or after it are partial and dropped")
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--out-md", required=True)
    ap.add_argument("--reps", type=int, default=D.REPS)
    a = ap.parse_args(argv)
    if a.reps != D.REPS:
        print("refusing: --reps must be the registered %d" % D.REPS)
        return 2
    res = run(a.data, a.asof, a.reps)
    with open(a.out_json, "w") as f:
        json.dump(res, f, indent=1, sort_keys=True)
    with open(a.out_md, "w") as f:
        f.write(render(res))
    if res["gate"]["stop_positive_skill"]:
        print("STOP: zero-move band shows positive skill on the hold-out; treat as leakage/bug")
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
