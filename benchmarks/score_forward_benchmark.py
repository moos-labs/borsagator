#!/usr/bin/env python3
"""Forward quality benchmark over the calibration ledger (issue #79).

Scores every matured forecast row in ledger/ledger.json against
baselines reconstructed point-in-time from the sweep archive:

  ensemble        the ledger row itself (direction_hit / move_error_pp
                  as published by ledger.py's score_forecast)
  naive-flat      predicted move 0.00% ("the price will not move")
  momentum        prior-period move continued: the realised move over
                  the s sessions ending at as_of (s = the row's own
                  horizon length in sessions) is the prediction for
                  the next s sessions
  family-<name>   each voting family standalone, definition (a) from
                  the #79 section-13 decisions: the benchmark_freeze
                  combine re-run with that family's weight 1 and all
                  others 0, kmove zeroed for non-price families and
                  recomputed from the Kronos CSV for price-forecast
                  (kronos_at row-index mirror). Inputs are the sweep's
                  archived ensemble.json (family scores, sigma_daily)
                  and collected/kronos/forecast.csv.

Scoring is ledger.py's, identical for every entrant: direction with
the +/-0.75% flat band, move error in percentage points, against the
row's (dividend-adjusted where applicable) realised move.

Headline aggregates EXCLUDE gap-flagged matured rows (dividend_gap
set), per decision D-79-1: flagged rows stay listed and counted
(excluded_flagged) but never enter skill/aggregate numbers. The
all-matured aggregates are printed in an appendix for completeness.

Usage:
  score_forward_benchmark.py --ledger ledger/ledger.json \
      --archive <archive-branch checkout> --scripts scripts \
      --benchmark-json ledger/benchmark.json \
      --out-md benchmarks/forward-quality-benchmark.md \
      --out-json /tmp/forward-benchmark-rows.json
"""

import argparse
import json
import math
import os
import sys
from collections import defaultdict

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ledger_freshness as LF  # noqa: E402

FAMILIES = ("price-forecast", "technicals", "sentiment", "agent",
            "fundamentals")

# Price-series files (archive branch) used for the momentum baseline,
# per ticker, merged in order (later files overwrite the same date).
# These are the very files ledger.json's `series` metadata lists as
# the accumulated sources for each ticker.
SERIES_FILES = {
    "POUL.CA": [
        "sweeps/2026-11-12/163459__backfill-issue-14__sweep-lite-poul-ca"
        "-market-egx/collected/egx-data/egxpy_poul.csv",
        "sweeps/2026-11-24/062345__sweep-lite-poul-ca-market-egx"
        "__runsched-2026-11-24/collected/egx-data/egxpy_poul.csv",
    ],
    "NVDA": [
        "sweeps/2026-11-16/041242__run-yahooquery-nvda__run43802588955"
        "/collected/yahooquery/NVDA.csv",
        "sweeps/2026-11-16/041633__run-openbb-nvda__run43802957047"
        "/collected/openbb/NVDA.csv",
    ],
}


def build_series(archive, ledger_mod):
    series = {}
    for ticker, rels in SERIES_FILES.items():
        merged = {}
        for rel in rels:
            path = os.path.join(archive, rel)
            with open(path, encoding="utf-8") as f:
                parsed, symbols = ledger_mod.parse_price_csv(f.read())
            if parsed is None:
                raise SystemExit(f"series file unparseable: {rel}")
            if symbols and ticker not in symbols:
                raise SystemExit(f"series file names other symbols: {rel}")
            merged.update(parsed)
        series[ticker] = merged
    return series


