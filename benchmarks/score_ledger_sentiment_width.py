#!/usr/bin/env python3
"""Forward-ledger scorer for sentiment-weighted width (shadow, nothing
fitted).

INS-IMPROVE-001 round 5, item 1 (targets T2, T3). Reads
ledger/ledger.json forecasts_detail directly. Built on the #764
machinery (benchmarks/score_ledger_sentiment_tilt.py): same eligible
rows, same cutoff-clustered CI, same rule, same counts-only output.

Widening: each row's PUBLISHED band keeps its centre and its
half-width is scaled by
  scale = 1 + BETA x min(|sentiment|, 1),   BETA = 0.25.
Widen-only (scale >= 1), at most +25% and about +19% on the matured
rows (|sentiment| up to 0.757). BETA and the form are fixed by the
proposal; nothing is fitted.

Skill definition (as confirmed for #764): ledger rows carry no sigma,
so skill is measured against the same row's own published band,
  RangeSkill = 1 - mean IS(widened band) / mean IS(published band),
Winkler interval score alpha 0.2. Coverage is the widened band's
in-range rate. Known caveat, accepted before building: week coverage
on the current eligible rows is already 1.0, so widening can only
cost week interval score there. The verdict rests on future rows.

Pre-registered keep rule: the #764 rule. Per horizon, one scoring once
n >= 30 matured rows over >= 10 tickers and >= 2 as-of dates: KEEP when
the cutoff-clustered (by as_of) 95% CI lower bound of RangeSkill > 0
and coverage is within 0.75-0.85; REJECT when the sample is enough and
either fails; INSUFFICIENT otherwise. While INSUFFICIENT the default
output prints only sample counts; numbers need --descriptive.
Sentiment only (the scale of other families is not read).

Usage:
  python3 benchmarks/score_ledger_sentiment_width.py
      [--ledger ledger/ledger.json] [--descriptive] [--reps 5000]
      [--json OUT]
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
import score_ledger_sentiment_tilt as T  # noqa: E402
import score_adoption_594 as A  # noqa: E402
import backtest_score as bs  # noqa: E402
import replay_band_candidates as R  # noqa: E402

HORIZONS = T.HORIZONS
BETA = 0.25
FAMILY = "sentiment"
eligible = T.eligible
sample = T.sample
enough = T.enough
verdicts = T.verdicts


def widened_band(row, beta=BETA):
    lo, hi = row["range_low_pct"], row["range_high_pct"]
    c, half = (lo + hi) / 2.0, (hi - lo) / 2.0
    s = min(abs(float(row["families"][FAMILY])), 1.0)
    h2 = half * (1.0 + beta * s)
    return c - h2, c + h2


def score_rows(rows, beta=BETA):
    pairs = []
    for r in rows:
        if not eligible(r, FAMILY):
            continue
        real = r["realized_move_pct"]
        lo, hi = widened_band(r, beta)
        base = bs.winkler_is(real, r["range_low_pct"],
                             r["range_high_pct"])
        pairs.append({
            "ticker": r["ticker"], "as_of": r["as_of"],
            "horizon": r["horizon"],
            "is_naive": base, "is_v2": base,
            "is_ch": bs.winkler_is(real, lo, hi),
            "in_v2": r["range_low_pct"] <= real <= r["range_high_pct"],
            "in_ch": lo <= real <= hi})
    return pairs


def render(smp, ver, res, descriptive):
    L = ["Ledger sentiment width, BETA %.2f widen-only, skill vs the "
         "row's own band" % BETA]
    for h in HORIZONS:
        s = smp[h]
        L.append("%s: n=%d matured rows, %d tickers, %d as-of dates  "
                 "-> %s%s" % (h, s["n"], s["tickers"], s["dates"],
                              ver[h][0],
                              " (" + ver[h][1] + ")" if ver[h][1] else ""))
        if (descriptive or ver[h][0] != "INSUFFICIENT") and res \
                and s["n"]:
            c, f = res[h], T._f
            L.append("  widened coverage %s  RangeSkill %s  CI cutoff "
                     "[%s, %s]  CI ticker [%s, %s]  published-band "
                     "coverage %s"
                     % (f(c["ch"]["coverage"]), f(c["ch"]["range_skill"]),
                        f(c["ch_ci_cutoff"][0]), f(c["ch_ci_cutoff"][1]),
                        f(c["ch_ci_ticker"][0]), f(c["ch_ci_ticker"][1]),
                        f(c["v2"]["coverage"])))
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.
                                 RawDescriptionHelpFormatter)
    ap.add_argument("--ledger", default=os.path.join(
        ROOT, "ledger", "ledger.json"))
    ap.add_argument("--descriptive", action="store_true")
    ap.add_argument("--reps", type=int, default=A.DEFAULT_REPS)
    ap.add_argument("--seed", type=int, default=A.DEFAULT_SEED)
    ap.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    with open(a.ledger, encoding="utf-8") as f:
        rows = json.load(f)["forecasts_detail"]
    pairs = score_rows(rows)
    smp = sample(pairs)
    need = any(enough(smp[h]) for h in HORIZONS)
    res = (R.evaluate(pairs, a.reps, a.seed)
           if (need or a.descriptive) else None)
    ver = verdicts(pairs, res)
    print(render(smp, ver, res, a.descriptive))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump({"beta": BETA, "sample": smp,
                       "verdicts": {h: ver[h][0] for h in HORIZONS}},
                      fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
