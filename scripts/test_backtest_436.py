#!/usr/bin/env python3
"""Tests for the #436 walk-forward backtest harness (design §6.2).

Covers, per the design and the step-2 brief:
  * truncation — every staged input ends at the as-of cutoff (§1.4.1)
  * warm-up — < 60 sessions before the cutoff is skipped, not scored (§1.3)
  * anti-look-ahead audit — a planted future-dated row aborts the cutoff (§1.4)
  * determinism — the same cutoff twice gives identical directions (§6.4d);
    a non-deterministic Kronos stub is caught, not passed
  * runner-failure classification — a pandas-ta/talib MIN_ROWS failure is
    skipped-with-reason, not an unexpected error (step-1 observation)
  * gate — history depth / gaps / flat segments / events feed (§4)
  * scorer — ledger.score_forecast reuse, entrant blocks cross-checked
    against benchmark_freeze.freeze_* on identical fixtures, agg values,
    index-baseline deltas, and the separation guard (no backtest file is
    ever read by ledger.py)
  * ensemble 2-family mode — env-off output is byte-identical to the
    pre-change golden; env-on votes only price-forecast + technicals,
    risk none, weights_source base-v1
  * end-to-end smoke — the harness runs stub runners, stages a capture,
    audits it, and the scorer emits backtest.json/md carrying the §0
    flattery warning and the §5.2 exclusion statement

Standalone: `python3 scripts/test_backtest_436.py` (stdlib only, no
network, no model). Also wired into `scripts/harness_issue109.py`
as `--backtest`, mirroring the existing `--scorer` mode.
"""
import csv
import hashlib
import importlib.util
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

CHECKS = {"pass": 0, "fail": 0}
FAILURES = []


def check(name, cond, detail=""):
    if cond:
        CHECKS["pass"] += 1
        print("  PASS %s" % name)
    else:
        CHECKS["fail"] += 1
        FAILURES.append(name)
        print("  FAIL %s %s" % (name, detail))


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# --------------------------------------------------------------------------
# Deterministic fixture: a synthetic 300-session COMI.CA series ending
# exactly at the cutoff, plus canned runner outputs for it.
# --------------------------------------------------------------------------
FIXTURE_TICKER = "COMI.CA"
FIXTURE_CUTOFF = "2025-06-30"
FIXTURE_N = 300


def synthetic_series(n=FIXTURE_N, cutoff=FIXTURE_CUTOFF):
    """300 weekday sessions ending at the cutoff. Close drifts up
    with a sine wobble; no two consecutive closes are equal and
    there are no gaps — the clean case the gate must pass."""
    end = date.fromisoformat(cutoff)
    days = []
    d = end
    while len(days) < n:
        if d.weekday() < 5:  # Mon-Fri fixture calendar
            days.append(d)
        d -= timedelta(days=1)
    days.reverse()
    rows = []
    for i, d in enumerate(days):
        close = round(100.0 + 0.05 * i + 2.0 * math.sin(i / 7.0), 4)
        rows.append({"date": d.isoformat(), "close": close,
                     "open": round(close * 0.999, 4),
                     "high": round(close * 1.005, 4),
                     "low": round(close * 0.995, 4),
                     "volume": 1000000 + i * 100})
    return rows


def fixture_kronos_rows(series, cutoff=FIXTURE_CUTOFF, bars=21):
    """Kronos forecast path: 21 calendar days after the cutoff,
    closes continuing the drift (+0.1% per bar)."""
    base = series[-1]["close"]
    start = date.fromisoformat(cutoff) + timedelta(days=1)
    rows = []
    for j in range(bars):
        c = round(base * (1 + 0.001 * (j + 1)), 4)
        rows.append({"date": (start + timedelta(days=j)).isoformat(),
                     "open": round(c * 0.999, 4),
                     "high": round(c * 1.006, 4),
                     "low": round(c * 0.994, 4),
                     "close": c})
    return rows


def fixture_ta_metrics(series, cutoff=FIXTURE_CUTOFF):
    """pandas-ta snapshot metrics chosen for a known tech score:
    RSI 40 (+0.15), MACD hist +0.5 (+0.30), ADX 20 (no dampening),
    close above EMA20 (+0.15), Stoch 50 (0) -> tech score +0.60."""
    last = series[-1]["close"]
    return {"ticker": FIXTURE_TICKER, "as_of": cutoff,
            "date": cutoff, "open": series[-1]["open"],
            "high": series[-1]["high"], "low": series[-1]["low"],
            "close": last, "rsi_14": 40.0, "macd": 0.8,
            "macd_signal": 0.3, "macd_hist": 0.5,
            "ema_20": round(last * 0.99, 4), "ema_50": round(last * 0.97, 4),
            "ema_200": None, "adx_14": 20.0, "bb_upper": round(last * 1.02, 4),
            "bb_mid": last, "bb_lower": round(last * 0.98, 4),
            "bb_pctb": 0.5, "atr_14": 1.5, "stoch_k": 50.0, "stoch_d": 48.0,
            "rows_fetched": len(series), "rows_used": len(series),
            "first_date_used": series[0]["date"], "last_date": cutoff,
            "drop_before": "2019-01-01"}


def build_fixture_stage(stage_dir, cutoff=FIXTURE_CUTOFF,
                        ticker=FIXTURE_TICKER, with_digest=True):
    """Stage dir in the exact layout ensemble.py reads (digest/ +
    collected/), with canned runner outputs for the synthetic
    series. Returns (series, kronos_rows, ta_metrics)."""
    series = synthetic_series(cutoff=cutoff)
    kronos_rows = fixture_kronos_rows(series, cutoff)
    ta = fixture_ta_metrics(series, cutoff)
    for sub in ("digest", "collected/kronos", "collected/pandas-ta",
                "collected/talib"):
        os.makedirs(os.path.join(stage_dir, sub), exist_ok=True)
    with open(os.path.join(stage_dir, "collected/kronos/forecast.csv"),
              "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["date", "open", "high", "low",
                                          "close"])
        w.writeheader()
        w.writerows(kronos_rows)
    with open(os.path.join(stage_dir, "collected/kronos/report.md"),
              "w", encoding="utf-8") as f:
        f.write("# Kronos-small forecast — %s\n\n" % ticker)
        f.write("- Model: `NeoQuasar/Kronos-small` with tokenizer "
                "`NeoQuasar/Kronos-Tokenizer-base` (CPU inference, "
                "seed 42, T=1.0, top_p=0.9, sample_count=1)\n")
        f.write("- Context window used: %s to %s — %d sessions\n"
                % (series[0]["date"], cutoff, len(series)))
        f.write("- As-of cutoff: %s\n" % cutoff)
    tail = series[-250:]
    for tool in ("pandas-ta", "talib"):
        with open(os.path.join(stage_dir, "collected", tool,
                               "indicators.csv"),
                  "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["date", "open", "high",
                                              "low", "close", "volume"])
            w.writeheader()
            w.writerows([{k: r[k] for k in ("date", "open", "high",
                                            "low", "close", "volume")}
                         for r in tail])
    with open(os.path.join(stage_dir, "collected/pandas-ta",
                           "ta_snapshot.json"), "w", encoding="utf-8") as f:
        json.dump(ta, f, indent=1)
    talib_latest = {"ticker": ticker, "as_of": cutoff,
                    "rows_fetched": len(series), "rows_used": len(series),
                    "date_range": {"first": series[0]["date"],
                                   "last": cutoff},
                    "last_date": cutoff,
                    "last_close": series[-1]["close"],
                    "indicators": {"RSI_14": 40.0, "MACD": 0.8,
                                   "MACD_signal": 0.3, "MACD_hist": 0.5,
                                   "EMA_20": ta["ema_20"],
                                   "EMA_50": ta["ema_50"], "ADX_14": 20.0},
                    "patterns_last_60_sessions": {}}
    with open(os.path.join(stage_dir, "collected/talib/ta_latest.json"),
              "w", encoding="utf-8") as f:
        json.dump(talib_latest, f, indent=1)
    if with_digest:
        digest = {"ticker": ticker, "date": cutoff,
                  "job": "walkforward-backtest-fixture",
                  "corporate_actions": [],
                  "results": [
                      {"tool": "kronos", "status": "ok",
                       "summary": {"metrics": {
                           "forecast.csv_last_close":
                               kronos_rows[-1]["close"]}}},
                      {"tool": "pandas-ta", "status": "ok",
                       "summary": {"metrics": dict(ta)}},
                      {"tool": "talib", "status": "ok",
                       "summary": {"metrics": {
                           "close": series[-1]["close"]}}},
                  ]}
        with open(os.path.join(stage_dir, "digest/digest.json"),
                  "w", encoding="utf-8") as f:
            json.dump(digest, f, indent=1)
    return series, kronos_rows, ta


def run_ensemble(stage_dir, two_family=False, ensemble_path=None):
    """Run scripts/ensemble.py as a subprocess with cwd=stage_dir
    (exactly how the harness drives it). Returns the parsed
    digest/ensemble.json, or None when the run wrote none."""
    env = dict(os.environ)
    if two_family:
        env["BORSAGATOR_BACKTEST_TWO_FAMILY"] = "1"
    else:
        env.pop("BORSAGATOR_BACKTEST_TWO_FAMILY", None)
    # Weights must come from the builtin base table in the fixture:
    # point the measured-weights lookup at a file that does not
    # exist, exactly as the harness does for a real cell.
    env["BORSAGATOR_WEIGHTS"] = os.path.join(
        stage_dir, "no-such-weights.json")
    proc = subprocess.run(
        [sys.executable,
         ensemble_path or os.path.join(HERE, "ensemble.py")],
        cwd=stage_dir, env=env, capture_output=True, text=True,
        timeout=120)
    path = os.path.join(stage_dir, "digest/ensemble.json")
    if not os.path.exists(path):
        print("ensemble produced no output; stdout=%s stderr=%s"
              % (proc.stdout[-2000:], proc.stderr[-2000:]))
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# Golden ensemble output for the fixture above, produced by the
# PRE-CHANGE scripts/ensemble.py (main 69185656) on 2026-11-20.
# The 2-family-mode test asserts the env-off run still reproduces
# this exactly, so a refactor of the combine cannot silently move
# live numbers.
GOLDEN = {
    "ticker": "COMI.CA",
    "base_price": 113.041,
    "base_date": "2025-06-30",
    "sigma_daily": 0.0017,
    "weights_source": "builtin",
    "family_scores": {"technicals": 0.6, "sentiment": None,
                      "agent": None, "fundamentals": None,
                      "price-forecast": 1.0},
    "horizons": {
        "day": {"direction": "flat", "expected_move_pct": 0.1,
                "range_low_pct": -0.74, "range_high_pct": 0.94,
                "confidence": 0.35, "net_score": 0.429,
                "trading_sessions": 1},
        "week": {"direction": "flat", "expected_move_pct": 0.42,
                 "range_low_pct": -0.39, "range_high_pct": 1.23,
                 "confidence": 0.35, "net_score": 0.671,
                 "trading_sessions": 4},
        "month": {"direction": "up", "expected_move_pct": 1.57,
                  "range_low_pct": 0.34, "range_high_pct": 2.79,
                  "confidence": 0.35, "net_score": 0.882,
                  "trading_sessions": 15},
    },
}


