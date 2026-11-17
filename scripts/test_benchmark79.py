#!/usr/bin/env python3
"""Proof harness for issue #79 (forward quality benchmark).

Harness-first: FAILS on the pristine HEAD (no benchmark_freeze.py,
no ledger benchmark ingestion, no publisher benchmark validation)
and PASSES on the fixed tree. Stdlib only, no network — the ledger
runs against a synthetic fixture archive via patched fetch
functions, and the raw-LLM call path runs against a local stub HTTP
server.

Fixtures mirror the REAL archived sweep 141124 (16 Nov 2026, POUL.CA,
base 8.02, sigma 0.0677, risk shock) with its exact horizon values
and Kronos rows 0/4/20, and a synthetic ledger archive reproducing
the live matured set's structure (5 clean day rows + the 4
gap-flagged 15 Nov rows, realised -20.99% each).

Usage: python3 scripts/test_benchmark79.py
Exit 0 only when every test passes.
"""
import copy
import csv
import hashlib
import http.server
import io
import json
import math
import os
import re
import shutil
import socketserver
import subprocess
import sys
import tempfile
import threading
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)

FREEZE = os.path.join(SCRIPTS, "benchmark_freeze.py")
PROMPT = os.path.join(SCRIPTS, "benchmark_prompt_v1.txt")

RESULTS = []


def check(name, fn):
    try:
        fn()
    except Exception as e:
        RESULTS.append((name, False, f"{type(e).__name__}: {e}"))
        print(f"FAIL {name}: {type(e).__name__}: {e}")
        return
    RESULTS.append((name, True, ""))
    print(f"PASS {name}")


def approx(a, b, tol=0.01):
    assert a is not None and abs(a - b) <= tol, f"{a} != {b} (±{tol})"


# ---------------------------------------------------------------- fixtures

# Real 141124 Kronos dates (Sun-Thu sessions 2026-11-15..2026-12-13);
# rows 0/4/20 carry the real file's exact closes, the rest are
# plausible fills — the harness asserts only rows 0/4/20 + row 0's
# date.
KRONOS_DATES = ["2026-11-15", "2026-11-16", "2026-11-17", "2026-11-18",
                "2026-11-19", "2026-11-22", "2026-11-23", "2026-11-24",
                "2026-11-25", "2026-11-26", "2026-11-29", "2026-11-30",
                "2026-12-01", "2026-12-02", "2026-12-03", "2026-12-06",
                "2026-12-07", "2026-12-08", "2026-12-09", "2026-12-10",
                "2026-12-13"]
KRONOS_CLOSES = {0: (10.3096, 10.5824, 10.0952),
                 4: (9.8933, 10.5285, 9.8569),
                 20: (9.6256, 9.8781, 9.5086)}


def ensemble_141124():
    return {
        "tool": "forecast-ensemble", "version": 2, "ticker": "POUL.CA",
        "base_price": 8.02, "base_source": "egx-data/egxpy_poul.csv",
        "base_date": "2026-11-16",
        "price_crosscheck": {"status": "agree", "base_stale": False},
        "corporate_actions": [
            {"type": "dividend", "dps": 1.8999999998,
             "ex_date": "2026-11-16", "date_basis": "entitlement+1",
             "mechanical_pct": -23.69,
             "title": "dividend announcement"},
            {"type": "dividend", "dps": 1.89, "ex_date": None,
             "date_basis": None, "mechanical_pct": -23.57,
             "title": "press mention"},
            {"type": "dividend", "dps": 1.9, "ex_date": None,
             "date_basis": None, "mechanical_pct": -23.69,
             "title": "press mention"}],
        "kronos_ex_rescale": None,
        "sigma_daily": 0.0677, "sigma_source": "egx-data",
        "sessions_per_calendar_day": 0.66,
        "date": "2026-11-16",
        "risk": {"level": "shock", "conf_cap": 0.3, "price_mult": 0.5,
                 "flags": []},
        "family_scores": {"technicals": 0.297, "sentiment": -0.101,
                          "agent": None, "fundamentals": 0.4,
                          "price-forecast": 0.395},
        "horizons": {
            "day": {"direction": "up", "expected_move_pct": 18.71,
                    "range_low_pct": 2.82, "range_high_pct": 34.61,
                    "confidence": 0.3, "net_score": 0.457,
                    "families": {"technicals": 0.297,
                                 "sentiment": -0.101,
                                 "price-forecast": 1.0},
                    "horizon_short": False, "trading_sessions": 1},
            "week": {"direction": "up", "expected_move_pct": 16.73,
                     "range_low_pct": -11.04, "range_high_pct": 44.49,
                     "confidence": 0.3, "net_score": 0.452,
                     "families": {"technicals": 0.297,
                                  "sentiment": -0.101,
                                  "price-forecast": 0.996},
                     "horizon_short": False, "trading_sessions": 3},
            "month": {"direction": "up", "expected_move_pct": 16.36,
                      "range_low_pct": -35.85, "range_high_pct": 68.56,
                      "confidence": 0.3, "net_score": 0.335,
                      "families": {"technicals": 0.297,
                                   "sentiment": -0.101,
                                   "fundamentals": 0.4,
                                   "price-forecast": 0.395},
                      "horizon_short": False, "trading_sessions": 14}},
    }


