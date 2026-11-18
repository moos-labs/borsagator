#!/usr/bin/env python3
"""Delta module (#70): what changed since the last sweep of this ticker.

Pure, deterministic, stdlib-only. The diff core takes two *sweep
views* and returns one delta dict (``delta_version: 1``); it never
reads the network, the ledger, or a live branch.

Two input paths, one diff core:

* **Raw ensemble pairs (shipped now, #68 unlanded).** A thin adapter
  (``load_sweep_view``) builds a view from an archived sweep dir:
  ``ensemble.json`` + ``digest.json`` + the price CSVs' last
  close-bearing rows + ``news.json`` / ``disclosures.json`` identity
  keys. This is the path the harness proves against the golden pairs.
* **Report Models (#68 landed).** A Report Model already carries
  every field the view needs (``price_series_last``, news identity
  keys, ``ledger_pin``); ``model_to_view`` feeds the same
  ``compute_delta`` core, and the harness re-proves the golden pairs
  through the model path. The model-path delta matches the raw-path
  delta everywhere EXCEPT the ledger-pin-carrying fields: the raw
  ensembles carry no ledger counts (``counts: None``), while the
  model carries the pinned counts -- that difference is the point
  of the model path, not a drift, and the harness asserts the pin
  separately against its exact values (see ``harness_issue70.py``
  ``strip_calibration`` / ``calibration_failures``).

Legal gate (#77 framing v2, binding): every rendered delta line is
descriptive-conditional only. No buy / sell / hold wording, no
imperative, no recommendation derived from a move, no accuracy
figure (D4 / #79 gate: none until the ledger holds n >= 30 matured
forecasts). The delta reports what moved; the recommendation decides
what it means.

Thresholds are module constants (scoping section 4g), never magic
numbers in the diff code. Every section prints the raw delta
alongside the flag, so a reader can disagree with a threshold
without re-running anything. ``null`` is always "no data", never 0.
"""

import argparse
import csv
import glob
import hashlib
import json
import math
import os
import re
import sys
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

DELTA_VERSION = 1

# Thresholds (issue #70 scoping section 4g, adopted as proposed).
TH_HORIZON_MOVE_PP = 0.5      # |delta expected_move_pct| per horizon
TH_FAMILY_SCORE = 0.10         # |delta| family score
TH_APPLIED_FACTOR = 0.01       # |delta| applied weight factor
TH_BASE_PRICE_PCT = 0.5        # |delta| base price, after ex-date decomposition

# A direction flip, a confidence change, a risk-level change, a family
# vote flip, a new/removed corporate action, a weights_source change,
# a ledger-count change, and any tool add/remove/status change always
# flag (no threshold).

NEWS_IDENTITY_SCHEME = "resolved_url|title-date-hash"
ISSUE_130 = "#130"
ISSUE_129 = "#129"
ISSUE_92 = "#92"
ISSUE_67 = "#67"

# Backtest and stats tools run reference workloads; their CSVs are not
# this ticker's price series (ensemble.py EXCLUDED_PRICE_CATEGORIES).
EXCLUDED_PRICE_CATEGORIES = ("backtest", "stats")

# Tools whose summary envelope ticker is never this sweep's ticker by
# construction. There are none: the envelope ticker is the job ticker
# on every tool that carries one, including the reference workloads
# (their foreign ticker lives in metrics.ticker, which the tripwire
# deliberately never reads). Kept as an explicit empty set so a future
# legitimate exception is a one-line, reviewed change, not a silent
# carve-out in the tripwire.
TRIPWIRE_EXEMPT_TOOLS = frozenset()


class DeltaError(Exception):
    """A sweep dir cannot be read as a delta input at all."""


# ---------------------------------------------------------------- helpers

def _fnum(value):
    """Parse a number; None for anything missing, non-numeric, or
    non-finite (NaN / Infinity are rejected, never coerced)."""
    if value is None or isinstance(value, bool):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def _round(value, places=2):
    if value is None:
        return None
    return round(float(value), places)