def load_sweep_json(archive, sweep, name):
    path = os.path.join(archive, sweep, name)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class FamilyScorer:
    """Reconstruct family-alone forecasts (definition (a)) for one
    sweep from its archived ensemble.json + Kronos CSV."""

    def __init__(self, archive, sweep, bf, ens_mod):
        self.bf = bf
        self.ens = load_sweep_json(archive, sweep, "ensemble.json")
        self.digest = load_sweep_json(archive, sweep, "digest.json")
        self.sweep = sweep
        self.sigma = None
        self.sigma_note = None
        if self.ens is not None:
            sig = bf.fnum(self.ens.get("sigma_daily"))
            if sig:
                self.sigma = sig
                self.sigma_note = "recorded"
            else:
                self.sigma = self._recompute_sigma(archive, ens_mod)
                self.sigma_note = ("recomputed via ensemble.realized_sigma"
                                   if self.sigma else "unavailable")
            # Kronos path (price-forecast kmove), rescaled as recorded.
            bf.KRONOS_CSV = os.path.join(
                archive, sweep, "collected", "kronos", "forecast.csv")
            path, _first, _note = bf.read_kronos_csv(self.digest)
            if path:
                path, _rec = bf.rescale_kronos(path, self.ens)
            self.kronos_path = path
        else:
            self.kronos_path = None

    def _recompute_sigma(self, archive, ens_mod):
        """Two pre-recording sweeps (2026-11-12 backfills) carry no
        sigma_daily in ensemble.json. Recompute it with the combine's
        own function over the sweep's collected pool, exactly as
        ensemble.py did at freeze time."""
        try:
            ens_mod.COLLECTED = os.path.join(archive, self.sweep,
                                             "collected")
            okmap = {}
            for r in (self.digest or {}).get("results", []):
                if isinstance(r, dict) and r.get("tool"):
                    okmap[r["tool"]] = r.get("status") == "ok"
            ok = (lambda name: okmap.get(name, False)) if okmap else None
            # ensemble.realized_sigma returns 4 values (sigma,
            # sigma60, source, density) since the v2 band (#594);
            # the old 3-value unpack raised ValueError here and the
            # except below silently dropped sigma to None.
            sigma, _sigma60, _src, _density = ens_mod.realized_sigma(
                self.ens.get("ticker"), base=self.ens.get("base_price"),
                ok=ok)
            return sigma or None
        except Exception:
            return None

    def family_expected(self, fam, horizon):
        """Expected move (fraction) for family `fam` alone at
        `horizon`, or None when the family did not vote / its inputs
        are absent. Mirrors benchmark_freeze.freeze_family_alone."""
        bf = self.bf
        if self.ens is None or self.sigma is None:
            return None
        ens_h = ((self.ens.get("horizons") or {}).get(horizon))
        if not isinstance(ens_h, dict):
            return None
        if fam == "price-forecast":
            score = bf.fnum((ens_h.get("families") or {})
                            .get("price-forecast"))
        else:
            score = bf.fnum((self.ens.get("family_scores") or {})
                            .get(fam))
        if score is None:
            return None
        bar = bf.HORIZONS[horizon]
        density = bf.fnum(self.ens.get("sessions_per_calendar_day")) \
            or (5 / 7)
        h_eff = ens_h.get("trading_sessions")
        if not isinstance(h_eff, int) or h_eff <= 0:
            h_eff = max(1, round(bar * density))
        vol_h = self.sigma * math.sqrt(h_eff)
        kmove = 0.0
        if fam == "price-forecast":
            ka = bf.kronos_at(self.kronos_path,
                              self.ens.get("base_price"), bar)
            if ka is None:
                return None
            kmove = ka["move"]
        return 0.6 * kmove + 0.4 * score * (1.28 * vol_h)


def momentum_prediction(row, series, ledger_mod):
    """Prior-period move continued. Returns (pred_pct, gap_reason,
    level_divergence). The anchor is the last series close on or
    before as_of — a sweep can run on a non-trading day (e.g. Friday
    2026-11-13) with the previous session's close as its base. The
    prediction is a return computed entirely inside one series, so a
    base_price recorded from a different (e.g. cum-dividend) source
    does not invalidate it; that level divergence is reported, and
    the binding validation is the maturity close, which the ledger
    itself took from this accumulated series."""
    ser = series.get(row["ticker"])
    if not ser:
        return None, "no price series for ticker", False
    dates = sorted(ser)
    upto = [d for d in dates if d <= row["as_of"]]
    if not upto:
        return None, "no series close on or before as_of", False
    anchor = upto[-1]
    mat = row.get("maturity_date")
    if mat not in ser:
        return None, "maturity close not in series", False
    if ledger_mod.rel_close(ser[mat], row["close_at_maturity"]) \
            > ledger_mod.VALID_TOL:
        return None, "series close at maturity does not match ledger", \
            False
    divergence = ledger_mod.rel_close(ser[anchor], row["base_price"]) \
        > ledger_mod.VALID_TOL
    i = dates.index(anchor)
    s = row["sessions"]
    if i - s < 0:
        return None, "insufficient prior sessions in series", False
    prior = ser[dates[i - s]]
    pred = (ser[anchor] / prior - 1.0) * 100.0
    return pred, None, divergence


