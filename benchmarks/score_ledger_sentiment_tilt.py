#!/usr/bin/env python3
"""Forward-ledger scorer for the sentiment tilt (shadow, nothing fitted).

INS-IMPROVE-001 round 4, experiment S1 (target T2). Reads
ledger/ledger.json forecasts_detail directly (no ledger.py change).

Tilt: each ledger row's PUBLISHED band, re-centred by
  shift_pp = GAMMA x clip(sentiment, -1, 1) x half,   GAMMA = 0.25,
where half = (range_high_pct - range_low_pct) / 2 of that row. The
width is unchanged. GAMMA is fixed by the proposal and nothing is
fitted. Sentiment scores on the matured rows run from -0.313 to
+0.757, so the clip is a no-op in practice.

Control and skill definition (stated for review): ledger rows carry no
sigma, so the naive band is not rebuildable here. Skill is therefore
measured against the same row's own published band (no tilt):
  RangeSkill = 1 - mean IS(tilt band) / mean IS(published band),
Winkler interval score alpha 0.2 (scripts/backtest_score.winkler_is).
Positive means the sentiment shift beats leaving the band alone.
Coverage is the tilt band's in-range rate.

Rows scored: matured, not dividend-gap flagged (#79), carrying a
sentiment score, i.e. the skill-eligible rows that make up
family_skill n. Matured gap-flagged rows are excluded.

Pre-registered keep rule (accepted by Moos in Slack on 2026-11-26),
per horizon, ONE scoring per horizon once the sample is enough: with
at least 30 matured rows over at least 10 tickers (and at least 2
as-of dates for a cutoff-clustered CI),
  (1) RangeSkill cutoff-clustered (by as_of) 95% CI lower bound > 0,
  (2) the cutoff-clustered tilt coverage CI overlaps [0.75, 0.85]
      (round 11 ruling by Moos; was point coverage within 0.75-0.85).
KEEP when both hold, REJECT when the sample is enough and either
fails, INSUFFICIENT otherwise. While a horizon is INSUFFICIENT the
default output prints only sample counts; numbers need --descriptive.
The same scorer takes the fundamentals family via --family
fundamentals when its rows mature (same rule). GAMMA 0.25 is
confirmed for sentiment only; for fundamentals it is fixed after its
score scale is read from matured rows.

Usage:
  python3 benchmarks/score_ledger_sentiment_tilt.py
      [--ledger ledger/ledger.json] [--family sentiment]
      [--descriptive] [--reps 5000] [--json OUT]
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
import backtest_score as bs  # noqa: E402
import replay_band_candidates as R  # noqa: E402
import ledger_freshness as LF  # noqa: E402

HORIZONS = A.HORIZONS
GAMMA = 0.25
MIN_ROWS, MIN_TICKERS, MIN_DATES = 30, 10, 2
COV_BAND = (0.75, 0.85)


def eligible(row, family="sentiment"):
    """Matured, not gap-flagged, with a usable score and band."""
    fam = (row.get("families") or {}).get(family)
    return (row.get("status") == "matured"
            and not row.get("dividend_gap")
            and fam is not None
            and row.get("range_low_pct") is not None
            and row.get("range_high_pct") is not None
            and row.get("realized_move_pct") is not None)


def shifted_band(row, family="sentiment", gamma=GAMMA):
    lo, hi = row["range_low_pct"], row["range_high_pct"]
    half = (hi - lo) / 2.0
    s = max(-1.0, min(1.0, float(row["families"][family])))
    shift = gamma * s * half
    return lo + shift, hi + shift


def score_rows(rows, family="sentiment", gamma=GAMMA):
    pairs = []
    for r in rows:
        if not eligible(r, family):
            continue
        real = r["realized_move_pct"]
        lo, hi = shifted_band(r, family, gamma)
        pairs.append({
            "ticker": r["ticker"], "as_of": r["as_of"],
            "horizon": r["horizon"],
            "is_naive": bs.winkler_is(real, r["range_low_pct"],
                                      r["range_high_pct"]),
            "is_v2": bs.winkler_is(real, r["range_low_pct"],
                                   r["range_high_pct"]),
            "is_ch": bs.winkler_is(real, lo, hi),
            "in_v2": r["range_low_pct"] <= real <= r["range_high_pct"],
            "in_ch": lo <= real <= hi})
    return pairs


def direction_hits(rows, family="sentiment"):
    """Context only: sentiment sign vs realised sign, per horizon."""
    out = {}
    for h in HORIZONS:
        rs = [r for r in rows if eligible(r, family)
              and r["horizon"] == h and r["families"][family] != 0
              and r["realized_move_pct"] != 0]
        hit = sum((r["families"][family] > 0)
                  == (r["realized_move_pct"] > 0) for r in rs)
        out[h] = {"n": len(rs), "hits": hit}
    return out


def sample(pairs):
    s = {}
    for h in HORIZONS:
        hp = [p for p in pairs if p["horizon"] == h]
        s[h] = {"n": len(hp), "tickers": len({p["ticker"] for p in hp}),
                "dates": len({p["as_of"] for p in hp})}
    return s


def enough(s):
    return (s["n"] >= MIN_ROWS and s["tickers"] >= MIN_TICKERS
            and s["dates"] >= MIN_DATES)


def verdicts(pairs, res=None):
    """Per-horizon verdicts; res is evaluate() output (needed once a
    horizon has enough sample)."""
    smp = sample(pairs)
    out = {}
    for h in HORIZONS:
        s = smp[h]
        if not enough(s):
            out[h] = ("INSUFFICIENT",
                      "n=%d tickers=%d dates=%d (need >=%d, >=%d, >=%d)"
                      % (s["n"], s["tickers"], s["dates"], MIN_ROWS,
                         MIN_TICKERS, MIN_DATES))
            continue
        c = res[h]
        lo, cov = c["ch_ci_cutoff"][0], c["ch"]["coverage"]
        bad = []
        if lo is None or lo <= 0:
            bad.append("CI lower bound %s not > 0" % _f(lo))
        if not R.coverage_ci_ok(c["ch_cov_ci_cutoff"], COV_BAND):
            bad.append(R.coverage_ci_reason("", c["ch_cov_ci_cutoff"], cov,
                                            COV_BAND).strip())
        out[h] = ("REJECT" if bad else "KEEP", "; ".join(bad))
    return out


def _f(v, nd=3):
    return "n/a" if v is None else ("%.*f" % (nd, v))


def render(smp, ver, res, dh, family, descriptive):
    L = ["Ledger %s tilt, GAMMA %.2f, skill vs the row's own band"
         % (family, GAMMA)]
    for h in HORIZONS:
        s = smp[h]
        L.append("%s: n=%d matured rows, %d tickers, %d as-of dates  "
                 "-> %s%s" % (h, s["n"], s["tickers"], s["dates"],
                              ver[h][0],
                              " (" + ver[h][1] + ")" if ver[h][1] else ""))
        show = descriptive or ver[h][0] != "INSUFFICIENT"
        if show and res is not None and s["n"]:
            c = res[h]
            L.append("  tilt coverage %s  RangeSkill %s  CI cutoff "
                     "[%s, %s]  CI ticker [%s, %s]  published-band "
                     "coverage %s  direction hits %d/%d"
                     % (_f(c["ch"]["coverage"]),
                        _f(c["ch"]["range_skill"]),
                        _f(c["ch_ci_cutoff"][0]),
                        _f(c["ch_ci_cutoff"][1]),
                        _f(c["ch_ci_ticker"][0]),
                        _f(c["ch_ci_ticker"][1]),
                        _f(c["v2"]["coverage"]), dh[h]["hits"],
                        dh[h]["n"]))
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.
                                 RawDescriptionHelpFormatter)
    ap.add_argument("--ledger", default=os.path.join(
        ROOT, "ledger", "ledger.json"))
    ap.add_argument("--family", default="sentiment",
                    choices=("sentiment", "fundamentals"))
    ap.add_argument("--descriptive", action="store_true")
    ap.add_argument("--reps", type=int, default=A.DEFAULT_REPS)
    ap.add_argument("--seed", type=int, default=A.DEFAULT_SEED)
    ap.add_argument("--json", default=None)
    LF.add_args(ap)
    a = ap.parse_args(argv)
    with open(a.ledger, encoding="utf-8") as f:
        rows = json.load(f)["forecasts_detail"]
    fresh, refused = LF.gate(rows, a)
    if refused:
        return refused
    pairs = score_rows(rows, a.family)
    smp = sample(pairs)
    need = any(enough(smp[h]) for h in HORIZONS)
    res = (R.evaluate(pairs, a.reps, a.seed)
           if (need or a.descriptive) else None)
    ver = verdicts(pairs, res)
    dh = direction_hits(rows, a.family)
    print(render(smp, ver, res, dh, a.family, a.descriptive))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump({"family": a.family, "gamma": GAMMA,
                       "freshness": fresh, "sample": smp,
                       "verdicts": {h: ver[h][0] for h in HORIZONS}},
                      fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
