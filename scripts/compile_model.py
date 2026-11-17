#!/usr/bin/env python3
"""Report Model compiler: one archived sweep -> one versioned Report Model JSON (issue #68).

Reads a sweep dir (``digest.json`` + ``ensemble.json`` when present +
``collected/<tool>/summary.json``) and writes ``report-model.json``
into the same dir (decision D-2). Stdlib only, deterministic, no LLM,
no network: every number traces to a source field in the sweep dir,
the archive commit, or the main-branch ledger/profile snapshots taken
at compile time.

Decisions adopted from #68 comment 6943619608 (see the #68 deep
scoping, ``hidden_files/issue-68/issue-68-scoping.md``):
  D-1  standalone ``scripts/compile_model.py`` (this file).
  D-2  model lives as ``report-model.json`` inside the sweep dir.
  D-3  build now against Actions sweeps; prove on the first
       worker-merged sweep when #67 lands (synthetic worker case
       until then).
  D-4  emit degraded models with flags, never hold -- except the
       three fail-loudly cases: F-1 ticker mismatch, F-5 unverifiable
       digest, F-9 unknown status.
  D-5  ``levels`` computed by the compiler as ``base x (1 + pct/100)``
       from the WEEK horizon range.
  D-6  LLM vote without provenance is warn-only in v1 (F-12).
  D-7  strict schema versioning: any field change increments
       ``model_version`` and the ``schema`` string; consumers refuse
       unknown versions (``--check-model``).
  D-8  never embed news bodies (pointers to archived files only).
  D-9  start from the next live sweep; backfill only the golden
       pairs #70 needs.
  D-10 no Muhammad decision.

Exit codes: 0 = model emitted (clean or degraded); 2 = refused
(fail-loudly: no model, ``compile_error.txt`` written next to the
would-be model); 1 = crash.

Usage:
    compile_model.py <sweep_dir> [--repo-root PATH]
                     [--archive-sha SHA] [--compiler-sha SHA]
                     [--profiles-dir PATH] [--out PATH]
                     [--sharia-standards AAOIFI,EGX33]
    compile_model.py --check-model <report-model.json>

The compiler never re-reads the ledger to "correct" a sweep: the
ensemble's pinned weights are the forecast's weights at sweep time
(``ledger_pin`` records both the sweep-time SHA and the main-current
SHA plus whether they match). It never dedups corporate actions, never
recomputes a forecast, and never invents a field an input lacks --
absent input fields normalise to ``null`` and are recorded in
``ensemble_shape``.

Sharia section (issue #170): every model carries a ``sharia`` block
projected from the Sharia engine's stored verdict tables
(``<repo-root>/sharia/verdicts-<standard>.json``, issue #168) for
the standards named by ``--sharia-standards`` (default: all
implemented standards). The compiler consumes the engine's tables
and API only -- it re-implements no screening logic. An unknown or
unimplemented standard refuses the compile: the job errors clearly
rather than silently dropping it. A selected standard with no
stored row for the ticker renders as ``insufficient-data`` with the
gap named -- never a blank or silently partial section. Standards
that define no purification rule (EGX33) are excluded from the
block's average purification ratio, and the exclusion is shown in
the block itself, never hidden. The block is additive, so the
schema stays ``borsagator-report-model/1``: every existing
consumer reads named fields only (``delta.model_to_view`` carries
the block through for the renderer, unread by the diff core). A
change to an existing field's meaning still bumps the version
under D-7.
"""
import argparse
import csv
import glob
import hashlib
import json
import math
import os
import re
import subprocess
import sys
from datetime import datetime
from email.utils import parsedate_to_datetime

MODEL_VERSION = 1
SCHEMA = "borsagator-report-model/1"
COMPILER_PATH = "scripts/compile_model.py"

VOTING_FAMILIES = ("price-forecast", "technicals", "sentiment",
                   "agent", "fundamentals")
EXCLUDED_PRICE_CATEGORIES = ("backtest", "stats")
KNOWN_STATUSES = ("ok", "failed", "no-summary", "error")
DEGRADED_REASONS = ("keyless", "partial-fleet", "no-base-price",
                    "merge-failed")
# Tripwire sanity band: a price series' last close must agree with
# the ensemble base within this fraction after ex-date adjustment
# (the 25% anchor ``realized_sigma`` uses, ensemble.py:311-315).
SANITY_PCT = 0.25
# A credential key is an exact known name, an ``_API_KEY`` suffix,
# or a TOKEN / SECRET / PASSWORD-style component. The component test
# is a SUBSTRING test, not a whole-part test: concatenated /
# camelCase spellings (apiKey, accessToken, clientSecret, secretKey)
# split to a single part and would otherwise match nothing (#150).
# A bare ``KEY`` alone is NOT enough: tools legitimately emit
# ``*_stat_key`` metrics (bt), which are data, not credentials —
# ``KEY`` only counts together with ``API``.
SECRET_PATTERNS = ("TOKEN", "SECRET", "PASSWORD", "PRIVATE",
                   "BEARER", "SESSION", "COOKIE", "CREDENTIAL", "AUTH")
KNOWN_SECRET_NAMES = ("COHERE_API_KEY", "SIMFIN_API_KEY",
                      "GATOR_BUS_URL", "GH_TOKEN",
                      "BORSAGATOR_APP_PRIVATE_KEY", "FMP_API_KEY")
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# Benchmark entrant files frozen by scripts/benchmark_freeze.py (#79).
BENCHMARK_ENTRANTS = ("family-price-forecast", "family-technicals",
                      "family-sentiment", "family-agent",
                      "family-fundamentals", "kronos-alone",
                      "raw-llm-cohere", "buy-and-hold")


class CompileError(Exception):
    """A fail-loudly refusal: no model is emitted."""


class _NonFinite:
    """A NaN / Infinity token found while loading JSON. ``json.load``
    accepts bare NaN/Infinity by default; the compiler must see them
    to coerce them to null (F-3) instead of silently passing them
    through. Equality is by token so the F-5 parsed comparison still
    works on inputs that carry one."""

    __slots__ = ("token",)

    def __init__(self, token):
        self.token = token

    def __eq__(self, other):
        return isinstance(other, _NonFinite) and \
            self.token == other.token

    def __hash__(self):
        return hash(("nonfinite", self.token))

    def __repr__(self):
        return self.token


def _load_json_lenient(path):
    """Load JSON, turning NaN / Infinity / -Infinity into
    ``_NonFinite`` sentinels instead of floats."""
    with open(path, encoding="utf-8") as handle:
        return json.load(handle,
                         parse_constant=lambda c: _NonFinite(c))


def _load_json_strict(path):
    """Load JSON, rejecting NaN / Infinity outright."""
    def _reject(constant):
        raise ValueError(f"non-finite constant {constant!r} in JSON")
    with open(path, encoding="utf-8") as handle:
        return json.load(handle, parse_constant=_reject)


