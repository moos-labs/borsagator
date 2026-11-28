#!/usr/bin/env python3
"""Replay harness for volatility-estimator band candidates (P2/P3).

INS-IMPROVE-001 round 1. v2 is the naive band by construction
(centre 0, half = k x sigma60 x sqrt(sessions)), so RangeSkill can
only move through a better volatility forecast. This harness picks
ONE candidate estimator and k table on the fit cells, writes them to
a freeze file, and scores that file once on untouched cells.

Candidates (daily sigma from the capture's own pre-cutoff history,
collected/pandas-ta/indicators.csv, rows dated <= the capture's base
date only; nothing after the cutoff is read):
  s60        stdev of the last 60 log returns (the v2 estimator,
             recomputed here: the control)
  s20        stdev of the last 20 log returns
  ewma94     RiskMetrics EWMA, lambda 0.94, zero mean
  blend2060  sqrt(0.5 s20^2 + 0.5 s60^2)
  park60     Parkinson high-low estimator over the last 60 bars
  gk60       Garman-Klass OHLC estimator over the last 60 bars
Band: centre 0, half = k_h x sigma x sqrt(sessions_h) x RISK_MULT
(sessions 1/5/21 as ledger.DEFAULT_SESSIONS). RISK_MULT comes from
each capture's own risk level and is applied to every band in fit and
score, as in the frozen v2 band. It is inert today: every backtest
capture carries risk "none" (benchmarks/audit_risk_mult_594), but a
future non-"none" capture must not silently mis-state v2.

FIT (mode `fit`): for each candidate and horizon, k is the grid value
(0.50 to 2.50, step 0.01) that minimises mean Winkler interval score
(alpha 0.2) over the fit rows. Candidates are COMPARED by
leave-one-cutoff-out cross-validation: k is fit on all other cutoffs
and the held-out cutoff is scored. Selection score = mean over
horizons of (CV mean IS / naive mean IS); lowest wins, ties go to the
earlier candidate in the list above. Exactly one winner is frozen.
Default fit cells: 1-47 (the cells the v2 freeze used).

SCORE (mode `score`): scores the frozen file on cells >= 73 only
(refuses lower cells unless --descriptive, which prints a banner).
Pre-registered keep rule, per horizon, on >= 30 untouched rows:
  (a) RangeSkill >= +0.05 vs naive,
  (b) the cutoff-clustered coverage CI overlaps [0.75, 0.85] and is no
      wider than MAX_CI_WIDTH = 0.15 (round 11 ruling; round 9 cap;
      was: point coverage inside the band),
  (c) RangeSkill >= frozen-v2 RangeSkill on the same rows.
KEEP only if (a), (b) and (c) hold on every horizon. Below 30 rows
the verdict is INSUFFICIENT. The formal adoption gate (CI lower
bound > 0, benchmarks/score_adoption_594.py) is separate and still
applies before any ensemble.py change. Nothing here edits
scripts/ensemble.py.

Realised moves, dividend handling and the naive range come from
scripts/backtest_score.py score_capture, so this cannot disagree with
the #436 scorer.

Usage:
  python3 benchmarks/replay_band_candidates.py fit --captures DIR ...
      [--max-cell 47] --out frozen.json
  python3 benchmarks/replay_band_candidates.py score --frozen
      frozen.json --captures DIR ... [--min-cell 73] [--descriptive]
      [--reps 5000] [--json OUT]
"""
import argparse
import csv
import json
import math
import os
import random
import shutil
import sys
import tempfile

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
CANDIDATES = ("s60", "s20", "ewma94", "blend2060", "park60", "gk60")
K_GRID = [round(0.50 + 0.01 * i, 2) for i in range(201)]
MIN_ROWS = 30
SKILL_FLOOR = 0.05
COV_BAND = (0.75, 0.85)
# Design parameter (round 9, Muhammad's call (a)): an absolute cap on the
# width of the cutoff-clustered coverage CI, 1.5x the band width. A CI
# wider than this cannot establish overlap, however it straddles the
# band. No relaxation below n = 30: the small-k case is exactly where the
# cap matters. Revisit with evidence if it proves too tight or too loose.
MAX_CI_WIDTH = 0.15
_W_EPS = 1e-9


