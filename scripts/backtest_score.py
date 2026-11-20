#!/usr/bin/env python3
"""Thin scorer for the #436 walk-forward backtest (design §6.2).

Reads staged captures (backtest/<cutoff>/<ticker>/, written by
scripts/backtest.py) and scores them with the ledger's own rule —
ledger.score_forecast() imported verbatim — so backtest numbers
are comparable in DEFINITION to the forward ledger while living in
a separate publication (backtest/backtest.json + backtest.md,
tool "walkforward-backtest"). The scorer NEVER reads the archive
branch, NEVER reads ledger/, and NEVER writes to ledger/:
the two series are never mixed (design §0).

Entrants (design §5.1 + §2.2), built from each capture's
ensemble.json + Kronos path with the benchmark_freeze.py
formulas (family-alone, kronos-alone, buy-and-hold — mirrored,
cross-checked by tests/test_backtest_436.py against the freeze
itself):
  2-family-ensemble, kronos-alone, family-technicals,
  buy-and-hold, index-baseline (flat 0% scored on the index's
  realised closes — EGX30 for EGX tickers, S&P 500 for US — a
  market-difficulty reference; benchmark_freeze.py does NOT freeze
  an index baseline, so the scorer builds this reference directly
  from the capture's index closes).

Scoring is by the ledger's session counts (day 1 / week 5 /
month 14, ledger.DEFAULT_SESSIONS), not the ensemble's Kronos
bars; the forecast's own session count is recorded per row as
sessions_forecast (design §1.1).

Stdlib only (plus the repo's own ledger/benchmark_freeze
modules). No network.
"""
import argparse
import csv
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import ledger  # noqa: E402
import benchmark_freeze as bf  # noqa: E402
import ensemble as ens_mod  # noqa: E402

TOOL = "walkforward-backtest"
VERSION = 1
ENTRANTS = ("2-family-ensemble", "kronos-alone", "family-technicals",
            "buy-and-hold", "index-baseline")

FLATTERY_WARNING = (
    "Kronos-small (NeoQuasar/Kronos-small) is a pretrained model "
    "whose training data is historical market data. Backtest scores "
    "are therefore an UPPER BOUND on live skill, not an estimate of "
    "it. The forward ledger (issue #79) remains the only basis for "
    "accuracy claims (decision D4 unchanged).")
EXCLUSION_STATEMENT = (
    "Out of scope for this backtest (design §5.2): sentiment/news "
    "(no complete historical headline archive exists), agent/LLM "
    "(training knowledge leaks the future), fundamentals (no "
    "verified point-in-time statement vintages), and validation / "
    "backtest-category tools (qlib, vectorbt, backtrader) which are "
    "not direction voters. Only price-forecast (Kronos) and "
    "technicals (pandas-ta voter + talib cross-check) are scored, "
    "separately and as a 2-family ensemble.")


def fnum(v):
    try:
        x = float(v)
    except Exception:
        return None
    return x if math.isfinite(x) else None


def load_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def read_kronos_path(path):
    """Kronos forecast path from an explicit CSV path — the same
    DictReader logic as benchmark_freeze.read_kronos_csv, but the
    freeze reads the module-level KRONOS_CSV (cwd-bound); the
    scorer reads the capture's file. Returns (path_list,
    first_row_date) or (None, None)."""
    if not os.path.exists(path):
        return None, None
    try:
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    except Exception:
        return None, None
    out, first_date = [], None
    for row in rows:
        c = fnum(row.get("close"))
        if not c:
            continue
        if first_date is None:
            raw = str(row.get("date") or "")[:10]
            import re
            first_date = raw if re.match(r"^\d{4}-\d{2}-\d{2}$", raw) \
                else None
        h, l = fnum(row.get("high")), fnum(row.get("low"))
        out.append((c, h or c, l or c))
    return (out, first_date) if out else (None, None)


def _horizon_block(direction, expected_pct, low_pct, high_pct,
                   confidence, net_score, families, ens_h,
                   sessions_forecast):
    block = {"direction": direction,
             "expected_move_pct": round(expected_pct, 2)
             if expected_pct is not None else None,
             "range_low_pct": round(low_pct, 2)
             if low_pct is not None else None,
             "range_high_pct": round(high_pct, 2)
             if high_pct is not None else None,
             "confidence": confidence, "net_score": net_score,
             "families": families,
             "trading_sessions": (ens_h or {}).get("trading_sessions"),
             "sessions_forecast": sessions_forecast,
             "horizon_short": bool((ens_h or {}).get("horizon_short"))}
    if isinstance((ens_h or {}).get("corporate_action"), dict):
        block["corporate_action"] = (ens_h or {}).get("corporate_action")
    return block


