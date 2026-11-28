#!/usr/bin/env python3
"""Round 89: results-season calendar flag (FRA listing rules Art. 46(2),
45 days after quarter end; 90 days after year end), width-neutral
reallocation over frozen v2. Pre-registration:
docs/round89_results_season_prereg.md (committed before any number).
Descriptive screen; additive; nothing edits ensemble.py or frozen values.

Usage:
  screen_results_season.py fit --captures DIR ... --out FILE
  screen_results_season.py describe --frozen FILE --captures DIR ... [--min-cell 48 --max-cell 90]
  screen_results_season.py score --frozen FILE --captures DIR ... [--min-cell 91]
"""
import argparse
import datetime
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
import loop_bar  # noqa: E402

HORIZONS = A.HORIZONS
M_GRID = [round(0.70 + 0.05 * i, 2) for i in range(17)]
MIN_GROUP = 5
TRAIN_MAX_CELL = 47
CLEAN_MIN_CELL = 91
DESC_MAX_CELL = 90
SESSIONS = {"day": 1, "week": 5, "month": 21}
EGX_WEEKEND = (4, 5)  # Friday, Saturday (datetime.weekday)


QUARTER_DAYS = 45   # Art. 46(2): quarterly statements within 45 days of period end
ANNUAL_DAYS = 90    # Art. 46(1): annual statements within 3 months of year end
FIRST_YEAR, LAST_YEAR = 2022, 2027


def load_season(quarter_days=QUARTER_DAYS, annual_days=ANNUAL_DAYS):
    """List of (season start, season end) ISO season: the day after each
    period end to period end + N days (N = annual_days for 31 December)."""
    out = []
    for y in range(FIRST_YEAR, LAST_YEAR + 1):
        for m, d, n in ((3, 31, quarter_days), (6, 30, quarter_days),
                        (9, 30, quarter_days), (12, 31, annual_days)):
            q = datetime.date(y, m, d)
            out.append(((q + datetime.timedelta(days=1)).isoformat(),
                        (q + datetime.timedelta(days=n)).isoformat()))
    return out


def window_end(cutoff, sessions):
    """Date of the sessions-th Egyptian business day (Sun-Thu) after cutoff."""
    d = datetime.date.fromisoformat(cutoff[:10])
    n = 0
    while n < sessions:
        d += datetime.timedelta(days=1)
        if d.weekday() not in EGX_WEEKEND:
            n += 1
    return d.isoformat()


def flagged(cutoff, horizon, season):
    """True when the window (cutoff, end] overlaps a results season."""
    c = cutoff[:10]
    e = window_end(c, SESSIONS[horizon])
    return any(c < end and e >= start for start, end in season)


def v2_half(row):
    h = row["horizon"]
    return R.half_pct(row["v2_sigma"], h, ens_mod.V2_BAND_K[h], row["mult"])


def split(rows, h, season):
    ev, ne = [], []
    for r in rows:
        if r["horizon"] != h or not r.get("v2_sigma"):
            continue
        (ev if flagged(r["as_of"], h, season) else ne).append(r)
    return ev, ne


def fit_horizon(rows, h, season):
    ev, ne = split(rows, h, season)
    out = {"n_event": len(ev), "n_nonevent": len(ne),
           "m_event": 1.0, "m_nonevent": 1.0, "fitted": False}
    if len(ev) < MIN_GROUP or len(ne) < MIN_GROUP:
        return out
    se = sum(v2_half(r) for r in ev)
    sn = sum(v2_half(r) for r in ne)
    n = len(ev) + len(ne)
    best = None
    for me in M_GRID:
        mn = ((se + sn) - me * se) / sn
        if mn <= 0:
            continue
        mean_is = (sum(R.row_is(r, me * v2_half(r)) for r in ev)
                   + sum(R.row_is(r, mn * v2_half(r)) for r in ne)) / n
        key = (round(mean_is, 9), abs(me - 1.0))
        if best is None or key < best[0]:
            best = (key, me, mn)
    if best is None:
        return out
    out.update(m_event=best[1], m_nonevent=best[2], fitted=True)
    return out