def score_rows(ledger, series, archive, mods):
    L, BF, ENS = mods
    scorers = {}
    out = []
    for row in ledger["forecasts_detail"]:
        if row["status"] != "matured":
            continue
        realized = row["realized_move_pct"]
        # The ledger's recorded direction is authoritative (it was
        # computed from the unrounded realised move; the stored
        # move is rounded to 2 dp, which can flip the band edge).
        rdir = row["realized_direction"]
        rec = {"ticker": row["ticker"], "as_of": row["as_of"],
               "sweep": row["sweep"], "horizon": row["horizon"],
               "realized_move_pct": realized,
               "realized_direction": rdir,
               "gap_flagged": bool(row.get("dividend_gap")),
               "entrants": {}}
        rec["entrants"]["ensemble"] = {
            "direction": row["direction"],
            "expected_move_pct": row["expected_move_pct"],
            "hit": bool(row["direction_hit"]),
            "error_pp": row["move_error_pp"]}
        rec["entrants"]["naive-flat"] = {
            "direction": "flat", "expected_move_pct": 0.0,
            "hit": rdir == "flat", "error_pp": abs(realized)}
        pred, gap, divergence = momentum_prediction(row, series, L)
        if pred is None:
            rec["momentum_gap"] = gap
        else:
            if divergence:
                rec["momentum_level_divergence"] = True
            d = BF.direction_of(pred / 100.0)
            rec["entrants"]["momentum"] = {
                "direction": d, "expected_move_pct": round(pred, 2),
                "hit": d == rdir,
                "error_pp": round(abs(pred - realized), 2)}
        sweep = row["sweep"]
        if sweep not in scorers:
            scorers[sweep] = FamilyScorer(archive, sweep, BF, ENS)
        fs = scorers[sweep]
        rec["sigma_note"] = fs.sigma_note
        for fam in FAMILIES:
            exp = fs.family_expected(fam, row["horizon"])
            if exp is None:
                continue
            d = BF.direction_of(exp)
            rec["entrants"][f"family-{fam}"] = {
                "direction": d,
                "expected_move_pct": round(exp * 100, 2),
                "hit": d == rdir,
                "error_pp": round(abs(exp * 100 - realized), 2)}
        out.append(rec)
    return out


def aggregate(records, entrants):
    """{(horizon, entrant): (n, hits, mae)}"""
    agg = {}
    for horizon in ("day", "week", "month"):
        for entrant in entrants:
            sel = [r["entrants"][entrant] for r in records
                   if r["horizon"] == horizon
                   and entrant in r["entrants"]]
            if not sel:
                agg[(horizon, entrant)] = (0, 0, None)
            else:
                mae = sum(e["error_pp"] for e in sel) / len(sel)
                agg[(horizon, entrant)] = (
                    len(sel), sum(1 for e in sel if e["hit"]), mae)
    return agg


