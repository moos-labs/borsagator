#!/usr/bin/env python3
"""Round 100: shrinkage of frozen v2 toward a per-name empirical-quantile
baseline, shadow scorer.

Pre-registration: docs/round100_shrinkage_challenger_prereg.md. Modes:
`fit` (cells 1-47 only, prints the per-horizon covered-row counts and
the frozen weights) and `describe` (cells 48-90 only, counts first, no
verdict word). There is no scoring mode here: cells 91+ are never
loaded by this script. scripts/ensemble.py and every frozen value are
read, never edited.
"""
import argparse
import bisect
import csv
import datetime
import json
import math
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "benchmarks"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import replay_band_candidates as R  # noqa: E402
import score_adoption_594 as A  # noqa: E402
import ensemble as ens_mod  # noqa: E402
import backtest_score as bs  # noqa: E402

HORIZONS = A.HORIZONS
SESSIONS = A.SESSIONS
WINDOW = 250
MIN_MOVES = 125
Q_LO, Q_HI = 0.10, 0.90
GRID = [i / 20.0 for i in range(21)]
MIN_CLUSTERS = 10  # fully mature cutoff clusters per horizon (registered loop bar)
MIN_COVERED = 100  # pooled over the three horizons (Moos decision, relayed)
FREEZE = "2025-08-15"
FIT_CELLS = (1, 47)
DESC_CELLS = (48, 90)


def load_closes(path):
    """Dated sessions. A record without a usable ISO date is rejected. A
    record with a usable date but an empty, missing or unparseable close is
    KEPT with a NaN close, so session offsets do not shift and the baseline
    window check excludes the rows that read it."""
    out = []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                d = str(r["date"])[:10]
                datetime.date.fromisoformat(d)
            except (ValueError, KeyError, TypeError):
                continue
            try:
                c = float(r["close"])
            except (ValueError, KeyError, TypeError):
                c = float("nan")
            out.append((d, c))
    out.sort()
    return out


def quantile(vals, p):
    """Linear interpolation between order statistics at (n-1) x p."""
    s = sorted(vals)
    if not s:
        return None
    pos = (len(s) - 1) * p
    lo = int(pos)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def baseline(closes, base_date, horizon):
    """(q_lo, q_hi, n_moves). Moves 100 x (c[t+S]/c[t]-1), overlapping,
    the 250 most recent whose END close is dated <= base_date. None
    edges when fewer than MIN_MOVES moves exist."""
    S = SESSIONS[horizon]
    dates = [d for d, _ in closes]
    end = bisect.bisect_right(dates, base_date) - 1  # last idx <= base
    moves = []
    for e in range(end, S - 1, -1):
        c0 = closes[e - S][1]
        if not (math.isfinite(c0) and math.isfinite(closes[e][1])):
            return None, None, len(moves)  # non-finite close in the window
        if c0 > 0:
            moves.append(100.0 * (closes[e][1] / c0 - 1.0))
        if len(moves) == WINDOW:
            break
    if len(moves) < MIN_MOVES:
        return None, None, len(moves)
    return quantile(moves, Q_LO), quantile(moves, Q_HI), len(moves)


def window_nonfinite(closes, base_date, horizon):
    """True when a close that the baseline window reads (the end close or the
    start close of any move it consumes) is NaN or infinite. Non-finite
    closes stay in the price history, so session offsets never shift."""
    S = SESSIONS[horizon]
    dates = [d for d, _ in closes]
    end = bisect.bisect_right(dates, base_date) - 1
    n = 0
    for e in range(end, S - 1, -1):
        c0 = closes[e - S][1]
        if not (math.isfinite(c0) and math.isfinite(closes[e][1])):
            return True
        if c0 > 0:
            n += 1
        if n == WINDOW:
            break
    return False


def realised_date(closes, base_date, horizon):
    """Date of the close S sessions after the base session, or None."""
    dates = [d for d, _ in closes]
    i = bisect.bisect_right(dates, base_date) - 1
    j = i + SESSIONS[horizon]
    return dates[j] if i >= 0 and j < len(dates) else None