def build_entrants(ens, kronos_path, kronos_first_date):
    """Entrant horizon blocks for one capture. Formulas mirror
    benchmark_freeze.freeze_family_alone / freeze_kronos_alone /
    freeze_buy_and_hold exactly (same combine, same risk mult,
    same conf formula); the ensemble entrant is the ensemble's
    own horizons verbatim. Returns {entrant: {horizon: block}}."""
    base = fnum(ens.get("base_price"))
    sigma = fnum(ens.get("sigma_daily")) or 0.0
    density = fnum(ens.get("sessions_per_calendar_day")) or (5 / 7)
    risk = ens.get("risk") or {}
    conf_cap = risk.get("conf_cap")
    if conf_cap is None:
        conf_cap = 0.6
    risk_mult = bf.RISK_MULT.get(risk.get("level"), 1.0)
    kronos, kronos_rescale = bf.rescale_kronos(kronos_path, ens)
    scores = ens.get("family_scores") or {}
    out = {}

    # 2-family ensemble: the ensemble's own horizons, verbatim.
    out["2-family-ensemble"] = {}
    for h in ledger.HORIZONS:
        hb = (ens.get("horizons") or {}).get(h)
        if not isinstance(hb, dict):
            continue
        out["2-family-ensemble"][h] = _horizon_block(
            hb.get("direction"), hb.get("expected_move_pct"),
            hb.get("range_low_pct"), hb.get("range_high_pct"),
            hb.get("confidence"), hb.get("net_score"),
            {k: fnum(v) for k, v in (hb.get("families") or {}).items()
             if fnum(v) is not None},
            hb, hb.get("trading_sessions"))

    # Kronos-alone: mirror freeze_kronos_alone — kronos_at row
    # rule, expected from the row close vs the base, range from
    # the row's own high/low.
    out["kronos-alone"] = {}
    if kronos and base:
        for h, bar in bf.HORIZONS.items():
            hb = (ens.get("horizons") or {}).get(h)
            if not isinstance(hb, dict):
                continue
            ka = bf.kronos_at(kronos, base, bar)
            if ka is None:
                continue
            h_eff = hb.get("trading_sessions")
            if not isinstance(h_eff, int) or h_eff <= 0:
                h_eff = max(1, round(bar * density))
            vol_h = sigma * math.sqrt(h_eff)
            price_score = (max(-1.0, min(1.0, ka["move"] / (2.0 * vol_h)))
                           if vol_h > 0 else 0.0)
            i = min(bar, len(kronos)) - 1
            _c, _h, _l = kronos[i]
            out["kronos-alone"][h] = _horizon_block(
                bf.direction_of(ka["move"]), ka["move"] * 100,
                (_l / base - 1) * 100, (_h / base - 1) * 100,
                None, round(price_score, 3),
                {"price-forecast": round(price_score, 3)},
                hb, hb.get("trading_sessions"))

    # Technicals-alone: mirror freeze_family_alone — the combine
    # re-run with the technicals weight 1, kmove zeroed, via the
    # extracted ensemble.expected_move() (design §5.3).
    out["family-technicals"] = {}
    tech = fnum(scores.get("technicals"))
    if tech is not None:
        for h, bar in bf.HORIZONS.items():
            hb = (ens.get("horizons") or {}).get(h)
            if not isinstance(hb, dict):
                continue
            h_eff = hb.get("trading_sessions")
            if not isinstance(h_eff, int) or h_eff <= 0:
                h_eff = max(1, round(bar * density))
            vol_h = sigma * math.sqrt(h_eff)
            expected = ens_mod.expected_move(0.0, tech, vol_h)
            half = max(1.28 * vol_h, 0.0) * risk_mult * 1.0
            conf = min(conf_cap, .20 + .45 * 1.0 + .10 * (1 / 5))
            out["family-technicals"][h] = _horizon_block(
                bf.direction_of(expected), expected * 100,
                (expected - half) * 100, (expected + half) * 100,
                round(conf, 2), round(tech, 3),
                {"technicals": round(tech, 3)}, hb,
                hb.get("trading_sessions"))

    # Buy-and-hold: mirror freeze_buy_and_hold — flat 0% with a
    # pure ±1.28σ√h_eff range.
    out["buy-and-hold"] = {}
    for h, bar in bf.HORIZONS.items():
        hb = (ens.get("horizons") or {}).get(h)
        if not isinstance(hb, dict):
            continue
        h_eff = hb.get("trading_sessions")
        if not isinstance(h_eff, int) or h_eff <= 0:
            h_eff = max(1, round(bar * density))
        half_pct = 1.28 * sigma * math.sqrt(h_eff) * 100
        out["buy-and-hold"][h] = _horizon_block(
            "flat", 0.0, -half_pct, half_pct, None, None, {}, hb,
            hb.get("trading_sessions"))

    # Index baseline: flat 0%, no range (a market-difficulty
    # reference scored on the index's own realised closes — see
    # score_capture). No confidence, no families.
    out["index-baseline"] = {}
    for h, bar in bf.HORIZONS.items():
        hb = (ens.get("horizons") or {}).get(h)
        if not isinstance(hb, dict):
            continue
        out["index-baseline"][h] = _horizon_block(
            "flat", 0.0, None, None, None, None, {}, hb,
            hb.get("trading_sessions"))
    return out