def _replace_nonfinite(obj):
    """Walk a structure, replacing sentinels with float NaN so it can
    be re-serialised with ``allow_nan=True`` (canonical-form check)."""
    if isinstance(obj, _NonFinite):
        return float("nan")
    if isinstance(obj, dict):
        return {k: _replace_nonfinite(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_replace_nonfinite(v) for v in obj]
    return obj


def _canonical_bytes(obj):
    """The byte form the Actions EMITTER / orchestrator writes:
    ``json.dumps(obj, indent=2)``, no trailing newline."""
    return json.dumps(_replace_nonfinite(obj), indent=2).encode("utf-8")


def _sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def _fnum(value):
    """Parse a number; None for anything missing, non-numeric, or
    non-finite (NaN / Infinity are rejected, never coerced)."""
    if value is None or isinstance(value, bool) \
            or isinstance(value, _NonFinite):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def _iso_date(value):
    """First 10 chars of an ISO date/datetime, or None."""
    if not value:
        return None
    text = str(value)[:10]
    return text if ISO_DATE_RE.match(text) else None


def _rfc2822_to_iso(value):
    """RFC-2822 date -> ISO UTC string, or None when unparseable."""
    try:
        return parsedate_to_datetime(str(value)).strftime(
            "%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return None


def _git_rev_parse(repo_dir, rev):
    try:
        out = subprocess.run(
            ["git", "-C", repo_dir, "rev-parse", rev],
            capture_output=True, text=True, timeout=30)
    except Exception:
        return None
    text = (out.stdout or "").strip()
    return text if out.returncode == 0 and text else None


# ---------------------------------------------------------------- coercion

def _is_secret_key(key):
    """A metric/summary key that names a credential (R-12). Exact
    known names, an ``_API_KEY`` suffix, or a TOKEN / SECRET /
    PASSWORD-style component. The component test is a SUBSTRING
    test on the upper-cased key, so concatenated / camelCase
    spellings (``apiKey``, ``accessToken``, ``clientSecret``,
    ``secretKey``) are caught too (#150). A bare ``KEY`` alone
    (``total_return_stat_key``, ``monkey``) is a tool metric, not
    a credential, and is kept — ``KEY`` only counts together with
    ``API``."""
    upper = str(key).upper()
    if upper in KNOWN_SECRET_NAMES:
        return True
    if any(p in upper for p in ("TOKEN", "SECRET", "PASSWORD")):
        return True
    if "API" in upper and "KEY" in upper:
        return True
    parts = re.split(r"[^A-Z0-9]+", upper)
    return any(p in SECRET_PATTERNS for p in parts)


def coerce_metrics(metrics, tool, coercion_failed, secret_dropped):
    """Typed coercion of one tool's flat metrics dict (scoping §1c).
    Numeric strings -> numbers; the raw string is kept alongside as
    ``{field}_raw`` only when the conversion is lossy (``repr`` does
    not round-trip the original); non-finite values -> null +
    ``coercion_failed`` entry; secret-pattern keys are dropped, never
    copied (R-12). Returns the coerced dict."""
    if not isinstance(metrics, dict):
        return {}
    out = {}
    for field, value in metrics.items():
        if _is_secret_key(field):
            secret_dropped.append({"tool": tool, "field": field})
            continue
        if isinstance(value, _NonFinite):
            coercion_failed.append(
                {"tool": tool, "field": field, "raw_value": value.token,
                 "reason": "non-finite value"})
            out[field] = None
            continue
        if isinstance(value, bool) or value is None:
            out[field] = value
            continue
        if isinstance(value, (int, float)):
            if isinstance(value, float) and not math.isfinite(value):
                coercion_failed.append(
                    {"tool": tool, "field": field,
                     "raw_value": repr(value),
                     "reason": "non-finite value"})
                out[field] = None
                continue
            out[field] = value
            continue
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.lower() in ("nan", "infinity", "-infinity",
                                    "+infinity"):
                coercion_failed.append(
                    {"tool": tool, "field": field, "raw_value": value,
                     "reason": "non-finite value"})
                out[field] = None
                continue
            if re.fullmatch(r"-?\d+", stripped):
                try:
                    out[field] = int(stripped)
                    continue
                except ValueError:
                    pass
            if re.fullmatch(r"-?\d+\.\d+([eE][+-]?\d+)?", stripped) or \
                    re.fullmatch(r"-?\d+[eE][+-]?\d+", stripped):
                try:
                    num = float(stripped)
                except ValueError:
                    num = None
                if num is not None and math.isfinite(num):
                    out[field] = num
                    if repr(num) != stripped:
                        out[field + "_raw"] = value
                    continue
                coercion_failed.append(
                    {"tool": tool, "field": field, "raw_value": value,
                     "reason": "non-finite value"})
                out[field] = None
                continue
            if field.endswith("_date") or field == "date":
                if ISO_DATE_RE.match(stripped):
                    out[field] = value
                    continue
                try:
                    datetime.fromisoformat(
                        stripped.replace("Z", "+00:00"))
                    # An ISO datetime (e.g. the yahooquery dividend
                    # row's "2026-11-16 10:00:00+02:00") is a valid
                    # date value; kept raw, never reformatted.
                    out[field] = value
                    continue
                except ValueError:
                    pass
                if _rfc2822_to_iso(value) is not None:
                    # Kept raw in metrics; the news section carries
                    # the ISO form. Never silently reformatted.
                    out[field] = value
                    continue
                coercion_failed.append(
                    {"tool": tool, "field": field, "raw_value": value,
                     "reason": "unparseable date"})
                out[field] = value
                continue
            out[field] = value
            continue
        # Non-scalar metric (the EMITTER only emits scalars).
        coercion_failed.append(
            {"tool": tool, "field": field,
             "raw_value": json.dumps(value)[:120],
             "reason": "non-scalar metric value"})
        out[field] = None
    return out


def sanitize_summary(summary, tool, coercion_failed, secret_dropped):
    """Coerce a whole summary dict: metrics through
    :func:`coerce_metrics`, any other non-finite value anywhere in
    the structure to null with a ``coercion_failed`` entry (F-3).
    Returns the sanitised summary."""
    if not isinstance(summary, dict):
        return summary

    def _walk(obj, path):
        if isinstance(obj, _NonFinite):
            coercion_failed.append(
                {"tool": tool, "field": path, "raw_value": obj.token,
                 "reason": "non-finite value"})
            return None
        if isinstance(obj, dict):
            out = {}
            for key, val in obj.items():
                if key == "metrics" and path == "":
                    out[key] = coerce_metrics(
                        val, tool, coercion_failed, secret_dropped)
                elif _is_secret_key(key) and path == "":
                    # A secret-pattern key at the summary top level
                    # (a runner dumping env into its summary) is
                    # dropped, never copied (R-12).
                    secret_dropped.append({"tool": tool, "field": key})
                else:
                    out[key] = _walk(val, f"{path}.{key}" if path
                                     else str(key))
            return out
        if isinstance(obj, list):
            return [_walk(v, f"{path}[{i}]")
                    for i, v in enumerate(obj)]
        if isinstance(obj, float) and not math.isfinite(obj):
            coercion_failed.append(
                {"tool": tool, "field": path, "raw_value": repr(obj),
                 "reason": "non-finite value"})
            return None
        return obj

    return _walk(summary, "")


# ---------------------------------------------------------------- job shape

def normalize_job_shape(job):
    """Normalized job shape: kind (+ subkind for category/run) +
    ticker + trailing filters (delta.py's rule, shared so #70's
    resolver and the model agree)."""
    if not job:
        return ""
    parts = str(job).split()
    if not parts:
        return ""
    kind = parts[0]
    ticker = next((p for p in parts if "." in p), "")
    rest = [p for p in parts[1:] if p != ticker]
    if kind in ("category", "run") and rest:
        shape = f"{kind} {rest[0]}"
        rest = rest[1:]
    else:
        shape = kind
    if ticker:
        shape += f" {ticker}"
    if rest:
        shape += " " + " ".join(rest)
    return shape


def market_from_job(job):
    """Market token parsed from the job string; None when absent,
    never inferred from the tool set."""
    match = re.search(r"market=([A-Za-z]+)", str(job or ""))
    return match.group(1).upper() if match else None


def job_kind(job):
    parts = str(job or "").split()
    return parts[0] if parts else ""


def is_sweep_shape(job):
    return job_kind(job) in ("sweep", "sweep-lite")


def planned_tools(job, registry):
    """The worker's parse_job selection, re-derived from the job
    string + registry (merge.py's rule, same grammar, same trailing
    filters). Sweep / sweep-lite only; category / run jobs return the
    tools of their named category / the single named tool."""
    tools = {t["id"]: t for t in (registry or {}).get("tools", [])
             if t.get("status") == "active"}
    parts = str(job or "").split()
    if not parts or len(parts) < 2:
        return []
    kind = parts[0]
    ticker = parts[1]
    if kind in ("sweep", "sweep-lite"):
        sel = [(t, ticker) for t, v in tools.items()
               if kind == "sweep" or v.get("category") != "agent"]
        for tok in parts[2:]:
            if tok.startswith("market="):
                mkt = tok.split("=", 1)[1].upper()
                sel = [(t, tk) for t, tk in sel
                       if mkt in [m.upper()
                                  for m in tools[t].get("markets", [])]]
            elif tok == "no-agent":
                sel = [(t, tk) for t, tk in sel
                       if tools[t].get("category") != "agent"]
            else:
                return []
        return [(t, tk) for t, tk in sel if t in tools]
    if kind == "category":
        cat = parts[1] if len(parts) > 1 else ""
        return [(t, ticker) for t, v in tools.items()
                if v.get("category") == cat]
    if kind == "run":
        tool = parts[1] if len(parts) > 1 else ""
        return [(tool, ticker)] if tool in tools else []
    return []


# ---------------------------------------------------------------- price series

def read_price_series(sweep_dir, ticker, registry):
    """Last close-bearing row per price source, mirroring
    ``ensemble.py`` price_series / ``delta.py`` _read_price_series:
    registry categories backtest/stats excluded; filename must
    contain ohlc / indicators / the ticker code (so Kronos
    forecast.csv is excluded: it is a forecast, not a price
    series); rows < 5 skipped; the last row with a parseable finite
    close wins, never the literal last CSV row (the yahooquery
    dividend-row trap: its last row carries dividends, no OHLC).
    Volume / OHLC come from that same row, or None when the row has
    no usable value (never faked from another source)."""
    code = re.sub(r"[^a-z0-9]", "", ticker.split(".")[0].lower())
    collected = os.path.join(sweep_dir, "collected")
    categories = {t.get("id"): t.get("category")
                  for t in (registry or {}).get("tools", [])}
    series = []
    excluded = []
    for path in sorted(glob.glob(os.path.join(collected, "*", "*.csv"))):
        tool = os.path.basename(os.path.dirname(path))
        name = os.path.basename(path)
        lname = name.lower()
        if categories.get(tool) in EXCLUDED_PRICE_CATEGORIES:
            continue
        if "forecast" in lname:
            excluded.append(
                f"{tool}/{name}: forecast rows, not actuals")
            continue
        if not any(s in lname for s in ("ohlc", "indicators", code)):
            continue
        try:
            with open(path, newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
        except Exception:
            continue
        if len(rows) < 5 or not rows[0]:
            continue
        header = [c for c in rows[0] if c]
        lower = [c.strip().lower() for c in header]
        close_col = next((header[i] for i, c in enumerate(lower)
                          if c in ("close", "adj close", "adjclose")),
                         None)
        if not close_col:
            continue
        date_col = next((header[i] for i, c in enumerate(lower)
                         if "date" in c
                         or c in ("datetime", "index")), None)
        vol_col = next((header[i] for i, c in enumerate(lower)
                        if c in ("volume", "vol")), None)
        open_col = next((header[i] for i, c in enumerate(lower)
                         if c == "open"), None)
        high_col = next((header[i] for i, c in enumerate(lower)
                         if c == "high"), None)
        low_col = next((header[i] for i, c in enumerate(lower)
                        if c == "low"), None)
        last = None
        last_idx = None
        for idx, row in enumerate(rows):
            close = _fnum(row.get(close_col))
            if close is None:
                continue
            entry = {"last_date": _iso_date(row.get(date_col))
                     if date_col else None,
                     "last_close": close,
                     "last_volume": _fnum(row.get(vol_col))
                     if vol_col else None,
                     "last_open": _fnum(row.get(open_col))
                     if open_col else None,
                     "last_high": _fnum(row.get(high_col))
                     if high_col else None,
                     "last_low": _fnum(row.get(low_col))
                     if low_col else None}
            last = entry
            last_idx = idx
        if last is None:
            continue
        last["source"] = f"{tool}/{name}"
        last["rows"] = len(rows)
        note = None
        if last_idx is not None and last_idx != len(rows) - 1:
            tail = rows[-1]
            div = tail.get("dividends") or tail.get("dividend")
            if div not in (None, "", "0", "0.0"):
                note = ("last row is a dividend row "
                        f"(dividends {div}, no OHLC); last "
                        "close-bearing row used")
            else:
                note = ("last close-bearing row is not the literal "
                        "last row")
        if last["last_volume"] is None:
            vol_note = ("no usable volume on the last close-bearing "
                        "row")
            note = f"{note}; {vol_note}" if note else vol_note
        last["note"] = note
        series.append(last)
    series.sort(key=lambda s: (not s["source"].startswith("egx-data/"),
                               s["source"]))
    freshest = None
    for entry in series:
        if entry["last_date"] and (freshest is None
                                   or entry["last_date"] > freshest):
            freshest = entry["last_date"]
    for entry in series:
        entry["stale"] = entry["last_date"] is None or \
            (freshest is not None and entry["last_date"] < freshest)
    return series, excluded


# ---------------------------------------------------------------- news

def identity_key(item):
    """Derived news/disclosure identity (delta.py's rule, shared):
    ``resolved_url`` when present, else a hash of (title, date)."""
    url = (item or {}).get("resolved_url")
    if url:
        return str(url), "resolved_url"
    title = str((item or {}).get("title") or "")
    date = str((item or {}).get("date") or "")
    digest = hashlib.sha256(
        f"{title}|{date}".encode("utf-8")).hexdigest()
    return digest[:16], "title-date-hash"


def read_news_items(sweep_dir, filename):
    """Identity keys + titles for one feed file. Missing file ->
    empty list (a sweep without the feed has no items, not zero
    items). Bodies are never read, never embedded (D-8)."""
    path = os.path.join(sweep_dir, "collected", "news-disclosure",
                        filename)
    try:
        doc = _load_json_lenient(path)
    except Exception:
        return [], False
    items = []
    for entry in doc.get("items", []) or []:
        key, key_type = identity_key(entry)
        items.append({"identity_key": key, "key_type": key_type,
                      "title": entry.get("title"),
                      "date": entry.get("date"),
                      "source": entry.get("source")})
    return items, True


# ---------------------------------------------------------------- tripwire

def ex_date_adjustment(last_date, base_date, corporate_actions):
    """Mechanical adjustment for a series whose last close predates
    an ex-date inside (last_date, base_date]: the COMPOUNDED
    fraction of EVERY dated action in that window, or None when no
    dated action applies.

    Each action's mechanical_pct is ``-dps / base * 100`` against
    the same ensemble base (ensemble.py), so two in-window actions
    drop the price by dps1 + dps2 off that one base -- the
    compounded fraction is the SUM of the fractions. (Multiplicative
    compounding would understate the drop by the m1*m2 cross-term
    and is wrong for this definition.) In-window actions are summed
    in (ex_date, mechanical_pct) order so the result never depends
    on disclosure-item order. An unparseable mechanical_pct on any
    in-window action returns None (fail closed, as before: the
    tripwire then compares the unadjusted close and can only
    false-flag, never false-pass)."""
    if not last_date or not base_date:
        return None
    in_window = []
    for action in corporate_actions or []:
        ex_date = action.get("ex_date")
        mech = action.get("mechanical_pct")
        if not ex_date or mech is None:
            continue
        if last_date < ex_date <= base_date:
            in_window.append((ex_date, mech))
    if not in_window:
        return None
    total = 0.0
    for _ex_date, mech in sorted(in_window, key=lambda pair: (
            pair[0], str(pair[1]))):
        try:
            total += float(mech) / 100.0
        except (TypeError, ValueError):
            return None
    return total


def tripwire(digest, ensemble, series, base_source):
    """Ticker-consistency tripwire (scoping §6 F-1, rescoped).
    Checks, in order:
      1. ensemble.ticker != digest.ticker -> refuse.
      2. ensemble.base_source names a file for another ticker
         (a ``<code>`` file whose code is not the digest ticker's,
         and not a generic ohlc/indicators file) -> refuse.
         A non-file base source ("consensus median") is skipped.
      3. every selected price series' last close agrees with the
         ensemble base within SANITY_PCT after ex-date adjustment
         -> refuse on disagreement.
      4. any summary envelope ticker != digest ticker -> refuse.
    Explicitly NOT checked: metrics.ticker on backtest / stats /
    reference tools (AAPL is legitimate there), prose metric
    values, tools with no ticker metric at all. Returns the list of
    mismatch dicts (empty = clean)."""
    problems = []
    digest_ticker = (digest or {}).get("ticker")
    ens_ticker = (ensemble or {}).get("ticker")
    if ens_ticker and digest_ticker and ens_ticker != digest_ticker:
        problems.append({"field": "ensemble.ticker",
                         "expected": digest_ticker, "found": ens_ticker})
    if digest_ticker and base_source and "/" in str(base_source):
        code = re.sub(r"[^a-z0-9]", "",
                      digest_ticker.split(".")[0].lower())
        fname = os.path.basename(str(base_source)).lower()
        if code not in fname and "ohlc" not in fname \
                and "indicators" not in fname:
            problems.append({"field": "ensemble.base_source",
                             "expected": digest_ticker,
                             "found": base_source})
    base_price = _fnum((ensemble or {}).get("base_price"))
    base_date = _iso_date((ensemble or {}).get("base_date"))
    actions = (ensemble or {}).get("corporate_actions") or []
    if base_price:
        for entry in series or []:
            close = entry.get("last_close")
            if close is None:
                continue
            adj = ex_date_adjustment(entry.get("last_date"), base_date,
                                     actions)
            check = close * (1.0 + adj) if adj is not None else close
            if abs(check / base_price - 1.0) > SANITY_PCT:
                problems.append({
                    "tool": entry["source"].split("/")[0],
                    "expected": digest_ticker,
                    "found": (f"{entry['source']} last close "
                              f"{close} at {entry.get('last_date')} "
                              f"vs base {base_price}"),
                    "field": "price_series_last"})
    for result in (digest or {}).get("results", []) or []:
        summary = result.get("summary") or {}
        found = summary.get("ticker")
        if found and digest_ticker and found != digest_ticker:
            problems.append({"field":
                             f"summary.ticker:{result.get('tool')}",
                             "expected": digest_ticker,
                             "found": found})
    return problems


# ---------------------------------------------------------------- sections

def build_llm(tools, family_scores):
    """The #74 provenance block, v1 reality: no registry/llms.json,
    no token or cost field anywhere in borsagator. Records what
    exists -- one calls entry per tool whose summary carries an
    llm_provider / translation_provider / model metric -- with
    tokens/cost null ("not recorded") and llm_status
    "not-recorded". The agent-vote-without-provenance tripwire is
    warn-only in v1 (D-6): it returns the flag, it never refuses."""
    calls = []
    for entry in tools:
        summary = entry.get("summary") or {}
        metrics = summary.get("metrics") or {}
        tool = entry["tool"]
        provider = metrics.get("llm_provider")
        if provider is not None:
            calls.append({"tool": tool, "role": "llm",
                          "provider": provider,
                          "model": metrics.get("llm_model"),
                          "source": None, "tokens_in": None,
                          "tokens_out": None, "usd": None,
                          "fallback_from": None})
        translator = metrics.get("translation_provider")
        if translator is not None:
            calls.append({"tool": tool, "role": "translation",
                          "provider": translator, "model": None,
                          "source": None, "tokens_in": None,
                          "tokens_out": None, "usd": None,
                          "fallback_from": None})
        model = metrics.get("model")
        if model is not None and provider is None:
            calls.append({"tool": tool, "role": "model",
                          "provider": None, "model": model,
                          "source": None, "tokens_in": None,
                          "tokens_out": None, "usd": None,
                          "fallback_from": None})
    flags = []
    agent_score = (family_scores or {}).get("agent")
    agent_tools = [t for t in tools
                   if t.get("category") == "agent"]
    agent_proven = any(
        c["tool"] == t["tool"] for c in calls for t in agent_tools)
    if agent_score is not None and agent_tools and not agent_proven:
        flags.append("llm-provenance-missing: agent vote without "
                     "provider/model")
    return {"list_version": None, "calls": calls,
            "budget": {"cap_usd": None, "spent_usd": None,
                       "status": None},
            "llm_status": "not-recorded"}, flags


def build_levels(ensemble):
    """D-5 / #77 D2: support / resistance as price levels from the
    WEEK horizon range: base x (1 + pct/100). A unit conversion of
    fields the model already carries, not a forecast. Returns
    (levels_or_None, flag_or_None)."""
    if not ensemble:
        return None, "levels-unavailable: no ensemble"
    base = _fnum(ensemble.get("base_price"))
    week = (ensemble.get("horizons") or {}).get("week") or {}
    low = _fnum(week.get("range_low_pct"))
    high = _fnum(week.get("range_high_pct"))
    if base is None or low is None or high is None:
        return None, "levels-unavailable: no week horizon range"
    return {"support": round(base * (1.0 + low / 100.0), 4),
            "resistance": round(base * (1.0 + high / 100.0), 4),
            "basis": ("week horizon range_low_pct / range_high_pct "
                      "(expected_move_pct +/- half-range, % of base)"),
            "note": ("descriptive-conditional levels (D2); not a "
                     "buy/sell instruction")}, None


def build_benchmark(sweep_dir):
    """#79: read the frozen benchmark entrants from the staged
    ``benchmark/`` dir -- pointers + SHAs only, never recomputed,
    never embedded in full."""
    bench_dir = os.path.join(sweep_dir, "benchmark")
    if not os.path.isdir(bench_dir):
        return {"present": False, "entrants": [], "files": {},
                "statuses": {}}
    files = {}
    statuses = {}
    for name in sorted(os.listdir(bench_dir)):
        path = os.path.join(bench_dir, name)
        if not os.path.isfile(path) or not name.endswith(".json"):
            continue
        files[name] = _sha256_file(path)
        try:
            doc = _load_json_lenient(path)
            statuses[name] = doc.get("status") if isinstance(
                doc, dict) else None
        except Exception:
            statuses[name] = None
    error_path = os.path.join(bench_dir, "freeze_error.txt")
    out = {"present": bool(files),
           "entrants": [n[:-5] for n in sorted(files)],
           "files": files, "statuses": statuses}
    if os.path.isfile(error_path):
        out["freeze_error"] = True
    return out


# ---------------------------------------------------------------- sharia

# The average is labelled as exactly what it is -- an average of
# per-standard ratios -- never as a standard's own figure (#170).
AVG_PURIFICATION_LABEL_EN = (
    "Average purification ratio across the selected standards that "
    "define a purification rule (an average of per-standard ratios; "
    "not a figure of any single standard)")
AVG_PURIFICATION_LABEL_AR = (
    "متوسط نسبة التطهير عبر المعايير المختارة التي تعرّف قاعدة تطهير "
    "(متوسط لنسب كل معيار على حدة، وليس رقمًا خاصًا بمعيار واحد)")


def _load_sharia_engine():
    """Import the sibling Sharia engine (issue #168). The compiler
    consumes its API only -- the implemented-standard list and the
    framing lines -- and its stored verdict tables; no screening
    logic is re-implemented here."""
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    try:
        import sharia_engine
    except Exception as exc:
        raise CompileError(f"sharia engine unavailable: {exc}")
    return sharia_engine


def resolve_sharia_standards(requested):
    """Validate the ``sharia_standards`` job parameter (issue #170).

    ``None`` selects all implemented standards. Any unknown or
    unimplemented id refuses the compile (fail loudly): the job
    errors clearly rather than silently dropping the standard.
    Returns (resolved_ids, engine_module)."""
    engine = _load_sharia_engine()
    implemented = engine.available_standards()
    if requested is None:
        return list(implemented), engine
    resolved = []
    for raw in requested:
        std = str(raw).strip().upper()
        if not std:
            continue
        if std not in implemented:
            raise CompileError(
                f"unknown sharia standard {raw!r} in "
                f"sharia_standards: implemented standards are "
                f"{', '.join(implemented)}")
        if std not in resolved:
            resolved.append(std)
    if not resolved:
        raise CompileError(
            "sharia_standards parameter names no standard")
    return resolved, engine


def load_sharia_table(repo_root, standard):
    """Load the engine's stored verdict table
    ``<repo-root>/sharia/verdicts-<standard>.json``; ``None`` when
    the table file is absent or unreadable (the section renders
    that as insufficient-data, never as a silent skip)."""
    path = os.path.join(repo_root, "sharia",
                        f"verdicts-{standard.lower()}.json")
    if not os.path.isfile(path):
        return None
    try:
        doc = _load_json_lenient(path)
    except Exception:
        return None
    return doc if isinstance(doc, dict) else None


def build_sharia_section(ticker, requested, standards, tables,
                         engine):
    """Assemble the model's ``sharia`` block (issue #170) from the
    engine's stored verdict tables. Pure projection of the rows the
    engine emitted: verdict, ratio table, purification, statement
    period, rule-set version, the denominator variant where the
    rule set has one, and the not-a-fatwa framing -- in both
    languages, at section level and on every per-standard entry.

    A selected standard whose table is missing, or which has no
    row for the ticker, renders as ``insufficient-data`` with the
    gap named in ``missing_inputs``. The average purification
    ratio covers only the selected standards that define a
    purification rule AND produced a ratio; every other selected
    standard is listed under ``excluded`` with its reason.
    Returns (section, flags)."""
    entries = []
    flags = []
    included = []
    excluded = []
    for std in standards:
        table = tables.get(std)
        meta = (table or {}).get("standard") or {}
        entry = {
            "standard": std,
            "name_en": meta.get("name_en"),
            "name_ar": meta.get("name_ar"),
            "ruleset_version": meta.get("ruleset_version"),
            "engine_version": (table or {}).get("engine_version"),
            "source_table": f"sharia/verdicts-{std.lower()}.json",
            "table_generated_at": (table or {}).get("generated_at"),
            "verdict": "insufficient-data",
            "statement_period": None,
            "screening_date": None,
            "parameters": {},
            "denominator_variant": None,
            "activity": {"classification": None,
                         "evidence_source": None},
            "ratios": [],
            "purification": {"defined": False, "ratio": None,
                             "per_share": None},
            "missing_inputs": [],
            "framing_en": engine.FRAMING_EN,
            "framing_ar": engine.FRAMING_AR,
        }
        row = None
        if table is None:
            entry["missing_inputs"] = [
                f"stored verdict table "
                f"sharia/verdicts-{std.lower()}.json"]
            flags.append(f"sharia-table-missing: {std}")
        else:
            row = next((r for r in table.get("rows") or []
                        if r.get("ticker") == ticker), None)
            if row is None:
                entry["missing_inputs"] = [
                    f"verdict row for {ticker} in "
                    f"sharia/verdicts-{std.lower()}.json"]
                flags.append(f"sharia-row-missing: {std} {ticker}")
        if row is not None:
            entry.update({
                "ruleset_version": row.get("ruleset_version"),
                "engine_version": row.get("engine_version"),
                "verdict": row.get("verdict"),
                "statement_period": row.get("statement_period"),
                "screening_date": row.get("screening_date"),
                "parameters": row.get("parameters") or {},
                "denominator_variant":
                    (row.get("parameters") or {}).get(
                        "denominator_variant"),
                "activity": row.get("activity") or entry["activity"],
                "ratios": row.get("ratios") or [],
                "purification": row.get("purification")
                or entry["purification"],
                "missing_inputs": row.get("missing_inputs") or [],
                "framing_en": row.get("framing_en")
                or engine.FRAMING_EN,
                "framing_ar": row.get("framing_ar")
                or engine.FRAMING_AR,
            })
            if entry["verdict"] == "insufficient-data":
                flags.append(f"sharia-insufficient-data: {std}")
        entries.append(entry)

        # Average-purification membership is decided here, where
        # row presence is known, so the exclusion reason is exact.
        purification = entry["purification"] or {}
        if row is None:
            excluded.append({
                "standard": std,
                "reason": "no verdict row (insufficient-data)"})
        elif not purification.get("defined"):
            excluded.append({
                "standard": std,
                "reason": "standard defines no purification rule"})
        elif purification.get("ratio") is None:
            excluded.append({
                "standard": std,
                "reason": "purification ratio unavailable "
                          "(insufficient-data)"})
        else:
            included.append({"standard": std,
                             "ratio": purification["ratio"]})

    # Disagreement is judged on determinate verdicts only: an
    # insufficient-data entry is an absence of a verdict, not a
    # dissenting one.
    determinate = [e["verdict"] for e in entries
                   if e["verdict"] != "insufficient-data"]
    disagreement = len(set(determinate)) > 1

    average = None
    if included:
        average = round(
            sum(item["ratio"] for item in included)
            / len(included), 6)

    section = {
        "requested": list(requested) if requested is not None
        else None,
        "selection": "parameter" if requested is not None
        else "default-all-implemented",
        "standards": entries,
        "verdicts": {e["standard"]: e["verdict"] for e in entries},
        "disagreement": disagreement,
        "average_purification": {
            "value": average,
            "label_en": AVG_PURIFICATION_LABEL_EN,
            "label_ar": AVG_PURIFICATION_LABEL_AR,
            "included": included,
            "excluded": excluded,
        },
        "framing_en": engine.FRAMING_EN,
        "framing_ar": engine.FRAMING_AR,
    }
    return section, flags


# ---------------------------------------------------------------- compile

def _sweep_rel_path(sweep_dir):
    norm = os.path.normpath(sweep_dir).replace(os.sep, "/")
    for marker in ("sweeps/", "worker-runs/"):
        idx = norm.find(marker)
        if idx >= 0:
            return norm[idx:]
    return os.path.basename(norm)


def _run_id_from(sweep_dir, manifest):
    run_id = (manifest or {}).get("github_run_id") \
        or (manifest or {}).get("run_id")
    if run_id is not None:
        return str(run_id)
    match = re.search(r"__run([A-Za-z0-9_\-]+)$",
                      os.path.basename(os.path.normpath(sweep_dir)))
    return match.group(1) if match else None


def compile_sweep(sweep_dir, repo_root=None, archive_sha=None,
                  compiler_sha=None, profiles_dir=None,
                  sharia_standards=None):
    """Compile one sweep dir into a Report Model dict. Raises
    CompileError on a fail-loudly refusal (F-1 / F-5 / F-9 / F-6 /
    F-10). Degraded models are returned with their flags."""
    sweep_dir = os.path.normpath(sweep_dir)
    if repo_root is None:
        repo_root = os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)))
    if profiles_dir is None:
        profiles_dir = os.path.join(repo_root, "profiles")
    digest_path = os.path.join(sweep_dir, "digest.json")
    ensemble_path = os.path.join(sweep_dir, "ensemble.json")
    manifest_path = os.path.join(sweep_dir, "manifest.json")
    registry_path = os.path.join(sweep_dir, "registry.json")
    if not os.path.isfile(digest_path):
        raise CompileError(f"no digest.json in {sweep_dir}")
    try:
        digest = _load_json_lenient(digest_path)
    except Exception as exc:
        raise CompileError(f"digest.json unreadable in {sweep_dir}: "
                           f"{exc}")
    if not isinstance(digest, dict):
        raise CompileError(f"digest.json is not an object in "
                           f"{sweep_dir}")
    manifest = None
    if os.path.isfile(manifest_path):
        try:
            manifest = _load_json_lenient(manifest_path)
        except Exception:
            manifest = None
    registry = {}
    if os.path.isfile(registry_path):
        try:
            registry = _load_json_lenient(registry_path) or {}
        except Exception:
            registry = {}
    if not registry:
        # Fall back to the checkout's registry (same snapshot the
        # merge stages); a sweep without either is degraded, not
        # refused -- the registry only feeds planned-tool derivation.
        try:
            registry = _load_json_lenient(
                os.path.join(repo_root, "registry", "tools.json")) or {}
        except Exception:
            registry = {}

    flags = []
    job = digest.get("job")
    ticker = digest.get("ticker")
    job_shape = normalize_job_shape(job)
    sweep_shape = is_sweep_shape(job)
    if not ticker:
        raise CompileError(f"digest has no ticker in {sweep_dir}")
    if not job:
        raise CompileError(f"digest has no job in {sweep_dir}")
    finished = digest.get("finished")
    if not finished and sweep_shape:
        # F-10: pair resolution needs finished on a sweep shape.
        raise CompileError(
            f"digest without finished in {sweep_dir} (sweep shape)")
    if not finished:
        flags.append("finished-missing")

    # ---- sharia parameter (issue #170): validate FIRST, so an
    # ---- unknown standard refuses before any heavy verification.
    sharia_resolved, sharia_engine_mod = resolve_sharia_standards(
        sharia_standards)

    ensemble = None
    ensemble_absent = not os.path.isfile(ensemble_path)
    if not ensemble_absent:
        try:
            ensemble = _load_json_lenient(ensemble_path)
        except Exception as exc:
            raise CompileError(f"ensemble.json unreadable in "
                               f"{sweep_dir}: {exc}")
        if not isinstance(ensemble, dict):
            raise CompileError(f"ensemble.json is not an object in "
                               f"{sweep_dir}")
    if ensemble_absent and sweep_shape:
        digest_md = ""
        md_path = os.path.join(sweep_dir, "digest.md")
        if os.path.isfile(md_path):
            try:
                with open(md_path, encoding="utf-8") as handle:
                    digest_md = handle.read()
            except OSError:
                digest_md = ""
        marker = ("NO ensemble forecast" in digest_md) or \
            ((manifest or {}).get("merge") == "no-ensemble")
        if not marker:
            # F-6: a sweep-shape job with no ensemble and no recorded
            # reason is indistinguishable from a lost ensemble.
            raise CompileError(
                f"sweep-shape job {job!r} has no ensemble.json and "
                f"no no-base-price / merge: no-ensemble marker in "
                f"{sweep_dir}")
        flags.append("ensemble-absent: no base price or merge "
                     "no-ensemble (see digest.md)")

    # ---- tools: verify embedded vs collected (F-5), coerce (F-3),
    # ---- unknown status (F-9), base-tool summary (F-2).
    coercion_failed = []
    secret_dropped = []
    tools = []
    tools_failed = []
    ticker_mismatch = []
    registry_by_id = {t.get("id"): t
                      for t in registry.get("tools", [])}
    results = digest.get("results") or []
    if not isinstance(results, list):
        raise CompileError(f"digest results is not a list in "
                           f"{sweep_dir}")
    digest_tools = set()
    for result in results:
        if not isinstance(result, dict):
            raise CompileError(f"digest result is not an object in "
                               f"{sweep_dir}")
        tool = result.get("tool")
        status = result.get("status")
        if status not in KNOWN_STATUSES:
            # F-9: the status vocabulary is closed.
            raise CompileError(
                f"unknown digest-row status {status!r} for tool "
                f"{tool!r} in {sweep_dir}")
        if tool:
            digest_tools.add(tool)
        summary = result.get("summary")
        summary_sha = None
        collected_path = os.path.join(
            sweep_dir, "collected", str(tool), "summary.json") \
            if tool else None
        if summary is not None:
            if not isinstance(summary, dict):
                raise CompileError(
                    f"embedded summary for {tool!r} is not an object "
                    f"in {sweep_dir}")
            if collected_path is None or not os.path.isfile(
                    collected_path):
                # F-5: the verification source is missing; the model
                # must not be emitted on an unverifiable digest.
                raise CompileError(
                    f"embedded summary for {tool!r} has no collected "
                    f"summary.json in {sweep_dir}")
            try:
                collected = _load_json_lenient(collected_path)
            except Exception as exc:
                raise CompileError(
                    f"collected summary.json for {tool!r} unreadable "
                    f"in {sweep_dir}: {exc}")
            if collected != summary:
                keys = sorted(
                    {k for k in list(collected.keys()) +
                     list(summary.keys())
                     if isinstance(collected, dict)
                     and isinstance(summary, dict)
                     and collected.get(k) != summary.get(k)})
                raise CompileError(
                    f"embedded summary for {tool!r} differs from "
                    f"collected summary.json in {sweep_dir} "
                    f"(differing keys: {keys})")
            raw = open(collected_path, "rb").read()
            canon = _canonical_bytes(summary)
            if raw not in (canon, canon + b"\n"):
                flags.append(f"summary-format-diff: {tool} (parsed-"
                             "identical, bytes differ from the "
                             "canonical indent=2 form)")
            summary_sha = _sha256_bytes(raw)
            summary = sanitize_summary(summary, tool, coercion_failed,
                                       secret_dropped)
        else:
            # no-summary / error rows carry no summary; detail
            # instead. A missing collected file here is expected.
            if status in ("ok", "failed"):
                flags.append(f"summary-missing: {tool} ({status})")
        entry = {
            "tool": tool,
            "category": result.get("category") or
            registry_by_id.get(tool, {}).get("category"),
            "repo": result.get("repo") or
            registry_by_id.get(tool, {}).get("repo"),
            "status": status,
            "exit_code": (summary or {}).get("exit_code"),
            "conclusion": result.get("conclusion"),
            "run_url": result.get("run_url"),
            "worker_run": result.get("worker_run"),
            "claim_id": result.get("claim_id"),
            "summary": summary,
            "summary_sha256": summary_sha,
            "report_md_present": bool(tool) and os.path.isfile(
                os.path.join(sweep_dir, "collected", str(tool),
                             "report.md")),
        }
        tools.append(entry)
        if status in ("failed", "no-summary", "error"):
            tools_failed.append({"tool": tool, "status": status,
                                 "detail": result.get("detail")})
    if ensemble is not None:
        base_tool = None
        base_source = str(ensemble.get("base_source") or "")
        if "/" in base_source:
            base_tool = base_source.split("/")[0]
        if base_tool and base_tool in digest_tools:
            row = next((r for r in results
                        if r.get("tool") == base_tool), None)
            if row is not None and "summary" not in row:
                # F-2: the ensemble stands on a price tool with no
                # summary -- the base is unverifiable.
                raise CompileError(
                    f"base-price tool {base_tool!r} has no summary "
                    f"in {sweep_dir}")

    planned = planned_tools(job, registry)
    planned_ids = [t for t, _tk in planned]
    tools_absent = [t for t in planned_ids if t not in digest_tools]
    partial = (not sweep_shape) or bool(tools_absent)
    if tools_absent and sweep_shape:
        # F-6 / §2d: a partial fleet presented as a whole sweep.
        raise CompileError(
            f"planned tools absent from the digest in {sweep_dir}: "
            f"{tools_absent}")

    # ---- price series + tripwire (F-1).
    series, series_excluded = read_price_series(
        sweep_dir, ticker, registry)
    ensemble_for_tripwire = ensemble or {}
    mismatches = tripwire(
        digest, ensemble_for_tripwire, series,
        ensemble_for_tripwire.get("base_source"))
    if mismatches:
        ticker_mismatch.extend(mismatches)
        detail = "; ".join(
            f"{m.get('field', m.get('tool'))}: expected "
            f"{m.get('expected')}, found {m.get('found')}"
            for m in mismatches)
        raise CompileError(
            f"ticker mismatch (F-1) in {sweep_dir}: {detail}")

    # ---- ensemble sections (verbatim passthrough, probed shape).
    if ensemble is None:
        ensemble_shape = {"version": None,
                          "has_applied_weights": False,
                          "has_base_date": False,
                          "has_kronos_ex_rescale": False,
                          "has_price_crosscheck": False,
                          "has_corporate_actions": False,
                          "has_sessions_per_calendar_day": False}
    else:
        ensemble_shape = {
            "version": ensemble.get("version"),
            "has_applied_weights": "applied_weights" in ensemble,
            "has_base_date": "base_date" in ensemble,
            "has_kronos_ex_rescale": "kronos_ex_rescale" in ensemble,
            "has_price_crosscheck": "price_crosscheck" in ensemble,
            "has_corporate_actions": "corporate_actions" in ensemble,
            "has_sessions_per_calendar_day":
                "sessions_per_calendar_day" in ensemble}
    ensemble_empty = bool(ensemble is not None) and \
        not (ensemble.get("horizons") or {})
    if ensemble_empty:
        flags.append("ensemble-empty: horizons is empty (no family "
                     "scored)")
    if ensemble is not None and ensemble.get("base_price") is None:
        flags.append("ensemble-no-base-price")
    if ensemble is not None and not ensemble_shape[
            "has_kronos_ex_rescale"]:
        # Claim (c), settled: the rescale code landed 2026-11-17
        # 01:05 +0200 (#130), after the 16 Nov sweeps ran -- their
        # ensembles carry no kronos_ex_rescale key at all, not a
        # null value. Null here means "rescale state not recorded".
        flags.append("kronos-ex-rescale-not-recorded: ensemble "
                     "predates #130 rescale code")

    price = None
    family_scores = None
    horizons = None
    risk = None
    corporate_actions = None
    kronos_ex_rescale = None
    weights = None
    if ensemble is not None:
        price = {
            "base_price": ensemble.get("base_price"),
            "base_source": ensemble.get("base_source"),
            "base_date": ensemble.get("base_date"),
            "price_crosscheck": ensemble.get("price_crosscheck"),
            "sigma_daily": ensemble.get("sigma_daily"),
            "sigma_source": ensemble.get("sigma_source"),
            "sessions_per_calendar_day": ensemble.get(
                "sessions_per_calendar_day"),
        }
        family_scores = ensemble.get("family_scores")
        horizons = None if ensemble_empty else ensemble.get("horizons")
        risk = ensemble.get("risk")
        corporate_actions = ensemble.get("corporate_actions")
        kronos_ex_rescale = ensemble.get("kronos_ex_rescale")
        weights = {
            "weights_source": ensemble.get("weights_source"),
            "applied_weights": ensemble.get("applied_weights"),
            "confidence_basis": ensemble.get("confidence_basis"),
        }
        cross = ensemble.get("price_crosscheck") or {}
        common = cross.get("common_date")
        base_date = ensemble.get("base_date")
        if common and base_date and common < base_date:
            flags.append(f"witnesses-stale: common_date {common} vs "
                         f"base_date {base_date}")
        base_src_used = str(cross.get("base_source_used") or "")
        if re.search(r"row\d*\b", base_src_used):
            flags.append("base-from-undated-row")
        undated = sum(1 for a in (corporate_actions or [])
                      if isinstance(a, dict)
                      and a.get("ex_date") is None)
        if undated:
            flags.append(f"undated-actions: {undated}")
        if (cross.get("base_source_used") or "") and \
                price is not None:
            base_entry = next(
                (s for s in series
                 if s["source"] == cross.get("base_source_used")),
                None)
            if base_entry is not None and \
                    base_entry.get("last_date") is None:
                flags.append("base-from-undated-row")

    # ---- ledger pin (snapshot, never a live re-read).
    ledger_pin = {"version": None, "counts": None,
                  "weights_file_sha256": None,
                  "weights_file_sha256_at_compile": None,
                  "weights_sha_matches_ensemble": None,
                  "tree_sha": None}
    ledger_path = os.path.join(repo_root, "ledger", "ledger.json")
    weights_path = os.path.join(repo_root, "ledger", "weights.json")
    try:
        ledger = _load_json_lenient(ledger_path)
        ledger_pin["version"] = ledger.get("version")
        ledger_pin["counts"] = ledger.get("counts")
    except Exception:
        flags.append("ledger-unreadable: ledger/ledger.json")
    try:
        ledger_pin["weights_file_sha256_at_compile"] = \
            _sha256_file(weights_path)
    except Exception:
        flags.append("ledger-unreadable: ledger/weights.json")
    if ensemble is not None:
        applied = ensemble.get("applied_weights") or {}
        ledger_pin["weights_file_sha256"] = applied.get("file_sha256")
    both = ledger_pin["weights_file_sha256"] and \
        ledger_pin["weights_file_sha256_at_compile"]
    if both:
        ledger_pin["weights_sha_matches_ensemble"] = \
            ledger_pin["weights_file_sha256"] == \
            ledger_pin["weights_file_sha256_at_compile"]
        if not ledger_pin["weights_sha_matches_ensemble"]:
            flags.append("weights-sha-differs-from-main")

    # ---- provenance.
    if archive_sha is None:
        archive_sha = _git_rev_parse(sweep_dir, "HEAD")
    tree_sha = None
    if archive_sha is not None:
        tree_sha = _git_rev_parse(sweep_dir, "HEAD^{tree}")
        if tree_sha is None:
            flags.append("tree-sha-unavailable: archive SHA given "
                         "by flag, no git checkout to derive the "
                         "tree SHA")
    if archive_sha is None:
        flags.append("archive-sha-unavailable: sweep dir is not a "
                     "git checkout and no --archive-sha was given")
    ledger_pin["tree_sha"] = tree_sha
    if compiler_sha is None:
        compiler_sha = _git_rev_parse(repo_root, "HEAD")
    merged_by = "actions"
    worker_code_sha = worker_release_sha = claim_id = None
    source_runs = None
    if manifest is not None:
        if manifest.get("merged_by") == "worker" or \
                manifest.get("source_runs"):
            merged_by = "worker"
            worker_code_sha = manifest.get("worker_code_sha")
            worker_release_sha = manifest.get("worker_release_sha")
            claim_id = manifest.get("claim_id")
            source_runs = manifest.get("source_runs")

    # ---- degraded block (merge's, or compiler-derived).
    degraded = (digest or {}).get("degraded")
    degraded_derived = False
    if degraded is not None:
        reason = degraded.get("reason") if isinstance(
            degraded, dict) else None
        if reason not in DEGRADED_REASONS:
            raise CompileError(
                f"unknown degraded reason {reason!r} in {sweep_dir}")
    elif merged_by == "worker" and ensemble is not None:
        # §2d: a keyless worker sweep without a degraded block is
        # derived, and labelled as the compiler's, not the merge's.
        fam_tools = {}
        for tool_id, _tk in planned:
            fam = registry_by_id.get(tool_id, {}).get("family")
            if fam:
                fam_tools.setdefault(fam, []).append(tool_id)
        absent_families = []
        for fam in VOTING_FAMILIES:
            tools_in_fam = fam_tools.get(fam)
            if not tools_in_fam:
                continue
            ok = any(next((r.get("status") == "ok" for r in results
                           if r.get("tool") == t), False)
                     for t in tools_in_fam)
            if not ok:
                absent_families.append(fam)
        absent_tools = [e["tool"] for e in tools_failed]
        if absent_families:
            degraded = {"reason": "keyless"
                        if all(f in ("agent", "fundamentals")
                               for f in absent_families)
                        and not absent_tools else "partial-fleet",
                        "absent_families": absent_families,
                        "absent_tools": absent_tools,
                        "degraded_derived": True}
            degraded_derived = True
    if manifest is None:
        flags.append("manifest-missing")
    if degraded is not None:
        # The degraded block is carried verbatim, and surfaced in
        # the top-level flags so a reader never has to dig for it.
        fams = ", ".join(degraded.get("absent_families") or []) or "—"
        derived_note = " (derived by the compiler)" \
            if degraded_derived else ""
        flags.append(f"degraded: {degraded.get('reason')} (absent "
                     f"families: {fams}){derived_note}")

    # ---- news (identity keys + titles only; bodies never embedded).
    news_items, news_present = read_news_items(sweep_dir, "news.json")
    disc_items, disc_present = read_news_items(
        sweep_dir, "disclosures.json")
    news_meta = {"news_count": len(news_items),
                 "disclosure_count": len(disc_items),
                 "latest_news_date": None,
                 "latest_news_date_raw": None,
                 "latest_disclosure_date": None,
                 "latest_disclosure_date_raw": None}
    for result in results:
        if result.get("tool") != "news-disclosure":
            continue
        metrics = (result.get("summary") or {}).get("metrics") or {}
        for raw_key, key in (
                ("latest_news_date", "latest_news_date"),
                ("latest_disclosure_date", "latest_disclosure_date")):
            raw = metrics.get(raw_key)
            if raw:
                news_meta[key + "_raw"] = raw
                news_meta[key] = _rfc2822_to_iso(raw)
        for count_key in ("news_count", "disclosure_count"):
            if metrics.get(count_key) is not None:
                news_meta[count_key] = metrics.get(count_key)
        break
    if not news_present:
        flags.append("news-file-missing: collected/news-disclosure/"
                     "news.json")
    if not disc_present:
        flags.append("disclosures-file-missing: collected/"
                     "news-disclosure/disclosures.json")

    # ---- recommendation + reaction profile (main snapshots).
    recommendation = None
    rec_path = os.path.join(profiles_dir,
                            f"{ticker}.recommendation.json")
    rec = None
    if os.path.isfile(rec_path):
        try:
            rec = _load_json_lenient(rec_path)
        except Exception:
            rec = None
    if rec is None:
        flags.append("recommendation-unavailable: no profiles/"
                     f"{ticker}.recommendation.json")
    elif rec.get("as_of") != digest.get("date") or \
            _fnum(rec.get("base_price")) != _fnum(
                (ensemble or {}).get("base_price")):
        flags.append(
            f"recommendation-stale: profile as_of {rec.get('as_of')} "
            f"base {rec.get('base_price')} != sweep "
            f"{digest.get('date')} base "
            f"{(ensemble or {}).get('base_price')}")
    else:
        recommendation = {
            key: rec.get(key) for key in (
                "ticker", "as_of", "archive_commit", "base_price",
                "reference_price", "action", "buy_below",
                "sell_above", "expected_week_pct", "nudge_pct",
                "expected_week_adj_pct", "confidence", "risk",
                "weights_source", "notes")}
        # R-10: audit the copied notes for imperative wording.
        notes = recommendation.get("notes") or []
        if any(re.search(r"\b(buy|sell|hold)\b", str(n),
                         re.IGNORECASE) for n in notes):
            flags.append("recommendation-notes-carry-advice-wording")
    levels, levels_flag = build_levels(ensemble)
    if levels_flag:
        flags.append(levels_flag)

    profile = None
    profile_path = os.path.join(profiles_dir, f"{ticker}.json")
    reaction_profile = {"ticker": ticker, "present": False,
                        "built_at": None, "archive_commit": None,
                        "walk_forward": None, "fit": None}
    if os.path.isfile(profile_path):
        try:
            profile = _load_json_lenient(profile_path)
        except Exception:
            profile = None
    if isinstance(profile, dict):
        fit_src = profile.get("reaction_fit") or {}
        by_type = fit_src.get("by_type") or {}
        dividend = by_type.get("dividend") or {}
        reaction_profile.update({
            "present": True,
            "built_at": profile.get("built_at"),
            "archive_commit": profile.get("archive_commit"),
            "walk_forward": profile.get("walk_forward"),
            "fit": {"global_median_r5_adj":
                    fit_src.get("global_median_r5_adj"),
                    "dividend_shrunk":
                    dividend.get("shrunk_r5_adj"),
                    "shrinkage_k": fit_src.get("shrinkage_k")},
        })
    else:
        flags.append(f"reaction-profile-missing: no profiles/"
                     f"{ticker}.json")

    llm, llm_flags = build_llm(tools, family_scores)
    flags.extend(llm_flags)

    # ---- sharia section (issue #170): projection of the engine's
    # ---- stored verdict tables from the main checkout.
    sharia_tables = {std: load_sharia_table(repo_root, std)
                     for std in sharia_resolved}
    sharia, sharia_flags = build_sharia_section(
        ticker, sharia_standards, sharia_resolved, sharia_tables,
        sharia_engine_mod)
    flags.extend(sharia_flags)

    model = {
        "model_version": MODEL_VERSION,
        "schema": SCHEMA,
        "ticker": ticker,
        "job": job,
        "job_shape": job_shape,
        "market": market_from_job(job),
        "date": digest.get("date"),
        "started": digest.get("started"),
        "finished": finished,
        "sweep_dir": _sweep_rel_path(sweep_dir),
        "archive_commit": archive_sha,
        "provenance": {
            "merged_by": merged_by,
            "worker_code_sha": worker_code_sha,
            "worker_release_sha": worker_release_sha,
            "claim_id": claim_id,
            "source_runs": source_runs,
            "run_id": _run_id_from(sweep_dir, manifest),
            "compiler": COMPILER_PATH,
            "compiler_sha": compiler_sha,
        },
        "partial": partial,
        "ensemble_absent": ensemble_absent,
        "ensemble_empty": ensemble_empty,
        "ensemble_shape": ensemble_shape,
        "degraded": degraded,
        "degraded_derived": degraded_derived,
        "ticker_mismatch": ticker_mismatch,
        "coercion_failed": coercion_failed,
        "secret_fields_dropped": secret_dropped,
        "ensemble": ensemble,
        "price": price,
        "price_series_last": series,
        "price_series_excluded": series_excluded,
        "family_scores": family_scores,
        "horizons": horizons,
        "risk": risk,
        "risk_events_truncated": True if ensemble is not None
        else None,
        "corporate_actions": corporate_actions,
        "kronos_ex_rescale": kronos_ex_rescale,
        "weights": weights,
        "ledger_pin": ledger_pin,
        "news": {
            "news_count": news_meta["news_count"],
            "disclosure_count": news_meta["disclosure_count"],
            "latest_news_date": news_meta["latest_news_date"],
            "latest_news_date_raw":
                news_meta["latest_news_date_raw"],
            "latest_disclosure_date":
                news_meta["latest_disclosure_date"],
            "latest_disclosure_date_raw":
                news_meta["latest_disclosure_date_raw"],
            "identity_scheme": "resolved_url|title-date-hash",
            "news_items": news_items,
            "disclosure_items": disc_items,
        },
        "tools": tools,
        "tools_absent": tools_absent,
        "tools_failed": tools_failed,
        "recommendation": recommendation,
        "levels": levels,
        "reaction_profile": reaction_profile,
        "llm": llm,
        "benchmark": build_benchmark(sweep_dir),
        "sharia": sharia,
        "flags": flags,
        "metrics_schema": "untyped-flat",
    }
    return model


