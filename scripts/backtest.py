#!/usr/bin/env python3
"""Walk-forward backtest harness (borsagator #436, step 2;
design §6.2).

One invocation runs ONE (cutoff, ticker) cell — the unit the
worker bus schedules (design §6.4) so a failure is isolated and
re-runnable:

  1. admission gate (backtest_gate.py, design §4)
  2. 60-session warm-up gate (design §1.3 — the harness enforces
     it; Kronos's own floor is only --min-context 20)
  3. the three runners with --as-of (step 1), each failure
     classified: a runner's own minimum-rows refusal is
     skipped-with-reason, anything else is an error
  4. scripts/ensemble.py in 2-family mode (price-forecast +
     technicals, base weights, news overlay off) on the staged
     outputs
  5. anti-look-ahead audit (design §1.4) + the #87 base-price
     guard, both before anything is published
  6. optional Kronos determinism re-run (design §6.4d)
  7. realised closes fetched separately and staged apart from the
     forecast inputs (design §1.4.4)
  8. the capture written to backtest/<cutoff>/<ticker>/ with a
     manifest (cutoff, ticker, runner refs, model refs, seed,
     sha256 of every file, audit result)

The harness NEVER writes to the forward ledger or the archive:
its only output root is --out-root (default ./backtest). Scoring
is a separate step (scripts/backtest_score.py) over the captures.

Stdlib only. Network is used only by the Yahoo fetches (gate +
realised); --realised-file and --history-csv let a cell run
offline from pre-fetched data, which is how the tests drive it.
"""
import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import backtest_gate  # noqa: E402
import ledger  # noqa: E402

TOOL = "walkforward-backtest"
VERSION = 1
WARMUP_SESSIONS = 60
KRONOS_PRED_LEN = 21  # ensemble month bar (design §1.1)
DROP_BEFORE = "2019-01-01"
# Design §3: 12 quarter-ends, 2023-12-29 -> 2026-09-30. A
# quarter-end that is not a session is adjusted to the last
# session of the quarter by the gate (the harness records the
# session actually used).
CUTOFFS_V1 = ["2023-12-29", "2024-03-28", "2024-06-27",
              "2024-09-30", "2024-12-31", "2025-03-31",
              "2025-06-30", "2025-09-30", "2025-12-31",
              "2026-03-31", "2026-06-30", "2026-09-30"]
# Design §4: 5 EGX + 1 US. POUL contributes ZERO v1 cutoffs
# (usable series starts 2026-09-28, §1.5) — it is listed here so
# the plan says so explicitly instead of silently omitting it.
TICKERS_V1 = ["COMI.CA", "ETEL.CA", "ORAS.CA", "TMGH.CA", "NVDA",
              "POUL.CA"]
SERIES_START = {"POUL.CA": "2026-09-28"}
CONTEXT_START = {"POUL.CA": "2026-09-28"}
INDEX_TICKER = {"EGX": "^EGX30", "US": "^GSPC"}
SESSIONS_NEEDED = ledger.DEFAULT_SESSIONS["month"]  # 14
# A runner failing on its own minimum-rows floor is a skip, not
# an error (step-1 observation: pandas-ta/talib enforce 60 inside
# the runner; Kronos enforces --min-context). Match the refusal
# wording the three runners actually print. Kronos's real refusal
# is "--as-of <C>: only <N> sessions on/before the cutoff
# (< 20 minimum rows); refusing to forecast" — note it never
# contains the string "min-context", so a bare min-context
# pattern would misclassify argparse usage text (which names the
# --min-context option) as a skip and exit zero on a real error.
MIN_ROWS_PATTERNS = (
    re.compile(r"only \d+ sessions", re.I),
    re.compile(r"minimum rows", re.I),
    re.compile(r"only \d+ sessions on/before the cutoff", re.I),
    re.compile(r"fewer than .* rows", re.I),
    re.compile(r"below .*min", re.I),
)


def parse_iso(s):
    try:
        return date.fromisoformat(str(s)[:10])
    except Exception:
        return None


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def market_of(ticker):
    return "EGX" if str(ticker).upper().endswith(".CA") else "US"


def sessions_on_or_before(rows, cutoff, series_start=None):
    """Usable sessions on/before the cutoff: after DROP_BEFORE
    and after any corporate discontinuity (design §1.5)."""
    c = parse_iso(cutoff)
    out = []
    for r in rows:
        d = parse_iso(r["date"])
        if d is None or d > c:
            continue
        if d < parse_iso(DROP_BEFORE):
            continue
        if series_start and d < parse_iso(series_start):
            continue
        out.append(r)
    return out


def warmup_check(rows, cutoff, series_start=None):
    """Design §1.3: 60 sessions before the cutoff or the cutoff is
    untestable — skipped with the reason, never scored as a miss."""
    usable = sessions_on_or_before(rows, cutoff, series_start)
    n = len(usable)
    if n < WARMUP_SESSIONS:
        return False, n, (
            "warm-up: only %d usable sessions on/before %s "
            "(need %d)" % (n, cutoff, WARMUP_SESSIONS))
    return True, n, ""


def classify_runner_failure(text):
    """(is_min_rows_skip, reason): a runner's own minimum-rows
    refusal is a skip; anything else is an unexpected error."""
    text = text or ""
    for pat in MIN_ROWS_PATTERNS:
        m = pat.search(text)
        if m:
            return True, "runner minimum-rows refusal: %s" % m.group(0)
    return False, ""


