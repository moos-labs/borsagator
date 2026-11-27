#!/usr/bin/env python3
"""Audit of the technicals-tilt KEEP reading (INS-IMPROVE-001 round 23
item 1; brief: Moos Slack 1795736150.489689). DESCRIPTIVE ONLY: no
verdict key or verdict line in text or JSON, no scorer or frozen value is
changed, and per Muhammad's round-8 ruling no reading here is an
adoption by itself (it needs this audit plus forward confirmation).

The question: the tilt scorer (score_tilt_technicals_594, cells >= 73)
reads week and month as KEEP on 5 cutoff clusters. Does that reading
survive the stricter views already on the record? Per horizon this
prints, on the SAME matured rows the scorer uses (its own score_pairs):
  1. the scorer's own two legs: RangeSkill cutoff-CI lower bound > 0,
     and the (uncapped) coverage CI overlap with [0.75, 0.85];
  2. the 10-cluster bar: cutoff clusters >= 10 (the audit minimum;
     MIN_CUTOFFS stays 2 in code until the cycle rules);
  3. the ticker-block view: RangeSkill ticker-block CI lower bound > 0
     (diagnostic, the tilt rule does not use it);
  4. the 0.15 cap applied: the coverage CI width and
     replay_band_candidates.coverage_ci_ok (overlap AND width <= 0.15);
  5. the ci_audit machinery on the cutoff clusters: jackknife,
     sign-flip permutation and wild cluster bootstrap, via
     ci_audit.audit_pairs (name "tilt");
  6. leave-one-cutoff-out: the cutoff-clustered skill and CI lower
     bound with each cutoff dropped, and the per-cutoff skill, so a
     single cutoff carrying the reading is visible.
Each is printed as a number plus a yes/no for the leg it names; the
legs are not combined into a word.

Usage:
  python3 benchmarks/audit_tilt_keep.py --captures DIR ...
      [--min-cell 73] [--reps 5000] [--seed N] [--json OUT]
"""
import argparse
import json
import os
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import score_adoption_594 as A  # noqa: E402
import score_tilt_technicals_594 as T  # noqa: E402
import replay_band_candidates as R  # noqa: E402
import ci_audit as CA  # noqa: E402

HORIZONS = A.HORIZONS
CLUSTER_BAR = 10          # audit minimum (#774), not a code gate
_f = lambda v, nd=3: "n/a" if v is None else "%.*f" % (nd, v)  # noqa: E731


def _lo(ci):
    return ci[0] if ci and ci[0] is not None else None


def scorer_legs(cell):
    """The tilt scorer's own legs, from T.evaluate's cell."""
    cci = cell["coverage_ci_cutoff"]
    lo = _lo(cell["skill_ci_cutoff"])
    cov_ok = R.coverage_ci_ok(cci, (T.COV_LO, T.COV_HI))
    return {"skill_ci_lower": lo,
            "skill_leg": lo is not None and lo > 0,
            "coverage_ci": list(cci), "coverage_leg": cov_ok}


def _eval_h(hp, reps, seed):
    """T.evaluate on one horizon's rows (re-tagged), same draws."""
    tag = [dict(p, horizon="day") for p in hp]
    return T.evaluate(tag, reps, seed)["day"]


def leave_one_cutoff_out(hp, reps, seed):
    """Per cutoff dropped: remaining clusters, skill, CI lower bound;
    plus each cutoff's own skill (D_c / N_c)."""
    cuts = sorted({p["as_of"] for p in hp})
    drops = []
    for c in cuts:
        rest = [p for p in hp if p["as_of"] != c]
        e = _eval_h(rest, reps, seed)
        drops.append({"dropped": c, "clusters": e["cutoffs"],
                      "range_skill": e["range_skill"],
                      "skill_ci_lower": _lo(e["skill_ci_cutoff"])})
    own = []
    for c in cuts:
        cl = CA.clusters([p for p in hp if p["as_of"] == c], "tilt")
        own.append({"as_of": c, "range_skill": CA.skill(cl)})
    return drops, own


def audit(pairs, reps=A.DEFAULT_REPS, seed=A.DEFAULT_SEED):
    base = T.evaluate(pairs, reps, seed)
    ca = CA.audit_pairs(pairs, "tilt", reps, seed)
    out = {}
    for h in HORIZONS:
        hp = [p for p in pairs if p["horizon"] == h]
        c = base[h]
        cci = c["coverage_ci_cutoff"]
        width = (cci[1] - cci[0]) if None not in cci else None
        tlo = _lo(c["skill_ci_ticker"])
        drops, own = leave_one_cutoff_out(hp, reps, seed)
        ca[h]["signflip"]["min_p"] = (
            0.5 ** c["cutoffs"] if c["cutoffs"] else None)
        out[h] = {
            "n": c["n"], "cutoffs": c["cutoffs"], "tickers": c["tickers"],
            "range_skill": c["range_skill"], "coverage": c["coverage"],
            "scorer": scorer_legs(c),
            "cluster_bar": {"needed": CLUSTER_BAR,
                            "met": c["cutoffs"] >= CLUSTER_BAR},
            "ticker_view": {"skill_ci_ticker": list(c["skill_ci_ticker"]),
                            "lower_gt_0": tlo is not None and tlo > 0},
            "cap": {"coverage_ci_width": width,
                    "cap": R.MAX_CI_WIDTH,
                    "coverage_ci_ok": R.coverage_ci_ok(cci, R.COV_BAND)},
            "ci_audit": {m: dict(ca[h][m]) for m in
                         ("existing", "jackknife", "signflip", "wild")},
            "leave_one_cutoff_out": drops, "per_cutoff_skill": own}
    return out