def digest_141124():
    return {"job": "sweep-lite POUL.CA", "ticker": "POUL.CA",
            "date": "2026-11-16",
            "started": "2026-11-16T13:27:27+00:00",
            "finished": "2026-11-16T14:11:24+00:00",
            "results": [{"tool": "kronos", "status": "ok",
                         "summary": {"metrics": {
                             "forecast.csv_last_close": "9.6256"}}}]}


def write_json(path, doc):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1, ensure_ascii=False)


def make_sweep_dir(root, with_kronos=True, with_ensemble=True):
    """Actions-shaped sweep working dir mirroring 141124."""
    os.makedirs(os.path.join(root, "digest"), exist_ok=True)
    write_json(os.path.join(root, "digest", "digest.json"),
               digest_141124())
    with open(os.path.join(root, "digest", "digest.md"), "w",
              encoding="utf-8") as f:
        f.write("# 🐊 Borsagator digest — sweep-lite POUL.CA\n")
    if with_ensemble:
        write_json(os.path.join(root, "digest", "ensemble.json"),
                   ensemble_141124())
    if with_kronos:
        kdir = os.path.join(root, "collected", "kronos")
        os.makedirs(kdir, exist_ok=True)
        with open(os.path.join(kdir, "forecast.csv"), "w",
                  newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["date", "open", "high", "low", "close",
                        "volume", "amount"])
            for i, d in enumerate(KRONOS_DATES):
                c, h, l = KRONOS_CLOSES.get(i, (10.0 + 0.01 * i,
                                                10.3 + 0.01 * i,
                                                9.8 + 0.01 * i))
                w.writerow([d, f"{c - 0.19:.4f}", f"{h:.4f}",
                            f"{l:.4f}", f"{c:.4f}", "1000000.0",
                            "10000000.0"])
    # Price history for the raw-LLM prompt (last-10-closes input).
    import datetime as _dt
    edir = os.path.join(root, "collected", "egx-data")
    os.makedirs(edir, exist_ok=True)
    with open(os.path.join(edir, "egxpy_poul.csv"), "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Date", "Open", "High", "Low", "Close", "Volume"])
        day = _dt.date(2026, 10, 20)
        for _i in range(30):
            w.writerow([day.isoformat(), "10.0", "10.2", "9.9", "10.0",
                        "1000"])
            day += _dt.timedelta(days=1)
    return root


def clean_env(extra=None):
    env = dict(os.environ)
    env.pop("COHERE_API_KEY", None)
    env.pop("COHERE_API_URL", None)
    env.pop("GITHUB_RUN_ID", None)
    env.pop("BENCHMARK_RUN_ID", None)
    if extra:
        env.update(extra)
    return env


def run_freeze(sweep_dir, env=None):
    return subprocess.run(
        [sys.executable, FREEZE], cwd=sweep_dir,
        env=env if env is not None else clean_env(),
        capture_output=True, text=True, timeout=300)


def load_bench(sweep_dir, entrant):
    with open(os.path.join(sweep_dir, "benchmark", f"{entrant}.json"),
              encoding="utf-8") as f:
        return json.load(f)


def mask_replay(doc):
    d = copy.deepcopy(doc)
    d.pop("frozen_at", None)
    d.pop("inputs_sha256", None)
    return d


# ------------------------------------------------------- ledger fixtures

CLEAN_PRICE = [0.01, 0.005, 0.01, 0.005, 0.005]
CLEAN_TECH = [0.3, 0.25, 0.25, 0.24, 0.25]
CLEAN_SENT = [-0.02, -0.03, -0.02, -0.03, -0.02]
# Clean-only skill means: price -0.007, tech -0.258, sent +0.024 ->
# factors 0.993 / 0.742 / 1.024 (the #79 §9 exclude-variant values).
# Flagged rows (price 0.3435, tech 0.3, sent 0.1, realised -20.99%)
# would drag the keep-variant factors to ~0.843 / 0.725 / 1.009.