def coverage_ci_ok(ci, band=None):
    """Coverage leg of every keep rule (Moos ruling, round 11): the
    cutoff-clustered 95% coverage CI must OVERLAP [0.75, 0.85], using
    the same clustering and draws as the scorer's RangeSkill CI. A point
    check on n = 30 rejects a perfect 80% model about half the time. An
    undefined CI (fewer than two cutoffs) is not an overlap, and a CI
    wider than MAX_CI_WIDTH (round 9) cannot establish overlap."""
    lo, hi = band or COV_BAND
    if not ci or ci[0] is None or ci[1] is None:
        return False
    if ci[1] - ci[0] > MAX_CI_WIDTH + _W_EPS:
        return False
    return ci[0] <= hi and ci[1] >= lo


def coverage_ci_reason(h, ci, cov, band=None):
    lo, hi = band or COV_BAND
    if (ci and ci[0] is not None and ci[1] is not None
            and ci[1] - ci[0] > MAX_CI_WIDTH + _W_EPS):
        return ("%s coverage CI [%.3f, %.3f] is %.3f wide, over the "
                "%.2f cap, so it cannot establish overlap with "
                "[%.2f, %.2f]" % (h, ci[0], ci[1], ci[1] - ci[0],
                                  MAX_CI_WIDTH, lo, hi))
    return ("%s coverage CI [%s, %s] (point %s) does not overlap "
            "[%.2f, %.2f]" % (h, *(("n/a" if v is None else "%.3f" % v)
                                   for v in (ci or (None, None))),
                              "n/a" if cov is None else "%.3f" % cov,
                              lo, hi))
LN2 = math.log(2.0)


# ------------------------------------------------------- estimators
def _logrets(closes):
    return [math.log(closes[i] / closes[i - 1])
            for i in range(1, len(closes))
            if closes[i] > 0 and closes[i - 1] > 0]


def _sd(rets):
    """Population stdev about the mean, as ensemble.realized_sigma."""
    if len(rets) < 5:
        return None
    mu = sum(rets) / len(rets)
    return math.sqrt(sum((r - mu) ** 2 for r in rets) / len(rets))


def _ewma(rets, lam=0.94):
    if len(rets) < 25:
        return None
    var = sum(r * r for r in rets[:20]) / 20.0
    for r in rets[20:]:
        var = lam * var + (1 - lam) * r * r
    return math.sqrt(var)


def _bars(ohlc, n=60):
    ok = [(o, h, l, c) for o, h, l, c in ohlc
          if min(o, h, l, c) > 0 and h >= l]
    return ok[-n:] if len(ok) >= n else None


def _park(ohlc):
    b = _bars(ohlc)
    if not b:
        return None
    return math.sqrt(sum(math.log(h / l) ** 2 for _, h, l, _c in b)
                     / (4 * LN2 * len(b)))


def _gk(ohlc):
    b = _bars(ohlc)
    if not b:
        return None
    v = sum(0.5 * math.log(h / l) ** 2
            - (2 * LN2 - 1) * math.log(c / o) ** 2
            for o, h, l, c in b) / len(b)
    return math.sqrt(v) if v > 0 else None


def sigmas(ohlc):
    """{candidate: daily sigma or None} from [(o, h, l, c)] bars
    (oldest first, nothing after the cutoff)."""
    closes = [c for _, _, _, c in ohlc if c > 0]
    rets = _logrets(closes)
    s60, s20 = _sd(rets[-60:]), _sd(rets[-20:])
    out = {"s60": s60, "s20": s20, "ewma94": _ewma(rets)}
    out["blend2060"] = (math.sqrt(0.5 * s20 ** 2 + 0.5 * s60 ** 2)
                        if s20 is not None and s60 is not None else None)
    out["park60"] = _park(ohlc)
    out["gk60"] = _gk(ohlc)
    return out


