#!/usr/bin/env python3
"""Context-neutralisation subset analysis (for #592).

Reads the published scorer-v2 re-score data (backtest/backtest.json and
backtest/cells/cellNN_score_v2.json, merged in PR #687) and reproduces the
context-neutralisation subset computation from issue #592:

  z = (cutoff close - mean of last 512 closes incl. cutoff session)
      / population std of those 512 closes

Subset = cells with |z| <= 1. Prints (and writes, next to this script,
subset592_context_neutralisation.md) the per-cell z table and the
subset-vs-full-set month-horizon numbers: Kronos month MAE, zero-baseline
month MAE, ensemble month MAE / hit / RangeSkill.

Price data is not published in the repo (the harness price.csv files live on
the worker cycle-state, not in git), so daily closes are fetched from the
Yahoo chart API, the same source the triage comment on #592 used for the 23
cells without a harness price.csv (the two sources agreed exactly on all 13
overlap cells there). Each fetched cutoff close is checked against the
cell's recorded base_price; any mismatch above tolerance is reported.

Stdlib only. Usage: python3 benchmarks/subset592_context_neutralisation.py
"""

import datetime as dt
import glob
import json
import math
import os
import sys
import urllib.request
import zoneinfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CELLS_GLOB = os.path.join(ROOT, "backtest", "cells", "cell*_score_v2.json")
OUT_MD = os.path.join(ROOT, "benchmarks", "subset592_context_neutralisation.md")
CONTEXT = 512
Z_MAX = 1.0
BASE_PRICE_TOL_PCT = 0.5  # max allowed |yahoo close - base_price| / base_price


def load_cells():
    cells = []
    for path in glob.glob(CELLS_GLOB):
        n = int(os.path.basename(path).split("cell")[1].split("_")[0])
        with open(path) as f:
            cells.append((n, json.load(f)))
    return sorted(cells)


def month_rows(cell):
    """Per-entrant month-horizon forecast rows for one cell."""
    out = {}
    for row in cell["forecasts_detail"]:
        if row["horizon"] == "month":
            out[row["entrant"]] = row
    return out


def fetch_closes(ticker, start, end):
    """Daily closes for ticker between start and end (dates), Yahoo chart API."""
    p1 = int(dt.datetime(start.year, start.month, start.day,
                         tzinfo=dt.timezone.utc).timestamp())
    p2 = int(dt.datetime(end.year, end.month, end.day,
                         tzinfo=dt.timezone.utc).timestamp())
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/"
           f"{ticker}?period1={p1}&period2={p2}&interval=1d")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.load(resp)["chart"]["result"][0]
    tz = zoneinfo.ZoneInfo(result["meta"].get("exchangeTimezoneName", "UTC"))
    ts = result["timestamp"]
    closes = result["indicators"]["quote"][0]["close"]
    series = [(dt.datetime.fromtimestamp(t, tz).date(), c)
              for t, c in zip(ts, closes) if c is not None]
    series.sort()
    return series


def z_score(series, as_of):
    """z of the close at as_of vs the trailing 512 closes incl. that session.

    Returns (z, session_date, close, window_n). Window requires >= 2 closes.
    """
    upto = [(d, c) for d, c in series if d <= as_of]
    if not upto:
        raise ValueError(f"no sessions on or before {as_of}")
    session, close = upto[-1]
    window = [c for _, c in upto[-CONTEXT:]]
    mean = sum(window) / len(window)
    var = sum((c - mean) ** 2 for c in window) / len(window)  # population std
    std = math.sqrt(var)
    z = (close - mean) / std if std > 0 else float("nan")
    return z, session, close, len(window)


def mean(xs):
    return sum(xs) / len(xs) if xs else float("nan")


def pearson(xs, ys):
    mx, my = mean(xs), mean(ys)
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    return cov / math.sqrt(vx * vy) if vx > 0 and vy > 0 else float("nan")


def group_stats(records):
    """Month-horizon stats for a group of per-cell records."""
    n = len(records)
    k_err = [r["kronos"]["move_error_pp"] for r in records]
    k_hit = [1 if r["kronos"]["direction_hit"] else 0 for r in records]
    e_err = [r["ensemble"]["move_error_pp"] for r in records]
    e_hit = [1 if r["ensemble"]["direction_hit"] else 0 for r in records]
    e_is = [r["ensemble_is"] for r in records]
    n_is = [r["naive_is"] for r in records]
    zero_err = [abs(r["kronos"]["realized_move_pct"]) for r in records]
    rs = 1 - mean(e_is) / mean(n_is) if n_is and mean(n_is) != 0 else float("nan")
    return {
        "n": n,
        "kronos_mae": mean(k_err),
        "kronos_hit": mean(k_hit),
        "ensemble_mae": mean(e_err),
        "ensemble_hit": mean(e_hit),
        "ensemble_range_skill": rs,
        "zero_mae": mean(zero_err),
    }


def fmt_row(label, s):
    return (f"| {label} | {s['n']} | {s['kronos_mae']:.2f} | {s['kronos_hit']:.3f} "
            f"| {s['ensemble_mae']:.2f} | {s['ensemble_hit']:.3f} "
            f"| {s['ensemble_range_skill']:.3f} | {s['zero_mae']:.2f} |")