def score_capture(capture_dir):
    """Score one capture dir. Returns (rows, gaps): rows are
    ledger-shaped forecast dicts after score_forecast(), gaps are
    strings for the report. A capture without realised.json is
    skipped with a gap, never scored on partial data."""
    rel = os.path.relpath(capture_dir)
    ens = load_json(os.path.join(capture_dir, "digest/ensemble.json"))
    realised = load_json(os.path.join(capture_dir, "realised.json"))
    gaps = []
    if not isinstance(ens, dict) or not ens.get("base_price"):
        gaps.append("%s: no ensemble.json / no base — skipped" % rel)
        return [], gaps
    if not isinstance(realised, dict):
        gaps.append("%s: no realised.json — not scored" % rel)
        return [], gaps
    ticker = ens.get("ticker")
    as_of = str(ens.get("date") or realised.get("cutoff") or "")[:10]
    base = fnum(ens.get("base_price"))
    kronos_path, kronos_first = read_kronos_path(
        os.path.join(capture_dir, "collected/kronos/forecast.csv"))
    entrants = build_entrants(ens, kronos_path, kronos_first)
    # Series for scoring: the C close plus the 14 realised
    # sessions (design §1.4.4 — fetched separately, never visible
    # to the forecast). Provenance is a single backtest source;
    # own_sweep is a value that never appears in it, so every
    # post-cutoff session is usable (unlike the forward ledger,
    # where maturity must come from another sweep).
    series = {}
    if realised.get("base_close") is not None and realised.get(
            "base_date"):
        series[realised["base_date"]] = float(realised["base_close"])
    for s in realised.get("sessions") or []:
        try:
            series[s["date"]] = float(s["close"])
        except Exception:
            continue
    index_series = {}
    if realised.get("index_base_close") is not None and realised.get(
            "base_date"):
        index_series[realised["base_date"]] = float(
            realised["index_base_close"])
    for s in realised.get("index_sessions") or []:
        try:
            index_series[s["date"]] = float(s["close"])
        except Exception:
            continue
    provenance = {d: {"backtest"} for d in series}
    index_prov = {d: {"backtest"} for d in index_series}
    # Corporate actions for scoring: the forecast-known actions
    # (ex <= C) plus the scoring-window actions (C < ex <=
    # maturity), normalised through ledger.normalize_actions so
    # the ex-date == as-of cum-dividend test and the dedup behave
    # exactly as in the forward ledger.
    merged_actions = list(ens.get("corporate_actions") or [])
    for a in realised.get("actions") or []:
        merged_actions.append({
            "type": "dividend", "dps": a.get("dps"),
            "ex_date": a.get("ex_date"),
            "entitlement_end": a.get("entitlement_end"),
            "mechanical_pct": a.get("mechanical_pct")})
    norm = ledger.normalize_actions(
        {"corporate_actions": merged_actions}, {})
    splits = realised.get("splits") or []
    rows = []
    for entrant in ENTRANTS:
        for h in ledger.HORIZONS:
            hb = (entrants.get(entrant) or {}).get(h)
            if not isinstance(hb, dict):
                gaps.append("%s: %s has no %s horizon — no row"
                            % (rel, entrant, h))
                continue
            # The index baseline is a forecast ON the index, so
            # its base is the index close at the cutoff — scoring
            # it against the ticker's base would divide an index
            # close by a stock price.
            fc_base = (fnum(realised.get("index_base_close"))
                       if entrant == "index-baseline" else base)
            fc = {"ticker": ticker, "as_of": as_of,
                  "sweep": rel, "horizon": h,
                  "direction": hb.get("direction"),
                  "expected_move_pct": fnum(hb.get("expected_move_pct")),
                  "range_low_pct": fnum(hb.get("range_low_pct")),
                  "range_high_pct": fnum(hb.get("range_high_pct")),
                  "confidence": fnum(hb.get("confidence")),
                  "net_score": fnum(hb.get("net_score")),
                  "base_price": fc_base,
                  "families": {k: fnum(v) for k, v in
                               (hb.get("families") or {}).items()
                               if fnum(v) is not None},
                  "sessions": ledger.DEFAULT_SESSIONS[h],
                  "sessions_forecast": hb.get("sessions_forecast"),
                  "corporate_actions": norm,
                  "entrant": entrant}
            if splits:
                r = dict(fc)
                r.update(status="invalid",
                         invalid_reason=(
                             "split inside the horizon (%s) — the "
                             "price scale changes and the ledger "
                             "has no split adjustment"
                             % ", ".join(str(s.get("ex_date"))
                                         for s in splits)))
                rows.append(r)
                continue
            use_series = (index_series if entrant == "index-baseline"
                          else series)
            use_prov = (index_prov if entrant == "index-baseline"
                        else provenance)
            rows.append(ledger.score_forecast(
                fc, use_series, use_prov, "__backtest__"))
    return rows, gaps