def test_ensemble_two_family():
    print("== ensemble 2-family mode ==")
    stage = tempfile.mkdtemp(prefix="bt436-ens-")
    try:
        series, kronos_rows, ta = build_fixture_stage(stage)
        # Env OFF: must reproduce the pre-change golden exactly.
        ens = run_ensemble(stage, two_family=False)
        check("ensemble runs on fixture", ens is not None)
        if ens is None:
            return
        for key in ("ticker", "base_price", "base_date", "sigma_daily",
                    "weights_source"):
            check("golden %s" % key,
                  ens.get(key) == GOLDEN[key],
                  "got %r want %r" % (ens.get(key), GOLDEN[key]))
        check("golden family_scores",
              ens.get("family_scores") == GOLDEN["family_scores"],
              "got %r" % (ens.get("family_scores"),))
        for h, want in GOLDEN["horizons"].items():
            got = (ens.get("horizons") or {}).get(h) or {}
            for k, v in want.items():
                check("golden horizon %s.%s" % (h, k),
                      got.get(k) == v,
                      "got %r want %r" % (got.get(k), v))
        # Env ON: only the two backtestable families vote, the news
        # risk overlay is disabled, weights are the base table.
        ens2 = run_ensemble(stage, two_family=True)
        check("2-family ensemble runs", ens2 is not None)
        if ens2 is None:
            return
        check("2-family weights_source is base-v1",
              ens2.get("weights_source") == "base-v1",
              "got %r" % (ens2.get("weights_source"),))
        check("2-family risk level none",
              (ens2.get("risk") or {}).get("level") == "none",
              "got %r" % (ens2.get("risk"),))
        check("2-family price_mult 1.0",
              (ens2.get("risk") or {}).get("price_mult") == 1.0)
        fams = ens2.get("family_scores") or {}
        check("2-family sentiment null", fams.get("sentiment") is None)
        check("2-family agent null", fams.get("agent") is None)
        check("2-family fundamentals null",
              fams.get("fundamentals") is None)
        check("2-family technicals votes",
              fams.get("technicals") == 0.6, "got %r" % (fams.get("technicals"),))
        check("2-family price-forecast votes",
              fams.get("price-forecast") is not None)
        for h in ("day", "week", "month"):
            hb = (ens2.get("horizons") or {}).get(h) or {}
            voted = sorted((hb.get("families") or {}).keys())
            check("2-family horizon %s voters" % h,
                  voted == ["price-forecast", "technicals"],
                  "got %r" % (voted,))
        # The 2-family combine renormalises the live weights and
        # drops the news price_mult (0.8 -> 1.0): day .45/.30 with
        # the fixture's day price_score 0.286 (golden) and tech 0.6
        # gives net = (.45*0.286 + .30*0.6)/.75 = 0.412.
        day = (ens2.get("horizons") or {}).get("day") or {}
        check("2-family day net_score 0.412",
              day.get("net_score") == 0.412,
              "got %r" % (day.get("net_score"),))
        # expected = .6*kmove + .4*net*(1.28*vol_h), with kmove and
        # vol_h read back from the horizon block's own emitted
        # fields (no recomputation from rounded sigma).
        kmove = (day.get("kronos_move_pct") or 0.0) / 100.0
        vol_h = (day.get("vol_h_pct") or 0.0) / 100.0
        want_exp = round((0.6 * kmove
                          + 0.4 * day.get("net_score", 0)
                          * (1.28 * vol_h)) * 100, 2)
        check("2-family day expected matches combine",
              day.get("expected_move_pct") == want_exp,
              "got %r want %r" % (day.get("expected_move_pct"), want_exp))
        check("2-family day kmove is first Kronos bar",
              abs(kmove - (kronos_rows[0]["close"]
                           / ens2["base_price"] - 1.0)) < 1e-6,
              "got %r" % (kmove,))
        # expected_move() extracted from ensemble.py is the same rule.
        ens_mod = load_module(os.path.join(HERE, "ensemble.py"),
                              "ensemble_for_test")
        check("expected_move() matches inline rule",
              abs(ens_mod.expected_move(kmove, 0.412, vol_h)
                  - (0.6 * kmove + 0.4 * 0.412 * (1.28 * vol_h))) < 1e-12)
    finally:
        shutil.rmtree(stage, ignore_errors=True)


# --------------------------------------------------------------------------
# Gate (§4), warm-up (§1.3), runner-failure classification
# --------------------------------------------------------------------------
def _gate_rows(n=820, end="2025-07-28", flat_run=0, gap_after=None):
    series = synthetic_series(n=n, cutoff=end)
    if gap_after is not None:
        # Drop 30 calendar days of sessions after index gap_after.
        cut = date.fromisoformat(series[gap_after]["date"])
        series = [r for r in series
                  if not (cut < date.fromisoformat(r["date"])
                          <= cut + timedelta(days=30))]
    if flat_run:
        for r in series[100:100 + flat_run]:
            r["close"] = series[99]["close"]
    return series


def test_gate():
    print("== admission gate ==")
    bt = load_module(os.path.join(HERE, "backtest_gate.py"),
                     "backtest_gate")
    rows = _gate_rows()
    rec = bt.gate_ticker("COMI.CA", rows, True, "2025-06-30")
    check("gate passes clean history", rec["passed"],
          "; ".join(rec["reasons"]))
    # Quality checks run on bars on/before the cutoff only, so
    # the record counts those (820 fetched, 800 on/before
    # 2025-06-30) and its last date is the cutoff itself.
    usable_n = len([r for r in rows if r["date"] <= "2025-06-30"])
    check("gate rows are the on-or-before-cutoff bars",
          rec["rows"] == usable_n,
          "got %r want %r" % (rec["rows"], usable_n))
    check("gate last_date is the cutoff", rec["last_date"] == "2025-06-30",
          "got %r" % rec["last_date"])
    check("gate first_date 3y+", rec["first_date"] <= "2022-06-29",
          "got %r" % rec["first_date"])
    # A 30-day data gap AFTER the cutoff must not reject the
    # ticker for that cutoff: the fetched series still covers it
    # (sessions resume in August), and the gap is outside the
    # checked history. The pre-fix gate failed this on the July
    # gap (~21 missed sessions).
    july_gap = synthetic_series(n=860, cutoff="2025-08-28")
    cut = date.fromisoformat("2025-06-30")
    july_gap = [r for r in july_gap
                if not (cut < date.fromisoformat(r["date"])
                        <= cut + timedelta(days=30))]
    rec = bt.gate_ticker("COMI.CA", july_gap, True, "2025-06-30")
    check("gate ignores a post-cutoff gap", rec["passed"],
          "; ".join(rec["reasons"]))
    # A feed parsing failure (a dropped dividend) is reported
    # separately from a verified empty feed — and still fails.
    rec = bt.gate_ticker("COMI.CA", rows, False, "2025-06-30",
                         events_error="1 event record(s) unparseable "
                         "and dropped: dividend@1751241600")
    check("gate reports a feed parsing failure separately",
          not rec["passed"]
          and any("parsing failed" in r for r in rec["reasons"]),
          "; ".join(rec["reasons"]))
    check("gate records the parse error",
          rec["events_parse_error"] is not None)
    # unpack_fetch accepts the older 3-tuple (test fetchers) as a
    # clean feed.
    check("unpack_fetch 3-tuple reads clean",
          bt.unpack_fetch((rows, [], True))[3] is None)
    check("unpack_fetch 4-tuple passes through",
          bt.unpack_fetch((rows, [], False, "x"))[2] is False)
    check("unpack_fetch 3/4-tuples default to no dropped bars",
          bt.unpack_fetch((rows, [], True))[4] == []
          and bt.unpack_fetch((rows, [], False, "x"))[4] == [])
    check("unpack_fetch 5-tuple passes dropped dates through",
          bt.unpack_fetch((rows, [], True, None, ["2025-07-01"]))[4]
          == ["2025-07-01"])
    short = _gate_rows(n=100)
    rec = bt.gate_ticker("COMI.CA", short, True, "2025-06-30")
    check("gate fails short history", not rec["passed"]
          and any("history starts" in r for r in rec["reasons"]),
          "; ".join(rec["reasons"]))
    gapped = _gate_rows(gap_after=400)
    rec = bt.gate_ticker("COMI.CA", gapped, True, "2025-06-30")
    check("gate fails 30-day gap", not rec["passed"]
          and any("gap" in r for r in rec["reasons"]),
          "; ".join(rec["reasons"]))
    flat = _gate_rows(flat_run=25)
    rec = bt.gate_ticker("COMI.CA", flat, True, "2025-06-30")
    check("gate fails 25-flat run", not rec["passed"]
          and any("flat" in r for r in rec["reasons"]),
          "; ".join(rec["reasons"]))
    rec = bt.gate_ticker("COMI.CA", rows, False, "2025-06-30")
    check("gate fails without events feed", not rec["passed"]
          and any("events" in r for r in rec["reasons"]),
          "; ".join(rec["reasons"]))
    # The POUL trap (§1.5): history from 2020, but the usable
    # series starts 2026-09-28 — the gate must fail it on depth.
    poul = synthetic_series(n=1500, cutoff="2026-09-30")
    rec = bt.gate_ticker("POUL.CA", poul, True, "2026-09-30",
                         series_start="2026-09-28")
    check("gate fails POUL usable-series depth", not rec["passed"]
          and any("history starts" in r for r in rec["reasons"]),
          "; ".join(rec["reasons"]))
    check("gate POUL usable rows tiny", rec["rows"] <= 5,
          "got %r" % rec["rows"])
    # [1] a coverage gap at the END of the cutoff window: history
    # ends 2025-06-02 and resumes 2025-07-01, so the June 30 gate
    # must fail even though fetched data reaches past the cutoff
    # (fetched_last is past it, and max_gap only measures gaps
    # inside the usable rows). The pre-fix gate passed this.
    tail_gap = synthetic_series(n=820, cutoff="2025-07-28")
    tail_gap = [r for r in tail_gap
                if not ("2025-06-03" <= r["date"] <= "2025-06-30")]
    rec = bt.gate_ticker("COMI.CA", tail_gap, True, "2025-06-30")
    check("gate fails a tail gap before the cutoff",
          not rec["passed"]
          and any("sessions before" in r for r in rec["reasons"]),
          "; ".join(rec["reasons"]))
    # Control: last bar Friday 2025-06-27, cutoff Monday
    # 2025-06-30 — a non-session cutoff stays valid (the tail
    # tolerance is the same session estimate as max_gap).
    weekend = synthetic_series(n=820, cutoff="2025-07-28")
    weekend = [r for r in weekend
               if not ("2025-06-28" <= r["date"] <= "2025-06-30")]
    rec = bt.gate_ticker("COMI.CA", weekend, True, "2025-06-30")
    check("gate passes a weekend tail before the cutoff",
          rec["passed"], "; ".join(rec["reasons"]))
    # [5] the tail estimate must not subtract a session: the
    # tail runs from the last observed bar to the cutoff, and
    # no observed session closes it (unlike a gap between two
    # observed bars). A 15-calendar-day tail is ~11 missed
    # sessions — over the 10-session limit — where the old
    # estimate subtracted one and admitted it at exactly 10.
    tail15 = [r for r in synthetic_series(n=820, cutoff="2025-07-28")
              if r["date"] <= "2025-06-13" or r["date"] > "2025-06-30"]
    tail15.append({"date": "2025-06-15", "close": 100.0,
                   "open": 100.0, "high": 100.0, "low": 100.0,
                   "volume": 1})
    tail15.sort(key=lambda r: r["date"])
    rec = bt.gate_ticker("COMI.CA", tail15, True, "2025-06-30")
    check("gate fails a 15-day tail before the cutoff",
          not rec["passed"]
          and any("sessions before" in r for r in rec["reasons"]),
          "; ".join(rec["reasons"]))
    # Control: a 14-day tail estimates exactly the 10-session
    # limit and still passes.
    tail14 = [r for r in synthetic_series(n=820, cutoff="2025-07-28")
              if not ("2025-06-17" <= r["date"] <= "2025-06-30")]
    rec = bt.gate_ticker("COMI.CA", tail14, True, "2025-06-30")
    check("gate passes a 14-day tail before the cutoff",
          rec["passed"], "; ".join(rec["reasons"]))
    # [0] a non-finite dividend amount (NaN/inf via float()) is
    # an unparseable record: dropped, feed marked failed — never
    # kept into realised.json, where json.dump would write a bare
    # NaN token and the scorer's dividend-adjusted close goes NaN.
    import datetime as _dt
    import urllib.request as _urlreq

    def _chart_payload(amount):
        ts = lambda y, m, d: int(_dt.datetime(
            y, m, d, tzinfo=_dt.timezone.utc).timestamp())
        return {"chart": {"error": None, "result": [{
            "timestamp": [ts(2025, 6, 27), ts(2025, 6, 30)],
            "indicators": {"quote": [{"close": [100.0, 101.0]}]},
            "meta": {"exchangeTimezoneName": "Africa/Cairo"},
            "events": {"dividend": {
                str(ts(2025, 6, 29)): {"amount": amount,
                                       "date": ts(2025, 6, 29)}}}}]}}

    class _FakeResp:
        def __init__(self, payload):
            self._data = json.dumps(payload).encode("utf-8")

        def read(self):
            return self._data

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    real_urlopen = _urlreq.urlopen
    try:
        _urlreq.urlopen = lambda req, timeout=30: _FakeResp(
            _chart_payload(float("nan")))
        rows_n, ev_n, ok_n, err_n, drop_n = bt.fetch_chart("COMI.CA")
        check("NaN dividend record is dropped",
              ev_n == [], "got %r" % (ev_n,))
        check("NaN dividend marks the feed failed",
              ok_n is False and err_n is not None
              and "dividend" in err_n, "ok=%r err=%r" % (ok_n, err_n))
        check("NaN dividend still parses the price rows",
              len(rows_n) == 2, "got %d" % len(rows_n))
        _urlreq.urlopen = lambda req, timeout=30: _FakeResp(
            _chart_payload(1.9))
        rows_f, ev_f, ok_f, err_f, drop_f = bt.fetch_chart("COMI.CA")
        check("finite dividend keeps its current path",
              ok_f is True and err_f is None and len(ev_f) == 1
              and ev_f[0]["dps"] == 1.9,
              "ok=%r err=%r ev=%r" % (ok_f, err_f, ev_f))
        check("clean feed records no dropped bars",
              drop_f == [], "got %r" % (drop_f,))
    finally:
        _urlreq.urlopen = real_urlopen
    # [8] a non-finite CLOSE (NaN via float()) must be dropped
    # the same way: kept, it counts toward realised maturity
    # and is later written to realised.json as a bare NaN.
    def _chart_payload_nan_close():
        ts = lambda y, m, d: int(_dt.datetime(
            y, m, d, tzinfo=_dt.timezone.utc).timestamp())
        return {"chart": {"error": None, "result": [{
            "timestamp": [ts(2025, 6, 27), ts(2025, 6, 30)],
            "indicators": {"quote": [{"close": [100.0,
                                                 float("nan")]}]},
            "meta": {"exchangeTimezoneName": "Africa/Cairo"}}]}}

    real_urlopen = _urlreq.urlopen
    try:
        _urlreq.urlopen = lambda req, timeout=30: _FakeResp(
            _chart_payload_nan_close())
        rows_x, _ev_x, _ok_x, _err_x, drop_x = bt.fetch_chart("COMI.CA")
        check("NaN close row is dropped",
              len(rows_x) == 1 and rows_x[0]["close"] == 100.0,
              "got %r" % (rows_x,))
        check("NaN close date is recorded as dropped",
              drop_x == ["2025-06-30"], "got %r" % (drop_x,))
    finally:
        _urlreq.urlopen = real_urlopen


