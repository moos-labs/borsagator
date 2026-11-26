#!/usr/bin/env python3
"""Band calibration layer (issue #593, INS-PUSH T3 procedure).

The shipped p10-p90-style band failed on its CENTRE, not its width:
on the clean forward-ledger rows (48 matured, 12 gap-flagged
excluded per D-79-1, 36 clean) the day band covered 0.476 and the
week band 1.000, with median expected-move bias -8.5 pp (day) and
-22.0 pp (week). No width rescale fixes a biased centre, so this
layer does BOTH, per (ticker, horizon) cell, recomputed
deterministically from the ledger's matured rows:

1. Window: trailing W=30 matured, non-gap-flagged rows for the
   cell. A cell applies at n >= 10, with shrinkage toward the
   horizon pool; public accuracy claims only at n >= 30 (D4).
2. Centre correction: b = median(realised - expected) over the
   window, clamped to |b| <= the window's median half-width.
   Published centre c' = expected + b'.
3. Width factor: k = 85th percentile (nearest-rank) of
   z_i = |(realised - expected) - b| / half_i, clamped to
   [0.5, 2.0]. The quantile construction puts in-window coverage
   at ~0.85 by design, so out-of-sample coverage lands inside
   the 0.75-0.85 launch-gate tolerance.
4. Shrinkage: k' = (n*k + 10*k_H) / (n+10), b' = (n*b + 10*b_H) /
   (n+10), with k_H / b_H the horizon-pooled fits. A cell with
   n < 10 falls back to the horizon pool; a pool with n < 10 falls
   back to k=1, b=0 — the uncalibrated model band, marked as such.
5. Application (ensemble.py, where the band is built):
   centre = expected + b', half = k' x half. Direction is taken
   from the corrected centre so direction and range agree.

6. Launch-gate alerts (accepted #593 design note): a cell pages
   when it holds one full trailing window of independent blocks
   (n_eff >= PUBLIC_N[horizon]: day 30, week 6, month 2) and its
   as-published coverage trips the per-horizon exact-binomial
   predicate (alert_predicate): day outside [0.75, 0.85], week at
   coverage <= 2/6, month at 0/2; no high-side page for week/month.
   One 30-row window can only catch catastrophic week/month
   under-coverage — fine week/month calibration is not decidable at
   6 / 2 independent blocks.

Formula basis: residuals are only meaningful against the centre
formula that produced them, so compute_calibration() can filter
rows to one formula tag (ledger rows carry the producing
ensemble's `formula`). When the centre formula changes, b is
recomputed from that formula's own rows; if the new centre is
unbiased, b converges to 0 and this becomes a pure width control.

This module is a SEPARABLE layer: it sits downstream of whatever
centre/half the ensemble emits and never reaches into the frozen
v2 parameters (#594). Pure functions over row dicts, stdlib only,
deterministic, never raises on malformed rows (they are skipped).
Units follow the rows: ledger rows are in percentage points, so
b is in pp and k is unitless; callers working in fractions scale
b themselves.
"""
import json
import math
import os
import statistics

WINDOW = 30            # trailing matured rows per cell
MIN_N = 10             # a cell (or pool) applies at n >= MIN_N
PRIOR_N = 10           # shrinkage prior weight toward the pool
PUBLIC_N = {"day": 30, "week": 6, "month": 2}
                       # launch-gate alert threshold per horizon: one
                       # full trailing window of independent blocks
                       # (WINDOW / sessions; accepted #593 design)
K_MIN, K_MAX = 0.5, 2.0
TARGET_COVERAGE = 0.80
ALERT_BAND = (0.75, 0.85)   # day launch-gate page band per ticker cell
WEEK_PAGE_LOW = 2.0 / 6.0   # week pages low at coverage <= 2/6 (exact
                            # binomial at target 0.80: ~1.7% false-page)
MONTH_PAGE_LOW = 0.0        # month pages low at 0/2 only (~4% false-page)
                            # No high-side page for week/month: at 6 / 2
                            # blocks a full-window 6/6 or 2/2 reading is
                            # common at true 0.80 coverage.
HORIZONS = ("day", "week", "month")


def effective_n(n, horizon):
    """Non-overlapping-block count for a cell: ceil(n / sessions),
    where sessions are day=1, week=5, month=21. Day is unchanged."""
    sessions = {"day": 1, "week": 5, "month": 21}.get(horizon, 1)
    try:
        n = int(n)
    except (TypeError, ValueError):
        return 0
    if sessions <= 0:
        sessions = 1
    return math.ceil(n / sessions) if n > 0 else 0


