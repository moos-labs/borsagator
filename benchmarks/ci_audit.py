#!/usr/bin/env python3
"""CI audit of the keep-rule RangeSkill interval (INS-IMPROVE-006,
Moos round 8 GO). DESCRIPTIVE ONLY: no verdict is issued or changed,
nothing is fitted, scripts/ensemble.py and frozen values are untouched.

The keep rule's second leg is "RangeSkill CI lower bound > 0", where
the interval is a percentile cluster bootstrap: resample the as_of
clusters (cutoffs) with replacement, recompute
  RangeSkill = 1 - sum(IS_band) / sum(IS_naive)
(score_adoption_594.range_skill), 95% percentile interval, 5000 reps,
seed A.DEFAULT_SEED (the same draws replay_band_candidates._boot makes).
This script recomputes that interval three other ways on the same
matured rows and reports, per horizon, whether the lower-bound > 0 call
would change:
  1. jackknife: leave one cutoff out, SE from the delete-one estimates,
     interval = estimate +/- 1.96 x SE (also the delete-one min/max).
  2. sign-flip permutation: per-cutoff skill numerator D_c =
     sum(IS_naive - IS_band) over the cutoff; under "no skill" each D_c
     is symmetric about 0, so flip signs, statistic sum(D_c)/sum(N_c).
     One-sided p = P(stat* >= observed). Exact enumeration up to 16
     cutoffs, else 20000 Monte Carlo flips. "Pass" = p < 0.025, the
     one-sided counterpart of a 95% two-sided lower bound > 0.
  3. wild cluster bootstrap, Rademacher weights: residual e_c = D_c -
     s^ x N_c (s^ the observed skill); D*_c = s^ x N_c + w_c x e_c with
     w_c = +/-1; s* = sum(D*_c)/sum(N_c); 95% percentile interval,
     5000 reps. With k cutoffs there are only 2^k distinct weight
     draws, which is the known limit of Rademacher weights at small k.
Cluster = as_of (cutoff), as in the keep rule. All three are fixed-seed.

Rows: the frozen v2 band (scripts/ensemble.py V2_BAND_K, unchanged)
against the naive band on matured rows from the captures, cells >=
--min-cell (default 48, descriptive: those cells informed earlier
decisions). The audit functions take any pair dicts with is_naive and
is_<band>, so a challenger's rows audit the same way.

Usage:
  python3 benchmarks/ci_audit.py --captures DIR ... [--min-cell 48]
      [--reps 5000] [--json OUT]
"""
import argparse
import itertools
import json
import math
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
import ensemble as ens_mod  # noqa: E402

HORIZONS = A.HORIZONS
Z95 = 1.959964
EXACT_MAX = 16
MC_FLIPS = 20000


def clusters(pairs, name, by="as_of"):
    """[(D_c, N_c)] per cluster: D = sum(IS_naive - IS_name),
    N = sum(IS_naive). RangeSkill = sum D / sum N."""
    g = {}
    for p in pairs:
        d, n = g.get(p[by], (0.0, 0.0))
        g[p[by]] = (d + p["is_naive"] - p["is_" + name],
                    n + p["is_naive"])
    return [g[k] for k in sorted(g)]


def skill(cl):
    n = sum(c[1] for c in cl)
    return sum(c[0] for c in cl) / n if n > 0 else None


def existing_ci(cl, reps, seed):
    """Percentile cluster bootstrap, same draw scheme as _boot."""
    rng = random.Random(seed)
    k = len(cl)
    draws = []
    for _ in range(reps if k else 0):
        s = skill([cl[rng.randrange(k)] for _ in range(k)])
        if s is not None:
            draws.append(s)
    return A.percentile_ci(draws)


def jackknife_ci(cl):
    k = len(cl)
    est = skill(cl)
    if k < 2 or est is None:
        return None, None, None, None
    loo = [skill(cl[:i] + cl[i + 1:]) for i in range(k)]
    loo = [x for x in loo if x is not None]
    if len(loo) < 2:
        return None, None, None, None
    m = sum(loo) / len(loo)
    se = math.sqrt((len(loo) - 1) / len(loo)
                   * sum((x - m) ** 2 for x in loo))
    return est - Z95 * se, est + Z95 * se, min(loo), max(loo)


def signflip_p(cl, seed, flips=MC_FLIPS):
    """One-sided p for no skill; (p, mode)."""
    k = len(cl)
    obs = skill(cl)
    if obs is None or k == 0:
        return None, None
    den = sum(c[1] for c in cl)
    eps = 1e-12
    if k <= EXACT_MAX:
        hit = 0
        for signs in itertools.product((1, -1), repeat=k):
            if sum(s * c[0] for s, c in zip(signs, cl)) / den >= obs - eps:
                hit += 1
        return hit / float(2 ** k), "exact"
    rng = random.Random(seed)
    hit = 0
    for _ in range(flips):
        t = sum((1 if rng.random() < 0.5 else -1) * c[0] for c in cl) / den
        if t >= obs - eps:
            hit += 1
    return (hit + 1) / float(flips + 1), "monte-carlo"