def test_warmup_and_failure_classification():
    print("== warm-up + runner-failure classification ==")
    bt = load_module(os.path.join(HERE, "backtest.py"), "backtest")
    rows = synthetic_series(n=40, cutoff="2025-06-30")
    ok, n, reason = bt.warmup_check(rows, "2025-06-30")
    check("warm-up fails 40 sessions", not ok and n == 40, reason)
    rows = synthetic_series(n=60, cutoff="2025-06-30")
    ok, n, reason = bt.warmup_check(rows, "2025-06-30")
    check("warm-up passes exactly 60", ok and n == 60, reason)
    rows = synthetic_series(n=300, cutoff="2025-06-30")
    ok, n, reason = bt.warmup_check(rows, "2025-06-30",
                                    series_start="2026-09-28")
    check("warm-up fails POUL pre-resumption cutoff", not ok,
          "n=%r" % n)
    skip, why = bt.classify_runner_failure(
        "RuntimeError: --as-of 2024-01-02: only 15 sessions "
        "on/before the cutoff (min-context 20)")
    check("kronos min-context refusal is a skip", skip, why)
    skip, why = bt.classify_runner_failure(
        "--as-of 2024-01-02: only 15 sessions on/before the cutoff "
        "(< 20 minimum rows); refusing to forecast")
    check("kronos real refusal line is a skip", skip, why)
    # Argparse usage text names the --min-context option: it must
    # stay an error, not a minimum-rows skip (else the CLI exits
    # zero on a real argument error).
    skip, _why = bt.classify_runner_failure(
        "usage: kronos_forecast.py [-h] [--ticker TICKER] "
        "[--pred-len PRED_LEN] [--as-of AS_OF] "
        "[--min-context MIN_CONTEXT]\n"
        "kronos_forecast.py: error: argument --min-context: "
        "invalid int value: 'x'")
    check("usage text naming --min-context is an error, not a skip",
          not skip)
    skip, why = bt.classify_runner_failure(
        "cutoff (< 60 minimum rows); refusing to snapshot")
    check("pandas-ta MIN_ROWS refusal is a skip", skip, why)
    skip, _why = bt.classify_runner_failure(
        "Traceback (most recent call last):\nKeyError: 'close'")
    check("traceback is an error, not a skip", not skip)
    skip, _why = bt.classify_runner_failure("")
    check("empty output is an error, not a skip", not skip)


# --------------------------------------------------------------------------
# Audit (§1.4)
# --------------------------------------------------------------------------
def test_audit():
    print("== anti-look-ahead audit ==")
    bt = load_module(os.path.join(HERE, "backtest.py"), "backtest")
    stage = tempfile.mkdtemp(prefix="bt436-audit-")
    try:
        build_fixture_stage(stage)
        ens = run_ensemble(stage, two_family=True)
        check("audit fixture ensemble runs", ens is not None)
        v = bt.audit_stage(stage, FIXTURE_CUTOFF, FIXTURE_TICKER)
        check("audit passes clean stage", v == [], "; ".join(v))
        # Plant a future-dated row in an input CSV: the audit
        # must abort the cutoff.
        path = os.path.join(stage, "collected/pandas-ta/indicators.csv")
        with open(path, "a", encoding="utf-8") as f:
            f.write("2025-07-01,120,121,119,120,1000\n")
        v = bt.audit_stage(stage, FIXTURE_CUTOFF, FIXTURE_TICKER)
        check("audit aborts planted future row",
              any("after cutoff" in x for x in v), "; ".join(v))
        # Tamper the weights source: measured weights must never
        # leak into a backtest cell.
        with open(path, "w", encoding="utf-8") as f:
            pass
        build_fixture_stage(stage)
        ens = run_ensemble(stage, two_family=True)
        epath = os.path.join(stage, "digest/ensemble.json")
        doc = json.load(open(epath, encoding="utf-8"))
        doc["weights_source"] = "ledger"
        json.dump(doc, open(epath, "w", encoding="utf-8"))
        v = bt.audit_stage(stage, FIXTURE_CUTOFF, FIXTURE_TICKER)
        check("audit aborts ledger weights leak",
              any("base-v1" in x for x in v), "; ".join(v))
        # A report with no context-window line at all: the audit
        # cannot verify what history Kronos consumed, so it must
        # fail instead of passing silently.
        build_fixture_stage(stage)
        ens = run_ensemble(stage, two_family=True)
        rpath = os.path.join(stage, "collected/kronos/report.md")
        with open(rpath, "w", encoding="utf-8") as f:
            f.write("# Kronos-small forecast — %s\n\n"
                    "- Model: `NeoQuasar/Kronos-small`\n" % FIXTURE_TICKER)
        v = bt.audit_stage(stage, FIXTURE_CUTOFF, FIXTURE_TICKER)
        check("audit fails a report with no context line",
              any("no context window" in x for x in v), "; ".join(v))
        # A context line ending after the cutoff still fails.
        build_fixture_stage(stage)
        ens = run_ensemble(stage, two_family=True)
        with open(rpath, "w", encoding="utf-8") as f:
            f.write("# Kronos-small forecast — %s\n\n"
                    "- Context window used: 2024-01-02 to 2025-07-01 "
                    "— 300 sessions\n" % FIXTURE_TICKER)
        v = bt.audit_stage(stage, FIXTURE_CUTOFF, FIXTURE_TICKER)
        check("audit fails a post-cutoff context end",
              any("after cutoff" in x for x in v), "; ".join(v))
        # Base-price guard: the #87 case (COMI 10.15 vs 128.51).
        ok, why = bt.base_price_guard(10.15, 128.51, "2025-06-30",
                                      "2025-06-30", [])
        check("base-price guard rejects wrong-ticker base", not ok,
              why)
        ok, why = bt.base_price_guard(113.041, 113.041, "2025-06-30",
                                      "2025-06-30", [])
        check("base-price guard accepts matching base", ok, why)
    finally:
        shutil.rmtree(stage, ignore_errors=True)


