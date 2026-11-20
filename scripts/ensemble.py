#!/usr/bin/env python3
"""Borsagator ensemble synthesizer (v2).

Runs inside the Borsagator workflow right after orchestrate.py. Reads
digest/digest.json + the harvested per-tool results in collected/ and
produces ONE forecast per horizon (day / week / month).

Design (v2 — root fixes over v1):
- Tools vote by FAMILY (registry family+role), never per tool.
- Sentiment inputs are LIVE per-ticker headlines: the FinBERT trio
  fetches the day's coverage itself (fetch_headlines.py in each
  sentiment repo) — no stored samples anywhere in the chain.
- Ranges are anchored in the stock's OWN realized volatility
  (sigma = max of 60-session and 10-session daily-return stdev, from
  the price history the fleet already collects), not in the forecast
  model's self-reported bands — so intervals widen by themselves on
  shock days, because the shock is inside the recent returns.
- The price family's score is the Kronos move measured in units of
  that volatility (z-score), not an arbitrary multiplier — a +5% path
  means something different on a calm stock than on a crashing one.
- The news layer never votes direction; it is a risk overlay that
  caps confidence, discounts the price weight and stretches ranges.
- Confidence is PROVISIONAL (uncalibrated) until the scoring ledger
  (phase 2) has measured this ensemble's own history.

Deterministic, stdlib only, no LLM. Never raises.
"""
import csv, glob, json, math, os, re, sys, tempfile
from datetime import datetime, timezone, date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DIGEST = os.path.join(os.getcwd(), "digest", "digest.json")
COLLECTED = os.path.join(os.getcwd(), "collected")
REGISTRY = os.path.join(ROOT, "registry", "tools.json")
OUT_JSON = os.path.join(os.getcwd(), "digest", "ensemble.json")
OUT_MD = os.path.join(os.getcwd(), "digest", "digest.md")

HORIZONS = {"day": 1, "week": 5, "month": 21}
W = {
    "price-forecast": {"day": .45, "week": .40, "month": .30},
    "technicals":     {"day": .30, "week": .20, "month": .10},
    "sentiment":      {"day": .15, "week": .15, "month": .05},
    "agent":          {"day": .10, "week": .20, "month": .30},
    "fundamentals":   {"day": .00, "week": .00, "month": .25},
}


def expected_move(kmove, net_score, vol_h):
    """The combine's expected move (issue #436): the Kronos path
    move carries 60%, the family net score 40% scaled by the
    1.28-sigma horizon band. Extracted verbatim from main() so the
    walk-forward backtest can build family-alone entrants with the
    same rule instead of a second one; the horizon loop below calls
    this function, it does not duplicate the formula."""
    return .6 * kmove + .4 * net_score * (1.28 * vol_h)


def two_family_backtest():
    """Issue #436: the walk-forward harness runs the ensemble in a
    2-family mode (price-forecast + technicals only) by setting
    BORSAGATOR_BACKTEST_TWO_FAMILY=1 on the ensemble subprocess.
    Sentiment/news and agents cannot be backtested (no historical
    headline archive; LLM training leaks the future) and
    fundamentals have no verified point-in-time vintages, so those
    families are forced to not vote and the news risk overlay is
    disabled. Unset in every live sweep — the env var is the only
    switch, and the harness sets it only for backtest cells."""
    return bool(os.environ.get("BORSAGATOR_BACKTEST_TWO_FAMILY"))

# Registry categories whose CSVs are REFERENCE workloads, never this
# ticker's price series (issue #133): backtest tools run reference
# backtests (vectorbt's poul_ohlc.csv ends at 3.13) and stats tools
# (quantstats) emit reference analytics ending at 2.83, while every
# price-bearing tool agrees on ~10.2. The registry holds no
# further reference-workload category — do not invent one.
EXCLUDED_PRICE_CATEGORIES = ("backtest", "stats")

def _digest_header(digest):
    job = (digest or {}).get("job") or ""
    return (f"# 🐊 Borsagator digest — {job}"
            if job else "# 🐊 Borsagator digest")


def _ensure_digest_header(digest):
    """Issue #113: the ensemble appends to digest.md with mode 'a',
    which CREATES a headerless file when the gator died before writing
    it — and the issue step titles from that file's first line, so an
    empty first line killed the digest issue (run 43815097317).
    Ensure the '# 🐊' header line is present first: prepend it when
    absent, create the file headed when missing.
    Issue #120: the prepend is a temp file + atomic rename in the
    same directory — the old read + rewrite-in-place could leave a
    torn digest if the process died mid-rewrite."""
    header = _digest_header(digest)
    existing = ""
    if os.path.exists(OUT_MD):
        with open(OUT_MD, encoding="utf-8") as f:
            existing = f.read()
    if any(line.startswith("# 🐊") for line in existing.splitlines()):
        return
    directory = os.path.dirname(OUT_MD) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".digest-header-",
                               suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            if existing:
                f.write(header + "\n" + existing)
            else:
                f.write(header + "\n")
        os.replace(tmp, OUT_MD)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


# Issue #120: set immediately after this run writes ensemble.json.
# The __main__ handler deletes the file only when this run wrote it —
# a stale file from an earlier run is never this run's to remove.
_ENSEMBLE_JSON_WRITTEN = False


def _fmt_factor(v):
    """Issue #120: a None factor renders as "—", never raises
    TypeError on :g formatting in the digest-section build (as the
    family-scores line already does)."""
    return f"{v:g}" if v is not None else "—"


def _note_digest_warning(line):
    """Issue #120: an early return must leave a ⚠️ line in the digest
    like the exception handler does — silently returning with exit 0
    used to leave nothing at all. Best-effort: never raises."""
    try:
        os.makedirs(os.path.dirname(OUT_MD) or ".", exist_ok=True)
        _ensure_digest_header(load_json(DIGEST))
        with open(OUT_MD, "a", encoding="utf-8") as f:
            f.write("\n" + line + "\n")
    except Exception:
        pass


def _apply_measured_weights(base):
    """Issue #28: measured-weights feedback. If the calibration
    ledger has published family skill factors (ledger/weights.json
    in the repo checkout, or $BORSAGATOR_WEIGHTS), scale the
    hand-set base weights by them. The ledger bounds the factors to
    [0.5, 1.5] and enforces a minimum sample, so this side only
    multiplies. Absent or unreadable file = base weights, exactly
    the pre-#28 behaviour.
    Defense in depth (INS-R5-08): a factor is used only when it is
    a finite number in [0.5, 1.5] for a known family with n >= 3
    measured samples — a malformed or externally supplied file can
    never smuggle a NaN, negative, or out-of-range factor in.
    A document with no eligible factor at all reports 'builtin'
    (INS-R5-09): the committed weights.json at first publication
    carries n=0 everywhere, and that must not be labelled
    calibrated.
    Issue #93: also return an audit record of the factors ACTUALLY
    applied (every family, 1.0 where no eligible factor entered)
    plus the provenance of the weights document (path + sha256 of
    the exact bytes read), so a verifier can reconcile the merge
    against the committed ledger/weights.json.
    Issue #436: in 2-family backtest mode the measured-weights
    feedback is forbidden outright — the ledger's factors are
    measured on 2026 sweeps, i.e. from the future relative to any
    historical cutoff. The backtest always runs on the hand-set
    base weights, recorded as source 'base-v1'."""
    if two_family_backtest():
        return base, "base-v1", {
            "source": "base-v1", "file": None, "file_sha256": None,
            "factors": {fam: 1.0 for fam in base}, "eligible": {}}
    import hashlib
    path = os.environ.get("BORSAGATOR_WEIGHTS", "ledger/weights.json")
    info = {"source": "builtin", "file": path, "file_sha256": None,
            "factors": {fam: 1.0 for fam in base}, "eligible": {}}
    try:
        with open(path, "rb") as f:
            raw = f.read()
        info["file_sha256"] = hashlib.sha256(raw).hexdigest()
        doc = json.loads(raw.decode("utf-8"))
        factors = {}
        for k, v in (doc.get("factors") or {}).items():
            if k not in base:
                continue
            try:
                fv = float(v["factor"])
                n = int(v.get("n", 0))
            except Exception:
                continue
            if not math.isfinite(fv) or not (0.5 <= fv <= 1.5) or n < 3:
                print(f"weights: ignoring ineligible factor for {k}: "
                      f"factor={v.get('factor')} n={v.get('n')}")
                continue
            factors[k] = fv
            info["eligible"][k] = {"factor": fv, "n": n,
                                   "skill": v.get("skill")}
        if not factors:
            return base, "builtin", info
    except Exception:
        return base, "builtin", info
    info["source"] = "ledger"
    info["factors"] = {fam: factors.get(fam, 1.0) for fam in base}
    out = {fam: {h: round(w * factors.get(fam, 1.0), 4)
                 for h, w in hs.items()}
           for fam, hs in base.items()}
    return out, "ledger", info