def score_rows(rows, frozen, season):
    out = []
    for r in rows:
        h = r["horizon"]
        if not r.get("v2_sigma"):
            continue
        p = frozen["horizons"][h]
        m = p["m_event"] if flagged(r["as_of"], h, season) else p["m_nonevent"]
        v2 = v2_half(r)
        ch = m * v2
        out.append({"ticker": r["ticker"], "as_of": r["as_of"], "horizon": h,
                    "event": flagged(r["as_of"], h, season),
                    "is_naive": R.row_is(r, r["naive_half"]),
                    "is_v2": R.row_is(r, v2), "is_ch": R.row_is(r, ch),
                    "in_v2": abs(r["real"]) <= v2, "in_ch": abs(r["real"]) <= ch})
    return out


def group_counts(pairs):
    return {h: {"event": sum(1 for p in pairs if p["horizon"] == h and p["event"]),
                "nonevent": sum(1 for p in pairs if p["horizon"] == h and not p["event"])}
            for h in HORIZONS}


def _line(h, c):
    return ("%s: n=%d cutoffs=%d coverage %s RangeSkill %s CI cutoff [%s, %s] cov CI [%s, %s]"
            " | v2 coverage %s RangeSkill %s" % (
                h, c["n"], c["cutoffs"], R._f(c["ch"]["coverage"]), R._f(c["ch"]["range_skill"]),
                R._f(c["ch_ci_cutoff"][0]), R._f(c["ch_ci_cutoff"][1]),
                R._f(c["ch_cov_ci_cutoff"][0]), R._f(c["ch_cov_ci_cutoff"][1]),
                R._f(c["v2"]["coverage"]), R._f(c["v2"]["range_skill"])))


def clean_report(res, counts, cells, v, why):
    """COUNTS ONLY: counts and reasons only, no coverage, skill or CI."""
    L = ["CLEAN SCORING cells >= %d" % cells]
    if v == "COUNTS ONLY":
        ct = {h: {"n": res[h]["n"], "cutoffs": res[h]["cutoffs"], **counts[h]} for h in HORIZONS}
        for h in HORIZONS:
            L.append("%s: n=%d cutoffs=%d event=%d nonevent=%d" % (
                h, ct[h]["n"], ct[h]["cutoffs"], ct[h]["event"], ct[h]["nonevent"]))
        L.append("LOOP BAR: COUNTS ONLY (%s)" % "; ".join(why))
        return "\n".join(L), {"counts": ct, "verdict": v, "reasons": why}
    for h in HORIZONS:
        L.append(_line(h, res[h]) + " event=%d nonevent=%d" % (counts[h]["event"], counts[h]["nonevent"]))
    L.append("LOOP BAR: %s%s" % (v, " (" + "; ".join(why) + ")" if why else ""))
    return "\n".join(L), {"results": res, "counts": counts, "verdict": v, "reasons": why}


NOTE_MARK = "realised window rebuilt"  # build_rows note: build_rows did not drop this capture; later scoring or the s60 check may still exclude it


def row_id(r):
    return "%s %s %s" % (r.get("ticker"), str(r.get("as_of"))[:10], r.get("horizon"))


