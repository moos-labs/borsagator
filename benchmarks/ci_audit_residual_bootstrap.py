#!/usr/bin/env python3
"""Cluster-preserving residual bootstrap audit of the keep rule
(INS-IMPROVE-001 round 9 item 2; Muhammad's call (c), relayed in Moos
Slack 1795722327.752229). DESCRIPTIVE ONLY: no verdict key or word is
produced, nothing is adopted, scripts/ensemble.py and frozen values are
untouched.

Question: if the world looked like the training rows, how would the
keep rule's legs behave on a set of untouched rows of the same shape?
Shape of the audit (the pre-registration):
  1. FIT on training rows only (cells <= --max-cell, default 47): per
     horizon, the band half-width factor k (R.K_GRID, minimum mean
     Winkler IS alpha 0.2) over the standardised residuals
       z = realised move / (naive half / 1.2816 x mult),
     i.e. the move in units of the capture's own sigma x sqrt(sessions).
  2. RESAMPLE REAL RESIDUALS BY WHOLE CUTOFF CLUSTERS. The training
     rows are grouped by as_of per horizon; a cluster is the list of
     residuals of every ticker at one cutoff. Each test cutoff cluster
     draws ONE whole training cluster (with replacement) and a single
     sign flip w = +/-1 for the whole cluster; the drawn cluster's
     residuals are shuffled and assigned to the test cluster's rows
     (wrapping if the test cluster is larger). Residuals are never
     drawn individually, so the cross-sectional co-movement inside a
     cutoff, which is what makes the effective n the cluster count,
     survives the resample. The sign flip keeps the world symmetric.
  3. REGENERATE the untouched-cell returns: synthetic move = w x z x
     (the test row's own scale x mult). Test rows keep their real
     tickers, cutoffs, sigmas and horizons.
  4. RE-SCORE each replicate (default 1000): RangeSkill of the fitted-k
     band against the naive band, coverage, the cutoff-clustered
     RangeSkill CI (lower bound > 0 leg) and coverage CI (overlaps
     [0.75, 0.85] with the 0.15 width cap) using the scorers' own
     bootstrap (R._boot, by as_of, --inner-reps draws).
Reported per horizon: the replicate distribution (2.5%, median, 97.5%)
of RangeSkill and coverage, the share of replicates where each leg holds
and where both hold ("training-world pass rate"), and the observed
values on the real test rows with their percentile in the replicate
distribution. Raw n and cutoff-cluster counts are printed together
(train and test). A horizon with fewer than 2 training or test
clusters is reported as undefined, never as a number.

Rows: captures with a cell number only (unnumbered captures are
dropped). Test cells >= --min-cell (default 48, descriptive: those
cells informed earlier decisions).

Usage:
  python3 benchmarks/ci_audit_residual_bootstrap.py --captures DIR ...
      [--max-cell 47] [--min-cell 48] [--reps 1000] [--inner-reps 200]
      [--seed N] [--json OUT]
"""
import argparse
import json
import os
import random
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import replay_band_candidates as R  # noqa: E402
import score_adoption_594 as A  # noqa: E402
import backtest_score as bs  # noqa: E402

HORIZONS = A.HORIZONS
NAIVE_K = 1.2816
MIN_CLUSTERS = 2
DEFAULT_REPS = 1000
DEFAULT_INNER = 200


def scale_of(row):
    """Row's own scale in pp: sigma x sqrt(sessions) x 100 x mult."""
    return row["naive_half"] / NAIVE_K * row.get("mult", 1.0)


def usable(row):
    return (row.get("naive_half") or 0) > 0 and row.get("real") is not None


def residual_clusters(rows):
    """{horizon: {as_of: [z]}} from training rows."""
    out = {h: {} for h in HORIZONS}
    for r in rows:
        if r["horizon"] in out and usable(r):
            out[r["horizon"]].setdefault(r["as_of"], []).append(
                r["real"] / scale_of(r))
    return out