def dump_model(model, out_path):
    """Write the model deterministically (sorted keys, fixed float
    formatting, no wall-clock timestamps) and verify it parses
    under strict JSON before the write lands. The write is atomic
    (#161): the text goes to a temp file in the same directory and
    is moved into place, so a crash or write failure can never
    leave a truncated report-model.json behind."""
    text = json.dumps(model, indent=2, ensure_ascii=False,
                      sort_keys=True, allow_nan=False) + "\n"
    json.loads(text, parse_constant=lambda c: (_ for _ in ()).throw(
        ValueError(f"non-finite constant {c!r} in model")))
    tmp_path = out_path + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(tmp_path, out_path)
    except Exception:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise
    return text


def _quarantine_previous_model(out_path):
    """#161: invalidate the previous model before a recompile is
    attempted. A refused/failed recompile must not leave an older
    report-model.json in place for a file-presence consumer to use
    as current, so the old file is moved aside (kept for
    inspection under ``.quarantined``) before compile_sweep runs.
    Returns True when there was nothing to quarantine or the move
    succeeded; False when the move failed -- in that case the
    caller must not proceed, or the stale model would survive a
    refusal exactly as before."""
    if not os.path.isfile(out_path):
        return True
    try:
        os.replace(out_path, out_path + ".quarantined")
    except OSError as exc:
        print(f"compile failed quarantining previous model "
              f"{out_path}: {exc}", file=sys.stderr)
        return False
    return True


