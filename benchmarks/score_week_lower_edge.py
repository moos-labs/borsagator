"""Round 104 challenger: lower-edge shrinkage, pooled fit, scored on WEEK only.

Interval = [a x (-half) + (1 - a) x q_lo,  half]: the upper edge is the frozen
v2 edge (b = 1 fixed), the lower edge moves toward the baseline quantile q_lo.
ONE parameter a, fit on the POOLED covered rows (all horizons) of cells 1-47
only: grid 0, 0.05, ..., 1, ties to the larger a, gate 100 pooled covered rows.
Week-only scope is a post hoc choice made after the cells 48-90 descriptive
(stated in docs/round104_week_lower_edge_prereg.md). Day and month are COUNTS
ONLY and never KEEP-eligible.

Modes: fit (cells 1-47), describe (cells 48-90, uses --a-file), score (cells 91+
only, after the pre-registration is merged).
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import score_shrinkage_challenger as T  # noqa: E402

A, R = T.A, T.R
GRID = T.GRID
MIN_COVERED = 100
MIN_CLUSTERS = 10
SCORE_CELLS = (91, 10 ** 6)
SEED = A.DEFAULT_SEED


def fit_a(rows):
    """Pooled covered rows, b = 1. Returns (covered count, exclusion lines, a or None)."""
    ex = ["excluded row %s: close after freeze date" % r["key"] for r in rows if r["rdate"] >= T.FREEZE]
    cov = [r for r in rows if r["rdate"] < T.FREEZE]
    if len(cov) < MIN_COVERED:
        return len(cov), ex, None
    best, ba = None, None
    for a in GRID:
        m = sum(T.row_scores(r, a, 1.0)[0] for r in cov) / len(cov)
        if best is None or m < best - 1e-12 or (abs(m - best) <= 1e-12 and a > ba):
            best, ba = m, a
    return len(cov), ex, ba


def mature_clusters(caps, week_rows):
    """Cutoff clusters whose every intended row (one per capture of that cutoff)
    has a usable week row with a realised close. Returns (mature, all) cutoff sets."""
    intended = {}
    for c in caps:
        cutoff = os.path.basename(os.path.dirname(c))
        intended.setdefault(cutoff, set()).add(os.path.basename(c).upper())
    have = {}
    for r in week_rows:
        have.setdefault(r["base"], set()).add(r["ticker"].upper())
    mature = {k for k, v in intended.items() if v and v <= have.get(k, set())}
    return mature, set(intended)


def load(roots, lo, hi, ohlcv_dir):
    closes = {fn[:-4].replace("_", "."): T.load_closes(os.path.join(ohlcv_dir, fn))
              for fn in sorted(os.listdir(ohlcv_dir)) if fn.endswith(".csv")}
    _, caps = T.cell_caps(roots, lo, hi)
    rows, gaps = R.build_rows(caps)
    usable, ex = T.prepare(rows, closes)
    return caps, usable, ["excluded: %s" % g for g in gaps] + ex


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mode", choices=("fit", "describe", "score"))
    ap.add_argument("--captures", nargs="+", required=True)
    ap.add_argument("--ohlcv-dir", required=True)
    ap.add_argument("--a-file", default=None)
    ap.add_argument("--reps", type=int, default=A.DEFAULT_REPS)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    if a.reps != A.DEFAULT_REPS or a.seed != SEED:
        print("refusing: --reps must be %d and --seed %d" % (A.DEFAULT_REPS, SEED))
        return 2
    lo, hi = {"fit": T.FIT_CELLS, "describe": T.DESC_CELLS, "score": SCORE_CELLS}[a.mode]
    caps, usable, ex = load(a.captures, lo, hi, a.ohlcv_dir)
    if a.mode == "fit":
        n, fx, fa = fit_a(usable)
        print("COUNTS cells %d-%d, %d usable rows, pooled covered rows=%d (gate %d)" % (lo, hi, len(usable), n, MIN_COVERED))
        print("EXCLUSIONS (every one listed)")
        print("\n".join(ex + fx))
        print("FROZEN a (b=1 fixed): %s" % json.dumps(fa))
        if a.json:
            with open(a.json, "w", encoding="utf-8") as fh:
                json.dump({"a": fa, "covered": n}, fh)
        return 0
    if not a.a_file:
        print("refusing: %s needs --a-file from a fit run" % a.mode)
        return 2
    with open(a.a_file, encoding="utf-8") as fh:
        fa = json.load(fh)["a"]
    if fa is None:
        print("refusing: the fit produced no a (counts only)")
        return 2
    week = [r for r in usable if r["horizon"] == "week"]
    mature, allcl = mature_clusters(caps, week)
    print("COUNTS (before any statistic), cells %d-%d, frozen a=%s b=1" % (lo, hi, fa))
    for h in T.HORIZONS:
        hp = [r for r in usable if r["horizon"] == h]
        print("%s: rows=%d cutoff clusters=%d%s" % (h, len(hp), len({r["base"] for r in hp}),
              "" if h == "week" else " (counts only, not KEEP-eligible)"))
    print("week fully mature cutoff clusters=%d of %d" % (len(mature), len(allcl)))
    print("EXCLUSIONS (every one listed, before any statistic)")
    print("\n".join(ex))
    if a.mode == "score" and len(mature) < MIN_CLUSTERS:
        print("COUNTS ONLY: %d fully mature clusters < %d, no statistic printed" % (len(mature), MIN_CLUSTERS))
        return 0
    wk = [r for r in week if r["base"] in mature] if a.mode == "score" else week
    res = T.evaluate_pairs(wk, (fa, 1.0), a.reps, a.seed)["week"]
    print("%s week: n=%d, %d cutoffs, crossed-edge rows=%d" % (
        "SCORED" if a.mode == "score" else "DESCRIPTIVE ONLY", res["n"], res["cutoffs"], res["crossed"]))
    for k in res.get("crossed_keys", []):
        print("crossed edges: %s (reason: crossed edges, v2 interval used)" % k)
    print("  challenger: coverage %s RangeSkill %s coverage CI [%s, %s]" % (
        T.f3(res["cov_ch"]), T.f3(res["rs_ch"]), T.f3(res["cov_ci_cutoff"][0]), T.f3(res["cov_ci_cutoff"][1])))
    print("  frozen v2: coverage %s RangeSkill %s" % (T.f3(res["cov_v2"]), T.f3(res["rs_v2"])))
    print("  challenger minus v2 RangeSkill CI [%s, %s]" % (T.f3(res["delta_ci_cutoff"][0]), T.f3(res["delta_ci_cutoff"][1])))
    if a.mode == "score":
        d_lo = res["delta_ci_cutoff"][0]
        c_lo, c_hi = res["cov_ci_cutoff"]
        rules = [d_lo > 0, c_hi >= 0.75 and c_lo <= 0.85, (c_hi - c_lo) <= 0.15, len(mature) >= MIN_CLUSTERS]
        print("KEEP RULE (all four): RS-diff lower bound > 0: %s; coverage CI overlaps [0.75, 0.85]: %s; "
              "width <= 0.15: %s; >= 10 mature clusters: %s" % tuple(rules))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump({"mode": a.mode, "a": fa, "mature_clusters": sorted(mature), "result": res, "excluded": ex}, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
