#!/usr/bin/env python3
"""Shadow challenger: shrinkage of the per-ticker sigma toward the
pooled cross-ticker level (round 58).

Round 58 task (Moos, Slack 1795773619.072989, relayed): shrink
per-ticker quantile forecasts toward the pooled cross-ticker mean,
shrinkage strength fitted on TRAINING windows only (cells 1-47).
Mechanism, stated as built (an empirical-Bayes, fixed-weight
estimator, not a full hierarchical model):
  sigma_shr = exp( (1 - lam_h) ln sigma_t + lam_h ln sigma_pool )
  half      = k_h x sigma_shr x sqrt(sessions_h) x RISK_MULT
sigma_t is the frozen v2 sigma60 of the capture, sigma_pool(as_of)
is the geometric mean of sigma_t over the distinct tickers scored
at the same cutoff (as_of) in the same cell window, pre-cutoff
information only. The v2 k table is imported from scripts/
ensemble.py and not refitted. Centre 0, RISK_MULT as in v2.
lam_h in [0, 1] is the grid value (step 0.05) that minimises mean
Winkler IS on the TRAINING rows of horizon h (ties to the smaller
lam); fewer than MIN_FIT_ROWS training rows keeps lam = 0 (= v2).
Training = cells 1-47 of the --captures dirs only (--fit-max-cell,
never above 47 and exactly 47 for a clean run), refitted from those
cells on every run and printed; the fit's price reference comes from
the training captures only and the JSON records the effective fit
window and price-reference provenance; scoring refuses
a range that overlaps them. A cutoff with fewer than MIN_POOL
distinct tickers has no usable pool: its rows keep the v2 sigma
(lam 0) and are counted. No external source, nothing edits
scripts/ensemble.py, no Kronos.

Pre-registered keep rule (same as the round 3 challengers), one
scoring, per horizon, >= 30 rows over >= 5 tickers and >= 2 cutoffs:
(1) RangeSkill CI lower bound (cutoff-clustered by as_of) > 0 and
(2) the cutoff-clustered coverage CI overlaps [0.75, 0.85], untouched
cells only (>= 91). Cells 48-90 are scored only with --descriptive,
which prints no verdict word and writes no verdict key.

Usage:
  python3 benchmarks/replay_bayes_shrinkage.py score --captures DIR ...
      [--min-cell 91] [--max-cell N] [--descriptive] [--reps 5000]
      [--json OUT]
  python3 benchmarks/replay_bayes_shrinkage.py diag --captures DIR ...
"""
import argparse
import json
import math
import os
import re
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import replay_band_candidates as R  # noqa: E402
import replay_parkinson_width as PK  # noqa: E402
import score_adoption_594 as A  # noqa: E402
import ensemble as ens_mod  # noqa: E402

HORIZONS = A.HORIZONS
LAM_GRID = [round(0.05 * i, 2) for i in range(21)]
MIN_FIT_ROWS = 10
MIN_POOL = 3
FIT_MAX_CELL = 47
CLEAN_MIN_CELL = 91
keep_verdict = PK.keep_verdict


def pools(rows):
    """{as_of: (geometric mean sigma, distinct tickers)}; one sigma
    per (as_of, ticker)."""
    by = {}
    for r in rows:
        if r["v2_sigma"] and r["v2_sigma"] > 0:
            by.setdefault(r["as_of"], {})[r["ticker"]] = r["v2_sigma"]
    return {a: (math.exp(sum(math.log(s) for s in d.values()) / len(d)),
                len(d)) for a, d in by.items()}


def shrunk_sigma(r, lam, pool):
    p = pool.get(r["as_of"])
    if not p or p[1] < MIN_POOL:
        return r["v2_sigma"]
    return math.exp((1 - lam) * math.log(r["v2_sigma"])
                    + lam * math.log(p[0]))


def half(r, sigma):
    h = r["horizon"]
    return R.half_pct(sigma, h, ens_mod.V2_BAND_K[h], r["mult"])


def fit(rows):
    """({horizon: lam}, {horizon: training rows}, pools) from the
    training rows only."""
    pool = pools(rows)
    lam, counts = {}, {}
    for h in HORIZONS:
        sub = [r for r in rows if r["horizon"] == h and r["v2_sigma"]
               and r["v2_sigma"] > 0]
        counts[h] = len(sub)
        best = 0.0
        if len(sub) >= MIN_FIT_ROWS:
            best = min(LAM_GRID, key=lambda x: (round(sum(
                R.row_is(r, half(r, shrunk_sigma(r, x, pool)))
                for r in sub), 9), x))
        lam[h] = best
    return lam, counts, pool