def fit_k(zs):
    """Grid k minimising mean Winkler IS of [-k, k] over z (unit
    scale); None without residuals."""
    if not zs:
        return None
    best, best_k = None, None
    for k in R.K_GRID:
        m = sum(bs.winkler_is(z, -k, k) for z in zs) / len(zs)
        if best is None or m < best - 1e-12:
            best, best_k = m, k
    return best_k


def fit(train_rows):
    cl = residual_clusters(train_rows)
    ks = {h: fit_k([z for c in cl[h].values() for z in c])
          for h in HORIZONS}
    return cl, ks


def make_pair(row, real, k):
    sc = scale_of(row)
    half = k * sc
    nh = row["naive_half"]
    return {"ticker": row["ticker"], "as_of": row["as_of"],
            "horizon": row["horizon"],
            "is_naive": bs.winkler_is(real, -nh, nh),
            "is_ch": bs.winkler_is(real, -half, half),
            "in_ch": abs(real) <= half, "real": real}


def observed_pairs(test_rows, ks):
    return [make_pair(r, r["real"], ks[r["horizon"]])
            for r in test_rows if usable(r) and ks.get(r["horizon"])]


def synthetic_pairs(test_rows, train_cl, ks, rng):
    """One replicate: regenerated moves, scored with the fitted k."""
    pairs = []
    for h in HORIZONS:
        pool = [train_cl[h][a] for a in sorted(train_cl[h])]
        if not pool or ks.get(h) is None:
            continue
        by = {}
        for r in test_rows:
            if r["horizon"] == h and usable(r):
                by.setdefault(r["as_of"], []).append(r)
        for a in sorted(by):
            src = list(pool[rng.randrange(len(pool))])
            rng.shuffle(src)
            w = 1.0 if rng.random() < 0.5 else -1.0
            for j, r in enumerate(by[a]):
                z = w * src[j % len(src)]
                pairs.append(make_pair(r, z * scale_of(r), ks[h]))
    return pairs


def legs(pairs_h, inner, seed):
    """Skill, coverage and the two keep-rule legs for one horizon."""
    skill = A.range_skill(pairs_h, "ch")
    n = len(pairs_h)
    cov = sum(p["in_ch"] for p in pairs_h) / n if n else None
    sk_draws, cov_draws = R._boot(pairs_h, "as_of", inner, seed)
    lo, _ = A.percentile_ci(sk_draws)
    cci = list(A.percentile_ci(cov_draws))
    return {"skill": skill, "coverage": cov,
            "skill_leg": lo is not None and lo > 0,
            "coverage_leg": R.coverage_ci_ok(cci, R.COV_BAND)}


def quantile(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(q * len(xs)))] if xs else None


def audit(train_rows, test_rows, reps=DEFAULT_REPS, inner=DEFAULT_INNER,
          seed=A.DEFAULT_SEED):
    train_cl, ks = fit(train_rows)
    obs = observed_pairs(test_rows, ks)
    out = {}
    rng = random.Random(seed)
    reps_by_h = {h: [] for h in HORIZONS}
    test_cl = {h: len({r["as_of"] for r in test_rows
                       if r["horizon"] == h and usable(r)})
               for h in HORIZONS}
    for i in range(reps):
        pairs = synthetic_pairs(test_rows, train_cl, ks, rng)
        for h in HORIZONS:
            hp = [p for p in pairs if p["horizon"] == h]
            if hp and len({p["as_of"] for p in hp}) >= MIN_CLUSTERS:
                reps_by_h[h].append(legs(hp, inner, seed + i))
    for h in HORIZONS:
        tr = train_cl[h]
        cell = {"k": ks[h], "train_rows": sum(len(v) for v in tr.values()),
                "train_clusters": len(tr), "test_clusters": test_cl[h],
                "test_rows": len([p for p in obs if p["horizon"] == h]),
                "replicates": len(reps_by_h[h])}
        if (len(tr) < MIN_CLUSTERS or test_cl[h] < MIN_CLUSTERS
                or not reps_by_h[h]):
            cell["defined"] = False
            out[h] = cell
            continue
        rs = reps_by_h[h]
        sk = [r["skill"] for r in rs if r["skill"] is not None]
        cv = [r["coverage"] for r in rs]
        ob = legs([p for p in obs if p["horizon"] == h], inner, seed)
        cell.update({
            "defined": True,
            "skill_q": [quantile(sk, q) for q in (0.025, 0.5, 0.975)],
            "coverage_q": [quantile(cv, q) for q in (0.025, 0.5, 0.975)],
            "skill_leg_rate": sum(r["skill_leg"] for r in rs) / len(rs),
            "coverage_leg_rate": sum(r["coverage_leg"] for r in rs)
            / len(rs),
            "both_legs_rate": sum(r["skill_leg"] and r["coverage_leg"]
                                  for r in rs) / len(rs),
            "observed": {"skill": ob["skill"], "coverage": ob["coverage"],
                         "skill_leg": ob["skill_leg"],
                         "coverage_leg": ob["coverage_leg"],
                         "skill_percentile": (
                             sum(1 for x in sk if x <= ob["skill"])
                             / len(sk) if ob["skill"] is not None and sk
                             else None)}})
        out[h] = cell
    return out


