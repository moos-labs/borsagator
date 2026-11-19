#!/usr/bin/env python3
"""Proof harness for issue #109 (structured bilingual EGX disclosure
events, archive/shadow pilot).

Runs the extractor (``scripts/disclosure_events.py``, stdlib only) over
the golden fixtures (``scripts/disclosure_events_fixtures/fixtures.json``)
plus synthetic negatives, scores field-level precision/recall, checks
the verification-state split, proves the harness bites with a pristine
(naive) control and with gutted mutants, checks determinism, and runs
the shadow extraction over archived sweeps' news inputs with a legacy
``detect_corporate_actions`` comparison.

Usage:
    harness_issue109.py [--archive-root PATH] [--stage PATH]
    harness_issue109.py --pristine [--stage PATH]
    harness_issue109.py --mutate {role-swap,round2dp} [--stage PATH]

Archive root defaults to ``$BORSAGATOR_ARCHIVE_ROOT`` or the sibling
``borsagator-archive`` checkout. Stage defaults to
``$BORSAGATOR_HARNESS_STAGE`` or ``~/workspace/goals/
stock-analysis-tool-runners/hidden_files/109-harness-stage`` (the VM's
/tmp is a 512M tmpfs — never stage there).

Pristine control (--pristine): a naive extractor (first number near a
dividend word as a float amount, first date in the body as EVERY date,
no candidate state, no digit normalisation) is run through the
discriminating cases — it must FAIL golden_poul_dividend,
arabic_numerals, date_role_swap, clipped_amount,
golden_comi_earnings_consolidated and loss_earnings. If the naive
control passes any of them, the case does not test what it claims and
the harness exits 1.

Mutation (--mutate): the extractor is copied to the stage, gutted in
one place (role-swap: payout/ex labels exchanged; round2dp: decimal
strings rounded to 2dp), and the fixture suite is re-run against the
mutant. The mutant MUST fail (exit 1 with counted failures) or the
harness exits 1 — an untested core is not a proof.

Shadow run: the extractor runs over every archived sweep's
collected/news-disclosure/disclosures.json plus harvest/*.json in the
archive root, deduplicated by source document id. Archive reads only;
no Actions logs or artifacts. The pilot universe per #109 is top-30
EGX over the last quarter — the archive holds only POUL.CA + COMI.CA
EGX sweeps, so the report states the achieved coverage honestly
instead of inventing the missing 28 names.

Scorer checks (--scorer, also run in the default path): the #283
top-30 scorer's own cases (scripts/test_top30_scorer_283.py,
spec docs/top30-scoring.md) — swapped-date, sign, duplicate-reuse
and candidate-only negative controls plus positive/structural cases.
They score synthetic gold/predicted pairs and never touch the
archive, so they run identically with or without one.
"""
import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from decimal import Decimal

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
FIXTURES = os.path.join(HERE, "disclosure_events_fixtures",
                        "fixtures.json")
ARCHIVE_DEFAULT = os.environ.get(
    "BORSAGATOR_ARCHIVE_ROOT",
    os.path.join(os.path.dirname(REPO), "borsagator-archive"))
STAGE_DEFAULT = os.environ.get(
    "BORSAGATOR_HARNESS_STAGE",
    os.path.expanduser("~/workspace/goals/stock-analysis-tool-runners/"
                       "hidden_files/109-harness-stage"))

CHECKS = {"pass": 0, "fail": 0}
FAILURES = []
# Field-level scoring over the pilot set (Ins T9).
SCORE = {"tp": 0, "fp": 0, "fn": 0}
FIELD_SCORE = {}


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


def load_fixtures():
    with open(FIXTURES, encoding="utf-8") as f:
        return json.load(f)["cases"]


# --- field accessors: expected-key -> (event) -> value --------------------
def _get(ev, key):
    p = ev.get("payload", {})
    if key == "coupon":
        return p.get("coupon_number")
    if key == "amount":
        return p.get("amount_per_share", {}).get("value")
    if key in ("ex_date", "entitlement_end", "payout_date", "record_date"):
        return p.get(key, {}).get("value")
    if key == "record_derived_candidate":
        return p.get("record_date", {}).get("derived_candidate")
    if key == "announced":
        return ev.get("announced", {}).get("value")
    if key == "basis":
        return p.get("basis")
    if key in ("period_start", "period_end"):
        return p.get(key, {}).get("value")
    if key == "npat":
        return p.get("npat", {}).get("value")
    if key == "npat_scale":
        return p.get("npat", {}).get("scale")
    if key == "npat_comparative":
        return p.get("npat_comparative", {}).get("value")
    if key == "yoy":
        return p.get("yoy_npat_pct", {}).get("value")
    if key == "revenue":
        return p.get("revenue", {}).get("value")
    if key == "subtype":
        return ev.get("subtype")
    if key in ("assembly_date", "meeting_date"):
        return p.get(key, {}).get("value")
    if key == "assembly_time":
        return p.get("assembly_time")
    if key == "state":
        return p.get("state")
    if key == "status":
        return ev.get("extraction_status")
    if key == "verification":
        return ev.get("verification_status")
    if key == "stale":
        return ev.get("stale")
    raise KeyError(key)


