#!/usr/bin/env python3
"""Round 85 challenger 2: log-HAR vol forecast + quantile-regression band width.

Pre-registration: docs/round85_loghar_quantile_prereg.md (committed before
any number). Reuses replay_log_har.py unchanged for the volatility
forecast; the new part is the width map half = exp(a) * unit**b, with
(a, b) the tau = 0.80 linear quantile regression of ln|move| on ln(unit)
fitted per horizon on training cells 1-47 only. Additive: nothing edits
scripts/ensemble.py or frozen values.

Usage:
  replay_loghar_quantile.py fit --captures DIR ... --out FILE
  replay_loghar_quantile.py describe --captures DIR ... [--min-cell 48 --max-cell 102]
      (numbers only, no verdict; plain log-HAR control alongside)
  replay_loghar_quantile.py score --frozen FILE --captures DIR ... [--min-cell 91]
"""
import argparse
import json
import math
import os
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import replay_log_har as H  # noqa: E402
import replay_band_candidates as R  # noqa: E402
import score_adoption_594 as A  # noqa: E402
import loop_bar  # noqa: E402

HORIZONS = A.HORIZONS
TAU = 0.80
MOVE_FLOOR = 0.01
MIN_TRAIN_ROWS = 8
TRAIN_MAX_CELL = 47
CLEAN_MIN_CELL = 91
KEY = H.KEY


def pinball(points, a, b, tau=TAU):
    t = 0.0
    for x, y in points:
        e = y - (a + b * x)
        t += tau * e if e >= 0 else (tau - 1.0) * e
    return t


def fit_quantile(points, tau=TAU):
    """Exact line QR for (x, y) points: the pinball optimum passes
    through two points. Ties: smaller |b - 1|, then smaller a."""
    if len(points) < MIN_TRAIN_ROWS:
        return None
    best = None
    for i in range(len(points)):
        for j in range(i + 1, len(points)):
            x1, y1 = points[i]
            x2, y2 = points[j]
            if x1 == x2:
                continue
            b = (y2 - y1) / (x2 - x1)
            a = y1 - b * x1
            key = (round(pinball(points, a, b, tau), 9), abs(b - 1.0), a)
            if best is None or key < best[0]:
                best = (key, a, b)
    if best is None:
        return None
    return {"a": best[1], "b": best[2], "loss": best[0][0], "n": len(points)}


def unit_pct(row):
    return R.half_pct(row[KEY], row["horizon"], 1.0, row["mult"])


def train_points(rows, h):
    pts = []
    for r in rows:
        if r["horizon"] != h or not r.get(KEY):
            continue
        u = unit_pct(r)
        if u <= 0:
            continue
        pts.append((math.log(u), math.log(max(abs(r["real"]), MOVE_FLOOR))))
    return pts


def quantile_half(row, ab):
    return math.exp(ab["a"]) * unit_pct(row) ** ab["b"]


def fit(rows):
    q = {}
    for h in HORIZONS:
        q[h] = fit_quantile(train_points(rows, h))
    cells = sorted({r["cell"] for r in rows if r["cell"] is not None})
    return {"spec": {"tau": TAU, "move_floor": MOVE_FLOOR,
                     "min_train_rows": MIN_TRAIN_ROWS, "rv": H.RV["mode"]},
            "quantile": q,
            "plain_k_control": {h: H.V.fit_k([r for r in rows if r.get(KEY)], h, KEY)
                                for h in HORIZONS},
            "fit_cells": [cells[0], cells[-1]] if cells else None}


def score_rows(rows, frozen):
    out = []
    for r in rows:
        s = r.get(KEY)
        ab = frozen["quantile"].get(r["horizon"])
        if not s or not r["v2_sigma"] or not ab:
            continue
        h = r["horizon"]
        ch = quantile_half(r, ab)
        v2 = R.half_pct(r["v2_sigma"], h, H.ens_mod.V2_BAND_K[h], r["mult"])
        out.append({"ticker": r["ticker"], "as_of": r["as_of"], "horizon": h,
                    "is_naive": R.row_is(r, r["naive_half"]),
                    "is_v2": R.row_is(r, v2), "is_ch": R.row_is(r, ch),
                    "in_v2": abs(r["real"]) <= v2, "in_ch": abs(r["real"]) <= ch})
    return out