def _price_csv(root):
    closes = {}
    import datetime as _dt
    day = _dt.date(2026, 10, 20)
    for _ in range(30):
        closes[day.isoformat()] = 10.0
        day += _dt.timedelta(days=1)
    closes["2026-11-13"] = 9.804    # clean rows mature here: -1.96%
    closes["2026-11-15"] = 10.0
    closes["2026-11-16"] = 7.901    # flagged rows mature here: -20.99%
    closes["2026-11-17"] = 8.02
    closes["2026-11-18"] = 8.1
    edir = os.path.join(root, "collected", "egx-data")
    os.makedirs(edir, exist_ok=True)
    with open(os.path.join(edir, "egxpy_poul.csv"), "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Date", "Open", "High", "Low", "Close", "Volume"])
        for d in sorted(closes):
            w.writerow([d, closes[d], closes[d], closes[d], closes[d],
                        "1000"])


def _fixture_ensemble(as_of, base, expected, fams, actions,
                      sessions=1):
    return {
        "tool": "forecast-ensemble", "version": 2, "ticker": "POUL.CA",
        "base_price": base, "base_source": "egx-data/egxpy_poul.csv",
        "base_date": as_of,
        "price_crosscheck": {"status": "agree", "base_stale": False},
        "corporate_actions": actions, "kronos_ex_rescale": None,
        "sigma_daily": 0.02, "sessions_per_calendar_day": 0.714,
        "date": as_of,
        "risk": {"level": "none", "conf_cap": 0.6, "price_mult": 1.0,
                 "flags": []},
        "family_scores": dict(fams),
        "horizons": {
            "day": {"direction": "up", "expected_move_pct": expected,
                    "range_low_pct": -5.0, "range_high_pct": 5.0,
                    "confidence": 0.5,
                    "net_score": fams.get("price-forecast", 0.0),
                    "families": dict(fams),
                    "horizon_short": False,
                    "trading_sessions": sessions}}}


def make_ledger_archive(root, with_benchmark=True):
    """Synthetic archive tree: 5 clean + 4 flagged + 1 pending sweep.
    Mirrors the live matured set's structure (9 matured day rows,
    4 gap-flagged at -20.99%)."""
    sweeps = []
    for i in range(5):
        fams = {"price-forecast": CLEAN_PRICE[i],
                "technicals": CLEAN_TECH[i],
                "sentiment": CLEAN_SENT[i]}
        sweeps.append((f"sweeps/2026-11-12/12000{i}__clean-{i}__run100{i}",
                       "2026-11-12", 10.0, 0.5, fams, []))
    for i, exp in enumerate([1.22, 1.22, 1.21, 1.21]):
        fams = {"price-forecast": 0.3435, "technicals": 0.3,
                "sentiment": 0.1}
        actions = [{"type": "dividend", "dps": 1.9, "ex_date": None,
                    "entitlement_end": None, "mechanical_pct": -19.0}]
        sweeps.append((f"sweeps/2026-11-15/1200{i}__flagged-{i}__run200{i}",
                       "2026-11-15", 10.0, exp, fams, actions))
    fams = {"price-forecast": 0.5, "technicals": 0.2, "sentiment": 0.0}
    sweeps.append(("sweeps/2026-11-17/120000__later__run300",
                   "2026-11-17", 8.02, 1.0, fams, []))
    for path, as_of, base, exp, fams, actions in sweeps:
        sdir = os.path.join(root, path)
        os.makedirs(sdir, exist_ok=True)
        sessions = 5 if "later" in path else 1
        write_json(os.path.join(sdir, "ensemble.json"),
                   _fixture_ensemble(as_of, base, exp, fams, actions,
                                     sessions))
        write_json(os.path.join(sdir, "digest.json"),
                   {"job": "sweep-lite POUL.CA", "ticker": "POUL.CA",
                    "date": as_of, "results": []})
        _price_csv(sdir)
    if with_benchmark:
        # A family-technicals file mirroring clean-0's ensemble row
        # exactly (F5: identical scoring), plus a family-sentiment
        # file with extreme skill (F6/L1: a leak would move weights).
        c0 = "sweeps/2026-11-12/120000__clean-0__run1000"
        bdir = os.path.join(root, c0, "benchmark")
        os.makedirs(bdir, exist_ok=True)
        base_doc = {
            "tool": "benchmark-freeze", "version": 1,
            "entrant": "family-technicals", "status": "present",
            "ticker": "POUL.CA", "as_of": "2026-11-12",
            "sweep": c0, "base_price": 10.0,
            "base_source": "egx-data/egxpy_poul.csv",
            "base_date": "2026-11-12",
            "frozen_at": "2026-11-12T12:00:00+00:00",
            "inputs_sha256": {}, "derivation": "fixture mirror",
            "corporate_actions": [],
            "risk": {"level": "none", "conf_cap": 0.6,
                     "price_mult": 1.0},
            "sigma_daily": 0.02, "sessions_per_calendar_day": 0.714,
            "horizons": {
                "day": {"direction": "up", "expected_move_pct": 0.5,
                        "range_low_pct": -5.0, "range_high_pct": 5.0,
                        "confidence": 0.5, "net_score": 0.3,
                        "families": {"technicals": 0.3},
                        "trading_sessions": 1,
                        "horizon_short": False}}}
        write_json(os.path.join(bdir, "family-technicals.json"), base_doc)
        sent = copy.deepcopy(base_doc)
        sent["entrant"] = "family-sentiment"
        sent["horizons"]["day"] = {
            "direction": "up", "expected_move_pct": 5.0,
            "range_low_pct": -5.0, "range_high_pct": 15.0,
            "confidence": 0.5, "net_score": 1.0,
            "families": {"sentiment": 1.0},
            "trading_sessions": 1, "horizon_short": False}
        write_json(os.path.join(bdir, "family-sentiment.json"), sent)
        # Class B: one valid capture, one late filing (>48h after
        # as_of), one with no source timestamp — the latter two must
        # be rejected (F13).
        cbdir = os.path.join(root, c0, "benchmark", "class-b")
        os.makedirs(cbdir, exist_ok=True)
        write_json(os.path.join(cbdir, "acme.2026-11-12.json"),
                   {"competitor": "acme", "url": "https://example.invalid/acme",
                    "captured_at": "2026-11-12T10:00:00+00:00",
                    "capturer": "borsagator-cycle 2026-11-12",
                    "call": {"direction": "up", "target": 5.0,
                             "horizon": "day",
                             "verbatim": "acme calls POUL up 5%",
                             "source_type": "public-note",
                             "timestamp": "2026-11-12T09:00:00+00:00"}})
        write_json(os.path.join(cbdir, "late.2026-11-15.json"),
                   {"competitor": "late", "url": "https://example.invalid/late",
                    "captured_at": "2026-11-15T10:00:00+00:00",
                    "capturer": "borsagator-cycle 2026-11-15",
                    "call": {"direction": "up", "target": 5.0,
                             "horizon": "day",
                             "verbatim": "late filing",
                             "source_type": "public-note",
                             "timestamp": "2026-11-15T09:00:00+00:00"}})
        write_json(os.path.join(cbdir, "nots.2026-11-12.json"),
                   {"competitor": "nots", "url": "https://example.invalid/nots",
                    "captured_at": "2026-11-12T10:00:00+00:00",
                    "capturer": "borsagator-cycle 2026-11-12",
                    "call": {"direction": "up", "target": 5.0,
                             "horizon": "day",
                             "verbatim": "no source timestamp",
                             "source_type": "public-note"}})
    return root


