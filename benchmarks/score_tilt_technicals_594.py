#!/usr/bin/env python3
"""Pre-registered scorer for the technicals tilt on new cells.

INS-IMPROVE-001 round 2, technicals tilt (target T2).

The "tilt-technicals" entrant (scripts/backtest_score.py) is the
ensemble's own tilt_centre_pct with the v2 band half-width re-centred
on the tilt. On the seen cells 48-72 (25 archive captures, cell 70
included) it shows no skill (day -0.035, week -0.024, month -0.071
RangeSkill vs naive; coverage 0.640 / 0.760 / 0.520). This script scores it on cells NOT seen when the rule was
written. It does not touch scripts/ensemble.py or any frozen value.

Pre-registered keep/reject rule (written by Ins before cells 73-78
were scored). Provenance: the tilt thresholds (>= 5 tickers, >= 2
cutoffs, coverage band, CI test) are Ins's. Moos accepted the
forward-ledger rule and the plan to pre-register this one in Slack on
2026-11-26. Per horizon, on untouched cells only (cell >= 73):
  KEEP the tilt when, on at least 30 untouched rows over at least 5
  tickers and at least 2 cutoffs,
    (1) tilt RangeSkill vs naive has a cutoff-clustered 95% CI lower
        bound > 0, and
    (2) the cutoff-clustered tilt coverage CI overlaps 0.75-0.85
        (round 11 ruling by Moos; was point coverage within the band).
  REJECT when n, tickers and cutoffs are enough and (1) or (2) fails.
  INSUFFICIENT otherwise: numbers are printed, no keep/reject.
One scoring of cells 73-78, no re-fit, no change to the tilt.
Expected shape, stated before scoring: cells 73-78 are one cutoff
(2026-08-14) and 6 tickers, so 6 rows per horizon. The verdict on
them alone is INSUFFICIENT, and a cutoff-clustered CI over one
cutoff is undefined. The numbers are descriptive until more
untouched cells exist (the 2026-05-15 and 2026-02-13 sets are not
defined yet). Sentiment and agent tilts are NOT scored here: backtest
captures are 2-family, so they are judged on ledger/ledger.json.
Cells 48-72 give descriptive output only (seen).

Scoring uses scripts/backtest_score.py's score_capture for the
realised move, dividend handling and naive range, and
score_adoption_594's range_skill and percentile_ci.

Usage:
  python3 benchmarks/score_tilt_technicals_594.py --captures DIR
      [DIR ...] [--min-cell 73] [--reps 5000] [--seed 20261125]
      [--json OUT]
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
import score_adoption_594 as A  # noqa: E402
import backtest_score as bs  # noqa: E402

HORIZONS = A.HORIZONS
MIN_ROWS = A.MIN_ROWS
MIN_TICKERS = A.MIN_TICKERS
MIN_CUTOFFS = 2
COV_LO, COV_HI = 0.75, 0.85


def score_pairs(capture_dirs):
    """One row per (ticker, cutoff, horizon): naive and tilt interval
    scores and in-range flags, matured and not dividend-gapped."""
    pairs, gaps = [], []
    for cap in capture_dirs:
        try:
            rows, g = bs.score_capture(cap)
        except Exception as e:  # one bad cell never aborts
            gaps.append("%s: scoring failed: %s" % (cap, e))
            continue
        by = {}
        for r in rows:
            if r.get("status") != "matured" or r.get("dividend_gap"):
                continue
            if r.get("entrant") in ("naive-range", "tilt-technicals"):
                by[(r["entrant"], r["ticker"], r["as_of"],
                    r["horizon"])] = r
        for (ent, t, a, h), nv in sorted(by.items()):
            if ent != "naive-range":
                continue
            tl = by.get(("tilt-technicals", t, a, h))
            if tl is None or tl.get("range_low_pct") is None \
                    or nv.get("range_low_pct") is None:
                continue
            real = nv["realized_move_pct"]
            pairs.append({
                "ticker": t, "as_of": a, "horizon": h,
                "is_naive": bs.winkler_is(
                    real, nv["range_low_pct"], nv["range_high_pct"]),
                "is_tilt": bs.winkler_is(
                    real, tl["range_low_pct"], tl["range_high_pct"]),
                "in_tilt": bool(tl.get("in_range"))})
    return pairs, gaps


def _boot(pairs, by, reps, seed):
    groups = {}
    for p in pairs:
        groups.setdefault(p[by], []).append(p)
    keys = sorted(groups)
    rng = random.Random(seed)
    skill, cov = [], []
    if len(keys) < 2:
        return skill, cov
    for _ in range(reps):
        draw = []
        for _ in keys:
            draw.extend(groups[rng.choice(keys)])
        s = A.range_skill(draw, "tilt")
        if s is None:
            continue
        skill.append(s)
        cov.append(sum(p["in_tilt"] for p in draw) / len(draw))
    return skill, cov


def evaluate(pairs, reps=A.DEFAULT_REPS, seed=A.DEFAULT_SEED):
    res = {}
    for h in HORIZONS:
        hp = [p for p in pairs if p["horizon"] == h]
        n = len(hp)
        sk_c, cov_c = _boot(hp, "as_of", reps, seed)
        sk_t, _ = _boot(hp, "ticker", reps, seed)
        res[h] = {
            "n": n, "cutoffs": len({p["as_of"] for p in hp}),
            "tickers": len({p["ticker"] for p in hp}),
            "range_skill": A.range_skill(hp, "tilt"),
            "coverage": (sum(p["in_tilt"] for p in hp) / n
                         if n else None),
            "skill_ci_cutoff": list(A.percentile_ci(sk_c)),
            "skill_ci_ticker": list(A.percentile_ci(sk_t)),
            "coverage_ci_cutoff": list(A.percentile_ci(cov_c))}
    return res


def tilt_rule(cell):
    """Pre-registered keep/reject for one horizon (see module doc)."""
    if (cell["n"] < MIN_ROWS or cell["tickers"] < MIN_TICKERS
            or cell["cutoffs"] < MIN_CUTOFFS):
        return ("INSUFFICIENT (n=%d, tickers=%d, cutoffs=%d; need "
                ">=%d, >=%d, >=%d): no keep/reject"
                % (cell["n"], cell["tickers"], cell["cutoffs"],
                   MIN_ROWS, MIN_TICKERS, MIN_CUTOFFS))
    lo = cell["skill_ci_cutoff"][0]
    cov = cell["coverage"]
    cci = cell.get("coverage_ci_cutoff") or [None, None]
    cov_ok = (cci[0] is not None and cci[1] is not None
              and cci[0] <= COV_HI and cci[1] >= COV_LO)
    ok = lo is not None and lo > 0 and cov_ok
    return ("KEEP" if ok else "REJECT") + (
        " (RangeSkill CI lower bound %s vs 0; coverage %s, CI [%s, %s] "
        "must overlap %.2f-%.2f)"
        % (_f(lo), _f(cov), _f(cci[0]), _f(cci[1]), COV_LO, COV_HI))


def _f(v, nd=3):
    return "n/a" if v is None else ("%.*f" % (nd, v))


def render(res, n_caps, gaps):
    L = ["Technicals tilt vs naive (INS-IMPROVE-001 round 2)",
         "captures: %d   CI: 95%% percentile, cutoff and ticker blocks"
         % n_caps, ""]
    for h in HORIZONS:
        c = res[h]
        L.append("%s: n=%d rows, %d cutoffs, %d tickers"
                 % (h, c["n"], c["cutoffs"], c["tickers"]))
        L.append("  RangeSkill %s  cutoff CI [%s, %s]  ticker CI [%s, %s]"
                 % (_f(c["range_skill"]), _f(c["skill_ci_cutoff"][0]),
                    _f(c["skill_ci_cutoff"][1]),
                    _f(c["skill_ci_ticker"][0]),
                    _f(c["skill_ci_ticker"][1])))
        L.append("  coverage %s  cutoff CI [%s, %s]"
                 % (_f(c["coverage"]), _f(c["coverage_ci_cutoff"][0]),
                    _f(c["coverage_ci_cutoff"][1])))
        L.append("  RULE: " + tilt_rule(c))
    L += [""] + ["gap: " + g for g in gaps]
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.
                                 RawDescriptionHelpFormatter)
    ap.add_argument("--captures", nargs="+", required=True)
    ap.add_argument("--min-cell", type=int, default=73,
                    help="first cell scored; default 73 = untouched")
    ap.add_argument("--reps", type=int, default=A.DEFAULT_REPS)
    ap.add_argument("--seed", type=int, default=A.DEFAULT_SEED)
    ap.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    caps = A.find_captures(a.captures, a.min_cell)
    pairs, gaps = score_pairs(caps)
    res = evaluate(pairs, a.reps, a.seed)
    print(render(res, len(caps), gaps))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump({"captures": len(caps), "results": res,
                       "gaps": gaps}, f, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