def _line(h, c, tag):
    return "%s %s: n=%d cutoffs=%d coverage %s RangeSkill %s CI cutoff [%s, %s] cov CI [%s, %s]" % (
        h, tag, c["n"], c["cutoffs"], R._f(c["ch"]["coverage"]), R._f(c["ch"]["range_skill"]),
        R._f(c["ch_ci_cutoff"][0]), R._f(c["ch_ci_cutoff"][1]),
        R._f(c["ch_cov_ci_cutoff"][0]), R._f(c["ch_cov_ci_cutoff"][1]))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="mode", required=True)
    f = sub.add_parser("fit")
    f.add_argument("--captures", nargs="+", required=True)
    f.add_argument("--out", required=True)
    f.add_argument("--reps", type=int, default=A.DEFAULT_REPS)
    d = sub.add_parser("describe")
    d.add_argument("--captures", nargs="+", required=True)
    d.add_argument("--frozen", required=True)
    d.add_argument("--min-cell", type=int, default=48)
    d.add_argument("--max-cell", type=int, default=102)
    d.add_argument("--reps", type=int, default=A.DEFAULT_REPS)
    d.add_argument("--json", default=None)
    s = sub.add_parser("score")
    s.add_argument("--frozen", required=True)
    s.add_argument("--captures", nargs="+", required=True)
    s.add_argument("--min-cell", type=int, default=CLEAN_MIN_CELL)
    s.add_argument("--reps", type=int, default=A.DEFAULT_REPS)
    s.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    if a.mode == "score" and a.min_cell < CLEAN_MIN_CELL:
        print("refusing: score is for cells >= %d only" % CLEAN_MIN_CELL)
        return 2
    allc = A.find_captures(a.captures, None)
    num = A.cell_number
    if a.mode == "fit":
        caps = [c for c in allc if num(c) is not None and num(c) <= TRAIN_MAX_CELL]
        rows, _g = H.build_rows(caps, allc)
        fz = fit(rows)
        print("TRAINING CELLS 1-%d" % TRAIN_MAX_CELL)
        for h in HORIZONS:
            q = fz["quantile"][h]
            print("%s: quantile a=%s b=%s n=%s | plain log-HAR k=%s" % (
                h, R._f(q and q["a"]), R._f(q and q["b"]), q and q["n"],
                R._f(fz["plain_k_control"][h])))
        tr = score_rows(rows, fz)
        res = R.evaluate(tr, a.reps)
        for h in HORIZONS:
            print(_line(h, res[h], "quantile (in-sample)") +
                  " | v2 coverage %s RangeSkill %s" % (R._f(res[h]["v2"]["coverage"]),
                                                       R._f(res[h]["v2"]["range_skill"])))
        with open(a.out, "w", encoding="utf-8") as fh:
            json.dump({"frozen": fz}, fh, indent=1)
        return 0
    fz = json.load(open(a.frozen))["frozen"]
    hi = a.max_cell if a.mode == "describe" else 10 ** 9
    caps = [c for c in allc if num(c) is not None and a.min_cell <= num(c) <= hi]
    rows, _g = H.build_rows(caps, allc)
    res = R.evaluate(score_rows(rows, fz), a.reps)
    if a.mode == "describe":
        ctl = R.evaluate(H.score_rows(rows, {"k": fz["plain_k_control"]}), a.reps)
        print("DESCRIPTIVE ONLY cells %d-%d, no verdict" % (a.min_cell, a.max_cell))
        for h in HORIZONS:
            print(_line(h, res[h], "quantile") + " | v2 coverage %s RangeSkill %s" % (
                R._f(res[h]["v2"]["coverage"]), R._f(res[h]["v2"]["range_skill"])))
            print(_line(h, ctl[h], "plain log-HAR control"))
        if a.json:
            json.dump({"descriptive": True, "results": res, "control": ctl},
                      open(a.json, "w", encoding="utf-8"), indent=1)
        return 0
    v, why = loop_bar.loop_bar_verdict(res)
    print("CLEAN SCORING cells >= %d" % a.min_cell)
    for h in HORIZONS:
        print(_line(h, res[h], "quantile") + " | v2 coverage %s RangeSkill %s" % (
            R._f(res[h]["v2"]["coverage"]), R._f(res[h]["v2"]["range_skill"])))
    print("LOOP BAR: %s%s" % (v, " (" + "; ".join(why) + ")" if why else ""))
    if a.json:
        json.dump({"results": res, "verdict": v, "reasons": why},
                  open(a.json, "w", encoding="utf-8"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