SCORED_KEYS = ("coupon", "amount", "ex_date", "entitlement_end",
               "payout_date", "record_date", "record_derived_candidate",
               "announced", "basis", "period_start", "period_end",
               "npat", "npat_scale", "npat_comparative", "yoy", "revenue",
               "subtype", "assembly_date", "assembly_time", "state",
               "meeting_date", "status", "verification", "stale")


def score_case(name, expected, events, report=None):
    """Score one fixture case; returns True when every expectation
    holds. Field-level: a wrong predicted value is 1 FP + 1 FN."""
    ok = True
    n_exp = expected.get("n_events", 0)
    if len(events) != n_exp:
        # A missing event is FN, a spurious event is FP.
        if len(events) < n_exp:
            SCORE["fn"] += n_exp - len(events)
        else:
            SCORE["fp"] += len(events) - n_exp
        check("%s: n_events=%d" % (name, n_exp),
              len(events) == n_exp,
              "got %d" % len(events))
        ok = False
        if not events:
            return False
    if report is not None:
        for key in ("duplicate_documents", "duplicate_links"):
            if key in expected:
                check("%s: %s=%s" % (name, key, expected[key]),
                      report.get(key) == expected[key],
                      "got %s" % report.get(key))
                ok = ok and report.get(key) == expected[key]
    if not events:
        return ok
    ev = events[0]
    if "event_type" in expected:
        match = ev.get("event_type") == expected["event_type"]
        check("%s: event_type=%s" % (name, expected["event_type"]),
              match, "got %s" % ev.get("event_type"))
        ok = ok and match
    for key in SCORED_KEYS:
        if key not in expected:
            continue
        got = _get(ev, key)
        want = expected[key]
        fs = FIELD_SCORE.setdefault(key, {"tp": 0, "fp": 0, "fn": 0})
        if got == want:
            SCORE["tp"] += 1
            fs["tp"] += 1
        else:
            SCORE["fp"] += 1
            SCORE["fn"] += 1
            fs["fp"] += 1
            fs["fn"] += 1
            ok = False
        check("%s: %s=%s" % (name, key, want), got == want,
              "got %r" % (got,))
    return ok


def run_fixture_suite(mod, verbose=True):
    """The whole fixture suite against one extractor module."""
    cases = load_fixtures()
    for case in cases:
        exp = case["expected"]
        if case["kind"] == "feed":
            events, report = mod.extract_feed(case["doc"])
        else:
            events = mod.extract_document(case["doc"])
            report = None
        score_case(case["name"], exp, events, report)
    # Verification-state split over the extracted goldens.
    extracted = []
    for case in cases:
        if case["kind"] != "single":
            continue
        for ev in mod.extract_document(case["doc"]):
            extracted.append(ev)
    split = {}
    for ev in extracted:
        split[ev["verification_status"]] = \
            split.get(ev["verification_status"], 0) + 1
    if verbose:
        print("verification split over single-doc fixtures: %s" % split)
    return split


# --- pristine (naive) control ---------------------------------------------
def naive_extract(doc):
    """First number near a dividend word (float), first date in the
    body as every date, no candidate state, no digit normalisation."""
    import re as _re
    body = str(doc.get("body") or "")
    title = str(doc.get("title") or "")
    text = title + "\n" + body
    m = _re.search(r"(\d+(?:\.\d+)?)\s*(?:جنيه|EGP)", text)
    amount = float(m.group(1)) if m else None
    dates = _re.findall(r"(\d{1,2}/\d{1,2}/\d{4})", text)
    first = dates[0] if dates else None

    def _d(s):
        if not s:
            return None
        d, mo, y = s.split("/")
        return "%s-%s-%s" % (y, mo.zfill(2), d.zfill(2))
    ev = {"event_type": "dividend",
          "subtype": "cash_dividend",
          "announced": {"value": _d(first)},
          "extraction_status": "extracted",
          "verification_status": "verified",
          "stale": False,
          "payload": {
              "coupon_number": None,
              "amount_per_share": {"value": str(amount)
                                   if amount is not None else None},
              "ex_date": {"value": _d(first)},
              "entitlement_end": {"value": _d(first)},
              "payout_date": {"value": _d(first)},
              "record_date": {"value": _d(first),
                              "derived_candidate": None}}}
    cm = _re.search(r"رقم الكوبون\s*:?\s*(\d+)", text)
    ev["payload"]["coupon_number"] = cm.group(1) if cm else None
    return [ev]


