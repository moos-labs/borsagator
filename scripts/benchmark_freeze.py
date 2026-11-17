#!/usr/bin/env python3
"""Borsagator benchmark freeze (issue #79).

Runs AFTER ensemble.py and BEFORE the archive stage, in the sweep
working directory, on BOTH sweep paths (Actions step +
scripts/merge.py). Writes one ensemble-shaped JSON per entrant under
benchmark/ in the sweep dir, so the calibration ledger can score the
ensemble against fixed baselines and alternatives under one scoring
rule.

Entrants (fixed registry, issue #79 §4):
  family-price-forecast, family-technicals, family-sentiment,
  family-agent, family-fundamentals, kronos-alone, raw-llm-cohere,
  buy-and-hold. The ensemble itself is NOT duplicated — it is the
  reference, read from digest/ensemble.json.

Rules that matter:
- Family-alone is definition (a): re-run the combine with the
  family's weight 1 and all others 0. kmove is zeroed for non-price
  families (it IS the Kronos move, so keeping it would make every
  alone-forecast mostly Kronos); kept for family-price-forecast,
  recomputed from the Kronos CSV, never inverted from the clamped
  price_score.
- Kronos-alone mirrors ensemble.py's kronos_at() row-index rule
  exactly (bar rows, clamped), never a calendar-date lookup, never
  the CSV's first row as the base.
- Raw-LLM uses the FROZEN prompt scripts/benchmark_prompt_v1.txt,
  model command-r-08-2024, temperature 0, one call, no retry, no
  fallback model. Key absent / call failed / response unparseable
  all produce an absent record, never a failure.
- Buy-and-hold is flat 0% with a pure ±1.28σ√h_eff range.
- Corporate actions and per-horizon corporate_action marks are
  copied VERBATIM from the ensemble into every entrant, so the
  ledger's dividend adjustment / gap-flagging behaves identically.
- A frozen entrant replays byte-identical from the archived inputs
  except frozen_at (the one wall-clock field).

Failure semantics (mirror ensemble.py): the freeze NEVER fails the
sweep. A crash writes benchmark/freeze_error.txt + a warning line
in digest.md and exits 0. A sweep with no benchmark/ dir at all is
legal (every pre-#79 sweep). Stdlib only.
"""
import csv
import hashlib
import json
import math
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CWD = os.getcwd()
DIGEST_JSON = os.path.join(CWD, "digest", "digest.json")
ENSEMBLE_JSON = os.path.join(CWD, "digest", "ensemble.json")
DIGEST_MD = os.path.join(CWD, "digest", "digest.md")
KRONOS_CSV = os.path.join(CWD, "collected", "kronos", "forecast.csv")
PROMPT_FILE = os.path.join(HERE, "benchmark_prompt_v1.txt")
BENCH_DIR = os.path.join(CWD, "benchmark")

VERSION = 1
ENTRANTS = ("family-price-forecast", "family-technicals",
            "family-sentiment", "family-agent", "family-fundamentals",
            "kronos-alone", "raw-llm-cohere", "buy-and-hold")
FAMILIES = ("price-forecast", "technicals", "sentiment", "agent",
            "fundamentals")
LLM_MODEL = "command-r-08-2024"
# v2 endpoint: the request body ({messages, response_format}) and
# the response parse (message.content) are the v2 contract — v1
# uses `message`/`text` and rejects this model with "this model is
# not supported with '/v1/chat', please use '/v2/chat' instead"
# (Cohere migration guide, docs.cohere.com/docs/migrating-v1-to-v2).
LLM_URL_DEFAULT = "https://api.cohere.com/v2/chat"
DIRECTIONS = ("up", "down", "flat")

# Pinned literals, used only when the ensemble import fails (the
# freeze records constants_source so a reader can tell).
_HORIZONS_FALLBACK = {"day": 1, "week": 5, "month": 21}
_RISK_MULT_FALLBACK = {"none": 1.0, "elevated": 1.2, "shock": 1.5,
                       "unknown": 1.3}


