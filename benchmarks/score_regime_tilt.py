#!/usr/bin/env python3
"""Round 88: regime-tilt cell scorer over frozen v2 (stdlib). Pre-registration:
docs/round88_regime_tilt_scorer_prereg.md (committed before any number);
parent design docs/round78_regime_macro_tilt_design.md. Additive; nothing
edits ensemble.py or frozen values.

Usage:
  score_regime_tilt.py fit --captures DIR ... --out FILE
  score_regime_tilt.py describe --frozen FILE --captures DIR ... [--min-cell 48 --max-cell 90]
  score_regime_tilt.py score --frozen FILE --captures DIR ... [--min-cell 91]
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
import loop_bar  # noqa: E402
import regime_macro_tilt_shadow as T  # noqa: E402

HORIZONS = A.HORIZONS
REGIMES = T.REGIME_LABELS
DECISIONS = os.path.join(ROOT, "evaluation", "macro_series", "cbe_decisions.json")
W_GRID = (0.9, 1.0, 1.1)
W_MIN, W_MAX = 0.9, 1.1
MIN_GROUP = 5
TRAIN_MAX_CELL = 47
CLEAN_MIN_CELL = 91
DESC_MAX_CELL = 90
NOTE_MARK = "realised window rebuilt"  # build_rows note: build_rows did not drop it


def clip(w):
    return min(W_MAX, max(W_MIN, w))


def v2_half(row):
    h = row["horizon"]
    return R.half_pct(row["v2_sigma"], h, ens_mod.V2_BAND_K[h], row["mult"])


def regime_of(row, decisions):
    return T.regime_from_decisions(decisions, row["as_of"][:10])


def regime_counts(rows, decisions):
    """{horizon: {regime or 'none': {rows, cutoffs}}} over rows with a v2 sigma."""
    out = {h: {} for h in HORIZONS}
    seen = {h: {} for h in HORIZONS}
    for r in rows:
        if not r.get("v2_sigma"):
            continue
        g = regime_of(r, decisions) or "none"
        c = out[r["horizon"]].setdefault(g, {"rows": 0, "cutoffs": 0})
        c["rows"] += 1
        seen[r["horizon"]].setdefault(g, set()).add(r["as_of"][:10])
    for h in HORIZONS:
        for g, s in seen[h].items():
            out[h][g]["cutoffs"] = len(s)
    return out


def degenerate(counts):
    """True when the rows hold at most one regime at every horizon."""
    return all(len([g for g in counts[h] if g != "none"]) <= 1 for h in HORIZONS)


def fit_horizon(rows, h, decisions):
    """Per regime: w chosen by lowest mean interval score, ties to 1.0."""
    out = {}
    for g in REGIMES:
        grp = [r for r in rows if r["horizon"] == h and r.get("v2_sigma")
               and regime_of(r, decisions) == g]
        o = {"n": len(grp), "w": 1.0, "fitted": False}
        if len(grp) >= MIN_GROUP:
            best = None
            for w in W_GRID:
                m = sum(R.row_is(r, clip(w) * v2_half(r)) for r in grp) / len(grp)
                key = (round(m, 9), abs(w - 1.0))
                if best is None or key < best[0]:
                    best = (key, w)
            o.update(w=clip(best[1]), fitted=True)
        out[g] = o
    return out


def score_rows(rows, frozen, decisions):
    out = []
    for r in rows:
        h = r["horizon"]
        if not r.get("v2_sigma"):
            continue
        g = regime_of(r, decisions)
        w = frozen["horizons"][h].get(g, {}).get("w", 1.0) if g else 1.0
        v2 = v2_half(r)
        ch = clip(w) * v2
        out.append({"ticker": r["ticker"], "as_of": r["as_of"], "horizon": h,
                    "regime": g or "none", "event": g or "none",
                    "is_naive": R.row_is(r, r["naive_half"]),
                    "is_v2": R.row_is(r, v2), "is_ch": R.row_is(r, ch),
                    "in_v2": abs(r["real"]) <= v2, "in_ch": abs(r["real"]) <= ch})
    return out


def group_counts(pairs):
    out = {}
    for h in HORIZONS:
        c = {}
        for p in pairs:
            if p["horizon"] == h:
                c[p["regime"]] = c.get(p["regime"], 0) + 1
        out[h] = c
    return out


def _line(h, c):
    return ("%s: n=%d cutoffs=%d coverage %s RangeSkill %s CI cutoff [%s, %s] cov CI [%s, %s]"
            " | v2 coverage %s RangeSkill %s" % (
                h, c["n"], c["cutoffs"], R._f(c["ch"]["coverage"]), R._f(c["ch"]["range_skill"]),
                R._f(c["ch_ci_cutoff"][0]), R._f(c["ch_ci_cutoff"][1]),
                R._f(c["ch_cov_ci_cutoff"][0]), R._f(c["ch_cov_ci_cutoff"][1]),
                R._f(c["v2"]["coverage"]), R._f(c["v2"]["range_skill"])))


def count_lines(title, counts):
    L = [title]
    for h in HORIZONS:
        L.append("%s: %s" % (h, ", ".join("%s rows=%d cutoffs=%d" % (g, c["rows"], c["cutoffs"])
                                          for g, c in sorted(counts[h].items())) or "no rows"))
    if degenerate(counts):
        L.append("TILT DEGENERATE: these cells hold a single regime, so no regime contrast exists")
    return L


def row_id(r):
    return "%s %s %s" % (r.get("ticker"), str(r.get("as_of"))[:10], r.get("horizon"))


def exclusion_lines(gaps, dropped_rows, unnumbered):
    """Everything that did not enter the run, with reasons. gaps: the list
    R.build_rows returns; dropped_rows: identifiers of rows without a v2
    sigma; unnumbered: paths of captures with no cell number. Each omitted
    observation gets its own line."""
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


def clean_report(res, counts, cells, v, why):
    """COUNTS ONLY: counts and reasons only, no coverage, skill or CI."""
    L = ["CLEAN SCORING cells >= %d" % cells]
    if v == "COUNTS ONLY":
        ct = {h: {"n": res[h]["n"], "cutoffs": res[h]["cutoffs"], "by_regime": counts[h]} for h in HORIZONS}
        for h in HORIZONS:
            L.append("%s: n=%d cutoffs=%d by regime %s" % (h, ct[h]["n"], ct[h]["cutoffs"], counts[h]))
        L.append("LOOP BAR: COUNTS ONLY (%s)" % "; ".join(why))
        return "\n".join(L), {"counts": ct, "verdict": v, "reasons": why}
    for h in HORIZONS:
        L.append(_line(h, res[h]) + " by regime %s" % counts[h])
    L.append("LOOP BAR: %s%s" % (v, " (" + "; ".join(why) + ")" if why else ""))
    return "\n".join(L), {"results": res, "counts": counts, "verdict": v, "reasons": why}


def load_decisions(path=DECISIONS):
    try:
        return T.load_decisions(path)
    except (OSError, ValueError):
        return [], 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="mode", required=True)
    f = sub.add_parser("fit")
    f.add_argument("--captures", nargs="+", required=True)
    f.add_argument("--out", required=True)
    f.add_argument("--decisions", default=DECISIONS)
    d = sub.add_parser("describe")
    d.add_argument("--captures", nargs="+", required=True)
    d.add_argument("--frozen", required=True)
    d.add_argument("--decisions", default=DECISIONS)
    d.add_argument("--min-cell", type=int, default=TRAIN_MAX_CELL + 1)
    d.add_argument("--max-cell", type=int, default=DESC_MAX_CELL)
    d.add_argument("--reps", type=int, default=A.DEFAULT_REPS)
    d.add_argument("--json", default=None)
    s = sub.add_parser("score")
    s.add_argument("--captures", nargs="+", required=True)
    s.add_argument("--frozen", required=True)
    s.add_argument("--decisions", default=DECISIONS)
    s.add_argument("--min-cell", type=int, default=CLEAN_MIN_CELL)
    s.add_argument("--reps", type=int, default=A.DEFAULT_REPS)
    s.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    if a.mode == "score" and a.min_cell < CLEAN_MIN_CELL:
        print("refusing: score is for cells >= %d only" % CLEAN_MIN_CELL)
        return 2
    if a.mode == "describe" and not (TRAIN_MAX_CELL < a.min_cell <= a.max_cell <= DESC_MAX_CELL):
        print("refusing: describe needs %d <= min-cell <= max-cell <= %d (cells %d+ go through score)" % (
            TRAIN_MAX_CELL + 1, DESC_MAX_CELL, CLEAN_MIN_CELL))
        return 2
    allc = A.find_captures(a.captures, None)
    if not allc:
        print("refusing: no captures found under %s" % " ".join(a.captures))
        return 2
    decisions, n_rej = load_decisions(a.decisions)
    if not decisions:
        print("refusing: no usable decisions in %s (%d rejected)" % (a.decisions, n_rej))
        return 2
    num = A.cell_number
    unnumbered = [c for c in allc if num(c) is None]
    if a.mode == "fit":
        caps = [c for c in allc if num(c) is not None and num(c) <= TRAIN_MAX_CELL]
        rows, gaps = R.build_rows(caps, allc)
        if not rows:
            print("refusing: no training rows; %s not written" % a.out)
            return 2
        counts = regime_counts(rows, decisions)
        L = count_lines("TRAINING CELLS 1-%d regime counts" % TRAIN_MAX_CELL, counts)
        fz = {"decisions_rejected": n_rej, "degenerate": degenerate(counts),
              "horizons": {h: fit_horizon(rows, h, decisions) for h in HORIZONS}}
        for h in HORIZONS:
            L.append("%s: " % h + ", ".join("%s n=%d fitted=%s w=%.2f" % (
                g, p["n"], p["fitted"], p["w"]) for g, p in fz["horizons"][h].items()))
        L.extend(exclusion_lines(gaps, [row_id(r) for r in rows if not r.get("v2_sigma")], unnumbered))
        print("\n".join(L))
        with open(a.out, "w", encoding="utf-8") as fh:
            json.dump({"frozen": fz, "training_regime_counts": counts}, fh, indent=1)
        return 0
    fz = json.load(open(a.frozen))["frozen"]
    hi = a.max_cell if a.mode == "describe" else 10 ** 9
    caps = [c for c in allc if num(c) is not None and a.min_cell <= num(c) <= hi]
    rows, gaps = R.build_rows(caps, allc)
    pairs = score_rows(rows, fz, decisions)
    ex = exclusion_lines(gaps, [row_id(r) for r in rows if not r.get("v2_sigma")], unnumbered)
    res = R.evaluate(pairs, a.reps)
    counts = group_counts(pairs)
    rc = regime_counts(rows, decisions)
    if a.mode == "describe":
        L = count_lines("DESCRIPTIVE ONLY cells %d-%d, no verdict; regime counts" % (a.min_cell, a.max_cell), rc)
        for h in HORIZONS:
            L.append(_line(h, res[h]) + " by regime %s" % counts[h])
        print("\n".join(L + ex))
        if a.json:
            json.dump({"descriptive": True, "results": res, "counts": counts,
                       "regime_counts": rc, "excluded": ex}, open(a.json, "w", encoding="utf-8"), indent=1)
        return 0
    v, why = loop_bar.loop_bar_verdict(res)
    text, payload = clean_report(res, counts, a.min_cell, v, why)
    print(text)
    if degenerate(rc):
        print("TILT DEGENERATE: cells >= %d hold a single regime" % a.min_cell)
    print("\n".join(ex))
    payload["excluded"] = ex
    payload["regime_counts"] = rc
    if a.json:
        json.dump(payload, open(a.json, "w", encoding="utf-8"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