def git_head(path):
    try:
        r = subprocess.run(["git", "-C", path, "rev-parse", "HEAD"],
                           capture_output=True, text=True, timeout=30)
        return r.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def run_subprocess(cmd, cwd, env=None, timeout=1800):
    merged = dict(os.environ)
    if env:
        merged.update(env)
    proc = subprocess.run(cmd, cwd=cwd, env=merged,
                          capture_output=True, text=True, timeout=timeout)
    return proc


# --------------------------------------------------------------------------
# Runners
# --------------------------------------------------------------------------
RUNNERS = {
    "kronos": {
        "script": "scripts/kronos_forecast.py",
        "args": lambda t, c, extra: [
            "--ticker", t, "--pred-len", str(KRONOS_PRED_LEN),
            "--as-of", c, "--context-start",
            CONTEXT_START.get(t.upper(), DROP_BEFORE)] + extra,
        "outputs": ["results/forecast.csv", "results/report.md"],
        "stage": {"results/forecast.csv": "collected/kronos/forecast.csv",
                  "results/report.md": "collected/kronos/report.md"},
    },
    "pandas-ta": {
        "script": "scripts/ta_snapshot.py",
        "args": lambda t, c, extra: ["--ticker", t, "--as-of", c] + extra,
        "outputs": ["results/ta_snapshot.json",
                    "results/indicators.csv"],
        "stage": {"results/ta_snapshot.json":
                  "collected/pandas-ta/ta_snapshot.json",
                  "results/indicators.csv":
                  "collected/pandas-ta/indicators.csv"},
    },
    "talib": {
        "script": "scripts/ta.py",
        "args": lambda t, c, extra: [t, "--as-of", c] + extra,
        "outputs": ["results/ta_latest.json",
                    "results/indicators.csv"],
        "stage": {"results/ta_latest.json": "collected/talib/ta_latest.json",
                  "results/indicators.csv": "collected/talib/indicators.csv"},
    },
}