def run_ledger_on_archive(archive_root, out_dir):
    """Run ledger.main with fetch patched to the local fixture tree.
    Returns (ledger_doc, weights_doc, benchmark_doc)."""
    import ledger as ledger_mod
    entries = []
    for dirpath, _dirs, names in os.walk(archive_root):
        for name in sorted(names):
            p = os.path.join(dirpath, name)
            rel = os.path.relpath(p, archive_root).replace(os.sep, "/")
            entries.append({"path": rel, "type": "blob",
                            "size": os.path.getsize(p)})
    commit = "fixturecommit00000000000000000000000000000000"
    tree = {"sha": "fixturetree00000000000000000000000000000000",
            "tree": sorted(entries, key=lambda e: e["path"]),
            "truncated": False}

    def fake_fetch_tree():
        return tree, commit, "fixture"

    def fake_fetch_text(url):
        marker = "/moos-labs/borsagator/" + commit + "/"
        assert marker in url, f"unexpected fetch URL: {url}"
        rel = urllib.parse.unquote(url.split(marker, 1)[1])
        with open(os.path.join(archive_root, rel),
                  encoding="utf-8") as f:
            return f.read()

    ledger_mod.fetch_tree = fake_fetch_tree
    ledger_mod.fetch_text = fake_fetch_text
    ledger_mod.WARNINGS.clear()
    ledger_mod.STATS["skipped_rows"] = 0
    old_argv = sys.argv
    sys.argv = ["ledger.py", out_dir]
    try:
        ledger_mod.main()
    finally:
        sys.argv = old_argv
    with open(os.path.join(out_dir, "ledger.json"),
              encoding="utf-8") as f:
        ledger_doc = json.load(f)
    with open(os.path.join(out_dir, "weights.json"),
              encoding="utf-8") as f:
        weights_doc = json.load(f)
    with open(os.path.join(out_dir, "benchmark.json"),
              encoding="utf-8") as f:
        bench_doc = json.load(f)
    return ledger_doc, weights_doc, bench_doc


_LEDGER_RUNS = {}


