"""Leave-one-cutoff-out and leave-one-ticker-out descriptives for the
shrinkage challenger on cells 48-90 with the FROZEN shared pair (no refit).
Point estimates only per fold: challenger-minus-v2 RangeSkill and challenger
coverage, per horizon. No bootstrap, no verdict wording.

  python3 benchmarks/score_shrinkage_leave_out.py --captures ARCH \
      --ohlcv-dir OHLCV --weights w.json
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import score_shrinkage_challenger as T  # noqa: E402

A, R = T.A, T.R


def fold_stats(rows, a, b):
    pairs = []
    for r in rows:
        is_ch, inside, _ = T.row_scores(r, a, b)
        pairs.append({"as_of": r["base"], "is_naive": R.row_is(r, r["naive_half"]),
                      "is_v2": R.row_is(r, r["half"]), "is_ch": is_ch,
                      "in_ch": inside})
    x, y = A.range_skill(pairs, "ch"), A.range_skill(pairs, "v2")
    if x is None or y is None:
        return None
    return {"n": len(pairs), "diff": x - y, "cov": sum(p["in_ch"] for p in pairs) / len(pairs)}


def build_folds(rows, a, b, key, caps=None):
    """Full-sample row plus one fold per value of `key` left out. With `caps`
    (the in-range captures), each leave-one-cutoff fold recomputes its fully
    mature cluster count from the retained captures and returns
    {"counts_only": N} instead of statistics when N < T.MIN_CLUSTERS.
    Leave-one-ticker folds are unchanged."""
    out = [("all", fold_stats(rows, a, b))]
    for v in sorted({r[key] for r in rows}):
        fr = [r for r in rows if r[key] != v]
        if key == "base" and caps is not None:
            kept = [c for c in caps if os.path.basename(os.path.dirname(c)) != v]
            n_mature = len(T.mature_clusters(kept, fr)[0])
            if n_mature < T.MIN_CLUSTERS:
                out.append((v, {"counts_only": n_mature}))
                continue
        out.append((v, fold_stats(fr, a, b)))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--captures", nargs="+", required=True)
    ap.add_argument("--ohlcv-dir", required=True)
    ap.add_argument("--weights", required=True)
    a = ap.parse_args(argv)
    with open(a.weights, encoding="utf-8") as fh:
        w = json.load(fh)["weights"]
    if not w:
        print("refusing: weights file has no frozen pair")
        return 2
    lo, hi = T.DESC_CELLS
    closes = {fn[:-4].replace("_", "."): T.load_closes(os.path.join(a.ohlcv_dir, fn))
              for fn in sorted(os.listdir(a.ohlcv_dir)) if fn.endswith(".csv")}
    allc, caps = T.cell_caps(a.captures, lo, hi)
    # In-range captures only as the reference set (see the challenger).
    pend = []
    rows, gaps = R.build_rows(caps, pending=pend)
    usable, ex = T.prepare(rows, closes)
    ex = ex + T.pending_exclusions(pend)
    print("COUNTS cells %d-%d: %d usable rows, frozen pair a=%s b=%s, no refit" % (lo, hi, len(usable), w[0], w[1]))
    gex, rebuilt = T.split_gaps(gaps)
    print("REBUILT WINDOWS (scored, not exclusions)")
    print("\n".join(rebuilt))
    notes = T.endpoint_notes(usable)
    print("ENDPOINT DATE DIFFERENCES (scored, not exclusions): %d" % len(notes))
    print("\n".join(notes))
    print("EXCLUSIONS (every one listed, before any fold; excluded rows stay out of the folds)")
    print("\n".join(["excluded: %s" % g for g in gex] + ex))
    crossed = ["crossed edges: %s (reason: crossed edges, v2 interval used)" % r["key"]
               for r in usable if T.row_scores(r, w[0], w[1])[2]]
    print("CROSSED-EDGE FALLBACKS (every one listed, before any fold; rows stay in scoring): %d" % len(crossed))
    print("\n".join(crossed))
    mature = {}
    for h in T.HORIZONS:
        mt, al = T.mature_clusters(caps, [r for r in usable if r["horizon"] == h])
        mature[h] = (len(mt), len(al))
    gated = T.gate_horizons(mature)
    for h in T.HORIZONS:
        hp = [r for r in usable if r["horizon"] == h]
        if h in gated:
            print("%s: COUNTS ONLY, %d of %d cutoff clusters fully mature (registered minimum %d); "
                  "no fold differences or coverage (gate enforced in code)" % (h, mature[h][0], mature[h][1], T.MIN_CLUSTERS))
            continue
        for key, label in (("base", "cutoff"), ("ticker", "ticker")):
            print("%s, leave one %s out (diff = challenger minus v2 RangeSkill):" % (h, label))
            for v, st in build_folds(hp, w[0], w[1], key, caps):
                if st is None:
                    print("  %s: n/a" % v)
                elif "counts_only" in st:
                    print("  %-12s COUNTS ONLY, %d fully mature clusters retained (registered minimum %d); "
                          "no difference or coverage" % (v, st["counts_only"], T.MIN_CLUSTERS))
                else:
                    print("  %-12s n=%2d diff %+.3f coverage %.3f" % (v, st["n"], st["diff"], st["cov"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