# --------------------------------------------------------------------------
# Stub runners (smoke + determinism): mimic the three runners'
# CLIs and outputs from a prices.csv next to the script.
# --------------------------------------------------------------------------
STUB_KRONOS = '''#!/usr/bin/env python3
import argparse, csv, os, sys
from datetime import date, timedelta
ap = argparse.ArgumentParser()
ap.add_argument("--ticker", default="COMI.CA")
ap.add_argument("--pred-len", type=int, default=10)
ap.add_argument("--context-start", default="2019-01-01")
ap.add_argument("--fallback-len", type=int, default=400)
ap.add_argument("--min-context", type=int, default=20)
ap.add_argument("--as-of", default=None)
args = ap.parse_args()
here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rows = list(csv.DictReader(open(os.path.join(here, "prices.csv"),
                                newline="", encoding="utf-8")))
if args.as_of:
    rows = [r for r in rows if r["date"] <= args.as_of]
if len(rows) < args.min_context:
    sys.exit("--as-of %s: only %d sessions on/before the cutoff "
             "(min-context %d)" % (args.as_of, len(rows),
                                   args.min_context))
counter = os.path.join(here, "kronos-runs.txt")
n = int(open(counter).read().strip() or 0) if os.path.exists(counter) else 0
open(counter, "w").write(str(n + 1))
flip = os.environ.get("BT436_KRONOS_FLIP") == "1" and (n % 2 == 1)
base = float(rows[-1]["close"])
os.makedirs("results", exist_ok=True)
start = date.fromisoformat(rows[-1]["date"]) + timedelta(days=1)
with open("results/forecast.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["date", "open", "high", "low",
                                      "close"])
    w.writeheader()
    for j in range(args.pred_len):
        drift = -0.001 if flip else 0.001
        c = round(base * (1 + drift * (j + 1)), 4)
        w.writerow({"date": (start + timedelta(days=j)).isoformat(),
                    "open": round(c * 0.999, 4),
                    "high": round(c * 1.006, 4),
                    "low": round(c * 0.994, 4), "close": c})
with open("results/report.md", "w") as f:
    f.write("# Kronos-small forecast — %s\\n\\n" % args.ticker)
    f.write("- Model: `NeoQuasar/Kronos-small` with tokenizer "
            "`NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed "
            "42, T=1.0, top_p=0.9, sample_count=1)\\n")
    f.write("- Context window used: %s to %s — %d sessions\\n"
            % (rows[0]["date"], rows[-1]["date"], len(rows)))
    if args.as_of:
        f.write("- As-of cutoff: %s\\n" % args.as_of)
print("[as-of] cutoff=%s rows_on_or_before=%d last_session=%s"
      % (args.as_of, len(rows), rows[-1]["date"]))
'''

STUB_PANDAS_TA = '''#!/usr/bin/env python3
import argparse, csv, json, os, sys
ap = argparse.ArgumentParser()
ap.add_argument("--ticker", default="COMI.CA")
ap.add_argument("--drop-before", default="2019-01-01")
ap.add_argument("--as-of", default=None)
args = ap.parse_args()
here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rows = list(csv.DictReader(open(os.path.join(here, "prices.csv"),
                                newline="", encoding="utf-8")))
if args.as_of:
    rows = [r for r in rows if r["date"] <= args.as_of]
if len(rows) < 60:
    sys.exit("cutoff (< 60 minimum rows); refusing to snapshot "
             "(only %d sessions on/before %s)"
             % (len(rows), args.as_of))
last = rows[-1]
close = float(last["close"])
snap = {"ticker": args.ticker, "as_of": args.as_of,
        "date": last["date"], "open": float(last["open"]),
        "high": float(last["high"]), "low": float(last["low"]),
        "close": close, "rsi_14": 40.0, "macd": 0.8,
        "macd_signal": 0.3, "macd_hist": 0.5,
        "ema_20": round(close * 0.99, 4),
        "ema_50": round(close * 0.97, 4), "ema_200": None,
        "adx_14": 20.0, "bb_upper": round(close * 1.02, 4),
        "bb_mid": close, "bb_lower": round(close * 0.98, 4),
        "bb_pctb": 0.5, "atr_14": 1.5, "stoch_k": 50.0,
        "stoch_d": 48.0, "rows_fetched": len(rows),
        "rows_used": len(rows), "first_date_used": rows[0]["date"],
        "last_date": last["date"], "drop_before": args.drop_before}
os.makedirs("results", exist_ok=True)
json.dump(snap, open("results/ta_snapshot.json", "w"), indent=1)
with open("results/indicators.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["date", "open", "high", "low",
                                      "close", "volume"])
    w.writeheader()
    w.writerows(rows[-250:])
print("[as-of] cutoff=%s rows_on_or_before=%d last_session=%s"
      % (args.as_of, len(rows), last["date"]))
'''

STUB_TALIB = '''#!/usr/bin/env python3
import argparse, csv, json, os, sys
ap = argparse.ArgumentParser()
ap.add_argument("ticker", nargs="?", default="COMI.CA")
ap.add_argument("--as-of", default=None)
args = ap.parse_args()
here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rows = list(csv.DictReader(open(os.path.join(here, "prices.csv"),
                                newline="", encoding="utf-8")))
if args.as_of:
    rows = [r for r in rows if r["date"] <= args.as_of]
min_rows = int(os.environ.get("BT436_TALIB_MIN_ROWS", "60"))
if len(rows) < min_rows:
    sys.exit("cutoff (< %d minimum rows); refusing to snapshot "
             "(only %d sessions on/before %s)"
             % (min_rows, len(rows), args.as_of))
last = rows[-1]
close = float(last["close"])
out = {"ticker": args.ticker, "as_of": args.as_of,
       "rows_fetched": len(rows), "rows_used": len(rows),
       "date_range": {"first": rows[0]["date"], "last": last["date"]},
       "last_date": last["date"], "last_close": close,
       "indicators": {"RSI_14": 40.0, "MACD": 0.8,
                      "MACD_signal": 0.3, "MACD_hist": 0.5,
                      "EMA_20": round(close * 0.99, 4),
                      "EMA_50": round(close * 0.97, 4),
                      "ADX_14": 20.0},
       "patterns_last_60_sessions": {}}
os.makedirs("results", exist_ok=True)
json.dump(out, open("results/ta_latest.json", "w"), indent=1)
with open("results/indicators.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["date", "open", "high", "low",
                                      "close", "volume"])
    w.writeheader()
    w.writerows(rows[-250:])
print("[as-of] cutoff=%s rows_on_or_before=%d last_session=%s"
      % (args.as_of, len(rows), last["date"]))
'''


def _write_stub_runner(root, kind, code, filename, series):
    d = os.path.join(root, kind)
    os.makedirs(os.path.join(d, "scripts"), exist_ok=True)
    with open(os.path.join(d, "scripts", filename), "w",
              encoding="utf-8") as f:
        f.write(code)
    with open(os.path.join(d, "prices.csv"), "w", newline="",
              encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["date", "open", "high",
                                          "low", "close", "volume"])
        w.writeheader()
        w.writerows(series)
    return d


def _stub_fetcher(series, index_series):
    def fetch(ticker):
        if str(ticker).startswith("^"):
            return list(index_series), [], True
        return list(series), [], True
    return fetch


def _smoke_cfg(tmp, series, index_series, flip=False):
    runners = {
        "kronos": _write_stub_runner(tmp, "kronos-runner", STUB_KRONOS,
                                     "kronos_forecast.py", series),
        "pandas-ta": _write_stub_runner(tmp, "pandas-ta-runner",
                                        STUB_PANDAS_TA,
                                        "ta_snapshot.py", series),
        "talib": _write_stub_runner(tmp, "talib-runner", STUB_TALIB,
                                    "ta.py", series),
    }
    if flip:
        os.environ["BT436_KRONOS_FLIP"] = "1"
    elif "BT436_KRONOS_FLIP" in os.environ:
        del os.environ["BT436_KRONOS_FLIP"]
    return {"out_root": os.path.join(tmp, "backtest"),
            "runners": runners, "borsagator_root": REPO,
            "latest_cutoff": FIXTURE_CUTOFF, "timeout": 120,
            "repeat_kronos": True, "realised_file": None,
            "fetcher": _stub_fetcher(series, index_series)}


def test_smoke_and_determinism():
    print("== smoke + determinism (stub runners) ==")
    bt = load_module(os.path.join(HERE, "backtest.py"), "backtest")
    tmp = tempfile.mkdtemp(prefix="bt436-smoke-")
    try:
        series = synthetic_series(n=820, cutoff="2025-07-28")
        index = [{"date": r["date"],
                  "close": round(30000.0 + 2.0 * i, 4),
                  "open": 0, "high": 0, "low": 0, "volume": 0}
                 for i, r in enumerate(series)]
        cfg = _smoke_cfg(tmp, series, index)
        res = bt.run_cell(FIXTURE_CUTOFF, FIXTURE_TICKER, cfg)
        check("smoke cell ok", res["status"] == "ok",
              "%s: %s" % (res["status"], res.get("reason", "")))
        if res["status"] != "ok":
            return
        cap = res["capture_dir"]
        check("smoke capture dir", os.path.isdir(cap))
        man = json.load(open(os.path.join(cap, "manifest.json"),
                             encoding="utf-8"))
        check("manifest tool", man["tool"] == "walkforward-backtest")
        check("manifest audit passed",
              man["audit"]["passed"] is True)
        check("manifest determinism rerun",
              man["determinism"].get("rerun") is True)
        check("manifest weights base-v1",
              man["weights_source"] == "base-v1")
        check("manifest kronos seed 42",
              man["kronos"]["seed"] == 42)
        for rel, sha in man["files"].items():
            p = os.path.join(cap, rel)
            check("manifest sha %s" % rel,
                  os.path.exists(p) and bt.sha256_file(p) == sha)
        ens = json.load(open(os.path.join(
            cap, "digest/ensemble.json"), encoding="utf-8"))
        check("capture ensemble 2-family",
              (ens.get("risk") or {}).get("level") == "none"
              and ens.get("weights_source") == "base-v1")
        check("capture realised has 14 sessions",
              len(json.load(open(os.path.join(
                  cap, "realised.json"),
                  encoding="utf-8"))["sessions"]) == 14)
        # Non-deterministic Kronos: the repeat run flips the path,
        # so the cell must fail — not publish.
        cfg2 = _smoke_cfg(tmp + "-flip", series, index, flip=True)
        res2 = bt.run_cell(FIXTURE_CUTOFF, FIXTURE_TICKER, cfg2)
        check("non-deterministic kronos fails the cell",
              res2["status"] == "error"
              and "non-deterministic" in (res2.get("reason") or ""),
              "%s: %s" % (res2["status"], res2.get("reason", "")))
        check("failed cell publishes no capture",
              res2.get("capture_dir") is None)
        # [8] a realised file carrying a non-finite value (an
        # offline NaN) must fail before publication: the
        # capture writes use allow_nan=False, so the dump
        # raises instead of writing a bare NaN the scorer
        # would read back as a close.
        cfg3 = _smoke_cfg(tmp + "-nan", series, index)
        cfg3["repeat_kronos"] = False
        after = [r for r in series if r["date"] > FIXTURE_CUTOFF][:14]
        realised_nan = {
            "ticker": FIXTURE_TICKER, "cutoff": FIXTURE_CUTOFF,
            "base_close": [r for r in series
                           if r["date"] <= FIXTURE_CUTOFF][-1]["close"],
            "base_date": FIXTURE_CUTOFF,
            "sessions": [{"date": r["date"], "close": r["close"]}
                         for r in after],
            "maturity_date": after[-1]["date"],
            "index_ticker": "^EGX30", "index_base_close": 30000.0,
            "index_sessions": [], "index_gap": "fixture",
            "actions": [], "splits": []}
        realised_nan["sessions"][3]["close"] = float("nan")
        nan_path = os.path.join(tmp, "realised-nan.json")
        with open(nan_path, "w", encoding="utf-8") as f:
            json.dump(realised_nan, f)
        cfg3["realised_file"] = nan_path
        raised = None
        try:
            bt.run_cell(FIXTURE_CUTOFF, FIXTURE_TICKER, cfg3)
        except ValueError as e:
            raised = e
        check("NaN realised value fails before publication",
              raised is not None, "no ValueError raised")
        check("NaN realised publishes no capture",
              not os.path.exists(os.path.join(
                  tmp + "-nan", "backtest", FIXTURE_CUTOFF,
                  FIXTURE_TICKER)))
    finally:
        os.environ.pop("BT436_KRONOS_FLIP", None)
        shutil.rmtree(tmp, ignore_errors=True)
        shutil.rmtree(tmp + "-flip", ignore_errors=True)