def main():
    cells = load_cells()
    if not cells:
        sys.exit("no cell files found under backtest/cells/")

    # Per-cell facts from the published re-score data.
    records = []
    for n, cell in cells:
        rows = month_rows(cell)
        kronos = rows.get("kronos-alone")
        ensemble = rows.get("2-family-ensemble")
        if not kronos or not ensemble:
            print(f"cell{n}: missing kronos/ensemble month row, skipped")
            continue
        e_month = cell["by_entrant"]["2-family-ensemble"]["month"]
        records.append({
            "cell": n,
            "ticker": kronos["ticker"],
            "as_of": dt.date.fromisoformat(kronos["as_of"]),
            "base_price": kronos["base_price"],
            "kronos": kronos,
            "ensemble": ensemble,
            "ensemble_is": e_month["mean_interval_score"],
            "naive_is": e_month["naive_interval_score"],
        })

    # Price series per ticker, covering the oldest context window.
    start = min(r["as_of"] for r in records) - dt.timedelta(days=CONTEXT * 2 + 200)
    end = max(r["as_of"] for r in records) + dt.timedelta(days=3)
    series = {}
    for ticker in sorted({r["ticker"] for r in records}):
        series[ticker] = fetch_closes(ticker, start, end)

    # z per cell, with base_price cross-check.
    checks = []
    for r in records:
        z, session, close, wn = z_score(series[r["ticker"]], r["as_of"])
        r["z"] = z
        r["z_session"] = session.isoformat()
        r["z_window_n"] = wn
        dev = abs(close - r["base_price"]) / r["base_price"] * 100
        checks.append((dev, r["cell"]))
        if dev > BASE_PRICE_TOL_PCT:
            print(f"WARNING cell{r['cell']}: yahoo close {close} vs base_price "
                  f"{r['base_price']} ({dev:.2f}% off)")
    worst = max(checks)
    print(f"base_price cross-check: max deviation {worst[0]:.3f}% (cell{worst[1]}), "
          f"tolerance {BASE_PRICE_TOL_PCT}%")

    subset = [r for r in records if abs(r["z"]) <= Z_MAX]
    complement = [r for r in records if abs(r["z"]) > Z_MAX]

    # Correlations over the full set.
    zs = [r["z"] for r in records]
    k_exp = [r["kronos"]["expected_move_pct"] for r in records]
    k_signed = [r["kronos"]["expected_move_pct"] - r["kronos"]["realized_move_pct"]
                for r in records]
    k_abs = [r["kronos"]["move_error_pp"] for r in records]
    corrs = {
        "z_vs_kronos_expected": pearson(zs, k_exp),
        "z_vs_signed_error": pearson(zs, k_signed),
        "z_vs_abs_error": pearson(zs, k_abs),
    }

    # Sign-flip tell inside the neutral subset.
    sub_exp = mean([r["kronos"]["expected_move_pct"] for r in subset])
    sub_real = mean([r["kronos"]["realized_move_pct"] for r in subset])
    sub_up = sum(1 for r in subset if r["kronos"]["expected_move_pct"] > 0)

    lines = []
    lines.append("# Context-neutralisation subset (|z| <= 1) — reproducible numbers (for #592)\n")
    lines.append(f"Generated by `benchmarks/subset592_context_neutralisation.py` on "
                 f"{dt.date.today().isoformat()} from `backtest/` (scorer v2, PR #687) "
                 f"plus Yahoo chart API daily closes for the z computation.\n")
    lines.append(f"z = (cutoff close − mean of last {CONTEXT} closes incl. cutoff session) "
                 f"/ population std. Subset = |z| ≤ {Z_MAX}. "
                 f"base_price cross-check max deviation {worst[0]:.3f}%.\n")
    lines.append(f"\n## Subset membership: {len(subset)} of {len(records)} cells\n")
    lines.append("| cell | ticker | as_of | z | in subset |")
    lines.append("|---|---|---|---|---|")
    for r in records:
        lines.append(f"| {r['cell']} | {r['ticker']} | {r['as_of']} | {r['z']:+.3f} "
                     f"| {'yes' if abs(r['z']) <= Z_MAX else 'no'} |")
    lines.append("\n## Month-horizon numbers, subset vs full set\n")
    lines.append("| group | n | Kronos MAE | Kronos hit | ensemble MAE | ensemble hit "
                 "| ensemble RangeSkill | zero-move MAE |")
    lines.append("|---|---|---|---|---|---|---|---|")
    lines.append(fmt_row(f"|z| ≤ {Z_MAX}", group_stats(subset)))
    lines.append(fmt_row(f"|z| > {Z_MAX}", group_stats(complement)))
    lines.append(fmt_row("full set", group_stats(records)))
    lines.append("\nRangeSkill = 1 − mean Winkler IS (α=0.2) / mean naive IS, "
                 "per the scorer's own definition (cell-level month interval scores).")
    lines.append("\n## Correlations over the full set\n")
    lines.append(f"- corr(z, Kronos month expected move) = {corrs['z_vs_kronos_expected']:.3f}")
    lines.append(f"- corr(z, Kronos signed error, expected − realised) = {corrs['z_vs_signed_error']:.3f}")
    lines.append(f"- corr(z, Kronos |error|) = {corrs['z_vs_abs_error']:.3f}")
    lines.append("\n## Sign check inside the neutral subset\n")
    lines.append(f"- mean Kronos month expected move: {sub_exp:+.2f}% "
                 f"({sub_up} of {len(subset)} cells forecast up)")
    lines.append(f"- mean realised month move: {sub_real:+.2f}%")
    comp_exp = mean([r["kronos"]["expected_move_pct"] for r in complement])
    lines.append(f"- complement (|z| > {Z_MAX}) mean Kronos month expected move: {comp_exp:+.2f}%")
    out = "\n".join(lines) + "\n"
    with open(OUT_MD, "w") as f:
        f.write(out)
    print(out)
    print(f"wrote {os.path.relpath(OUT_MD, ROOT)}")


if __name__ == "__main__":
    main()