def agg(subset):
    """ledger.py:agg, mirrored (same definitions, same rounding):
    hit rate + MAE over all rows, range coverage only over rows
    that carry a range."""
    n = len(subset)
    if not n:
        return {"n": 0, "hit_rate": None, "mean_abs_error_pp": None,
                "range_coverage": None}
    ranged = [r for r in subset if r.get("in_range") is not None]
    return {"n": n,
            "hit_rate": round(sum(r["direction_hit"] for r in subset) / n, 3),
            "mean_abs_error_pp": round(
                sum(r["move_error_pp"] for r in subset) / n, 2),
            "range_coverage": (round(
                sum(r["in_range"] for r in ranged) / len(ranged), 3)
                if ranged else None)}


def score_all(captures_root):
    """Score every capture under the root. Returns the backtest
    document (JSON-serialisable) plus the markdown text."""
    rows, gaps = [], []
    captures = []
    for cutoff in sorted(os.listdir(captures_root)):
        cdir = os.path.join(captures_root, cutoff)
        if not os.path.isdir(cdir):
            continue
        for ticker in sorted(os.listdir(cdir)):
            tdir = os.path.join(cdir, ticker)
            if os.path.isdir(tdir):
                captures.append(tdir)
    for cap in sorted(captures):
        r, g = score_capture(cap)
        rows.extend(r)
        gaps.extend(g)
    matured = [r for r in rows if r["status"] == "matured"]
    invalid = [r for r in rows if r["status"] == "invalid"]
    pending = [r for r in rows if r["status"] == "pending"]
    flagged = [r for r in matured if r.get("dividend_gap")]
    skill_rows = [r for r in matured if not r.get("dividend_gap")]
    by_ticker = {}
    for t in sorted({r["ticker"] for r in rows}):
        by_ticker[t] = {
            "found": sum(1 for r in rows if r["ticker"] == t),
            "matured": sum(1 for r in matured if r["ticker"] == t),
            "pending": sum(1 for r in pending if r["ticker"] == t),
            "invalid": sum(1 for r in invalid if r["ticker"] == t)}
    # Per (entrant, horizon) cells, with deltas vs the two
    # baselines (design §2.2 — hit rate and MAE relative to the
    # baselines, not just absolute).
    def cell(entrant, h):
        return agg([r for r in skill_rows
                    if r["entrant"] == entrant and r["horizon"] == h])
    by_entrant = {}
    for entrant in ENTRANTS:
        by_entrant[entrant] = {}
        for h in ledger.HORIZONS:
            a = cell(entrant, h)
            bah = cell("buy-and-hold", h)
            idx = cell("index-baseline", h)
            a["hit_rate_vs_buy_and_hold"] = (
                round(a["hit_rate"] - bah["hit_rate"], 3)
                if a["hit_rate"] is not None
                and bah["hit_rate"] is not None else None)
            a["mae_vs_buy_and_hold_pp"] = (
                round(a["mean_abs_error_pp"] - bah["mean_abs_error_pp"], 2)
                if a["mean_abs_error_pp"] is not None
                and bah["mean_abs_error_pp"] is not None else None)
            a["hit_rate_vs_index"] = (
                round(a["hit_rate"] - idx["hit_rate"], 3)
                if a["hit_rate"] is not None
                and idx["hit_rate"] is not None else None)
            a["mae_vs_index_pp"] = (
                round(a["mean_abs_error_pp"] - idx["mean_abs_error_pp"], 2)
                if a["mean_abs_error_pp"] is not None
                and idx["mean_abs_error_pp"] is not None else None)
            # No quality claim for a cell with n < 10 (design §2.2).
            a["quality_claim"] = a["n"] >= 10
            by_entrant[entrant][h] = a
    fam_vals = {}
    for r in skill_rows:
        if r["entrant"] != "2-family-ensemble":
            continue
        for fam, v in (r.get("family_skill") or {}).items():
            fam_vals.setdefault(fam, []).append(v)
        if r.get("net_skill") is not None:
            fam_vals.setdefault("ensemble (net_score)", []).append(
                r["net_skill"])
    family_skill = {fam: {"mean_skill": round(sum(v) / len(v), 3),
                          "n": len(v)}
                    for fam, v in sorted(fam_vals.items())}
    doc = {
        "tool": TOOL, "version": VERSION, "issue": 436,
        "flattery_warning": FLATTERY_WARNING,
        "exclusions": EXCLUSION_STATEMENT,
        "counts": {"captures": len(captures),
                   "forecasts": len(rows), "matured": len(matured),
                   "pending": len(pending), "invalid": len(invalid),
                   "excluded_flagged": len(flagged)},
        "by_ticker": by_ticker,
        "by_entrant": by_entrant,
        "family_skill": family_skill,
        "forecasts_detail": rows,
        "gaps": gaps,
    }
    return doc, render_md(doc)