def _load_constants():
    """HORIZONS bars + RISK_MULT from ensemble.py (one source of
    truth); pinned literals only when the import fails."""
    try:
        sys.path.insert(0, HERE)
        import ensemble
        return (dict(ensemble.HORIZONS), dict(ensemble.RISK_MULT),
                "ensemble.py")
    except Exception:
        return (dict(_HORIZONS_FALLBACK), dict(_RISK_MULT_FALLBACK),
                "pinned-literals")


HORIZONS, RISK_MULT, CONSTANTS_SOURCE = _load_constants()


def fnum(v):
    try:
        return float(v)
    except Exception:
        return None


def load_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _r2(x):
    return round(x, 2) if isinstance(x, (int, float)) else x


def _r3(x):
    return round(x, 3) if isinstance(x, (int, float)) else x


def direction_of(expected_frac):
    if expected_frac > 0.0075:
        return "up"
    if expected_frac < -0.0075:
        return "down"
    return "flat"


def sweep_target(digest):
    """Archive-style sweep dir (same naming as archive.py /
    merge.py sweep_dir_name): finished time + job slug + run id.
    The run id comes from BENCHMARK_RUN_ID (set by merge.py to the
    claim id), GITHUB_RUN_ID (Actions), else 'local'. The ledger
    does not depend on this string — it keys benchmark rows by the
    sweep dir it enumerates — so a fallback here is informational
    only, never a scoring input."""
    job = str((digest or {}).get("job") or "unknown-job")
    slug = re.sub(r"[^a-z0-9]+", "-", job.lower()).strip("-")[:60] or "job"
    run_id = (os.environ.get("BENCHMARK_RUN_ID")
              or os.environ.get("GITHUB_RUN_ID") or "local")
    date_str = str((digest or {}).get("date") or "")[:10]
    hhmmss = "000000"
    try:
        fin = str((digest or {}).get("finished") or "")
        dt = datetime.fromisoformat(fin.replace("Z", "+00:00"))
        date_str = dt.strftime("%Y-%m-%d")
        hhmmss = dt.strftime("%H%M%S")
    except Exception:
        pass
    if not date_str:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"sweeps/{date_str}/{hhmmss}__{slug}__run{run_id}"