def test_cell_guards():
    print("== cell guards (capture path / base date / realised / publish) ==")
    bt = load_module(os.path.join(HERE, "backtest.py"), "backtest")
    tmp = tempfile.mkdtemp(prefix="bt436-guards-")
    try:
        # [10] capture-path validation is pure.
        cell, err = bt.validate_capture_path(
            "/tmp/bt-out", "2025-06-30", "COMI.CA")
        check("capture path accepts a clean cell",
              err == "" and cell.endswith("2025-06-30/COMI.CA"), err)
        _c, err = bt.validate_capture_path(
            "/tmp/bt-out", "../ledger", "COMI.CA")
        check("capture path rejects a traversal cutoff", err != "", err)
        _c, err = bt.validate_capture_path(
            "/tmp/bt-out", "2025-06-30", "../../etc")
        check("capture path rejects a traversal ticker", err != "", err)
        _c, err = bt.validate_capture_path(
            os.path.join(REPO, "ledger"), "2025-06-30", "COMI.CA")
        check("capture path rejects an out-root inside ledger/",
              err != "", err)
        _c, err = bt.validate_capture_path(
            os.path.join(REPO, "archive"), "2025-06-30", "COMI.CA")
        check("capture path rejects an out-root inside archive/",
              err != "", err)
        _c, err = bt.validate_capture_path(
            "/tmp/bt-out", "2025-6-30", "COMI.CA")
        check("capture path rejects a non-ISO cutoff", err != "", err)
        # [4] a cell alias resolving to the out-root itself must
        # be rejected: publish would rename the whole out-root
        # to .old- and delete every other capture under it.
        out_alias = os.path.join(tmp, "out-alias")
        os.makedirs(os.path.join(out_alias, "2025-06-30"),
                    exist_ok=True)
        os.symlink(out_alias, os.path.join(
            out_alias, "2025-06-30", "COMI.CA"))
        _c, err = bt.validate_capture_path(
            out_alias, "2025-06-30", "COMI.CA")
        check("capture path rejects a cell resolving to the "
              "out-root", err != "", err)
        # [2] a ticker alias resolving to its own cutoff
        # directory must be rejected too: publish renames the
        # resolved cell dir to the backup path and deletes it,
        # which here would wipe every sibling capture under
        # the cutoff (the ETEL.CA capture included).
        out_cell = os.path.join(tmp, "out-cell")
        os.makedirs(os.path.join(out_cell, "2025-06-30", "ETEL.CA"))
        os.symlink(os.path.join(out_cell, "2025-06-30"),
                   os.path.join(out_cell, "2025-06-30", "COMI.CA"))
        _c, err = bt.validate_capture_path(
            out_cell, "2025-06-30", "COMI.CA")
        check("capture path rejects a cell resolving to its "
              "cutoff directory", err != "", err)
        # [5] a cell alias resolving to the repo root must be
        # rejected too: the containment check only guards a cell
        # *inside* the ledger/archive trees, not a cell that
        # *contains* them — publish would move the whole repo
        # to the backup path and delete it. The fixture lives
        # entirely under tmp: a fake repo root with ledger/ and
        # archive/ trees, with bt.REPO_ROOT patched to it (and
        # restored in the finally). An earlier version built
        # the cell dir beside the real checkout with
        # exist_ok=True and deleted it in the finally — a
        # directory the test may not have created.
        fake_repo = os.path.join(tmp, "fake-repo")
        os.makedirs(os.path.join(fake_repo, "ledger"))
        os.makedirs(os.path.join(fake_repo, "archive"))
        broad_cell_dir = os.path.join(tmp, "2025-06-30")
        os.makedirs(broad_cell_dir)
        broad_link = os.path.join(broad_cell_dir, "COMI.CA")
        real_repo_root = bt.REPO_ROOT
        bt.REPO_ROOT = fake_repo
        try:
            os.symlink(fake_repo, broad_link)
            _c, err = bt.validate_capture_path(
                tmp, "2025-06-30", "COMI.CA")
            check("capture path rejects a cell containing the "
                  "ledger/archive trees", err != "", err)
        finally:
            bt.REPO_ROOT = real_repo_root
            if os.path.islink(broad_link):
                os.unlink(broad_link)
            shutil.rmtree(broad_cell_dir, ignore_errors=True)
        # [11] ensemble base-date check is pure.
        check("base-date check accepts the evidenced session",
              bt.check_ensemble_base_date(
                  "2025-06-30", "2025-06-30", "2025-06-30") == "")
        check("base-date check rejects an older base",
              bt.check_ensemble_base_date(
                  "2025-06-27", "2025-06-30", "2025-06-30") != "")
        check("base-date check rejects a missing base_date",
              bt.check_ensemble_base_date(
                  None, "2025-06-30", "2025-06-30") != "")

        series = synthetic_series(n=820, cutoff="2025-07-28")
        index = [{"date": r["date"],
                  "close": round(30000.0 + 2.0 * i, 4),
                  "open": 0, "high": 0, "low": 0, "volume": 0}
                 for i, r in enumerate(series)]

        # [10] a traversal ticker fails the cell before any work.
        cfg = _smoke_cfg(tmp + "-path", series, index)
        cfg["repeat_kronos"] = False
        res = bt.run_cell(FIXTURE_CUTOFF, "../../etc", cfg)
        check("traversal ticker fails the cell",
              res["status"] == "error"
              and "capture path" in (res.get("reason") or ""),
              "%s: %s" % (res["status"], res.get("reason", "")))
        check("traversal ticker writes nothing",
              not os.path.exists(os.path.join(
                  tmp + "-path", "backtest")))

        # [11] wiring: a June 27 ensemble base at the June 30
        # evidenced close (same price) must fail the cell — the
        # price guard alone would accept it.
        cfg = _smoke_cfg(tmp + "-stale", series, index)
        cfg["repeat_kronos"] = False
        real_run_ensemble = bt.run_ensemble

        def stale_ensemble(stage_dir, root, log, timeout=600):
            ens, err = real_run_ensemble(stage_dir, root, log, timeout)
            if ens is not None:
                ens = dict(ens)
                ens["base_date"] = "2025-06-27"
            return ens, err

        bt.run_ensemble = stale_ensemble
        try:
            res = bt.run_cell(FIXTURE_CUTOFF, FIXTURE_TICKER, cfg)
        finally:
            bt.run_ensemble = real_run_ensemble
        check("stale ensemble base_date fails the cell",
              res["status"] == "error"
              and "base_date" in (res.get("reason") or ""),
              "%s: %s" % (res["status"], res.get("reason", "")))
        check("stale-base cell publishes no capture",
              res.get("capture_dir") is None)

        # [12] a realised file labelled for another ticker (or
        # cutoff) must never be published as this cell's returns.
        cfg_ok = _smoke_cfg(tmp + "-ok", series, index)
        cfg_ok["repeat_kronos"] = False
        res_ok = bt.run_cell(FIXTURE_CUTOFF, FIXTURE_TICKER, cfg_ok)
        check("baseline cell ok for realised-file tests",
              res_ok["status"] == "ok",
              "%s: %s" % (res_ok["status"], res_ok.get("reason", "")))
        if res_ok["status"] == "ok":
            good = json.load(open(os.path.join(
                res_ok["capture_dir"], "realised.json"),
                encoding="utf-8"))
            for label, mutate in (
                    ("wrong ticker",
                     lambda d: d.update(ticker="ETEL.CA")),
                    ("wrong cutoff",
                     lambda d: d.update(cutoff="2025-03-31"))):
                bad = dict(good)
                mutate(bad)
                slug = label.replace(" ", "-")
                bad_path = os.path.join(tmp, "realised-%s.json" % slug)
                json.dump(bad, open(bad_path, "w"), indent=1)
                cfg_bad = _smoke_cfg(tmp + "-bad-" + slug,
                                     series, index)
                cfg_bad["repeat_kronos"] = False
                cfg_bad["realised_file"] = bad_path
                res_bad = bt.run_cell(FIXTURE_CUTOFF, FIXTURE_TICKER,
                                      cfg_bad)
                check("%s realised file fails the cell" % label,
                      res_bad["status"] == "error"
                      and "mismatch" in (res_bad.get("reason") or ""),
                      "%s: %s" % (res_bad["status"],
                                  res_bad.get("reason", "")))
                check("%s cell publishes no capture" % label,
                      res_bad.get("capture_dir") is None
                      and not os.path.exists(os.path.join(
                          tmp + "-bad-" + slug, "backtest",
                          FIXTURE_CUTOFF, FIXTURE_TICKER)))

        # [9] an exhausted index fetch records an explicit gap
        # and still publishes the matured stock capture.
        def fetch_no_index(ticker):
            if str(ticker).startswith("^"):
                raise RuntimeError("Yahoo chart error for ^EGX30: 429")
            return list(series), [], True

        cfg_idx = _smoke_cfg(tmp + "-idx", series, index)
        cfg_idx["repeat_kronos"] = False
        cfg_idx["fetcher"] = fetch_no_index
        res_idx = bt.run_cell(FIXTURE_CUTOFF, FIXTURE_TICKER, cfg_idx)
        check("index fetch failure still publishes the stock capture",
              res_idx["status"] == "ok",
              "%s: %s" % (res_idx["status"], res_idx.get("reason", "")))
        if res_idx["status"] == "ok":
            rj = json.load(open(os.path.join(
                res_idx["capture_dir"], "realised.json"),
                encoding="utf-8"))
            check("index-gap capture records the gap",
                  bool(rj.get("index_gap")), str(rj.get("index_gap")))
            check("index-gap capture has no index sessions",
                  rj.get("index_sessions") == [])

        # [6] an index fetch that SUCCEEDS but has no usable
        # close on/before the first stock session must take the
        # same index_gap path as a fetch failure — the stock
        # capture is preserved, not skipped with it.
        late_index = [r for r in index
                      if r["date"] > "2025-07-01"]

        def fetch_late_index(ticker):
            if str(ticker).startswith("^"):
                return list(late_index), [], True
            return list(series), [], True

        cfg_late = _smoke_cfg(tmp + "-late", series, index)
        cfg_late["repeat_kronos"] = False
        cfg_late["fetcher"] = fetch_late_index
        res_late = bt.run_cell(FIXTURE_CUTOFF, FIXTURE_TICKER,
                               cfg_late)
        check("index with no usable close still publishes the "
              "stock capture",
              res_late["status"] == "ok",
              "%s: %s" % (res_late["status"],
                          res_late.get("reason", "")))
        if res_late["status"] == "ok":
            rj = json.load(open(os.path.join(
                res_late["capture_dir"], "realised.json"),
                encoding="utf-8"))
            check("late-index capture records the gap",
                  bool(rj.get("index_gap")), str(rj.get("index_gap")))
            check("late-index capture has no index sessions",
                  rj.get("index_sessions") == [])
            check("late-index capture has no index base",
                  rj.get("index_base_close") is None)

        # [8] a realised fetch that cannot verify the events feed
        # (unavailable on the re-fetch, or dropping records)
        # skips the cell instead of publishing an empty window.
        calls = {"n": 0}

        def fetch_flaky_events(ticker):
            if str(ticker).startswith("^"):
                return list(index), [], True
            calls["n"] += 1
            ok = calls["n"] == 1  # gate fetch fine, realised not
            return list(series), [], ok

        cfg_ev = _smoke_cfg(tmp + "-ev", series, index)
        cfg_ev["repeat_kronos"] = False
        cfg_ev["fetcher"] = fetch_flaky_events
        res_ev = bt.run_cell(FIXTURE_CUTOFF, FIXTURE_TICKER, cfg_ev)
        check("unverifiable realised events skip the cell",
              res_ev["status"] == "skipped"
              and "not verifiable" in (res_ev.get("reason") or ""),
              "%s: %s" % (res_ev["status"], res_ev.get("reason", "")))
        check("unverified-events cell publishes no capture",
              res_ev.get("capture_dir") is None)

        calls2 = {"n": 0}

        def fetch_dropped_events(ticker):
            if str(ticker).startswith("^"):
                return list(index), [], True
            calls2["n"] += 1
            if calls2["n"] == 1:
                return list(series), [], True
            return list(series), [], False, \
                "1 event record(s) unparseable and dropped"

        cfg_ev2 = _smoke_cfg(tmp + "-ev2", series, index)
        cfg_ev2["repeat_kronos"] = False
        cfg_ev2["fetcher"] = fetch_dropped_events
        res_ev2 = bt.run_cell(FIXTURE_CUTOFF, FIXTURE_TICKER, cfg_ev2)
        check("dropped realised events skip the cell",
              res_ev2["status"] == "skipped"
              and "not verifiable" in (res_ev2.get("reason") or ""),
              "%s: %s" % (res_ev2["status"], res_ev2.get("reason", "")))

        # [13] a rerun republishes the whole capture as one unit:
        # the second run's capture is complete, its manifest
        # hashes match, and no staging/backup dirs are left.
        cfg_re = _smoke_cfg(tmp + "-re", series, index)
        cfg_re["repeat_kronos"] = False
        res_a = bt.run_cell(FIXTURE_CUTOFF, FIXTURE_TICKER, cfg_re)
        res_b = bt.run_cell(FIXTURE_CUTOFF, FIXTURE_TICKER, cfg_re)
        check("rerun cell ok",
              res_a["status"] == "ok" and res_b["status"] == "ok",
              "%s / %s" % (res_a["status"], res_b["status"]))
        if res_b["status"] == "ok":
            cap = res_b["capture_dir"]
            man = json.load(open(os.path.join(cap, "manifest.json"),
                                 encoding="utf-8"))
            check("rerun manifest hashes match",
                  all(os.path.exists(os.path.join(cap, rel))
                      and bt.sha256_file(os.path.join(cap, rel)) == sha
                      for rel, sha in man["files"].items()))
            leftovers = [d for d in os.listdir(os.path.join(
                tmp + "-re", "backtest", FIXTURE_CUTOFF))
                if ".tmp-" in d or ".old-" in d]
            check("rerun leaves no staging/backup dirs",
                  leftovers == [], str(leftovers))

        # [7] a rerun that fails AFTER staging its publish dir
        # (hashing here) must not leave the partial copy behind:
        # the previous complete capture stays readable, and no
        # .tmp- dir accumulates for the next retry to trip over.
        cfg_hash = _smoke_cfg(tmp + "-hash", series, index)
        cfg_hash["repeat_kronos"] = False
        res_h0 = bt.run_cell(FIXTURE_CUTOFF, FIXTURE_TICKER, cfg_hash)
        check("hash-failure test baseline cell ok",
              res_h0["status"] == "ok",
              "%s: %s" % (res_h0["status"], res_h0.get("reason", "")))
        if res_h0["status"] == "ok":
            cap_h = res_h0["capture_dir"]
            man_h0 = json.load(open(os.path.join(
                cap_h, "manifest.json"), encoding="utf-8"))
            real_sha = bt.sha256_file

            def boom_sha(path):
                raise RuntimeError("hashing failed for the test")

            bt.sha256_file = boom_sha
            try:
                bt.run_cell(FIXTURE_CUTOFF, FIXTURE_TICKER, cfg_hash)
                raised = False
            except RuntimeError:
                raised = True
            finally:
                bt.sha256_file = real_sha
            check("hash failure propagates out of the cell",
                  raised)
            leftovers = [d for d in os.listdir(os.path.join(
                tmp + "-hash", "backtest", FIXTURE_CUTOFF))
                if ".tmp-" in d or ".old-" in d]
            check("failed rerun leaves no partial publish dir",
                  leftovers == [], str(leftovers))
            man_h1 = json.load(open(os.path.join(
                cap_h, "manifest.json"), encoding="utf-8"))
            check("failed rerun keeps the previous capture",
                  man_h1 == man_h0)
    finally:
        for suffix in ("", "-path", "-stale", "-ok", "-bad-wrong-ticker",
                       "-bad-wrong-cutoff", "-idx", "-ev", "-ev2", "-re",
                       "-late", "-hash"):
            shutil.rmtree(tmp + suffix, ignore_errors=True)