DISCRIMINATING = ("golden_poul_dividend", "arabic_numerals",
                  "date_role_swap", "clipped_amount",
                  "golden_comi_earnings_consolidated", "loss_earnings")


def pristine_control():
    """The naive control must FAIL every discriminating case."""
    print("== pristine control (naive extractor) ==")
    cases = {c["name"]: c for c in load_fixtures()}
    naive = type("N", (), {"extract_document": staticmethod(naive_extract),
                           "extract_feed": staticmethod(
                               lambda docs: ([e for d in docs
                                             for e in naive_extract(d)],
                                             {}))})()
    for name in DISCRIMINATING:
        case = cases[name]
        if case["kind"] == "feed":
            events, report = naive.extract_feed(case["doc"])
        else:
            events = naive.extract_document(case["doc"])
            report = None
        # Scored quietly: the control's failures are expected and must
        # not pollute the real suite's precision/recall.
        exp = case["expected"]
        passed = True
        if len(events) != exp.get("n_events", 0):
            passed = False
        elif events:
            ev = events[0]
            if "event_type" in exp and \
                    ev.get("event_type") != exp["event_type"]:
                passed = False
            for key in SCORED_KEYS:
                if key in exp and _get(ev, key) != exp[key]:
                    passed = False
        check("pristine must FAIL %s" % name, not passed,
              "naive passed — case does not discriminate")


# --- mutations ---------------------------------------------------------------
MUTATIONS = {
    # Three steps with a sentinel: a plain pairwise replace would
    # swap the labels back (the first replacement creates a second
    # occurrence of the second label).
    "role-swap": (
        ("[r\"تاريخ التوزيع\", r\"distribution date\", r\"صرف الكوبون\"]",
         "[r\"__ROLE_SWAP_SENTINEL__\"]"),
        ("[r\"تاريخ تحريك الحدود السعرية\", r\"ex-date\", r\"ex date\"]",
         "[r\"تاريخ التوزيع\", r\"distribution date\", r\"صرف الكوبون\"]"),
        ("[r\"__ROLE_SWAP_SENTINEL__\"]",
         "[r\"تاريخ تحريك الحدود السعرية\", r\"ex-date\", r\"ex date\"]")),
    "round2dp": (
        ("    return format(d.normalize(), \"f\") if d == d.to_integral_value() \\\n"
         "        else format(d, \"f\")",
         "    return format(d.quantize(Decimal(\"0.01\"), rounding=ROUND_HALF_UP), \"f\")"),),
}


def run_mutant(kind, stage):
    print("== mutant: %s ==" % kind)
    src = os.path.join(REPO, "scripts", "disclosure_events.py")
    staged = os.path.join(stage, "disclosure_events_mutant.py")
    os.makedirs(stage, exist_ok=True)
    text = open(src, encoding="utf-8").read()
    for old, new in MUTATIONS[kind]:
        assert old in text, "mutation anchor missing: %s" % old[:60]
        text = text.replace(old, new, 1)
    with open(staged, "w", encoding="utf-8") as f:
        f.write(text)
    mod = load_module(staged, "disclosure_events_mutant")
    before_fail = CHECKS["fail"]
    run_fixture_suite(mod, verbose=False)
    killed = CHECKS["fail"] > before_fail
    print("mutant %s: %s (%d new failures)"
          % (kind, "KILLED" if killed else "SURVIVED",
             CHECKS["fail"] - before_fail))
    return killed


# --- #283 top-30 scorer checks ---------------------------------------------
def scorer_checks():
    """The #283 scorer's cases (docs/top30-scoring.md), folded into
    this harness's CHECKS so one harness run proves both the pilot
    extractor and the top-30 scorer. Synthetic gold/predicted pairs
    only — no archive, no network, no SCORE pollution."""
    print("== scorer checks (#283) ==")
    sys.path.insert(0, HERE)
    import test_top30_scorer_283 as t283
    for name, fn in t283.CASES:
        try:
            ok, detail = fn()
        except Exception as e:  # a crashing case is a failed case
            ok, detail = False, "raised %r" % (e,)
        check("scorer-283: %s" % name, ok, detail)