def score_rows(rows, lam):
    pool = pools(rows)
    out = []
    for r in rows:
        if not r["v2_sigma"] or r["v2_sigma"] <= 0:
            continue
        v2 = half(r, r["v2_sigma"])
        ch = half(r, shrunk_sigma(r, lam[r["horizon"]], pool))
        out.append({"ticker": r["ticker"], "as_of": r["as_of"],
                    "horizon": r["horizon"],
                    "is_naive": R.row_is(r, r["naive_half"]),
                    "is_v2": R.row_is(r, v2), "is_ch": R.row_is(r, ch),
                    "in_v2": abs(r["real"]) <= v2,
                    "in_ch": abs(r["real"]) <= ch})
    return out


def unpooled_rows(rows):
    pool = pools(rows)
    return sum(1 for r in rows if r["v2_sigma"]
               and (r["as_of"] not in pool
                    or pool[r["as_of"]][1] < MIN_POOL))


def windowed_captures(roots, lo, hi):
    """Capture dirs whose cell number is in [lo, hi], deduplicated
    WITHIN that window with the find_captures rule (one observation
    per (cutoff, ticker), lexically latest path wins). The window is
    applied before the dedup so a later-cell rerun of the same cutoff
    and ticker cannot replace the capture inside the window. Unnumbered
    captures never enter a window."""
    found = {}
    for root in roots:
        for dp, _dn, fn in os.walk(root):
            if ".tmp-" in dp or ".old-" in dp:
                continue
            if not ("manifest.json" in fn and "realised.json" in fn
                    and os.path.exists(os.path.join(
                        dp, "digest", "ensemble.json"))):
                continue
            cutoff = os.path.basename(os.path.dirname(dp))
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", cutoff):
                continue
            num = A.cell_number(dp)
            if num is None or num < lo or (hi is not None and num > hi):
                continue
            key = (cutoff, os.path.basename(dp).upper())
            if key not in found or dp > found[key]:
                found[key] = dp
    return [found[k] for k in sorted(found)]


def capture_key(path):
    """(cutoff, TICKER) identity of a capture dir."""
    return (os.path.basename(os.path.dirname(path)),
            os.path.basename(path).upper())


def exclude_trained(score_caps, train_caps):
    """score_caps without any capture whose (cutoff, ticker) the fit
    already saw in train_caps."""
    seen = {capture_key(c) for c in train_caps}
    return [c for c in score_caps if capture_key(c) not in seen]


def select_caps(allc, lo, hi):
    out = []
    for c in allc:
        n = A.cell_number(c)
        if n is not None and n >= lo and (hi is None or n <= hi):
            out.append(c)
    return out


def _f(v, nd=3):
    return PK._f(v, nd)


def count_gaps(gaps, text):
    return sum(1 for g in gaps if text in g)


def provenance(caps, gaps, source):
    return {"price_reference": source, "captures": len(caps),
            "realised_rebuilt": count_gaps(gaps, "realised window "
                                           "rebuilt"),
            "dropped_no_ohlc_captures": count_gaps(
                gaps, "no usable pre-cutoff OHLC")}


def make_report(res, lam, counts, unpooled, descriptive, fit_max, prov):
    out = {"k": ens_mod.V2_BAND_K, "lam": lam, "training_rows": counts,
           "unpooled_rows": unpooled, "results": res,
           "descriptive": descriptive,
           "fit_window": {"first_cell": 1, "last_cell": fit_max,
                          "registered_last_cell": FIT_MAX_CELL},
           "provenance": prov}
    if not descriptive:
        out["verdict"] = keep_verdict(res)[0]
    return out


def render(res, lam, counts, unpooled, descriptive, title,
           fit_max=FIT_MAX_CELL):
    L = [title, "pooled-sigma shrinkage on the v2 band, v2 k = %s"
         % json.dumps(ens_mod.V2_BAND_K),
         "fit (training cells <= %d only): lam %s (training rows %s)"
         % (fit_max,
            " ".join("%s %.2f" % (h, lam[h]) for h in HORIZONS),
            "/".join(str(counts[h]) for h in HORIZONS)),
         "rows at cutoffs with < %d tickers (v2 sigma kept): %d"
         % (MIN_POOL, unpooled)]
    for h in HORIZONS:
        c = res[h]
        L.append("%s: n=%d, %d cutoffs, %d tickers"
                 % (h, c["n"], c["cutoffs"], c["tickers"]))
        L.append("  challenger coverage %s  RangeSkill %s  CI cutoff "
                 "[%s, %s]  CI ticker [%s, %s]"
                 % (_f(c["ch"]["coverage"]), _f(c["ch"]["range_skill"]),
                    _f(c["ch_ci_cutoff"][0]), _f(c["ch_ci_cutoff"][1]),
                    _f(c["ch_ci_ticker"][0]), _f(c["ch_ci_ticker"][1])))
        L.append("  frozen v2  coverage %s  RangeSkill %s"
                 % (_f(c["v2"]["coverage"]), _f(c["v2"]["range_skill"])))
    if not descriptive:
        v, why = keep_verdict(res)
        L += ["", "KEEP RULE: %s%s" % (
            v, " (" + "; ".join(why) + ")" if why else "")]
    return "\n".join(L)


