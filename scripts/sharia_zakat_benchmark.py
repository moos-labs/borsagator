#!/usr/bin/env python3
"""Borsagator zakat-calculator accuracy benchmark (issue #173).

Runs the stored worked cases of the zakat calculator
(scripts/sharia_zakat.py, methods declared in
scripts/sharia_zakat_methods/) against the published
calculators and worked examples named in the issue, and
records every divergence with its explanation:

  Kashif trader-zakat calculator (kasheif.com)
      -> the issue's named benchmark for the TRADING method
  Borsa Halal zakat calculator (borsahalal.com/faq)
      -> the issue's named benchmark for both methods
  Tedawal guide (published worked example, TRADING)
      -> 200,000 SAR market value -> 5,000 SAR; nisab
         85 g x 290 SAR = 24,650 SAR
  AskZakariya (published worked example, TRADING)
      -> 9,200 + 2,375 + 180 unspent dividends = 11,755
         -> 293.88
  Almurakib (published formulas for both intents)
  NZF 25% proxy / ZakatCalc 30% proxy (INVESTMENT estimation
  proxies, priced against the actuals method on a worked
  case)

Freeze discipline (shared with issue #172): each source's
published material is snapshotted ONCE into
sharia/zakat-benchmark/sources/ with the source URL and
retrieval date on every row; scoring runs against the frozen
snapshots -- never against a moving page. Re-freeze
deliberately when a source republishes; re-score whenever a
method or a worked case changes.

Honesty rules (binding, same as issue #172):
- A source whose calculator or worked example cannot be run
  or read publicly is recorded as status "unavailable" with
  what was tried -- never fabricated, never scraped behind a
  login, and an interactive calculator this runner cannot
  operate is recorded as such, not simulated.
- A numeric mismatch on a like-for-like case beyond the
  source's own published rounding is recorded as a DEFECT in
  our implementation, not explained away.
- Every other divergence is explained by a named method
  difference, or marked "unexplained".
- Nisab is a wealth-level test (published guidance judges it
  on all of the owner's zakatable wealth together), so the
  AskZakariya comparison aggregates the two holdings' bases
  before applying it -- exactly as the published example
  does. The per-holding calculator results stand as computed.

Framing (binding): every output is a calculation under a
named published method -- never a fatwa and never religious
or investment advice. No user-facing accuracy claim ships
off the back of this benchmark (issues #77 / #79 rules).

The calculator itself stays offline; only this tool's freeze
step touches the network (urllib, public pages only).
Scoring is pure stdlib and re-runnable offline against the
frozen snapshots and raw cache.

Usage:
  python3 scripts/sharia_zakat_benchmark.py freeze
  python3 scripts/sharia_zakat_benchmark.py score
"""
import argparse
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import sharia_zakat as zk  # noqa: E402

BENCH_DIR = os.path.join(ROOT, "sharia", "zakat-benchmark")
SOURCES_DIR = os.path.join(BENCH_DIR, "sources")
RAW_DIR = os.path.join(BENCH_DIR, "raw")
CASES_FILE = os.path.join(
    HERE, "sharia_zakat_fixtures", "worked_cases.json")

FRAMING_EN = zk.FRAMING_EN
FRAMING_AR = zk.FRAMING_AR

UA = ("Mozilla/5.0 (X11; Linux x86_64) "
      "borsagator-sharia-benchmark/1.0")

TEDAWAL_URL = ("https://www.tedawal.com/%d8%ad%d8%b3%d8%a7%d8%a8-"
               "%d8%b2%d9%83%d8%a7%d8%a9-%d8%a7%d9%84%d8%a3%d8%b3"
               "%d9%87%d9%85/")
ASKZAKARIYA_URL = ("https://askzakariya.com/islamic-finance/"
                   "zakat-on-stocks/")
ALMURAKIB_URL = ("https://almurakib.com/%D8%AD%D8%A7%D8%B3%D8%A8"
                 "%D8%A9-%D8%B2%D9%83%D8%A7%D8%A9-%D8%A7%D9%84"
                 "%D8%A3%D8%B3%D9%87%D9%85-%D9%88-%D8%B7%D8%B1"
                 "%D9%8A%D9%82%D8%A9-%D8%A7%D9%84%D8%AD%D8%B3"
                 "%D8%A7%D8%A8/")