def mix_edges(half, q_lo, q_hi, a, b):
    return a * (-half) + (1.0 - a) * q_lo, b * half + (1.0 - b) * q_hi


def prepare(rows, closes_by_ticker):
    """(usable rows, exclusion lines). A row is dropped, and listed
    with a reason, when it has no realised close, no baseline
    history or v2 sigma is missing."""
    out, ex = [], []
    for r in rows:
        key = "%s %s %s" % (r["ticker"], str(r["as_of"])[:10], r["horizon"])
        cl = closes_by_ticker.get(r["ticker"])
        h = r["horizon"]
        if not r.get("v2_sigma"):
            ex.append("excluded row %s: missing or zero v2_sigma" % key)
            continue
        if cl is None:
            ex.append("excluded row %s: no price history file" % key)
            continue
        base = str(r["as_of"])[:10]
        rdate_ohlcv = realised_date(cl, base, h)
        # The OHLCV endpoint is needed only when the capture has no
        # recorded endpoint; a captured outcome with its own real_end
        # stays even when the OHLCV file ends at the cutoff.
        if r.get("real") is None or (not r.get("real_end") and rdate_ohlcv is None):
            ex.append("excluded row %s: no realised close" % key)
            continue
        # The freeze gate uses the date of the close that PRODUCED `real`
        # (the capture's own realised endpoint), not the OHLCV series
        # date: they can differ when the capture's session list lacks a
        # date the OHLCV file has. Rows without a recorded endpoint fall
        # back to the OHLCV date.
        rdate = r.get("real_end") or rdate_ohlcv
        if window_nonfinite(cl, base, h):
            ex.append("excluded row %s: non-finite close in the baseline window" % key)
            continue
        q_lo, q_hi, n = baseline(cl, base, h)
        if q_lo is None:
            ex.append("excluded row %s: short history (%d moves)" % (key, n))
            continue
        half = R.half_pct(r["v2_sigma"], h, ens_mod.V2_BAND_K[h], r["mult"])
        out.append(dict(r, half=half, q_lo=q_lo, q_hi=q_hi,
                        rdate=rdate, rdate_ohlcv=rdate_ohlcv,
                        base=base, key=key))
    return out, ex


REBUILD_NOTE = "realised window rebuilt to 21 sessions"


def mature_clusters(caps, horizon_rows):
    """(mature cutoffs, all cutoffs) for ONE horizon. Intended rows of a
    cutoff = one per in-range capture of that cutoff (its ticker); no
    eligibility filter applies: a captured ticker whose row for this
    horizon is dropped (capture rejection, v2_sigma missing, short history,
    no realised close) stays intended, so its cluster is not mature.
    A cutoff counts only when every intended ticker has a usable row for
    the horizon. Duplicates collapse and other cutoffs never count."""
    intended = {}
    for c in caps:
        cutoff = os.path.basename(os.path.dirname(c))
        intended.setdefault(cutoff, set()).add(os.path.basename(c).upper())
    have = {}
    for r in horizon_rows:
        have.setdefault(r["base"], set()).add(r["ticker"].upper())
    mature = {k for k, v in intended.items() if v and v <= have.get(k, set())}
    return mature, set(intended)


def split_gaps(gaps):
    """(exclusion gaps, rebuild notices). A successful window rebuild keeps
    the capture scored, so it is reported apart from exclusions."""
    ex = [g for g in gaps if REBUILD_NOTE not in g]
    return ex, [g for g in gaps if REBUILD_NOTE in g]


def endpoint_notes(usable):
    """Scored rows whose capture endpoint date differs from the OHLCV one
    (the freeze gate uses the capture's endpoint)."""
    return ["%s: capture endpoint %s, OHLCV endpoint %s (freeze gate uses %s)"
            % (r["key"], r["rdate"], r.get("rdate_ohlcv", r["rdate"]), r["rdate"])
            for r in usable if r.get("rdate_ohlcv", r["rdate"]) is not None
            and r["rdate"] != r.get("rdate_ohlcv", r["rdate"])]