def read_kronos_csv(digest):
    """Read collected/kronos/forecast.csv exactly as ensemble.py
    does (DictReader, close/high/low, drop rows with no close).
    Returns (path, first_row_date, fallback_note) or (None, None,
    reason) when absent / unparseable. The empty-but-present +
    kronos-ok fallback (forecast.csv_last_close x 10) mirrors the
    ensemble's, same conditions, and is recorded when it fires."""
    if not os.path.exists(KRONOS_CSV):
        return None, None, "no-kronos-csv"
    try:
        with open(KRONOS_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    except Exception:
        return None, None, "kronos-csv-unparseable"
    path = []
    first_date = None
    for row in rows:
        c = fnum(row.get("close"))
        if not c:
            continue
        if first_date is None:
            raw = str(row.get("date") or "")[:10]
            first_date = raw if re.match(r"^\d{4}-\d{2}-\d{2}$", raw) else None
        h, l = fnum(row.get("high")), fnum(row.get("low"))
        path.append((c, h or c, l or c))
    if path:
        return path, first_date, None
    # Empty CSV: the ensemble's fallback, same conditions.
    results = {r.get("tool"): r for r in (digest or {}).get("results", [])
               if isinstance(r, dict) and r.get("tool")}
    kr = results.get("kronos") or {}
    last = None
    if kr.get("status") == "ok":
        last = fnum(((kr.get("summary") or {}).get("metrics") or {})
                    .get("forecast.csv_last_close"))
    if last:
        return [(last, last, last)] * 10, None, (
            "fallback: empty forecast.csv, kronos ok, "
            "forecast.csv_last_close x 10")
    return None, None, "kronos-csv-unparseable"


def kronos_at(path, base, bar):
    """Mirror of ensemble.py's kronos_at(): row-index rule, same
    clamping. bar is a Kronos bar count (calendar days)."""
    if not path:
        return None
    i = min(bar, len(path)) - 1
    c, h, l = path[i]
    return {"close": c, "move": c / base - 1.0,
            "band": max((h - l) / 2.0 / base, 0.004),
            "short": len(path) < bar}


def rescale_kronos(path, ens):
    """Issue #130 ex-date rescale, honoured exactly as the ensemble
    recorded it: applied=true + factor -> multiply the whole path.
    Field absent / null (pre-#130 ensembles) -> 'unknown', NO
    rescale — a silent rescale would diverge from what the
    ensemble actually used. Returns (path, record)."""
    rec = ens.get("kronos_ex_rescale")
    if not isinstance(rec, dict):
        return path, "unknown"
    if rec.get("applied") and fnum(rec.get("factor")):
        f = float(rec["factor"])
        return ([(c * f, h * f, l * f) for (c, h, l) in path],
                {"applied": True, "factor": rec["factor"],
                 "ex_date": rec.get("ex_date")})
    return path, {"applied": False,
                  "reason": rec.get("reason") or "not applied"}


def base_header(ens, digest, entrant, inputs, derivation, extra=None):
    """Header fields shared by every frozen file (present + absent)."""
    risk = (ens or {}).get("risk") or {}
    check = (ens or {}).get("price_crosscheck") or {}
    doc = {
        "tool": "benchmark-freeze", "version": VERSION,
        "entrant": entrant, "status": "present",
        "ticker": (ens or {}).get("ticker") or (digest or {}).get("ticker"),
        "as_of": str((ens or {}).get("date")
                     or (digest or {}).get("date") or "")[:10],
        "sweep": sweep_target(digest),
        "base_price": (ens or {}).get("base_price"),
        "base_source": (ens or {}).get("base_source"),
        "base_date": (ens or {}).get("base_date"),
        "base_stale": bool(check.get("base_stale")),
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "inputs_sha256": inputs,
        "derivation": derivation,
        "corporate_actions": (ens or {}).get("corporate_actions") or [],
        "risk": {"level": risk.get("level"),
                 "conf_cap": risk.get("conf_cap"),
                 "price_mult": risk.get("price_mult")},
        "sigma_daily": (ens or {}).get("sigma_daily"),
        "sessions_per_calendar_day": (ens or {}).get(
            "sessions_per_calendar_day"),
        "constants_source": CONSTANTS_SOURCE,
    }
    if extra:
        doc.update(extra)
    return doc


def write_json(name, doc):
    os.makedirs(BENCH_DIR, exist_ok=True)
    path = os.path.join(BENCH_DIR, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1, ensure_ascii=False, sort_keys=True)
    return path


def absent_file(ens, digest, entrant, reason, inputs, derivation):
    doc = base_header(ens, digest, entrant, inputs, derivation)
    doc["status"] = "absent"
    doc["reason"] = reason
    doc.pop("horizons", None)
    # An absent record carries no forecast fields.
    for k in ("sigma_daily", "sessions_per_calendar_day"):
        doc.pop(k, None)
    write_json(f"{entrant}.json", doc)
    return reason


def horizon_block(ens_h, direction, expected_pct, low_pct, high_pct,
                  confidence, net_score, families, extra=None):
    """One ensemble-shaped horizon block. confidence_basis /
    extra keys ride alongside; None values stay explicit."""
    block = {
        "direction": direction,
        "expected_move_pct": _r2(expected_pct),
        "range_low_pct": _r2(low_pct),
        "range_high_pct": _r2(high_pct),
        "confidence": confidence,
        "net_score": net_score,
        "families": families,
        "trading_sessions": (ens_h or {}).get("trading_sessions"),
        "horizon_short": bool((ens_h or {}).get("horizon_short")),
    }
    if isinstance((ens_h or {}).get("corporate_action"), dict):
        block["corporate_action"] = (ens_h or {}).get("corporate_action")
    if extra:
        block.update(extra)
    return block


def freeze_family_alone(ens, digest, fam, kronos, kronos_first_date,
                        kronos_rescale, inputs):
    """Definition (a): re-run the combine with this family's weight
    1, all others 0. kmove zeroed for non-price families; kept for
    price-forecast (recomputed from the Kronos CSV)."""
    entrant = f"family-{fam}"
    scores = (ens or {}).get("family_scores") or {}
    risk = (ens or {}).get("risk") or {}
    conf_cap = risk.get("conf_cap")
    if conf_cap is None:
        conf_cap = 0.6
    risk_mult = RISK_MULT.get(risk.get("level"), 1.0)
    sigma = fnum((ens or {}).get("sigma_daily")) or 0.0
    density = fnum((ens or {}).get("sessions_per_calendar_day")) or (5 / 7)
    horizons = {}
    for hname, bar in HORIZONS.items():
        ens_h = ((ens or {}).get("horizons") or {}).get(hname)
        if not isinstance(ens_h, dict):
            continue
        if fam == "price-forecast":
            score = fnum(((ens_h.get("families") or {})
                          .get("price-forecast")))
        else:
            score = fnum(scores.get(fam))
        if score is None:
            continue
        h_eff = ens_h.get("trading_sessions")
        if not isinstance(h_eff, int) or h_eff <= 0:
            h_eff = max(1, round(bar * density))
        vol_h = sigma * math.sqrt(h_eff)
        ka = None
        kmove = 0.0
        ka_band = 0.0
        if fam == "price-forecast":
            ka = kronos_at(kronos, (ens or {}).get("base_price"), bar) \
                if kronos else None
            if ka is None:
                continue
            kmove, ka_band = ka["move"], ka["band"]
        expected = .6 * kmove + .4 * score * (1.28 * vol_h)
        half = max(1.28 * vol_h, ka_band) * risk_mult * 1.0
        conf = min(conf_cap, .20 + .45 * 1.0 + .10 * (1 / 5))
        horizons[hname] = horizon_block(
            ens_h, direction_of(expected), expected * 100,
            (expected - half) * 100, (expected + half) * 100,
            _r2(conf), _r3(score), {fam: _r3(score)})
    if not horizons:
        if fam == "price-forecast" and not kronos:
            return absent_file(
                ens, digest, entrant, "no-kronos-csv", inputs,
                "family-alone-v1: price-forecast needs the Kronos path "
                "to recompute kmove; CSV absent")
        return absent_file(
            ens, digest, entrant, "family-did-not-vote", inputs,
            f"family-alone-v1: {fam} score null in every horizon")
    if fam == "price-forecast":
        derivation = (
            "family-alone-v1: combine re-run, weight 1 for "
            "price-forecast, 0 else; kmove recomputed from the Kronos "
            "CSV (kronos_at row-index mirror), never inverted from the "
            "clamped price_score; risk mult + conf formula as "
            "ensemble.py; single voter, no disagreement widening")
    else:
        derivation = (
            f"family-alone-v1: combine re-run, weight 1 for {fam}, "
            "0 else; kmove zeroed (non-price family — the Kronos "
            "anchor belongs to price-forecast alone); risk mult + "
            "conf formula as ensemble.py; single voter, no "
            "disagreement widening")
    extra = {}
    if fam == "price-forecast":
        extra = {"kronos_first_row_date": kronos_first_date,
                 "kronos_row0_predates_asof":
                     bool(kronos_first_date and (ens or {}).get("date")
                          and kronos_first_date < str((ens or {}).get("date"))[:10]),
                 "kronos_rescale": kronos_rescale}
    doc = base_header(ens, digest, entrant, inputs, derivation, extra)
    doc["horizons"] = horizons
    write_json(f"{entrant}.json", doc)
    return "present"


def freeze_kronos_alone(ens, digest, kronos, kronos_first_date,
                        kronos_rescale, inputs):
    """Mirror kronos_at() exactly: same CSV, same row-index rule,
    same clamping. Base is ALWAYS the sweep's base_price."""
    entrant = "kronos-alone"
    if not kronos:
        return absent_file(
            ens, digest, entrant, "no-kronos-csv", inputs,
            "kronos-alone-v1: collected/kronos/forecast.csv absent or "
            "unparseable")
    base = fnum((ens or {}).get("base_price"))
    sigma = fnum((ens or {}).get("sigma_daily")) or 0.0
    density = fnum((ens or {}).get("sessions_per_calendar_day")) or (5 / 7)
    horizons = {}
    for hname, bar in HORIZONS.items():
        ens_h = ((ens or {}).get("horizons") or {}).get(hname)
        if not isinstance(ens_h, dict):
            continue
        ka = kronos_at(kronos, base, bar)
        if ka is None:
            continue
        h_eff = ens_h.get("trading_sessions")
        if not isinstance(h_eff, int) or h_eff <= 0:
            h_eff = max(1, round(bar * density))
        vol_h = sigma * math.sqrt(h_eff)
        price_score = (max(-1.0, min(1.0, ka["move"] / (2.0 * vol_h)))
                       if vol_h > 0 else 0.0)
        # Range from the row's OWN high/low (not the ensemble's
        # half-band): the row IS the Kronos forecast for this horizon.
        i = min(bar, len(kronos)) - 1
        _c, _h, _l = kronos[i]
        horizons[hname] = horizon_block(
            ens_h, direction_of(ka["move"]), ka["move"] * 100,
            (_l / base - 1) * 100, (_h / base - 1) * 100,
            None, _r3(price_score),
            {"price-forecast": _r3(price_score)},
            {"confidence_basis": "not defined for kronos-alone v1",
             "range_source": "kronos-row-high-low"})
    if not horizons:
        return absent_file(
            ens, digest, entrant, "no-kronos-csv", inputs,
            "kronos-alone-v1: no ensemble horizon to anchor on")
    derivation = (
        "kronos-alone-v1: kronos_at() row-index mirror (bar rows, "
        "clamped); expected from the row close vs the sweep base; "
        "range from the row's own high/low; confidence not defined "
        "for kronos-alone v1")
    extra = {"kronos_first_row_date": kronos_first_date,
             "kronos_row0_predates_asof":
                 bool(kronos_first_date and (ens or {}).get("date")
                      and kronos_first_date < str((ens or {}).get("date"))[:10]),
             "kronos_rescale": kronos_rescale}
    doc = base_header(ens, digest, entrant, inputs, derivation, extra)
    doc["horizons"] = horizons
    write_json(f"{entrant}.json", doc)
    return "present"


def _last_closes(ticker):
    """Last 10 closes (dates + closes) for the raw-LLM prompt:
    collected/egx-data/egxpy_<code>.csv for EGX tickers, else
    collected/yahooquery/<TICKER>.csv. Returns (rel, sha, table)."""
    code = ticker.split(".")[0].lower()
    if ticker.upper().endswith(".CA"):
        rel = f"collected/egx-data/egxpy_{code}.csv"
    else:
        rel = f"collected/yahooquery/{ticker.upper()}.csv"
    path = os.path.join(CWD, rel)
    if not os.path.exists(path):
        return rel, None, "price history unavailable (file not found)"
    try:
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    except Exception:
        return rel, None, "price history unreadable"
    dcol = next((c for c in (rows[0] if rows else {})
                 if c and ("date" in c.strip().lower()
                          or c.strip().lower() in ("datetime", "index"))),
                None)
    ccol = next((c for c in (rows[0] if rows else {})
                 if c and c.strip().lower() in ("close", "adj close",
                                                "adjclose")), None)
    if not dcol or not ccol:
        return rel, sha256_file(path), "price history has no date/close columns"
    pairs = []
    for r in rows:
        d = str(r.get(dcol) or "")[:10]
        c = fnum(r.get(ccol))
        if re.match(r"^\d{4}-\d{2}-\d{2}$", d) and c:
            pairs.append((d, c))
    pairs = pairs[-10:]
    if not pairs:
        return rel, sha256_file(path), "price history has no dated closes"
    table = "\n".join(f"{d}: {c:g}" for d, c in pairs)
    return rel, sha256_file(path), table


def _build_llm_prompt(ens, digest):
    """Render the frozen prompt v1. Returns (prompt, prompt_sha,
    price_rel, price_sha) or (None, sha, rel, sha) when the prompt
    file itself cannot be read (then the entrant is absent)."""
    try:
        with open(PROMPT_FILE, encoding="utf-8") as f:
            template = f.read()
    except Exception:
        return None, None, None, None
    prompt_sha = sha256_text(template)
    ticker = (ens or {}).get("ticker") or (digest or {}).get("ticker") or ""
    actions = (ens or {}).get("corporate_actions") or []
    if actions:
        acts = "; ".join(
            f"{a.get('type')} DPS {a.get('dps')}"
            + (f", ex-date {a.get('ex_date')}" if a.get("ex_date") else
               ", ex-date unknown")
            for a in actions if isinstance(a, dict))
    else:
        acts = "none"
    price_rel, price_sha, closes = _last_closes(ticker)
    prompt = (template
              .replace("__TICKER__", str(ticker))
              .replace("__AS_OF__", str((ens or {}).get("date")
                                        or (digest or {}).get("date") or ""))
              .replace("__BASE__", str((ens or {}).get("base_price")))
              .replace("__BASE_DATE__", str((ens or {}).get("base_date") or ""))
              .replace("__BASE_SOURCE__", str((ens or {}).get("base_source") or ""))
              .replace("__SIGMA_DAILY__", str((ens or {}).get("sigma_daily")))
              .replace("__SESSIONS_PER_DAY__",
                       str((ens or {}).get("sessions_per_calendar_day")))
              .replace("__CORPORATE_ACTIONS__", acts)
              .replace("__CLOSES__", closes))
    return prompt, prompt_sha, price_rel, price_sha


def call_llm(prompt, api_key, url=None):
    """ONE Cohere call, no retry. Returns (parsed_json, error_reason)
    with error_reason None on success. `url` is an env override for
    the harness stub server only; production always uses the
    default api.cohere.com endpoint."""
    target = url or os.environ.get("COHERE_API_URL") or LLM_URL_DEFAULT
    body = json.dumps({
        "model": LLM_MODEL, "temperature": 0,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"}},
        ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        target, data=body,
        headers={"Authorization": f"Bearer {api_key}",
                 "Content-Type": "application/json",
                 "User-Agent": "borsagator-benchmark-freeze"},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            raw = r.read().decode("utf-8", "replace")
    except Exception as e:
        return None, "llm-call-failed"
    try:
        resp = json.loads(raw)
    except Exception:
        return None, "llm-response-unparseable"
    return _parse_llm_response(resp)


def _parse_llm_response(resp):
    """Strict parse of a Cohere chat response. Any missing key,
    non-numeric value, or direction outside {up, down, flat} ->
    absent / llm-response-unparseable. Pure and testable."""
    try:
        content = (resp.get("message") or {}).get("content")
        text = None
        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            parts = [p.get("text") for p in content
                     if isinstance(p, dict) and isinstance(p.get("text"), str)]
            text = "".join(parts) if parts else None
        if not text:
            return None, "llm-response-unparseable"
        data = json.loads(text)
    except Exception:
        return None, "llm-response-unparseable"
    if not isinstance(data, dict):
        return None, "llm-response-unparseable"
    out = {}
    for h in ("day", "week", "month"):
        hb = data.get(h)
        if not isinstance(hb, dict):
            return None, "llm-response-unparseable"
        direction = hb.get("direction")
        if direction not in DIRECTIONS:
            return None, "llm-response-unparseable"
        vals = {}
        for k in ("expected_move_pct", "range_low_pct", "range_high_pct"):
            v = fnum(hb.get(k))
            if v is None:
                return None, "llm-response-unparseable"
            vals[k] = v
        conf = hb.get("confidence")
        if conf is not None:
            conf = fnum(conf)
            if conf is None or not (0.0 <= conf <= 1.0):
                return None, "llm-response-unparseable"
        out[h] = {"direction": direction, "expected_move_pct": vals["expected_move_pct"],
                  "range_low_pct": vals["range_low_pct"],
                  "range_high_pct": vals["range_high_pct"],
                  "confidence": conf}
    return out, None


def freeze_raw_llm(ens, digest, inputs):
    """Frozen prompt v1, command-r-08-2024, temp 0. Key absent ->
    absent / llm-key-absent. Never a fallback model, never a retry."""
    entrant = "raw-llm-cohere"
    prompt, prompt_sha, price_rel, price_sha = _build_llm_prompt(ens, digest)
    if prompt is None:
        return absent_file(
            ens, digest, entrant, "llm-call-failed", inputs,
            "raw-llm-cohere-v1: frozen prompt file unreadable")
    llm_inputs = dict(inputs)
    llm_inputs["scripts/benchmark_prompt_v1.txt"] = prompt_sha
    if price_sha:
        llm_inputs[price_rel] = price_sha
    api_key = os.environ.get("COHERE_API_KEY") or ""
    if not api_key:
        return absent_file(
            ens, digest, entrant, "llm-key-absent", llm_inputs,
            "raw-llm-cohere-v1: LLM API key absent — no fallback model")
    parsed, err = call_llm(prompt, api_key)
    if err:
        return absent_file(
            ens, digest, entrant, err, llm_inputs,
            "raw-llm-cohere-v1: single call, no retry")
    horizons = {}
    for hname, bar in HORIZONS.items():
        ens_h = ((ens or {}).get("horizons") or {}).get(hname)
        if not isinstance(ens_h, dict):
            continue
        hb = parsed[hname]
        horizons[hname] = horizon_block(
            ens_h, hb["direction"], hb["expected_move_pct"],
            hb["range_low_pct"], hb["range_high_pct"],
            (_r2(hb["confidence"]) if hb["confidence"] is not None else None),
            None, {})
    if not horizons:
        return absent_file(
            ens, digest, entrant, "llm-response-unparseable", llm_inputs,
            "raw-llm-cohere-v1: no ensemble horizon to anchor on")
    derivation = (
        "raw-llm-cohere-v1: frozen prompt v1, model "
        "command-r-08-2024, temperature 0, single call; inputs "
        "ticker/as_of/base/sigma/corporate actions/last 10 closes "
        "only — no family scores, no news, no Kronos path")
    doc = base_header(ens, digest, entrant, llm_inputs, derivation,
                      {"prompt_version": "v1",
                       "prompt_sha256": prompt_sha,
                       "llm_model": LLM_MODEL,
                       "price_series_file": price_rel})
    doc["horizons"] = horizons
    write_json(f"{entrant}.json", doc)
    return "present"


def freeze_buy_and_hold(ens, digest, inputs):
    """Flat 0%, pure ±1.28σ√h_eff range — no risk multiplier, no
    disagreement widening, no confidence."""
    entrant = "buy-and-hold"
    sigma = fnum((ens or {}).get("sigma_daily")) or 0.0
    density = fnum((ens or {}).get("sessions_per_calendar_day")) or (5 / 7)
    horizons = {}
    for hname, bar in HORIZONS.items():
        ens_h = ((ens or {}).get("horizons") or {}).get(hname)
        if not isinstance(ens_h, dict):
            continue
        h_eff = ens_h.get("trading_sessions")
        if not isinstance(h_eff, int) or h_eff <= 0:
            h_eff = max(1, round(bar * density))
        half_pct = 1.28 * sigma * math.sqrt(h_eff) * 100
        horizons[hname] = horizon_block(
            ens_h, "flat", 0.0, -half_pct, half_pct, None, None, {},
            {"confidence_basis": "not defined for buy-and-hold v1"})
    if not horizons:
        return absent_file(
            ens, digest, entrant, "ensemble-no-horizons", inputs,
            "buy-and-hold-v1: no ensemble horizon to anchor on")
    derivation = (
        "buy-and-hold-v1: expected 0.0, direction flat, range "
        "±1.28σ√h_eff (pure 1σ volatility band — no risk multiplier, "
        "no disagreement widening)")
    doc = base_header(ens, digest, entrant, inputs, derivation)
    doc["horizons"] = horizons
    write_json(f"{entrant}.json", doc)
    return "present"


def freeze_all():
    """Returns (present, absent) entrant lists for the digest line."""
    digest = load_json(DIGEST_JSON) or {}
    ens = load_json(ENSEMBLE_JSON)
    inputs = {}
    if os.path.exists(DIGEST_JSON):
        inputs["digest.json"] = sha256_file(DIGEST_JSON)
    present, absent = [], []
    if not isinstance(ens, dict) or not ens.get("base_price"):
        for entrant in ENTRANTS:
            inputs_e = dict(inputs)
            if os.path.exists(ENSEMBLE_JSON):
                inputs_e["ensemble.json"] = sha256_file(ENSEMBLE_JSON)
            absent_file(ens, digest, entrant, "no-ensemble-no-base",
                        inputs_e,
                        "no ensemble.json — no verified base; the freeze "
                        "never invents a base from a CSV")
            absent.append((entrant, "no-ensemble-no-base"))
        return present, absent
    if os.path.exists(ENSEMBLE_JSON):
        inputs["ensemble.json"] = sha256_file(ENSEMBLE_JSON)
    if not isinstance(ens.get("horizons"), dict) or not ens["horizons"]:
        for entrant in ENTRANTS:
            absent_file(ens, digest, entrant, "ensemble-no-horizons",
                        dict(inputs),
                        "ensemble.json carries no horizons")
            absent.append((entrant, "ensemble-no-horizons"))
        return present, absent
    kronos, kronos_first_date, kronos_note = read_kronos_csv(digest)
    kronos_inputs = dict(inputs)
    kronos_rescale = "unknown"
    if kronos is not None:
        kronos_inputs["collected/kronos/forecast.csv"] = sha256_file(KRONOS_CSV)
        kronos, kronos_rescale = rescale_kronos(kronos, ens)
    for fam in FAMILIES:
        entrant = f"family-{fam}"
        status = freeze_family_alone(
            ens, digest, fam, kronos, kronos_first_date, kronos_rescale,
            dict(kronos_inputs) if fam == "price-forecast" else dict(inputs))
        if status == "present":
            present.append((entrant, ""))
        else:
            absent.append((entrant, status))
    status = freeze_kronos_alone(
        ens, digest, kronos, kronos_first_date, kronos_rescale,
        dict(kronos_inputs))
    if status == "present":
        present.append(("kronos-alone", ""))
    else:
        absent.append(("kronos-alone", status))
    status = freeze_raw_llm(ens, digest, dict(inputs))
    if status == "present":
        present.append(("raw-llm-cohere", ""))
    else:
        absent.append(("raw-llm-cohere", status))
    status = freeze_buy_and_hold(ens, digest, dict(inputs))
    if status == "present":
        present.append(("buy-and-hold", ""))
    else:
        absent.append(("buy-and-hold", status))
    return present, absent


def append_digest_section(present, absent):
    """Short benchmark section in digest.md, mirroring the
    ensemble's digest append. Best-effort; never raises."""
    try:
        if not os.path.exists(DIGEST_MD):
            return
        lines = ["", "---", "", "## 📊 Benchmark freeze (v1)", ""]
        if present:
            lines.append("Frozen entrants: " + ", ".join(
                e for e, _ in present) + ".")
        if absent:
            lines.append("Absent entrants: " + "; ".join(
                f"{e} ({r})" for e, r in absent) + ".")
        if not present and not absent:
            lines.append("No entrants frozen.")
        lines.append("")
        lines.append("Frozen files live under `benchmark/` in this "
                     "sweep dir; the calibration ledger scores them "
                     "in a separate benchmark table (issue #79).")
        lines.append("")
        with open(DIGEST_MD, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    except Exception:
        pass


def main():
    try:
        present, absent = freeze_all()
        append_digest_section(present, absent)
        print(f"benchmark freeze: {len(present)} present, "
              f"{len(absent)} absent")
        for e, r in absent:
            print(f"  absent: {e} ({r})")
    except Exception as e:
        print(f"benchmark freeze failed (non-fatal): {e}")
        try:
            os.makedirs(BENCH_DIR, exist_ok=True)
            with open(os.path.join(BENCH_DIR, "freeze_error.txt"),
                      "w", encoding="utf-8") as f:
                f.write(f"benchmark freeze failed: {type(e).__name__}: {e}\n")
            if os.path.exists(DIGEST_MD):
                with open(DIGEST_MD, "a", encoding="utf-8") as f:
                    f.write("\n⚠️ **Benchmark freeze failed** — see "
                            "benchmark/freeze_error.txt; this sweep "
                            "carries no frozen entrants.\n")
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