ZAKATCALC_URL = "https://www.zakatcalc.info/"
AMAL_URL = "https://amalinvest.com/zakat-calculator"
KASHIF_URL = "https://kasheif.com/"
BORSA_HALAL_URL = "https://www.borsahalal.com/faq"


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def today_cairo():
    return (datetime.now(timezone.utc)
            + timedelta(hours=2)).strftime("%Y-%m-%d")


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", "replace")


def strip_text(html):
    t = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>",
               " ", html)
    t = re.sub(r"<[^>]+>", " ", t)
    t = (t.replace("&mdash;", "—").replace("&rsquo;", "’")
         .replace("&times;", "×").replace("&nbsp;", " "))
    return re.sub(r"\s+", " ", t)


def _num(s):
    return float(s.replace(",", ""))


def _write_snapshot(source_id, snapshot):
    os.makedirs(SOURCES_DIR, exist_ok=True)
    path = os.path.join(SOURCES_DIR, source_id + ".json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(snapshot, fh, ensure_ascii=False, indent=2,
                  sort_keys=True)
        fh.write("\n")
    return path


def _save_raw(name, content):
    os.makedirs(RAW_DIR, exist_ok=True)
    path = os.path.join(RAW_DIR, name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return path


def _base_snapshot(source_id, label, url):
    return {"source_id": source_id, "label": label,
            "source_url": url, "retrieved_at": now_iso(),
            "framing_en": FRAMING_EN, "framing_ar": FRAMING_AR,
            "status": "ok", "rows": [], "attempts": [],
            "method_note": None}


# ------------------------------------------------------- parsers
# Each parser works on the stripped text of the committed raw
# page, so the tests exercise exactly what score consumes.

def parse_tedawal(text):
    m = re.search(r"([\d,]+) × 2\.5% = ([\d,]+)", text)
    if not m:
        return None
    row = {"kind": "worked_example", "method": "TRADING",
           "market_value": _num(m.group(1)),
           "rate": 0.025, "published_zakat": _num(m.group(2)),
           "currency": "SAR"}
    n = re.search(r"85 × ([\d,]+) = ([\d,]+)", text)
    if n:
        row["nisab_gold_price_per_gram"] = _num(n.group(1))
        row["nisab_value"] = _num(n.group(2))
        row["nisab_grams"] = 85
    return row


def parse_askzakariya(text):
    def grab(pattern):
        m = re.search(pattern, text)
        return _num(m.group(1)) if m else None
    row = {"kind": "worked_example", "method": "TRADING",
           "currency": "USD",
           "components": {
               "aapl_market_value": grab(
                   r"AAPL @ \$230[^$]*\$([\d,]+)"),
               "spus_market_value": grab(
                   r"SPUS @ \$95[^$]*\$([\d,]+)"),
               "dividends_received_unspent": grab(
                   r"Dividends received \(cash, unspent\)"
                   r"[^$]*\$([\d,]+)")},
           "published_total_base": grab(
               r"Total zakatable stock wealth[^$]*\$([\d,]+)"),
           "published_zakat": grab(
               r"Zakat due \(2\.5%\)[^$]*\$([\d.]+)")}
    if any(v is None for v in row["components"].values()) \
            or row["published_total_base"] is None \
            or row["published_zakat"] is None:
        return None
    return row


def parse_almurakib(text):
    formulas = re.findall(r"المعادلة = \(([^)]+)\)", text)
    if len(formulas) < 2:
        return None
    return {"kind": "published_formulas",
            "trading_formula_ar": formulas[0],
            "investment_formula_ar": formulas[1],
            "nisab_grams_gold": 85 if "85 جرام" in text
            else None,
            "hawl_required": "عام هجري كامل" in text,
            "rate": 0.025}


def parse_zakatcalc(text):
    m = re.search(r"(\d+)% proxy method", text)
    if not m or "AAOIFI Standard 35 proxy" not in text:
        return None
    return {"kind": "estimation_proxy", "method": "INVESTMENT",
            "proxy_pct": _num(m.group(1)) / 100.0,
            "basis": "market value",
            "standard": "AAOIFI Standard 35 (proxy)"}


def parse_amal_nzf(text):
    m = re.search(r"NZF suggests using (\d+)% of the market "
                  r"value", text)
    if not m:
        return None
    return {"kind": "estimation_proxy", "method": "INVESTMENT",
            "proxy_pct": _num(m.group(1)) / 100.0,
            "basis": "market value",
            "standard": "AAOIFI Standard 35 via NZF proxy paper",
            "components_phrase_present":
                "cash, money owed to it and stock for sale"
                in text,
            "gregorian_rate_present": "2.577%" in text}


# ------------------------------------------------------- freeze

def _freeze_page(source_id, label, url, raw_name, parser,
                 note=None):
    snap = _base_snapshot(source_id, label, url)
    try:
        html = fetch(url)
    except Exception as e:  # network/HTTP failure: record it
        snap["status"] = "unavailable"
        snap["attempts"] = ["GET %s -> %s: %s"
                            % (url, type(e).__name__, e)]
        _write_snapshot(source_id, snap)
        print("%s: unavailable (fetch failed)" % source_id)
        return snap
    _save_raw(raw_name, html)
    row = parser(strip_text(html))
    if row is None:
        snap["status"] = "unavailable"
        snap["attempts"] = [
            "GET %s succeeded and the raw page is cached, but "
            "the published figures this benchmark parses were "
            "not found in it" % url]
    else:
        row["source_url"] = url
        row["retrieved_at"] = snap["retrieved_at"]
        snap["rows"] = [row]
    snap["method_note"] = note
    _write_snapshot(source_id, snap)
    print("%s: %s" % (source_id, snap["status"]))
    return snap


def freeze_kashif():
    snap = _base_snapshot(
        "kashif", "Kashif — trader-zakat calculator "
        "(kasheif.com)", KASHIF_URL)
    try:
        html = fetch(KASHIF_URL)
        _save_raw("kashif-home.html", html)
        reachable = True
    except Exception as e:
        reachable = False
        snap["attempts"].append("GET %s -> %s: %s"
                                % (KASHIF_URL,
                                   type(e).__name__, e))
    snap["status"] = "unavailable"
    snap["attempts"].append(
        "The kasheif.com homepage %s reachable and is cached "
        "raw; its tools section names calculators, and Kashif's "
        "FAQ (read live in this series' 2026-11-17 source "
        "research) states a trader-zakat calculator is offered. "
        "The calculator itself is an interactive web tool: this "
        "runner cannot operate interactive tools, and no worked "
        "example or text formula for the trader calculator is "
        "published on the pages read -- so no like-for-like "
        "numeric comparison could be run. Recorded, not "
        "simulated." % ("was" if reachable else "was not"))
    snap["method_note"] = (
        "Kashif's trader zakat is the TRADING method family "
        "(trade goods at market value); with no published "
        "worked example, the numeric witnesses for that method "
        "in this run are Tedawal and AskZakariya.")
    _write_snapshot("kashif", snap)
    print("kashif: unavailable (interactive calculator, no "
          "published worked example)")
    return snap


def freeze_borsa_halal():
    snap = _base_snapshot(
        "borsa_halal", "Borsa Halal — zakat calculator "
        "(borsahalal.com/faq)", BORSA_HALAL_URL)
    snap["status"] = "unavailable"
    snap["attempts"] = [
        "GET %s via the browser reader (2026-11-18): the page "
        "returned no extractable content." % BORSA_HALAL_URL,
        "The same FAQ was read live in this series' 2026-11-17 "
        "source research: it states the platform offers "
        "purification and zakat calculators under AAOIFI and "
        "S&P Shariah standards, and publishes no numeric "
        "thresholds and no worked zakat example.",
        "Not re-attempted by this freeze: two reads are on "
        "record and a third automated attempt would add no "
        "information. The calculator itself is interactive "
        "and, per the earlier research, its stock pages sit "
        "behind a login this benchmark never uses."]
    snap["method_note"] = (
        "No published worked example exists to compare "
        "against; recorded as unavailable rather than "
        "simulated.")
    _write_snapshot("borsa_halal", snap)
    print("borsa_halal: unavailable (no published worked "
          "example; calculator interactive)")
    return snap


def freeze():
    _freeze_page("tedawal", "Tedawal — zakat on stocks guide "
                 "(published worked example)", TEDAWAL_URL,
                 "tedawal.html", parse_tedawal)
    _freeze_page("askzakariya", "AskZakariya — Zakat on "
                 "Stocks (published worked example)",
                 ASKZAKARIYA_URL, "askzakariya.html",
                 parse_askzakariya)
    _freeze_page("almurakib", "Almurakib — stock zakat "
                 "calculator page (published formulas)",
                 ALMURAKIB_URL, "almurakib.html",
                 parse_almurakib)
    _freeze_page("zakatcalc", "ZakatCalc — long-term shares "
                 "AAOIFI proxy", ZAKATCALC_URL,
                 "zakatcalc.html", parse_zakatcalc)
    _freeze_page("amal_nzf", "Amal Invest / National Zakat "
                 "Foundation — AAOIFI Std 35 method + NZF "
                 "25% proxy", AMAL_URL, "amal-nzf.html",
                 parse_amal_nzf)
    freeze_kashif()
    freeze_borsa_halal()


# ------------------------------------------------------- score

def _load_snapshot(source_id):
    path = os.path.join(SOURCES_DIR, source_id + ".json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _load_cases():
    with open(CASES_FILE, encoding="utf-8") as fh:
        data = json.load(fh)
    out = {}
    for entry in data["cases"]:
        case = dict(entry["case"])
        ref = case.pop("snapshot_ref", None)
        if ref is not None:
            case["snapshot"] = data["snapshots"][ref]
        out[entry["id"]] = (case, entry["expected"])
    return out


def _delta(ours, published):
    return round(ours - published, 6)


def score():
    cases = _load_cases()
    comparisons = []

    # Internal correctness gate: every stored worked case
    # reproduces from its stored inputs.
    gate_ok, gate_total = 0, 0
    for case_id, (case, expected) in sorted(cases.items()):
        gate_total += 1
        r = zk.calculate(case)
        if r["status"] == expected["status"] \
                and r["zakat"] == expected["zakat"]:
            gate_ok += 1

    # --- Tedawal: like-for-like TRADING worked example
    snap = _load_snapshot("tedawal")
    if snap and snap["status"] == "ok":
        row = snap["rows"][0]
        r = zk.calculate(cases["tedawal-trading-200k"][0])
        d = _delta(r["zakat"], row["published_zakat"])
        comparisons.append({
            "source": "tedawal", "case": "tedawal-trading-200k",
            "kind": "numeric",
            "ours": r["zakat"],
            "published": row["published_zakat"],
            "delta": d,
            "verdict": "matched" if abs(d) <= 0.01
            else "defect",
            "explanation_en":
                "Identical method and inputs: market value "
                "200,000 SAR x 2.5%, nisab 24,650 SAR (85 g x "
                "290) below the base." if abs(d) <= 0.01 else
                "Numeric mismatch on a like-for-like case "
                "beyond rounding: recorded as a defect in our "
                "implementation.",
            "source_url": row["source_url"]})
    else:
        comparisons.append({"source": "tedawal",
                            "kind": "numeric",
                            "verdict": "unavailable",
                            "explanation_en": "Source snapshot "
                            "unavailable; see its attempts."})

    # --- AskZakariya: aggregate the two holdings, as the
    # published example does (nisab is a wealth-level test).
    snap = _load_snapshot("askzakariya")
    if snap and snap["status"] == "ok":
        row = snap["rows"][0]
        ra = zk.calculate(
            cases["askzakariya-aapl-with-dividends"][0])
        rs = zk.calculate(
            cases["askzakariya-spus-alone-below-nisab"][0])
        combined_base = round(
            ra["base"]["total"] + rs["base"]["total"], 6)
        rate = zk.load_method("TRADING")["rates"]["lunar"]
        ours = round(combined_base * rate, 6)
        d = _delta(ours, row["published_zakat"])
        comparisons.append({
            "source": "askzakariya",
            "case": "askzakariya aggregate (AAPL + SPUS + "
                    "unspent dividends)",
            "kind": "numeric",
            "ours": ours, "published": row["published_zakat"],
            "delta": d,
            "verdict": "matched" if abs(d) <= 0.01
            else "defect",
            "explanation_en":
                "Combined base 9,380 + 2,375 = 11,755 "
                "reproduces the published total exactly; "
                "11,755 x 2.5% = 293.875 vs the published "
                "293.88 -- the 0.005 delta is the source's "
                "own rounding to 2 decimal places, not a "
                "method difference. Judged per holding, the "
                "SPUS case alone is below the declared nisab "
                "parameter (2,375 < 6,800) and returns 0: "
                "the nisab is a wealth-level test, which is "
                "why the comparison aggregates, as the "
                "published example does.",
            "source_url": row["source_url"]})
    else:
        comparisons.append({"source": "askzakariya",
                            "kind": "numeric",
                            "verdict": "unavailable",
                            "explanation_en": "Source snapshot "
                            "unavailable; see its attempts."})

    # --- Almurakib: published formulas, both intents
    snap = _load_snapshot("almurakib")
    if snap and snap["status"] == "ok":
        comparisons.append({
            "source": "almurakib", "kind": "formula",
            "case": "trading formula",
            "verdict": "explained-divergence",
            "explanation_en":
                "Almurakib's speculation base = market value "
                "+ realised profits - realised losses + "
                "available cash. The shared term (market "
                "value at the zakat day, nisab 85 g gold, "
                "full Hijri hawl, 2.5%) is identical to our "
                "TRADING method. Their extra terms are "
                "holder-level cash items, not share value: "
                "our calculator takes the holding plus "
                "declared held dividends, and the owner's "
                "other cash joins his zakat on his own zakat "
                "date. Input-scope difference, not an "
                "arithmetic difference.",
            "source_url": snap["source_url"]})
        comparisons.append({
            "source": "almurakib", "kind": "formula",
            "case": "investment formula",
            "verdict": "explained-divergence",
            "explanation_en":
                "Almurakib's investment formula, as "
                "published, sums market value + dividends "
                "(received and accrued) + sale cash. That "
                "contradicts the page's own note ('the full "
                "market value is NOT zakat-ed as in "
                "speculation; the dividends are') and "
                "matches neither our INVESTMENT method "
                "(AAOIFI Std 35 zakatable assets per share) "
                "nor the yield-only position. Recorded as "
                "published and flagged as an internal "
                "inconsistency in the source; not followed "
                "and not silently 'corrected'.",
            "source_url": snap["source_url"]})
    else:
        comparisons.append({"source": "almurakib",
                            "kind": "formula",
                            "verdict": "unavailable",
                            "explanation_en": "Source snapshot "
                            "unavailable; see its attempts."})

    # --- Estimation proxies vs the actuals method (ACME case)
    acme_case, _ = cases["acme-investment-50k"]
    ours_r = zk.calculate(acme_case)
    proxy_price = 20.0  # declared benchmark parameter
    market_value = acme_case["shares"] * proxy_price
    for sid in ("amal_nzf", "zakatcalc"):
        snap = _load_snapshot(sid)
        if snap and snap["status"] == "ok":
            pct = snap["rows"][0]["proxy_pct"]
            proxy_zakat = round(market_value * pct
                                * ours_r["rate"], 6)
            comparisons.append({
                "source": sid, "kind": "numeric-proxy",
                "case": "acme-investment-50k at a declared "
                        "market price of 20.00/share "
                        "(market value 1,000,000)",
                "ours": ours_r["zakat"],
                "published": proxy_zakat,
                "delta": _delta(ours_r["zakat"], proxy_zakat),
                "verdict": "explained-divergence",
                "explanation_en":
                    "The %s%% figure is an ESTIMATION proxy "
                    "for this method's base, published for "
                    "when the per-share zakatable-assets "
                    "figure cannot be found (NZF's own "
                    "condition; AAOIFI Std 35 allows "
                    "estimation for shares, art. 4/2/4). "
                    "The ACME fixture carries the company's "
                    "actual figures, so our calculator "
                    "applies the method itself (base "
                    "400,000 -> 10,000) instead of estimating "
                    "it from market value. A proxy is not "
                    "the base; the delta prices the "
                    "estimation error the proxy accepts."
                    % int(pct * 100),
                "source_url": snap["source_url"]})
        else:
            comparisons.append({"source": sid,
                                "kind": "numeric-proxy",
                                "verdict": "unavailable",
                                "explanation_en": "Source "
                                "snapshot unavailable; see its "
                                "attempts."})

    # --- The issue's named calculators: unavailable, on record
    for sid in ("kashif", "borsa_halal"):
        snap = _load_snapshot(sid)
        comparisons.append({
            "source": sid, "kind": "numeric",
            "verdict": "unavailable",
            "explanation_en": (snap or {}).get("method_note")
            or "Unavailable; see the snapshot's attempts.",
            "attempts": (snap or {}).get("attempts", [])})

    report = {
        "schema": "borsagator-sharia-zakat-benchmark/1",
        "date": today_cairo(),
        "generated_at": now_iso(),
        "calculator": zk.CALCULATOR_PATH,
        "calculator_version": zk.CALCULATOR_VERSION,
        "framing_en": FRAMING_EN, "framing_ar": FRAMING_AR,
        "internal_gate": {"worked_cases_reproduced": gate_ok,
                          "worked_cases_total": gate_total},
        "comparisons": comparisons,
    }
    os.makedirs(BENCH_DIR, exist_ok=True)
    jpath = os.path.join(
        BENCH_DIR, "zakat-benchmark-%s.json" % report["date"])
    with open(jpath, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2,
                  sort_keys=True)
        fh.write("\n")
    mpath = os.path.join(
        BENCH_DIR, "zakat-benchmark-%s.md" % report["date"])
    with open(mpath, "w", encoding="utf-8") as fh:
        fh.write(render_md(report))
    print("gate: %d/%d worked cases reproduce"
          % (gate_ok, gate_total))
    for c in comparisons:
        print("%s [%s]: %s" % (c["source"], c["kind"],
                               c["verdict"]))
    print("wrote %s and %s" % (jpath, mpath))
    return report


def render_md(report):
    lines = [
        "# Zakat calculator benchmark — %s" % report["date"],
        "",
        "> %s" % report["framing_en"],
        ">",
        "> %s" % report["framing_ar"],
        "",
        "Internal correctness gate: **%d/%d** stored worked "
        "cases reproduce from their stored inputs."
        % (report["internal_gate"]["worked_cases_reproduced"],
           report["internal_gate"]["worked_cases_total"]),
        "",
        "| Source | Kind | Verdict | Ours | Published | "
        "Delta |",
        "|---|---|---|---:|---:|---:|",
    ]
    for c in report["comparisons"]:
        lines.append("| %s | %s | %s | %s | %s | %s |" % (
            c["source"], c["kind"], c["verdict"],
            c.get("ours", "—"), c.get("published", "—"),
            c.get("delta", "—")))
    lines += ["", "## Explanations", ""]
    for c in report["comparisons"]:
        lines.append("### %s — %s" % (c["source"], c["verdict"]))
        lines.append("")
        lines.append(c["explanation_en"])
        lines.append("")
        if c.get("attempts"):
            lines.append("Attempts on record:")
            for a in c["attempts"]:
                lines.append("- %s" % a)
            lines.append("")
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("freeze", help="snapshot the published "
                                  "sources (network step)")
    sub.add_parser("score", help="run the comparisons offline "
                                 "against the frozen snapshots")
    args = ap.parse_args(argv)
    if args.cmd == "freeze":
        freeze()
    else:
        score()
    return 0


if __name__ == "__main__":
    sys.exit(main())
