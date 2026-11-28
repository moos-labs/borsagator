"""Week-signal mechanism on cells 48-90 with the FROZEN shared pair (no
refit): per-ticker and per-cutoff RangeSkill delta vs frozen v2, and a
centre-vs-width decomposition. Descriptive, numbers only.

Decomposition (all vs v2, same rows, same RangeSkill): the challenger
interval [L, U] has width W_c = U - L and centre C_c = (L + U) / 2; v2 is
[-h, h] (width 2h, centre 0). Three variants:
  full    = [L, U]
  centre  = v2 width 2h placed at the challenger centre C_c
  width   = challenger width W_c placed at the v2 centre 0
The two parts need not add up to the full diff (interaction), which is
printed as the remainder.

  python3 benchmarks/score_shrinkage_mechanism.py --captures ARCH \
      --ohlcv-dir OHLCV --weights w.json [--horizon week]
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import score_shrinkage_challenger as T  # noqa: E402

A, R, bs = T.A, T.R, T.bs


def edges(r, a, b):
    lo, hi = T.mix_edges(r["half"], r["q_lo"], r["q_hi"], a, b)
    if lo >= hi:
        lo, hi = -r["half"], r["half"]
    return lo, hi


def pair_for(r, lo, hi):
    return {"as_of": r["base"], "is_naive": R.row_is(r, r["naive_half"]),
            "is_v2": R.row_is(r, r["half"]),
            "is_x": bs.winkler_is(r["real"], lo, hi),
            "in_x": lo <= r["real"] <= hi}


def variant_rows(rows, a, b, kind):
    out = []
    for r in rows:
        lo, hi = edges(r, a, b)
        c, w = (lo + hi) / 2.0, hi - lo
        if kind == "full":
            e = (lo, hi)
        elif kind == "centre":
            e = (c - r["half"], c + r["half"])
        else:
            e = (-w / 2.0, w / 2.0)
        out.append(pair_for(r, *e))
    return out


def diff(rows, a, b, kind):
    p = variant_rows(rows, a, b, kind)
    x, y = A.range_skill(p, "x"), A.range_skill(p, "v2")
    if x is None or y is None:
        return None
    return x - y


def summary(rows, a, b):
    """Mean challenger centre shift and width ratio vs v2 (pct points)."""
    sh, wr = [], []
    for r in rows:
        lo, hi = edges(r, a, b)
        sh.append((lo + hi) / 2.0)
        wr.append((hi - lo) / (2.0 * r["half"]))
    n = len(rows)
    return sum(sh) / n, sum(wr) / n


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--captures", nargs="+", required=True)
    ap.add_argument("--ohlcv-dir", required=True)
    ap.add_argument("--weights", required=True)
    ap.add_argument("--horizon", default="week", choices=T.HORIZONS)
    a = ap.parse_args(argv)
    with open(a.weights, encoding="utf-8") as fh:
        w = json.load(fh)["weights"]
    if not w:
        print("refusing: weights file has no frozen pair")
        return 2
    lo_c, hi_c = T.DESC_CELLS
    closes = {fn[:-4].replace("_", "."): T.load_closes(os.path.join(a.ohlcv_dir, fn))
              for fn in sorted(os.listdir(a.ohlcv_dir)) if fn.endswith(".csv")}
    allc, caps = T.cell_caps(a.captures, lo_c, hi_c)
    rows, gaps = R.build_rows(caps, allc)
    usable, ex = T.prepare(rows, closes)
    hp = [r for r in usable if r["horizon"] == a.horizon]
    pa, pb = w
    print("COUNTS cells %d-%d, %s: %d rows, %d cutoffs, %d tickers, frozen pair a=%s b=%s, no refit"
          % (lo_c, hi_c, a.horizon, len(hp), len({r["base"] for r in hp}),
             len({r["ticker"] for r in hp}), pa, pb))
    full, cen, wid = (diff(hp, pa, pb, k) for k in ("full", "centre", "width"))
    sh, wr = summary(hp, pa, pb)
    print("DECOMPOSITION (RangeSkill diff vs v2): full %+.3f, centre-only %+.3f, width-only %+.3f, remainder %+.3f"
          % (full, cen, wid, full - cen - wid))
    print("mean centre shift %+.3f pct points, mean width ratio challenger/v2 %.3f" % (sh, wr))
    for key, label in (("ticker", "ticker"), ("base", "cutoff")):
        print("PER %s (own rows only; diff full / centre-only / width-only, coverage, n):" % label.upper())
        for v in sorted({r[key] for r in hp}):
            sub = [r for r in hp if r[key] == v]
            f2, c2, w2 = (diff(sub, pa, pb, k) for k in ("full", "centre", "width"))
            cov = sum(p["in_x"] for p in variant_rows(sub, pa, pb, "full")) / len(sub)
            if f2 is None:
                print("  %-12s n=%2d n/a" % (v, len(sub)))
            else:
                print("  %-12s n=%2d %+.3f / %+.3f / %+.3f  cov %.3f" % (v, len(sub), f2, c2, w2, cov))
    return 0


if __name__ == "__main__":
    sys.exit(main())