def _parse_ts(value):
    """ISO timestamp -> aware datetime, or None (string compare is
    not relied on: finished times carry varying fractional seconds)."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _iso_date(value):
    """First 10 chars of an ISO date/datetime, or None."""
    if not value:
        return None
    text = str(value)[:10]
    return text if re.match(r"^\d{4}-\d{2}-\d{2}$", text) else None


def _load_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def normalize_job_shape(job):
    """Normalized job shape: kind (+ subkind for category/run) + ticker
    + trailing filters. ``sweep-lite POUL.CA market=EGX`` (14 tools)
    and ``sweep-lite POUL.CA`` (29 tools) are different shapes and
    never pair; ``category news`` and ``run <tool>`` keep their
    subkind, so two different category runs never pair either."""
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


def identity_key(item):
    """Derived news/disclosure identity (scoping section 4e): the
    items carry no stable ID. ``resolved_url`` when present, else a
    hash of (title, date). Returns (key, key_type)."""
    url = (item or {}).get("resolved_url")
    if url:
        return str(url), "resolved_url"
    title = str((item or {}).get("title") or "")
    date = str((item or {}).get("date") or "")
    digest = hashlib.sha256(f"{title}|{date}".encode("utf-8")).hexdigest()
    return digest[:16], "title-date-hash"


def _read_price_series(sweep_dir, ticker):
    """Last close-bearing row per price source, mirroring
    ``ensemble.py`` price_series: registry categories backtest/stats
    excluded; filename must contain ohlc / indicators / the ticker
    code (so Kronos forecast.csv is excluded: it is a forecast, not
    a price series); rows < 5 skipped; the last row with a parseable
    finite close wins, never the literal last CSV row (the yahooquery
    dividend-row trap: its last row carries dividends, no OHLC).
    Volume comes from that same row, or None when the row has no
    usable volume (never faked from another source)."""
    code = re.sub(r"[^a-z0-9]", "", ticker.split(".")[0].lower())
    collected = os.path.join(sweep_dir, "collected")
    registry = {}
    for candidate in (os.path.join(sweep_dir, "registry.json"),
                      os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "..", "registry", "tools.json")):
        try:
            registry = _load_json(candidate)
            break
        except Exception:
            continue
    categories = {t.get("id"): t.get("category")
                  for t in (registry or {}).get("tools", [])}
    series = []
    for path in sorted(glob.glob(os.path.join(collected, "*", "*.csv"))):
        tool = os.path.basename(os.path.dirname(path))
        if categories.get(tool) in EXCLUDED_PRICE_CATEGORIES:
            continue
        name = os.path.basename(path).lower()
        if not any(s in name for s in ("ohlc", "indicators", code)):
            continue
        try:
            with open(path, newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
        except Exception:
            continue
        if len(rows) < 5 or not rows[0]:
            continue
        header = [c for c in rows[0] if c]
        close_col = next((c for c in header
                          if c.strip().lower() in
                          ("close", "adj close", "adjclose")), None)
        if not close_col:
            continue
        date_col = next((c for c in header
                         if "date" in c.strip().lower()
                         or c.strip().lower() in ("datetime", "index")),
                        None)
        vol_col = next((c for c in header
                        if c.strip().lower() in ("volume", "vol")), None)
        last = None
        for row in rows:
            close = _fnum(row.get(close_col))
            if close is None:
                continue
            date = None
            if date_col:
                date = _iso_date(row.get(date_col))
            volume = _fnum(row.get(vol_col)) if vol_col else None
            last = {"last_date": date, "last_close": close,
                    "last_volume": volume}
        if last is None:
            continue
        last["source"] = f"{tool}/{os.path.basename(path)}"
        last["rows"] = len(rows)
        series.append(last)
    # Canonical order: egx-data first for EGX, then by source name,
    # so the output is deterministic and the reader sees the EGX-native
    # series first (ensemble.py freshest_close tie-break).
    series.sort(key=lambda s: (not s["source"].startswith("egx-data/"),
                               s["source"]))
    return series


def _read_news_items(sweep_dir, filename):
    """Identity keys + titles for one feed file. Missing file -> empty
    list (a sweep without the feed has no items, not zero items)."""
    path = os.path.join(sweep_dir, "collected", "news-disclosure",
                        filename)
    try:
        doc = _load_json(path)
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


# ---------------------------------------------------------------- loading

def load_sweep_view(sweep_dir, archive_sha=None):
    """Build a sweep view from an archived sweep dir. Raises
    DeltaError only when the dir is not a sweep at all (no digest and
    no manifest); every other absence is recorded in the view as
    "no data", never guessed."""
    sweep_dir = os.path.normpath(sweep_dir)
    digest_path = os.path.join(sweep_dir, "digest.json")
    ensemble_path = os.path.join(sweep_dir, "ensemble.json")
    manifest_path = os.path.join(sweep_dir, "manifest.json")
    digest = None
    manifest = None
    if os.path.exists(digest_path):
        digest = _load_json(digest_path)
    if os.path.exists(manifest_path):
        manifest = _load_json(manifest_path)
    if digest is None and manifest is None:
        raise DeltaError(f"not a sweep dir: no digest.json or "
                         f"manifest.json in {sweep_dir}")
    ensemble = None
    if os.path.exists(ensemble_path):
        ensemble = _load_json(ensemble_path)

    # Worker runs archive manifest-only: no digest, no ensemble.
    is_worker_run = digest is None and manifest is not None
    if is_worker_run:
        job = manifest.get("job")
        job_str = job.get("job") if isinstance(job, dict) else job
        ticker = None
        if job_str:
            ticker = next((p for p in str(job_str).split() if "." in p),
                          None)
        return {"kind": "worker-run", "sweep_dir": sweep_dir,
                "archive_sha": archive_sha, "ticker": ticker,
                "job": job_str, "job_shape": normalize_job_shape(job_str),
                "market": market_from_job(job_str),
                "date": _iso_date(manifest.get("started")),
                "started": manifest.get("started"),
                "finished": manifest.get("finished"),
                "ensemble": None, "ensemble_absent": True,
                "digest": None, "manifest": manifest,
                "price_series_last": [], "news_items": [],
                "disclosure_items": [], "ledger_pin": None,
                "tripwire": [], "notes": [
                    "worker sweep: manifest only, no ensemble "
                    f"(see {ISSUE_67})"]}

    job = digest.get("job")
    ticker = digest.get("ticker")
    ensemble = ensemble or {}
    applied = ensemble.get("applied_weights") or {}
    weights_sha = applied.get("file_sha256")
    news_items, news_present = _read_news_items(sweep_dir, "news.json")
    disc_items, disc_present = _read_news_items(sweep_dir,
                                                "disclosures.json")
    # Latest dates + counts are context only, from the news-disclosure
    # summary metrics (RFC-2822 strings, kept raw; parsed to ISO
    # where parseable). They are never the diff: the feed is a rolling
    # window and latest dates go backwards.
    news_meta = {"latest_news_date": None, "latest_news_date_iso": None,
                 "latest_disclosure_date": None,
                 "latest_disclosure_date_iso": None,
                 "news_count": len(news_items),
                 "disclosure_count": len(disc_items)}
    for result in digest.get("results", []) or []:
        if result.get("tool") != "news-disclosure":
            continue
        metrics = (result.get("summary") or {}).get("metrics") or {}
        for raw_key, key in (("latest_news_date", "latest_news_date"),
                             ("latest_disclosure_date",
                              "latest_disclosure_date")):
            raw = metrics.get(raw_key)
            if raw:
                news_meta[key] = raw
                try:
                    news_meta[key + "_iso"] = parsedate_to_datetime(
                        raw).strftime("%Y-%m-%dT%H:%M:%SZ")
                except Exception:
                    pass
        for count_key in ("news_count", "disclosure_count"):
            if metrics.get(count_key) is not None:
                news_meta[count_key] = metrics.get(count_key)
        break
    view = {"kind": "sweep", "sweep_dir": sweep_dir,
            "archive_sha": archive_sha, "ticker": ticker, "job": job,
            "job_shape": normalize_job_shape(job),
            "market": market_from_job(job),
            "date": digest.get("date") or _iso_date(digest.get("finished")),
            "started": digest.get("started"),
            "finished": digest.get("finished"),
            "ensemble": ensemble if os.path.exists(ensemble_path) else None,
            "ensemble_absent": not os.path.exists(ensemble_path),
            "digest": digest, "manifest": manifest,
            "price_series_last": _read_price_series(sweep_dir,
                                                    ticker or ""),
            "news_items": news_items,
            "disclosure_items": disc_items,
            "news_meta": news_meta,
            "news_present": news_present,
            "disclosures_present": disc_present,
            # Raw ensembles carry no ledger counts (matured / pending /
            # invalid): those arrive with the Report Model ledger_pin
            # (#68). The calibration section reports the pin it has
            # (weights) and nulls the counts, never re-reads the live
            # ledger. Weights-file SHA is the sweep-time pin.
            "ledger_pin": {"counts": None,
                           "counts_source": "unavailable: raw ensemble "
                           "carries no ledger counts (see #68 ledger_pin)",
                           "weights_file_sha256": weights_sha,
                           "eligible": (applied.get("eligible") or {})},
            "tripwire": tripwire(digest, ensemble),
            "notes": []}
    return view


def tripwire(digest, ensemble):
    """Ticker-consistency tripwire, envelope level only.

    Fires when the ensemble ticker differs from the digest ticker, or
    when any digest result's summary envelope ``ticker`` differs from
    the digest ticker. It deliberately never reads
    ``summary.metrics.ticker``: backtest/reference tools legitimately
    carry a foreign ticker there (backtrader / pybroker / edgartools
    run AAPL inside a POUL sweep), and a metrics-level check would
    false-fire on every full sweep. Rows without a summary (no-summary
    / error rows) carry no envelope ticker and are skipped, not
    treated as mismatches.
    """
    problems = []
    digest_ticker = (digest or {}).get("ticker")
    ens_ticker = (ensemble or {}).get("ticker")
    if ens_ticker and digest_ticker and ens_ticker != digest_ticker:
        problems.append({"field": "ensemble.ticker", "expected": digest_ticker,
                         "found": ens_ticker})
    for result in (digest or {}).get("results", []) or []:
        summary = result.get("summary") or {}
        found = summary.get("ticker")
        if found and digest_ticker and found != digest_ticker:
            problems.append({"field": f"summary.ticker:{result.get('tool')}",
                             "expected": digest_ticker, "found": found})
    return problems


# ------------------------------------------------------- model-path input

MODEL_SCHEMA = "borsagator-report-model/1"

# The raw view's price-series entry carries exactly these five keys
# (delta.py _read_price_series); the model carries more per series
# (last_open / last_high / last_low / stale / note). The converter
# projects down to the raw five so the price section diffs
# identically -- the extra model fields are price detail for the
# renderer, not delta inputs.
_PRICE_SERIES_KEYS = ("last_date", "last_close", "last_volume",
                      "source", "rows")


def model_to_view(model, sweep_dir=None, archive_sha=None):
    """Build a sweep view from a parsed Report Model dict (schema
    ``borsagator-report-model/1``) -- the model-path input to the
    same ``compute_delta`` core the raw-ensemble path feeds.

    The converter reads ONLY the model (plus the sweep dir it is
    handed, for the path strings the delta pins): it never re-reads
    the raw sweep files, so a delta built this way proves the model
    carries everything the delta needs. Raises DeltaError when the
    dict is not a /1 model.

    Field mapping (verified against the six golden models, archive
    647fdfbc -- every one of these equalities is asserted by the
    harness, not assumed):

    * ``ensemble`` -- embedded verbatim in the model; dict-equal to
      the sweep's ``ensemble.json`` on all six golden sweeps.
    * ``price_series_last`` -- projected to the raw view's five
      keys; values equal the CSV-derived raw series on all six.
    * ``news.news_items`` / ``news.disclosure_items`` -- identity
      keys + titles, dict-equal to the raw view's items.
    * ``news`` latest dates (raw RFC-2822 + ISO) and counts --
      equal to the raw view's ``news_meta`` on all six.
    * ``tools`` -- rebuilt into digest results. The compiler
      redacts the summary envelope (``tool`` / ``ticker`` /
      ``status`` are dropped from the stored summary); the diff
      core reads ``summary.status`` and ``summary.ticker``, which
      the model carries at tool level (``status``) and top level
      (``ticker``), so the envelope is rebuilt from those. A tool
      with no summary in the model (``summary: null`` -- a
      no-summary row) gets NO ``summary`` key in the rebuilt
      result, so ``has_summary`` matches the raw view exactly
      (085806 finbert-tone is the live case).
    * ``ledger_pin`` -- carried as the pin: counts, weights-file
      SHA, and ``eligible`` from the embedded ensemble's
      ``applied_weights``. This is the one place the model view
      deliberately differs from the raw view (raw counts are
      None); the calibration section therefore reports the pinned
      counts on the model path instead of "not carried".
    * ``ticker_mismatch`` -- the compiler refuses to emit a model
      on any ticker mismatch, so this is always [] on a valid
      model; it is the view's tripwire, taken as the compiler's
      recorded verdict rather than recomputed from the redacted
      summaries (which carry no envelope ticker to check).
    * ``levels`` -- carried in the view for the renderer (#69 /
      D2); the v1 diff core does not read them.
    * ``sharia`` -- carried in the view for the renderer (#69 /
      #170): the Report Model's Sharia evaluation section,
      projected by the compiler from the engine's stored verdict
      tables; the v1 diff core does not read it.
    """
    if not isinstance(model, dict) or model.get("schema") != MODEL_SCHEMA:
        raise DeltaError(
            f"not a {MODEL_SCHEMA} report model: schema is "
            f"{(model or {}).get('schema')!r}")
    ensemble = model.get("ensemble") or {}
    news = model.get("news") or {}
    pin = model.get("ledger_pin") or {}
    applied = ensemble.get("applied_weights") or {}
    ticker = model.get("ticker")

    series = []
    for entry in model.get("price_series_last") or []:
        series.append({key: (entry or {}).get(key)
                       for key in _PRICE_SERIES_KEYS})
    news_items = news.get("news_items") or []
    disc_items = news.get("disclosure_items") or []
    news_meta = {
        "latest_news_date": news.get("latest_news_date_raw"),
        "latest_news_date_iso": news.get("latest_news_date"),
        "latest_disclosure_date":
            news.get("latest_disclosure_date_raw"),
        "latest_disclosure_date_iso":
            news.get("latest_disclosure_date"),
        "news_count": news.get("news_count") if news.get("news_count")
        is not None else len(news_items),
        "disclosure_count": news.get("disclosure_count")
        if news.get("disclosure_count") is not None
        else len(disc_items)}

    # Rebuilt digest: only the fields the diff core reads (results
    # with tool / conclusion / summary envelope). The model records
    # no manifest, and no diff section reads one.
    results = []
    for tool in model.get("tools") or []:
        summary = tool.get("summary")
        entry = {"tool": tool.get("tool"),
                 "conclusion": tool.get("conclusion")}
        if summary is not None:
            rebuilt = dict(summary)
            rebuilt["tool"] = tool.get("tool")
            rebuilt["ticker"] = ticker
            rebuilt["status"] = tool.get("status")
            entry["summary"] = rebuilt
        results.append(entry)
    digest = {"job": model.get("job"), "ticker": ticker,
              "date": model.get("date"), "started": model.get("started"),
              "finished": model.get("finished"), "results": results}

    tripwire_problems = []
    for problem in model.get("ticker_mismatch") or []:
        field = problem.get("field")
        if not field and problem.get("tool"):
            field = f"summary.ticker:{problem.get('tool')}"
        tripwire_problems.append(
            {"field": field or "ticker",
             "expected": problem.get("expected"),
             "found": problem.get("found")})

    if sweep_dir is not None:
        sweep_dir = os.path.normpath(sweep_dir)
    elif model.get("sweep_dir"):
        sweep_dir = model.get("sweep_dir")
    return {"kind": "sweep", "sweep_dir": sweep_dir,
            "archive_sha": archive_sha, "ticker": ticker,
            "job": model.get("job"),
            "job_shape": model.get("job_shape")
            or normalize_job_shape(model.get("job")),
            "market": model.get("market", market_from_job(
                model.get("job"))),
            "date": model.get("date"),
            "started": model.get("started"),
            "finished": model.get("finished"),
            "ensemble": ensemble,
            "ensemble_absent": bool(model.get("ensemble_absent"))
            or model.get("ensemble") is None,
            "digest": digest, "manifest": None,
            "price_series_last": series,
            "news_items": news_items,
            "disclosure_items": disc_items,
            "news_meta": news_meta,
            # The model records no feed-file presence: a sweep with
            # an empty feed file is indistinguishable from a sweep
            # with no feed. Best-effort flags; nothing in the diff
            # core reads them.
            "news_present": bool(news_items
                                 or news.get("news_count")),
            "disclosures_present": bool(disc_items
                                        or news.get("disclosure_count")),
            "ledger_pin": {"counts": pin.get("counts"),
                           "counts_source": "report-model ledger_pin "
                           f"({MODEL_SCHEMA})",
                           "weights_file_sha256":
                               pin.get("weights_file_sha256")
                               or applied.get("file_sha256"),
                           "eligible": applied.get("eligible") or {}},
            "levels": model.get("levels"),
            "sharia": model.get("sharia"),
            "tripwire": tripwire_problems,
            "notes": ["view built from report-model.json "
                      f"({MODEL_SCHEMA}); raw sweep files not read"]}


def load_model_view(sweep_dir, archive_sha=None):
    """Load ``<sweep_dir>/report-model.json`` and return its view.
    Raises DeltaError when the model file is absent -- never a
    silent fall-back to the raw ensemble path: a model-path run
    with no models must fail visibly (that is the harness's
    negative control)."""
    sweep_dir = os.path.normpath(sweep_dir)
    path = os.path.join(sweep_dir, "report-model.json")
    if not os.path.exists(path):
        raise DeltaError(
            f"no report-model.json in {sweep_dir}: the model path "
            "cannot run without the Report Model (see #68)")
    return model_to_view(_load_json(path), sweep_dir, archive_sha)


def delta_pair_models(prev_dir, cur_dir, archive_sha=None):
    """Diff two sweep dirs through their Report Models. Mirrors
    ``delta_pair``: an ensemble-absent model yields
    delta_unavailable, a compiler-recorded ticker mismatch yields
    pair_invalid; both are normal outputs (exit 0), not crashes."""
    cur = load_model_view(cur_dir, archive_sha)
    prev = load_model_view(prev_dir, archive_sha)
    if prev.get("ensemble_absent") or cur.get("ensemble_absent"):
        missing = prev_dir if prev.get("ensemble_absent") else cur_dir
        return unavailable_delta(
            cur, f"sweep dir {os.path.basename(missing)} carries no "
            "ensemble (model path)")
    problems = (prev.get("tripwire") or []) + (cur.get("tripwire") or [])
    if problems:
        return invalid_pair_delta(prev, cur, problems)
    return compute_delta(prev, cur)


# ------------------------------------------------------------- resolution

def _iter_sweep_dirs(archive_root):
    """Yield (dir, kind) for every sweep and worker-run dir under an
    archive checkout: sweeps/<date>/* and worker-runs/<date>/*."""
    for branch in ("sweeps", "worker-runs"):
        base = os.path.join(archive_root, branch)
        if not os.path.isdir(base):
            continue
        for date_dir in sorted(os.listdir(base)):
            day = os.path.join(base, date_dir)
            if not os.path.isdir(day):
                continue
            for entry in sorted(os.listdir(day)):
                path = os.path.join(day, entry)
                if os.path.isdir(path):
                    yield path, branch


# Earliest sortable timestamp: undated candidates sort here, i.e.
# as oldest (issue #154).
_MIN_TS = datetime.min.replace(tzinfo=timezone.utc)


def _sort_ts(value):
    """Sort-key timestamp: None -> oldest; naive -> UTC-aware so a
    mixed archive never raises on comparison."""
    if value is None:
        return _MIN_TS
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _run_identity(view, path):
    """Claim / source-run id shared by a merged sweep and its raw
    worker-run twin (issue #154). The merged sweep's manifest
    carries claim_id / run_id; the raw twin's run manifest carries
    job.id. Falls back to the dir-name suffix (__run<id> on merged
    sweeps, __<id> on raw worker runs), so legacy Actions sweeps
    without a manifest still identify by their __run<github-run-id>
    suffix. None only when nothing identifies the run."""
    manifest = (view or {}).get("manifest") or {}
    for key in ("claim_id", "run_id"):
        value = manifest.get(key)
        if value:
            return str(value)
    job = manifest.get("job")
    if isinstance(job, dict) and job.get("id"):
        return str(job["id"])
    tail = os.path.basename(os.path.normpath(path)).split("__")[-1]
    if tail.startswith("run"):
        tail = tail[3:]
    return tail or None


def _dedupe_twins(candidates, archive_root):
    """Drop manifest-only worker-run twins of merged sweeps (issue
    #154). A merged worker sweep and its raw twin are the SAME
    execution: the merged sweep's manifest names the twin in
    ``source_runs`` (merge.py: ``worker-runs/<date>/<run-dir>``),
    and both carry the same claim id and the same finished
    timestamp. The twin must not shadow the merged representation
    in latest-selection -- with equal finished times the
    enumeration order (sweeps/ before worker-runs/) otherwise
    leaves the twin last and resolve_pair reports
    delta_unavailable despite an available merged ensemble.

    An unmerged worker run (no merged sweep names it, different
    claim/finished) is kept: as the latest sweep it still means
    delta_unavailable. A same-claim re-run at a different finished
    time is a different execution and is likewise kept. Returns
    (kept, dropped) with dropped as [(merged_path, twin_path)]."""
    twin_of = {}  # archive-relative twin path -> merged sweep path
    for _fin, _branch, path, view in candidates:
        if view.get("kind") != "sweep":
            continue
        for src in ((view.get("manifest") or {}).get("source_runs")
                    or []):
            if isinstance(src, str) and src:
                twin_of[src] = path
    kept = []
    dropped = []
    for cand in candidates:
        finished, branch, path, view = cand
        if view.get("kind") != "worker-run":
            kept.append(cand)
            continue
        rel = os.path.relpath(path, archive_root).replace(os.sep, "/")
        merged = twin_of.get(rel)
        if merged is None:
            # No source_runs link: fall back to the claim identity,
            # but only at the SAME finished time -- a re-run at a
            # later time is a different execution, not a twin.
            ident = _run_identity(view, path)
            if ident is not None and finished is not None:
                for fin2, _b2, path2, view2 in candidates:
                    if (view2.get("kind") == "sweep"
                            and fin2 == finished
                            and _run_identity(view2, path2) == ident):
                        merged = path2
                        break
        if merged is not None:
            dropped.append((merged, path))
            continue
        kept.append(cand)
    return kept, dropped


def resolve_pair(archive_root, ticker, job_shape, current_dir,
                 archive_sha=None):
    """Resolve the previous sweep for a current sweep dir (scoping
    section 2): same ticker, same normalized job shape, most recent
    by digest.finished. Returns (previous_dir, status, note) where
    status is one of:

    * ``paired`` — a previous sweep with an ensemble exists;
    * ``first_sweep`` — no earlier sweep of this ticker + shape;
    * ``delta_unavailable`` — the most recent earlier sweep exists
      but has no ensemble (a worker sweep before #67, or a sweep
      dir without one and no earlier ensemble-bearing sweep);
    * ``skipped`` is recorded inside the note, never hidden: a
      sweeps/ dir without an ensemble is skipped in favour of the
      next earlier ensemble-bearing sweep.

    Worker sweeps are checked first: a manifest-only worker sweep is
    the latest same-shape sweep, so the report says "delta
    unavailable", never "first sweep".

    Issue #154: an undated sweep (finished None) sorts as OLDEST,
    never as most recent; and a merged worker sweep's manifest-only
    raw twin is deduplicated (same execution, same claim id) so the
    merged representation decides, never the twin.
    """
    current_dir = os.path.normpath(current_dir)
    try:
        current = load_sweep_view(current_dir, archive_sha)
    except DeltaError as exc:
        return None, "error", str(exc)
    current_finished = _parse_ts(current.get("finished"))
    candidates = []
    skipped = []
    for path, branch in _iter_sweep_dirs(archive_root):
        if os.path.normpath(path) == current_dir:
            continue
        try:
            view = load_sweep_view(path, archive_sha)
        except DeltaError:
            continue
        if view.get("ticker") != ticker:
            continue
        if view.get("job_shape") != job_shape:
            continue
        finished = _parse_ts(view.get("finished"))
        if current_finished and finished and finished >= current_finished:
            continue
        candidates.append((finished, branch, path, view))
    # Issue #154: deduplicate merged-sweep / raw-twin pairs (same
    # execution) before latest-selection, and sort undated sweeps
    # as oldest -- the old key (c[0] is None, c[0]) sorted
    # finished=None LAST, so an undated sweep became "most recent".
    candidates, dropped_twins = _dedupe_twins(candidates, archive_root)
    candidates.sort(key=lambda c: (c[0] is not None, _sort_ts(c[0])))
    if not candidates:
        return None, "first_sweep", (
            f"no previous sweep of {ticker} + job shape "
            f"'{job_shape}'")
    # The most recent candidate decides availability: a worker sweep
    # (or any ensemble-less sweep) as the latest same-shape sweep
    # means the delta is unavailable, not that the pair is the next
    # earlier sweep -- except that a sweeps/ dir without an ensemble
    # is skipped in favour of an earlier ensemble-bearing one, and
    # the skip is recorded.
    latest_finished, latest_branch, latest_path, latest_view = \
        candidates[-1]
    if latest_view.get("kind") == "worker-run":
        return None, "delta_unavailable", (
            f"most recent previous sweep {os.path.basename(latest_path)} "
            f"is a worker sweep with no ensemble (see {ISSUE_67})")
    with_ensemble = [c for c in candidates
                     if not c[3].get("ensemble_absent")]
    skipped = [c for c in candidates if c[3].get("ensemble_absent")]
    if not with_ensemble:
        return None, "delta_unavailable", (
            f"most recent previous sweep "
            f"{os.path.basename(latest_path)} has no ensemble and no "
            f"earlier sweep of this ticker + shape carries one")
    previous = with_ensemble[-1][2]
    note = (f"same ticker + same job shape ({job_shape}) + most "
            f"recent by digest.finished")
    if skipped:
        note += ("; skipped "
                 + ", ".join(os.path.basename(c[2]) for c in skipped)
                 + " (no ensemble.json)")
    for merged, twin in dropped_twins:
        if os.path.normpath(merged) == os.path.normpath(previous):
            note += (f"; merged {os.path.basename(merged)} preferred "
                     f"over its manifest-only worker-run twin "
                     f"{os.path.basename(twin)} (same execution, "
                     f"issue #154)")
    return previous, "paired", note


# ------------------------------------------------------------------- diff

def _ex_date_in_window(prev, cur):
    """The dated corporate action whose ex-date falls between the two
    sweeps' base dates (inclusive of the current side -- the window
    starts AT the ex-date, #130). Returns the action dict or None.
    Base date falls back to the ensemble date on legacy ensembles
    that carry no base_date. Undated actions (ex_date null) never
    open a window: they are feed-timing churn (#92)."""
    prev_base = _iso_date((prev.get("ensemble") or {}).get("base_date")
                          or (prev.get("ensemble") or {}).get("date"))
    cur_base = _iso_date((cur.get("ensemble") or {}).get("base_date")
                         or (cur.get("ensemble") or {}).get("date"))
    if not prev_base or not cur_base:
        return None
    for action in (cur.get("ensemble") or {}).get("corporate_actions") or []:
        ex = _iso_date((action or {}).get("ex_date"))
        if ex and prev_base <= ex <= cur_base:
            return action
    return None


def _rescale_state(view):
    """kronos_ex_rescale as recorded: True only for an explicit
    {"applied": true}. The live ensembles carry the key ABSENT (not
    null) on the ex-date itself -- absent and null both mean "rescale
    state not recorded", never "rescale not needed"."""
    value = (view.get("ensemble") or {}).get("kronos_ex_rescale")
    if isinstance(value, dict):
        return bool(value.get("applied")), value
    return False, None


def _pct_change(from_value, to_value):
    if from_value in (None, 0) or to_value is None:
        return None
    return _round((to_value - from_value) / abs(from_value) * 100)


def _section(changed, note, **fields):
    out = {"changed": changed, "note": note}
    out.update(fields)
    return out


def _diff_price(prev, cur, ex_action):
    """Price section: the ensemble base for contrast, and the price
    series (egx-data first) for the move itself -- ensemble-only
    diffing reports "nothing changed" while the price moved (#94).
    With an ex-date in window the move is decomposed: the headline
    number is the residual (raw minus mechanical), the mechanical
    part is shown as the cause. mechanical_pct is the action's own
    figure, dps over the post-ex base (ensemble.py:710)."""
    prev_ens, cur_ens = prev.get("ensemble") or {}, cur.get("ensemble") or {}
    prev_base, cur_base = prev_ens.get("base_price"), cur_ens.get("base_price")
    raw_pct = _pct_change(prev_base, cur_base)
    prev_series = {s["source"]: s for s in prev.get("price_series_last", [])}
    cur_series = {s["source"]: s for s in cur.get("price_series_last", [])}
    series_diff = {}
    for source in sorted(set(prev_series) | set(cur_series)):
        p, c = prev_series.get(source), cur_series.get(source)
        entry = {"from": p, "to": c}
        if p and c and p.get("last_close") is not None \
                and c.get("last_close") is not None:
            entry["close_delta_pct"] = _pct_change(p["last_close"],
                                                   c["last_close"])
            if p.get("last_volume") is not None \
                    and c.get("last_volume") is not None:
                entry["volume_delta_pct"] = _pct_change(
                    p["last_volume"], c["last_volume"])
        series_diff[source] = entry
    # Witness staleness: price_crosscheck says "agree" while its
    # witnesses are days stale -- the delta surfaces common_date vs
    # base_date as its own flag and never trusts status alone.
    witness = {}
    for label, view in (("prev", prev), ("cur", cur)):
        cross = (view.get("ensemble") or {}).get("price_crosscheck") or {}
        common = _iso_date(cross.get("common_date"))
        base_date = _iso_date((view.get("ensemble") or {}).get("base_date"))
        witness[label] = {"status": cross.get("status"),
                          "common_date": common, "base_date": base_date,
                          "stale": bool(common and base_date
                                        and common < base_date)}
    mechanical = None
    residual = raw_pct
    if ex_action is not None:
        mechanical = _fnum(ex_action.get("mechanical_pct"))
        if mechanical is not None and raw_pct is not None:
            residual = _round(raw_pct - mechanical)
    series_changed = any(
        entry.get("close_delta_pct") not in (None, 0)
        or entry.get("volume_delta_pct") not in (None, 0)
        for entry in series_diff.values())
    price_changed = raw_pct not in (None, 0) or series_changed
    flagged = False
    if ex_action is not None:
        flagged = True
    elif raw_pct is not None and abs(raw_pct) >= TH_BASE_PRICE_PCT:
        flagged = True
    if witness["cur"].get("stale"):
        flagged = True
    if ex_action is not None:
        note = (f"base crossed ex-date {ex_action.get('ex_date')}; "
                f"mechanical {mechanical:+.2f}%, market residual "
                f"{residual:+.2f}% (raw {raw_pct:+.2f}%)")
    elif raw_pct is None:
        note = "no base price on one side"
    else:
        note = f"base moved {raw_pct:+.2f}%"
    if witness["cur"].get("stale"):
        note += (f"; crosscheck witnesses stale: common_date "
                 f"{witness['cur']['common_date']} vs base_date "
                 f"{witness['cur']['base_date']} (status says "
                 f"\"{witness['cur']['status']}\")")
    return _section(price_changed,
                    note,
                    **{"from": {"base_price": prev_base,
                                "base_date": prev_ens.get("base_date"),
                                "base_source": prev_ens.get("base_source")},
                       "to": {"base_price": cur_base,
                              "base_date": cur_ens.get("base_date"),
                              "base_source": cur_ens.get("base_source")},
                       "delta": {"base_pct": raw_pct,
                                 "mechanical_pct": mechanical,
                                 "residual_pct": residual},
                       "flagged": flagged,
                       "price_series_last": series_diff,
                       "witness_stale": witness})


def _diff_horizons(prev, cur, ex_action):
    """Per-horizon diff. With an ex-date in window the horizon numbers
    are flagged unadjusted (Kronos rescale did not apply) and the
    mechanical part is recorded; the pp delta is measured against
    different bases, so the like-for-like view -- the implied target
    price (base x (1 + expected/100)) -- is printed alongside the
    rule-1 residual, and the note says which one to read."""
    prev_h = (prev.get("ensemble") or {}).get("horizons") or {}
    cur_h = (cur.get("ensemble") or {}).get("horizons") or {}
    prev_base = (prev.get("ensemble") or {}).get("base_price")
    cur_base = (cur.get("ensemble") or {}).get("base_price")
    mechanical = _fnum(ex_action.get("mechanical_pct")) \
        if ex_action is not None else None
    out = {}
    for horizon in ("day", "week", "month"):
        p, c = prev_h.get(horizon), cur_h.get(horizon)
        if p is None and c is None:
            out[horizon] = _section(None, "no data on either side")
            continue
        if p is None or c is None:
            out[horizon] = _section(
                None, "horizon present on one side only (shape change)",
                **{"from": p, "to": c, "flagged": True})
            continue
        from_move, to_move = p.get("expected_move_pct"), c.get("expected_move_pct")
        delta_pp = None
        if from_move is not None and to_move is not None:
            delta_pp = _round(to_move - from_move)
        flip = (p.get("direction") != c.get("direction"))
        conf_changed = (p.get("confidence") != c.get("confidence"))
        flagged = bool(flip or conf_changed
                       or (delta_pp is not None
                           and abs(delta_pp) >= TH_HORIZON_MOVE_PP)
                       or ex_action is not None)
        target = {}
        if prev_base and from_move is not None:
            target["from"] = _round(prev_base * (1 + from_move / 100), 4)
        if cur_base and to_move is not None:
            target["to"] = _round(cur_base * (1 + to_move / 100), 4)
        if target.get("from") and target.get("to"):
            target["delta_pct"] = _pct_change(target["from"], target["to"])
        residual_pp = None
        if delta_pp is not None and mechanical is not None:
            residual_pp = _round(delta_pp - mechanical)
        if ex_action is not None:
            if target.get("from") is not None \
                    and target.get("to") is not None \
                    and target.get("delta_pct") is not None:
                like_for_like = (f"read the implied target price "
                                 f"({target.get('from')} -> "
                                 f"{target.get('to')}, "
                                 f"{target.get('delta_pct'):+.2f}%) for "
                                 f"the like-for-like move, not the "
                                 f"{delta_pp:+.2f} pp headline")
            else:
                like_for_like = ("no like-for-like target price "
                                 "derivable (base missing on one side)")
            note = (f"ex-date in window ({ex_action.get('ex_date')}): "
                    f"horizon percentages are measured against "
                    f"different bases; {like_for_like}")
        elif flip:
            note = "direction flipped"
        elif delta_pp is not None:
            note = f"expected move moved {delta_pp:+.2f} pp"
        else:
            note = "no expected-move figure on one side"
        out[horizon] = _section(
            bool(flip or delta_pp not in (None, 0) or conf_changed),
            note,
            **{"direction_flip": flip,
               "expected_move_pct": {"from": from_move, "to": to_move,
                                     "delta_pp": delta_pp},
               "confidence": {"from": p.get("confidence"),
                              "to": c.get("confidence")},
               "flagged": flagged,
               "ex_date_decomposed": ex_action is not None,
               "mechanical_pp": mechanical,
               "residual_pp": residual_pp,
               "implied_target_price": target})
    return out


def _diff_families(prev, cur, ex_action):
    """Family scores. Null is "no data", never 0: a null <-> value
    transition is a shape change, flagged, and never reported as a
    flip from 0. A sign flip is always flagged; with an ex-date in
    window the flip carries its cause (the base change), not a
    standalone signal. Family scores are unitless, so the ex-date
    decomposition is cause-attribution, not a numeric mechanical
    part (mechanical_pct is a percentage of base and does not apply
    to a -1..1 score)."""
    prev_f = (prev.get("ensemble") or {}).get("family_scores") or {}
    cur_f = (cur.get("ensemble") or {}).get("family_scores") or {}
    out = {}
    for family in sorted(set(prev_f) | set(cur_f)):
        p, c = prev_f.get(family), cur_f.get(family)
        if p is None and c is None:
            out[family] = _section(None, "no data both sides",
                                   **{"from": None, "to": None,
                                      "flagged": False})
            continue
        if p is None or c is None:
            out[family] = _section(
                True, "family present on one side only (shape change, "
                "not a move from 0)",
                **{"from": p, "to": c, "flip": False, "flagged": True})
            continue
        delta = _round(c - p, 4)
        def _sign(value):
            return 1 if value > 0 else -1 if value < 0 else 0
        flip = bool(_sign(p) != _sign(c))
        flagged = bool(flip or abs(delta) >= TH_FAMILY_SCORE)
        cause = None
        if flip and ex_action is not None:
            cause = "ex-date base change"
            flagged = True
        note = ("no change" if delta == 0 else f"moved {delta:+.3f}")
        if flip:
            note = f"vote flipped {p:+.3f} -> {c:+.3f}" + (
                f" (cause: {cause})" if cause else "")
        out[family] = _section(delta != 0, note,
                               **{"from": p, "to": c, "delta": delta,
                                  "flip": flip, "flagged": flagged,
                                  "cause": cause,
                                  "ex_date_decomposed":
                                  ex_action is not None and flip})
    return out


def _diff_weights(prev, cur):
    """Calibration weights: the pinned factors and weights-file SHA.
    A weights change with no ledger-count change is a weights-file
    change (SHA differs); the counts themselves arrive with the
    Report Model ledger_pin and are null on the raw path."""
    prev_ens, cur_ens = prev.get("ensemble") or {}, cur.get("ensemble") or {}
    prev_aw, cur_aw = prev_ens.get("applied_weights") or {}, \
        cur_ens.get("applied_weights") or {}
    prev_factors, cur_factors = prev_aw.get("factors") or {}, \
        cur_aw.get("factors") or {}
    factors = {}
    changed = False
    for family in sorted(set(prev_factors) | set(cur_factors)):
        p, c = prev_factors.get(family), cur_factors.get(family)
        delta = None
        if p is not None and c is not None:
            delta = _round(c - p, 4)
        entry = {"from": p, "to": c, "delta": delta}
        if delta is not None and abs(delta) >= TH_APPLIED_FACTOR:
            changed = True
        factors[family] = entry
    prev_sha, cur_sha = prev_aw.get("file_sha256"), cur_aw.get("file_sha256")
    if prev_sha != cur_sha:
        changed = True
    prev_src, cur_src = prev_ens.get("weights_source"), cur_ens.get("weights_source")
    if prev_src != cur_src:
        changed = True
    prev_pin, cur_pin = prev.get("ledger_pin") or {}, cur.get("ledger_pin") or {}
    prev_elig, cur_elig = prev_pin.get("eligible") or {}, \
        cur_pin.get("eligible") or {}
    eligible = {}
    for family in sorted(set(prev_elig) | set(cur_elig)):
        p, c = prev_elig.get(family) or {}, cur_elig.get(family) or {}
        eligible[family] = {"from_n": p.get("n"), "to_n": c.get("n"),
                            "from_factor": p.get("factor"),
                            "to_factor": c.get("factor")}
    note = "weights unchanged" if not changed else "weights changed"
    if prev_pin.get("counts") is None and cur_pin.get("counts") is None:
        note += ("; ledger counts not carried by raw ensembles "
                 "(see #68 ledger_pin)")
    return _section(changed, note,
                    **{"weights_source": {"from": prev_src, "to": cur_src},
                       "applied_factors": factors,
                       "weights_file_sha256": {"from": prev_sha,
                                               "to": cur_sha},
                       "eligible": eligible,
                       "ledger_counts": {"from": prev_pin.get("counts"),
                                         "to": cur_pin.get("counts"),
                                         "source": prev_pin.get(
                                             "counts_source")},
                       "flagged": changed})


def _diff_corporate_actions(prev, cur):
    """Dedup-aware: dated blocks compare by (dps, ex_date); undated
    blocks (ex_date null) are feed-timing churn (#92) and are never
    reported as added/removed on their own -- the block count and
    the dps set are reported as context with the #92 link."""
    def blocks(view):
        return (view.get("ensemble") or {}).get("corporate_actions")
    prev_ca, cur_ca = blocks(prev), blocks(cur)
    if prev_ca is None and cur_ca is None:
        return _section(None, "no corporate-action data on either side",
                        **{"added": [], "removed": [], "flagged": False})
    prev_list, cur_list = prev_ca or [], cur_ca or []
    def dated(actions):
        return {(a.get("type"), _round(a.get("dps"), 4),
                 _iso_date(a.get("ex_date")))
                for a in actions if _iso_date(a.get("ex_date"))}
    def undated(actions):
        return [a for a in actions if not _iso_date(a.get("ex_date"))]
    prev_dated, cur_dated = dated(prev_list), dated(cur_list)
    added = sorted(cur_dated - prev_dated)
    removed = sorted(prev_dated - cur_dated)
    prev_und, cur_und = undated(prev_list), undated(cur_list)
    changed = bool(added or removed)
    if changed:
        note = f"dated corporate actions changed: +{len(added)} / -{len(removed)}"
    else:
        note = (f"same dated blocks; {len(cur_und)} undated duplicate "
                f"block(s) unchanged -- feed-timing churn, see {ISSUE_92}")
    return _section(changed, note,
                    **{"added": [list(a) for a in added],
                       "removed": [list(a) for a in removed],
                       "undated_blocks": {"from": len(prev_und),
                                          "to": len(cur_und),
                                          "dps": sorted(
                                              {_round(a.get("dps"), 4)
                                               for a in cur_und
                                               if a.get("dps") is not None})},
                       "flagged": changed})


def _diff_risk(prev, cur):
    """Risk events diff by (type, severity, title) set; titles are
    the identity. A title change reads as added+removed, and the
    delta says so. Level / conf-cap changes always flag."""
    prev_r, cur_r = (prev.get("ensemble") or {}).get("risk") or {}, \
        (cur.get("ensemble") or {}).get("risk") or {}
    def events(risk):
        return {(e.get("type"), e.get("severity"), e.get("title"))
                for e in risk.get("events") or []}
    prev_ev, cur_ev = events(prev_r), events(cur_r)
    added = sorted(cur_ev - prev_ev)
    removed = sorted(prev_ev - cur_ev)
    level_changed = prev_r.get("level") != cur_r.get("level")
    cap_changed = prev_r.get("conf_cap") != cur_r.get("conf_cap")
    changed = bool(level_changed or cap_changed or added or removed)
    flagged = bool(level_changed or cap_changed)
    if level_changed:
        note = (f"risk level moved {prev_r.get('level')} -> "
                f"{cur_r.get('level')}")
    elif added or removed:
        note = (f"risk level unchanged ({cur_r.get('level')}); event "
                f"set churned: +{len(added)} / -{len(removed)}")
    else:
        note = f"risk unchanged ({cur_r.get('level')})"
    return _section(changed, note,
                    **{"level": {"from": prev_r.get("level"),
                                 "to": cur_r.get("level")},
                       "conf_cap": {"from": prev_r.get("conf_cap"),
                                    "to": cur_r.get("conf_cap")},
                       "events_added": [list(e) for e in added],
                       "events_removed": [list(e) for e in removed],
                       "flagged": flagged})


def _diff_news(prev, cur):
    """News / disclosure diff by derived identity set, never by count
    or latest date (counts and latest dates are context only: the
    feed is a rolling window and latest dates go backwards). An item
    whose identity key changed type between sweeps (same title and
    date, resolved_url on one side only) is reported as re-keyed,
    not as added+removed phantom churn."""
    out = {}
    for label, key in (("news", "news_items"),
                       ("disclosures", "disclosure_items")):
        prev_items = {i["identity_key"]: i
                      for i in prev.get(key, [])}
        cur_items = {i["identity_key"]: i
                     for i in cur.get(key, [])}
        added_keys = set(cur_items) - set(prev_items)
        removed_keys = set(prev_items) - set(cur_items)
        # Re-keyed: same (title, date) on both sides, different key.
        rekeyed = []
        removed_by_title = {}
        for k in removed_keys:
            item = prev_items[k]
            removed_by_title[(item.get("title"), item.get("date"))] = k
        for k in sorted(added_keys):
            item = cur_items[k]
            match = removed_by_title.get((item.get("title"),
                                          item.get("date")))
            if match is not None:
                rekeyed.append({"title": item.get("title"),
                                "date": item.get("date"),
                                "from_key": match,
                                "from_key_type":
                                prev_items[match]["key_type"],
                                "to_key": k,
                                "to_key_type": item["key_type"]})
                added_keys.discard(k)
                removed_keys.discard(match)
        added = [cur_items[k] for k in sorted(added_keys)]
        removed = [prev_items[k] for k in sorted(removed_keys)]
        unchanged = len(set(prev_items) & set(cur_items))
        changed = bool(added or removed or rekeyed)
        note = (f"{len(prev_items)} -> {len(cur_items)} items, "
                f"{unchanged} unchanged")
        if rekeyed:
            note += (f"; {len(rekeyed)} item(s) re-keyed between "
                     f"identity schemes (same title+date, resolved_url "
                     f"present on one side only)")
        # Latest dates are context only, never the diff.
        latest_key = ("latest_news_date" if label == "news"
                      else "latest_disclosure_date")
        out[label] = _section(
            changed, note,
            **{f"{label}_count": {"from": len(prev_items),
                                  "to": len(cur_items)},
               "added": added, "removed": removed, "rekeyed": rekeyed,
               "unchanged": unchanged,
               "latest_date": {
                   "from": (prev.get("news_meta") or {}).get(latest_key),
                   "to": (cur.get("news_meta") or {}).get(latest_key),
                   "from_iso": (prev.get("news_meta") or {}).get(
                       latest_key + "_iso"),
                   "to_iso": (cur.get("news_meta") or {}).get(
                       latest_key + "_iso")},
               "flagged": changed})
    out["identity_scheme"] = NEWS_IDENTITY_SCHEME
    return out


def _diff_tools(prev, cur):
    """Tool add / remove / status change is a shape note, never a
    ticker change. A tool present on one side only is listed, never
    treated as failed."""
    def tools(view):
        out = {}
        for result in (view.get("digest") or {}).get("results", []) or []:
            summary = result.get("summary") or {}
            out[result.get("tool")] = {
                "conclusion": result.get("conclusion"),
                "status": summary.get("status"),
                "has_summary": "summary" in result}
        return out
    prev_t, cur_t = tools(prev), tools(cur)
    added = sorted(set(cur_t) - set(prev_t))
    removed = sorted(set(prev_t) - set(cur_t))
    status_changed = []
    for tool in sorted(set(prev_t) & set(cur_t)):
        if prev_t[tool] != cur_t[tool]:
            status_changed.append({"tool": tool,
                                   "from": prev_t[tool],
                                   "to": cur_t[tool]})
    changed = bool(added or removed or status_changed)
    note = (f"same {len(cur_t)}-tool shape both sides"
            if not changed else
            f"tool set moved: +{len(added)} / -{len(removed)} / "
            f"{len(status_changed)} status change(s)")
    return _section(changed, note,
                    **{"added": added, "removed": removed,
                       "status_changed": status_changed,
                       "flagged": changed})


def _diff_calibration(prev, cur, ex_action):
    """Calibration section: the pinned weights and (when the model
    carries them) the pinned ledger counts. Matured and eligible-n
    are never equated: the applied weights are eligible at n=5 per
    family while the ledger holds 9 matured forecasts. No accuracy
    figure is printed (D4 / #79 gate)."""
    weights = _diff_weights(prev, cur)
    prev_pin, cur_pin = prev.get("ledger_pin") or {}, cur.get("ledger_pin") or {}
    counts_changed = False
    prev_counts, cur_counts = prev_pin.get("counts"), cur_pin.get("counts")
    counts_diff = {}
    if prev_counts is not None and cur_counts is not None:
        for key in sorted(set(prev_counts) | set(cur_counts)):
            counts_diff[key] = {"from": prev_counts.get(key),
                                "to": cur_counts.get(key)}
            if prev_counts.get(key) != cur_counts.get(key):
                counts_changed = True
    changed = bool(weights["changed"] or counts_changed)
    note = weights["note"]
    if ex_action is not None and prev_counts is not None \
            and prev_counts.get("dividend_adjusted") == 0:
        note += (f"; ledger rows behind this section are not "
                 f"dividend-adjusted (dividend_adjusted 0) while a "
                 f"horizon spans a known ex-date -- see {ISSUE_129}")
    elif ex_action is not None:
        note += ("; dividend-adjustment of the ledger rows cannot be "
                 f"checked on the raw path (no ledger pin) -- see "
                 f"{ISSUE_129}")
    return _section(changed, note,
                    **{"weights": weights,
                       "ledger_counts": counts_diff or None,
                       "ledger_counts_source": prev_pin.get("counts_source"),
                       "flagged": changed})


# ------------------------------------------------------------- top level

def compute_delta(prev, cur):
    """The pure diff: two sweep views -> one delta dict. Assumes the
    pair has already passed the tripwire (checked by delta_pair);
    compute_delta itself never refuses a pair."""
    ex_action = _ex_date_in_window(prev, cur)
    rescaled, _ = _rescale_state(cur)
    prev_ens, cur_ens = prev.get("ensemble") or {}, cur.get("ensemble") or {}
    pair_rule = (f"same ticker + same job shape "
                 f"({cur.get('job_shape')}) + most recent by "
                 f"digest.finished")
    shape_warning = None
    if prev.get("job_shape") != cur.get("job_shape"):
        # The shape rule is the resolver's: it never pairs across
        # shapes. The diff core still diffs an explicitly handed
        # cross-shape pair (the harness reproduces the flat
        # scoping's cross-shape Pair C numbers this way) but says
        # so out loud.
        shape_warning = (f"different job shapes: previous "
                         f"'{prev.get('job_shape')}' vs current "
                         f"'{cur.get('job_shape')}' -- tool-set "
                         f"differences are shape, not ticker change")
    sections = {
        "price": _diff_price(prev, cur, ex_action),
        "horizons": _diff_horizons(prev, cur, ex_action),
        "family_scores": _diff_families(prev, cur, ex_action),
        "weights": _diff_weights(prev, cur),
        "corporate_actions": _diff_corporate_actions(prev, cur),
        "risk": _diff_risk(prev, cur),
        "news": _diff_news(prev, cur),
        "tools": _diff_tools(prev, cur),
        "calibration": _diff_calibration(prev, cur, ex_action),
    }
    ex_section = {"in_window": ex_action is not None,
                  "ex_date": _iso_date(ex_action.get("ex_date"))
                  if ex_action else None,
                  "mechanical_pct": _fnum(ex_action.get("mechanical_pct"))
                  if ex_action else None,
                  "kronos_rescaled": rescaled,
                  "flag": None}
    if ex_action is not None and not rescaled:
        ex_section["flag"] = (
            "rescale did not apply on the ex-date sweep -- the horizon "
            f"numbers are unadjusted; see {ISSUE_130}")
    return {"delta_version": DELTA_VERSION,
            "ticker": cur.get("ticker"),
            "current_sweep": cur.get("sweep_dir"),
            "previous_sweep": prev.get("sweep_dir"),
            "current_archive_sha": cur.get("archive_sha"),
            "previous_archive_sha": prev.get("archive_sha"),
            "pair_rule": pair_rule,
            "pair_invalid": None,
            "shape_warning": shape_warning,
            "sections": sections,
            "ex_date": ex_section,
            "first_sweep": False}


def first_sweep_delta(cur):
    """First sweep of this ticker + job shape: a normal output, not
    an error. Every section reports "no previous sweep"."""
    sections = {}
    for name in ("price", "horizons", "family_scores", "weights",
                 "corporate_actions", "risk", "news", "tools",
                 "calibration"):
        sections[name] = _section(
            None, "no previous sweep of this ticker + job shape")
    return {"delta_version": DELTA_VERSION,
            "ticker": cur.get("ticker"),
            "current_sweep": cur.get("sweep_dir"),
            "previous_sweep": None,
            "current_archive_sha": cur.get("archive_sha"),
            "previous_archive_sha": None,
            "pair_rule": None,
            "pair_invalid": None,
            "shape_warning": None,
            "sections": sections,
            "ex_date": {"in_window": False, "ex_date": None,
                        "mechanical_pct": None, "kronos_rescaled": False,
                        "flag": None},
            "first_sweep": True}


def unavailable_delta(cur, reason):
    """A previous sweep exists but carries no ensemble (worker sweep
    before #67): the delta is unavailable. Distinct from first_sweep
    and from pair_invalid -- three states, three renderings, never
    conflated."""
    return {"delta_version": DELTA_VERSION,
            "ticker": cur.get("ticker"),
            "current_sweep": cur.get("sweep_dir"),
            "previous_sweep": None,
            "current_archive_sha": cur.get("archive_sha"),
            "previous_archive_sha": None,
            "pair_rule": None,
            "pair_invalid": None,
            "shape_warning": None,
            "sections": None,
            "ex_date": {"in_window": False, "ex_date": None,
                        "mechanical_pct": None, "kronos_rescaled": False,
                        "flag": None},
            "first_sweep": False,
            "delta_unavailable": reason}


def invalid_pair_delta(prev, cur, problems):
    """The ticker tripwire failed on one side: the pair is refused,
    never silently diffed."""
    return {"delta_version": DELTA_VERSION,
            "ticker": cur.get("ticker"),
            "current_sweep": cur.get("sweep_dir"),
            "previous_sweep": prev.get("sweep_dir"),
            "current_archive_sha": cur.get("archive_sha"),
            "previous_archive_sha": prev.get("archive_sha"),
            "pair_rule": None,
            "pair_invalid": {"reason": "ticker mismatch in sweep data",
                             "problems": problems},
            "shape_warning": None,
            "sections": None,
            "ex_date": {"in_window": False, "ex_date": None,
                        "mechanical_pct": None, "kronos_rescaled": False,
                        "flag": None},
            "first_sweep": False}


def delta_pair(prev_dir, cur_dir, archive_sha=None):
    """Load two sweep dirs and diff them. A worker-run dir on either
    side yields delta_unavailable; a tripwire failure yields
    pair_invalid; both are normal outputs (exit 0), not crashes."""
    cur = load_sweep_view(cur_dir, archive_sha)
    if cur.get("kind") == "worker-run":
        return unavailable_delta(
            cur, "current sweep is a worker sweep with no ensemble "
            f"(see {ISSUE_67})")
    prev = load_sweep_view(prev_dir, archive_sha)
    if prev.get("kind") == "worker-run":
        return unavailable_delta(
            cur, "previous sweep is a worker sweep with no ensemble "
            f"(see {ISSUE_67})")
    if prev.get("ensemble_absent") or cur.get("ensemble_absent"):
        missing = prev_dir if prev.get("ensemble_absent") else cur_dir
        return unavailable_delta(
            cur, f"sweep dir {os.path.basename(missing)} carries no "
            "ensemble.json")
    problems = (prev.get("tripwire") or []) + (cur.get("tripwire") or [])
    if problems:
        return invalid_pair_delta(prev, cur, problems)
    return compute_delta(prev, cur)


def to_markdown(delta):
    """MD twin of a delta dict: the same numbers, descriptive-
    conditional wording only (legal gate #77)."""
    lines = [f"# Delta: {delta.get('ticker')}",
             "",
             f"Current sweep: {delta.get('current_sweep')}",
             f"Previous sweep: {delta.get('previous_sweep')}",
             ""]
    if delta.get("first_sweep"):
        lines.append("First sweep of this ticker -- nothing to compare "
                     "against yet.")
        return "\n".join(lines) + "\n"
    if delta.get("delta_unavailable"):
        lines.append(f"Delta unavailable: {delta['delta_unavailable']}")
        return "\n".join(lines) + "\n"
    if delta.get("pair_invalid"):
        lines.append("Pair invalid: "
                     f"{delta['pair_invalid']['reason']}")
        for problem in delta["pair_invalid"].get("problems", []):
            lines.append(f"- {problem['field']}: expected "
                         f"{problem['expected']}, found "
                         f"{problem['found']}")
        return "\n".join(lines) + "\n"
    sections = delta["sections"]
    price = sections["price"]
    lines.append("## Price")
    lines.append(f"- {price['note']}")
    for horizon in ("day", "week", "month"):
        entry = sections["horizons"][horizon]
        move = entry.get("expected_move_pct") or {}
        lines.append(f"## Horizon: {horizon}")
        lines.append(f"- Expected move: {move.get('from')}% -> "
                     f"{move.get('to')}% ({move.get('delta_pp'):+.2f} pp)" if move.get('delta_pp') is not None else
                     f"- Expected move: {move.get('from')}% -> {move.get('to')}%")
        lines.append(f"- {entry['note']}")
    lines.append("## Family scores")
    for family, entry in sorted(sections["family_scores"].items()):
        lines.append(f"- {family}: {entry.get('from')} -> "
                     f"{entry.get('to')} -- {entry['note']}")
    lines.append("## Weights")
    lines.append(f"- {sections['weights']['note']}")
    lines.append("## Corporate actions")
    lines.append(f"- {sections['corporate_actions']['note']}")
    lines.append("## Risk")
    lines.append(f"- {sections['risk']['note']}")
    lines.append("## News")
    for label in ("news", "disclosures"):
        entry = sections["news"][label]
        lines.append(f"- {label}: {entry['note']}")
    lines.append("## Tools")
    lines.append(f"- {sections['tools']['note']}")
    lines.append("## Calibration")
    lines.append(f"- {sections['calibration']['note']}")
    ex = delta["ex_date"]
    if ex.get("in_window"):
        lines.append("## Ex-date")
        lines.append(f"- Ex-date {ex['ex_date']} in window; mechanical "
                     f"{ex['mechanical_pct']:+.2f}%; Kronos rescaled: "
                     f"{ex['kronos_rescaled']}")
        if ex.get("flag"):
            lines.append(f"- {ex['flag']}")
    return "\n".join(lines) + "\n"


def _dump(delta, out_path):
    text = json.dumps(delta, indent=2, sort_keys=True,
                      ensure_ascii=False) + "\n"
    if out_path:
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write(text)
        md_path = out_path[:-5] + ".md" if out_path.endswith(".json") \
            else out_path + ".md"
        with open(md_path, "w", encoding="utf-8") as handle:
            handle.write(to_markdown(delta))
        return out_path, md_path
    sys.stdout.write(text)
    return None, None


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Delta (#70): what changed since the last sweep "
                    "of a ticker.")
    parser.add_argument("prev_dir", nargs="?",
                        help="previous sweep dir (explicit pair)")
    parser.add_argument("cur_dir", nargs="?",
                        help="current sweep dir")
    parser.add_argument("--resolve", metavar="ARCHIVE_ROOT",
                        help="resolve the previous sweep from an "
                             "archive checkout instead of passing it")
    parser.add_argument("--ticker", help="ticker for --resolve")
    parser.add_argument("--shape", help="job shape for --resolve")
    parser.add_argument("--out", help="write delta JSON (+ MD twin) "
                                      "to this path")
    parser.add_argument("--model", action="store_true",
                        help="diff through the sweeps' report-model.json "
                             "files (model_to_view) instead of the raw "
                             "ensemble files")
    parser.add_argument("--archive-sha", default=None,
                        help="archive commit SHA to pin in the output")
    args = parser.parse_args(argv)
    try:
        if args.model and args.resolve:
            parser.error("--model cannot be combined with --resolve "
                         "(the resolver is raw-path only)")
        if args.model:
            if not args.prev_dir or not args.cur_dir:
                parser.error("--model needs PREV_DIR CUR_DIR")
            delta = delta_pair_models(args.prev_dir, args.cur_dir,
                                      args.archive_sha)
        elif args.resolve:
            if not args.cur_dir or not args.ticker or not args.shape:
                parser.error("--resolve needs CUR_DIR, --ticker and "
                             "--shape")
            previous, status, note = resolve_pair(
                args.resolve, args.ticker, args.shape, args.cur_dir,
                args.archive_sha)
            cur = load_sweep_view(args.cur_dir, args.archive_sha)
            if status == "paired":
                delta = delta_pair(previous, args.cur_dir,
                                   args.archive_sha)
                delta["pair_resolution_note"] = note
            elif status == "first_sweep":
                delta = first_sweep_delta(cur)
                delta["pair_resolution_note"] = note
            elif status == "delta_unavailable":
                delta = unavailable_delta(cur, note)
                delta["pair_resolution_note"] = note
            else:
                print(f"resolve error: {note}", file=sys.stderr)
                return 2
        else:
            if not args.prev_dir or not args.cur_dir:
                parser.error("need PREV_DIR CUR_DIR, or --resolve")
            delta = delta_pair(args.prev_dir, args.cur_dir,
                               args.archive_sha)
    except DeltaError as exc:
        print(f"delta: {exc}", file=sys.stderr)
        return 2
    _dump(delta, args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
