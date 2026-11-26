#!/usr/bin/env python3
"""Shadow challenger: frozen v2 band with a drift centre.

INS-IMPROVE-001 round 3, experiment 2 (target T2).

Band: the frozen v2 half-width (V2_BAND_K x sigma60 x sqrt(sessions)
x RISK_MULT, unchanged) re-centred on
  centre_pct = BETA x mean_ret_60 x sessions_h x 100,   BETA = 0.10.
BETA is fixed by the brief and nothing is fitted, so there is no fit
mode. mean_ret_60 is the mean of the last 60 daily log returns from
the capture's own pre-cutoff OHLC history (nothing after the base
date). The brief wrote "centre += beta x mean_ret_60" without a
horizon scale; here the daily drift is multiplied by the horizon's
trading sessions (1 / 5 / 21, as ledger.DEFAULT_SESSIONS), so the
centre is a horizon move like the band half-width. Stated for review.

Reuses benchmarks/replay_band_candidates.py for rows, realised moves,
dividend handling and the naive range (scripts/backtest_score.py
score_capture). Frozen v2 (scripts/ensemble.py) is untouched and is
the comparison column.

Pre-registered keep rule (written by Ins before any untouched cell was
scored; the RangeSkill and coverage conditions are Moos's round 3
brief, the minimum-sample conditions are the #751 ones). Untouched
cells only (cell >= 73). KEEP when, on EVERY horizon, with at least
30 rows over at least 5 tickers and at least 2 cutoffs,
  (1) RangeSkill vs naive has a cutoff-clustered 95% CI lower bound
      > 0, and
  (2) the cutoff-clustered coverage CI overlaps [0.75, 0.85] (round 11
      ruling by Moos; the original wording was point coverage within
      0.75-0.85), same clustering and draws as the RangeSkill CI.
REJECT when the sample is enough on every horizon and either fails
anywhere. INSUFFICIENT when any horizon lacks the sample. One scoring,
no re-fit. Cells 48-72 give descriptive output only (--descriptive).
Nothing here edits scripts/ensemble.py.

Disclosure: before this PR was opened a descriptive run on all cells >= 48
(n = 31 per horizon) included cells 73-78, so those six rows were seen
for this challenger. A valid keep/reject needs cells not in 1-78, i.e.
the batch D/E cells (91-102) once they land.

Usage:
  python3 benchmarks/replay_centre_drift.py --captures DIR ...
      [--min-cell 73] [--descriptive] [--reps 5000] [--json OUT]
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
import replay_band_candidates as R  # noqa: E402
import score_adoption_594 as A  # noqa: E402
import ensemble as ens_mod  # noqa: E402
import backtest_score as bs  # noqa: E402

HORIZONS = A.HORIZONS
BETA = 0.10
DRIFT_N = 60
MIN_ROWS, MIN_TICKERS, MIN_CUTOFFS = 30, 5, 2
COV_BAND = (0.75, 0.85)


def mean_ret(closes, n=DRIFT_N):
    """Mean of the last n daily log returns; None when fewer."""
    rets = R._logrets([c for c in closes if c > 0])[-n:]
    return sum(rets) / len(rets) if len(rets) >= n else None


def centre_pct(m60, horizon, beta=BETA):
    if m60 is None:
        return None
    return beta * m60 * R.SESSIONS[horizon] * 100


def build_rows(capture_dirs, ref_dirs):
    """R.build_rows rows, each with mean_ret_60 added."""
    out, gaps = [], []
    for cap in capture_dirs:
        rows, g = R.build_rows([cap], ref_dirs)
        gaps.extend(g)
        ens = bs.load_json(os.path.join(cap, "digest", "ensemble.json"))
        bars = R.read_ohlc(cap, str((ens or {}).get("base_date")
                                    or "")[:10])
        m60 = mean_ret([c for _, _, _, c in bars])
        for r in rows:
            r["mean_ret_60"] = m60
            out.append(r)
    return out, gaps


def score_rows(rows):
    out = []
    for r in rows:
        if not r["v2_sigma"] or r.get("mean_ret_60") is None:
            continue
        h = r["horizon"]
        half = R.half_pct(r["v2_sigma"], h, ens_mod.V2_BAND_K[h],
                          r["mult"])
        c = centre_pct(r["mean_ret_60"], h)
        out.append({"ticker": r["ticker"], "as_of": r["as_of"],
                    "horizon": h,
                    "is_naive": R.row_is(r, r["naive_half"]),
                    "is_v2": R.row_is(r, half),
                    "is_ch": bs.winkler_is(r["real"], c - half, c + half),
                    "in_v2": abs(r["real"]) <= half,
                    "in_ch": abs(r["real"] - c) <= half})
    return out


def keep_verdict(res):
    """Pre-registered rule (module doc): (verdict, reasons)."""
    short = [h for h in HORIZONS
             if res[h]["n"] < MIN_ROWS
             or res[h]["tickers"] < MIN_TICKERS
             or res[h]["cutoffs"] < MIN_CUTOFFS]
    if short:
        return "INSUFFICIENT", [
            "%s n=%d tickers=%d cutoffs=%d (need >=%d, >=%d, >=%d)"
            % (h, res[h]["n"], res[h]["tickers"], res[h]["cutoffs"],
               MIN_ROWS, MIN_TICKERS, MIN_CUTOFFS) for h in short]
    bad = []
    for h in HORIZONS:
        c = res[h]
        lo = c["ch_ci_cutoff"][0]
        cov = c["ch"]["coverage"]
        if lo is None or lo <= 0:
            bad.append("%s CI lower bound %s not > 0" % (h, _f(lo)))
        if not R.coverage_ci_ok(c["ch_cov_ci_cutoff"], COV_BAND):
            bad.append(R.coverage_ci_reason(h, c["ch_cov_ci_cutoff"], cov,
                                            COV_BAND))
    return ("REJECT" if bad else "KEEP"), bad


def _f(v, nd=3):
    return "n/a" if v is None else ("%.*f" % (nd, v))


def render(res, descriptive):
    L = []
    if descriptive:
        L += ["DESCRIPTIVE ONLY: these cells were seen before the "
              "challenger was written. No keep/reject is valid.", ""]
    L.append("Centre drift beta %.2f x mean_ret_60 x sessions, frozen "
             "v2 half-width" % BETA)
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
    v, why = keep_verdict(res)
    L += ["", "KEEP RULE: %s%s" % (
        v, "" if descriptive else (" (" + "; ".join(why) + ")"
                                   if why else ""))]
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.
                                 RawDescriptionHelpFormatter)
    ap.add_argument("--captures", nargs="+", required=True)
    ap.add_argument("--min-cell", type=int, default=73)
    ap.add_argument("--descriptive", action="store_true")
    ap.add_argument("--reps", type=int, default=A.DEFAULT_REPS)
    ap.add_argument("--seed", type=int, default=A.DEFAULT_SEED)
    ap.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    if a.min_cell < 73 and not a.descriptive:
        print("refusing: cells below 73 were seen; pass --descriptive")
        return 2
    allc = A.find_captures(a.captures, None)
    caps = A.find_captures(a.captures, a.min_cell)
    rows, gaps = build_rows(caps, allc)
    res = R.evaluate(score_rows(rows), a.reps, a.seed)
    print(render(res, a.descriptive))
    for g in gaps:
        print("gap: " + g)
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump({"beta": BETA, "results": res,
                       "verdict": keep_verdict(res)[0],
                       "descriptive": a.descriptive}, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
