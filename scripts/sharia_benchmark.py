#!/usr/bin/env python3
"""Borsagator Sharia accuracy benchmark (issue #172).

Measures OUR Sharia engine (scripts/sharia_engine.py) against the
published classifications of the sources that use each standard:

  Musaffa            -> our AAOIFI, denominator variant avg36m
                        (Musaffa: trailing 36-month average market value)
  Faisal Securities  -> our AAOIFI, denominator variant spot
                        (Faisal: spot market capitalisation)
  Ostool Securities  -> our EGX33 (Ostool adopts the EGX33 criteria
                        verbatim, so its list is a like-for-like witness)
  EGX33 membership   -> our EGX33 (index membership is the ground truth
                        for that standard)

plus a purification comparison: our AAOIFI purification ratio vs the
per-stock percentages the sources publish (Ostool's prohibited-income
column; Nour Borsa's purification percentages as an extra witness;
Musaffa publishes no per-stock ratio on its public pages).

Freeze discipline (shared with issue #79): each source's published
classification is snapshotted ONCE into sharia/benchmark/sources/
with the source URL and retrieval date on every row, and scoring runs
against the frozen snapshots — never against a moving page. Re-freeze
deliberately when a source republishes; re-score whenever a rule set
or an input pipeline changes.

Honesty rules (binding):
- A source whose current list cannot be fetched from a public
  page/PDF is recorded as status "unavailable" with what was tried —
  never fabricated, never scraped behind a login.
- Our verdict of insufficient-data is counted in its own bucket,
  never as agreement or disagreement.
- Agreement % is null (not 0, not 100) when there are no determinate
  pairs to score.
- A disagreement's driver is labelled a hypothesis unless it is read
  directly off the published inputs.

Framing (binding): every output is a per-standard screening result —
"screened under standard X" — never a fatwa and never religious or
investment advice. No user-facing accuracy claim ships off the back
of this benchmark (issues #77 / #79 rules).

The engine itself stays offline; only this tool's freeze step touches
the network (urllib, public pages/PDFs only). Scoring is pure stdlib
and re-runnable offline against the frozen snapshots and raw cache.
The Ostool PDF is converted with the system `pdftotext -layout` when
available; without it the freeze records the source unavailable.

Usage:
  python3 scripts/sharia_benchmark.py freeze [--sources a,b,c]
  python3 scripts/sharia_benchmark.py freeze --mark-unavailable faisal \
      --reason "..."
  python3 scripts/sharia_benchmark.py score
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import sharia_engine  # noqa: E402  (offline engine; our side of the bench)

BENCH_DIR = os.path.join(ROOT, "sharia", "benchmark")
SOURCES_DIR = os.path.join(BENCH_DIR, "sources")
RAW_DIR = os.path.join(BENCH_DIR, "raw")
UNIVERSE_FILE = os.path.join(HERE, "sharia_fixtures", "covered_universe.json")

FRAMING_EN = ("Screening result under the named standard only, computed "
              "from the company's published financials. This is not a "
              "fatwa, and not religious or investment advice.")
FRAMING_AR = ("نتيجة فحص وفق المعيار المذكور فقط، محسوبة من القوائم المالية "
              "المنشورة للشركة. ليست فتوى، وليست نصيحة دينية أو استثمارية.")

UA = "Mozilla/5.0 (X11; Linux x86_64) borsagator-sharia-benchmark/1.0"

MUSAFFA_STOCK_URL = "https://musaffa.com/stock/{ticker}/"
OSTOOL_PDF_URL = "https://stocks.templatesnippet.com/pdfs/osoul/compliance-list.pdf"
FAISAL_PDF_URL = ("https://fbcbrokerage.com/wp-content/uploads/2024/03/"
                  "التحليل-الفني-لأهم-الاسهم-المتوافقة-31-03-2024.pdf")
EGX33_LIST_URL = "https://foudalens.com/en/halal-stocks"
EGX33_ORIGIN_URL = "https://beta.egx.com.eg/ar/market/indices/overview?index=EGX_SHARIAH"
NOUR_BORSA_URL = "https://nourborsa.com/"

# EGX33 thresholds, for driver hypotheses read off Ostool's published
# percentages (the same numbers the EGX33 rule set encodes).
EGX33_LIMITS = {"interest_deposits_pct": 33.0, "interest_loans_pct": 33.0,
                "liquid_assets_pct": 70.0, "prohibited_income_pct": 5.0}


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def today_cairo():
    # Cairo is UTC+2 year-round since 2023's DST repeal was reversed;
    # close enough for a report label: derive from UTC date +2h.
    from datetime import timedelta
    return (datetime.now(timezone.utc) + timedelta(hours=2)).strftime("%Y-%m-%d")


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def load_universe():
    with open(UNIVERSE_FILE, encoding="utf-8") as f:
        data = json.load(f)
    return data["snapshots"] if isinstance(data, dict) else data


def write_json(path, doc):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")


# ---------------------------------------------------------------- parsers

def parse_musaffa_page(text):
    """Verdict off a Musaffa per-stock page (HTML or rendered text).

    Returns {verdict, verdict_raw, as_of} or None when no verdict
    statement is present. Musaffa's labels: halal / not halal /
    doubtful, under AAOIFI."""
    m = re.search(r"classified as\s+(NOT HALAL|HALAL|DOUBTFUL)\b", text, re.I)
    if not m:
        return None
    raw = m.group(1).upper()
    verdict = {"HALAL": "compliant", "NOT HALAL": "non-compliant",
               "DOUBTFUL": "doubtful"}[raw]
    as_of = None
    m2 = re.search(r"As of\s+([A-Z][a-z]+ \d{4})", text)
    if m2:
        as_of = m2.group(1)
    return {"verdict": verdict, "verdict_raw": raw, "as_of": as_of}


def parse_ostool_layout(text):
    """Rows off `pdftotext -layout` output of the Ostool PDF.

    Column order was pinned against the PDF's own header by word
    x-positions (pdftotext -bbox): in layout (left-to-right) order a
    data row reads: verdict, prohibited-income %, liquid-assets %,
    interest-loans %, interest-deposits %, total assets (EGP m),
    average market value (EGP m), sector, name, code. Percentages are
    Ostool's published ratios on the EGX33 base (greater of total
    assets or average market value); the liquid-assets % is of total
    assets. Rows for companies admitted via their own Sharia board
    (the three Islamic banks, two leasing companies) carry a verdict
    and no percentages.
    """
    rows = {}
    order = []
    for line in text.splitlines():
        m = re.search(r"\b([A-Z]{2,6})\.CA\b", line)
        if not m:
            continue
        ticker = m.group(1) + ".CA"
        if "غير متوافق" in line:
            verdict, verdict_raw = "non-compliant", "غير متوافق"
        elif "متوافق" in line:
            verdict, verdict_raw = "compliant", "متوافق"
        else:
            continue
        pcts = [float(x) for x in re.findall(r"%(\d+(?:\.\d+)?)", line)]
        nums = [float(x.replace(",", "")) for x in re.findall(
            r"(?<![%\d.])(\d{1,3}(?:,\d{3})+\.\d+|\d+\.\d+)", line)]
        ratios = None
        if len(pcts) == 4:
            ratios = {
                "prohibited_income_pct": pcts[0],
                "liquid_assets_pct": pcts[1],
                "interest_loans_pct": pcts[2],
                "interest_deposits_pct": pcts[3],
            }
        row = {
            "ticker": ticker,
            "verdict": verdict,
            "verdict_raw": verdict_raw,
            "published_ratios": ratios,
            "total_assets_m_egp": nums[0] if len(nums) >= 2 else None,
            "avg_market_value_m_egp": nums[1] if len(nums) >= 2 else None,
            "ratios_note": (None if ratios else
                            "No percentages published for this row "
                            "(company admitted via its own Sharia board)."),
        }
        if ticker not in rows:
            order.append(ticker)
        rows[ticker] = row
    return [rows[t] for t in order]


def parse_egx33_constituents(html):
    """EGX33 constituent tickers off the mirror page. The page states
    the list is complete (34 names) and sourced from the official EGX
    Shariah index; a whole-page code scan reproduced exactly that
    count at freeze time."""
    codes = re.findall(r"\b([A-Z]{2,6})\.CA\b", html)
    seen, out = set(), []
    for c in codes:
        t = c + ".CA"
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def parse_faisal_text(text):
    """Faisal Securities' report is a binary compliant list: a ticker
    whose code appears in the report is listed as compliant. (Parser
    implemented for the next freeze; the 2026-11-18 freeze could not
    retrieve the PDF — see the faisal snapshot's unavailable_reason.)
    """
    codes = re.findall(r"\b([A-Z]{2,6})\.CA\b", text)
    seen, out = set(), []
    for c in codes:
        t = c + ".CA"
        if t not in seen:
            seen.add(t)
            out.append({"ticker": t, "verdict": "compliant",
                        "verdict_raw": "listed (binary compliant list)"})
    return out


# ---------------------------------------------------------------- freeze

def base_snapshot(source_id, name_en, name_ar, standard, source_url):
    return {
        "source_id": source_id,
        "source_name_en": name_en,
        "source_name_ar": name_ar,
        "standard": standard,
        "source_url": source_url,
        "retrieved_at": now_iso(),
        "status": "ok",
        "unavailable_reason": None,
        "rows": [],
        "framing_en": FRAMING_EN,
        "framing_ar": FRAMING_AR,
    }


def stamp_rows(rows, source_url, retrieved_at):
    for r in rows:
        # A row may carry its own concrete source URL (e.g. a per-stock
        # page); the snapshot-level URL is the fallback.
        r.setdefault("source_url", source_url)
        r["retrieved_at"] = retrieved_at
    return rows


def freeze_musaffa():
    snap = base_snapshot(
        "musaffa", "Musaffa — per-stock Shariah screening (AAOIFI)",
        "مصفّى — تصنيف الأسهم وفق أيوفي", "AAOIFI",
        "https://musaffa.com/screening-methodology/")
    rows = []
    for snapshot in load_universe():
        ticker = snapshot["ticker"]
        url = MUSAFFA_STOCK_URL.format(ticker=ticker)
        raw = fetch(url)
        os.makedirs(RAW_DIR, exist_ok=True)
        with open(os.path.join(RAW_DIR, f"musaffa-{ticker}.html"), "wb") as f:
            f.write(raw)
        parsed = parse_musaffa_page(raw.decode("utf-8", "replace"))
        if parsed is None:
            rows.append({"ticker": ticker, "verdict": None,
                         "verdict_raw": None, "source_url": url,
                         "note": "No verdict statement found on the "
                                 "public page at freeze time."})
        else:
            rows.append({"ticker": ticker, **parsed, "source_url": url,
                         "purification_ratio": None,
                         "purification_note":
                             "Musaffa publishes no per-stock purification "
                             "ratio on its public stock pages (checked "
                             "at freeze time); its purification figures "
                             "sit behind its calculator/account."})
    snap["rows"] = stamp_rows(rows, MUSAFFA_STOCK_URL, snap["retrieved_at"])
    snap["method_note"] = ("Per-stock pages fetched for every ticker in "
                           "our covered universe; Musaffa's methodology "
                           "is AAOIFI with a trailing 36-month average "
                           "market-value denominator.")
    return snap


def freeze_ostool():
    snap = base_snapshot(
        "ostool",
        "Ostool Securities — Sharia compliance list (EGX33 criteria)",
        "أسطول لتداول الأوراق المالية — قائمة الأسهم المتوافقة (معايير EGX33)",
        "EGX33", OSTOOL_PDF_URL)
    raw = fetch(OSTOOL_PDF_URL)
    snap["document_date"] = "2026-08-04"
    snap["raw_sha256"] = sha256_bytes(raw)
    snap["raw_bytes"] = len(raw)
    try:
        proc = subprocess.run(
            ["pdftotext", "-layout", "-", "-"], input=raw,
            capture_output=True, timeout=120)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.decode("utf-8", "replace")[:200])
        text = proc.stdout.decode("utf-8", "replace")
    except Exception as e:
        snap["status"] = "unavailable"
        snap["unavailable_reason"] = (
            f"PDF fetched ({len(raw)} bytes, sha256 {snap['raw_sha256']}) "
            f"but text extraction failed: {e}. pdftotext (poppler) is "
            "required for this source.")
        return snap
    os.makedirs(RAW_DIR, exist_ok=True)
    with open(os.path.join(RAW_DIR, "ostool-compliance-list.layout.txt"),
              "w", encoding="utf-8") as f:
        f.write(text)
    rows = parse_ostool_layout(text)
    snap["rows"] = stamp_rows(rows, OSTOOL_PDF_URL, snap["retrieved_at"])
    snap["rows_parsed"] = len(rows)
    snap["method_note"] = (
        "Full published table frozen (all parsed rows, not only our "
        "universe). Ostool's report states it screened 100+ companies; "
        f"{len(rows)} rows were machine-parsed from the PDF's tables — "
        "any row lost to PDF line-splitting is missing from the "
        "snapshot, which matters only if it is in our covered "
        "universe. Column mapping was pinned against the PDF header "
        "by word x-positions (pdftotext -bbox).")
    return snap


def freeze_egx33():
    snap = base_snapshot(
        "egx33", "EGX33 Shariah Index — constituent membership "
        "(ground truth for the EGX33 standard)",
        "مؤشر الشريعة EGX33 — عضوية المؤشر", "EGX33", EGX33_LIST_URL)
    raw = fetch(EGX33_LIST_URL)
    os.makedirs(RAW_DIR, exist_ok=True)
    with open(os.path.join(RAW_DIR, "egx33-constituents-foudalens.html"),
              "wb") as f:
        f.write(raw)
    tickers = parse_egx33_constituents(raw.decode("utf-8", "replace"))
    rows = [{"ticker": t, "verdict": "compliant",
             "verdict_raw": "EGX33 constituent",
             "verdict_basis": "index membership"} for t in tickers]
    snap["rows"] = stamp_rows(rows, EGX33_LIST_URL, snap["retrieved_at"])
    snap["constituent_count"] = len(tickers)
    snap["list_complete"] = True
    snap["provenance_note"] = (
        "Constituent list as mirrored by FoudaLens, which states it "
        "reproduces the official EGX Shariah index constituents "
        "without computing ratios. EGX's own overview is "
        f"{EGX33_ORIGIN_URL} ; EGX's legacy constituents endpoint "
        "could not be fetched with the tooling available at freeze "
        "time, so the mirror is the frozen source and is named as "
        "such on every row. Non-membership of a covered ticker is "
        "derived from this complete list, and labelled derived.")
    return snap


FREEZERS = {"musaffa": freeze_musaffa, "ostool": freeze_ostool,
            "egx33": freeze_egx33}

SOURCE_META = {
    "faisal": ("Faisal Securities Brokerage — compliant-stocks report "
               "(AAOIFI, spot market cap)", "فيصل لتداول الأوراق المالية",
               "AAOIFI", FAISAL_PDF_URL),
    "nour_borsa": ("Nour Borsa — per-stock Sharia details and "
                   "purification percentages (extra witness)",
                   "نور البورصة", None, NOUR_BORSA_URL),
}


def mark_unavailable(source_id, reason):
    name_en, name_ar, standard, url = SOURCE_META[source_id]
    snap = base_snapshot(source_id, name_en, name_ar, standard, url)
    snap["status"] = "unavailable"
    snap["unavailable_reason"] = reason
    if source_id == "faisal":
        snap["document_date"] = "2024-03-31"
    return snap


# ---------------------------------------------------------------- scoring

def normalize_ours(verdict):
    if verdict in ("compliant", "compliant-with-purification"):
        return "compliant"
    if verdict == "non-compliant":
        return "non-compliant"
    return "insufficient-data"


def normalize_theirs(row):
    if row is None:
        return "not-covered"
    v = row.get("verdict")
    if v in ("compliant", "non-compliant"):
        return v
    if v == "doubtful":
        return "doubtful"
    return "not-covered"


def our_verdicts():
    """Run the engine over the covered universe for every comparison
    configuration. Returns {config_id: {ticker: engine row}}."""
    configs = {
        "aaoifi-avg36m": ("AAOIFI", {"denominator_variant": "avg36m"}),
        "aaoifi-spot": ("AAOIFI", {"denominator_variant": "spot"}),
        "egx33": ("EGX33", None),
    }
    out = {}
    universe = load_universe()
    for cfg, (std, params) in configs.items():
        ruleset = sharia_engine.load_ruleset(std)
        out[cfg] = {s["ticker"]: sharia_engine.screen(s, ruleset, params)
                    for s in universe}
    return out


def explain_row(our_row, their_row, outcome):
    """Per-row explanation from the inputs, or an explicit mark.
    Hypotheses are labelled as hypotheses."""
    if outcome == "our-insufficient-data":
        missing = ", ".join(our_row.get("missing_inputs") or [])
        return (f"Not comparable: our engine returned insufficient-data "
                f"(missing inputs: {missing}). Counted separately, "
                "never as agreement or disagreement.")
    if outcome in ("agree",):
        return "Both sides determinate and equal."
    if outcome.startswith("disagree"):
        parts = []
        for r in our_row.get("ratios") or []:
            if r.get("value") is not None and r.get("threshold") is not None:
                parts.append(f"our {r.get('id')}: {r['value']} vs "
                             f"limit {r['threshold']}")
        if their_row and their_row.get("published_ratios"):
            parts.append("their published ratios: " + json.dumps(
                their_row["published_ratios"], ensure_ascii=False))
        if parts:
            return ("Hypothesis (from the published inputs): "
                    + "; ".join(parts))
        return "unexplained"
    if outcome == "their-indeterminate":
        return ("Not comparable: the source's verdict is indeterminate "
                "(e.g. Musaffa 'doubtful'). Counted separately.")
    if outcome == "not-covered-by-source":
        return "The source does not cover this ticker in its frozen list."
    return "unexplained"


def compare(our_rows, source_snap):
    """Score one source snapshot against our engine rows."""
    their = {r["ticker"]: r for r in source_snap.get("rows") or []}
    counts = {"agree": 0, "we_compliant_they_non_compliant": 0,
              "we_noncompliant_they_compliant": 0,
              "our_insufficient_data": 0, "their_indeterminate": 0,
              "not_covered_by_source": 0}
    rows = []
    for ticker, our_row in sorted(our_rows.items()):
        ours = normalize_ours(our_row.get("verdict"))
        trow = their.get(ticker)
        theirs = normalize_theirs(trow)
        if theirs == "not-covered" and source_snap.get("list_complete"):
            # A complete list (EGX33 constituents): absence IS a
            # published non-membership, labelled derived.
            theirs = "non-compliant"
            trow = {"ticker": ticker, "verdict": "non-compliant",
                    "verdict_raw": "not an EGX33 constituent (derived "
                                   "from the complete frozen list)"}
        if ours == "insufficient-data":
            outcome = "our-insufficient-data"
            counts["our_insufficient_data"] += 1
        elif theirs == "not-covered":
            outcome = "not-covered-by-source"
            counts["not_covered_by_source"] += 1
        elif theirs == "doubtful":
            outcome = "their-indeterminate"
            counts["their_indeterminate"] += 1
        elif ours == theirs:
            outcome = "agree"
            counts["agree"] += 1
        elif ours == "compliant":
            outcome = "disagree"
            counts["we_compliant_they_non_compliant"] += 1
        else:
            outcome = "disagree"
            counts["we_noncompliant_they_compliant"] += 1
        rows.append({
            "ticker": ticker,
            "ours": our_row.get("verdict"),
            "ours_normalized": ours,
            "theirs": (trow or {}).get("verdict"),
            "theirs_raw": (trow or {}).get("verdict_raw"),
            "outcome": ("disagree-we-compliant-they-non-compliant"
                        if outcome == "disagree" and ours == "compliant"
                        else "disagree-we-noncompliant-they-compliant"
                        if outcome == "disagree" else outcome),
            "explanation": explain_row(our_row, trow,
                                       "our-insufficient-data"
                                       if outcome == "our-insufficient-data"
                                       else outcome),
            "our_missing_inputs": our_row.get("missing_inputs"),
            "their_published_ratios": (trow or {}).get("published_ratios"),
        })
    determinate = (counts["agree"]
                   + counts["we_compliant_they_non_compliant"]
                   + counts["we_noncompliant_they_compliant"])
    return {
        "counts": counts,
        "determinate_pairs": determinate,
        "agreement_pct": (round(100.0 * counts["agree"] / determinate, 2)
                          if determinate else None),
        "rows": rows,
    }


def purification_stats(pairs):
    """pairs: [{ticker, ours, theirs}] with both sides numeric.
    Returns summary error statistics (ratios as fractions)."""
    if not pairs:
        return {"n_pairs": 0, "mean_abs_diff": None, "max_abs_diff": None,
                "mean_rel_diff": None, "pairs": []}
    diffs = [abs(p["ours"] - p["theirs"]) for p in pairs]
    rel = [d / abs(p["theirs"]) for d, p in zip(diffs, pairs)
           if p["theirs"]]
    return {
        "n_pairs": len(pairs),
        "mean_abs_diff": round(sum(diffs) / len(diffs), 6),
        "max_abs_diff": round(max(diffs), 6),
        "mean_rel_diff": (round(sum(rel) / len(rel), 6) if rel else None),
        "pairs": pairs,
    }


def purification_comparison(our_aaoifi_rows, snapshots):
    """Our AAOIFI purification ratio vs published per-stock figures."""
    published = {}  # ticker -> [{source, ratio, note}]
    ost = snapshots.get("ostool") or {}
    for r in ost.get("rows") or []:
        pr = r.get("published_ratios") or {}
        if pr.get("prohibited_income_pct") is not None:
            published.setdefault(r["ticker"], []).append({
                "source": "ostool",
                "ratio": pr["prohibited_income_pct"] / 100.0,
                "published_pct": pr["prohibited_income_pct"],
                "basis": "Ostool's published prohibited-income % — the "
                         "non-compliant revenue share that AAOIFI-style "
                         "purification applies to dividends."})
    pairs, awaiting = [], []
    for ticker, our_row in sorted(our_aaoifi_rows.items()):
        ours = (our_row.get("purification") or {}).get("ratio")
        for pub in published.get(ticker, []):
            if ours is None:
                awaiting.append({"ticker": ticker, **pub, "ours": None,
                                 "note": "Our purification ratio is not "
                                         "computable yet (engine verdict "
                                         "insufficient-data); the "
                                         "published figure is recorded "
                                         "for the first scored run."})
            else:
                pairs.append({"ticker": ticker, "source": pub["source"],
                              "ours": ours, "theirs": pub["ratio"]})
    return {"stats": purification_stats(pairs), "awaiting_our_inputs": awaiting,
            "witnesses_unavailable": [
                {"source": s, "reason": (snapshots.get(s) or {}).get(
                    "unavailable_reason") or
                 (snapshots.get(s) or {}).get("rows", [{}])[0].get(
                     "purification_note")}
                for s in ("musaffa", "nour_borsa") if snapshots.get(s)]}


RATIO_LABELS = {"interest_deposits_pct": "interest-bearing deposits",
                "interest_loans_pct": "interest-bearing loans",
                "liquid_assets_pct": "liquid assets",
                "prohibited_income_pct": "prohibited income"}


def driver_hypothesis_ostool(row):
    """Read POUL-style drivers straight off Ostool's published ratios
    vs the EGX33 limits — labelled hypothesis, never our verdict."""
    pr = row.get("published_ratios") or {}
    fails = [f"{RATIO_LABELS.get(k, k)} {v}% > limit {EGX33_LIMITS[k]}%"
             for k, v in pr.items()
             if v is not None and v > EGX33_LIMITS[k]]
    if not fails:
        return None
    return ("Hypothesis (not our engine's computation): on Ostool's own "
            "published percentages, this ticker breaches the EGX33 "
            "limits on " + "; ".join(fails) +
            ". If our input pipeline (issues #78/#110) lands equivalent "
            "financials, our EGX33 screen would be expected to reach "
            "the same verdict. Our engine has NOT computed this — its "
            "verdict today is insufficient-data.")


COMPARISONS = [
    ("musaffa", "aaoifi-avg36m", "AAOIFI (avg36m)"),
    ("faisal", "aaoifi-spot", "AAOIFI (spot)"),
    ("ostool", "egx33", "EGX33"),
    ("egx33", "egx33", "EGX33"),
]


def load_snapshots():
    snaps = {}
    if os.path.isdir(SOURCES_DIR):
        for name in sorted(os.listdir(SOURCES_DIR)):
            if name.endswith(".json"):
                with open(os.path.join(SOURCES_DIR, name),
                          encoding="utf-8") as f:
                    doc = json.load(f)
                snaps[doc["source_id"]] = doc
    return snaps


def score():
    snapshots = load_snapshots()
    ours = our_verdicts()
    comparisons = []
    for source_id, cfg, std_label in COMPARISONS:
        snap = snapshots.get(source_id)
        entry = {"source_id": source_id, "our_config": cfg,
                 "standard": std_label,
                 "source_status": (snap or {}).get("status", "missing"),
                 "source_document_date": (snap or {}).get("document_date"),
                 "source_retrieved_at": (snap or {}).get("retrieved_at")}
        if snap is None:
            entry["note"] = "No frozen snapshot for this source."
        elif snap["status"] != "ok":
            entry["note"] = ("Source unavailable at freeze time: "
                             + (snap.get("unavailable_reason") or ""))
        else:
            entry.update(compare(ours[cfg], snap))
            for row in entry["rows"]:
                if source_id == "ostool":
                    trow = {r["ticker"]: r for r in snap["rows"]}.get(
                        row["ticker"])
                    if trow:
                        hyp = driver_hypothesis_ostool(trow)
                        if hyp:
                            row["driver_hypothesis"] = hyp
        comparisons.append(entry)
    purif = purification_comparison(ours["aaoifi-avg36m"], snapshots)
    universe = load_universe()
    report = {
        "benchmark": "sharia-accuracy-benchmark",
        "issue": 172,
        "generated_at": now_iso(),
        "report_date": today_cairo(),
        "engine_version": sharia_engine.ENGINE_VERSION,
        "covered_universe": [s["ticker"] for s in universe],
        "framing_en": FRAMING_EN,
        "framing_ar": FRAMING_AR,
        "method_notes": [
            "Scored against frozen snapshots in sharia/benchmark/"
            "sources/ (per-row source URL + retrieval date), never "
            "against a moving page.",
            "Our verdicts are re-computed by the engine from the "
            "covered-universe inputs at score time, per comparison "
            "configuration (AAOIFI avg36m / AAOIFI spot / EGX33).",
            "insufficient-data on our side is its own bucket, never "
            "agreement or disagreement; agreement % is null when "
            "there are no determinate pairs.",
            "No accuracy claim is made from this benchmark (issues "
            "#77/#79 rule): with the covered universe at one ticker "
            "and its balance-sheet inputs not yet wired (issues "
            "#78/#110), every comparison currently lands in the "
            "insufficient-data bucket — that IS the measured result.",
        ],
        "comparisons": comparisons,
        "purification": purif,
    }
    return report


def render_md(report):
    lines = []
    lines.append("# Sharia accuracy benchmark — first run "
                 f"({report['report_date']})")
    lines.append("")
    lines.append(f"> {report['framing_en']}")
    lines.append(f"> {report['framing_ar']}")
    lines.append("")
    lines.append("Issue #172. Our Sharia engine (per-standard screening "
                 "results) scored against the published classifications "
                 "of Musaffa (AAOIFI), Faisal Securities (AAOIFI, spot "
                 "market cap), Ostool (EGX33) and EGX33 index membership "
                 "(ground truth), plus a purification comparison.")
    lines.append("")
    lines.append(f"Covered universe: {', '.join(report['covered_universe'])}"
                 f" · Engine version: {report['engine_version']} · "
                 f"Generated: {report['generated_at']}")
    lines.append("")
    lines.append("## Verdict agreement")
    lines.append("")
    lines.append("| Source — standard | Status | Universe tickers | "
                 "Determinate pairs | Agreement | Our insufficient-data |")
    lines.append("|---|---|---|---|---|---|")
    for c in report["comparisons"]:
        counts = c.get("counts") or {}
        lines.append(
            f"| {c['source_id']} — {c['standard']} | {c['source_status']} "
            f"| {len(report['covered_universe'])} "
            f"| {c.get('determinate_pairs', '—')} "
            f"| {('—' if c.get('agreement_pct') is None else str(c['agreement_pct']) + '%')} "
            f"| {counts.get('our_insufficient_data', '—')} |")
    lines.append("")
    lines.append("Agreement % is shown as — wherever there are no "
                 "determinate pairs: a percentage over zero pairs would "
                 "be a fabricated accuracy figure.")
    lines.append("")
    lines.append("## Per-ticker rows")
    for c in report["comparisons"]:
        lines.append("")
        lines.append(f"### {c['source_id']} — {c['standard']}")
        if c.get("note"):
            lines.append("")
            lines.append(c["note"])
        for row in c.get("rows") or []:
            lines.append("")
            lines.append(f"- **{row['ticker']}** — ours: `{row['ours']}` · "
                         f"theirs: `{row['theirs']}` ({row['theirs_raw']}) "
                         f"· outcome: `{row['outcome']}`")
            lines.append(f"  {row['explanation']}")
            if row.get("driver_hypothesis"):
                lines.append(f"  {row['driver_hypothesis']}")
    lines.append("")
    lines.append("## Purification comparison")
    lines.append("")
    st = report["purification"]["stats"]
    lines.append(f"Comparable pairs: {st['n_pairs']} · mean abs diff: "
                 f"{st['mean_abs_diff']} · max abs diff: "
                 f"{st['max_abs_diff']} · mean rel diff: "
                 f"{st['mean_rel_diff']}")
    for a in report["purification"]["awaiting_our_inputs"]:
        lines.append(f"- {a['ticker']} — {a['source']} publishes "
                     f"{a['published_pct']}% ({a['basis']}) {a['note']}")
    for w in report["purification"]["witnesses_unavailable"]:
        lines.append(f"- Witness {w['source']}: {w['reason']}")
    lines.append("")
    lines.append("## Method notes")
    lines.append("")
    for n in report["method_notes"]:
        lines.append(f"- {n}")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------- main

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    fz = sub.add_parser("freeze")
    fz.add_argument("--sources", default=",".join(FREEZERS))
    fz.add_argument("--mark-unavailable", choices=sorted(SOURCE_META))
    fz.add_argument("--reason", default="")
    sub.add_parser("score")
    args = ap.parse_args(argv)

    if args.cmd == "freeze":
        os.makedirs(SOURCES_DIR, exist_ok=True)
        if args.mark_unavailable:
            snap = mark_unavailable(args.mark_unavailable, args.reason)
            path = os.path.join(SOURCES_DIR, f"{args.mark_unavailable}.json")
            write_json(path, snap)
            print(f"{args.mark_unavailable}: unavailable -> {path}")
            return 0
        for source_id in args.sources.split(","):
            source_id = source_id.strip()
            snap = FREEZERS[source_id]()
            path = os.path.join(SOURCES_DIR, f"{source_id}.json")
            write_json(path, snap)
            print(f"{source_id}: {snap['status']}, "
                  f"{len(snap.get('rows') or [])} rows -> {path}")
        return 0

    if args.cmd == "score":
        report = score()
        base = os.path.join(BENCH_DIR, f"benchmark-{report['report_date']}")
        write_json(base + ".json", report)
        with open(base + ".md", "w", encoding="utf-8") as f:
            f.write(render_md(report))
        print(f"report -> {base}.json / {base}.md")
        for c in report["comparisons"]:
            print(f"  {c['source_id']} ({c['standard']}): "
                  f"status={c['source_status']} "
                  f"determinate={c.get('determinate_pairs')} "
                  f"agreement={c.get('agreement_pct')}")
        print(f"  purification pairs: "
              f"{report['purification']['stats']['n_pairs']}")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