def fmt_table(agg, entrants, horizon):
    lines = [f"## {horizon}", "",
             "| Entrant | n | Direction hit rate | Mean abs. error (pp) |",
             "|---|---|---|---|"]
    for entrant in entrants:
        n, hits, mae = agg[(horizon, entrant)]
        if n == 0:
            lines.append(f"| {entrant} | 0 | — | — |")
        else:
            gate = " †" if n < 10 else ""
            lines.append(
                f"| {entrant} | {n}{gate} | {hits / n:.3f} | "
                f"{mae:.2f} |")
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--archive", required=True)
    ap.add_argument("--scripts", required=True)
    ap.add_argument("--benchmark-json")
    ap.add_argument("--out-md", required=True)
    ap.add_argument("--out-json")
    LF.add_args(ap)
    args = ap.parse_args()

    sys.path.insert(0, args.scripts)
    import benchmark_freeze as BF
    import ensemble as ENS
    import ledger as L

    with open(args.ledger, encoding="utf-8") as f:
        ledger = json.load(f)
    _, refused = LF.gate(ledger["forecasts_detail"], args)
    if refused:
        return refused
    series = build_series(args.archive, L)
    records = score_rows(ledger, series, args.archive, (L, BF, ENS))

    entrants = (["ensemble", "naive-flat", "momentum"]
                + [f"family-{f}" for f in FAMILIES])
    headline = [r for r in records if not r["gap_flagged"]]
    agg_head = aggregate(headline, entrants)
    agg_all = aggregate(records, entrants)

    # Cross-checks -------------------------------------------------
    checks = []
    bh = ledger["by_horizon"]
    for horizon in ("day", "week"):
        n, hits, mae = agg_head[(horizon, "ensemble")]
        ok = (n == bh[horizon]["n"]
              and abs(hits / n - bh[horizon]["hit_rate"]) < 1e-9
              and abs(mae - bh[horizon]["mean_abs_error_pp"]) < 0.005)
        checks.append(f"ensemble {horizon} reproduces ledger.json "
                      f"by_horizon: {'PASS' if ok else 'FAIL'} "
                      f"(n={n}, hit={hits / n:.3f}, MAE={mae:.2f})")
    frozen_cmp = None
    if args.benchmark_json:
        with open(args.benchmark_json, encoding="utf-8") as f:
            bench = json.load(f)
        frozen = {(r["sweep"], r["horizon"], r["entrant"]): r
                  for r in bench["rows"] if r["status"] == "matured"
                  and r["entrant"].startswith("family-")}
        mine = {}
        for r in records:
            for e, v in r["entrants"].items():
                if e.startswith("family-"):
                    mine[(r["sweep"], r["horizon"], e)] = v
        both = set(frozen) & set(mine)
        agree = sum(1 for k in both
                    if frozen[k]["direction_hit"] == mine[k]["hit"]
                    and abs(frozen[k]["move_error_pp"]
                            - mine[k]["error_pp"]) < 0.011)
        frozen_cmp = (len(both), agree)
        checks.append(
            f"family-alone reconstruction vs the frozen benchmark "
            f"(ledger/benchmark.json): {agree}/{len(both)} overlapping "
            f"rows agree on hit and |error| (<=0.01 pp)")

    if args.out_json:
        with open(args.out_json, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=1)

    # Markdown ------------------------------------------------------
    n_mat = len(records)
    n_flag = sum(1 for r in records if r["gap_flagged"])
    mom_gaps = [r for r in records if "momentum_gap" in r]
    recomputed = sorted({r["sweep"] for r in records
                         if r["sigma_note"]
                         and r["sigma_note"].startswith("recomputed")})
    md = []
    md.append("# Forward quality benchmark — ensemble vs baselines "
              "(issue #79)")
    md.append("")
    md.append(
        "Computed from `ledger/ledger.json` (every matured forecast "
        f"row: {n_mat}) and the point-in-time sweep archive. Generator: "
        "`benchmarks/score_forward_benchmark.py`; scoring is "
        "ledger.py's own machinery (direction with the ±0.75% flat "
        "band, move error in percentage points, realised moves "
        "dividend-adjusted where the ledger adjusted them).")
    md.append("")
    md.append(
        f"Headline tables EXCLUDE the {n_flag} gap-flagged matured "
        "rows (decision D-79-1: flagged rows stay listed and counted, "
        "never in aggregates). All-matured tables are in the appendix. "
        "Quality gate: no quality claim for any (entrant, horizon) "
        "cell with n < 10 matured forecasts; public accuracy claims "
        "need n ≥ 30 (D4). Cells below the gate print their numbers "
        "for the record, marked †.")
    md.append("")
    md.append("Entrants: **ensemble** (the ledger row as published); "
              "**naive-flat** (predicted move 0.00%); **momentum** "
              "(the realised move over the s sessions ending at as_of, "
              "continued for the next s sessions); **family-\\*** (each "
              "voting family standalone, definition (a): combine re-run "
              "with that family's weight 1, kmove zeroed for non-price "
              "families, Kronos kmove for price-forecast).")
    md.append("")
    md.append("# Headline (gap-flagged rows excluded)")
    md.append("")
    for horizon in ("day", "week", "month"):
        md += fmt_table(agg_head, entrants, horizon)
        md.append("")
    md.append("## Reading (gated cells only, n ≥ 10)")
    md.append("")
    for horizon in ("day", "week"):
        gated = [(e, agg_head[(horizon, e)]) for e in entrants
                 if agg_head[(horizon, e)][0] >= 10]
        ens_n, ens_hits, ens_mae = agg_head[(horizon, "ensemble")]
        best_mae = min(gated, key=lambda kv: kv[1][2])
        best_hit = max(gated, key=lambda kv: kv[1][1] / kv[1][0])
        rank = sorted(gated, key=lambda kv: kv[1][2]).index(
            ("ensemble", agg_head[(horizon, "ensemble")])) + 1
        verdict = ""
        flat = agg_head[(horizon, "naive-flat")]
        mom = agg_head[(horizon, "momentum")]
        if (ens_mae >= flat[2] and ens_mae >= mom[2]
                and ens_hits / ens_n <= flat[1] / flat[0]
                and ens_hits / ens_n <= mom[1] / mom[0]):
            verdict = (" The ensemble does not beat the naive "
                       "baselines on this horizon — on either metric.")
        md.append(
            f"- **{horizon}**: the ensemble (hit "
            f"{ens_hits / ens_n:.3f}, MAE {ens_mae:.2f} pp) ranks "
            f"{rank} of {len(gated)} gated entrants on MAE. Best MAE: "
            f"{best_mae[0]} ({best_mae[1][2]:.2f} pp). Best hit rate: "
            f"{best_hit[0]} ({best_hit[1][1] / best_hit[1][0]:.3f})."
            f"{verdict}")
    md.append("- The sample is one ticker (POUL.CA, 44 of 45 matured "
              "rows) plus one NVDA row, all from 2026-11-12 to "
              "2026-11-19 — a window dominated by POUL's 1.90 EGP "
              "ex-dividend drop. These are the ledger's real numbers, "
              "published as scored; they are not yet evidence about "
              "any other ticker or regime.")
    md.append("")
    md.append("# Appendix — all matured rows (gap-flagged included)")
    md.append("")
    for horizon in ("day", "week", "month"):
        md += fmt_table(agg_all, entrants, horizon)
        md.append("")
    md.append("## Gaps & notes")
    md.append("")
    md.append(f"- Matured rows scored: {n_mat}; gap-flagged and "
              f"excluded from the headline: {n_flag}; headline rows: "
              f"{len(headline)}.")
    md.append("- Month horizon: no matured forecasts yet (n=0 for "
              "every entrant) — nothing to score, nothing claimed.")
    if mom_gaps:
        md.append(f"- Momentum unavailable on {len(mom_gaps)} row(s): "
                  + "; ".join(
                      f"{r['ticker']} {r['as_of']} {r['horizon']} "
                      f"({r['momentum_gap']})" for r in mom_gaps))
    else:
        md.append("- Momentum: computable on every matured row. The "
                  "anchor is the last series close on or before as_of "
                  "(three sweeps ran on Friday 2026-11-13, a "
                  "non-trading day, on the 2026-11-12 close). The "
                  "series close at each row's maturity reproduces the "
                  "ledger's close_at_maturity within the 3% "
                  "validation tolerance on all rows.")
    n_div = sum(1 for r in records
                if r.get("momentum_level_divergence"))
    if n_div:
        md.append(
            f"- On {n_div} row(s) the series close at the anchor "
            "differs from the sweep's recorded base_price by more "
            "than 3% — the 2026-11-16 ex-date rows, whose base was "
            "recorded cum-dividend while the exchange series is "
            "ex-dividend. Momentum is a return computed inside one "
            "series, so it is still scored; its prior window spans "
            "the mechanical ex-date drop, which is exactly what a "
            "naive momentum baseline would have predicted from raw "
            "closes.")
    if recomputed:
        md.append(
            "- sigma_daily is not recorded in the archived "
            "ensemble.json of "
            + ", ".join(f"`{s}`" for s in recomputed)
            + "; for those sweeps sigma was recomputed with the "
            "combine's own ensemble.realized_sigma over the sweep's "
            "collected pool (the same function ensemble.py calls at "
            "freeze time). Family-alone rows from all other sweeps "
            "use the recorded sigma_daily.")
    md.append("- Family-alone n counts only rows where the family "
              "actually voted (score present in the sweep's "
              "ensemble.json); agent and fundamentals vote rarely, so "
              "their n is small and gated.")
    md.append("")
    md.append("## Cross-checks")
    md.append("")
    for c in checks:
        md.append(f"- {c}")
    md.append("")
    with open(args.out_md, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    print("\n".join(checks))
    print(f"rows={n_mat} flagged={n_flag} headline={len(headline)}")
    for horizon in ("day", "week", "month"):
        for e in entrants:
            n, hits, mae = agg_head[(horizon, e)]
            print(f"HEAD {horizon:5s} {e:22s} n={n:3d} "
                  f"hit={hits / n if n else float('nan'):.3f} "
                  f"mae={mae if mae is not None else float('nan'):.2f}")


if __name__ == "__main__":
    sys.exit(main())