# --- determinism ---------------------------------------------------------------
def determinism(stage):
    print("== determinism ==")
    feed = os.path.join(stage, "determinism-feed.json")
    cases = load_fixtures()
    docs = [c["doc"] for c in cases if c["kind"] == "single"]
    with open(feed, "w", encoding="utf-8") as f:
        json.dump({"items": docs}, f, ensure_ascii=False)
    outs = []
    for seed, tz in (("0", "UTC"), ("42", "Africa/Cairo")):
        env = dict(os.environ, PYTHONHASHSEED=seed, TZ=tz)
        proc = subprocess.run(
            [sys.executable, os.path.join(REPO, "scripts",
                                          "disclosure_events.py"),
             "extract", feed, "--out",
             os.path.join(stage, "determinism-%s.json" % seed)],
            capture_output=True, text=True, env=env, timeout=120)
        assert proc.returncode == 0, proc.stderr
        outs.append(open(os.path.join(stage, "determinism-%s.json" % seed),
                         "rb").read())
    check("determinism: byte-identical events across hash seed/TZ",
          outs[0] == outs[1])


# --- shadow run over archived sweeps -------------------------------------------
def _parse_item_date(s):
    import datetime as _dt
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%SZ", "%a, %d %b %Y %H:%M:%S %Z"):
        try:
            return _dt.datetime.strptime(str(s)[:10], "%Y-%m-%d").date() \
                if fmt == "%Y-%m-%d" else \
                _dt.datetime.strptime(str(s), fmt).date()
        except Exception:
            continue
    return None


def shadow_run(mod, archive_root, stage):
    """Extractor over every archived sweep's news inputs + harvests,
    with the legacy dividend detector as the comparison (shadow only)."""
    print("== shadow run: %s ==" % archive_root)
    import glob as _glob
    from datetime import date as _date
    seen, items = {}, []
    for path in sorted(_glob.glob(os.path.join(
            archive_root, "sweeps", "*", "*",
            "collected", "news-disclosure", "disclosures.json"))):
        try:
            data = json.load(open(path, encoding="utf-8"))
        except Exception:
            continue
        for it in data.get("items", []):
            # Dedup by the extractor's own document id (egx:NewsID):
            # the same disclosure is re-attached by every sweep, and
            # the harvest copy and the sweep copy carry the id in
            # different fields (id vs URL).
            key = mod._doc_id(it)
            if key not in seen:
                seen[key] = True
                items.append(it)
    harvest_items = 0
    for path in sorted(_glob.glob(os.path.join(
            archive_root, "harvest", "*.json"))):
        try:
            data = json.load(open(path, encoding="utf-8"))
        except Exception:
            continue
        for it in data.get("items", []):
            key = mod._doc_id(it)
            if key not in seen:
                seen[key] = True
                items.append(it)
                harvest_items += 1
    egx = [it for it in items
           if "egx.com.eg" in (it.get("url") or "")]
    qs, qe = mod.QUARTER_START, mod.QUARTER_END
    # Window by ANNOUNCED date as the extractor derives it (standalone
    # date line in the body), not by the harvester's item date: the
    # harvester iso_date bug stamps COMI 297291/297289 as 2026-01-01
    # (it read the period start), while their bodies announce
    # 10/11/2026. Items with no extractable announced date fall back
    # to the item date.
    in_window, out_window, undated = [], [], []

    def _doc_announced(it):
        raw = str(it.get("title") or "") + "\n" + str(it.get("body") or "")
        val, _, _, _ = mod._announced(mod.norm_digits(raw), raw,
                                      it.get("date"))
        if val:
            return val
        return _parse_item_date(it.get("date"))

    for it in egx:
        d = _doc_announced(it)
        if d is None:
            undated.append(it)
        elif qs <= d <= qe:
            in_window.append(it)
        else:
            out_window.append(it)
    events, report = mod.extract_feed(in_window, qs, qe)
    tickers = set()
    for it in in_window:
        m = re.search(r"\b([A-Z]{3,5}\.CA)\b",
                      (it.get("title") or "") + " " + (it.get("body") or ""))
        if m:
            tickers.add(m.group(1))
    # Legacy comparison (shadow only): ensemble.detect_corporate_actions.
    legacy = {"found": 0, "agree_ex_date": 0, "agree_dps": 0,
              "legacy_only": [], "pilot_only": []}
    try:
        sys.path.insert(0, os.path.join(REPO, "scripts"))
        import ensemble
        base = {"POUL.CA": 10.0, "COMI.CA": 100.0}
        legacy_actions = []
        for it in in_window:
            ticker = None
            m = re.search(r"\b([A-Z]{3,5}\.CA)\b",
                          (it.get("title") or "") + " " +
                          (it.get("body") or ""))
            ticker = m.group(1) if m else "POUL.CA"
            legacy_actions += ensemble.detect_corporate_actions(
                [it], base.get(ticker, 100.0), 2026)
        legacy["found"] = len(legacy_actions)
        pilot_divs = [(e["issuer"].get("ticker"),
                       e["payload"]["amount_per_share"]["value"],
                       e["payload"]["ex_date"]["value"])
                      for e in events if e["event_type"] == "dividend"]
        for a in legacy_actions:
            match = [p for p in pilot_divs
                     if p[2] == a.get("ex_date")
                     and mod._dps_same(p[1], a.get("dps"))]
            if match:
                legacy["agree_ex_date"] += 1
                legacy["agree_dps"] += 1
            else:
                legacy["legacy_only"].append(a)
        for p in pilot_divs:
            if not [a for a in legacy_actions
                    if a.get("ex_date") == p[2]
                    and mod._dps_same(p[1], a.get("dps"))]:
                legacy["pilot_only"].append(p)
    except Exception as e:  # legacy import failure is a report, not a crash
        legacy["error"] = repr(e)[:200]
    shadow = {"archive_root": archive_root,
              "archive_head": None,
              "sweep_items": len(items) - harvest_items,
              "harvest_items": harvest_items,
              "egx_items": len(egx),
              "in_quarter_window": len(in_window),
              "out_of_window": len(out_window),
              "undated": len(undated),
              "tickers": sorted(tickers),
              "extractor_report": report,
              "legacy_comparison": legacy,
              "pilot_dividends": [
                  {"ticker": e["issuer"].get("ticker"),
                   "coupon": e["payload"].get("coupon_number"),
                   "amount": e["payload"]["amount_per_share"]["value"],
                   "ex_date": e["payload"]["ex_date"]["value"],
                   "ex_basis": e["payload"]["ex_date"]["basis"],
                   "status": e["extraction_status"]}
                  for e in events if e["event_type"] == "dividend"]}
    try:
        proc = subprocess.run(["git", "-C", archive_root, "rev-parse",
                               "HEAD"], capture_output=True, text=True,
                              timeout=30)
        shadow["archive_head"] = proc.stdout.strip() or None
    except Exception:
        pass
    out = os.path.join(stage, "pilot_accuracy.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"field_score": SCORE, "field_detail": FIELD_SCORE,
                   "shadow": shadow}, f, ensure_ascii=False, indent=1)
    print("shadow: %d EGX items in window (%d tickers), %d events, "
          "%d legacy dividends, %d agree on ex-date"
          % (len(in_window), len(shadow["tickers"]), report["events"],
             legacy["found"], legacy["agree_ex_date"]))
    print("pilot accuracy report: %s" % out)
    return shadow


