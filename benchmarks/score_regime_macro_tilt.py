#!/usr/bin/env python3
"""Round 143: regime macro tilt, shadow scorer beside frozen v2 (stdlib).

Design and pre-registration: docs/round78_regime_macro_tilt_design.md. The
regime is read at the cutoff from the verified CBE decisions (rule-based:
tightening / easing / hold from the last decision strictly before as_of).
The tilt multiplies the frozen v2 half-width by w_regime, chosen on TRAINING
cells 1-47 only from the grid 0.9 / 1.0 / 1.1 (ties to 1.0); the centre stays
at 0 (reserved). Frozen v2 and scripts/ensemble.py are never edited.

Modes:
  counts    counts only, from capture directory names (no outcome is read):
            captures with / without a regime, cutoff clusters per regime and
            horizon, for training 1-47, descriptive 48-90 and untouched 91+.
  fit       cells 1-47 only: the per-regime width multipliers.
  describe  cells 48-90 only, DESCRIPTIVE numbers, no verdict word or key.
Cells 91+ are never scored here: no mode loads their outcomes, so there is no
KEEP output. `loop_bar` states the registered rule for a later untouched run.
"""
import argparse
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
import regime_macro_tilt_shadow as M  # noqa: E402

HORIZONS = A.HORIZONS
REGIMES = M.REGIME_LABELS
GRID = (0.9, 1.0, 1.1)
TRAIN_CELLS, DESC_CELLS = (1, 47), (48, 90)
UNTOUCHED_FROM = 91
MIN_CLUSTERS = 10
DECISIONS = os.path.join(ROOT, "evaluation", "macro_series", "cbe_decisions_verified_r143.json")


def band_of(cell):
    if cell is None:
        return None
    if TRAIN_CELLS[0] <= cell <= TRAIN_CELLS[1]:
        return "train 1-47"
    if DESC_CELLS[0] <= cell <= DESC_CELLS[1]:
        return "descriptive 48-90"
    return "untouched 91+" if cell >= UNTOUCHED_FROM else None


def capture_counts(captures, decisions):
    """Counts from capture paths only: {band: {...}}. A capture is
    <...>/<cutoff>/<TICKER>; its regime is read at the cutoff."""
    out = {}
    for c in captures:
        b = band_of(A.cell_number(c))
        if b is None:
            continue
        cutoff = os.path.basename(os.path.dirname(c))
        reg = M.regime_from_decisions(decisions, cutoff)
        o = out.setdefault(b, {"captures": 0, "with_regime": 0, "without_regime": 0, "by_regime": {}})
        o["captures"] += 1
        if reg is None:
            o["without_regime"] += 1
            continue
        o["with_regime"] += 1
        r = o["by_regime"].setdefault(reg, {"captures": 0, "cutoffs": set()})
        r["captures"] += 1
        r["cutoffs"].add(cutoff)
    for o in out.values():
        for r in o["by_regime"].values():
            r["cutoff_clusters"] = len(r.pop("cutoffs"))
    return out


def v2_half(r):
    return R.half_pct(r["v2_sigma"], r["horizon"], ens_mod.V2_BAND_K[r["horizon"]], r["mult"])


def regime_rows(rows, decisions):
    """(rows with 'regime' and 'half', exclusion lines)."""
    out, ex = [], []
    for r in rows:
        key = "%s %s %s" % (r["ticker"], str(r["as_of"])[:10], r["horizon"])
        if not r.get("v2_sigma"):
            ex.append("excluded row %s: missing or zero v2_sigma" % key)
            continue
        base = str(r["as_of"])[:10]
        reg = M.regime_from_decisions(decisions, base)
        if reg is None:
            ex.append("excluded row %s: no usable regime at the cutoff" % key)
            continue
        out.append(dict(r, regime=reg, half=v2_half(r), base=base, key=key))
    return out, ex


def mean_is(rows, w):
    return sum(bs.winkler_is(r["real"], -r["half"] * w, r["half"] * w) for r in rows) / len(rows)


def fit_weights(rows):
    """{regime: multiplier}. For each regime the grid value with the lowest
    mean Winkler IS over its training rows (all horizons pooled); 1.0 unless
    another value is lower by more than 1e-12 (ties go to 1.0); no rows -> 1.0."""
    w = {}
    for reg in REGIMES:
        rr = [r for r in rows if r["regime"] == reg]
        best, bw = (mean_is(rr, 1.0), 1.0) if rr else (None, 1.0)
        for g in GRID:
            if g == 1.0 or not rr:
                continue
            m = mean_is(rr, g)
            if m < best - 1e-12:
                best, bw = m, g
        w[reg] = bw
    return w


def _pair(r, weights):
    k = weights.get(r["regime"], 1.0)
    return {"as_of": r["base"], "is_naive": R.row_is(r, r["naive_half"]), "is_v2": R.row_is(r, r["half"]),
            "is_ch": bs.winkler_is(r["real"], -r["half"] * k, r["half"] * k),
            "in_ch": abs(r["real"]) <= r["half"] * k, "in_v2": abs(r["real"]) <= r["half"]}


