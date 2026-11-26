#!/usr/bin/env python3
"""Shadow challenger: v2 band with the day k set to the naive k.

INS-IMPROVE-001 round 1, proposal P1 (target T4).

The frozen v2 day band uses k=1.15, narrower than the naive band's
1.2816. On cells 48-72 it covers 0.625 against a 0.80 target and
RangeSkill is -0.036, so the narrow width costs skill. This script
scores a challenger that differs from frozen v2 ONLY in the k table
(default: day = 1.2816, week and month unchanged). It does NOT touch
scripts/ensemble.py: V2_BAND_K is pinned by the #594 freeze tests
and is the "frozen v2" baseline of score_adoption_594.py, so
changing it would move the baseline under the comparison.

Pre-registered keep/reject rule (as set by Moos on #436 thread,
2026-11-26; decided before any new cell is scored; use only on
cells NOT seen when this rule was written, i.e. not cells 1-72):
  KEEP the challenger's day k when, on at least 30 untouched rows,
    (1) challenger day coverage >= 0.75, and
    (2) challenger day RangeSkill >= -0.036 (the frozen-v2 day
        RangeSkill on cells 48-72, an absolute floor).
  REJECT otherwise. Fewer than 30 rows is INSUFFICIENT: the numbers
  are printed but no keep/reject is issued.
How to read it: every backtest capture carries risk "none"
(benchmarks/audit_risk_mult_594.py, P0), so RISK_MULT is 1.00 and
the challenger at k = 1.2816 IS the naive band on day: its day
RangeSkill is exactly 0, which clears (2) by construction. The rule
is therefore a day-coverage test. The challenger-minus-v2 delta is
still printed for information. If P0 ever reports a risk level other
than "none" on new cells, re-read the result with that in mind.
Run on cells 48-72 the output is descriptive only: those cells were
seen before the rule was written.

Scoring uses scripts/backtest_score.py's score_capture for the
realised move, dividend handling and the naive range, so this cannot
disagree with the #436 scorer on what a cell realised. The challenger
band is rebuilt from the capture's sigma60 exactly as v2 is
(benchmarks/score_adoption_594.v2_horizons), including RISK_MULT.

Usage:
  python3 benchmarks/score_day_k_challenger_594.py --captures DIR
      [DIR ...] [--min-cell 73] [--k day=1.2816 --k week=1.28 ...]
      [--reps 5000] [--seed 20261125] [--json OUT]
"""
import argparse
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
import score_adoption_594 as A  # noqa: E402
import ensemble as ens_mod  # noqa: E402
import backtest_score as bs  # noqa: E402

HORIZONS = A.HORIZONS
SESSIONS = A.SESSIONS
MIN_ROWS = A.MIN_ROWS
COVERAGE_FLOOR = 0.75
SKILL_FLOOR_DAY = -0.036  # absolute floor, frozen v2 day RangeSkill


def challenger_k(overrides=None):
    """Frozen v2 k table with `overrides` applied (default day=naive)."""
    k = dict(ens_mod.V2_BAND_K)
    k["day"] = ens_mod.V2_NAIVE_K
    k.update(overrides or {})
    return k


def half_pct(ens, horizon, k):
    """Half-width in pp for k on this capture, as v2_horizons builds
    it (sigma60 x sqrt(sessions) x RISK_MULT)."""
    sigma60 = A._sigma60(ens)
    if not sigma60:
        return None
    mult = ens_mod.RISK_MULT.get((ens.get("risk") or {}).get("level"), 1.0)
    return k * sigma60 * math.sqrt(SESSIONS[horizon]) * mult * 100


def score_pairs(capture_dirs, k_ch):
    """One row per (ticker, cutoff, horizon) with the naive, frozen
    v2 and challenger interval scores and in-range flags."""
    pairs, gaps = [], []
    for cap in capture_dirs:
        try:
            rows, g = bs.score_capture(cap)
        except Exception as e:  # one bad cell never aborts
            gaps.append("%s: scoring failed: %s" % (cap, e))
            continue
        ens = bs.load_json(os.path.join(cap, "digest", "ensemble.json"))
        for r in rows:
            if (r.get("entrant") != "naive-range"
                    or r.get("status") != "matured"
                    or r.get("dividend_gap")):
                continue
            h = r["horizon"]
            real = r["realized_move_pct"]
            row = {"ticker": r["ticker"], "as_of": r["as_of"],
                   "horizon": h,
                   "is_naive": bs.winkler_is(
                       real, r["range_low_pct"], r["range_high_pct"]),
                   "in_naive": bool(r.get("in_range"))}
            ok = True
            for name, k in (("v2", ens_mod.V2_BAND_K[h]),
                            ("ch", k_ch[h])):
                half = half_pct(ens, h, k)
                if half is None:
                    ok = False
                    break
                row["is_" + name] = bs.winkler_is(real, -half, half)
                row["in_" + name] = abs(real) <= half
            if ok:
                pairs.append(row)
    return pairs, gaps