W, WEIGHTS_SOURCE, WEIGHTS_INFO = _apply_measured_weights(W)
RISK_MULT = {"none": 1.0, "elevated": 1.2, "shock": 1.5, "unknown": 1.3}
SHOCK_WORDS = [
    "resign", "oust", "ceo", "earnings", "guidance", "investigat", "fraud",
    "halt", "merger", "acquisition", "dividend", "profit warning",
    "bankrupt", "lawsuit", "استقال", "إقال", "نتائج", "أرباح", "توزيع",
    "اندماج", "تحقيق", "إيقاف", "مجلس الإدارة", "جمعية عامة",
]
# Event taxonomy for the risk overlay (v2.1): a shock is an EVENT of a
# severe type, or a price move the event stream cannot explain — not a
# bag of keywords. Severity: high = shock-capable on its own; medium =
# elevated, or shock when the price confirms it.
EVENT_TYPES = [
    ("earnings", "high",
     ["earnings", "profit", "loss", "revenue", "results", "quarterly",
      "أرباح", "خسائر", "نتائج", "إيرادات", "صافي الربح", "نتائج الأعمال"]),
    ("management", "high",
     ["resign", "oust", "appoint", "ceo", "chief executive",
      "استقال", "إقال", "تعيين", "رئيس تنفيذي", "عضو منتدب"]),
    ("legal", "high",
     ["investigat", "lawsuit", "fine", "fraud", "bankrupt", "halt",
      "تحقيق", "غرامة", "احتيال", "قضية", "إفلاس", "إيقاف التداول"]),
    ("capital", "high",
     ["merger", "acquisition", "capital increase", "share split",
      "اندماج", "استحواذ", "زيادة رأس المال", "تجزئة"]),
    ("dividend", "medium",
     ["dividend", "distribution", "coupon", "توزيع", "كوبون"]),
    ("governance", "medium",
     ["board of directors", "general assembly", "agm", "egm",
      "مجلس الإدارة", "جمعية عامة", "جمعية عمومية"]),
]
RATING_MAP = {"strong buy": 1.0, "buy": .75, "overweight": .5, "hold": 0.0,
              "underweight": -.5, "sell": -.75, "strong sell": -1.0}


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


def find_key(obj, needles, depth=0):
    if depth > 4 or not isinstance(obj, dict):
        return None
    for k, v in obj.items():
        if any(n in k.lower() for n in needles):
            n = fnum(v)
            if n is not None:
                return n
    for v in obj.values():
        if isinstance(v, dict):
            r = find_key(v, needles, depth + 1)
            if r is not None:
                return r
    return None