def ledger_runs():
    """One patched ledger run WITH benchmark files and one WITHOUT
    (same fixture archive otherwise). Cached; the files are what
    F5/F6/F7/F10 assert on."""
    if _LEDGER_RUNS:
        return _LEDGER_RUNS
    tmp = tempfile.mkdtemp(prefix="bench79-ledger-")
    with_arch = make_ledger_archive(os.path.join(tmp, "with"), True)
    without_arch = make_ledger_archive(os.path.join(tmp, "without"),
                                       False)
    with_out = os.path.join(tmp, "out-with")
    without_out = os.path.join(tmp, "out-without")
    _LEDGER_RUNS["with"] = run_ledger_on_archive(with_arch, with_out)
    _LEDGER_RUNS["with_out"] = with_out
    _LEDGER_RUNS["without"] = run_ledger_on_archive(without_arch,
                                                     without_out)
    _LEDGER_RUNS["without_out"] = without_out
    _LEDGER_RUNS["tmp"] = tmp
    return _LEDGER_RUNS


# ---------------------------------------------------------------- tests

def test_f1_family_alone():
    assert os.path.exists(FREEZE), "no scripts/benchmark_freeze.py"
    tmp = tempfile.mkdtemp(prefix="bench79-f1-")
    sdir = make_sweep_dir(os.path.join(tmp, "sweep"))
    r = run_freeze(sdir)
    assert r.returncode == 0, f"freeze exit {r.returncode}: {r.stdout} {r.stderr}"
    tech = load_bench(sdir, "family-technicals")
    assert tech["status"] == "present"
    # .4 x 0.297 x (1.28 x 0.0677) = 1.03% (141124 day)
    approx(tech["horizons"]["day"]["expected_move_pct"], 1.03)
    assert tech["horizons"]["day"]["families"] == {"technicals": 0.297}
    assert tech["horizons"]["day"]["net_score"] == 0.297
    # kmove-zero property: without the Kronos CSV the non-price
    # alone-forecasts are byte-identical (frozen_at / inputs masked).
    sdir2 = make_sweep_dir(os.path.join(tmp, "sweep-nokronos"),
                           with_kronos=False)
    r2 = run_freeze(sdir2)
    assert r2.returncode == 0
    for fam in ("family-technicals", "family-sentiment",
                "family-fundamentals"):
        a = mask_replay(load_bench(sdir, fam))
        b = mask_replay(load_bench(sdir2, fam))
        assert a == b, f"{fam} changed when the Kronos CSV was removed"


def test_f2_kronos_alone():
    tmp = tempfile.mkdtemp(prefix="bench79-f2-")
    sdir = make_sweep_dir(os.path.join(tmp, "sweep"))
    r = run_freeze(sdir)
    assert r.returncode == 0
    k = load_bench(sdir, "kronos-alone")
    assert k["status"] == "present"
    assert k["base_price"] == 8.02
    # kronos_at row-index rule: rows 0/4/20, never CSV row 0 as base.
    approx(k["horizons"]["day"]["expected_move_pct"], 28.55)
    approx(k["horizons"]["week"]["expected_move_pct"], 23.36)
    approx(k["horizons"]["month"]["expected_move_pct"], 20.02)
    approx(k["horizons"]["day"]["range_low_pct"], 25.88)
    approx(k["horizons"]["day"]["range_high_pct"], 31.95)
    assert k["kronos_first_row_date"] == "2026-11-15"
    assert k["kronos_row0_predates_asof"] is True
    assert k["horizons"]["day"]["confidence"] is None
    # price-forecast-alone recomputes kmove from the CSV (never an
    # inverted clamped score): day .6 x 28.55% + .4 x 1.0 x 8.67%.
    p = load_bench(sdir, "family-price-forecast")
    approx(p["horizons"]["day"]["expected_move_pct"], 20.6)