def render_md(doc):
    L = ["# 🐊 Borsagator — walk-forward backtest (v1)", "",
         "> ⚠️ **Flattery warning:** " + FLATTERY_WARNING, "",
         "> " + EXCLUSION_STATEMENT, "",
         f"**Forecasts found: {doc['counts']['forecasts']} · "
         f"matured: {doc['counts']['matured']} · "
         f"pending: {doc['counts']['pending']} · "
         f"invalid: {doc['counts']['invalid']}"
         + (f" · excluded from skill: "
            f"{doc['counts']['excluded_flagged']} gap-flagged row(s)"
            if doc["counts"]["excluded_flagged"] else "")
         + f" · captures: {doc['counts']['captures']}**", "",
         "No quality claim is made for any (entrant, horizon) cell "
         "with n < 10 matured rows. Backtest n never counts toward "
         "the forward ledger's D4 threshold (n ≥ 30 matured).", "",
         "## By ticker", "",
         "| Ticker | Found | Matured | Pending | Invalid |",
         "|---|---|---|---|---|"]
    for t, b in doc["by_ticker"].items():
        L.append(f"| {t} | {b['found']} | {b['matured']} | "
                 f"{b['pending']} | {b['invalid']} |")
    L += ["", "## By entrant and horizon (matured only, gap-flagged "
          "rows excluded from skill)", "",
          "| Entrant | Horizon | n | Hit rate | MAE pp | Range cov. | "
          "Hit vs B&H | MAE vs B&H | Hit vs index | MAE vs index |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    fmt = lambda v, suf="": "—" if v is None else f"{v}{suf}"
    for entrant in ENTRANTS:
        for h in ledger.HORIZONS:
            a = doc["by_entrant"][entrant][h]
            claim = "" if a["quality_claim"] else " (n < 10 — no claim)"
            L.append(f"| {entrant} | {h} | {a['n']} | "
                     f"{fmt(a['hit_rate'])}{claim} | "
                     f"{fmt(a['mean_abs_error_pp'])} | "
                     f"{fmt(a['range_coverage'])} | "
                     f"{fmt(a['hit_rate_vs_buy_and_hold'])} | "
                     f"{fmt(a['mae_vs_buy_and_hold_pp'])} | "
                     f"{fmt(a['hit_rate_vs_index'])} | "
                     f"{fmt(a['mae_vs_index_pp'])} |")
    L += ["", "## Family skill (2-family ensemble rows only; mean of "
          "family_score × sign(realized), matured only)", "",
          "| Family | Mean skill | n |", "|---|---|---|"]
    if doc["family_skill"]:
        for fam, v in doc["family_skill"].items():
            L.append(f"| {fam} | {v['mean_skill']:+.3f} | {v['n']} |")
    else:
        L.append("| — | no matured forecasts yet | 0 |")
    L += ["", "## Forecasts", "",
          "| Ticker | As of | Horizon | Entrant | Dir | Expected % | "
          "Realized % | Hit | |Err| pp | In range | Adj | Status |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in doc["forecasts_detail"]:
        if r["status"] == "matured":
            f2 = lambda v: "—" if v is None else f"{v:+.2f}"
            f0 = lambda v: "—" if v is None else f"{v:.2f}"
            L.append(f"| {r['ticker']} | {r['as_of']} | {r['horizon']} | "
                     f"{r['entrant']} | {r['direction']} | "
                     f"{f2(r.get('expected_move_pct'))} | "
                     f"{f2(r.get('realized_move_pct'))} | "
                     f"{'✅' if r.get('direction_hit') else '❌'} | "
                     f"{f0(r.get('move_error_pp'))} | "
                     f"{'✅' if r.get('in_range') else '❌'} | "
                     f"{'💰' if r.get('dividend_adjusted') else ''} | "
                     f"matured {r.get('maturity_date', '')} |")
        elif r["status"] == "invalid":
            L.append(f"| {r['ticker']} | {r['as_of']} | {r['horizon']} | "
                     f"{r['entrant']} | {r['direction']} | "
                     f"{r.get('expected_move_pct')} | — | — | — | — | | "
                     f"invalid — {r.get('invalid_reason', '')} |")
        else:
            L.append(f"| {r['ticker']} | {r['as_of']} | {r['horizon']} | "
                     f"{r['entrant']} | {r['direction']} | "
                     f"{r.get('expected_move_pct')} | — | — | — | — | | "
                     f"pending ({r.get('sessions_available', 0)}/"
                     f"{r.get('sessions')} sessions) |")
    L += ["", "## Data gaps & notes", ""]
    for g in doc["gaps"]:
        L.append(f"- {g}")
    L += ["", "_Backtest scores are an upper bound on live skill "
          "(see the warning above). The forward ledger remains the "
          "only basis for accuracy claims._"]
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--captures", required=True,
                    help="Capture root (backtest/<cutoff>/<ticker>/).")
    ap.add_argument("--out", default=None,
                    help="Output dir for backtest.json + backtest.md "
                         "(default: the captures root).")
    args = ap.parse_args(argv)
    out_dir = args.out or args.captures
    last = os.path.basename(os.path.normpath(out_dir))
    if last == "ledger":
        ap.error("refusing to write backtest output into a ledger/ "
                 "directory — the two series must never mix")
    if not os.path.isdir(args.captures):
        ap.error("captures root not found: %s" % args.captures)
    doc, md = score_all(args.captures)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "backtest.json"), "w",
              encoding="utf-8") as f:
        json.dump(doc, f, indent=1, ensure_ascii=False)
    with open(os.path.join(out_dir, "backtest.md"), "w",
              encoding="utf-8") as f:
        f.write(md)
    print("backtest: %d forecasts (%d matured, %d invalid, %d pending) "
          "from %d captures -> %s"
          % (doc["counts"]["forecasts"], doc["counts"]["matured"],
             doc["counts"]["invalid"], doc["counts"]["pending"],
             doc["counts"]["captures"], out_dir))
    return 0


if __name__ == "__main__":
    sys.exit(main())