def _f(v, nd=3):
    return "n/a" if v is None else "%.*f" % (nd, v)


def render(res, reps, inner):
    L = ["Cluster-preserving residual bootstrap audit (descriptive "
         "only): %d replicates, %d inner draws" % (reps, inner)]
    for h in HORIZONS:
        c = res[h]
        L.append("%s: train raw n=%d in %d clusters, test raw n=%d in %d "
                 "clusters, fitted k %s"
                 % (h, c["train_rows"], c["train_clusters"],
                    c["test_rows"], c["test_clusters"], _f(c["k"], 2)))
        if not c["defined"]:
            L.append("  undefined (needs >= %d training and test "
                     "clusters)" % MIN_CLUSTERS)
            continue
        sq, cq, ob = c["skill_q"], c["coverage_q"], c["observed"]
        L.append("  replicates RangeSkill [2.5%%, median, 97.5%%] %s %s %s"
                 "  coverage %s %s %s"
                 % (_f(sq[0]), _f(sq[1]), _f(sq[2]), _f(cq[0]),
                    _f(cq[1]), _f(cq[2])))
        L.append("  legs hold in the training world: RangeSkill CI lower "
                 "> 0 %s, coverage CI overlap with cap %s, both %s"
                 % (_f(c["skill_leg_rate"]), _f(c["coverage_leg_rate"]),
                    _f(c["both_legs_rate"])))
        L.append("  observed: RangeSkill %s (percentile %s of the "
                 "replicates), coverage %s"
                 % (_f(ob["skill"]), _f(ob["skill_percentile"]),
                    _f(ob["coverage"])))
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.
                                 RawDescriptionHelpFormatter)
    ap.add_argument("--captures", nargs="+", required=True)
    ap.add_argument("--max-cell", type=int, default=47)
    ap.add_argument("--min-cell", type=int, default=48)
    ap.add_argument("--reps", type=int, default=DEFAULT_REPS)
    ap.add_argument("--inner-reps", type=int, default=DEFAULT_INNER)
    ap.add_argument("--seed", type=int, default=A.DEFAULT_SEED)
    ap.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    allc = [c for c in A.find_captures(a.captures, None)
            if A.cell_number(c) is not None]
    train_caps = [c for c in allc if A.cell_number(c) <= a.max_cell]
    test_caps = [c for c in allc if A.cell_number(c) >= a.min_cell]
    train_rows, _ = R.build_rows(train_caps, allc)
    test_rows, _ = R.build_rows(test_caps, allc)
    res = audit(train_rows, test_rows, a.reps, a.inner_reps, a.seed)
    print(render(res, a.reps, a.inner_reps))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump({"descriptive": True, "max_cell": a.max_cell,
                       "min_cell": a.min_cell, "reps": a.reps,
                       "inner_reps": a.inner_reps, "seed": a.seed,
                       "results": res}, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