def test_f3_raw_llm():
    assert os.path.exists(PROMPT), "no scripts/benchmark_prompt_v1.txt"
    prompt_sha = hashlib.sha256(open(PROMPT, "rb").read()).hexdigest()
    tmp = tempfile.mkdtemp(prefix="bench79-f3-")
    # Key absent -> absent record, exit 0.
    sdir = make_sweep_dir(os.path.join(tmp, "sweep-nokey"))
    r = run_freeze(sdir)
    assert r.returncode == 0
    llm = load_bench(sdir, "raw-llm-cohere")
    assert llm["status"] == "absent" and llm["reason"] == "llm-key-absent"
    assert "horizons" not in llm
    # Stub server: one unparseable response, then one valid response.
    hits = []

    class Handler(http.server.BaseHTTPRequestHandler):
        mode = "bad"

        def do_POST(self):
            hits.append(Handler.mode)
            length = int(self.headers.get("Content-Length") or 0)
            self.rfile.read(length)
            if Handler.mode == "bad":
                body = {"message": {"content": [{"text": "not json"}]}}
            else:
                body = {"message": {"content": [{"text": json.dumps({
                    "day": {"direction": "up", "expected_move_pct": 1.5,
                            "range_low_pct": -2.0, "range_high_pct": 5.0,
                            "confidence": 0.6},
                    "week": {"direction": "flat",
                             "expected_move_pct": 0.0,
                             "range_low_pct": -4.0, "range_high_pct": 4.0,
                             "confidence": 0.5},
                    "month": {"direction": "down",
                              "expected_move_pct": -3.0,
                              "range_low_pct": -9.0, "range_high_pct": 3.0,
                              "confidence": 0.4}})}]}}
            raw = json.dumps(body).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def log_message(self, *a):
            pass

    srv = socketserver.TCPServer(("127.0.0.1", 0), Handler)
    port = srv.server_address[1]
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    try:
        env = clean_env({"COHERE_API_KEY": "dummy-key",
                         "COHERE_API_URL": f"http://127.0.0.1:{port}"})
        Handler.mode = "bad"
        sdir_bad = make_sweep_dir(os.path.join(tmp, "sweep-bad"))
        r = run_freeze(sdir_bad, env)
        assert r.returncode == 0
        llm = load_bench(sdir_bad, "raw-llm-cohere")
        assert llm["status"] == "absent", llm
        assert llm["reason"] == "llm-response-unparseable", llm
        assert hits == ["bad"], f"expected exactly 1 call, got {hits}"
        Handler.mode = "good"
        sdir_good = make_sweep_dir(os.path.join(tmp, "sweep-good"))
        r = run_freeze(sdir_good, env)
        assert r.returncode == 0
        llm = load_bench(sdir_good, "raw-llm-cohere")
        assert llm["status"] == "present", llm
        approx(llm["horizons"]["day"]["expected_move_pct"], 1.5)
        assert llm["prompt_sha256"] == prompt_sha
        assert llm["prompt_version"] == "v1"
        assert llm["llm_model"] == "command-r-08-2024"
        assert hits == ["bad", "good"], f"retry detected: {hits}"
    finally:
        srv.shutdown()
    # Strict parse, direct: garbage and missing keys are unparseable.
    import benchmark_freeze as bf
    parsed, err = bf._parse_llm_response(
        {"message": {"content": [{"text": "hello"}]}})
    assert parsed is None and err == "llm-response-unparseable"


def test_f4_baseline():
    tmp = tempfile.mkdtemp(prefix="bench79-f4-")
    sdir = make_sweep_dir(os.path.join(tmp, "sweep"))
    r = run_freeze(sdir)
    assert r.returncode == 0
    b = load_bench(sdir, "buy-and-hold")
    assert b["status"] == "present"
    for h, half in (("day", 8.67), ("week", 15.01), ("month", 32.42)):
        hb = b["horizons"][h]
        assert hb["direction"] == "flat"
        assert hb["expected_move_pct"] == 0.0
        approx(hb["range_low_pct"], -half)
        approx(hb["range_high_pct"], half)
        assert hb["confidence"] is None
        assert hb["families"] == {}
        assert hb["net_score"] is None


def test_f5_ledger_ingestion_identical():
    runs = ledger_runs()
    bench_doc = runs["with"][2]
    ledger_doc = runs["with"][0]
    ens_rows = [r for r in ledger_doc["forecasts_detail"]
                if r["sweep"].endswith("__clean-0__run1000")
                and r["horizon"] == "day"]
    assert len(ens_rows) == 1, ens_rows
    bench_rows = [r for r in bench_doc["rows"]
                  if r.get("entrant") == "family-technicals"
                  and r["horizon"] == "day"]
    assert len(bench_rows) == 1, bench_rows
    e, b = ens_rows[0], bench_rows[0]
    for k in ("direction_hit", "move_error_pp", "in_range",
              "dividend_gap", "realized_move_pct", "status"):
        assert b.get(k) == e.get(k), f"{k}: bench {b.get(k)} != ens {e.get(k)}"
    assert b["entrant"] == "family-technicals"
    assert b["frozen_at"] == "2026-11-12T12:00:00+00:00"


def test_f6_no_leak():
    runs = ledger_runs()
    with_w = runs["with"][1]["factors"]
    without_w = runs["without"][1]["factors"]
    assert with_w == without_w, (
        f"weights moved when benchmark rows were added: "
        f"{without_w} -> {with_w}")
    ledger_doc = runs["with"][0]
    assert not any("entrant" in r
                   for r in ledger_doc["forecasts_detail"]), (
        "benchmark rows leaked into ledger.json forecasts_detail")
    assert len(ledger_doc["forecasts_detail"]) == len(
        runs["without"][0]["forecasts_detail"]), (
        "ledger row count changed when benchmark rows were added")