def read_ohlc(capture, base_date):
    """OHLC bars dated <= base_date from the capture's indicator CSV
    (pandas-ta, then talib). Empty list when unreadable."""
    for rel in ("collected/pandas-ta/indicators.csv",
                "collected/talib/indicators.csv"):
        path = os.path.join(capture, rel)
        if not os.path.exists(path):
            continue
        try:
            with open(path, newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
        except Exception:
            continue
        bars = []
        for r in rows:
            d = str(r.get("Date") or "")[:10]
            if not d or (base_date and d > base_date):
                continue
            vals = [A.fnum(r.get(k)) for k in
                    ("Open", "High", "Low", "Close")]
            if any(v is None for v in vals):
                continue
            bars.append(tuple(vals))
        if bars:
            return bars
    return []


# ------------------------------------------------------------ rows
def price_reference(capture_dirs):
    """{TICKER: [(date, close)]} from the capture price.csv with the
    latest last date per ticker. Used ONLY to rebuild a 21-session
    realised window for captures whose shipped realised.json is
    shorter (cells 1-47 carry 14 sessions; the #592 re-score built
    the 21-session window from the feed, not from the capture)."""
    best = {}
    for cap in capture_dirs:
        path = os.path.join(cap, "price.csv")
        if not os.path.exists(path):
            continue
        try:
            with open(path, newline="", encoding="utf-8") as f:
                pts = [(str(r["date"])[:10], float(r["close"]))
                       for r in csv.DictReader(f)
                       if r.get("date") and r.get("close")]
        except Exception:
            continue
        t = os.path.basename(cap).upper()
        if pts and (t not in best or pts[-1][0] > best[t][-1][0]):
            best[t] = pts
    return best


def _extend_realised(staged, ref, need=21):
    """Rewrite staged/realised.json with `need` sessions after the
    base date from `ref` when it has fewer. Returns True when it
    changed the file. Dividend adjustment is whatever score_capture
    applies from the capture's own corporate-actions record."""
    path = os.path.join(staged, "realised.json")
    with open(path, encoding="utf-8") as f:
        rl = json.load(f)
    if len(rl.get("sessions") or []) >= need or not ref:
        return False
    base = str(rl.get("base_date") or "")[:10]
    fut = [(d, c) for d, c in ref if d > base][:need]
    if len(fut) < need or len(rl.get("sessions") or []) > len(fut):
        return False
    rl["sessions"] = [{"date": d, "close": c} for d, c in fut]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rl, f)
    return True


def _realised_endpoints(staged):
    """Sorted session dates of the staged realised.json (after any
    extension): the list realised_move_pct is measured from."""
    with open(os.path.join(staged, "realised.json"), encoding="utf-8") as f:
        rl = json.load(f)
    return sorted(str(s.get("date"))[:10] for s in (rl.get("sessions") or []))


def endpoint_date(session_dates, as_of, horizon):
    """Date of the close that realised_move_pct is measured to: the Nth
    session dated after the cutoff (as_of), N = ledger sessions, the rule
    backtest_score.score_capture uses. None when the list is too short."""
    after = [d for d in session_dates if d > str(as_of)[:10]]
    n = A.SESSIONS[horizon]
    return after[n - 1] if len(after) >= n else None


