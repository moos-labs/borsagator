#!/usr/bin/env python3
"""Paired delta against frozen v2 for the round 24-26 screens
(INS-IMPROVE-001 round 30, proposal A of docs/proposals-round-26.md).
DESCRIPTIVE ONLY, never a verdict.

Provenance: the GO for this paired-delta screen (pre-registered,
descriptive, no cells scored) is Muhammad's, relayed in Slack message
1795742631.225549. The method finding behind it is in
docs/proposals-round-26.md: screen_band_models.reading_p tests the
candidate's RangeSkill against 0, not against frozen v2.

PRE-REGISTRATION (written before this screen was run):
Readings: the 48 readings of the three screens already merged, rebuilt
with their own pair builders unchanged (same data, same windows <=
2023-12-28, same regime split, same frozen v2 k):
  screen_market_factor.screen_pairs  18 = 3 models x 3 horizons x 2 regimes
  screen_exog_factor.screen_pairs    18 = 3 factors x 3 horizons x 2 regimes
  screen_fx_stress.screen_pairs      12 = 2 betas x 3 horizons x 2 regimes
Statistic per reading, on the rows of that reading:
  delta = RangeSkill(candidate) - RangeSkill(v2)
        = (sum IS_v2 - sum IS_candidate) / sum IS_naive,
the same RangeSkill definition as score_adoption_594.range_skill, so a
positive delta means the candidate's mean interval score is lower than
frozen v2's on the same rows. Resampling: whole cutoff dates (as_of) are
drawn with replacement (replay_band_candidates._boot's scheme), seed
A.DEFAULT_SEED, REPS draws (default 2000); draws with an undefined skill
(sum IS_naive <= 0) are dropped. One-sided p for H0 delta <= 0 =
(count of draws <= 0 + 1) / (draws + 1) (Phipson-Smyth). Holm-Bonferroni
over all 48 readings (a reading with no draws counts as p = 1 in the
family). The 95% percentile interval of the draws is printed beside the
point delta. Nothing is fitted. Cells 48-90 and 91+ are NOT scored here;
a cell scoring needs its own pre-registered step.

Usage:
  python3 benchmarks/screen_delta_vs_v2.py --history DIR --factors DIR
      --fx FILE [--regime pre|post] [--reps N] [--json OUT]
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
import screen_band_models as SB  # noqa: E402
import screen_market_factor as MF  # noqa: E402
import screen_exog_factor as XF  # noqa: E402
import screen_fx_stress as FX  # noqa: E402

HORIZONS = A.HORIZONS
REGIMES = SB.REGIMES
SCREENS = ("market_factor", "exog_factor", "fx_stress")
FAMILY_SIZE = (len(MF.MODELS) + len(XF.FACTORS) + len(FX.BETAS)) \
    * len(HORIZONS) * len(REGIMES)   # 48
_f = SB._f
_f4 = lambda v: "n/a" if v is None else "%.4f" % v  # noqa: E731
# display only: deltas can be below 0.001, so delta and its interval print
# at 4 decimals; p stays at 3. The JSON keeps full precision.


def delta_stat(pairs):
    """RangeSkill(candidate) - RangeSkill(v2) on the same rows, or None."""
    n = sum(p["is_naive"] for p in pairs)
    if not pairs or n <= 0:
        return None
    return (sum(p["is_v2"] for p in pairs)
            - sum(p["is_ch"] for p in pairs)) / n


def boot_delta(pairs, reps, seed=A.DEFAULT_SEED):
    """Draws of delta, resampling whole cutoff dates."""
    groups = {}
    for p in pairs:
        groups.setdefault(p["as_of"], []).append(p)
    keys = sorted(groups)
    rng = random.Random(seed)
    out = []
    for _ in range(reps if keys else 0):
        draw = []
        for _ in keys:
            draw.extend(groups[rng.choice(keys)])
        d = delta_stat(draw)
        if d is not None:
            out.append(d)
    return out


def reading(pairs, reps):
    """{n, cutoffs, delta, ci, p} for one reading."""
    draws = boot_delta(pairs, reps)
    lo, hi = A.percentile_ci(draws)
    return {"n": len(pairs), "cutoffs": len({p["as_of"] for p in pairs}),
            "delta": delta_stat(pairs), "ci": [lo, hi],
            "p": ((sum(1 for x in draws if x <= 0) + 1.0)
                  / (len(draws) + 1.0)) if draws else None}


def all_pairs(by_t, factor_bars, fx_bars, regime):
    """{(screen, name): [pair]} for one regime."""
    out = {}
    for k, v in MF.screen_pairs(by_t, regime=regime).items():
        out[("market_factor", k)] = v
    for k, v in XF.screen_pairs(by_t, factor_bars, regime=regime).items():
        out[("exog_factor", k)] = v
    for k, v in FX.screen_pairs(by_t, fx_bars, regime=regime).items():
        out[("fx_stress", "beta %.2f" % k)] = v
    return out


def holm_rows(readings):
    ps = {k: r["p"] for k, r in readings.items()}
    adj = SB.holm_adjust(ps, m=FAMILY_SIZE)
    return [{"screen": k[0], "name": k[1], "horizon": k[2], "regime": k[3],
             "n": readings[k]["n"], "cutoffs": readings[k]["cutoffs"],
             "delta": readings[k]["delta"], "ci": readings[k]["ci"],
             "p": readings[k]["p"], "holm_adj_p": adj.get(k)}
            for k in sorted(readings)]


def render(rows):
    L = ["PAIRED DELTA vs frozen v2 (RangeSkill candidate minus v2, same "
         "rows; Yahoo close, windows end <= %s), descriptive only"
         % SB.SCREEN_END]
    for r in rows:
        L.append("  %s %s %s %s: n=%d cutoffs=%d delta %s (CI cutoff "
                 "[%s, %s]) p %s Holm-adjusted p %s"
                 % (r["screen"], r["name"], r["regime"], r["horizon"],
                    r["n"], r["cutoffs"], _f4(r["delta"]), _f4(r["ci"][0]),
                    _f4(r["ci"][1]), _f(r["p"]), _f(r["holm_adj_p"])))
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.
                                 RawDescriptionHelpFormatter)
    ap.add_argument("--history", required=True)
    ap.add_argument("--factors", required=True)
    ap.add_argument("--fx", required=True)
    ap.add_argument("--regime", choices=REGIMES, default=None)
    ap.add_argument("--reps", type=int, default=2000)
    ap.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    by_t = MF.load(a.history)
    fb = {k: XF.read_factor(os.path.join(a.factors, fn))
          for k, fn in XF.FACTORS.items()}
    fx = FX.read_close_csv(a.fx)
    regimes = [a.regime] if a.regime else list(REGIMES)
    readings = {}
    for rg in regimes:
        for (scr, name), pairs in sorted(
                all_pairs(by_t, fb, fx, rg).items()):
            for h in HORIZONS:
                readings[(scr, name, h, rg)] = reading(
                    [p for p in pairs if p["horizon"] == h], a.reps)
    rows = holm_rows(readings)
    print(render(rows))
    print("Holm family fixed at %d readings; tickers: %d"
          % (FAMILY_SIZE, len(by_t)))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump({"descriptive": True, "source": "yahoo close",
                       "statistic": "RangeSkill(candidate) - "
                                    "RangeSkill(v2), same rows",
                       "holm": {"family_size": FAMILY_SIZE,
                                "method": "Holm-Bonferroni",
                                "readings": rows}}, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