def _yn(b):
    return "yes" if b else "no"


def render(res, n_caps):
    L = ["Audit of the technicals-tilt reading (descriptive only; %d "
         "captures; no leg is combined into a word)" % n_caps]
    for h in HORIZONS:
        c = res[h]
        L.append("")
        L.append("%s: n=%d rows, %d cutoff clusters, %d tickers, "
                 "RangeSkill %s, coverage %s"
                 % (h, c["n"], c["cutoffs"], c["tickers"],
                    _f(c["range_skill"]), _f(c["coverage"])))
        s = c["scorer"]
        L.append("  scorer legs: skill CI lower %s > 0: %s | coverage CI "
                 "[%s, %s] overlaps 0.75-0.85, width <= 0.15: %s"
                 % (_f(s["skill_ci_lower"]), _yn(s["skill_leg"]),
                    _f(s["coverage_ci"][0]), _f(s["coverage_ci"][1]),
                    _yn(s["coverage_leg"])))
        L.append("  %d-cluster bar: %d clusters: %s"
                 % (c["cluster_bar"]["needed"], c["cutoffs"],
                    _yn(c["cluster_bar"]["met"])))
        t = c["ticker_view"]
        L.append("  ticker-block CI [%s, %s], lower > 0: %s"
                 % (_f(t["skill_ci_ticker"][0]),
                    _f(t["skill_ci_ticker"][1]), _yn(t["lower_gt_0"])))
        k = c["cap"]
        L.append("  0.15 cap: coverage CI width %s, overlap and width "
                 "<= %.2f: %s" % (_f(k["coverage_ci_width"]), k["cap"],
                                  _yn(k["coverage_ci_ok"])))
        a = c["ci_audit"]
        L.append("  ci_audit lower > 0: cutoff bootstrap %s [%s, %s] | "
                 "jackknife %s [%s, %s] | wild %s [%s, %s] | sign-flip "
                 "p %s (%s) < 0.025: %s"
                 % (_yn(a["existing"]["pass"]), _f(a["existing"]["ci"][0]),
                    _f(a["existing"]["ci"][1]), _yn(a["jackknife"]["pass"]),
                    _f(a["jackknife"]["ci"][0]),
                    _f(a["jackknife"]["ci"][1]), _yn(a["wild"]["pass"]),
                    _f(a["wild"]["ci"][0]), _f(a["wild"]["ci"][1]),
                    _f(a["signflip"]["p_one_sided"]),
                    a["signflip"]["mode"], _yn(a["signflip"]["pass"])))
        mp = c["ci_audit"]["signflip"]["min_p"]
        if mp is None:
            L.append("  note: no matured rows at this horizon, so the "
                     "sign-flip minimum p is unavailable")
        else:
            L.append("  note: with %d clusters the smallest attainable "
                     "sign-flip p is %s, so the sign-flip < 0.025 leg is "
                     "%s" % (c["cutoffs"], _f(mp, 4),
                             "unattainable" if mp >= 0.025
                             else "attainable"))
        L.append("  per-cutoff skill: " + ", ".join(
            "%s %s" % (o["as_of"], _f(o["range_skill"]))
            for o in c["per_cutoff_skill"]))
        L.append("  leave one cutoff out (skill, CI lower): " + "; ".join(
            "-%s %s, %s" % (d["dropped"], _f(d["range_skill"]),
                            _f(d["skill_ci_lower"]))
            for d in c["leave_one_cutoff_out"]))
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.
                                 RawDescriptionHelpFormatter)
    ap.add_argument("--captures", nargs="+", required=True)
    ap.add_argument("--min-cell", type=int, default=73)
    ap.add_argument("--reps", type=int, default=A.DEFAULT_REPS)
    ap.add_argument("--seed", type=int, default=A.DEFAULT_SEED)
    ap.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    caps = [c for c in A.find_captures(a.captures, a.min_cell)
            if A.cell_number(c) is not None]
    pairs, gaps = T.score_pairs(caps)
    res = audit(pairs, a.reps, a.seed)
    print(render(res, len(caps)))
    for g in gaps:
        print("gap: " + g)
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump({"descriptive": True, "captures": len(caps),
                       "min_cell": a.min_cell, "reps": a.reps,
                       "seed": a.seed, "results": res, "gaps": gaps},
                      fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