def build_rows(capture_dirs, ref_dirs=None, pending=None):
    """One row per matured, non-gap (capture, horizon) with realised
    move, naive band, v2 sigma, and each candidate's daily sigma.
    When `pending` is a list, one record per captured (ticker, cutoff,
    horizon) that is NOT matured (status pending etc.) is appended to it
    as (ticker, as_of, horizon, status); those rows never enter `rows`."""
    rows, gaps = [], []
    prices = price_reference(ref_dirs if ref_dirs is not None
                             else capture_dirs)
    for cap in capture_dirs:
        # Stage with the ledger session counts (1/5/21): older
        # captures carry the Kronos-bar month session estimate, so
        # their month rows would stay "pending". This is the same
        # staging score_adoption_594 uses.
        tmp = tempfile.mkdtemp(prefix="replay-")
        try:
            staged = A._stage(cap, "v2", tmp)
            if _extend_realised(staged, prices.get(
                    os.path.basename(cap).upper())):
                gaps.append("%s: realised window rebuilt to 21 sessions "
                            "from price.csv" % cap)
            scored, _g = bs.score_capture(staged)
            real_end = _realised_endpoints(staged)
        except Exception as e:
            gaps.append("%s: scoring failed: %s" % (cap, e))
            continue
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        ens = bs.load_json(os.path.join(cap, "digest", "ensemble.json"))
        sig = sigmas(read_ohlc(cap, str((ens or {}).get("base_date")
                                        or "")[:10]))
        v2sig = A._sigma60(ens or {})
        if sig.get("s60") is None:
            gaps.append("%s: no usable pre-cutoff OHLC history" % cap)
            continue
        for r in scored:
            if (pending is not None and r.get("entrant") == "naive-range"
                    and r.get("status") != "matured"
                    and not r.get("dividend_gap")):
                pending.append((r["ticker"], r["as_of"], r["horizon"],
                                r.get("status")))
            if (r.get("entrant") != "naive-range"
                    or r.get("status") != "matured"
                    or r.get("dividend_gap")):
                continue
            rows.append({
                "cell": A.cell_number(cap), "ticker": r["ticker"],
                "as_of": r["as_of"], "horizon": r["horizon"],
                "real": r["realized_move_pct"],
                "naive_half": (r["range_high_pct"] - r["range_low_pct"])
                / 2.0,
                "mult": ens_mod.RISK_MULT.get(
                    ((ens or {}).get("risk") or {}).get("level"), 1.0),
                "v2_sigma": v2sig, "sig": sig,
                # date of the close that produced `real` (the capture's
                # own staged realised sessions), see _realised_endpoints
                "real_end": endpoint_date(real_end, r["as_of"],
                                          r["horizon"])})
    return rows, gaps


def half_pct(sigma, horizon, k, mult=1.0):
    """Half-width in pp: k x sigma x sqrt(sessions) x RISK_MULT."""
    return k * sigma * math.sqrt(SESSIONS[horizon]) * mult * 100


def row_is(row, half):
    return bs.winkler_is(row["real"], -half, half)


# ------------------------------------------------------------- fit
def fit_k(rows, cand, horizon):
    """Grid k minimising mean IS over rows (None without rows)."""
    hp = [r for r in rows if r["horizon"] == horizon
          and r["sig"].get(cand)]
    if not hp:
        return None
    best, best_k = None, None
    for k in K_GRID:
        m = sum(row_is(r, half_pct(r["sig"][cand], horizon, k, r["mult"]))
                for r in hp) / len(hp)
        if best is None or m < best - 1e-12:
            best, best_k = m, k
    return best_k


def loco_cv(rows, cand):
    """Per-horizon CV ratio: leave-one-cutoff-out mean IS of the
    candidate over naive mean IS (lower is better), plus the fitted
    k per cutoff fold count. None when a horizon has < 2 cutoffs."""
    out = {}
    for h in HORIZONS:
        hp = [r for r in rows if r["horizon"] == h
              and r["sig"].get(cand)]
        cuts = sorted({r["as_of"] for r in hp})
        if len(cuts) < 2:
            out[h] = None
            continue
        tot, naive, n = 0.0, 0.0, 0
        for c in cuts:
            train = [r for r in hp if r["as_of"] != c]
            test = [r for r in hp if r["as_of"] == c]
            k = fit_k(train, cand, h)
            for r in test:
                tot += row_is(r, half_pct(r["sig"][cand], h, k, r["mult"]))
                naive += row_is(r, r["naive_half"])
                n += 1
        out[h] = tot / naive if naive > 0 else None
    return out