def wild_ci(cl, reps, seed):
    est = skill(cl)
    if est is None:
        return None, None
    den = sum(c[1] for c in cl)
    resid = [c[0] - est * c[1] for c in cl]
    rng = random.Random(seed)
    draws = []
    for _ in range(reps):
        tot = 0.0
        for c, e in zip(cl, resid):
            tot += est * c[1] + (1 if rng.random() < 0.5 else -1) * e
        draws.append(tot / den)
    return A.percentile_ci(draws)


def audit_pairs(pairs, name, reps=A.DEFAULT_REPS, seed=A.DEFAULT_SEED):
    out = {}
    for h in HORIZONS:
        cl = clusters([p for p in pairs if p["horizon"] == h], name)
        est = skill(cl)
        cell = {"n_rows": sum(1 for p in pairs if p["horizon"] == h),
                "clusters": len(cl), "range_skill": est}
        lo, hi = existing_ci(cl, reps, seed)
        cell["existing"] = {"ci": [lo, hi], "pass": lo is not None
                            and lo > 0}
        jl, jh, mn, mx = jackknife_ci(cl)
        cell["jackknife"] = {"ci": [jl, jh], "loo_min": mn, "loo_max": mx,
                             "pass": jl is not None and jl > 0}
        p, mode = signflip_p(cl, seed)
        cell["signflip"] = {"p_one_sided": p, "mode": mode,
                            "pass": p is not None and p < 0.025}
        wl, wh = wild_ci(cl, reps, seed)
        cell["wild"] = {"ci": [wl, wh], "pass": wl is not None and wl > 0}
        base = cell["existing"]["pass"]
        cell["verdict_would_change_under"] = [
            m for m in ("jackknife", "signflip", "wild")
            if cell[m]["pass"] != base]
        out[h] = cell
    return out


def v2_pairs(rows):
    out = []
    for r in rows:
        if not r["v2_sigma"]:
            continue
        h = r["horizon"]
        half = R.half_pct(r["v2_sigma"], h, ens_mod.V2_BAND_K[h],
                          r["mult"])
        out.append({"ticker": r["ticker"], "as_of": r["as_of"],
                    "horizon": h,
                    "is_naive": R.row_is(r, r["naive_half"]),
                    "is_v2": R.row_is(r, half)})
    return out


def _f(v, nd=3):
    return "n/a" if v is None else ("%+.*f" % (nd, v))


def _ci(c):
    return "[%s, %s]" % (_f(c[0]), _f(c[1]))


def render(res, min_cell):
    L = ["CI AUDIT, DESCRIPTIVE ONLY, no verdict issued or changed. "
         "Frozen v2 band vs naive, cells >= %d, cluster = as_of." % min_cell]
    for h in HORIZONS:
        c = res[h]
        L.append("%s: %d rows, %d cutoffs, RangeSkill %s"
                 % (h, c["n_rows"], c["clusters"], _f(c["range_skill"])))
        L.append("  existing percentile cluster bootstrap %s  LB>0: %s"
                 % (_ci(c["existing"]["ci"]), c["existing"]["pass"]))
        j = c["jackknife"]
        L.append("  jackknife %s (delete-one range [%s, %s])  LB>0: %s"
                 % (_ci(j["ci"]), _f(j["loo_min"]), _f(j["loo_max"]),
                    j["pass"]))
        s = c["signflip"]
        L.append("  sign-flip one-sided p %s (%s)  p<0.025: %s"
                 % ("n/a" if s["p_one_sided"] is None
                    else "%.4f" % s["p_one_sided"], s["mode"], s["pass"]))
        L.append("  wild cluster (Rademacher) %s  LB>0: %s"
                 % (_ci(c["wild"]["ci"]), c["wild"]["pass"]))
        ch = c["verdict_would_change_under"]
        L.append("  LB>0 call differs from existing under: %s"
                 % (", ".join(ch) if ch else "none"))
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.
                                 RawDescriptionHelpFormatter)
    ap.add_argument("--captures", nargs="+", required=True)
    ap.add_argument("--min-cell", type=int, default=48)
    ap.add_argument("--reps", type=int, default=A.DEFAULT_REPS)
    ap.add_argument("--seed", type=int, default=A.DEFAULT_SEED)
    ap.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    allc = A.find_captures(a.captures, None)
    caps = [c for c in A.find_captures(a.captures, a.min_cell)
            if A.cell_number(c) is not None]
    rows, _gaps = R.build_rows(caps, allc)
    res = audit_pairs(v2_pairs(rows), "v2", a.reps, a.seed)
    print(render(res, a.min_cell))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump({"descriptive": True, "min_cell": a.min_cell,
                       "reps": a.reps, "seed": a.seed, "results": res},
                      fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