def test_runner_skip_classification_in_cell():
    print("== runner min-rows skip inside a cell ==")
    bt = load_module(os.path.join(HERE, "backtest.py"), "backtest")
    tmp = tempfile.mkdtemp(prefix="bt436-skip-")
    try:
        # 800 sessions before the cutoff: warm-up passes, but the
        # talib stub is told to demand 900 — its refusal must come
        # back as skipped-with-reason, not an error.
        series = synthetic_series(n=820, cutoff="2025-07-28")
        index = [{"date": r["date"], "close": 30000.0,
                  "open": 0, "high": 0, "low": 0, "volume": 0}
                 for r in series]
        os.environ["BT436_TALIB_MIN_ROWS"] = "900"
        cfg = _smoke_cfg(tmp, series, index)
        cfg["repeat_kronos"] = False
        res = bt.run_cell(FIXTURE_CUTOFF, FIXTURE_TICKER, cfg)
        check("talib min-rows refusal is a cell skip",
              res["status"] == "skipped"
              and "minimum-rows" in (res.get("reason") or ""),
              "%s: %s" % (res["status"], res.get("reason", "")))
    finally:
        os.environ.pop("BT436_TALIB_MIN_ROWS", None)
        shutil.rmtree(tmp, ignore_errors=True)


# --------------------------------------------------------------------------
# Scorer
# --------------------------------------------------------------------------
def _fixture_capture(tmp):
    """A capture dir built from the 2-family fixture ensemble plus
    hand-set realised closes: day +1.00%, week +2.00%, month
    -1.00% vs the C close; index +0.50% / +1.00% / +0.50%."""
    stage = os.path.join(tmp, "stage")
    build_fixture_stage(stage)
    ens = run_ensemble(stage, two_family=True)
    assert ens is not None
    base = ens["base_price"]
    cap = os.path.join(tmp, "backtest", FIXTURE_CUTOFF, FIXTURE_TICKER)
    os.makedirs(os.path.join(cap, "digest"), exist_ok=True)
    os.makedirs(os.path.join(cap, "collected/kronos"), exist_ok=True)
    shutil.copy(os.path.join(stage, "digest/ensemble.json"),
                os.path.join(cap, "digest/ensemble.json"))
    shutil.copy(os.path.join(stage, "collected/kronos/forecast.csv"),
                os.path.join(cap, "collected/kronos/forecast.csv"))
    series = synthetic_series()
    after = []
    c = date.fromisoformat(FIXTURE_CUTOFF)
    d = c
    moves = {1: 0.010, 5: 0.020, 14: -0.010}
    for i in range(1, 15):
        d += timedelta(days=1)
        while d.weekday() >= 5:
            d += timedelta(days=1)
        mv = moves.get(i, 0.002 * (i % 3 - 1))
        after.append({"date": d.isoformat(),
                      "close": round(base * (1 + mv), 4)})
    realised = {"ticker": FIXTURE_TICKER, "cutoff": FIXTURE_CUTOFF,
                "base_close": base, "base_date": FIXTURE_CUTOFF,
                "sessions": after, "maturity_date": after[-1]["date"],
                "index_ticker": "^EGX30",
                "index_base_close": 30000.0,
                "index_sessions": [
                    {"date": s["date"],
                     "close": round(30000.0 * (1 + mv), 2),
                     "exact": True}
                    for s, mv in zip(
                        after,
                        [0.005 if i == 1 else 0.010 if i == 5
                         else 0.005 if i == 14 else 0.001
                         for i in range(1, 15)])],
                "actions": [], "splits": [],
                "fetched_at": FIXTURE_CUTOFF}
    json.dump(realised, open(os.path.join(cap, "realised.json"), "w"),
              indent=1)
    # A complete capture carries a manifest (the scorer ignores
    # captures without one — a failed rerun's staging).
    manifest = {"tool": "walkforward-backtest", "version": 1,
                "issue": 436, "ticker": FIXTURE_TICKER,
                "cutoff": FIXTURE_CUTOFF, "status": "ok", "files": {}}
    json.dump(manifest, open(os.path.join(cap, "manifest.json"), "w"),
              indent=1)
    return cap, ens, base, after


