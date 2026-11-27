#!/usr/bin/env python3
"""Round 87: CBE MPC decision-date event windows, width-neutral
reallocation over frozen v2. Pre-registration:
docs/round87_mpc_windows_prereg.md (committed before any number).
Descriptive screen; additive; nothing edits ensemble.py or frozen values.

Usage:
  screen_mpc_windows.py fit --captures DIR ... --out FILE
  screen_mpc_windows.py describe --frozen FILE --captures DIR ... [--min-cell 48 --max-cell 102]
  screen_mpc_windows.py score --frozen FILE --captures DIR ... [--min-cell 91]
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
DECISIONS = os.path.join(ROOT, "evaluation", "macro_series", "cbe_decisions.json")
M_GRID = [round(0.70 + 0.05 * i, 2) for i in range(17)]
MIN_GROUP = 5
TRAIN_MAX_CELL = 47
CLEAN_MIN_CELL = 91
SESSIONS = {"day": 1, "week": 5, "month": 21}
EGX_WEEKEND = (4, 5)  # Friday, Saturday (datetime.weekday)


def load_dates(path=DECISIONS):
    with open(path, encoding="utf-8") as fh:
        return sorted({r["published_date"][:10] for r in json.load(fh)})


def window_end(cutoff, sessions):
    """Date of the sessions-th Egyptian business day (Sun-Thu) after cutoff."""
    d = datetime.date.fromisoformat(cutoff[:10])
    n = 0
    while n < sessions:
        d += datetime.timedelta(days=1)
        if d.weekday() not in EGX_WEEKEND:
            n += 1
    return d.isoformat()


def flagged(cutoff, horizon, dates):
    c = cutoff[:10]
    e = window_end(c, SESSIONS[horizon])
    return any(c < d <= e for d in dates)


def v2_half(row):
    h = row["horizon"]
    return R.half_pct(row["v2_sigma"], h, ens_mod.V2_BAND_K[h], row["mult"])


def split(rows, h, dates):
    ev, ne = [], []
    for r in rows:
        if r["horizon"] != h or not r.get("v2_sigma"):
            continue
        (ev if flagged(r["as_of"], h, dates) else ne).append(r)
    return ev, ne


def fit_horizon(rows, h, dates):
    ev, ne = split(rows, h, dates)
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


def score_rows(rows, frozen, dates):
    out = []
    for r in rows:
        h = r["horizon"]
        if not r.get("v2_sigma"):
            continue
        p = frozen["horizons"][h]
        m = p["m_event"] if flagged(r["as_of"], h, dates) else p["m_nonevent"]
        v2 = v2_half(r)
        ch = m * v2
        out.append({"ticker": r["ticker"], "as_of": r["as_of"], "horizon": h,
                    "event": flagged(r["as_of"], h, dates),
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
    d.add_argument("--max-cell", type=int, default=102)
    d.add_argument("--reps", type=int, default=A.DEFAULT_REPS)
    d.add_argument("--json", default=None)
    s = sub.add_parser("score")
    s.add_argument("--captures", nargs="+", required=True)
    s.add_argument("--frozen", required=True)
    s.add_argument("--min-cell", type=int, default=CLEAN_MIN_CELL)
    s.add_argument("--reps", type=int, default=A.DEFAULT_REPS)
    s.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    if a.mode == "score" and a.min_cell < CLEAN_MIN_CELL:
        print("refusing: score is for cells >= %d only" % CLEAN_MIN_CELL)
        return 2
    allc = A.find_captures(a.captures, None)
    if not allc:
        print("refusing: no captures found under %s" % " ".join(a.captures))
        return 2
    dates = load_dates()
    num = A.cell_number
    if a.mode == "fit":
        caps = [c for c in allc if num(c) is not None and num(c) <= TRAIN_MAX_CELL]
        rows, _g = R.build_rows(caps, allc)
        if not rows:
            print("refusing: no training rows; %s not written" % a.out)
            return 2
        fz = {"decision_dates": len(dates), "horizons": {h: fit_horizon(rows, h, dates) for h in HORIZONS}}
        print("TRAINING CELLS 1-%d" % TRAIN_MAX_CELL)
        for h in HORIZONS:
            p = fz["horizons"][h]
            print("%s: event=%d nonevent=%d fitted=%s m_event=%.2f m_nonevent=%.3f" % (
                h, p["n_event"], p["n_nonevent"], p["fitted"], p["m_event"], p["m_nonevent"]))
        with open(a.out, "w", encoding="utf-8") as fh:
            json.dump({"frozen": fz}, fh, indent=1)
        return 0
    fz = json.load(open(a.frozen))["frozen"]
    hi = a.max_cell if a.mode == "describe" else 10 ** 9
    caps = [c for c in allc if num(c) is not None and a.min_cell <= num(c) <= hi]
    rows, _g = R.build_rows(caps, allc)
    pairs = score_rows(rows, fz, dates)
    res = R.evaluate(pairs, a.reps)
    counts = group_counts(pairs)
    if a.mode == "describe":
        print("DESCRIPTIVE ONLY cells %d-%d, no verdict" % (a.min_cell, a.max_cell))
        for h in HORIZONS:
            print(_line(h, res[h]) + " event=%d nonevent=%d" % (counts[h]["event"], counts[h]["nonevent"]))
        if a.json:
            json.dump({"descriptive": True, "results": res, "counts": counts},
                      open(a.json, "w", encoding="utf-8"), indent=1)
        return 0
    v, why = loop_bar.loop_bar_verdict(res)
    text, payload = clean_report(res, counts, a.min_cell, v, why)
    print(text)
    if a.json:
        json.dump(payload, open(a.json, "w", encoding="utf-8"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