def pending_exclusions(pending):
    """Exclusion lines for captured rows that are not matured: they stay out
    of fitting and evaluation, each with its own reason."""
    return ["excluded row %s %s %s: no realised close (capture status %s)"
            % (t, str(d)[:10], h, st) for t, d, h, st in pending]


def gate_horizons(mature):
    """Horizons below the registered MIN_CLUSTERS fully mature clusters:
    counts only, no RangeSkill, coverage, interval or KEEP output.
    mature = {horizon: (mature count, cutoff count)}."""
    return [h for h in HORIZONS if mature[h][0] < MIN_CLUSTERS]


def row_scores(r, a, b):
    lo, hi = mix_edges(r["half"], r["q_lo"], r["q_hi"], a, b)
    crossed = lo >= hi
    if crossed:
        lo, hi = -r["half"], r["half"]
    return bs.winkler_is(r["real"], lo, hi), lo <= r["real"] <= hi, crossed


def fit_pooled(rows):
    """POOLED fit: one shared weight pair (a, b) over the covered rows of
    all three horizons. Returns covered count, freeze-date excluded lines,
    weights or None (fewer than MIN_COVERED covered rows pooled)."""
    hp = list(rows)
    ex = ["excluded row %s: close after freeze date" % r["key"]
          for r in hp if r["rdate"] >= FREEZE]
    cov = [r for r in hp if r["rdate"] < FREEZE]
    if len(cov) < MIN_COVERED:
        return len(cov), ex, None
    best, bw = None, None
    for a in GRID:
        for b in GRID:
            m = sum(row_scores(r, a, b)[0] for r in cov) / len(cov)
            if (best is None or m < best - 1e-12
                    or (abs(m - best) <= 1e-12 and (a + b) > sum(bw))):
                best, bw = m, (a, b)
    return len(cov), ex, bw


def evaluate_pairs(rows, w, reps, seed):
    """Per-horizon challenger rows (with the three RangeSkill inputs)
    and cutoff-cluster bootstrap. w is the ONE shared pair (a, b) or
    None; deltas are still reported separately per horizon."""
    res = {}
    for h in HORIZONS:
        hp = [r for r in rows if r["horizon"] == h]
        if w is None or not hp:
            res[h] = {"n": len(hp), "weights": None}
            continue
        a, b = w
        pairs = []
        for r in hp:
            is_ch, inside, crossed = row_scores(r, a, b)
            pairs.append({"as_of": r["base"], "key": r["key"], "is_naive": R.row_is(r, r["naive_half"]),
                          "is_v2": R.row_is(r, r["half"]), "is_ch": is_ch,
                          "in_ch": inside, "in_v2": abs(r["real"]) <= r["half"],
                          "crossed": crossed})
        groups = {}
        for p in pairs:
            groups.setdefault(p["as_of"], []).append(p)
        keys = sorted(groups)
        rng = random.Random(seed)
        dl, cv = [], []
        for _ in range(reps):
            draw = []
            for _k in keys:
                draw.extend(groups[rng.choice(keys)])
            x, y = A.range_skill(draw, "ch"), A.range_skill(draw, "v2")
            # coverage does not depend on RangeSkill: keep every draw
            cv.append(sum(p["in_ch"] for p in draw) / len(draw))
            if x is None or y is None:
                continue
            dl.append(x - y)
        res[h] = {"n": len(pairs), "cutoffs": len(keys), "weights": [a, b],
                  "crossed": sum(p["crossed"] for p in pairs),
                  "crossed_keys": [p["key"] for p in pairs if p["crossed"]],
                  "rs_ch": A.range_skill(pairs, "ch"),
                  "rs_v2": A.range_skill(pairs, "v2"),
                  "cov_ch": sum(p["in_ch"] for p in pairs) / len(pairs),
                  "cov_v2": sum(p["in_v2"] for p in pairs) / len(pairs),
                  "delta_ci_cutoff": list(A.percentile_ci(dl)),
                  "cov_ci_cutoff": list(A.percentile_ci(cv))}
    return res