def test_scorer():
    print("== scorer ==")
    sc = load_module(os.path.join(HERE, "backtest_score.py"),
                     "backtest_score")
    bf = load_module(os.path.join(HERE, "benchmark_freeze.py"),
                     "benchmark_freeze")
    tmp = tempfile.mkdtemp(prefix="bt436-score-")
    try:
        cap, ens, base, after = _fixture_capture(tmp)
        rows, gaps = sc.score_capture(cap)
        check("scorer gaps empty", gaps == [], "; ".join(gaps))
        check("scorer 15 rows (5 entrants x 3 horizons)",
              len(rows) == 15, "got %d" % len(rows))
        check("scorer all matured",
              all(r["status"] == "matured" for r in rows),
              str([(r["entrant"], r["horizon"], r["status"])
                   for r in rows if r["status"] != "matured"]))
        by = {(r["entrant"], r["horizon"]): r for r in rows}
        # Ensemble day: predicted flat +0.10%, realised +1.00%.
        ed = by[("2-family-ensemble", "day")]
        check("ensemble day expected 0.10",
              ed["expected_move_pct"] == 0.10,
              "got %r" % ed["expected_move_pct"])
        check("ensemble day realised +1.00",
              ed["realized_move_pct"] == 1.00,
              "got %r" % ed["realized_move_pct"])
        check("ensemble day miss (flat vs up)",
              ed["direction_hit"] is False)
        check("ensemble day error 0.90pp",
              ed["move_error_pp"] == 0.90,
              "got %r" % ed["move_error_pp"])
        check("ensemble day sessions scored 1",
              ed["sessions"] == 1)
        # Kronos-alone day: first forecast bar vs base (+0.10%).
        kd = by[("kronos-alone", "day")]
        check("kronos-alone day expected 0.10",
              kd["expected_move_pct"] == 0.10,
              "got %r" % kd["expected_move_pct"])
        # Technicals-alone day: .4 * 0.6 * 1.28 * vol_h, vol_h
        # from the ensemble's own emitted field.
        td = by[("family-technicals", "day")]
        vol_h = (ens["horizons"]["day"]["vol_h_pct"] or 0) / 100.0
        want = round(0.4 * 0.6 * (1.28 * vol_h) * 100, 2)
        check("technicals-alone day expected matches combine",
              td["expected_move_pct"] == want,
              "got %r want %r" % (td["expected_move_pct"], want))
        # Buy-and-hold day: flat 0, realised +1.00% -> miss, MAE 1.
        bd = by[("buy-and-hold", "day")]
        check("buy-and-hold day flat 0",
              bd["expected_move_pct"] == 0.0
              and bd["direction"] == "flat")
        check("buy-and-hold day miss", bd["direction_hit"] is False)
        check("buy-and-hold day error 1.00pp",
              bd["move_error_pp"] == 1.00)
        # Index baseline day: scored on the index series (+0.50%
        # realised) -> flat prediction hits (flat band 0.75%).
        idd = by[("index-baseline", "day")]
        check("index-baseline day realised +0.50",
              idd["realized_move_pct"] == 0.50,
              "got %r" % idd["realized_move_pct"])
        check("index-baseline day hit (flat in band)",
              idd["direction_hit"] is True)
        check("index-baseline day error 0.50pp",
              idd["move_error_pp"] == 0.50)
        # Cross-check the entrant blocks against the freeze
        # itself on the identical fixture inputs.
        bench_dir = os.path.join(tmp, "benchmark")
        bf.BENCH_DIR = bench_dir
        digest = json.load(open(os.path.join(
            tmp, "stage", "digest/digest.json"), encoding="utf-8"))
        kronos, first_date = sc.read_kronos_path(
            os.path.join(cap, "collected/kronos/forecast.csv"))
        kronos_r, rescale = bf.rescale_kronos(kronos, ens)
        mine = sc.build_entrants(ens, kronos, first_date)
        # Technicals-alone mirrors freeze_family_alone.
        st = bf.freeze_family_alone(
            ens, digest, "technicals", kronos_r, first_date, rescale, {})
        check("freeze family-technicals present", st == "present")
        frozen = json.load(open(os.path.join(
            bench_dir, "family-technicals.json"), encoding="utf-8"))
        for h in ("day", "week", "month"):
            fh = frozen["horizons"][h]
            mh = mine["family-technicals"][h]
            check("freeze cross-check technicals %s expected" % h,
                  mh["expected_move_pct"] == fh["expected_move_pct"],
                  "mine %r freeze %r"
                  % (mh["expected_move_pct"], fh["expected_move_pct"]))
            check("freeze cross-check technicals %s direction" % h,
                  mh["direction"] == fh["direction"])
            check("freeze cross-check technicals %s range" % h,
                  mh["range_low_pct"] == fh["range_low_pct"]
                  and mh["range_high_pct"] == fh["range_high_pct"])
        # Kronos-alone mirrors freeze_kronos_alone.
        st = bf.freeze_kronos_alone(
            ens, digest, kronos_r, first_date, rescale, {})
        check("freeze kronos-alone present", st == "present")
        frozen = json.load(open(os.path.join(
            bench_dir, "kronos-alone.json"), encoding="utf-8"))
        for h in ("day", "week", "month"):
            fh = frozen["horizons"][h]
            mh = mine["kronos-alone"][h]
            check("freeze cross-check kronos-alone %s expected" % h,
                  mh["expected_move_pct"] == fh["expected_move_pct"],
                  "mine %r freeze %r"
                  % (mh["expected_move_pct"], fh["expected_move_pct"]))
            check("freeze cross-check kronos-alone %s range" % h,
                  mh["range_low_pct"] == fh["range_low_pct"]
                  and mh["range_high_pct"] == fh["range_high_pct"])
        st = bf.freeze_buy_and_hold(ens, digest, {})
        check("freeze buy-and-hold present", st == "present")
        frozen = json.load(open(os.path.join(
            bench_dir, "buy-and-hold.json"), encoding="utf-8"))
        for h in ("day", "week", "month"):
            check("freeze cross-check buy-and-hold %s range" % h,
                  mine["buy-and-hold"][h]["range_low_pct"]
                  == frozen["horizons"][h]["range_low_pct"]
                  and mine["buy-and-hold"][h]["range_high_pct"]
                  == frozen["horizons"][h]["range_high_pct"])
        # Full summary: warning + exclusions present, cells n=1.
        doc, md = sc.score_all(os.path.join(tmp, "backtest"))
        check("summary tool", doc["tool"] == "walkforward-backtest")
        check("summary 15 forecasts",
              doc["counts"]["forecasts"] == 15)
        check("summary no quality claim at n=1",
              all(not doc["by_entrant"][e][h]["quality_claim"]
                  for e in sc.ENTRANTS for h in ("day", "week", "month")))
        check("md carries flattery warning",
              sc.FLATTERY_WARNING in md)
        check("md carries exclusion statement",
              sc.EXCLUSION_STATEMENT in md)
        check("md carries no-claim note", "n < 10" in md)
        # Separation guard: ledger.py never mentions the backtest.
        src = open(os.path.join(HERE, "ledger.py"),
                   encoding="utf-8").read()
        check("ledger.py never reads backtest files",
              "backtest" not in src.lower())
        # An explicit index gap: the stock capture still scores
        # (12 rows — the 4 stock entrants), but no index-baseline
        # rows are emitted and the gap is recorded.
        cap2 = os.path.join(tmp, "backtest2", FIXTURE_CUTOFF,
                            FIXTURE_TICKER)
        shutil.copytree(cap, cap2)
        r2 = json.load(open(os.path.join(cap2, "realised.json"),
                            encoding="utf-8"))
        r2["index_gap"] = "index fetch failed: Yahoo chart error"
        r2["index_base_close"] = None
        r2["index_sessions"] = []
        json.dump(r2, open(os.path.join(cap2, "realised.json"), "w"),
                  indent=1)
        rows2, gaps2 = sc.score_capture(cap2)
        check("index-gap capture scores 12 stock rows",
              len(rows2) == 12, "got %d" % len(rows2))
        check("index-gap capture emits no index-baseline rows",
              all(r["entrant"] != "index-baseline" for r in rows2))
        check("index-gap capture records the gap",
              any("index-baseline unavailable" in g for g in gaps2),
              "; ".join(gaps2))
        # A capture without a manifest is incomplete and never
        # scored, however valid its other files are.
        os.remove(os.path.join(cap2, "manifest.json"))
        rows3, gaps3 = sc.score_capture(cap2)
        check("manifest-less capture scores nothing",
              rows3 == [] and any("no manifest.json" in g
                                  for g in gaps3),
              "; ".join(gaps3))
        # [2] a missing index base with NO index_gap recorded:
        # the producer wrote index_base_close None (index fetch
        # returned no bar on/before the cutoff). The scorer must
        # take the index-gap path — 12 stock rows, no
        # index-baseline rows — not build index rows with a None
        # base that crash ledger.score_forecast (TypeError).
        cap3 = os.path.join(tmp, "backtest3", FIXTURE_CUTOFF,
                            FIXTURE_TICKER)
        shutil.copytree(cap, cap3)
        r3 = json.load(open(os.path.join(cap3, "realised.json"),
                            encoding="utf-8"))
        r3["index_base_close"] = None
        json.dump(r3, open(os.path.join(cap3, "realised.json"), "w"),
                  indent=1)
        crashed = None
        try:
            rows4, gaps4 = sc.score_capture(cap3)
        except TypeError as e:
            crashed = e
            rows4, gaps4 = [], []
        check("missing index base does not crash the scorer",
              crashed is None, "TypeError: %s" % crashed)
        check("missing index base scores 12 stock rows",
              len(rows4) == 12, "got %d" % len(rows4))
        check("missing index base emits no index-baseline rows",
              all(r["entrant"] != "index-baseline" for r in rows4))
        check("missing index base records the gap",
              any("index-baseline unavailable" in g for g in gaps4),
              "; ".join(gaps4))
        # [7] an EMPTY-STRING index base (an offline realised
        # file can carry one) must take the same index-gap path:
        # float("") raises before the gap check is reached and
        # aborts the whole capture, losing the stock rows.
        cap5 = os.path.join(tmp, "backtest5", FIXTURE_CUTOFF,
                            FIXTURE_TICKER)
        shutil.copytree(cap, cap5)
        r5 = json.load(open(os.path.join(cap5, "realised.json"),
                            encoding="utf-8"))
        r5["index_base_close"] = ""
        json.dump(r5, open(os.path.join(cap5, "realised.json"), "w"),
                  indent=1)
        crashed = None
        try:
            rows6, gaps6 = sc.score_capture(cap5)
        except Exception as e:  # noqa: BLE001 - any raise is the bug
            crashed = e
            rows6, gaps6 = [], []
        check("empty-string index base does not crash the scorer",
              crashed is None,
              "%s: %s" % (type(crashed).__name__, crashed))
        check("empty-string index base scores 12 stock rows",
              len(rows6) == 12, "got %d" % len(rows6))
        check("empty-string index base emits no index rows",
              all(r["entrant"] != "index-baseline" for r in rows6))
        check("empty-string index base records the gap",
              any("index-baseline unavailable" in g for g in gaps6),
              "; ".join(gaps6))
        # [3] one capture reached by two paths must count once:
        # a cutoff dir aliased onto the real one is the same
        # capture under a different sweep key, not a second
        # observation toward the quality threshold.
        alias_root = os.path.join(tmp, "backtest-alias")
        shutil.copytree(cap, os.path.join(
            alias_root, FIXTURE_CUTOFF, FIXTURE_TICKER))
        os.makedirs(os.path.join(alias_root, "2025-06-30-alias"),
                    exist_ok=True)
        os.symlink(os.path.join(alias_root, FIXTURE_CUTOFF,
                                FIXTURE_TICKER),
                   os.path.join(alias_root, "2025-06-30-alias",
                                FIXTURE_TICKER))
        doc_a, _md_a = sc.score_all(alias_root)
        check("aliased capture counted once",
              doc_a["counts"]["forecasts"] == 15,
              "got %d" % doc_a["counts"]["forecasts"])
        # Assert the dedup-specific message, not the substring
        # "alias": the alias PATH itself contains "alias", so
        # the old check passed even with dedup removed (the
        # path-identity check still rejects the alias and the
        # count stays 15). The dedup message is the only
        # evidence dedup itself ran.
        check("alias reported with the dedup message",
              any("aliased path) — counted once" in g
                  for g in doc_a["gaps"]),
              "; ".join(doc_a["gaps"]))
        # [1] an alias that sorts BEFORE the valid capture must
        # not claim it: discovery validates the candidate
        # against its manifest before dedup, so the alias (its
        # path cutoff != the manifest cutoff) is rejected
        # without claiming the canonical path, and the valid
        # capture still scores its 15 forecasts.
        early_root = os.path.join(tmp, "backtest-alias-early")
        shutil.copytree(cap, os.path.join(
            early_root, FIXTURE_CUTOFF, FIXTURE_TICKER))
        os.makedirs(os.path.join(early_root, "2025-03-31"),
                    exist_ok=True)
        os.symlink(os.path.join(early_root, FIXTURE_CUTOFF,
                                FIXTURE_TICKER),
                   os.path.join(early_root, "2025-03-31",
                                FIXTURE_TICKER))
        doc_e, _md_e = sc.score_all(early_root)
        check("earlier-sorting alias does not claim the capture",
              doc_e["counts"]["forecasts"] == 15,
              "got %d" % doc_e["counts"]["forecasts"])
        check("earlier-sorting alias reported as a gap",
              any("2025-03-31" in g for g in doc_e["gaps"]),
              "; ".join(doc_e["gaps"]))
        # A manifest claiming a different cell than its path
        # (copied capture, wrong cutoff dir) is never scored as
        # the path's cell.
        cap4 = os.path.join(tmp, "backtest4", "2025-03-31",
                            FIXTURE_TICKER)
        shutil.copytree(cap, cap4)
        rows5, gaps5 = sc.score_capture(cap4)
        check("manifest cutoff mismatch scores nothing",
              rows5 == [] and any("manifest" in g for g in gaps5),
              "; ".join(gaps5))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_realised_dropped_close():
    print("== realised dropped close (horizons must not shift) ==")
    bt = load_module(os.path.join(HERE, "backtest.py"), "backtest")
    gate = load_module(os.path.join(HERE, "backtest_gate.py"),
                       "backtest_gate")
    import datetime as _dt
    import urllib.request as _urlreq

    # Mon-Fri bars 2025-06-23 .. 2025-07-25; the cutoff is
    # 2025-06-30, so the first realised session is 2025-07-01
    # and the 14th is 2025-07-18.
    days = []
    d = date(2025, 6, 23)
    while d <= date(2025, 7, 25):
        if d.weekday() < 5:
            days.append(d)
        d += timedelta(days=1)

    def _ts(dd):
        return int(_dt.datetime(dd.year, dd.month, dd.day,
                                tzinfo=_dt.timezone.utc).timestamp())

    def _payload(null_date=None, index=False):
        closes = []
        for i, dd in enumerate(days):
            if null_date is not None and dd.isoformat() == null_date:
                closes.append(None)
            elif index:
                closes.append(30000.0 + 10.0 * i)
            else:
                closes.append(100.0 + i)
        body = {"timestamp": [_ts(dd) for dd in days],
                "indicators": {"quote": [{"close": closes}]},
                "meta": {"exchangeTimezoneName": "Africa/Cairo"}}
        if not index:
            body["events"] = {"dividend": {
                str(_ts(date(2025, 6, 29))): {
                    "amount": 1.0, "date": _ts(date(2025, 6, 29))}}}
        return {"chart": {"error": None, "result": [body]}}

    class _FakeResp:
        def __init__(self, payload):
            self._data = json.dumps(payload).encode("utf-8")

        def read(self):
            return self._data

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    holder = {"null_date": None, "index_null_date": None}

    def _fake_urlopen(req, timeout=30):
        if "EGX30" in req.full_url:
            return _FakeResp(_payload(
                null_date=holder["index_null_date"], index=True))
        return _FakeResp(_payload(null_date=holder["null_date"]))

    real_urlopen = _urlreq.urlopen
    try:
        _urlreq.urlopen = _fake_urlopen
        # Control: a clean feed publishes the true first 14
        # sessions, starting 2025-07-01.
        holder["null_date"] = None
        ok_realised, ok_err = bt.fetch_realised(
            FIXTURE_TICKER, FIXTURE_CUTOFF, fetcher=gate.fetch_chart)
        check("clean feed publishes a realised capture",
              ok_realised is not None, ok_err)
        if ok_realised is not None:
            check("clean feed starts at the first session",
                  ok_realised["sessions"][0]["date"] == "2025-07-01",
                  "got %r" % (ok_realised["sessions"][0],))
            check("clean feed maturity is the 14th session",
                  ok_realised["maturity_date"] == "2025-07-18",
                  "got %r" % (ok_realised["maturity_date"],))
        # A null close on the FIRST realised session: the bar
        # existed but its close is unusable. Counting the next
        # available close as session 1 would score the day
        # horizon on the wrong day's move — the cell must be
        # blocked, not published shifted.
        holder["null_date"] = "2025-07-01"
        bad_realised, bad_err = bt.fetch_realised(
            FIXTURE_TICKER, FIXTURE_CUTOFF, fetcher=gate.fetch_chart)
        check("dropped first realised close blocks the cell",
              bad_realised is None,
              "published sessions start %r"
              % ((bad_realised or {}).get("sessions", [{}])[0],))
        check("block reason names the missing session",
              bad_realised is None and "2025-07-01" in bad_err,
              "err=%r" % (bad_err,))
        # A null close AFTER the 14-session window does not
        # touch any scored horizon: the capture still publishes
        # with the true first 14 sessions.
        holder["null_date"] = "2025-07-23"
        late_realised, late_err = bt.fetch_realised(
            FIXTURE_TICKER, FIXTURE_CUTOFF, fetcher=gate.fetch_chart)
        check("dropped close past the window still publishes",
              late_realised is not None, late_err)
        if late_realised is not None:
            check("past-window drop keeps the true sessions",
                  late_realised["sessions"][0]["date"] == "2025-07-01"
                  and late_realised["maturity_date"] == "2025-07-18",
                  "got %r .. %r" % (late_realised["sessions"][0],
                                    late_realised["maturity_date"]))
        # Index side: a dropped index close on a realised
        # session date is NOT a non-session date — the index
        # traded, its close is just unusable. Carrying the
        # prior close forward would fabricate that session's
        # index return; the capture must record an index gap
        # and clear the index evidence instead, keeping the
        # matured stock capture.
        holder["null_date"] = None
        holder["index_null_date"] = "2025-07-01"
        idx_realised, idx_err = bt.fetch_realised(
            FIXTURE_TICKER, FIXTURE_CUTOFF, fetcher=gate.fetch_chart)
        check("dropped index close keeps the stock capture",
              idx_realised is not None, idx_err)
        if idx_realised is not None:
            check("dropped index close records an index gap",
                  bool(idx_realised.get("index_gap"))
                  and "2025-07-01" in idx_realised["index_gap"],
                  "gap=%r" % (idx_realised.get("index_gap"),))
            check("dropped index close clears index evidence",
                  idx_realised.get("index_sessions") == []
                  and idx_realised.get("index_base_close") is None,
                  "sessions=%r base=%r"
                  % (idx_realised.get("index_sessions"),
                     idx_realised.get("index_base_close")))
        # The cutoff date itself: if the index bar ON the
        # cutoff was dropped, the last earlier index close is
        # adopted as index_base_close — but the scorer anchors
        # that base AT the cutoff, so every index return would
        # be measured from the wrong close with no gap
        # recorded. The gap must be recorded and the base
        # cleared, exactly as for a dropped session date.
        holder["index_null_date"] = "2025-06-30"
        base_idx, base_idx_err = bt.fetch_realised(
            FIXTURE_TICKER, FIXTURE_CUTOFF, fetcher=gate.fetch_chart)
        check("dropped cutoff index close keeps the stock capture",
              base_idx is not None, base_idx_err)
        if base_idx is not None:
            check("dropped cutoff index close records an index gap",
                  bool(base_idx.get("index_gap"))
                  and "2025-06-30" in base_idx["index_gap"],
                  "gap=%r" % (base_idx.get("index_gap"),))
            check("dropped cutoff index close clears the base",
                  base_idx.get("index_base_close") is None
                  and base_idx.get("index_sessions") == [],
                  "base=%r sessions=%r"
                  % (base_idx.get("index_base_close"),
                     base_idx.get("index_sessions")))
        # Control: a dropped index close AFTER the window
        # touches no scored session — no gap, full evidence.
        holder["index_null_date"] = "2025-07-23"
        late_idx, late_idx_err = bt.fetch_realised(
            FIXTURE_TICKER, FIXTURE_CUTOFF, fetcher=gate.fetch_chart)
        check("past-window index drop keeps the capture",
              late_idx is not None, late_idx_err)
        if late_idx is not None:
            check("past-window index drop records no gap",
                  late_idx.get("index_gap") is None
                  and len(late_idx.get("index_sessions") or []) == 14,
                  "gap=%r sessions=%r"
                  % (late_idx.get("index_gap"),
                     len(late_idx.get("index_sessions") or [])))
    finally:
        _urlreq.urlopen = real_urlopen