def test_f7_n_gate():
    runs = ledger_runs()
    with open(os.path.join(runs["with_out"], "benchmark.md"),
              encoding="utf-8") as f:
        md = f.read()
    assert "below the n≥10 gate, no claim" in md
    low = md.lower()
    for word in ("beats", "wins", "winner", "best entrant"):
        assert word not in low, f"claim word {word!r} in benchmark.md"
    data_rows = [ln for ln in md.splitlines()
                 if ln.startswith("| ") and ("family-" in ln
                                            or "kronos-alone" in ln
                                            or "buy-and-hold" in ln
                                            or "| ensemble |" in ln)]
    assert data_rows, "no entrant rows in benchmark.md"
    for ln in data_rows:
        assert "below the n≥10 gate, no claim" in ln, ln


def test_f8_replay():
    tmp = tempfile.mkdtemp(prefix="bench79-f8-")
    sdir = make_sweep_dir(os.path.join(tmp, "sweep"))
    r1 = run_freeze(sdir)
    assert r1.returncode == 0
    first = {n: mask_replay(load_bench(sdir, n))
             for n in ("family-technicals", "family-price-forecast",
                       "kronos-alone", "buy-and-hold", "family-agent",
                       "raw-llm-cohere")}
    r2 = run_freeze(sdir)
    assert r2.returncode == 0
    for n, doc in first.items():
        assert mask_replay(load_bench(sdir, n)) == doc, \
            f"{n} not byte-identical on replay (frozen_at masked)"


def test_f9_absent_records():
    tmp = tempfile.mkdtemp(prefix="bench79-f9-")
    sdir = make_sweep_dir(os.path.join(tmp, "sweep"))
    r = run_freeze(sdir)
    assert r.returncode == 0
    agent = load_bench(sdir, "family-agent")
    assert agent["status"] == "absent"
    assert agent["reason"] == "family-did-not-vote"
    assert "horizons" not in agent
    sdir2 = make_sweep_dir(os.path.join(tmp, "sweep-nokronos"),
                           with_kronos=False)
    r2 = run_freeze(sdir2)
    assert r2.returncode == 0
    kronos = load_bench(sdir2, "kronos-alone")
    assert kronos["status"] == "absent"
    assert kronos["reason"] == "no-kronos-csv"
    # No ensemble at all -> all 8 absent, exit 0, never invents a base.
    sdir3 = make_sweep_dir(os.path.join(tmp, "sweep-noens"),
                           with_ensemble=False)
    r3 = run_freeze(sdir3)
    assert r3.returncode == 0
    for entrant in ("family-price-forecast", "family-technicals",
                    "family-sentiment", "family-agent",
                    "family-fundamentals", "kronos-alone",
                    "raw-llm-cohere", "buy-and-hold"):
        doc = load_bench(sdir3, entrant)
        assert doc["status"] == "absent", entrant
        assert doc["reason"] == "no-ensemble-no-base", entrant


def test_f10_flagged_exclusion():
    runs = ledger_runs()
    ledger_doc, weights_doc, bench_doc = runs["with"]
    assert ledger_doc["counts"]["matured"] == 9, ledger_doc["counts"]
    assert ledger_doc["counts"]["excluded_flagged"] == 4, \
        ledger_doc["counts"]
    assert ledger_doc["by_horizon"]["day"]["n"] == 5, \
        ledger_doc["by_horizon"]
    flagged = [r for r in ledger_doc["forecasts_detail"]
               if r.get("dividend_gap")]
    assert len(flagged) == 4, "flagged rows must stay listed with flags"
    assert all(r["status"] == "matured" for r in flagged)
    factors = weights_doc["factors"]
    assert factors["price-forecast"]["factor"] == 0.993, factors
    assert factors["technicals"]["factor"] == 0.742, factors
    assert factors["sentiment"]["factor"] == 1.024, factors
    # The aggregates move with the exclusion too (MAE 1.74pp, not
    # the keep-variant ~10.84pp on the live ledger).
    assert ledger_doc["by_horizon"]["day"]["mean_abs_error_pp"] == 2.46, \
        ledger_doc["by_horizon"]
    assert ledger_doc["by_horizon"]["day"]["range_coverage"] == 1.0


def test_f11_delta_walk():
    import delta as delta_mod
    tmp = tempfile.mkdtemp(prefix="bench79-f11-")
    # delta reads ARCHIVED sweep dirs (flat: digest.json at the root),
    # so stage archive-shaped dirs from the working-dir fixtures.
    # The benchmark/ dir is staged MANUALLY (not via the freeze): F11
    # asserts delta's sweep walk ignores the new dir, which must
    # hold on the pristine tree too (delta reads only named files).
    for name in ("a", "b"):
        src = make_sweep_dir(os.path.join(tmp, f"work-{name}"))
        dst = os.path.join(tmp, name)
        os.makedirs(dst, exist_ok=True)
        for f in ("digest.json", "ensemble.json"):
            shutil.copy(os.path.join(src, "digest", f),
                        os.path.join(dst, f))
        shutil.copytree(os.path.join(src, "collected"),
                        os.path.join(dst, "collected"))
    bdir = os.path.join(tmp, "b", "benchmark")
    os.makedirs(bdir, exist_ok=True)
    write_json(os.path.join(bdir, "family-technicals.json"),
               {"tool": "benchmark-freeze", "version": 1,
                "entrant": "family-technicals", "status": "present"})
    write_json(os.path.join(bdir, "kronos-alone.json"),
               {"tool": "benchmark-freeze", "version": 1,
                "entrant": "kronos-alone", "status": "absent",
                "reason": "no-kronos-csv"})
    va = delta_mod.load_sweep_view(os.path.join(tmp, "a"))
    vb = delta_mod.load_sweep_view(os.path.join(tmp, "b"))
    va.pop("sweep_dir")
    vb.pop("sweep_dir")
    assert va == vb, "delta sweep view changed when benchmark/ was added"


