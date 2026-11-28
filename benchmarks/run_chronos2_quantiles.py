#!/usr/bin/env python3
"""LLM-free Chronos-2 quantile runner for experiment E (round 93).

Writes <capture>/collected/chronos-2/quantiles.json in the format
benchmarks/score_tsfm_control.py reads, one forecast per capture:
  {"model": "chronos-2", "base_date": "YYYY-MM-DD",
   "context_sessions": N, "last_close_date": "...", "dtype": "bfloat16",
   "horizons": {"day": {"q10": x, "q50": y, "q90": z},
                "week": {...}, "month": {...}}}
Values are the cumulative return in PERCENT from the last close at steps
1 / 5 / 21: (price quantile at that step / last close - 1) x 100, from the
model's own per-step quantiles at 0.10 / 0.50 / 0.90. Nothing is fitted
and no multiplier is applied here (RISK_MULT is the scorer's).

Context: the capture's own price.csv closes dated on or before the
capture's cutoff (the <cutoff> directory name), at most CONTEXT_SESSIONS
(750, the value in the scorer's format example, fixed) latest closes,
at least MIN_CONTEXT (120). The model sees values only: the closes are
placed on a synthetic regular daily index, because EGX trades Sunday to
Thursday and Chronos2Pipeline.predict_df cannot infer a frequency from
those dates. No covariate, index or news is passed.

Guard (round 93, docs/round93_chronos2_prereg.md): without
--allow-verdict-cells the runner refuses any capture that is numbered
48 or higher, or whose cutoff is not strictly before 2025-10-20, so
smoke tests and hardware checks touch only pre-release, non-verdict
contexts. Every refused, skipped or failed capture is listed with its
reason. Existing quantiles.json files are kept unless --force.

Usage:
  python3 benchmarks/run_chronos2_quantiles.py --captures DIR ...
      [--out-root DIR] [--limit N] [--force] [--allow-verdict-cells]
Needs torch, pandas and chronos-forecasting only for the real model;
tests inject a stub forecaster and never import them.
"""
import argparse
import csv
import json
import math
import os
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import score_adoption_594 as A  # noqa: E402

MODEL = "chronos-2"
CONTEXT_SESSIONS = 750
MIN_CONTEXT = 120
STEPS = {"day": 1, "week": 5, "month": 21}
MAX_STEP = 21
LEVELS = (0.1, 0.5, 0.9)
RELEASE_DATE = "2025-10-20"
VERDICT_MIN_CELL = 48


def read_closes(capture, cutoff):
    """[(date, close)] from the capture's price.csv with date <= cutoff,
    ascending; None when the file is missing or unreadable."""
    try:
        with open(os.path.join(capture, "price.csv"), encoding="utf-8") as f:
            rows = [(r["date"], float(r["close"])) for r in csv.DictReader(f)
                    if r["date"] <= cutoff and r["close"] not in ("", None)]
    except (OSError, ValueError, KeyError):
        return None
    rows.sort()
    return rows


def cutoff_of(capture):
    return os.path.basename(os.path.dirname(os.path.normpath(capture)))


def guard_reason(capture, cutoff, allow_verdict):
    """Why the capture may not be run by default, or None."""
    if allow_verdict:
        return None
    n = A.cell_number(capture)
    if n is not None and n >= VERDICT_MIN_CELL:
        return "cell %d is a verdict cell (>= %d), needs --allow-verdict-cells" % (
            n, VERDICT_MIN_CELL)
    if not cutoff < RELEASE_DATE:
        return ("cutoff %s is not strictly before %s, needs "
                "--allow-verdict-cells" % (cutoff, RELEASE_DATE))
    return None


