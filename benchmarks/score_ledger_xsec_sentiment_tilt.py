#!/usr/bin/env python3
"""Forward-ledger scorer for the cross-sectional sentiment tilt (shadow,
nothing fitted).

INS-IMPROVE-001 round 8, experiment X1 (target T2). GO by Moos in Slack
(1795720900.500279). Reads ledger/ledger.json forecasts_detail directly.

Tilt: the S1 sentiment tilt (score_ledger_sentiment_tilt.py) with a
relative score. Within each (as_of cutoff, horizon) group of eligible
rows the score is demeaned by the group median,
  rel_i = clip(s_i - median(s over the group), -1, 1),
and each row's PUBLISHED band is re-centred by
  shift_pp = GAMMA x rel_i x half,   GAMMA = 0.25, width unchanged.
GAMMA is fixed (as S1), nothing is fitted. This removes the common
market-wide sentiment mode, so the shift carries only the cross-section.
A group with fewer than MIN_GROUP eligible tickers is dropped (a median
of one or two scores carries no cross-section).

Eligibility, control and skill are exactly S1's: matured, not
dividend-gap flagged, with a sentiment score and a band;
  RangeSkill = 1 - mean IS(tilt band) / mean IS(published band),
Winkler alpha 0.2. The ledger is forward data and nothing here is tuned
on it.

Pre-registered keep rule, per horizon, ONE scoring per horizon once the
sample is enough: at least MIN_ROWS matured rows over at least
MIN_TICKERS tickers and at least MIN_CUTOFFS as-of cutoffs,
  (1) RangeSkill cutoff-clustered (by as_of) 95% CI lower bound > 0,
  (2) the cutoff-clustered tilt coverage CI overlaps [0.75, 0.85]
      (Moos ruling, #775; an undefined CI is not an overlap),
  (3) rank leg: the mean over cutoffs of the Spearman correlation
      between the relative score and the realised move (cutoffs with at
      least MIN_GROUP tickers and a defined correlation), at least
      MIN_CUTOFFS such cutoffs, and the cutoff-bootstrap 95% CI lower
      bound of that mean > 0.
KEEP when all hold, REJECT when the sample is enough and any fails,
INSUFFICIENT otherwise. No KEEP is an adoption. MIN_CUTOFFS is 2, as in
the sibling ledger scorers; the decision to raise it to 10 is the
cycle's, and this constant moves with it. Descriptive runs print numbers
and carry no verdict, in text or JSON.

Usage:
  python3 benchmarks/score_ledger_xsec_sentiment_tilt.py
      [--ledger ledger/ledger.json] [--descriptive]
      [--reps 5000] [--seed N] [--json OUT]
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
import replay_band_candidates as R  # noqa: E402
import score_ledger_sentiment_tilt as S  # noqa: E402

HORIZONS = A.HORIZONS
GAMMA = 0.25
MIN_ROWS, MIN_TICKERS, MIN_CUTOFFS = 30, 10, 2
MIN_GROUP = 4
COV_BAND = (0.75, 0.85)
FAMILY = "sentiment"


def _median(xs):
    xs = sorted(xs)
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2.0


def relative_scores(rows):
    """{(ticker, as_of, horizon): rel} for eligible rows in groups with
    at least MIN_GROUP distinct tickers."""
    groups = {}
    for r in rows:
        if S.eligible(r, FAMILY):
            groups.setdefault((r["as_of"], r["horizon"]), []).append(r)
    out = {}
    for (a, h), rs in groups.items():
        if len({r["ticker"] for r in rs}) < MIN_GROUP:
            continue
        med = _median([float(r["families"][FAMILY]) for r in rs])
        for r in rs:
            rel = float(r["families"][FAMILY]) - med
            out[(r["ticker"], a, h)] = max(-1.0, min(1.0, rel))
    return out


def shifted_band(row, rel, gamma=GAMMA):
    lo, hi = row["range_low_pct"], row["range_high_pct"]
    shift = gamma * rel * (hi - lo) / 2.0
    return lo + shift, hi + shift


def score_rows(rows, gamma=GAMMA):
    rel = relative_scores(rows)
    pairs = []
    for r in rows:
        k = (r.get("ticker"), r.get("as_of"), r.get("horizon"))
        if not S.eligible(r, FAMILY) or k not in rel:
            continue
        real = r["realized_move_pct"]
        lo, hi = shifted_band(r, rel[k], gamma)
        pairs.append({
            "ticker": r["ticker"], "as_of": r["as_of"],
            "horizon": r["horizon"],
            "is_naive": bs.winkler_is(real, r["range_low_pct"],
                                      r["range_high_pct"]),
            "is_v2": bs.winkler_is(real, r["range_low_pct"],
                                   r["range_high_pct"]),
            "is_ch": bs.winkler_is(real, lo, hi),
            "in_v2": r["range_low_pct"] <= real <= r["range_high_pct"],
            "in_ch": lo <= real <= hi,
            "rel": rel[k], "real": real})
    return pairs


def _ranks(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    rk = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for k in range(i, j + 1):
            rk[order[k]] = (i + j) / 2.0 + 1.0
        i = j + 1
    return rk


def spearman(xs, ys):
    """Rank correlation; None when either side has no variance."""
    if len(xs) < 2:
        return None
    rx, ry = _ranks(xs), _ranks(ys)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    sxx = sum((a - mx) ** 2 for a in rx)
    syy = sum((b - my) ** 2 for b in ry)
    if sxx == 0 or syy == 0:
        return None
    return sum((a - mx) * (b - my) for a, b in zip(rx, ry)) / (
        sxx * syy) ** 0.5


def rank_ic(pairs, h, reps, seed):
    """Per-cutoff Spearman of rel vs realised move, mean and the
    cutoff-bootstrap 95% CI of the mean."""
    by = {}
    for p in pairs:
        if p["horizon"] == h:
            by.setdefault(p["as_of"], []).append(p)
    ics = []
    for a in sorted(by):
        ps = by[a]
        if len({p["ticker"] for p in ps}) < MIN_GROUP:
            continue
        ic = spearman([p["rel"] for p in ps], [p["real"] for p in ps])
        if ic is not None:
            ics.append(ic)
    if len(ics) < MIN_CUTOFFS:
        return {"cutoffs": len(ics), "mean": None, "ci": [None, None]}
    rng = random.Random(seed)
    means = []
    for _ in range(reps):
        d = [ics[rng.randrange(len(ics))] for _ in ics]
        means.append(sum(d) / len(d))
    return {"cutoffs": len(ics), "mean": sum(ics) / len(ics),
            "ci": list(A.percentile_ci(means))}


def sample(pairs):
    s = {}
    for h in HORIZONS:
        hp = [p for p in pairs if p["horizon"] == h]
        s[h] = {"n": len(hp), "tickers": len({p["ticker"] for p in hp}),
                "cutoffs": len({p["as_of"] for p in hp})}
    return s


def enough(s):
    return (s["n"] >= MIN_ROWS and s["tickers"] >= MIN_TICKERS
            and s["cutoffs"] >= MIN_CUTOFFS)


def _f(v, nd=3):
    return "n/a" if v is None else ("%.*f" % (nd, v))


def verdicts(pairs, res, ic):
    smp = sample(pairs)
    out = {}
    for h in HORIZONS:
        s = smp[h]
        if not enough(s):
            out[h] = ("INSUFFICIENT",
                      "n=%d tickers=%d cutoffs=%d (need >=%d, >=%d, >=%d)"
                      % (s["n"], s["tickers"], s["cutoffs"], MIN_ROWS,
                         MIN_TICKERS, MIN_CUTOFFS))
            continue
        c = res[h]
        lo, cov = c["ch_ci_cutoff"][0], c["ch"]["coverage"]
        bad = []
        if lo is None or lo <= 0:
            bad.append("CI lower bound %s not > 0" % _f(lo))
        if not R.coverage_ci_ok(c["ch_cov_ci_cutoff"], COV_BAND):
            bad.append(R.coverage_ci_reason("", c["ch_cov_ci_cutoff"], cov,
                                            COV_BAND).strip())
        ilo = ic[h]["ci"][0]
        if ilo is None or ilo <= 0:
            bad.append("rank-IC CI lower bound %s not > 0" % _f(ilo))
        out[h] = ("REJECT" if bad else "KEEP", "; ".join(bad))
    return out


def render(smp, ver, res, ic, descriptive):
    L = ["Ledger cross-sectional sentiment tilt, GAMMA %.2f, skill vs the "
         "row's own band" % GAMMA]
    if descriptive:
        L.append("DESCRIPTIVE: no keep/reject is valid on this run")
    for h in HORIZONS:
        s = smp[h]
        head = "%s: n=%d matured rows, %d tickers, %d cutoffs" % (
            h, s["n"], s["tickers"], s["cutoffs"])
        if not descriptive:
            head += "  -> %s%s" % (ver[h][0],
                                   " (" + ver[h][1] + ")"
                                   if ver[h][1] else "")
        L.append(head)
        show = descriptive or ver[h][0] != "INSUFFICIENT"
        if show and res is not None and s["n"]:
            c = res[h]
            L.append("  tilt coverage %s  RangeSkill %s  CI cutoff "
                     "[%s, %s]  published-band coverage %s"
                     % (_f(c["ch"]["coverage"]),
                        _f(c["ch"]["range_skill"]),
                        _f(c["ch_ci_cutoff"][0]),
                        _f(c["ch_ci_cutoff"][1]),
                        _f(c["v2"]["coverage"])))
            L.append("  rank-IC mean %s over %d cutoffs  CI [%s, %s]"
                     % (_f(ic[h]["mean"]), ic[h]["cutoffs"],
                        _f(ic[h]["ci"][0]), _f(ic[h]["ci"][1])))
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
    ic = {h: rank_ic(pairs, h, a.reps, a.seed) for h in HORIZONS}
    ver = verdicts(pairs, res, ic)
    print(render(smp, ver, res, ic, a.descriptive))
    if a.json:
        out = {"gamma": GAMMA, "sample": smp, "rank_ic": ic,
               "descriptive": a.descriptive}
        if not a.descriptive:
            out["verdicts"] = {h: ver[h][0] for h in HORIZONS}
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