def _run(a, lo, hi, descriptive, title):
    # Full reference set (price rebuild only); the cell windows below
    # are applied before the capture dedup, never after it.
    allc = A.find_captures(a.captures, None)
    train_caps = windowed_captures(a.captures, 1, a.fit_max_cell)
    # The fit sees outcomes only through training captures: its price
    # reference is selected from the training captures, never from the
    # held-out ones.
    train, train_gaps = R.build_rows(train_caps, train_caps)
    if not [r for r in train if r["v2_sigma"]]:
        print("refusing: no training rows (cells 1-%d)" % a.fit_max_cell)
        return 2, None
    lam, counts, _p = fit(train)
    score_caps = windowed_captures(a.captures, lo, hi)
    if lo > a.fit_max_cell:
        # A (cutoff, ticker) the fit saw is never scored when the
        # scoring window starts after the training window. The
        # diagnostic scoring of the training window itself is kept.
        score_caps = exclude_trained(score_caps, train_caps)
    rows, gaps = R.build_rows(score_caps, allc)
    pairs = score_rows(rows, lam)
    up = unpooled_rows(rows)
    res = R.evaluate(pairs, a.reps, getattr(a, "seed", A.DEFAULT_SEED))
    prov = {"fit": provenance(
                train_caps, train_gaps,
                "training captures only (cells 1-%d)" % a.fit_max_cell),
            "scored": provenance(
                score_caps, gaps,
                "all --captures dirs, latest last date per ticker")}
    print(render(res, lam, counts, up, descriptive, title,
                 a.fit_max_cell))
    return 0, make_report(res, lam, counts, up, descriptive,
                          a.fit_max_cell, prov)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.
                                 RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="mode", required=True)
    d = sub.add_parser("diag")
    d.add_argument("--captures", nargs="+", required=True)
    d.add_argument("--fit-max-cell", type=int, default=FIT_MAX_CELL)
    d.add_argument("--reps", type=int, default=A.DEFAULT_REPS)
    s = sub.add_parser("score")
    s.add_argument("--captures", nargs="+", required=True)
    s.add_argument("--min-cell", type=int, default=CLEAN_MIN_CELL)
    s.add_argument("--max-cell", type=int, default=None)
    s.add_argument("--fit-max-cell", type=int, default=FIT_MAX_CELL)
    s.add_argument("--descriptive", action="store_true")
    s.add_argument("--reps", type=int, default=A.DEFAULT_REPS)
    s.add_argument("--seed", type=int, default=A.DEFAULT_SEED)
    s.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    if a.fit_max_cell > FIT_MAX_CELL:
        print("refusing: --fit-max-cell above the registered %d"
              % FIT_MAX_CELL)
        return 2
    if a.mode == "diag":
        rc, _o = _run(a, 1, a.fit_max_cell, True,
                      "FIT CELLS 1-%d, descriptive only" % a.fit_max_cell)
        return rc
    if a.min_cell < CLEAN_MIN_CELL and not a.descriptive:
        print("refusing: cells below %d need --descriptive"
              % CLEAN_MIN_CELL)
        return 2
    if not a.descriptive and a.fit_max_cell != FIT_MAX_CELL:
        print("refusing: clean scoring needs --fit-max-cell %d"
              % FIT_MAX_CELL)
        return 2
    if a.min_cell <= a.fit_max_cell:
        print("refusing: scored cells overlap the training cells (<= %d)"
              % a.fit_max_cell)
        return 2
    rc, out = _run(a, a.min_cell, a.max_cell, a.descriptive,
                   "DESCRIPTIVE ONLY" if a.descriptive
                   else "CLEAN SCORING, cells >= %d" % a.min_cell)
    if rc == 0 and a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=1)
    return rc


if __name__ == "__main__":
    sys.exit(main())