def select(rows):
    """Compare every candidate by LOCO-CV; returns (frozen dict,
    table). Candidates missing a horizon are skipped."""
    table = {}
    for cand in CANDIDATES:
        cv = loco_cv(rows, cand)
        if any(v is None for v in cv.values()):
            continue
        table[cand] = {"cv_ratio": cv,
                       "score": sum(cv.values()) / len(HORIZONS)}
    if not table:
        return None, table
    winner = min(table, key=lambda c: (table[c]["score"],
                                       CANDIDATES.index(c)))
    k = {h: fit_k(rows, winner, h) for h in HORIZONS}
    cells = sorted({r["cell"] for r in rows if r["cell"] is not None})
    frozen = {"candidate": winner, "k": k,
              "fit_rows": len(rows),
              "fit_cells": [cells[0], cells[-1]] if cells else None,
              "selection_score": table[winner]["score"],
              "rule": {"skill_floor": SKILL_FLOOR,
                       "coverage": list(COV_BAND),
                       "min_rows": MIN_ROWS}}
    return frozen, table


# ----------------------------------------------------------- score
def score_rows(rows, frozen):
    cand, k = frozen["candidate"], frozen["k"]
    out = []
    for r in rows:
        s = r["sig"].get(cand)
        if not s or not r["v2_sigma"]:
            continue
        h = r["horizon"]
        ch = half_pct(s, h, k[h], r["mult"])
        v2 = half_pct(r["v2_sigma"], h, ens_mod.V2_BAND_K[h], r["mult"])
        out.append({
            "ticker": r["ticker"], "as_of": r["as_of"], "horizon": h,
            "is_naive": row_is(r, r["naive_half"]),
            "is_v2": row_is(r, v2), "is_ch": row_is(r, ch),
            "in_v2": abs(r["real"]) <= v2,
            "in_ch": abs(r["real"]) <= ch})
    return out


def _boot(pairs, by, reps, seed):
    groups = {}
    for p in pairs:
        groups.setdefault(p[by], []).append(p)
    keys = sorted(groups)
    rng = random.Random(seed)
    skill, cov = [], []
    for _ in range(reps if keys else 0):
        draw = []
        for _ in keys:
            draw.extend(groups[rng.choice(keys)])
        s = A.range_skill(draw, "ch")
        if s is None:
            continue
        skill.append(s)
        cov.append(sum(p["in_ch"] for p in draw) / len(draw))
    return skill, cov


def evaluate(pairs, reps=A.DEFAULT_REPS, seed=A.DEFAULT_SEED):
    res = {}
    for h in HORIZONS:
        hp = [p for p in pairs if p["horizon"] == h]
        n = len(hp)
        cell = {"n": n, "cutoffs": len({p["as_of"] for p in hp}),
                "tickers": len({p["ticker"] for p in hp})}
        for name in ("v2", "ch"):
            cell[name] = {
                "coverage": (sum(p["in_" + name] for p in hp) / n
                             if n else None),
                "range_skill": A.range_skill(hp, name)}
        sk_c, cv_c = _boot(hp, "as_of", reps, seed)
        sk_t, _ = _boot(hp, "ticker", reps, seed)
        cell["ch_ci_cutoff"] = list(A.percentile_ci(sk_c))
        cell["ch_cov_ci_cutoff"] = list(A.percentile_ci(cv_c))
        cell["ch_ci_ticker"] = list(A.percentile_ci(sk_t))
        res[h] = cell
    return res


def keep_verdict(res):
    """Pre-registered rule (module doc). Returns (verdict, reasons)."""
    if any(res[h]["n"] < MIN_ROWS for h in HORIZONS):
        return "INSUFFICIENT", ["n < %d on at least one horizon"
                                % MIN_ROWS]
    bad = []
    for h in HORIZONS:
        c = res[h]
        sk, cov = c["ch"]["range_skill"], c["ch"]["coverage"]
        if sk is None or sk < SKILL_FLOOR:
            bad.append("%s RangeSkill %s < +%.2f" % (h, _f(sk),
                                                      SKILL_FLOOR))
        if not coverage_ci_ok(c["ch_cov_ci_cutoff"]):
            bad.append(coverage_ci_reason(h, c["ch_cov_ci_cutoff"], cov))
        v2 = c["v2"]["range_skill"]
        if sk is not None and v2 is not None and sk < v2:
            bad.append("%s worse than frozen v2 (%s < %s)"
                       % (h, _f(sk), _f(v2)))
    return ("REJECT" if bad else "KEEP"), bad