def realized_sigma(ticker, base=None, ok=None):
    """Daily-return stdev from collected price CSVs.
    Returns (sigma, source, density): sigma = max(sigma_60, sigma_10);
    density = trading sessions per calendar day in that series — Kronos
    emits calendar-day bars, so horizon maths must convert.
    Series choice is ANCHORED on the verified base close when known:
    among candidates whose last close sits within 25% of base, take the
    longest (a stray foreign series must not set the volatility); with
    no anchor available, fall back to the DEFAULT sigma — a stale
    unanchored series must not set the volatility. Without a base
    to anchor on, the longest candidate is still used.
    `ok` (issue #147) is an optional tool -> bool predicate from the
    digest (status == "ok"): when given, a failed tool's CSVs never
    enter the sigma pool, even if they are sitting in collected/."""
    code = re.sub(r"[^a-z0-9]", "", ticker.split(".")[0].lower())
    best = None
    anchored = None
    _reg = load_json(REGISTRY) or {}
    _cats = {t.get("id"): t.get("category") for t in _reg.get("tools", [])}
    # Issue #67: sorted globs — glob order follows filesystem
    # scandir order, which varies by directory creation order, so
    # an unsorted glob makes ensemble.json's dict key order (and
    # hence its bytes) vary between two runs on identical inputs.
    # Sorting makes the output deterministic: the worker merge's
    # byte-parity bar depends on it, and Actions runs gain it too.
    # Selections here are max/longest-based, so order changes no
    # value — only the serialization order.
    for path in sorted(glob.glob(os.path.join(COLLECTED, "*", "*.csv"))):
        name = os.path.basename(path).lower()
        # Same exclusion as price_series (issue #133): backtest/stats
        # tools run reference workloads — their CSVs never enter
        # the sigma pool.
        # Issue #147: a failed tool's CSVs never enter the pool
        # either (its digest status is not "ok").
        if ok is not None and not ok(os.path.basename(
                os.path.dirname(path))):
            continue
        if _cats.get(os.path.basename(os.path.dirname(path))) in (
                EXCLUDED_PRICE_CATEGORIES):
            continue
        if not any(s in name for s in ("ohlc", "indicators", code)):
            continue
        try:
            with open(path, newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
        except Exception:
            continue
        if len(rows) < 30:
            continue
        col = next((c for c in rows[0] if c and c.strip().lower() in
                    ("close", "adj close", "adjclose")), None)
        if not col:
            continue
        closes = [fnum(r.get(col)) for r in rows]
        dates = []
        dcol = next((c for c in rows[0] if c and ("date" in c.strip().lower()
                     or c.strip().lower() in ("datetime", "index"))), None)
        if dcol:
            for r in rows:
                s = str(r.get(dcol) or "")[:10]
                try:
                    dates.append(datetime.strptime(s, "%Y-%m-%d"))
                except Exception:
                    dates.append(None)
        pairs = [(c, d) for c, d in zip(closes, dates or [None] * len(closes))
                 if c and c > 0]
        closes = [c for c, _ in pairs]
        if len(closes) < 30:
            continue
        cand = (closes, [d for _, d in pairs],
                os.path.basename(os.path.dirname(path)) + "/" + name)
        if best is None or len(closes) > len(best[0]):
            best = cand
        if base and abs(closes[-1] - base) / base <= 0.25:
            if anchored is None or len(closes) > len(anchored[0]):
                anchored = cand
    if anchored is not None:
        best = anchored
    if not best:
        return 0.02, "default (no history found)", 5 / 7
    if base and anchored is None:
        # No candidate anchored on the verified base close: the
        # longest series may be a stale reference (a dead series
        # ending far below the live price), so it must not set the
        # volatility — fall back to the default sigma instead.
        print(f"ensemble: no series anchored within 25% of base {base} "
              f"— longest candidate ends at {best[0][-1]} "
              f"({best[2]}); using default sigma")
        return 0.02, "default (no series anchored within 25% of base)", 5 / 7
    closes, dates, src = best
    density = 5 / 7
    ds = [d for d in dates if d]
    if len(ds) >= 30 and (ds[-1] - ds[0]).days > 0:
        density = min(1.0, max(0.4, (len(ds) - 1) / (ds[-1] - ds[0]).days))

    def sd(vals):
        rets = [math.log(vals[i] / vals[i - 1]) for i in range(1, len(vals))]
        if len(rets) < 5:
            return 0.0
        mu = sum(rets) / len(rets)
        return math.sqrt(sum((r - mu) ** 2 for r in rets) / len(rets))

    s60 = sd(closes[-61:])
    s10 = sd(closes[-11:])
    return max(s60, s10), f"{src} (σ60={s60:.4f}, σ10={s10:.4f})", density


def price_series(ticker, ok=None):
    """Collected price series for the ticker as {source: {date: close}}
    (date '' when the CSV has no usable date column). Backtest and
    stats tools are excluded by registry category: they run
    REFERENCE workloads (their CSVs are not this ticker's series —
    vectorbt's poul_ohlc.csv ends at 3.13, quantstats' at 2.83, while
    every price-bearing tool agrees on ~10.2).
    `ok` (issue #147) is an optional tool -> bool predicate from the
    digest (status == "ok"): when given, a failed tool's CSVs are
    excluded from voting/base selection, even if they are sitting in
    collected/ (a stale carry-over from an earlier run)."""
    code = re.sub(r"[^a-z0-9]", "", ticker.split(".")[0].lower())
    registry = load_json(REGISTRY) or {}
    cats = {t.get("id"): t.get("category")
            for t in registry.get("tools", [])}
    series = {}
    # Issue #67: sorted glob — see realized_sigma above. The
    # witnesses dict in price_crosscheck inherits this order, so an
    # unsorted glob makes ensemble.json bytes vary run to run.
    for path in sorted(glob.glob(os.path.join(COLLECTED, "*", "*.csv"))):
        tool = os.path.basename(os.path.dirname(path))
        # Issue #147: exclude a failed tool's files from base
        # selection and crosscheck witnesses.
        if ok is not None and not ok(tool):
            continue
        if cats.get(tool) in EXCLUDED_PRICE_CATEGORIES:
            continue
        name = os.path.basename(path).lower()
        if not any(s in name for s in ("ohlc", "indicators", code)):
            continue
        try:
            with open(path, newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
        except Exception:
            continue
        if len(rows) < 5:
            continue
        col = next((c for c in rows[0] if c and c.strip().lower() in
                    ("close", "adj close", "adjclose")), None)
        if not col:
            continue
        dcol = next((c for c in rows[0] if c and ("date" in c.strip().lower()
                     or c.strip().lower() in ("datetime", "index"))), None)
        out = {}
        for r in rows:
            c = fnum(r.get(col))
            if not c:
                continue
            d = ""
            if dcol:
                s = str(r.get(dcol) or "")[:10]
                try:
                    datetime.strptime(s, "%Y-%m-%d")
                    d = s
                except Exception:
                    d = ""
            out[d or f"row{len(out)}"] = c
        if out:
            src = os.path.basename(os.path.dirname(path)) + "/" + name
            series[src] = out
    return series


def _series_last(m):
    """(last_date, close) among a series' dated entries, else
    (None, None). Undated 'rowN' keys never count."""
    dated = sorted(d for d in m if len(d) == 10 and d[4] == "-")
    if not dated:
        return None, None
    return dated[-1], m[dated[-1]]


def freshest_close(series):
    """The freshest close across the collected series (issue #94):
    the series whose last dated close is newest wins; on a date tie
    the EGX-native series (egx-data) wins, then source name so the
    choice is deterministic. Returns {value, source, date} or None
    when no series carries dates."""
    cands = []
    for src, m in series.items():
        d, c = _series_last(m)
        if d is not None and c:
            cands.append((d, src.startswith("egx-data/"), src, c))
    if not cands:
        return None
    cands.sort(key=lambda t: t[2])
    cands.sort(key=lambda t: (t[0], t[1]), reverse=True)
    d, _, src, c = cands[0]
    return {"value": c, "source": src, "date": d}


def price_crosscheck(ticker, base, base_src, series, base_date=None):
    """Two-source verification of the price the forecast stands on
    (audit item: Yahoo was the single artery, with corrupted segments).
    Witnesses: the base from the digest metrics + the last close of
    every collected price series, aligned on the latest date at least
    two dated series share. A spread above 2% means the sources
    disagree: the ensemble then stands on the EGX-native series
    (egx-data) when present, else the median witness, and the digest
    says so out loud.
    Issue #94: the check is date-aware. It records base_date, the
    latest collected date across all series, and base_stale — set
    when the base's date trails the freshest collected close, the
    exact failure the old check blessed (a 15 Nov ensemble standing
    on an 11 Nov-aligned 'agree'). When the base IS a collected
    series' own close it needs no separate metrics witness."""
    dated_all = {s: _series_last(m)[0] for s, m in series.items()}
    latest_date = max((d for d in dated_all.values() if d), default=None)
    info = {"base_date": base_date, "latest_collected_date": latest_date,
            "base_stale": bool(base_date and latest_date
                               and base_date < latest_date)}
    base_is_series = base_src in series
    witnesses = {}
    if base and not base_is_series:
        witnesses[f"metrics:{base_src}"] = base
    dated = {s: m for s, m in series.items()
             if any(len(k) == 10 and k[4] == "-" for k in m)}
    common = None
    if len(dated) >= 2:
        sets = [set(m.keys()) for m in dated.values()]
        inter = set.intersection(*sets) if sets else set()
        real = sorted(d for d in inter if len(d) == 10 and d[4] == "-")
        common = real[-1] if real else None
    for src, m in series.items():
        if common and common in m:
            witnesses[src] = m[common]
        else:
            # Issue #135: dated-only witness. The old
            # m[sorted(m.keys())[-1]] let an undated 'rowN' key win
            # over a real date ('r' > '2'), so the witness could be
            # an arbitrary mid-series close. Reuse _series_last's
            # dated-only rule; only a series with no dated entries
            # at all falls back to its last row key.
            d, c = _series_last(m)
            witnesses[src] = c if d is not None else m[sorted(m.keys())[-1]]
    # Deduplicate by TOOL: a tool's own collected series supersedes its
    # digest metric — the same underlying data must not vote twice
    # (Ins review, issue #49).
    series_tools = {src.split("/")[0] for src in witnesses if "/" in src}
    witnesses = {k: v for k, v in witnesses.items()
                 if not (k.startswith("metrics:")
                         and k.split(":", 1)[1] in series_tools)}
    vals = sorted(witnesses.values())
    if len(vals) < 2:
        return {"status": "single-source", "witnesses": witnesses,
                "spread_pct": None, "common_date": common,
                "base_used": base, "base_source_used": base_src, **info}
    # Cluster the witnesses (2% chaining): the largest cluster is the
    # consensus. A lone outlier series must not veto four agreeing
    # sources — and the base standing OUTSIDE the consensus is exactly
    # the failure this check exists to catch.
    ordered = sorted(witnesses.items(), key=lambda kv: kv[1])
    clusters = [[ordered[0]]]
    for item in ordered[1:]:
        if item[1] <= clusters[-1][-1][1] * 1.02:
            clusters[-1].append(item)
        else:
            clusters.append([item])
    consensus = max(clusters, key=len)
    cons = dict(consensus)
    outliers = {s: v for s, v in witnesses.items() if s not in cons}
    cvals = sorted(cons.values())
    spread = (cvals[-1] - cvals[0]) / cvals[len(cvals) // 2] \
        if cvals[len(cvals) // 2] else 0.0
    base_key = f"metrics:{base_src}"
    base_in_cons = (base_key in cons or base_src in cons
                    or any(s.split("/")[0] == base_src.split("/")[0]
                           for s in cons))
    if base_in_cons and len(consensus) >= 2:
        return {"status": "agree", "witnesses": witnesses,
                "outliers": outliers,
                "spread_pct": round(spread * 100, 2), "common_date": common,
                "base_used": base, "base_source_used": base_src, **info}
    egx = next((s for s in cons if s.startswith("egx-data/")), None)
    if egx:
        chosen, chosen_src = cons[egx], egx
    else:
        chosen = cvals[len(cvals) // 2]
        chosen_src = "consensus median"
    gap = abs(base - chosen) / chosen if chosen else 0.0
    return {"status": "disagree", "witnesses": witnesses,
            "outliers": outliers,
            "spread_pct": round(gap * 100, 2), "common_date": common,
            "base_used": chosen, "base_source_used": chosen_src, **info}


_AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
_MONTHS = {"يناير": 1, "فبراير": 2, "مارس": 3, "أبريل": 4, "ابريل": 4,
           "مايو": 5, "يونيو": 6, "يوليو": 7, "أغسطس": 8, "اغسطس": 8,
           "سبتمبر": 9, "أكتوبر": 10, "اكتوبر": 10, "نوفمبر": 11,
           "ديسمبر": 12, "january": 1, "february": 2, "march": 3,
           "april": 4, "may": 5, "june": 6, "july": 7, "august": 8,
           "september": 9, "october": 10, "november": 11, "december": 12}
_DIV_WORDS = ("كوبون", "توزيع", "dividend", "coupon")


def _norm_digits(s):
    return str(s).translate(_AR_DIGITS)


def _find_dates(text, default_year):
    """All (date, start, end) triples in a text: numeric d/m/Y,
    '15 نوفمبر 2026', '15 November 2026', 'November 15, 2026'.
    Positions are character offsets into the digit-normalised text,
    so callers can measure the distance between a date and a wording
    mention (issue #129: the entitlement wording need not sit next
    to the date)."""
    t = _norm_digits(text)
    found = []
    for m in re.finditer(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})", t):
        try:
            found.append((date(int(m.group(3)), int(m.group(2)),
                               int(m.group(1))),
                          m.start(), m.end()))
        except ValueError:
            pass
    low = t.lower()
    for name, mon in _MONTHS.items():
        for m in re.finditer(r"(\d{1,2})\s+" + re.escape(name) +
                             r"(?:\s+(\d{4}))?", low):
            try:
                found.append((date(int(m.group(2) or default_year), mon,
                                   int(m.group(1))),
                              m.start(), m.end()))
            except ValueError:
                pass
        for m in re.finditer(re.escape(name) +
                             r"\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})", low):
            try:
                found.append((date(int(m.group(2)), mon, int(m.group(1))),
                              m.start(), m.end()))
            except ValueError:
                pass
    return found


def _dps_same(a, b):
    """Issue #131: two reports of one coupon differ in the last
    digits (1.89 vs 1.9 vs 1.8999999998 for coupon 42) — exact-float
    dedup treats them as three distributions. They are the same
    coupon when they agree within reporting noise: truncation to 2dp
    loses < 0.01 and 1dp rounding < 0.05, so tolerate the larger of
    0.02 absolute and 1% relative. This subsumes dedup on
    (round(dps, 2), ex_date) and also merges the adjacent-bucket
    case (1.89 vs 1.90) that 2dp rounding alone cannot."""
    try:
        a, b = float(a), float(b)
    except Exception:
        return False
    return abs(a - b) <= max(0.02, 0.01 * max(abs(a), abs(b)))


def _same_distribution(a_dps, a_ex, b_dps, b_ex):
    """One coupon reported twice: DPS within reporting noise and the
    ex-dates agree — or either side is undated (an undated press
    mention of ~the same amount is the same distribution). Two dated
    actions with different ex-dates are different events, however
    close their DPS."""
    if a_ex is not None and b_ex is not None and a_ex != b_ex:
        return False
    return _dps_same(a_dps, b_dps)


def events_to_corporate_actions(events, ticker, base):
    """Issue #281: verified #109 disclosure events -> #26 actions.

    The event record carries the dividend facts as structured fields,
    so nothing here re-parses prose: DPS, ex-date and entitlement-end
    are read verbatim. Gate (precision beats recall, as in #26): only
    ``event_type == "dividend"`` with ``verification_status ==
    "verified"`` and ``extraction_status == "extracted"`` feed
    scoring — a candidate is never a verified event, and an
    unverified (e.g. republication) extraction is not trusted to move
    the score. The issuer ticker must match the sweep ticker when the
    event names one (the feed file is already per-ticker, so a
    missing ticker is accepted, a mismatched one is not). The DPS
    guard is the same as the legacy path (0 < dps < base, EGP only).
    The ex-date is VERBATIM (``verbatim:تاريخ تحريك الحدود
    السعرية``) — the legacy path derives it as entitlement-end + 1,
    which agrees for coupon 42 but is a derivation, not a fact.
    Deliberately NOT fed: ``record_date`` (the extractor never states
    one — its T+2 value is an unvalidated candidate, never a fact)
    and ``payout_date`` (a payout date is NOT an ex-date, #26).
    Output shape is the ``detect_corporate_actions`` action dict plus
    provenance (``source``, ``event_id``, ``announced``,
    ``coupon_number``), so the horizon marking, the Kronos ex-date
    rescale (#130) and the model tripwire consume event actions
    exactly like legacy ones."""
    actions = []
    if not events or not base or base <= 0:
        return actions
    code = (ticker or "").upper()
    for ev in events:
        if not isinstance(ev, dict):
            continue
        if ev.get("event_type") != "dividend":
            continue
        if ev.get("verification_status") != "verified":
            continue
        if ev.get("extraction_status") != "extracted":
            continue
        issuer = ev.get("issuer") or {}
        ev_ticker = (issuer.get("ticker") or "").upper()
        if ev_ticker and ev_ticker != code:
            continue
        payload = ev.get("payload") or {}
        amt = payload.get("amount_per_share") or {}
        if (amt.get("currency") or "EGP") != "EGP":
            continue
        try:
            dps = float(amt.get("value"))
        except (TypeError, ValueError):
            continue
        if not (0 < dps < base):
            continue
        ex_raw = (payload.get("ex_date") or {}).get("value")
        try:
            ex_date = date.fromisoformat(str(ex_raw)[:10]) \
                if ex_raw else None
        except ValueError:
            ex_date = None
        if ex_date is None:
            continue
        ent_raw = (payload.get("entitlement_end") or {}).get("value")
        try:
            ent_date = date.fromisoformat(str(ent_raw)[:10]) \
                if ent_raw else None
        except ValueError:
            ent_date = None
        announced = (ev.get("announced") or {}).get("value")
        title = (ev.get("summary_en") or ev.get("summary_ar") or "")[:90]
        actions.append({
            "type": "dividend", "dps": dps,
            "ex_date": ex_date.isoformat(),
            "entitlement_end": (ent_date.isoformat()
                                if ent_date else None),
            "date_basis": "verbatim:ex-date",
            "mechanical_pct": round(-dps / base * 100, 2),
            "title": title,
            "source": "disclosure-event",
            "event_id": ev.get("event_id"),
            "verification_status": "verified",
            "announced": announced,
            "coupon_number": payload.get("coupon_number")})
    return actions


def merge_corporate_actions(legacy, event_actions):
    """Issue #281: merge legacy text-detected actions with
    event-sourced ones. An event action SUPERSEDES a legacy action
    for the same distribution — same DPS within the #131 tolerance
    and the ex-dates agree (or the legacy one is undated), per
    ``_same_distribution`` — or the legacy ex-date was DERIVED
    (``date_basis == "entitlement+1"``) and sits within one day of
    the verbatim ex-date, i.e. the verbatim date corrects the
    derivation. Anything else survives alongside: two genuinely
    different coupons (same DPS, different ex-dates) stay two
    actions, and non-dividend legacy entries are never touched.
    Deterministic: legacy order is kept, event actions append in
    event order."""
    merged = list(legacy or [])
    for ea in event_actions or []:
        keep = []
        for a in merged:
            if a.get("type") != "dividend":
                keep.append(a)
                continue
            same = _same_distribution(a.get("dps"), a.get("ex_date"),
                                      ea["dps"], ea["ex_date"])
            if not same and a.get("date_basis") == "entitlement+1":
                try:
                    a_ex = date.fromisoformat(a["ex_date"]) \
                        if a.get("ex_date") else None
                    e_ex = date.fromisoformat(ea["ex_date"])
                    if (a_ex is not None
                            and _dps_same(a.get("dps"), ea["dps"])
                            and abs((a_ex - e_ex).days) <= 1):
                        same = True
                except (ValueError, TypeError):
                    pass
            if not same:
                keep.append(a)
        merged = keep
        merged.append(ea)
    return merged


def detect_corporate_actions(items, base, default_year):
    """Dividend announcements in the collected items. Conservative by
    design: an amount is only trusted next to dividend wording, an
    ex-date only next to entitlement/ex wording (a payout date is NOT
    an ex-date). Issue #129: the entitlement-end date is carried on
    the action (`entitlement_end`, ex-date = +1 day) and derived by
    nearest-mention distance, not only by adjacency — press wording
    can put «نهاية الحق» far from the date and name the payout date
    in the same item. A miss records nothing — scoring-time
    re-detection on the archived items remains possible; a false
    positive would poison the ledger, so precision beats recall
    here."""
    actions = []
    for it in items:
        text = (str(it.get("title") or "") + " "
                + str(it.get("body") or "")[:1500])
        low = _norm_digits(text).lower()
        if not any(w in low for w in _DIV_WORDS):
            continue
        dps = None
        for pat in (r"بواقع\s*(\d+(?:\.\d+)?)",
                    r"(\d+(?:\.\d+)?)\s*(?:جنيه|جنيها|egp)\s*(?:للسهم|/share|per share)?",
                    r"(?:dividend|coupon)\s*(?:of\s*)?(?:egp\s*)?(\d+(?:\.\d+)?)"):
            m = re.search(pat, low)
            if m:
                dps = float(m.group(1))
                break
        if dps is None or base <= 0 or not (0 < dps < base):
            continue
        ex_date, basis, entitlement_end = None, None, None
        item_year = None
        try:
            item_year = int(str(it.get("date") or "")[:4]) or None
        except Exception:
            item_year = None
        dates = _find_dates(text, item_year or default_year)
        # Issue #129: the entitlement-end date is carried into the
        # action (as `entitlement_end`, ex-date = +1 day) so it can
        # be derived even when the date is not adjacent to the
        # entitlement wording. The old 40-chars-before window missed
        # the real 15 Nov press item, where «نهاية الحق» sits ~65
        # chars before the date and a payout date («صرفه يوم 18
        # نوفمبر») vetoed the item-level fallback. A date counts as
        # an entitlement end when an entitlement mention precedes it
        # with no other parsed date in between (so the payout date
        # and the later price-limit-move date in the EGX disclosure
        # are never misread as the entitlement end) and within 200
        # chars; an explicit ex-date mention wins for the same date.
        ent_mentions = [m.start() for w in
                        ("نهاية الحق", "استحقاق", "entitlement")
                        for m in re.finditer(re.escape(w), low)]
        ex_mentions = [m.start() for w in
                       ("ex-", "ex date", "خارج")
                       for m in re.finditer(re.escape(w), low)]

        def _mention_before(mentions, date_start):
            best = None
            for mp in mentions:
                if mp >= date_start or date_start - mp > 200:
                    continue
                if any(ds > mp and ds < date_start
                       for _, ds, _ in dates):
                    continue
                if best is None or mp > best:
                    best = mp
            return best

        for d, ds, _de in dates:
            if _mention_before(ex_mentions, ds) is not None:
                ex_date, basis = d, "ex-date"
                break
            if _mention_before(ent_mentions, ds) is not None:
                entitlement_end = d
                ex_date, basis = d + timedelta(days=1), "entitlement+1"
                break
        if ex_date is None and dates:
            # Item-level fallback: the wording need not precede the
            # date at all — take the date NEAREST to an entitlement
            # (or ex-date) mention. A payout date elsewhere in the
            # item loses on distance; the old blanket payout veto is
            # gone, it was the second half of the 15 Nov miss.
            for mentions, is_ent in ((ent_mentions, True),
                                     (ex_mentions, False)):
                if not mentions:
                    continue
                nearest = min(
                    dates,
                    key=lambda e: min(abs(e[1] - mp) for mp in mentions))
                if is_ent:
                    entitlement_end = nearest[0]
                    ex_date = entitlement_end + timedelta(days=1)
                    basis = "entitlement+1"
                else:
                    ex_date, basis = nearest[0], "ex-date"
                break
        # Issue #131: dedup on rounded DPS + ex-date with reporting-
        # noise tolerance — 1.89 / 1.9 / 1.8999999998 are one coupon
        # (42), not three. Keep the first detection (the EGX
        # disclosure's precise value wins: disclosures are scanned
        # before news). A dated detection supersedes an undated one
        # for the same distribution.
        ex_iso = ex_date.isoformat() if ex_date else None
        if ex_date is not None:
            actions = [a for a in actions
                       if not (a["ex_date"] is None
                               and _dps_same(a["dps"], dps))]
        if any(_same_distribution(a["dps"], a["ex_date"], dps, ex_iso)
               for a in actions):
            continue
        actions.append({
            "type": "dividend", "dps": dps,
            "ex_date": ex_date.isoformat() if ex_date else None,
            # Issue #129: the raw entitlement-end date travels with
            # the action so the ledger can re-derive the ex-date
            # (entitlement_end + 1) even when ex_date itself is
            # missing downstream.
            "entitlement_end": (entitlement_end.isoformat()
                                if entitlement_end else None),
            "date_basis": basis,
            "mechanical_pct": round(-dps / base * 100, 2),
            "title": str(it.get("title") or "")[:90]})
    return actions


def main():
    global _ENSEMBLE_JSON_WRITTEN
    digest = load_json(DIGEST)
    if not digest:
        print("ensemble: no digest.json — skipping")
        # Issue #120: a silent early return leaves nothing in the
        # digest — write a ⚠️ line like the exception handler does.
        _note_digest_warning("⚠️ **Ensemble skipped — no digest.json:** the "
                             "orchestrator wrote no digest, so no ensemble "
                             "forecast was produced for this sweep.")
        return
    ticker = (digest.get("ticker") or "").upper()
    results = {r["tool"]: r for r in digest.get("results", [])
               if isinstance(r, dict) and r.get("tool")}

    def metrics(tool):
        r = results.get(tool) or {}
        return ((r.get("summary") or {}).get("metrics")) or {}

    def ok(tool):
        return (results.get(tool) or {}).get("status") == "ok"

    # ---------- base price ----------
    # Freshest close wins (issue #94): the base is the newest dated
    # close across the collected price series. Vendor series lag —
    # on 15 Nov the ensemble stood on pandas-ta's 10.15 while the
    # same sweep's egx-data series already ended at the 15 Nov close
    # of 10.00, mis-anchoring every horizon by ~1.5%. The digest
    # metrics remain the fallback for sweeps whose collected CSVs
    # carry no usable dates.
    series = price_series(ticker, ok)
    fresh = freshest_close(series)
    base, base_src, base_date = None, "", None
    if fresh:
        base, base_src, base_date = (fresh["value"], fresh["source"],
                                     fresh["date"])
    else:
        for tool in ("pandas-ta", "talib"):
            m = metrics(tool)
            if ok(tool) and fnum(m.get("close")) and (m.get("ticker", ticker) == ticker):
                base, base_src = fnum(m["close"]), tool
                break
        if base is None:
            for tool in results:
                if not ok(tool):
                    continue
                for k, v in metrics(tool).items():
                    if k.endswith("_last_close") and ticker.replace(".", "_") in k.upper().replace(".", "_"):
                        base, base_src = fnum(v), tool
                        break
                if base:
                    break
    if not base:
        print("ensemble: no base price found — skipping")
        # Issue #120: see the no-digest.json early return above.
        _note_digest_warning("⚠️ **Ensemble skipped — no base price found:** "
                             "no usable close could be read from the "
                             "collected series or the digest metrics, so no "
                             "ensemble forecast was produced for this sweep.")
        return

    # ---------- two-source price verification ----------
    check = price_crosscheck(ticker, base, base_src, series, base_date)
    if check["status"] == "disagree":
        print(f"ensemble: PRICE SOURCES DISAGREE (spread "
              f"{check['spread_pct']}%): {check['witnesses']} — "
              f"standing on {check['base_source_used']}")
        base, base_src = check["base_used"], check["base_source_used"]
        # The re-stood base is a common-date close: restamp the
        # check's date fields so base_stale describes the base the
        # forecast actually stands on (issue #94).
        base_date = check.get("common_date")
        check["base_date"] = base_date
        check["base_stale"] = bool(
            base_date and check.get("latest_collected_date")
            and base_date < check["latest_collected_date"])

    sigma, sigma_src, density = realized_sigma(ticker, base, ok)

    # ---------- Kronos path ----------
    kronos_path = []
    kcsv = os.path.join(COLLECTED, "kronos", "forecast.csv")
    # Issue #147: a failed Kronos run's forecast.csv (stale carry-over
    # or this run's partial output) must not set the price path.
    if ok("kronos") and os.path.exists(kcsv):
        try:
            with open(kcsv, newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    c, h, l = fnum(row.get("close")), fnum(row.get("high")), fnum(row.get("low"))
                    if c:
                        kronos_path.append((c, h or c, l or c))
        except Exception:
            kronos_path = []
    if not kronos_path and ok("kronos"):
        last = fnum(metrics("kronos").get("forecast.csv_last_close"))
        if last:
            kronos_path = [(last, last, last)] * 10

    def kronos_at(bar):
        if not kronos_path:
            return None
        i = min(bar, len(kronos_path)) - 1
        c, h, l = kronos_path[i]
        return {"close": c, "move": c / base - 1.0,
                "band": max((h - l) / 2.0 / base, 0.004),
                "short": len(kronos_path) < bar}

    # ---------- technicals (pandas-ta voter) ----------
    tech = None
    if ok("pandas-ta"):
        m = metrics("pandas-ta")
        rsi, hist, adx = fnum(m.get("rsi_14")), fnum(m.get("macd_hist")), fnum(m.get("adx_14"))
        close, ema20 = fnum(m.get("close")), fnum(m.get("ema_20"))
        stoch = fnum(m.get("stoch_k"))
        if rsi is not None:
            s = 0.0
            s += .45 if rsi < 30 else .15 if rsi < 45 else 0 if rsi <= 55 else -.15 if rsi <= 70 else -.45
            if adx and adx > 40:
                s *= .55
            if hist is not None:
                s += .30 if hist > 0 else -.30
            if close and ema20:
                s += .15 if close > ema20 else -.15
            if stoch is not None:
                s += -.10 if stoch > 80 else .10 if stoch < 20 else 0
            tech = max(-1.0, min(1.0, s))

    # ---------- sentiment (live-headline trio + news FinBERT) ----------
    subs = []
    for tool in ("finbert", "finbert-tone", "financial-roberta"):
        if not ok(tool):
            continue
        d = load_json(os.path.join(COLLECTED, tool, "sentiment.json"))
        mp = (d or {}).get("mean_probabilities") or {}
        pos, neg = fnum(mp.get("positive")), fnum(mp.get("negative"))
        if pos is None and d:
            pos, neg = find_key(d, ["positive"]), find_key(d, ["negative"])
        if pos is not None and neg is not None:
            subs.append(pos - neg)
    nd = metrics("news-disclosure")
    # The news tool contributes ONE sentiment slot: the average of its
    # own legs (FinBERT on English titles, FinBERT on translated
    # Arabic, the multilingual model on Arabic) — three legs from one
    # tool must not outvote the rest of the family.
    news_legs = []
    if ok("news-disclosure"):
        for pos_k, neg_k in (("finbert_positive", "finbert_negative"),
                             ("translated_positive", "translated_negative"),
                             ("multilingual_positive", "multilingual_negative")):
            if fnum(nd.get(pos_k)) is not None:
                news_legs.append(fnum(nd[pos_k]) - fnum(nd.get(neg_k) or 0))
    if news_legs:
        subs.append(sum(news_legs) / len(news_legs))
    sentiment = (sum(subs) / len(subs)) if subs else None

    # ---------- agents ----------
    avotes = []
    if ok("tradingagents"):
        rating = str(metrics("tradingagents").get("final_rating") or "").strip().lower()
        if rating in RATING_MAP:
            avotes.append(RATING_MAP[rating])
    if ok("finrobot"):
        verdict = str(metrics("finrobot").get("verdict") or "").lower()
        if "bullish" in verdict or "buy" in verdict:
            avotes.append(.6)
        elif "bearish" in verdict or "sell" in verdict:
            avotes.append(-.6)
        elif "neutral" in verdict or "hold" in verdict:
            avotes.append(0.0)
    agent = (sum(avotes) / len(avotes)) if avotes else None

    # ---------- fundamentals (month only, ticker-checked) ----------
    fund = None
    if ok("financetoolkit"):
        comp = str(metrics("financetoolkit").get("company") or "")
        code = ticker.split(".")[0]
        if code in comp or ticker in comp or not comp:
            pe, ref = None, None

            def scan_pe(obj, ref_ctx=None, depth=0):
                """Find a P/E leaf: keys like pe_consolidated_npat_x or
                price_to_earnings, values numeric or {'value': n}.
                Sections named VALUATION_AT_<price> set the ref price."""
                nonlocal pe, ref
                if pe is not None or depth > 6:
                    return
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        m = re.search(r"valuation_at_([\d.]+)", k.lower())
                        r2 = float(m.group(1)) if m else ref_ctx
                        kl = k.lower()
                        if re.search(r"(^|_)pe(_|$)", kl) or "price_to_earnings" in kl \
                                or "price_earnings" in kl:
                            val = fnum(v) if not isinstance(v, dict) else fnum(v.get("value"))
                            if val:
                                pe, ref = val, r2
                                return
                        scan_pe(v, r2, depth + 1)
                        if pe is not None:
                            return
                elif isinstance(obj, list):
                    for v in obj:
                        scan_pe(v, ref_ctx, depth + 1)
                        if pe is not None:
                            return

            def scan_quality(obj):
                """Fallback: latest-period ROE + net margin from blocks
                like {'FY2025': {'roe_pct': {'value': 39.4}, ...}}."""
                best = {}

                def walk(o, section=""):
                    if isinstance(o, dict):
                        for k, v in o.items():
                            kl = k.lower()
                            if kl in ("roe_pct",) or "net_margin" in kl:
                                val = fnum(v) if not isinstance(v, dict) else fnum(v.get("value"))
                                if val is not None:
                                    yr = max([int(y) for y in re.findall(r"(20\d\d)", section)] or [0])
                                    cur = best.get(kl if kl == "roe_pct" else "net_margin")
                                    if cur is None or yr >= cur[0]:
                                        best[kl if kl == "roe_pct" else "net_margin"] = (yr, val)
                            walk(v, k)
                walk(obj)
                roe = best.get("roe_pct", (0, None))[1]
                nm = best.get("net_margin", (0, None))[1]
                if roe is None and nm is None:
                    return None
                s = 0.0
                if roe is not None:
                    s += .30 if roe >= 25 else .15 if roe >= 15 else 0 if roe >= 5 else -.25
                if nm is not None:
                    s += .10 if nm >= 15 else 0 if nm >= 5 else -.10
                return max(-.5, min(.5, s))

            quality = None
            # Issue #67: sorted glob — see realized_sigma above.
            for path in sorted(glob.glob(os.path.join(
                    COLLECTED, "financetoolkit", "*.json"))):
                d = load_json(path)
                if not d:
                    continue
                scan_pe(d)
                if pe:
                    break
                if quality is None:
                    quality = scan_quality(d)
            if pe and pe > 0:
                if ref:
                    pe = pe * base / ref  # rescale the file's reference price to today's base
                fund = .4 if pe < 8 else .15 if pe < 15 else -.1 if pe < 25 else -.35
            elif quality is not None:
                fund = quality

    # ---------- news risk overlay ----------
    # "none" is a MEASURED state (the news tool ran and found nothing
    # alarming). If the tool is missing or failed, the risk is UNKNOWN —
    # never silently "none": cap confidence and widen ranges instead
    # (sweep #20 printed uncapped 0.54 confidence with no overlay at all
    # after the news tool errored).
    risk = {"level": "none", "conf_cap": .60, "price_mult": 1.0, "flags": []}
    if not ok("news-disclosure"):
        risk.update(level="unknown", conf_cap=.35, price_mult=.8,
                    flags=["news overlay unavailable — risk unassessed, "
                           "confidence capped"])
    else:
        news = load_json(os.path.join(COLLECTED, "news-disclosure", "news.json")) or {}
        disc = load_json(os.path.join(COLLECTED, "news-disclosure", "disclosures.json")) or {}
        items = (disc.get("items") or []) + (news.get("items") or [])
        now = datetime.now(timezone.utc)
        fresh_disc = 0
        events = []  # (severity, type, title)
        for it in items:
            title = str(it.get("title") or "")
            dt = None
            for fmt in ("%a, %d %b %Y %H:%M:%S %Z", "%Y-%m-%d"):
                try:
                    dt = datetime.strptime(str(it.get("date") or ""), fmt).replace(tzinfo=timezone.utc)
                    break
                except Exception:
                    continue
            age = (now - dt).days if dt else 99
            if it.get("kind") == "disclosure" and age <= 3:
                fresh_disc += 1
            window = 3 if it.get("kind") == "disclosure" else 2
            if age <= window:
                # Classify on the article BODY when the runner fetched
                # it — a headline can be clickbait or boilerplate while
                # the text carries the actual event.
                text = title + " " + str(it.get("body") or "")[:600]
                low = text.lower()
                for etype, sev, words in EVENT_TYPES:
                    if any(w in low for w in words):
                        events.append((sev, etype, title[:90]))
                        break
        # Abnormal-move confirmation from the verified price series:
        # a severe event the price ignores is weaker than one it
        # confirms, and a >=2.5-sigma session is a shock on its own.
        z_last = z_max3 = 0.0
        try:
            series = price_series(ticker, ok)
            pick = next((s for s in series if s.startswith("egx-data/")), None)
            if pick is None and series:
                pick = max(series, key=lambda s: len(series[s]))
            if pick:
                m = series[pick]
                closes = [m[d] for d in sorted(m)
                          if len(d) == 10 and d[4] == "-"]
                closes = [c for c in closes if c and c > 0]
                if len(closes) >= 4 and sigma > 0:
                    rets = [math.log(closes[i] / closes[i - 1])
                            for i in range(1, len(closes))]
                    z_last = abs(rets[-1]) / sigma
                    z_max3 = max(abs(r) for r in rets[-3:]) / sigma
        except Exception:
            pass
        high = [e for e in events if e[0] == "high"]
        med = [e for e in events if e[0] == "medium"]
        risk["events"] = [{"type": t, "severity": s, "title": ti}
                          for s, t, ti in events[:6]]
        risk["move_z"] = {"last": round(z_last, 2),
                          "max3": round(z_max3, 2)}
        if high or z_last >= 2.5 or (med and z_max3 >= 1.5):
            risk.update(level="shock", conf_cap=.30, price_mult=.5)
            risk["flags"] = [f"{t} event: {ti}" for _, t, ti in high[:3]]
            if not risk["flags"]:
                risk["flags"] = [f"abnormal move: last session "
                                 f"{z_last:.1f}σ"]
            if high and z_last >= 1.5:
                risk["flags"].append(f"price confirms: last session "
                                     f"{z_last:.1f}σ")
        elif med or z_max3 >= 1.5 or fresh_disc or len(items) >= 10:
            risk.update(level="elevated", conf_cap=.45, price_mult=.8)
            risk["flags"] = [f"{t} event: {ti}" for _, t, ti in med[:2]]
            if fresh_disc:
                risk["flags"].append(f"{fresh_disc} disclosure(s) in the last 3 days")
            if z_max3 >= 1.5:
                risk["flags"].append(f"abnormal move: {z_max3:.1f}σ in the last 3 sessions")

    # Issue #436: 2-family backtest mode — the news risk overlay is
    # disabled outright (no news tool runs in a backtest cell, so the
    # live "unknown" cap of 0.35 and price_mult 0.8 would be a
    # penalty for missing data, not a measured risk). The forecast
    # stands on the two families with no cap and no discount.
    if two_family_backtest():
        risk = {"level": "none", "conf_cap": .60, "price_mult": 1.0,
                "flags": ["2-family backtest: news risk overlay "
                          "disabled (issue #436)"]}

    # ---------- corporate actions (dividend awareness) ----------
    # A forecast that spans an ex-date contains a MECHANICAL move (the
    # price drops by ~the dividend on the ex-date) that is not a market
    # signal. Detect announced dividends in the collected items, record
    # the decomposition, and mark every horizon that spans the ex-date
    # — the calibration ledger will score those forecasts on a
    # dividend-adjusted basis instead of counting the drop as error.
    actions = []
    try:
        _news = load_json(os.path.join(COLLECTED, "news-disclosure", "news.json")) or {}
        _disc = load_json(os.path.join(COLLECTED, "news-disclosure", "disclosures.json")) or {}
        _items = (_disc.get("items") or []) + (_news.get("items") or [])
        as_of = None
        try:
            as_of = date.fromisoformat(str(digest.get("date") or "")[:10])
        except Exception:
            as_of = datetime.now(timezone.utc).date()
        actions = detect_corporate_actions(_items, base, as_of.year)
    except Exception:
        actions = []
    # Issue #436: the backtest harness supplies the dividend actions
    # known at the cutoff in digest["corporate_actions"] (Yahoo
    # events feed, ex-dates <= as-of only — an ex-date after the
    # cutoff is unknown to the forecast and enters only at scoring
    # time). They merge exactly like the #281 event feed below, so
    # the #130 rescale and the horizon marking consume them the same
    # way. Shape: {type: "dividend", dps, ex_date,
    # entitlement_end?, mechanical_pct, source}.
    try:
        _digest_actions = digest.get("corporate_actions")
        if isinstance(_digest_actions, list) and _digest_actions:
            _clean = [a for a in _digest_actions
                      if isinstance(a, dict)
                      and a.get("type") == "dividend"
                      and a.get("ex_date") and a.get("dps") is not None]
            if _clean:
                actions = merge_corporate_actions(actions, _clean)
    except Exception:
        pass
    # Issue #281: feed verified #109 disclosure events into the same
    # scoring. The worker's phase-2 extraction writes
    # disclosure-events/<CODE>-events.json into the run dir and
    # merge.py stages it into the sweep dir before the ensemble runs,
    # so the file is here (cwd) when present. Absent on Actions
    # sweeps and pre-#278 runs; a missing or malformed feed changes
    # nothing — the legacy text detection above still stands, and a
    # dead feed never loses a sweep.
    try:
        _ev_path = os.path.join(
            os.getcwd(), "disclosure-events",
            "%s-events.json" % ticker.split(".")[0])
        _feed = load_json(_ev_path)
        if isinstance(_feed, dict):
            _ev_actions = events_to_corporate_actions(
                _feed.get("events") or [], ticker, base)
            if _ev_actions:
                actions = merge_corporate_actions(actions, _ev_actions)
    except Exception:
        pass

    # ---------- issue #130: ex-date-today Kronos rescale ----------
    # On the ex-date itself (as_of == ex_date) the base is already
    # post-ex while the Kronos path is still pre-ex scale: the model
    # was fit on pre-ex history and knows nothing of the dividend,
    # so kronos_at() measures a ~+DPS/pre-ex move that is purely the
    # mechanical ex-gap (16 Nov proof run: +28.55% move, day expected
    # +18.61%). Re-anchor the whole path multiplicatively to the
    # post-ex level — factor (pre_ex_close - DPS) / pre_ex_close —
    # which preserves Kronos's own relative moves instead of
    # subtracting a flat DPS from each bar. The path carries no
    # usable dates for this (its row dates lag as_of by a session
    # and row 0 IS the day forecast), so the rescale applies to the
    # whole path, not by row date. It applies only when the base is
    # provably post-ex (base_date >= ex_date) AND the path actually
    # sits above the post-ex base by at least half the mechanical
    # gap — a path already in post-ex scale is left alone. Any
    # failure here degrades to no rescale; the marking below still
    # says the ex-date is today.
    ex_rescale = None
    try:
        _today = [a for a in actions
                  if a.get("ex_date")
                  and date.fromisoformat(a["ex_date"]) == as_of]
        if _today:
            _a = _today[0]
            _ex = date.fromisoformat(_a["ex_date"])
            _dps = float(_a["dps"])
            _base_d = None
            try:
                _base_d = date.fromisoformat(str(base_date)[:10]) if base_date else None
            except Exception:
                _base_d = None
            ex_rescale = {"ex_date": _a["ex_date"], "dps": _a["dps"],
                          "applied": False}
            if _base_d is not None and _base_d >= _ex:
                _pre, _pre_src = None, None
                _cands = []
                for _src, _m in (series or {}).items():
                    _dated = sorted(d for d in _m
                                    if len(d) == 10 and d[4] == "-"
                                    and d < _a["ex_date"])
                    if _dated:
                        _cands.append((_dated[-1],
                                       _src.startswith("egx-data/"),
                                       _src, _m[_dated[-1]]))
                if _cands:
                    _cands.sort(key=lambda t: (t[0], t[1]))
                    _pre = _cands[-1][3]
                    _pre_src = _cands[-1][2]
                if _pre is None:
                    _pre, _pre_src = base + _dps, "base+dps (no pre-ex close in series)"
                if _pre and 0 < _dps < _pre:
                    _f = (_pre - _dps) / _pre
                    _gap = _dps / _pre
                    _inflated = bool(kronos_path) and (
                        kronos_path[0][0] / base - 1.0 > 0.5 * _gap)
                    ex_rescale.update(
                        pre_ex_close=_pre, pre_ex_source=_pre_src,
                        factor=round(_f, 4))
                    if 0.5 < _f < 1.0 and _inflated:
                        kronos_path = [(c * _f, h * _f, l * _f)
                                       for (c, h, l) in kronos_path]
                        ex_rescale["applied"] = True
                    else:
                        ex_rescale["reason"] = (
                            "path already post-ex scale"
                            if not _inflated else "factor out of range")
                else:
                    ex_rescale["reason"] = "no usable pre-ex close"
            else:
                ex_rescale["reason"] = "base not post-ex (base_date %s)" % (base_date,)
    except Exception as e:
        ex_rescale = {"applied": False, "reason": f"rescale error: {e}"}

    # ---------- combine per horizon ----------
    # Issue #436: 2-family backtest mode — sentiment, agent and
    # fundamentals never vote (see two_family_backtest()). The
    # blocks above still ran (they read metrics/files only), but
    # their scores are discarded here, before the combine.
    if two_family_backtest():
        sentiment = agent = fund = None
    fam_fixed = {"technicals": tech, "sentiment": sentiment,
                 "agent": agent, "fundamentals": fund}
    out = {"tool": "forecast-ensemble", "version": 2, "ticker": ticker,
           "base_price": base, "base_source": base_src,
           "base_date": base_date,
           "price_crosscheck": check, "corporate_actions": actions,
           "kronos_ex_rescale": ex_rescale,
           "sigma_daily": round(sigma, 4), "sigma_source": sigma_src,
           "sessions_per_calendar_day": round(density, 3),
           "date": digest.get("date"), "risk": risk,
           "weights_source": WEIGHTS_SOURCE,
           "applied_weights": WEIGHTS_INFO,
           "family_scores": {}, "horizons": {},
           "confidence_basis": ("calibrated (ledger skill factors applied)"
                                if WEIGHTS_SOURCE == "ledger" else
                                "provisional (uncalibrated — no scoring history yet)")}
    fam_display = dict(fam_fixed)
    for hname, bar in HORIZONS.items():
        ka = kronos_at(bar)
        # Kronos bars are CALENDAR days; sigma is per TRADING session.
        # A horizon of `bar` calendar days contains ~bar*density sessions,
        # and it is the sessions that carry the volatility.
        h_eff = max(1, round(bar * density))
        vol_h = sigma * math.sqrt(h_eff)        # 1-sigma move over the horizon
        price_score = None
        if ka:
            price_score = max(-1.0, min(1.0, ka["move"] / (2.0 * vol_h))) if vol_h > 0 else 0.0
        fam_display["price-forecast"] = price_score
        scores, weights = {}, {}
        for fam, s in list(fam_fixed.items()) + [("price-forecast", price_score)]:
            if s is None or W[fam][hname] == 0:
                continue
            w = W[fam][hname] * (risk["price_mult"] if fam == "price-forecast" else 1.0)
            scores[fam], weights[fam] = s, w
        if not scores:
            continue
        wsum = sum(weights.values())
        net = sum(scores[f] * weights[f] for f in scores) / wsum
        var = sum(weights[f] * (scores[f] - net) ** 2 for f in scores) / wsum
        disagree = math.sqrt(var)
        kmove = ka["move"] if ka else 0.0
        expected = expected_move(kmove, net, vol_h)
        half = max(1.28 * vol_h, ka["band"] if ka else 0.0) \
            * RISK_MULT[risk["level"]] * (1 + .5 * disagree)
        agree = max(0.0, 1.0 - disagree)
        conf = min(risk["conf_cap"], .20 + .45 * agree + .10 * (len(scores) / 5))
        out["horizons"][hname] = {
            "direction": "up" if expected > .0075 else "down" if expected < -.0075 else "flat",
            "expected_move_pct": round(expected * 100, 2),
            "range_low_pct": round((expected - half) * 100, 2),
            "range_high_pct": round((expected + half) * 100, 2),
            "confidence": round(conf, 2),
            "net_score": round(net, 3),
            "families": {f: round(scores[f], 3) for f in scores},
            "horizon_short": bool(ka and ka["short"]),
            "trading_sessions": h_eff,
            # Issue #436: the backtest scorer rebuilds the
            # family-alone entrants from these two numbers instead
            # of re-deriving them from rounded sigma_daily.
            "kronos_move_pct": round(kmove * 100, 4) if ka else None,
            "vol_h_pct": round(vol_h * 100, 4),
        }
        # Mark horizons spanning an ex-date: the mechanical dividend
        # drop inside them is decomposed, not forecast skill/error.
        # Issue #130: the window starts AT the ex-date, not after
        # it — on the ex-date itself the base is already post-ex,
        # so the horizon must say so out loud (and the Kronos path
        # above was rescaled to the post-ex level when it applied).
        # Issue #131: keep the FIRST in-window action — after the
        # detection dedup at most one action per distribution
        # survives, so the horizon block no longer depends on
        # disclosure-item order.
        for a in actions:
            if (a.get("ex_date")
                    and "corporate_action" not in out["horizons"][hname]):
                try:
                    ex = date.fromisoformat(a["ex_date"])
                except Exception:
                    continue
                if as_of <= ex <= as_of + timedelta(days=bar):
                    _mark = {
                        "type": a["type"], "dps": a["dps"],
                        "ex_date": a["ex_date"],
                        "mechanical_pct": a["mechanical_pct"]}
                    # Issue #129: carry the entitlement-end date
                    # into the horizon block too, so the ledger can
                    # re-derive the ex-date from the block alone.
                    if a.get("entitlement_end"):
                        _mark["entitlement_end"] = a["entitlement_end"]
                    if ex == as_of:
                        _mark["ex_date_today"] = True
                        _mark["kronos_rescaled"] = bool(
                            ex_rescale and ex_rescale.get("applied")
                            and ex_rescale.get("ex_date") == a["ex_date"])
                        if _mark["kronos_rescaled"]:
                            _mark["rescale_factor"] = ex_rescale["factor"]
                            _mark["pre_ex_close"] = ex_rescale["pre_ex_close"]
                    out["horizons"][hname]["corporate_action"] = _mark
    out["family_scores"] = {k: (round(v, 3) if v is not None else None)
                            for k, v in fam_display.items()}

    # Issue #120: ensemble.json is written BEFORE the digest section
    # is appended below — if anything raises in between, the __main__
    # handler removes this run's ensemble.json, so the digest's "NO
    # ensemble forecast" line and the file on disk cannot contradict
    # each other (the ledger scores ensemble.json when present).
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    _ENSEMBLE_JSON_WRITTEN = True

    lines = ["", "---", "", "## 🎯 Ensemble forecast (synthesizer v2)", "",
             f"Base price {base} ({base_src}"
             + (f", {base_date}" if base_date else "") + f"). Daily volatility σ {sigma:.2%} ({sigma_src}). "
             f"Kronos bars are calendar days — horizons are scaled to trading sessions "
             f"(density {density:.2f}/day). "
             f"News risk: **{risk['level']}**"
             + ((" — " + "; ".join(risk["flags"])) if risk["flags"] else "") + ".",
             "Ranges are anchored in realized volatility. Confidence is provisional "
             "(uncalibrated) until the scoring ledger has history.", ""]
    if check["status"] == "disagree":
        wit = ", ".join(f"{s} {v:g}" for s, v in check["witnesses"].items())
        lines += [f"⚠️ **Price sources disagree** (spread {check['spread_pct']}%: "
                  f"{wit}) — this forecast stands on {check['base_source_used']} "
                  f"= {check['base_used']:g}.", ""]
    if check.get("base_stale"):
        lines += [f"⚠️ **Stale base:** the base close is dated "
                  f"{check.get('base_date')} but the freshest collected "
                  f"series reaches {check.get('latest_collected_date')} — "
                  f"this forecast is anchored on an older close.", ""]
    _aw = WEIGHTS_INFO.get("factors") or {}
    lines += ["Applied weights (" + WEIGHTS_SOURCE + "): " + ", ".join(
        f"{k} ×{_fmt_factor(v)}" for k, v in _aw.items()) + ".", ""]
    for a in actions:
        if a.get("ex_date"):
            # Issue #281: name the event source in the digest line so
            # the dividend-aware adjustment is visibly event-fed, not
            # only text-detected.
            _prov = ""
            if a.get("source") == "disclosure-event":
                _prov = (" — via verified EGX disclosure event %s "
                         "(verbatim ex-date)"
                         % (a.get("event_id") or "?"))
            if a["ex_date"] == as_of.isoformat():
                # Issue #130: the ex-date is TODAY — the drop already
                # happened and the base already reflects it, so there
                # is no mechanical move left to expect; say what was
                # done about the pre-ex Kronos path instead.
                if ex_rescale and ex_rescale.get("applied"):
                    _rs = (f"the Kronos path was rescaled ×{ex_rescale['factor']:.3f} "
                           f"to the post-ex level (pre-ex close "
                           f"{ex_rescale['pre_ex_close']:g}), so the "
                           f"forecasts below carry no mechanical ex-gap")
                else:
                    _rs = ("the Kronos path showed no mechanical "
                           "inflation, so no rescale was applied")
                lines += [f"💰 **Corporate action:** dividend {a['dps']:g}/share, "
                          f"ex-date {a['ex_date']} (today) — the base price "
                          f"already reflects the ex-dividend drop; {_rs}. "
                          f"Horizons are marked ex-distorted; the calibration "
                          f"ledger scores them without further adjustment.{_prov}", ""]
            else:
                lines += [f"💰 **Corporate action:** dividend {a['dps']:g}/share, "
                          f"ex-date {a['ex_date']} — a mechanical "
                          f"≈ {a['mechanical_pct']:+.2f}% move is expected on the "
                          f"ex-date (not a market signal). Horizons spanning it "
                          f"are marked; the calibration ledger will score them "
                          f"dividend-adjusted.{_prov}", ""]
    lines += [
             "| Horizon | Direction | Expected | Range | Confidence |",
             "|---|---|---|---|---|"]
    for hname in ("day", "week", "month"):
        h = out["horizons"].get(hname)
        if not h:
            continue
        arrow = {"up": "⬆ up", "down": "⬇ down", "flat": "➡ flat"}[h["direction"]]
        note = " (fleet horizon)" if h["horizon_short"] else ""
        if h.get("trading_sessions") and h["trading_sessions"] != HORIZONS[hname]:
            note += f" (≈{h['trading_sessions']} sessions)"
        if h.get("corporate_action"):
            _ca = h["corporate_action"]
            if _ca.get("ex_date_today"):
                if _ca.get("kronos_rescaled"):
                    note += (f" (ex-date today — Kronos path rescaled "
                             f"×{_ca['rescale_factor']:.3f} to post-ex level)")
                else:
                    note += " (ex-date today — no Kronos rescale needed)"
            else:
                note += (f" (incl. {_ca['mechanical_pct']:+.1f}% "
                         f"mechanical ex-dividend)")
        lines.append(f"| {hname}{note} | {arrow} | {h['expected_move_pct']:+.2f}% | "
                     f"{h['range_low_pct']:+.2f}% … {h['range_high_pct']:+.2f}% | {h['confidence']:.2f} |")
    lines += ["", "Family scores (−1…+1): " + ", ".join(
        f"{k} {v:+.2f}" if v is not None else f"{k} —" for k, v in fam_display.items()) + ".",
        "Verdicts are combined by family, weighted by horizon; disagreement widens "
        "the range instead of being averaged away."]
    # Issue #113: ensure the digest is headed before appending, so a
    # gator that died before writing digest.md cannot leave the
    # ensemble section orphaned in a headerless file.
    _ensure_digest_header(digest)
    with open(OUT_MD, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("ensemble v2: written for", ticker, "| sigma", round(sigma, 4),
          "| horizons:", list(out["horizons"]))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("ensemble failed (non-fatal):", e)
        # Issue #120: ensemble.json is written BEFORE the digest
        # section is appended — an exception in between used to leave
        # a complete ensemble.json on disk while the handler wrote
        # "this digest has NO ensemble forecast", and the ledger later
        # scored the file. Remove this run's file so the warning is
        # true; the failure is still recorded in ensemble_error.txt
        # and the digest.
        if _ENSEMBLE_JSON_WRITTEN:
            try:
                os.remove(OUT_JSON)
            except OSError:
                pass
        # Never fail SILENTLY: leave a sentinel next to the digest and a
        # visible warning in it, so a missing ensemble is noticed.
        try:
            ddir = os.path.dirname(OUT_JSON)
            os.makedirs(ddir, exist_ok=True)
            with open(os.path.join(ddir, "ensemble_error.txt"), "w") as f:
                f.write(f"ensemble failed: {type(e).__name__}: {e}\n")
            if os.path.exists(OUT_MD):
                with open(OUT_MD, "a") as f:
                    f.write("\n## ⚠️ Ensemble failed — see ensemble_error.txt; "
                            "this digest has NO ensemble forecast.\n")
            else:
                # Issue #113: a missing digest.md must not stay missing
                # — write it headed (job from digest.json when present)
                # so the issue step still titles and files the digest.
                job = ""
                try:
                    with open(DIGEST, encoding="utf-8") as f:
                        job = json.load(f).get("job") or ""
                except Exception:
                    pass
                header = (f"# 🐊 Borsagator digest — {job}"
                          if job else "# 🐊 Borsagator digest")
                with open(OUT_MD, "w", encoding="utf-8") as f:
                    f.write(header + "\n\n## ⚠️ Ensemble failed — see "
                            "ensemble_error.txt; this digest has NO "
                            "ensemble forecast.\n")
        except Exception:
            pass
    sys.exit(0)