def _clear_error_marker(error_path):
    """#161: remove a stale compile_error.txt after a successful
    compile, so a good model never sits next to an old error
    marker. Best-effort with a warning: the model is already
    written, so a removal failure must not fail the compile."""
    if not os.path.isfile(error_path):
        return
    try:
        os.remove(error_path)
    except OSError as exc:
        print(f"compile warning: could not clear stale error "
              f"marker {error_path}: {exc}", file=sys.stderr)


# ---------------------------------------------------------------- consumer check

MODEL_REQUIRED_FIELDS = (
    "model_version", "schema", "ticker", "job", "job_shape", "date",
    "finished", "sweep_dir", "archive_commit", "provenance",
    "partial", "ensemble_absent", "ensemble_shape", "degraded",
    "ticker_mismatch", "coercion_failed", "ensemble", "price",
    "price_series_last", "family_scores", "horizons", "risk",
    "corporate_actions", "kronos_ex_rescale", "weights", "ledger_pin",
    "news", "tools", "tools_absent", "tools_failed", "recommendation",
    "levels", "reaction_profile", "llm", "flags", "metrics_schema")


def validate_model_schema(model):
    """Consumer-side schema check (F-8 / D-7): refuse a model whose
    ``schema`` is not understood, listing the missing required
    fields -- never silently degrade, never guess a default.
    Returns a list of problems (empty = valid)."""
    problems = []
    if not isinstance(model, dict):
        return ["model is not an object"]
    schema = model.get("schema")
    if schema != SCHEMA or model.get("model_version") != MODEL_VERSION:
        problems.append(
            f"model_schema_unsupported: expected {SCHEMA}, found "
            f"{schema!r} (model_version "
            f"{model.get('model_version')!r})")
    for field in MODEL_REQUIRED_FIELDS:
        if field not in model:
            problems.append(f"missing required field: {field}")
    return problems