def f3(v):
    return "n/a" if v is None else "%.3f" % v


def cell_caps(roots, lo, hi):
    allc = A.find_captures(roots, None)
    caps = [c for c in allc if A.cell_number(c) is not None
            and lo <= A.cell_number(c) <= hi]
    return allc, caps


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mode", choices=("fit", "describe"))
    ap.add_argument("--captures", nargs="+", required=True)
    ap.add_argument("--ohlcv-dir", required=True)
    ap.add_argument("--min-cell", type=int, default=None)
    ap.add_argument("--max-cell", type=int, default=None)
    ap.add_argument("--reps", type=int, default=A.DEFAULT_REPS)
    ap.add_argument("--seed", type=int, default=A.DEFAULT_SEED)
    ap.add_argument("--weights", default=None,
                    help="JSON file written by `fit` (describe only)")
    ap.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    if a.reps != A.DEFAULT_REPS:
        print("refusing: --reps must be the registered %d, got %d"
              % (A.DEFAULT_REPS, a.reps))
        return 2
    if a.seed != A.DEFAULT_SEED:
        print("refusing: --seed must be the registered %d, got %d"
              % (A.DEFAULT_SEED, a.seed))
        return 2
    lo, hi = FIT_CELLS if a.mode == "fit" else DESC_CELLS
    mn = a.min_cell if a.min_cell is not None else lo
    mx = a.max_cell if a.max_cell is not None else hi
    if mn < lo or mx > hi:
        print("refusing: %s covers cells %d-%d only" % (a.mode, lo, hi))
        return 2
    closes = {}
    for fn in sorted(os.listdir(a.ohlcv_dir)):
        if fn.endswith(".csv"):
            closes[fn[:-4].replace("_", ".")] = load_closes(
                os.path.join(a.ohlcv_dir, fn))
    allc, caps = cell_caps(a.captures, mn, mx)
    # Reference set = the in-range captures only: an out-of-range capture
    # (for example a 91+ cell in fit mode) must never supply the price
    # series for an in-range row's realised-window rebuild.
    pend = []
    rows, gaps = R.build_rows(caps, pending=pend)
    usable, ex = prepare(rows, closes)
    gex, rebuilt = split_gaps(gaps)
    ex = ["excluded: %s" % g for g in gex] + ex + pending_exclusions(pend)
    notes = endpoint_notes(usable)
    if a.mode == "fit":
        n, fx, wh = fit_pooled(usable)
        lines = ["pooled over day, week, month: covered training rows=%d%s" % (
            n, "" if wh else " (<%d: no fit, counts only)" % MIN_COVERED)]
        for h in HORIZONS:
            lines.append("%s: usable rows=%d covered rows=%d" % (
                h, sum(1 for r in usable if r["horizon"] == h),
                sum(1 for r in usable if r["horizon"] == h and r["rdate"] < FREEZE)))
        w = list(wh) if wh else None
        print("COUNTS cells %d-%d, %d rows built, %d usable" % (mn, mx, len(rows), len(usable)))
        print("\n".join(lines))
        print("REBUILT WINDOWS (scored, not exclusions)")
        print("\n".join(rebuilt))
        print("ENDPOINT DATE DIFFERENCES (scored, not exclusions): %d" % len(notes))
        print("\n".join(notes))
        print("EXCLUSIONS (every one listed)")
        print("\n".join(ex + fx))
        print("FROZEN SHARED WEIGHT PAIR (a, b): %s" % json.dumps(w))
        # Training-cell rows whose challenger edges cross under the frozen pair
        # (covered rows only, the rows the fit used). Listed individually; the
        # v2 interval is what the scorer uses for them.
        crossed_tr = []
        if w:
            crossed_tr = ["%s (reason: crossed edges under the frozen pair, v2 interval used)" % r["key"]
                          for r in usable if r["rdate"] < FREEZE and row_scores(r, w[0], w[1])[2]]
            print("CROSSED-EDGE ROWS UNDER THE FROZEN PAIR, cells %d-%d, covered rows: %d of %d" % (
                mn, mx, len(crossed_tr), n))
            print("\n".join(crossed_tr))
        if a.json:
            with open(a.json, "w", encoding="utf-8") as fh:
                json.dump({"weights": w, "counts": lines, "crossed_rows": crossed_tr,
                           "rebuilt_windows": rebuilt, "endpoint_differences": notes,
                           "excluded": ex + fx}, fh, indent=1)
        return 0
    if not a.weights:
        print("refusing: describe needs --weights from a fit run")
        return 2
    with open(a.weights, encoding="utf-8") as fh:
        w = json.load(fh)["weights"]
    w = tuple(w) if w else None
    lines = []
    for h in HORIZONS:
        hp = [r for r in usable if r["horizon"] == h]
        lines.append("%s: rows=%d cutoff clusters=%d tickers=%d shared weights=%s" % (
            h, len(hp), len({r["base"] for r in hp}),
            len({r["ticker"] for r in hp}), w))
    print("COUNTS (before any statistic), cells %d-%d, %d rows built, %d usable"
          % (mn, mx, len(rows), len(usable)))
    print("\n".join(lines))
    print("REBUILT WINDOWS (scored, not exclusions)")
    print("\n".join(rebuilt))
    print("ENDPOINT DATE DIFFERENCES (scored, not exclusions): %d" % len(notes))
    print("\n".join(notes))
    mature = {}
    for h in HORIZONS:
        mt, al = mature_clusters(caps, [r for r in usable if r["horizon"] == h])
        mature[h] = (len(mt), len(al))
        print("%s: fully mature cutoff clusters=%d of %d (registered minimum %d; intended rows = captured "
              "tickers of the cutoff, no eligibility filter)" % (h, len(mt), len(al), MIN_CLUSTERS))
    print("EXCLUSIONS (every one listed, before any statistic)")
    print("\n".join(ex))
    gated = gate_horizons(mature)
    for h in gated:
        print("%s: COUNTS ONLY, %d of the registered %d fully mature clusters; no RangeSkill, coverage, "
              "interval or KEEP output (gate enforced in code)" % (h, mature[h][0], MIN_CLUSTERS))
    res = evaluate_pairs([r for r in usable if r["horizon"] not in gated], w, a.reps, a.seed)
    print("CROSSED-EDGE FALLBACKS (every one listed, before any statistic; rows stay in scoring)")
    for r in usable:
        if row_scores(r, w[0], w[1])[2] if w else False:
            print("crossed edges: %s (reason: crossed edges, v2 interval used)" % r["key"])
    print("DESCRIPTIVE ONLY cells %d-%d, %d reps seed %d" % (mn, mx, a.reps, a.seed))
    for h in HORIZONS:
        c = res[h]
        if h in gated:
            continue
        if c.get("weights") is None:
            print("%s: no weights or no rows (counts only)" % h)
            continue
        print("%s: n=%d, %d cutoffs, crossed-edge rows=%d" % (h, c["n"], c["cutoffs"], c["crossed"]))
        print("  challenger: coverage %s RangeSkill %s coverage CI cutoff [%s, %s]" % (
            f3(c["cov_ch"]), f3(c["rs_ch"]), f3(c["cov_ci_cutoff"][0]), f3(c["cov_ci_cutoff"][1])))
        print("  frozen v2: coverage %s RangeSkill %s" % (f3(c["cov_v2"]), f3(c["rs_v2"])))
        print("  challenger minus v2 RangeSkill CI cutoff [%s, %s]" % (
            f3(c["delta_ci_cutoff"][0]), f3(c["delta_ci_cutoff"][1])))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump({"descriptive": True, "counts": lines,
                       "results": {h: v for h, v in res.items() if h not in gated},
                       "counts_only_horizons": gated,
                       "mature_clusters": {h: {"mature": m, "cutoffs": t} for h, (m, t) in mature.items()},
                       "excluded": ex}, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