def test_f13_class_b():
    runs = ledger_runs()
    bench_doc = runs["with"][2]
    acme = [r for r in bench_doc["rows"]
            if r.get("entrant") == "class-b-acme"]
    assert len(acme) == 1, bench_doc["rows"]
    assert acme[0]["horizon"] == "day"
    assert acme[0]["expected_move_pct"] == 5.0
    assert acme[0]["status"] == "matured", acme[0]
    assert acme[0]["in_range"] is None  # no range was ever claimed
    assert not any(r.get("entrant") == "class-b-late"
                   for r in bench_doc["rows"])
    assert not any(r.get("entrant") == "class-b-nots"
                   for r in bench_doc["rows"])
    gaps = " ".join(bench_doc["gaps"])
    assert "anti-backfill" in gaps, bench_doc["gaps"]
    assert "no timestamp" in gaps, bench_doc["gaps"]


def test_f12_publisher_validation():
    import ledger_publish as pub
    assert hasattr(pub, "validate_benchmark"), (
        "no ledger_publish.validate_benchmark")
    assert "benchmark.json" in pub.FILES and "benchmark.md" in pub.FILES, (
        f"benchmark files not in publisher FILES: {pub.FILES}")
    good = {"tool": "benchmark-ledger", "version": 1, "counts": {},
            "by_entrant": {"family-technicals": {
                "day": {"n": 5, "hit_rate": 0.0,
                        "mean_abs_error_pp": 2.0,
                        "range_coverage": 1.0}}},
            "rows": [], "gaps": []}
    pub.validate_benchmark(good, None)
    pub.validate_benchmark(good, copy.deepcopy(good))
    regressed = copy.deepcopy(good)
    regressed["by_entrant"]["family-technicals"]["day"]["n"] = 4
    try:
        pub.validate_benchmark(regressed, good)
    except RuntimeError:
        pass
    else:
        raise AssertionError("matured-count decrease did not reject")
    malformed = copy.deepcopy(good)
    malformed["gaps"] = ["benchmark file malformed: x is not parseable"]
    try:
        pub.validate_benchmark(malformed, None)
    except RuntimeError:
        pass
    else:
        raise AssertionError("malformed benchmark file did not reject")
    bad_entrant = copy.deepcopy(good)
    bad_entrant["rows"] = [{"entrant": "not-a-real-entrant",
                            "status": "pending"}]
    try:
        pub.validate_benchmark(bad_entrant, None)
    except RuntimeError:
        pass
    else:
        raise AssertionError("bad entrant did not reject")
    error_row = copy.deepcopy(good)
    error_row["rows"] = [{"entrant": "family-technicals",
                          "status": "error", "error": "boom"}]
    try:
        pub.validate_benchmark(error_row, None)
    except RuntimeError:
        pass
    else:
        raise AssertionError("error row did not reject")
    try:
        pub.validate_benchmark(None, None)
    except RuntimeError:
        pass
    else:
        raise AssertionError("unparseable benchmark did not reject")


def main():
    tests = [
        ("F1 family-alone", test_f1_family_alone),
        ("F2 kronos-alone", test_f2_kronos_alone),
        ("F3 raw-llm", test_f3_raw_llm),
        ("F4 baseline", test_f4_baseline),
        ("F5 ledger ingestion", test_f5_ledger_ingestion_identical),
        ("F6 no-leak L1/L2", test_f6_no_leak),
        ("F7 n-gate", test_f7_n_gate),
        ("F8 replay", test_f8_replay),
        ("F9 absent records", test_f9_absent_records),
        ("F10 flagged exclusion", test_f10_flagged_exclusion),
        ("F11 delta walk", test_f11_delta_walk),
        ("F12 publisher validation", test_f12_publisher_validation),
        ("F13 class-b capture", test_f13_class_b),
    ]
    for name, fn in tests:
        check(name, fn)
    failed = [r for r in RESULTS if not r[1]]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} passed")
    if failed:
        for name, _ok, detail in failed:
            print(f"  FAILED: {name}: {detail}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