def _num(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def row_half(row):
    """Published half-width of a ledger row, in row units (pp)."""
    lo, hi = _num(row.get("range_low_pct")), _num(row.get("range_high_pct"))
    if lo is None or hi is None:
        return None
    return (hi - lo) / 2.0


def row_residual(row):
    """realised - expected, in row units (pp)."""
    exp, real = _num(row.get("expected_move_pct")), _num(row.get("realized_move_pct"))
    if exp is None or real is None:
        return None
    return real - exp


def is_clean_matured(row):
    """A row the calibration may learn from: matured, not
    gap-flagged (D-79-1 excludes dividend_gap rows), with a usable
    residual and a positive published half-width."""
    if not isinstance(row, dict) or row.get("status") != "matured":
        return False
    if row.get("dividend_gap"):
        return False
    half = row_half(row)
    return half is not None and half > 0 and row_residual(row) is not None


def uncalibrated_view(row):
    """Issue #701: the row as the frozen model band published it.

    A row whose band the layer itself calibrated
    (band_calibration.applied == true) carries expected/range
    values already shifted by b' and scaled by k'. Fitting on those
    values makes the layer learn from its own output (feedback
    loop). Instead of dropping such rows (which would starve every
    cell once the layer is live, since all new rows are calibrated),
    the uncalibrated band is reconstructed from the b_pp and k the
    ensemble recorded on the row: expected_raw = expected - b_pp,
    half_raw = half / k, centred on expected_raw. The realised
    move is untouched, so the residual is the frozen model's own.

    Returns a copy of the row for fitting, the row itself when the
    layer did not touch it, or None when the row was calibrated but
    cannot be reconstructed (missing/invalid b_pp or k): such rows
    are excluded rather than guessed. Idempotent: the returned view
    is marked applied=False. Reconstruction carries the rows'
    2-decimal rounding."""
    if not isinstance(row, dict):
        return None
    bc = row.get("band_calibration")
    if not isinstance(bc, dict) or not bc.get("applied"):
        return row
    b, k = _num(bc.get("b_pp")), _num(bc.get("k"))
    exp = _num(row.get("expected_move_pct"))
    half = row_half(row)
    if b is None or k is None or k <= 0 or exp is None or half is None:
        return None
    exp0 = exp - b
    half0 = half / k
    out = dict(row)
    out["expected_move_pct"] = exp0
    out["range_low_pct"] = exp0 - half0
    out["range_high_pct"] = exp0 + half0
    out["band_calibration"] = {"applied": False,
                               "reconstructed_from": bc.get("basis")}
    return out


def _window(rows):
    """Trailing WINDOW rows, deterministic order (as_of, sweep)."""
    ordered = sorted(rows, key=lambda r: (str(r.get("as_of") or ""),
                                          str(r.get("sweep") or "")))
    return ordered[-WINDOW:]


def _quantile85(values):
    """85th percentile, nearest-rank — deterministic.

    The in-sample quantile for k must exceed the target coverage
    (0.80) so that out-of-sample coverage lands inside the 0.75-0.85
    launch-gate tolerance; hence the 0.85 quantile."""
    ordered = sorted(values)
    idx = max(0, math.ceil(0.85 * len(ordered)) - 1)
    return ordered[idx]


def _fit(rows):
    """Raw (unshrunk) fit over one set of clean rows.

    Returns {n, b, k, coverage} or None when no usable rows.
    b is the median residual clamped to the median half-width;
    k is the 85th percentile of |residual - b| / half, clamped
    to [K_MIN, K_MAX]; coverage is the as-published coverage
    (|residual| <= half)."""
    usable = [r for r in rows if is_clean_matured(r)]
    if not usable:
        return None
    residuals = [row_residual(r) for r in usable]
    halves = [row_half(r) for r in usable]
    half_med = statistics.median(halves)
    b = statistics.median(residuals)
    b = max(-half_med, min(half_med, b))
    k = _quantile85([abs(res - b) / h for res, h in zip(residuals, halves)])
    k = max(K_MIN, min(K_MAX, k))
    coverage = sum(1 for res, h in zip(residuals, halves)
                   if abs(res) <= h) / len(usable)
    return {"n": len(usable), "b": b, "k": k, "coverage": coverage}


def _coverage(rows, b, k):
    """Coverage of the band (centre + b, half x k) over rows."""
    usable = [r for r in rows if is_clean_matured(r)]
    if not usable:
        return None
    hits = sum(1 for r in usable
               if abs(row_residual(r) - b) <= k * row_half(r))
    return hits / len(usable)


def compute_calibration(rows, formula=None):
    """Fit the calibration over ledger forecasts_detail rows.

    When `formula` is given, only rows produced by that centre
    formula (row["formula"] == formula) are used — residuals from
    a retired centre must never re-centre its successor.

    Returns {
      "formula": formula, "window": WINDOW, "target": 0.80,
      "cells": {(ticker, horizon): entry},
      "pools": {horizon: {"n", "b", "k", "calibrated"}},
    }
    where entry = {ticker, horizon, n, b, k, calibrated, basis,
    coverage_before, coverage_calibrated, pool_n}. basis is
    "cell" (n >= MIN_N, shrunk toward the pool), "pool" (cell too
    small, horizon pool applied) or "none" (k=1, b=0 — the
    uncalibrated model band)."""
    # Issue #701: never fit on the layer's own output — rows whose
    # band was calibrated are reconstructed to the uncalibrated
    # model band (or excluded when that is impossible).
    views = [uncalibrated_view(r) for r in (rows or [])]
    usable = [r for r in views if r is not None and is_clean_matured(r)]
    if formula is not None:
        usable = [r for r in usable if r.get("formula") == formula]

    pools = {}
    for h in HORIZONS:
        pool_rows = _window([r for r in usable if r.get("horizon") == h])
        fit = _fit(pool_rows)
        if fit and fit["n"] >= MIN_N:
            pools[h] = {"n": fit["n"], "b": fit["b"], "k": fit["k"],
                        "calibrated": True}
        elif fit:
            pools[h] = {"n": fit["n"], "b": 0.0, "k": 1.0,
                        "calibrated": False}
        else:
            pools[h] = {"n": 0, "b": 0.0, "k": 1.0, "calibrated": False}

    cells = {}
    keys = sorted({(r.get("ticker"), r.get("horizon")) for r in usable
                   if r.get("ticker") and r.get("horizon") in HORIZONS})
    for ticker, horizon in keys:
        cell_rows = _window([r for r in usable
                             if r.get("ticker") == ticker
                             and r.get("horizon") == horizon])
        fit = _fit(cell_rows)
        pool = pools[horizon]
        # The shrinkage prior is the pool's RAW fit when the pool
        # itself qualifies, else the uncalibrated (k=1, b=0).
        if pool["calibrated"]:
            prior_b, prior_k = pool["b"], pool["k"]
        else:
            prior_b, prior_k = 0.0, 1.0
        if fit and fit["n"] >= MIN_N:
            n = fit["n"]
            b = (n * fit["b"] + PRIOR_N * prior_b) / (n + PRIOR_N)
            k = (n * fit["k"] + PRIOR_N * prior_k) / (n + PRIOR_N)
            entry = {"ticker": ticker, "horizon": horizon, "n": n,
                     "n_eff": effective_n(n, horizon),
                     "b": b, "k": k, "calibrated": True, "basis": "cell",
                     "coverage_before": fit["coverage"],
                     "coverage_calibrated": _coverage(cell_rows, b, k),
                     "pool_n": pool["n"]}
        elif pool["calibrated"]:
            entry = {"ticker": ticker, "horizon": horizon,
                     "n": fit["n"] if fit else 0,
                     "n_eff": effective_n(fit["n"] if fit else 0, horizon),
                     "b": pool["b"], "k": pool["k"],
                     "calibrated": True, "basis": "pool",
                     "coverage_before": fit["coverage"] if fit else None,
                     "coverage_calibrated": _coverage(
                         cell_rows, pool["b"], pool["k"]) if fit else None,
                     "pool_n": pool["n"]}
        else:
            entry = {"ticker": ticker, "horizon": horizon,
                     "n": fit["n"] if fit else 0,
                     "n_eff": effective_n(fit["n"] if fit else 0, horizon),
                     "b": 0.0, "k": 1.0,
                     "calibrated": False, "basis": "none",
                     "coverage_before": fit["coverage"] if fit else None,
                     "coverage_calibrated": None,
                     "pool_n": pool["n"]}
        cells[(ticker, horizon)] = entry
    return {"formula": formula, "window": WINDOW,
            "target": TARGET_COVERAGE, "cells": cells, "pools": pools}


def apply_calibration(centre, half, entry):
    """Apply one cell entry to a band. Returns
    (centre', half', applied). Uncalibrated entries (or None)
    return the band unchanged — the frozen model band ships as-is
    and is labelled uncalibrated by the caller. `centre` and the
    entry's b must be in the same units."""
    if not entry or not entry.get("calibrated"):
        return centre, half, False
    return centre + entry["b"], half * entry["k"], True


def public_n(horizon):
    """Launch-gate alert threshold for a horizon: one full trailing
    window of independent blocks (WINDOW / sessions — day 30, week 6,
    month 2; accepted #593 design). Unknown horizons gate at the day
    value, matching effective_n's sessions default."""
    return PUBLIC_N.get(horizon, PUBLIC_N["day"])


def alert_predicate(horizon, coverage):
    """Launch-gate page predicate at TARGET_COVERAGE (accepted #593
    design note), exact-binomial so a conforming cell false-pages
    rarely at the horizon's own block count. Day keeps the
    [0.75, 0.85] band on both sides (the status quo). Week pages low
    at coverage <= 2/6 (~1.7% false-page at true 0.80) and month at
    0/2 only (~4%); there is NO high-side page for week/month — a
    full-window 6/6 or 2/2 reading is common at true 0.80, so a
    high-side page would mostly cry wolf. One 30-row window can only
    catch catastrophic week/month under-coverage."""
    if coverage is None:
        return False
    if horizon == "week":
        return coverage <= WEEK_PAGE_LOW
    if horizon == "month":
        return coverage <= MONTH_PAGE_LOW
    return not (ALERT_BAND[0] <= coverage <= ALERT_BAND[1])


def alert_cells(calibration):
    """Cells the guard should page on (triage step 6, accepted #593
    per-horizon predicate): n_eff at one full window of independent
    blocks (PUBLIC_N per horizon) with AS-PUBLISHED coverage tripping
    alert_predicate for the horizon."""
    out = []
    for entry in (calibration.get("cells") or {}).values():
        horizon = entry.get("horizon")
        n_eff = entry.get("n_eff")
        if n_eff is None:
            n_eff = effective_n(entry.get("n", 0), horizon)
        if (n_eff >= public_n(horizon)
                and alert_predicate(horizon, entry.get("coverage_before"))):
            out.append(entry)
    return sorted(out, key=lambda e: (str(e["ticker"]), str(e["horizon"])))


def calibration_table(calibration):
    """Markdown lines for the per-cell table the ledger scoring
    pass emits into ledger/benchmark.md (triage step 6): one row
    per (ticker, horizon) cell with n, as-published coverage,
    calibrated in-window coverage, k and b."""
    lines = ["| Ticker | Horizon | n | n_eff | Coverage (as published) | "
             "Coverage (calibrated, in-window) | k | b (pp) | Basis |",
             "|---|---|---|---|---|---|---|---|---|"]
    cells = (calibration.get("cells") or {}).values()
    order = {h: i for i, h in enumerate(HORIZONS)}
    for e in sorted(cells, key=lambda e: (str(e["ticker"]),
                                          order.get(e["horizon"], 99))):
        fmt = lambda v: "—" if v is None else "%.3f" % v
        basis = e["basis"] if e["calibrated"] else "uncalibrated"
        lines.append(
            "| %s | %s | %d | %d | %s | %s | %.3f | %+.2f | %s |" % (
                e["ticker"], e["horizon"], e["n"],
                e.get("n_eff", effective_n(e.get("n", 0), e.get("horizon"))),
                fmt(e["coverage_before"]), fmt(e["coverage_calibrated"]),
                e["k"], e["b"], basis))
    return lines


def load_calibration(ledger_path, formula=None):
    """Read a ledger.json and fit the calibration. Returns an
    empty calibration ({cells: {}, pools: {}}) on any problem —
    callers must never fail because calibration is unavailable."""
    try:
        with open(ledger_path, encoding="utf-8") as f:
            doc = json.load(f)
        return compute_calibration(doc.get("forecasts_detail") or [],
                                   formula=formula)
    except Exception:
        return {"formula": formula, "window": WINDOW,
                "target": TARGET_COVERAGE, "cells": {}, "pools": {}}


def default_ledger_path(root=None):
    if root is None:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(root, "ledger", "ledger.json")


if __name__ == "__main__":  # pragma: no cover - manual inspection
    cal = load_calibration(default_ledger_path())
    print("\n".join(calibration_table(cal)))