def exclusion_lines(gaps, dropped_rows, unnumbered):
    """Everything that did not enter the run, with reasons. gaps: the list
    R.build_rows returns (entries that only note a rebuilt realised window
    are printed as notes, not exclusions); dropped_rows: identifiers of rows
    without a v2 sigma; unnumbered: paths of captures with no cell number.
    Each omitted observation gets its own line."""
    drops = [g for g in gaps if NOTE_MARK not in g]
    notes = [g for g in gaps if NOTE_MARK in g]
    L = ["EXCLUDED: %d capture(s) dropped by build_rows, %d row(s) without a v2 sigma, "
         "%d unnumbered capture(s) never scored; %d note(s) (rebuild notes, not exclusions)" % (
             len(drops), len(dropped_rows), len(unnumbered), len(notes))]
    L.extend("excluded: %s" % g for g in drops)
    L.extend("excluded: row %s: no v2 sigma" % x for x in dropped_rows)
    L.extend("excluded: capture %s: no cell number, never scored" % x for x in unnumbered)
    L.extend("note: %s" % g for g in notes)
    return L


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="mode", required=True)
    f = sub.add_parser("fit")
    f.add_argument("--captures", nargs="+", required=True)
    f.add_argument("--out", required=True)
    d = sub.add_parser("describe")
    d.add_argument("--captures", nargs="+", required=True)
    d.add_argument("--frozen", required=True)
    d.add_argument("--min-cell", type=int, default=48)
    d.add_argument("--max-cell", type=int, default=DESC_MAX_CELL)
    d.add_argument("--reps", type=int, default=A.DEFAULT_REPS)
    d.add_argument("--json", default=None)
    s = sub.add_parser("score")
    s.add_argument("--captures", nargs="+", required=True)
    s.add_argument("--frozen", required=True)
    s.add_argument("--min-cell", type=int, default=CLEAN_MIN_CELL)
    s.add_argument("--reps", type=int, default=A.DEFAULT_REPS)
    s.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    if a.mode == "describe" and not (TRAIN_MAX_CELL < a.min_cell <= a.max_cell <= DESC_MAX_CELL):
        print("refusing: describe needs %d <= min-cell <= max-cell <= %d (cells %d+ go through score)" % (
            TRAIN_MAX_CELL + 1, DESC_MAX_CELL, CLEAN_MIN_CELL))
        return 2
    if a.mode == "score" and a.min_cell < CLEAN_MIN_CELL:
        print("refusing: score is for cells >= %d only" % CLEAN_MIN_CELL)
        return 2
    allc = A.find_captures(a.captures, None)
    if not allc:
        print("refusing: no captures found under %s" % " ".join(a.captures))
        return 2
    season = load_season()
    num = A.cell_number
    if a.mode == "fit":
        caps = [c for c in allc if num(c) is not None and num(c) <= TRAIN_MAX_CELL]
        rows, gaps = R.build_rows(caps, allc)
        if not rows:
            print("refusing: no training rows; %s not written" % a.out)
            return 2
        fz = {"season_windows": len(season), "horizons": {h: fit_horizon(rows, h, season) for h in HORIZONS}}
        print("TRAINING CELLS 1-%d" % TRAIN_MAX_CELL)
        for h in HORIZONS:
            p = fz["horizons"][h]
            print("%s: event=%d nonevent=%d fitted=%s m_event=%.2f m_nonevent=%.3f" % (
                h, p["n_event"], p["n_nonevent"], p["fitted"], p["m_event"], p["m_nonevent"]))
        ex = exclusion_lines(gaps, [row_id(r) for r in rows if not r.get("v2_sigma")],
                             [c for c in allc if num(c) is None])
        print("\n".join(ex))
        with open(a.out, "w", encoding="utf-8") as fh:
            json.dump({"frozen": fz}, fh, indent=1)
        return 0
    fz = json.load(open(a.frozen))["frozen"]
    hi = a.max_cell if a.mode == "describe" else 10 ** 9
    caps = [c for c in allc if num(c) is not None and a.min_cell <= num(c) <= hi]
    rows, gaps = R.build_rows(caps, allc)
    pairs = score_rows(rows, fz, season)
    ex = exclusion_lines(gaps, [row_id(r) for r in rows if not r.get("v2_sigma")],
                         [c for c in allc if num(c) is None])
    res = R.evaluate(pairs, a.reps)
    counts = group_counts(pairs)
    if a.mode == "describe":
        print("DESCRIPTIVE ONLY cells %d-%d, no verdict" % (a.min_cell, a.max_cell))
        for h in HORIZONS:
            print(_line(h, res[h]) + " event=%d nonevent=%d" % (counts[h]["event"], counts[h]["nonevent"]))
        if a.json:
            json.dump({"descriptive": True, "results": res, "counts": counts, "excluded": ex},
                      open(a.json, "w", encoding="utf-8"), indent=1)
        print("\n".join(ex))
        return 0
    v, why = loop_bar.loop_bar_verdict(res)
    text, payload = clean_report(res, counts, a.min_cell, v, why)
    print(text)
    print("\n".join(ex))
    payload["excluded"] = ex
    if a.json:
        json.dump(payload, open(a.json, "w", encoding="utf-8"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