def to_horizons(last_close, steps):
    """steps: {k: (q10, q50, q90)} price quantiles for k = 1..MAX_STEP.
    Returns (horizons dict, None) or (None, reason)."""
    if not (math.isfinite(last_close) and last_close > 0):
        return None, "last close %r is not a finite positive number" % (
            last_close,)
    out = {}
    for h, k in STEPS.items():
        if k not in steps:
            return None, "no forecast for step %d" % k
        q = [(float(v) / last_close - 1.0) * 100.0 for v in steps[k]]
        if len(q) != 3 or not all(math.isfinite(v) for v in q):
            return None, "%s has a non-finite return quantile" % h
        r = [round(v, 6) for v in q]
        # validated after rounding: this is what the file holds
        if not (r[0] <= r[1] <= r[2]) or not r[2] > r[0]:
            return None, ("%s quantiles not ordered q10 <= q50 <= q90 "
                          "with q90 > q10 after rounding" % h)
        out[h] = {"q10": r[0], "q50": r[1], "q90": r[2]}
    return out, None


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=1, allow_nan=False)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def run_capture(capture, forecaster, out_root=None, force=False,
                allow_verdict=False):
    """Returns ("written"|"kept"|"excluded", reason or path)."""
    cutoff = cutoff_of(capture)
    why = guard_reason(capture, cutoff, allow_verdict)
    if why:
        return "excluded", why
    if out_root:
        dst = os.path.join(out_root, cutoff, os.path.basename(capture),
                           "collected", MODEL, "quantiles.json")
    else:
        dst = os.path.join(capture, "collected", MODEL, "quantiles.json")
    if os.path.exists(dst) and not force:
        return "kept", dst
    closes = read_closes(capture, cutoff)
    if closes is None:
        return "excluded", "price.csv missing or unreadable"
    closes = closes[-CONTEXT_SESSIONS:]
    if len(closes) < MIN_CONTEXT:
        return "excluded", "only %d closes on or before %s, need %d" % (
            len(closes), cutoff, MIN_CONTEXT)
    try:
        steps = forecaster([c for _, c in closes])
    except Exception as e:  # noqa: BLE001 the reason is listed
        return "excluded", "forecast failed: %s" % type(e).__name__
    try:
        hz, why = to_horizons(closes[-1][1], steps)
    except (ArithmeticError, ValueError, TypeError, KeyError,
            IndexError) as e:
        return "excluded", "forecast not usable: %s" % type(e).__name__
    if hz is None:
        return "excluded", why
    try:
        write_json(dst, {"model": MODEL, "base_date": cutoff,
                         "context_sessions": len(closes),
                         "last_close_date": closes[-1][0],
                         "dtype": "bfloat16", "horizons": hz})
    except (OSError, ValueError, TypeError) as e:
        return "excluded", "write failed: %s" % type(e).__name__
    return "written", dst


def load_chronos2():
    """Real forecaster: bfloat16 on CPU, synthetic daily index."""
    import torch
    import pandas as pd
    from chronos import Chronos2Pipeline
    torch.manual_seed(0)
    pipe = Chronos2Pipeline.from_pretrained(
        "amazon/chronos-2", device_map="cpu", dtype=torch.bfloat16)

    def forecast(values):
        df = pd.DataFrame({
            "id": "s",
            "timestamp": pd.date_range("2000-01-01", periods=len(values),
                                       freq="D"),
            "target": [float(v) for v in values]})
        out = pipe.predict_df(df, prediction_length=MAX_STEP,
                              quantile_levels=list(LEVELS), id_column="id",
                              timestamp_column="timestamp", target="target")
        out = out.sort_values("timestamp").reset_index(drop=True)
        return {k + 1: (float(out.loc[k, "0.1"]), float(out.loc[k, "0.5"]),
                        float(out.loc[k, "0.9"])) for k in range(MAX_STEP)}
    return forecast


class LazyForecaster:
    """Loads the real model on the first forecast call only, so kept,
    guarded and excluded captures never trigger the load."""

    def __init__(self):
        self.fn = None

    def __call__(self, values):
        if self.fn is None:
            self.fn = load_chronos2()
        return self.fn(values)


def main(argv=None, forecaster=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.
                                 RawDescriptionHelpFormatter)
    ap.add_argument("--captures", nargs="+", required=True)
    ap.add_argument("--out-root", default=None)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--allow-verdict-cells", action="store_true")
    a = ap.parse_args(argv)
    caps = A.find_captures(a.captures, None)
    if a.limit is not None:
        caps = caps[:a.limit]
    if not caps:
        print("refusing: no captures found under %s" % " ".join(a.captures))
        return 2
    fc = forecaster if forecaster is not None else LazyForecaster()
    counts = {"written": 0, "kept": 0, "excluded": 0}
    lines = []
    for c in caps:
        try:
            st, info = run_capture(c, fc, a.out_root, a.force,
                                   a.allow_verdict_cells)
        except (OSError, ValueError, TypeError, KeyError, IndexError,
                ArithmeticError) as e:
            st, info = "excluded", "failed: %s" % type(e).__name__
        counts[st] += 1
        if st == "excluded":
            lines.append("excluded: capture %s: %s" % (c, info))
        else:
            print("%s: %s" % (st, info))
    print("captures %d: written %d, kept %d, excluded %d" % (
        len(caps), counts["written"], counts["kept"], counts["excluded"]))
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