def precision_recall():
    tp, fp, fn = SCORE["tp"], SCORE["fp"], SCORE["fn"]
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    return prec, rec


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--archive-root", default=ARCHIVE_DEFAULT)
    ap.add_argument("--stage", default=STAGE_DEFAULT)
    ap.add_argument("--pristine", action="store_true")
    ap.add_argument("--scorer", action="store_true",
                    help="run only the #283 scorer checks")
    ap.add_argument("--mutate", choices=list(MUTATIONS))
    ap.add_argument("--no-shadow", action="store_true")
    args = ap.parse_args(argv)
    os.makedirs(args.stage, exist_ok=True)
    mod = load_module(os.path.join(REPO, "scripts",
                                   "disclosure_events.py"),
                      "disclosure_events")
    if args.scorer:
        scorer_checks()
    elif args.pristine:
        pristine_control()
    elif args.mutate:
        killed = run_mutant(args.mutate, args.stage)
        check("mutant %s is killed" % args.mutate, killed)
    else:
        print("== fixture suite ==")
        split = run_fixture_suite(mod)
        determinism(args.stage)
        pristine_control()
        scorer_checks()
        if not args.no_shadow:
            shadow_run(mod, args.archive_root, args.stage)
    prec, rec = precision_recall()
    print("FIELD SCORE tp=%d fp=%d fn=%d precision=%.3f recall=%.3f"
          % (SCORE["tp"], SCORE["fp"], SCORE["fn"], prec, rec))
    print("CHECKS pass=%d fail=%d" % (CHECKS["pass"], CHECKS["fail"]))
    if FAILURES:
        print("FAILURES: %s" % ", ".join(FAILURES))
    return 0 if CHECKS["fail"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