def _f(v, nd=3):
    return "n/a" if v is None else ("%.*f" % (nd, v))


def render_fit(frozen, table):
    L = ["Fit (LOCO-CV over cutoffs), candidates by selection score "
         "(mean over horizons of CV IS / naive IS; < 1 beats naive):"]
    for c in sorted(table, key=lambda c: table[c]["score"]):
        L.append("  %-10s score %s  day %s  week %s  month %s"
                 % (c, _f(table[c]["score"]),
                    _f(table[c]["cv_ratio"]["day"]),
                    _f(table[c]["cv_ratio"]["week"]),
                    _f(table[c]["cv_ratio"]["month"])))
    if frozen:
        L.append("FROZEN: %s  k %s  (%d fit rows, cells %s)"
                 % (frozen["candidate"], json.dumps(frozen["k"]),
                    frozen["fit_rows"], frozen["fit_cells"]))
    return "\n".join(L)


def render_score(res, frozen, descriptive):
    L = []
    if descriptive:
        L += ["DESCRIPTIVE ONLY: these cells were seen before the "
              "candidate was frozen. No keep/reject is valid.", ""]
    L.append("Frozen candidate %s k %s vs frozen v2"
             % (frozen["candidate"], json.dumps(frozen["k"])))
    for h in HORIZONS:
        c = res[h]
        L.append("%s: n=%d, %d cutoffs, %d tickers" % (
            h, c["n"], c["cutoffs"], c["tickers"]))
        L.append("  candidate coverage %s [%s, %s]  RangeSkill %s  "
                 "CI cutoff [%s, %s]  CI ticker [%s, %s]"
                 % (_f(c["ch"]["coverage"]),
                    _f(c["ch_cov_ci_cutoff"][0]),
                    _f(c["ch_cov_ci_cutoff"][1]),
                    _f(c["ch"]["range_skill"]),
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
    sub = ap.add_subparsers(dest="mode", required=True)
    f = sub.add_parser("fit")
    f.add_argument("--captures", nargs="+", required=True)
    f.add_argument("--max-cell", type=int, default=47)
    f.add_argument("--out", required=True)
    s = sub.add_parser("score")
    s.add_argument("--frozen", required=True)
    s.add_argument("--captures", nargs="+", required=True)
    s.add_argument("--min-cell", type=int, default=73)
    s.add_argument("--descriptive", action="store_true")
    s.add_argument("--reps", type=int, default=A.DEFAULT_REPS)
    s.add_argument("--seed", type=int, default=A.DEFAULT_SEED)
    s.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    if a.mode == "fit":
        caps = [c for c in A.find_captures(a.captures, None)
                if (A.cell_number(c) or 0) <= a.max_cell]
        rows, gaps = build_rows(caps, A.find_captures(a.captures, None))
        frozen, table = select(rows)
        print(render_fit(frozen, table))
        for g in gaps:
            print("gap: " + g)
        if frozen is None:
            return 1
        with open(a.out, "w", encoding="utf-8") as fh:
            json.dump({"frozen": frozen, "table": table}, fh, indent=1)
        return 0
    if a.min_cell < 73 and not a.descriptive:
        print("refusing: cells below 73 were seen; pass --descriptive")
        return 2
    with open(a.frozen, encoding="utf-8") as fh:
        frozen = json.load(fh)["frozen"]
    caps = A.find_captures(a.captures, a.min_cell)
    rows, gaps = build_rows(caps, A.find_captures(a.captures, None))
    res = evaluate(score_rows(rows, frozen), a.reps, a.seed)
    print(render_score(res, frozen, a.descriptive))
    for g in gaps:
        print("gap: " + g)
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump({"frozen": frozen, "results": res,
                       "verdict": keep_verdict(res)[0],
                       "descriptive": a.descriptive}, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