def run_runner(kind, runner_dir, ticker, cutoff, stage_dir, log,
               timeout=1800, extra_args=()):
    """Run one runner with --as-of and stage its outputs.
    Returns (status, detail) where status is ok | skipped | error.
    `log` is an open file the runner's output is appended to."""
    spec = RUNNERS[kind]
    script = os.path.join(runner_dir, spec["script"])
    cmd = [sys.executable, script] + spec["args"](ticker, cutoff,
                                                  list(extra_args))
    log.write("\n$ %s (cwd=%s)\n" % (" ".join(cmd), runner_dir))
    log.flush()
    try:
        proc = run_subprocess(cmd, cwd=runner_dir, timeout=timeout)
    except subprocess.TimeoutExpired:
        return "error", "%s timed out after %ds" % (kind, timeout)
    log.write(proc.stdout or "")
    log.write(proc.stderr or "")
    log.write("[rc=%d]\n" % proc.returncode)
    log.flush()
    out_text = (proc.stdout or "") + "\n" + (proc.stderr or "")
    if proc.returncode != 0:
        skip, reason = classify_runner_failure(out_text)
        if skip:
            return "skipped", "%s: %s" % (kind, reason)
        return "error", "%s exited %d: %s" % (
            kind, proc.returncode, (proc.stderr or proc.stdout or "")[-500:])
    for rel in spec["outputs"]:
        if not os.path.exists(os.path.join(runner_dir, rel)):
            return "error", "%s: expected output %s missing" % (kind, rel)
    # A pandas-ta NO DATA snapshot (fetch failed but rc 0) is a
    # skip, not a forecast: the snapshot carries close None.
    if kind == "pandas-ta":
        try:
            with open(os.path.join(runner_dir,
                                   "results/ta_snapshot.json"),
                      encoding="utf-8") as f:
                snap = json.load(f)
            if snap.get("close") is None:
                return "skipped", (
                    "pandas-ta: no data (%s)"
                    % (snap.get("verdict") or "empty snapshot"))
        except (OSError, ValueError) as e:
            return "error", "pandas-ta: unreadable snapshot: %s" % e
    for src_rel, dst_rel in spec["stage"].items():
        dst = os.path.join(stage_dir, dst_rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(os.path.join(runner_dir, src_rel), dst)
    return "ok", ""


# --------------------------------------------------------------------------
# Digest + ensemble
# --------------------------------------------------------------------------
def forecast_actions(events, cutoff, base):
    """Dividend actions known at the cutoff (design §1.4.3): only
    ex-dates <= as-of enter the forecast. Later ex-dates enter
    only at scoring time (backtest_score.py). Shape is the
    ensemble's action dict."""
    out = []
    for ev in events or []:
        if ev.get("type") != "dividend":
            continue
        ex = ev.get("ex_date")
        if not ex or parse_iso(ex) > parse_iso(cutoff):
            continue
        try:
            dps = float(ev.get("dps"))
        except Exception:
            continue
        if not (0 < dps < base):
            continue
        out.append({"type": "dividend", "dps": dps, "ex_date": ex,
                    "entitlement_end": None,
                    "mechanical_pct": round(-dps / base * 100, 2),
                    "source": "yahoo-events",
                    "date_basis": "yahoo-events-feed"})
    return out


def build_digest(stage_dir, ticker, cutoff, actions):
    """digest.json in the shape ensemble.py reads, from the staged
    runner outputs. Kronos contributes its forecast path (the CSV,
    not the metrics); pandas-ta contributes the snapshot metrics
    the tech score reads; talib contributes the close as the base
    fallback."""
    with open(os.path.join(stage_dir,
                           "collected/pandas-ta/ta_snapshot.json"),
              encoding="utf-8") as f:
        ta = json.load(f)
    with open(os.path.join(stage_dir, "collected/talib/ta_latest.json"),
              encoding="utf-8") as f:
        tb = json.load(f)
    kronos_last = None
    with open(os.path.join(stage_dir,
                           "collected/kronos/forecast.csv"),
              newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
        if rows:
            try:
                kronos_last = float(rows[-1].get("close"))
            except Exception:
                kronos_last = None
    digest = {"ticker": ticker.upper(), "date": cutoff,
              "job": "walkforward-backtest",
              "corporate_actions": actions,
              "results": [
                  {"tool": "kronos", "status": "ok",
                   "summary": {"metrics": {
                       "forecast.csv_last_close": kronos_last}}},
                  {"tool": "pandas-ta", "status": "ok",
                   "summary": {"metrics": dict(ta)}},
                  {"tool": "talib", "status": "ok",
                   "summary": {"metrics": {
                       "close": tb.get("last_close")}}},
              ]}
    os.makedirs(os.path.join(stage_dir, "digest"), exist_ok=True)
    with open(os.path.join(stage_dir, "digest/digest.json"),
              "w", encoding="utf-8") as f:
        json.dump(digest, f, indent=1, ensure_ascii=False)
    return digest


def run_ensemble(stage_dir, borsagator_root, log, timeout=600):
    """Run scripts/ensemble.py in 2-family mode with cwd=stage.
    Returns (ensemble_doc, error)."""
    script = os.path.join(borsagator_root, "scripts/ensemble.py")
    env = {"BORSAGATOR_BACKTEST_TWO_FAMILY": "1",
           # Belt and braces: the mode already forces base-v1, but
           # point the measured-weights lookup at a file that does
           # not exist so no ledger file can ever leak in.
           "BORSAGATOR_WEIGHTS": os.path.join(
               stage_dir, "no-such-weights.json")}
    log.write("\n$ %s %s (cwd=%s, 2-family mode)\n"
              % (sys.executable, script, stage_dir))
    log.flush()
    proc = run_subprocess([sys.executable, script], cwd=stage_dir,
                          env=env, timeout=timeout)
    log.write(proc.stdout or "")
    log.write(proc.stderr or "")
    log.flush()
    path = os.path.join(stage_dir, "digest/ensemble.json")
    if not os.path.exists(path):
        return None, "ensemble wrote no ensemble.json: %s" % (
            (proc.stdout or "")[-500:])
    if os.path.exists(os.path.join(stage_dir,
                                   "digest/ensemble_error.txt")):
        return None, "ensemble failed (see ensemble_error.txt)"
    with open(path, encoding="utf-8") as f:
        return json.load(f), ""


# --------------------------------------------------------------------------
# Audit (design §1.4)
# --------------------------------------------------------------------------
def _csv_max_date(path):
    """Max date in a price/indicator CSV, or None when the file
    carries no usable dates."""
    latest = None
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            d = parse_iso(str(row.get("date") or row.get("Date") or "")
                          [:10])
            if d and (latest is None or d > latest):
                latest = d
    return latest


def audit_stage(stage_dir, cutoff, ticker):
    """Anti-look-ahead audit. Every INPUT file must end at or
    before the cutoff; the Kronos forecast path is a prediction
    (dated after the cutoff by construction) and is audited
    separately for length, never for its dates. Returns a list of
    violation strings (empty = pass)."""
    c = parse_iso(cutoff)
    violations = []
    # 1. Truncation proof: every input CSV ends <= C.
    for rel in ("collected/pandas-ta/indicators.csv",
                "collected/talib/indicators.csv"):
        path = os.path.join(stage_dir, rel)
        if not os.path.exists(path):
            violations.append("audit: missing input %s" % rel)
            continue
        latest = _csv_max_date(path)
        if latest is None:
            violations.append("audit: %s carries no dates" % rel)
        elif latest > c:
            violations.append(
                "audit: %s ends %s, after cutoff %s"
                % (rel, latest.isoformat(), cutoff))
    # Kronos context window (report.md) must end <= C. A report
    # with no context line at all is a violation too: without it
    # there is no evidence of what history Kronos consumed, and a
    # passing audit would otherwise bless a forecast on unknown
    # context.
    report = os.path.join(stage_dir, "collected/kronos/report.md")
    ctx_end = None
    if os.path.exists(report):
        with open(report, encoding="utf-8") as f:
            m = re.search(r"Context window used: .*? to (\d{4}-\d{2}-\d{2})",
                          f.read())
        if m:
            ctx_end = parse_iso(m.group(1))
            if ctx_end is None:
                violations.append(
                    "audit: Kronos context end %s is not a valid date"
                    % m.group(1))
            elif ctx_end > c:
                violations.append(
                    "audit: Kronos context ends %s, after cutoff %s"
                    % (m.group(1), cutoff))
        else:
            violations.append(
                "audit: Kronos report has no context window line — "
                "the context end date cannot be verified")
    else:
        violations.append("audit: missing collected/kronos/report.md")
    # 2. Snapshot last dates.
    for rel, key in (("collected/pandas-ta/ta_snapshot.json",
                      "last_date"),
                     ("collected/talib/ta_latest.json", "last_date")):
        path = os.path.join(stage_dir, rel)
        if not os.path.exists(path):
            violations.append("audit: missing input %s" % rel)
            continue
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
        d = parse_iso(str(doc.get(key) or ""))
        if d is None:
            violations.append("audit: %s has no %s" % (rel, key))
        elif d > c:
            violations.append("audit: %s %s is %s, after cutoff %s"
                              % (rel, key, doc.get(key), cutoff))
    # 3. Ensemble output: base at the cutoff, 2-family only.
    epath = os.path.join(stage_dir, "digest/ensemble.json")
    if not os.path.exists(epath):
        violations.append("audit: missing digest/ensemble.json")
        return violations
    with open(epath, encoding="utf-8") as f:
        ens = json.load(f)
    if str(ens.get("ticker") or "").upper() != ticker.upper():
        violations.append("audit: ensemble ticker %r != %s"
                          % (ens.get("ticker"), ticker))
    base_date = parse_iso(str(ens.get("base_date") or ""))
    if base_date is None:
        violations.append("audit: ensemble has no base_date")
    elif base_date > c:
        violations.append("audit: ensemble base_date %s after cutoff %s"
                          % (ens.get("base_date"), cutoff))
    if ens.get("weights_source") != "base-v1":
        violations.append(
            "audit: ensemble weights_source is %r, not base-v1 — "
            "measured weights leaked into the backtest"
            % (ens.get("weights_source"),))
    if (ens.get("risk") or {}).get("level") != "none":
        violations.append(
            "audit: ensemble risk level is %r, not none — the news "
            "overlay was not disabled"
            % ((ens.get("risk") or {}).get("level"),))
    for h in ledger.HORIZONS:
        hb = (ens.get("horizons") or {}).get(h)
        if not isinstance(hb, dict):
            violations.append("audit: ensemble has no %s horizon" % h)
            continue
        voters = sorted((hb.get("families") or {}).keys())
        if voters != ["price-forecast", "technicals"]:
            violations.append(
                "audit: %s horizon voters %r, not the 2 families"
                % (h, voters))
        if hb.get("horizon_short"):
            violations.append(
                "audit: %s horizon is short (Kronos path < 21 bars)"
                % h)
    # 4. Kronos path length: 21 bars were requested.
    kpath = os.path.join(stage_dir, "collected/kronos/forecast.csv")
    if os.path.exists(kpath):
        with open(kpath, newline="", encoding="utf-8") as f:
            n = sum(1 for _ in csv.DictReader(f))
        if n < KRONOS_PRED_LEN:
            violations.append(
                "audit: Kronos forecast.csv has %d rows, need %d"
                % (n, KRONOS_PRED_LEN))
    else:
        violations.append("audit: missing collected/kronos/forecast.csv")
    return violations


def base_price_guard(base, evidenced_close, level_date, as_of, actions):
    """The #87 guard, reused (design §1.4.2): the as-of base close
    must agree with the ticker-evidenced close at the cutoff
    within ledger.VALID_TOL (3%), unless it is a cum-dividend base
    on the ex-date itself."""
    if not base or not evidenced_close:
        return False, "no base or evidenced close to compare"
    rel = ledger.rel_close(base, evidenced_close)
    if rel <= ledger.VALID_TOL:
        return True, ""
    if ledger.cum_div_base_valid(base, evidenced_close, level_date,
                                 as_of, actions):
        return True, "cum-dividend base on ex-date (issue #129)"
    return False, (
        "base_price %s deviates %.1f%% from the ticker-evidenced "
        "close %s at %s (issue #87)" % (base, rel * 100,
                                        evidenced_close, level_date))


def check_ensemble_base_date(ens_base_date, ev_date, cutoff):
    """The ensemble base must be as of the evidenced session — the
    last valid session on/before the cutoff, not the cutoff date
    itself when the cutoff is not a session. A June 27 base at the
    same price as the June 30 evidenced close is a June 27
    forecast, not a June 30 one, and the price guard alone cannot
    tell them apart. Returns an error string, or "" when the dates
    agree."""
    ens_base_date = str(ens_base_date or "")[:10]
    if not ens_base_date:
        return "ensemble has no base_date"
    if ens_base_date != ev_date:
        return ("ensemble base_date %s != evidenced session %s "
                "(cutoff %s) — the forecast is as of an older "
                "session" % (ens_base_date, ev_date, cutoff))
    return ""


# The harness writes only under --out-root and never to the
# ledger or the archive. Both are repo-root trees, so a hostile
# or mistaken cutoff/ticker (or out-root) must be rejected before
# anything is created or replaced.
PROTECTED_TREES = ("ledger", "archive")


def validate_capture_path(out_root, cutoff, ticker):
    """(cell_dir, error): the capture dir for one cell, or an
    error string when the cutoff/ticker are not single path
    components, or the resolved destination escapes the resolved
    out-root, or it lands inside a protected tree."""
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(cutoff or "")):
        return None, "cutoff %r is not a YYYY-MM-DD date" % (cutoff,)
    if parse_iso(cutoff) is None:
        return None, "cutoff %r is not a valid date" % (cutoff,)
    if not ticker or str(ticker) in (".", "..") \
            or "/" in str(ticker) or "\\" in str(ticker) \
            or str(ticker) != str(ticker).strip():
        return None, ("ticker %r is not a single path component"
                      % (ticker,))
    root = os.path.realpath(out_root)
    expected = os.path.join(root, cutoff, ticker)
    cell = os.path.realpath(expected)
    if cell != expected:
        # The cutoff/ticker components themselves redirect the
        # destination (a ticker symlink resolving to its own
        # cutoff directory, say): publish would rename the
        # resolved directory to the backup path and delete it,
        # wiping every sibling capture under it. Only the
        # out-root itself may be an alias (resolved above); the
        # two components below it must be literal.
        return None, ("capture dir %s resolves to %s — the "
                      "cutoff/ticker path must not redirect"
                      % (expected, cell))
    if cell == root or os.path.commonpath([cell, root]) != root:
        return None, "capture dir %s escapes out-root %s" % (cell, root)
    for tree in PROTECTED_TREES:
        protected = os.path.realpath(os.path.join(REPO_ROOT, tree))
        # Overlap in EITHER direction: a cell inside a protected
        # tree writes into it, and a cell containing one (an
        # alias resolving to the repo root) would let publish
        # move the whole tree to the backup path and delete it.
        if (os.path.commonpath([cell, protected]) == protected
                or os.path.commonpath([root, protected]) == protected
                or os.path.commonpath([protected, cell]) == cell):
            return None, ("capture path %s overlaps the protected "
                          "%s tree" % (cell, tree))
    return cell, ""


# --------------------------------------------------------------------------
# Realised closes (scoring input, fetched separately — §1.4.4)
# --------------------------------------------------------------------------
def fetch_realised(ticker, cutoff, fetcher=None):
    """Realised closes for scoring: the C row plus the first 14
    sessions after C, the index closes on the same dates, and the
    dividend/split events inside the horizon. Fetched in a
    separate step from the forecast, stored in a separate file,
    never visible to the forecast step. `fetcher` is injectable
    for tests (defaults to the Yahoo chart API)."""
    fetcher = fetcher or backtest_gate.fetch_chart
    rows, events, ev_ok, ev_error, dropped = backtest_gate.unpack_fetch(
        fetcher(ticker))
    # The realised window's actions must be VERIFIED, not merely
    # empty: the admission fetch may have retrieved actions while
    # this separate realised fetch reports the feed unavailable
    # (or drops records). Publishing an empty action window then
    # would let the scorer count an unadjusted corporate-action
    # move as forecast error. A verified action-free window
    # (ev_ok True, no events) still scores.
    if not ev_ok or ev_error:
        return None, (
            "realised: dividend/split events feed not verifiable "
            "(%s) — the action window cannot be established, so "
            "the cell is not published"
            % (ev_error or "feed not retrievable"))
    c = parse_iso(cutoff)
    after = [r for r in rows if parse_iso(r["date"]) > c]
    after.sort(key=lambda r: r["date"])
    base_rows = [r for r in rows if parse_iso(r["date"]) <= c]
    base_close = base_rows[-1]["close"] if base_rows else None
    base_date = base_rows[-1]["date"] if base_rows else None
    if len(after) < SESSIONS_NEEDED:
        return None, (
            "realised: only %d sessions after %s, need %d — "
            "horizons not yet mature" % (len(after), cutoff,
                                         SESSIONS_NEEDED))
    sessions = after[:SESSIONS_NEEDED]
    maturity = sessions[-1]["date"]
    # A bar dropped for a missing/unusable close inside the
    # realised window must not shift the scored horizons: the
    # surviving rows alone would count the NEXT session's close
    # as the dropped session (the day horizon would be scored
    # on the second session's move) and still publish the
    # capture as complete. Block the cell instead — the same
    # fail-closed treatment as an unverifiable events feed.
    # Drops after the window touch no scored horizon and do
    # not block.
    dropped_in_window = [d for d in dropped or []
                         if parse_iso(d) is not None
                         and c < parse_iso(d) <= parse_iso(maturity)]
    if dropped_in_window:
        return None, (
            "realised: %d session(s) inside the realised window "
            "have no usable close (%s) — the next available "
            "close must not be counted as that session, so the "
            "cell is not published"
            % (len(dropped_in_window),
               ", ".join(dropped_in_window)))
    index_ticker = INDEX_TICKER[market_of(ticker)]
    # The index fetch must not take the stock capture down with
    # it: if the index request exhausts its retries, record an
    # explicit index gap and publish the matured stock capture
    # without index evidence — the scorer leaves index scores and
    # deltas unavailable until usable index data exists.
    index_gap = None
    try:
        irows, _ievents, _iok, _ierr, _idropped = \
            backtest_gate.unpack_fetch(fetcher(index_ticker))
    except Exception as e:  # noqa: BLE001 - index fetch exhausted
        irows = []
        index_gap = "index fetch failed: %s" % e
    imap = {r["date"]: r["close"] for r in irows}
    ibase = [r for r in irows if parse_iso(r["date"]) <= c]
    index_base_close = ibase[-1]["close"] if ibase else None
    index_sessions = []
    for s in sessions:
        if index_gap is not None:
            break  # no index evidence at all — see index_gap
        d = s["date"]
        if d in imap:
            index_sessions.append({"date": d, "close": imap[d],
                                   "exact": True})
        else:
            prior = [x for x in sorted(imap) if x <= d]
            if not prior:
                # No usable index close on/before this session:
                # the index evidence is unusable, but the mature
                # stock capture is still published — the same
                # index_gap path as a fetch failure.
                index_gap = ("no %s close on or before %s"
                             % (index_ticker, d))
                index_base_close = None
                index_sessions = []
                break
            index_sessions.append({"date": d, "close": imap[prior[-1]],
                                   "exact": False,
                                   "index_date": prior[-1]})
    if index_gap is None and not any(
            parse_iso(d) is not None
            and c < parse_iso(d) <= parse_iso(maturity)
            for d in imap):
        # The index feed has no close inside the realised
        # window (it ends at/before the cutoff): every session
        # above would carry the base close forward — a flat
        # index path scored as real index evidence. Record the
        # gap and keep the stock capture, exactly as for a
        # failed index fetch. (Carrying the latest close across
        # individual non-session dates stays: that path is only
        # reached when an in-window index observation exists,
        # which this check has just established.)
        index_gap = ("no %s close after %s in the realised "
                     "window" % (index_ticker, cutoff))
        index_base_close = None
        index_sessions = []
    window_actions = []
    window_splits = []
    for ev in events or []:
        ex = parse_iso(ev.get("ex_date") or "")
        if ex and c < ex <= parse_iso(maturity):
            if ev.get("type") == "dividend":
                window_actions.append(ev)
            elif ev.get("type") == "split":
                window_splits.append(ev)
    return {"ticker": ticker.upper(), "cutoff": cutoff,
            "base_close": base_close, "base_date": base_date,
            "sessions": [{"date": s["date"], "close": s["close"]}
                         for s in sessions],
            "maturity_date": maturity,
            "index_ticker": index_ticker,
            "index_base_close": index_base_close,
            "index_sessions": index_sessions,
            "index_gap": index_gap,
            "actions": window_actions,
            "splits": window_splits,
            "fetched_at": date.today().isoformat()}, ""


# --------------------------------------------------------------------------
# One cell
# --------------------------------------------------------------------------
def run_cell(cutoff, ticker, cfg):
    """Run one (cutoff, ticker) cell. Returns a result dict with
    status ok | skipped | error and, on ok, the capture dir."""
    ticker = ticker.upper()
    out_root = cfg["out_root"]
    result = {"tool": TOOL, "ticker": ticker, "cutoff": cutoff,
              "status": "error", "capture_dir": None}
    # The capture directory boundary is enforced before any work:
    # a bad cutoff/ticker or an out-root inside the ledger or
    # archive trees fails the cell instead of writing there.
    cell_dir, verr = validate_capture_path(out_root, cutoff, ticker)
    if verr:
        result.update(status="error", reason="capture path: " + verr)
        return result
    stage = tempfile.mkdtemp(prefix="bt436-cell-")
    log_path = os.path.join(stage, "harness.log")
    publish_dir = None  # this invocation's staging dir, if any
    try:
        with open(log_path, "w", encoding="utf-8") as log:
            log.write("walk-forward backtest cell %s %s\n"
                      % (cutoff, ticker))
            # 1. Gate (history fetch is the gate's own fetch).
            fetcher = cfg.get("fetcher") or backtest_gate.fetch_chart
            rows, events, ev_ok, ev_error, _dropped = \
                backtest_gate.unpack_fetch(fetcher(ticker))
            gate = backtest_gate.gate_ticker(
                ticker, rows, ev_ok, cfg["latest_cutoff"],
                SERIES_START.get(ticker), ev_error)
            result["gate"] = gate
            log.write("gate: %s\n" % json.dumps(gate))
            if not gate["passed"]:
                result.update(status="skipped",
                              reason="gate failed: "
                              + "; ".join(gate["reasons"]))
                return result
            # 2. Warm-up (§1.3 — harness-enforced 60 sessions).
            ok, n, reason = warmup_check(
                rows, cutoff, SERIES_START.get(ticker))
            result["warmup_sessions"] = n
            if not ok:
                result.update(status="skipped", reason=reason)
                return result
            # 3. Runners with --as-of.
            for kind in ("kronos", "pandas-ta", "talib"):
                status, detail = run_runner(
                    kind, cfg["runners"][kind], ticker, cutoff, stage,
                    log, timeout=cfg["timeout"])
                if status != "ok":
                    if status == "skipped":
                        result.update(status="skipped", reason=detail)
                    else:
                        result.update(status="error", reason=detail)
                    return result
            # 4. Digest + 2-family ensemble.
            base_rows = sessions_on_or_before(
                rows, cutoff, SERIES_START.get(ticker))
            base = base_rows[-1]["close"]
            actions = forecast_actions(events, cutoff, base)
            build_digest(stage, ticker, cutoff, actions)
            ens, err = run_ensemble(stage, cfg["borsagator_root"], log)
            if ens is None:
                result.update(status="error", reason=err)
                return result
            result["ensemble"] = {
                "base_price": ens.get("base_price"),
                "base_date": ens.get("base_date"),
                "weights_source": ens.get("weights_source")}
            # 5. Audit + base-price guard.
            violations = audit_stage(stage, cutoff, ticker)
            result["audit_violations"] = violations
            if violations:
                result.update(status="error",
                              reason="audit failed: "
                              + "; ".join(violations))
                return result
            ev_close = base_rows[-1]["close"]
            ev_date = base_rows[-1]["date"]
            # The ensemble base must be as of the evidenced
            # session, not an older one at the same price.
            date_err = check_ensemble_base_date(
                ens.get("base_date"), ev_date, cutoff)
            if date_err:
                result.update(status="error",
                              reason="base-price guard: " + date_err)
                return result
            ok, why = base_price_guard(ens.get("base_price"), ev_close,
                                       ev_date, cutoff, actions)
            if not ok:
                result.update(status="error",
                              reason="base-price guard: " + why)
                return result
            # 6. Determinism re-run (design §6.4d): Kronos twice,
            # directions must agree.
            if cfg.get("repeat_kronos"):
                stage2 = tempfile.mkdtemp(prefix="bt436-repeat-")
                try:
                    shutil.copytree(os.path.join(stage, "collected"),
                                    os.path.join(stage2, "collected"))
                    shutil.copytree(os.path.join(stage, "digest"),
                                    os.path.join(stage2, "digest"))
                    os.remove(os.path.join(stage2,
                                           "digest/ensemble.json"))
                    status, detail = run_runner(
                        "kronos", cfg["runners"]["kronos"], ticker,
                        cutoff, stage2, log, timeout=cfg["timeout"])
                    if status != "ok":
                        result.update(status="error",
                                      reason="repeat kronos: " + detail)
                        return result
                    build_digest(stage2, ticker, cutoff, actions)
                    ens2, err = run_ensemble(
                        stage2, cfg["borsagator_root"], log)
                    if ens2 is None:
                        result.update(status="error",
                                      reason="repeat ensemble: " + err)
                        return result
                    diffs = []
                    for h in ledger.HORIZONS:
                        a = (ens.get("horizons") or {}).get(h) or {}
                        b = (ens2.get("horizons") or {}).get(h) or {}
                        if (a.get("direction"), a.get("expected_move_pct")) \
                                != (b.get("direction"),
                                    b.get("expected_move_pct")):
                            diffs.append(
                                "%s: %s/%s vs %s/%s"
                                % (h, a.get("direction"),
                                   a.get("expected_move_pct"),
                                   b.get("direction"),
                                   b.get("expected_move_pct")))
                    result["determinism"] = {
                        "rerun": True, "diffs": diffs}
                    if diffs:
                        result.update(
                            status="error",
                            reason="kronos non-deterministic: "
                            + "; ".join(diffs))
                        return result
                finally:
                    shutil.rmtree(stage2, ignore_errors=True)
            else:
                result["determinism"] = {"rerun": False}
            # 7. Realised closes (separate fetch, separate file).
            if cfg.get("realised_file"):
                with open(cfg["realised_file"],
                          encoding="utf-8") as f:
                    realised = json.load(f)
                rerr = ""
            else:
                realised, rerr = fetch_realised(
                    ticker, cutoff, fetcher=cfg.get("fetcher"))
            if realised is None:
                result.update(status="skipped",
                              reason=rerr or "realised fetch failed")
                return result
            # The realised file is labelled by its own ticker and
            # cutoff — a file staged under the wrong cell (an ETEL
            # cell handed a COMI realised file) must never be
            # published as this ticker's returns.
            if (str(realised.get("ticker") or "").upper() != ticker
                    or str(realised.get("cutoff") or "")[:10] != cutoff):
                result.update(
                    status="error",
                    reason="realised ticker/cutoff mismatch: file "
                    "says %r/%r, cell is %s/%s"
                    % (realised.get("ticker"), realised.get("cutoff"),
                       ticker, cutoff))
                return result
            # 8. Publish the capture as one unit. The complete
            # capture (files + manifest with their hashes) is
            # written and hashed in a sibling staging directory
            # first; only then is it swapped into place. A rerun
            # that fails before the swap leaves the previous
            # complete capture readable, and the scorer ignores
            # staging/backup directories (no manifest, .tmp-/
            # .old- names) so it never reads a half-written cell.
            publish_dir = cell_dir + ".tmp-%d" % os.getpid()
            if os.path.exists(publish_dir):
                shutil.rmtree(publish_dir)
            os.makedirs(publish_dir)
            for sub in ("collected/kronos", "collected/pandas-ta",
                        "collected/talib", "digest"):
                src = os.path.join(stage, sub)
                dst = os.path.join(publish_dir, sub)
                shutil.copytree(src, dst)
            with open(os.path.join(publish_dir, "price.csv"),
                      "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=["date", "close"])
                w.writeheader()
                w.writerows([{"date": r["date"], "close": r["close"]}
                             for r in base_rows])
            with open(os.path.join(publish_dir, "realised.json"),
                      "w", encoding="utf-8") as f:
                json.dump(realised, f, indent=1, ensure_ascii=False,
                          allow_nan=False)
            shutil.copyfile(log_path,
                            os.path.join(publish_dir, "harness.log"))
            manifest = {
                "tool": TOOL, "version": VERSION, "issue": 436,
                "ticker": ticker, "cutoff": cutoff,
                "status": "ok",
                "gate": gate, "warmup_sessions": n,
                "weights_source": ens.get("weights_source"),
                "base_price": ens.get("base_price"),
                "base_date": ens.get("base_date"),
                "runner_refs": {k: git_head(v) for k, v
                                in cfg["runners"].items()},
                "kronos": {"seed": 42,
                           "pred_len": KRONOS_PRED_LEN,
                           "context_start": CONTEXT_START.get(
                               ticker, DROP_BEFORE)},
                "determinism": result.get("determinism", {}),
                "realised": {"maturity_date":
                             realised.get("maturity_date"),
                             "index_ticker":
                             realised.get("index_ticker")},
                "audit": {"passed": True, "violations": []},
                "files": {},
            }
            for root, _dirs, files in os.walk(publish_dir):
                for name in sorted(files):
                    if name == "manifest.json":
                        continue
                    p = os.path.join(root, name)
                    manifest["files"][os.path.relpath(p, publish_dir)] = \
                        sha256_file(p)
            with open(os.path.join(publish_dir, "manifest.json"),
                      "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=1, ensure_ascii=False,
                          allow_nan=False)
            backup_dir = cell_dir + ".old-%d" % os.getpid()
            if os.path.exists(backup_dir):
                shutil.rmtree(backup_dir)
            try:
                if os.path.exists(cell_dir):
                    os.rename(cell_dir, backup_dir)
                os.rename(publish_dir, cell_dir)
            except OSError:
                if os.path.exists(backup_dir) \
                        and not os.path.exists(cell_dir):
                    os.rename(backup_dir, cell_dir)
                raise
            shutil.rmtree(backup_dir, ignore_errors=True)
            result["manifest"] = manifest
            result.update(status="ok", capture_dir=cell_dir)
            return result
    finally:
        shutil.rmtree(stage, ignore_errors=True)
        if publish_dir:
            # A rerun that failed after staging its publish dir
            # (copying, hashing) leaves the partial copy behind:
            # remove this invocation's own staging. On success
            # the dir was renamed into place, so this is a
            # no-op; the backup holding the previous complete
            # capture is never touched here — on a swap failure
            # it was already restored to the cell.
            shutil.rmtree(publish_dir, ignore_errors=True)


def v1_plan():
    """The v1 plan (design §3 + §4): 12 cutoffs x 6 tickers, with
    POUL contributing zero cutoffs (§1.5) — stated, not omitted."""
    plan = []
    for ticker in TICKERS_V1:
        cutoffs = [] if ticker == "POUL.CA" else list(CUTOFFS_V1)
        plan.append({"ticker": ticker, "cutoffs": cutoffs,
                     "reason": ("usable series starts 2026-09-28 — "
                                "zero v1 cutoffs (design §1.5)")
                     if ticker == "POUL.CA" else ""})
    return {"tool": TOOL, "version": VERSION, "issue": 436,
            "cutoffs": CUTOFFS_V1, "tickers": TICKERS_V1,
            "plan": plan,
            "cells": sum(len(p["cutoffs"]) for p in plan)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cutoff", help="Cutoff date (YYYY-MM-DD).")
    ap.add_argument("--ticker", help="Ticker, e.g. COMI.CA.")
    ap.add_argument("--out-root", default="backtest",
                    help="Capture root (default ./backtest). "
                         "Never the ledger or the archive.")
    ap.add_argument("--kronos-runner", default=None)
    ap.add_argument("--pandas-ta-runner", default=None)
    ap.add_argument("--talib-runner", default=None)
    ap.add_argument("--borsagator-root", default=REPO_ROOT)
    ap.add_argument("--latest-cutoff", default=CUTOFFS_V1[-1],
                    help="Latest cutoff the gate must cover.")
    ap.add_argument("--timeout", type=int, default=1800,
                    help="Seconds per runner (default 1800).")
    ap.add_argument("--repeat-kronos", action="store_true",
                    help="Re-run Kronos and diff directions "
                         "(design §6.4d).")
    ap.add_argument("--no-repeat-kronos", action="store_true")
    ap.add_argument("--realised-file", default=None,
                    help="Use a pre-fetched realised.json instead "
                         "of fetching (offline / tests).")
    ap.add_argument("--plan", action="store_true",
                    help="Print the v1 plan and exit.")
    ap.add_argument("--gate-only", action="store_true",
                    help="Run only the admission gate for --ticker.")
    args = ap.parse_args(argv)
    if args.plan:
        print(json.dumps(v1_plan(), indent=1))
        return 0
    if not args.cutoff or not args.ticker:
        ap.error("--cutoff and --ticker are required (or --plan)")
    if args.gate_only:
        rows, events, ev_ok, ev_error, _dropped = \
            backtest_gate.unpack_fetch(
                backtest_gate.fetch_chart(args.ticker))
        rec = backtest_gate.gate_ticker(
            args.ticker, rows, ev_ok, args.latest_cutoff,
            SERIES_START.get(args.ticker.upper()), ev_error)
        print(json.dumps(rec, indent=1))
        return 0 if rec["passed"] else 1
    # Runner checkouts and the repo root are resolved to absolute
    # paths once, here: run_runner joins the script path to the
    # runner dir AND uses it as the child's cwd, so a relative
    # checkout would be resolved twice (runners/kronos +
    # runners/kronos/scripts/... does not exist), and run_ensemble
    # runs with cwd=stage_dir, so a relative root would resolve
    # from the stage directory instead of the repo.
    runners = {k: (os.path.abspath(v) if v else v)
               for k, v in {"kronos": args.kronos_runner,
                           "pandas-ta": args.pandas_ta_runner,
                           "talib": args.talib_runner}.items()}
    missing = [k for k, v in runners.items() if not v]
    if missing:
        ap.error("runner checkout(s) required: "
                 + ", ".join("--%s-runner" % k.replace("-", "_")
                             for k in missing))
    cfg = {"out_root": args.out_root, "runners": runners,
           "borsagator_root": os.path.abspath(args.borsagator_root),
           "latest_cutoff": args.latest_cutoff,
           "timeout": args.timeout,
           "repeat_kronos": args.repeat_kronos
           and not args.no_repeat_kronos,
           "realised_file": args.realised_file,
           "fetcher": None}
    result = run_cell(args.cutoff, args.ticker, cfg)
    print(json.dumps({k: v for k, v in result.items()
                      if k != "manifest"}, indent=1, default=str))
    return 0 if result["status"] in ("ok", "skipped") else 1


if __name__ == "__main__":
    sys.exit(main())