def test_realised_index_window():
    print("== realised index window (flat index = gap) ==")
    bt = load_module(os.path.join(HERE, "backtest.py"), "backtest")
    series = synthetic_series(n=820, cutoff="2025-07-28")
    index_full = [{"date": r["date"],
                   "close": round(30000.0 + 2.0 * i, 4)}
                  for i, r in enumerate(series)]
    # [3] an index feed ending AT the cutoff: every realised
    # session would carry the base close forward — a flat
    # index path scored as real index evidence. The capture
    # must record an index gap instead and keep the stock
    # sessions.
    index_flat = [r for r in index_full if r["date"] <= FIXTURE_CUTOFF]
    realised, err = bt.fetch_realised(
        FIXTURE_TICKER, FIXTURE_CUTOFF,
        fetcher=_stub_fetcher(series, index_flat))
    check("flat index feed still returns the stock capture",
          realised is not None, err)
    if realised is not None:
        check("flat index feed records an index gap",
              bool(realised.get("index_gap")),
              "gap=%r" % (realised.get("index_gap"),))
        check("flat index feed emits no index sessions",
              realised.get("index_sessions") == [],
              "got %r" % (realised.get("index_sessions"),))
        check("flat index feed keeps 14 stock sessions",
              len(realised.get("sessions") or []) == 14)
    # Control: an index trading through the window scores.
    realised2, err2 = bt.fetch_realised(
        FIXTURE_TICKER, FIXTURE_CUTOFF,
        fetcher=_stub_fetcher(series, index_full))
    check("live index feed returns a capture",
          realised2 is not None, err2)
    if realised2 is not None:
        check("live index feed has no index gap",
              realised2.get("index_gap") is None,
              "gap=%r" % (realised2.get("index_gap"),))
        check("live index feed emits 14 index sessions",
              len(realised2.get("index_sessions") or []) == 14)
    # A single in-window index close still counts as evidence:
    # the other sessions carry the latest observed close.
    after = [r for r in series if r["date"] > FIXTURE_CUTOFF]
    index_sparse = index_flat + [{"date": after[4]["date"],
                                  "close": 31000.0}]
    realised3, err3 = bt.fetch_realised(
        FIXTURE_TICKER, FIXTURE_CUTOFF,
        fetcher=_stub_fetcher(series, index_sparse))
    check("sparse index feed returns a capture",
          realised3 is not None, err3)
    if realised3 is not None:
        check("sparse index feed has no index gap",
              realised3.get("index_gap") is None,
              "gap=%r" % (realised3.get("index_gap"),))
        check("sparse index feed emits 14 index sessions",
              len(realised3.get("index_sessions") or []) == 14)


def run_backtest_checks(verbose=True):
    """Entry point for harness_issue109.py --backtest. Returns
    (passed, failed, failures)."""
    test_ensemble_two_family()
    test_gate()
    test_warmup_and_failure_classification()
    test_audit()
    test_cell_guards()
    test_realised_index_window()
    test_realised_dropped_close()
    test_smoke_and_determinism()
    test_runner_skip_classification_in_cell()
    test_scorer()
    return CHECKS["pass"], CHECKS["fail"], list(FAILURES)


def main(argv=None):
    run_backtest_checks()
    print("CHECKS pass=%d fail=%d" % (CHECKS["pass"], CHECKS["fail"]))
    if FAILURES:
        print("FAILURES: %s" % ", ".join(FAILURES))
    return 0 if CHECKS["fail"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