def _boot(pairs, names, by, reps, seed):
    groups = {}
    for p in pairs:
        groups.setdefault(p[by], []).append(p)
    keys = sorted(groups)
    rng = random.Random(seed)
    out = {n: [] for n in names}
    out["cov"] = {n: [] for n in names}
    out["diff"] = []
    if not keys:
        return out
    for _ in range(reps):
        draw = []
        for _ in keys:
            draw.extend(groups[rng.choice(keys)])
        sk = {n: A.range_skill(draw, n) for n in names}
        if any(v is None for v in sk.values()):
            continue
        for n in names:
            out[n].append(sk[n])
            out["cov"][n].append(sum(p["in_" + n] for p in draw)
                                 / len(draw))
        out["diff"].append(sk["ch"] - sk["v2"])
    return out


def evaluate(pairs, reps=A.DEFAULT_REPS, seed=A.DEFAULT_SEED):
    res = {}
    for h in HORIZONS:
        hp = [p for p in pairs if p["horizon"] == h]
        n = len(hp)
        cell = {"n": n, "cutoffs": len({p["as_of"] for p in hp}),
                "tickers": len({p["ticker"] for p in hp})}
        bc = _boot(hp, ("v2", "ch"), "as_of", reps, seed)
        for name in ("v2", "ch"):
            cell[name] = {
                "coverage": (sum(p["in_" + name] for p in hp) / n
                             if n else None),
                "range_skill": A.range_skill(hp, name),
                "skill_ci_cutoff": list(A.percentile_ci(bc[name])),
                "coverage_ci_cutoff": list(A.percentile_ci(
                    bc["cov"][name]))}
        cell["ch_minus_v2_skill"] = {
            "point": (None if not n else
                      (cell["ch"]["range_skill"] or 0)
                      - (cell["v2"]["range_skill"] or 0)),
            "ci_cutoff": list(A.percentile_ci(bc["diff"]))}
        res[h] = cell
    return res


def day_rule(cell):
    """Pre-registered keep/reject for the day k (see module doc)."""
    if cell["n"] < MIN_ROWS:
        return "INSUFFICIENT (n=%d < %d): no keep/reject" % (
            cell["n"], MIN_ROWS)
    cov = cell["ch"]["coverage"]
    sk = cell["ch"]["range_skill"]
    ok = cov is not None and cov >= COVERAGE_FLOOR \
        and sk is not None and sk >= SKILL_FLOOR_DAY
    return ("KEEP" if ok else "REJECT") + (
        " (day coverage %s vs floor %.2f; day RangeSkill %s vs floor "
        "%.3f)" % (_f(cov), COVERAGE_FLOOR, _f(sk), SKILL_FLOOR_DAY))


def _f(v, nd=3):
    return "n/a" if v is None else ("%.*f" % (nd, v))


def render(res, k_ch, n_caps, gaps):
    L = ["Day-k challenger vs frozen v2 (P1, INS-IMPROVE-001)",
         "captures: %d   frozen v2 k: %s   challenger k: %s"
         % (n_caps, json.dumps(ens_mod.V2_BAND_K), json.dumps(k_ch)),
         "CI: cutoff-block bootstrap, 95%, percentile.", ""]
    for h in HORIZONS:
        c = res[h]
        L.append("%s: n=%d rows, %d cutoffs, %d tickers"
                 % (h, c["n"], c["cutoffs"], c["tickers"]))
        for name, label in (("v2", "v2 frozen "), ("ch", "challenger")):
            x = c[name]
            L.append("  %s coverage %s [%s, %s]  RangeSkill %s [%s, %s]"
                     % (label, _f(x["coverage"]),
                        _f(x["coverage_ci_cutoff"][0]),
                        _f(x["coverage_ci_cutoff"][1]),
                        _f(x["range_skill"]),
                        _f(x["skill_ci_cutoff"][0]),
                        _f(x["skill_ci_cutoff"][1])))
        d = c["ch_minus_v2_skill"]
        L.append("  challenger minus v2 RangeSkill %s  CI [%s, %s]"
                 % (_f(d["point"]), _f(d["ci_cutoff"][0]),
                    _f(d["ci_cutoff"][1])))
    L += ["", "DAY RULE: " + day_rule(res["day"]), ""]
    L += ["gap: " + g for g in gaps]
    return "\n".join(L)


def _parse_k(items):
    out = {}
    for it in items or []:
        h, _, v = it.partition("=")
        if h not in HORIZONS:
            raise SystemExit("--k horizon must be one of %s" % (HORIZONS,))
        out[h] = float(v)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.
                                 RawDescriptionHelpFormatter)
    ap.add_argument("--captures", nargs="+", required=True)
    ap.add_argument("--min-cell", type=int, default=73,
                    help="first cell scored; default 73 = untouched")
    ap.add_argument("--k", action="append", metavar="H=K")
    ap.add_argument("--reps", type=int, default=A.DEFAULT_REPS)
    ap.add_argument("--seed", type=int, default=A.DEFAULT_SEED)
    ap.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    k_ch = challenger_k(_parse_k(a.k))
    caps = A.find_captures(a.captures, a.min_cell)
    pairs, gaps = score_pairs(caps, k_ch)
    res = evaluate(pairs, a.reps, a.seed)
    print(render(res, k_ch, len(caps), gaps))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump({"k_v2": ens_mod.V2_BAND_K, "k_challenger": k_ch,
                       "captures": len(caps), "results": res,
                       "gaps": gaps}, f, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