# ---------------------------------------------------------------- CLI

def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Report Model compiler (issue #68).")
    ap.add_argument("sweep_dir", nargs="?",
                    help="archived sweep dir to compile")
    ap.add_argument("--repo-root", default=None,
                    help="main-branch checkout (ledger + profiles); "
                         "default: parent of scripts/")
    ap.add_argument("--archive-sha", default=None,
                    help="archive HEAD SHA (default: git rev-parse "
                         "in the sweep dir)")
    ap.add_argument("--compiler-sha", default=None,
                    help="main HEAD SHA (default: git rev-parse in "
                         "the repo root)")
    ap.add_argument("--profiles-dir", default=None,
                    help="profiles dir (default: <repo-root>/profiles)")
    ap.add_argument("--out", default=None,
                    help="model output path (default: "
                         "<sweep_dir>/report-model.json)")
    ap.add_argument("--sharia-standards", default=None,
                    action="append",
                    help="Sharia standards for the model's sharia "
                         "section (issue #170): comma-separated "
                         "and/or repeatable; default: all "
                         "implemented standards. An unknown "
                         "standard refuses the compile.")
    ap.add_argument("--check-model", default=None,
                    help="consumer schema check for a model file "
                         "(exits 2 when unsupported)")
    args = ap.parse_args(argv)
    if args.check_model:
        try:
            model = _load_json_strict(args.check_model)
        except Exception as exc:
            print(f"model_schema_unsupported: cannot read "
                  f"{args.check_model}: {exc}", file=sys.stderr)
            return 2
        problems = validate_model_schema(model)
        if problems:
            for problem in problems:
                print(f"model_schema_unsupported: {problem}",
                      file=sys.stderr)
            return 2
        print(f"model schema OK: {SCHEMA}")
        return 0
    if not args.sweep_dir:
        ap.error("sweep_dir is required (or --check-model)")
    out_path = args.out or os.path.join(
        os.path.normpath(args.sweep_dir), "report-model.json")
    error_path = os.path.join(
        os.path.dirname(out_path), "compile_error.txt")
    # #161: invalidate the previous model BEFORE compiling, so a
    # refusal, crash, or write failure can never leave it in place
    # as if it were the current compile's result. Fail closed when
    # the quarantine itself fails.
    if not _quarantine_previous_model(out_path):
        return 1
    sharia_standards = None
    if args.sharia_standards:
        sharia_standards = [
            part.strip() for chunk in args.sharia_standards
            for part in chunk.split(",") if part.strip()]
    try:
        model = compile_sweep(
            args.sweep_dir, repo_root=args.repo_root,
            archive_sha=args.archive_sha,
            compiler_sha=args.compiler_sha,
            profiles_dir=args.profiles_dir,
            sharia_standards=sharia_standards)
    except CompileError as exc:
        message = f"compile refused: {exc}\n"
        print(message, end="", file=sys.stderr)
        try:
            with open(error_path, "w", encoding="utf-8") as handle:
                handle.write(message)
        except OSError:
            pass
        return 2
    try:
        dump_model(model, out_path)
    except Exception as exc:
        print(f"compile failed writing {out_path}: {exc}",
              file=sys.stderr)
        return 1
    # #161: a successful compile clears any stale error marker, so
    # a good model never sits next to an old refusal.
    _clear_error_marker(error_path)
    degraded = "degraded" if model["flags"] else "clean"
    print(f"compile_model: {model['sweep_dir']} -> {out_path} "
          f"({degraded}, {len(model['flags'])} flags, "
          f"{len(model['tools'])} tools)")
    for flag in model["flags"]:
        print(f"  flag: {flag}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