def evaluate(rows, weights, reps, seed):
    res = {}
    for h in HORIZONS:
        pairs = [_pair(r, weights) for r in rows if r["horizon"] == h]
        if not pairs:
            res[h] = {"n": 0}
            continue
        groups = {}
        for p in pairs:
            groups.setdefault(p["as_of"], []).append(p)
        keys = sorted(groups)
        rng = random.Random(seed)
        dl, cv = [], []
        for _ in range(reps):
            draw = []
            for _k in keys:
                draw.extend(groups[rng.choice(keys)])
            cv.append(sum(p["in_ch"] for p in draw) / len(draw))
            x, y = A.range_skill(draw, "ch"), A.range_skill(draw, "v2")
            if x is None or y is None:
                continue
            dl.append(x - y)
        res[h] = {"n": len(pairs), "cutoffs": len(keys),
                  "rs_ch": A.range_skill(pairs, "ch"), "rs_v2": A.range_skill(pairs, "v2"),
                  "cov_ch": sum(p["in_ch"] for p in pairs) / len(pairs),
                  "cov_v2": sum(p["in_v2"] for p in pairs) / len(pairs),
                  "delta_ci_cutoff": list(A.percentile_ci(dl)), "cov_ci_cutoff": list(A.percentile_ci(cv))}
    return res


def loop_bar(clusters, delta_ci, cov_ci):
    """Registered keep rule for an UNTOUCHED horizon: RangeSkill-difference CI
    lower bound > 0 AND coverage CI overlaps [0.75, 0.85] with width <= 0.15
    AND >= 10 fully mature clusters. Fewer clusters: counts only (None)."""
    if clusters < MIN_CLUSTERS:
        return None
    lo, hi = cov_ci
    return bool(delta_ci[0] > 0 and lo <= 0.85 and hi >= 0.75 and round(hi - lo, 9) <= 0.15)


def f3(v):
    return "n/a" if v is None else "%.3f" % v


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mode", choices=("counts", "fit", "describe"))
    ap.add_argument("--captures", nargs="+", required=True)
    ap.add_argument("--decisions", default=DECISIONS)
    ap.add_argument("--weights", default=None, help="JSON written by fit (describe only)")
    ap.add_argument("--reps", type=int, default=A.DEFAULT_REPS)
    ap.add_argument("--seed", type=int, default=A.DEFAULT_SEED)
    ap.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    if a.reps != A.DEFAULT_REPS or a.seed != A.DEFAULT_SEED:
        print("refusing: --reps/--seed must be the registered %d / %d" % (A.DEFAULT_REPS, A.DEFAULT_SEED))
        return 2
    decisions, n_rej = M.load_decisions(a.decisions)
    print("DECISIONS %d usable, %d rejected (%s)" % (len(decisions), n_rej, os.path.basename(a.decisions)))
    allc = A.find_captures(a.captures, None)
    if a.mode == "counts":
        cc = capture_counts(allc, decisions)
        for b in ("train 1-47", "descriptive 48-90", "untouched 91+"):
            o = cc.get(b, {"captures": 0, "with_regime": 0, "without_regime": 0, "by_regime": {}})
            print("%s: captures=%d with regime=%d without regime=%d" % (b, o["captures"], o["with_regime"], o["without_regime"]))
            for reg in REGIMES:
                r = o["by_regime"].get(reg, {"captures": 0, "cutoff_clusters": 0})
                for h in HORIZONS:
                    print("  %s %s: captures=%d cutoff clusters=%d" % (reg, h, r["captures"], r["cutoff_clusters"]))
        print("untouched 91+ counts come from capture paths only; no outcome is loaded")
        if a.json:
            with open(a.json, "w", encoding="utf-8") as fh:
                json.dump({"counts": cc}, fh, indent=1)
        return 0
    lo, hi = TRAIN_CELLS if a.mode == "fit" else DESC_CELLS
    caps = [c for c in allc if A.cell_number(c) is not None and lo <= A.cell_number(c) <= hi]
    rows, gaps = R.build_rows(caps)
    usable, ex = regime_rows(rows, decisions)
    print("COUNTS cells %d-%d, %d rows built, %d usable" % (lo, hi, len(rows), len(usable)))
    for reg in REGIMES:
        for h in HORIZONS:
            rr = [r for r in usable if r["regime"] == reg and r["horizon"] == h]
            print("  %s %s: rows=%d cutoff clusters=%d" % (reg, h, len(rr), len({r["base"] for r in rr})))
    print("EXCLUSIONS (every one listed)")
    print("\n".join(["excluded: %s" % g for g in gaps if "rebuilt to 21" not in g] + ex))
    if a.mode == "fit":
        w = fit_weights(usable)
        print("FITTED WIDTH MULTIPLIERS (cells 1-47, grid %s, ties to 1.0, centre 0): %s" % (list(GRID), json.dumps(w)))
        if a.json:
            with open(a.json, "w", encoding="utf-8") as fh:
                json.dump({"weights": w, "rows": len(usable)}, fh, indent=1)
        return 0
    if not a.weights:
        print("refusing: describe needs --weights from a fit run")
        return 2
    w = json.load(open(a.weights, encoding="utf-8"))["weights"]
    res = evaluate(usable, w, a.reps, a.seed)
    print("DESCRIPTIVE ONLY cells %d-%d, %d reps seed %d, multipliers %s" % (lo, hi, a.reps, a.seed, json.dumps(w)))
    for h in HORIZONS:
        c = res[h]
        if not c["n"]:
            print("%s: no rows" % h)
            continue
        print("%s: n=%d, %d cutoffs" % (h, c["n"], c["cutoffs"]))
        print("  tilt: coverage %s RangeSkill %s coverage CI cutoff [%s, %s]" % (
            f3(c["cov_ch"]), f3(c["rs_ch"]), f3(c["cov_ci_cutoff"][0]), f3(c["cov_ci_cutoff"][1])))
        print("  frozen v2: coverage %s RangeSkill %s" % (f3(c["cov_v2"]), f3(c["rs_v2"])))
        print("  tilt minus v2 RangeSkill CI cutoff [%s, %s]" % (f3(c["delta_ci_cutoff"][0]), f3(c["delta_ci_cutoff"][1])))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump({"descriptive": True, "weights": w, "results": res}, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
