#!/usr/bin/env python3
"""Sharia screening engine core: data model + pluggable rule engine (issue #168).

Screens a ticker's own published financials under a named Sharia
standard. A standard is a DECLARATIVE rule-set file (JSON in
``scripts/sharia_rules/``), never engine code: adding a standard =
adding a rule-set file plus tests, with no engine change. The first
two rule sets are AAOIFI (Sharia Standard 21, as operationalised by
Musaffa and by Faisal Securities) and EGX33 (the EGX Sharia
Supervisory Committee methodology, which Ostool adopts verbatim).

FRAMING (binding, from the issue): every output of this engine is a
per-standard SCREENING result -- "screened under standard X" -- never
a fatwa and never religious or investment advice. The framing lines
below ship in English and Arabic inside every emitted table and every
verdict row; their final wording is reviewed under issue #77.

Stdlib only, deterministic, no network: inputs are plain data
structures (a per-ticker financials snapshot, market-cap aggregates or
a market-cap series, dividend events), so the live data wiring
(issues #78 / #109 / #110) plugs in later without touching the rules.

DATA MODEL -- one snapshot per ticker per statement period::

    {
      "ticker": "POUL.CA",
      "statement_period": {"label": "FY2025",
                           "start": "2025-01-01", "end": "2025-12-31"},
      "screening_date": "2026-11-17",
      "activity": {"classification": "permissible" | "prohibited",
                   "evidence_source": "<where the classification came from>"},
      "financials": {
        "total_revenue": ..., "non_compliant_revenue": ...,
        "interest_bearing_debt": ...,       # short + long term, summed upstream
        "interest_bearing_assets": ...,     # interest-bearing deposits/investments
        "cash_and_liquid_assets": ..., "total_assets": ...,
        "accounts_receivable": ..., "shares_outstanding": ...
      },
      "market": {
        # any subset; explicit aggregates win over series-derived ones
        "spot_market_cap": ..., "avg_market_value_36m": ...,
        "avg_market_value_review_period": ...,
        "market_cap_series": [{"date": "2026-11-16", "market_cap": ...}, ...]
      },
      "dividends": [{"per_share": 1.90, "ex_date": "2026-11-16",
                     "pay_date": "2026-11-18"}, ...]
    }

Every field is optional in the structure and REQUIRED only as a rule
set demands it: the engine derives a rule set's required inputs from
its own ratio and purification definitions. A missing required input
is named in the verdict row and yields the first-class verdict
``insufficient-data`` -- never a guessed value, never a silent pass.
One precedence exception, deliberate: a PROHIBITED activity
classification is decisive for ``non-compliant`` under both shipped
standards even when financial inputs are also missing (the missing
inputs are still named in the row for audit).

Market aggregates derived from ``market_cap_series``:
  spot            = market cap of the latest point on/before the
                    screening date
  avg36m          = mean of points in the 36 calendar months ending
                    on the screening date
  review-period   = mean of points inside the statement period

Verdicts: ``compliant`` / ``compliant-with-purification`` (only for
rule sets whose purification definition affects the verdict) /
``non-compliant`` / ``insufficient-data``.

Rule-set expressiveness (issue #169): a ratio's ``numerator`` may
name a single field or a LIST of fields to sum (MSCI's and FTSE's
"cash and interest-bearing securities" and "accounts receivables
and cash" are sums of two data-model fields). A rule set's
purification may define a ratio only (``per_share_definition``
null -- MSCI's dividend adjustment factor, FTSE/Yasaar's dividend
percentage, Islamicly's DP ratio): then no per-share figure is
produced and ``shares_outstanding`` is not a required input.
Every pre-#169 rule set evaluates identically under these
extensions.

Usage:
    sharia_engine.py screen --inputs snapshots.json --out-dir sharia/
                     [--standard AAOIFI] [--standard EGX33]
                     [--variant avg36m|spot]

Exit codes: 0 = tables written; 2 = bad input / unknown standard /
invalid parameter (fail loudly, nothing written); 1 = crash.
"""
import argparse
import json
import os
import sys
from datetime import date, datetime, timezone

ENGINE_VERSION = "1.0.0"
SCHEMA = "borsagator-sharia/1"
ENGINE_PATH = "scripts/sharia_engine.py"
RULES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "sharia_rules")

FRAMING_EN = ("Screening result under the named standard only, computed "
              "from the company's published financials. This is not a "
              "fatwa, and not religious or investment advice.")
FRAMING_AR = ("نتيجة فحص وفق المعيار المذكور فقط، محسوبة من القوائم المالية "
              "المنشورة للشركة. ليست فتوى، وليست نصيحة دينية أو استثمارية.")

VERDICTS = ("compliant", "compliant-with-purification",
            "non-compliant", "insufficient-data")
ACTIVITY_VALUES = ("permissible", "prohibited")
MARKET_AGGREGATES = ("spot_market_cap", "avg_market_value_36m",
                     "avg_market_value_review_period")


# ---------------------------------------------------------------- dates

def _parse_date(value):
    if value is None:
        return None
    return date.fromisoformat(value)


def _months_back(d, months):
    """The date ``months`` calendar months before ``d`` (day clamped)."""
    total = (d.year * 12 + (d.month - 1)) - months
    year, month0 = divmod(total, 12)
    month = month0 + 1
    # clamp the day to the target month's length
    if month == 12:
        next_first = date(year + 1, 1, 1)
    else:
        next_first = date(year, month + 1, 1)
    last_day = (next_first - date(year, month, 1)).days
    return date(year, month, min(d.day, last_day))


# ---------------------------------------------------------------- rules

def load_ruleset(standard_id):
    """Load a rule set by standard id from ``scripts/sharia_rules/``."""
    path = os.path.join(RULES_DIR, standard_id.lower() + ".json")
    if not os.path.exists(path):
        raise ValueError("unknown standard: %s (no rule set at %s)"
                         % (standard_id, path))
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def available_standards():
    out = []
    for name in sorted(os.listdir(RULES_DIR)):
        if name.endswith(".json"):
            out.append(name[:-5].upper())
    return out


def _resolve_parameters(ruleset, params):
    """Merge caller params over rule-set defaults; fail loudly on bad ones."""
    resolved = {}
    declared = ruleset.get("parameters") or {}
    for name, spec in declared.items():
        value = (params or {}).get(name, spec.get("default"))
        allowed = spec.get("allowed")
        if allowed is not None and value not in allowed:
            raise ValueError("parameter %s=%r not in allowed %s for %s"
                             % (name, value, allowed,
                                ruleset.get("standard_id")))
        resolved[name] = value
    for name in (params or {}):
        if name not in declared:
            raise ValueError("unknown parameter %r for %s"
                             % (name, ruleset.get("standard_id")))
    return resolved


# ---------------------------------------------------------------- inputs

def _market_aggregates(snapshot):
    """Resolve the three market aggregates.

    Returns {name: (value, source)} with source "market" (explicit
    field) or "series" (derived from market_cap_series). Explicit
    aggregates always win: the input pipeline may compute them from a
    fuller daily series than the snapshot carries.
    """
    market = snapshot.get("market") or {}
    out = {}
    for name in MARKET_AGGREGATES:
        if market.get(name) is not None:
            out[name] = (market[name], "market")
    series = market.get("market_cap_series") or []
    if not series:
        return out
    points = []
    for pt in series:
        d = _parse_date(pt.get("date"))
        if d is not None and pt.get("market_cap") is not None:
            points.append((d, pt["market_cap"]))
    points.sort()
    screening = _parse_date(snapshot.get("screening_date"))
    period = snapshot.get("statement_period") or {}
    p_start, p_end = _parse_date(period.get("start")), _parse_date(period.get("end"))

    def mean(window):
        vals = [v for d, v in points if window(d)]
        return (sum(vals) / len(vals)) if vals else None

    if "spot_market_cap" not in out and screening is not None:
        past = [p for p in points if p[0] <= screening]
        if past:
            out["spot_market_cap"] = (past[-1][1], "series")
    if "avg_market_value_36m" not in out and screening is not None:
        lo = _months_back(screening, 36)
        val = mean(lambda d: lo <= d <= screening)
        if val is not None:
            out["avg_market_value_36m"] = (val, "series")
    if "avg_market_value_review_period" not in out \
            and p_start is not None and p_end is not None:
        val = mean(lambda d: p_start <= d <= p_end)
        if val is not None:
            out["avg_market_value_review_period"] = (val, "series")
    return out


def _lookup(snapshot, aggregates, field):
    """Resolve a data-model field: financials first, then market."""
    fin = snapshot.get("financials") or {}
    if fin.get(field) is not None:
        return fin[field], "financials"
    if field in aggregates:
        return aggregates[field]
    market = snapshot.get("market") or {}
    if market.get(field) is not None:
        return market[field], "market"
    return None, None


# ---------------------------------------------------------------- screen

def _eval_ratio(spec, snapshot, aggregates, ruleset, params):
    """Evaluate one ratio spec. Returns (entry, missing_fields)."""
    entry = {"id": spec["id"],
             "label_en": spec.get("label_en"),
             "label_ar": spec.get("label_ar"),
             "numerator_field": spec["numerator"],
             "numerator": None, "denominator": None,
             "denominator_base": None, "value": None,
             "threshold": spec["threshold"],
             "comparison": spec.get("comparison", "le"),
             "passed": None, "missing": [], "error": None}
    missing = []

    # Numerator: a single field, or a list of fields to sum
    # (issue #169 -- composite numerators such as MSCI's
    # "accounts receivables and cash"). A missing component is
    # named and the sum is never partially computed.
    if isinstance(spec["numerator"], list):
        entry["numerator_field"] = " + ".join(spec["numerator"])
        total = 0
        for field in spec["numerator"]:
            v, _ = _lookup(snapshot, aggregates, field)
            if v is None:
                missing.append(field)
            else:
                total += v
        if not missing:
            entry["numerator"] = total
    else:
        num, _ = _lookup(snapshot, aggregates, spec["numerator"])
        if num is None:
            missing.append(spec["numerator"])
        else:
            entry["numerator"] = num

    den_spec = spec["denominator"]
    kind = den_spec["kind"]
    den = None
    if kind == "field":
        entry["denominator_base"] = den_spec["field"]
        den, _ = _lookup(snapshot, aggregates, den_spec["field"])
        if den is None:
            missing.append(den_spec["field"])
    elif kind == "parameterised_market_value":
        pname = den_spec["parameter"]
        variant = params[pname]
        variant_spec = ruleset["parameters"][pname]["variants"][variant]
        field = variant_spec["market_field"]
        entry["denominator_base"] = "market_value[%s]:%s" % (variant, field)
        den, _ = _lookup(snapshot, aggregates, field)
        if den is None:
            missing.append(field)
    elif kind == "max_of_fields":
        fields = den_spec["fields"]
        entry["denominator_base"] = "max(%s)" % ", ".join(fields)
        vals = []
        for f in fields:
            v, _ = _lookup(snapshot, aggregates, f)
            if v is None:
                missing.append(f)
            else:
                vals.append(v)
        if not missing:
            den = max(vals)
    else:
        raise ValueError("unknown denominator kind: %s" % kind)

    entry["missing"] = missing
    if missing:
        return entry, missing
    entry["denominator"] = den
    if den == 0:
        entry["error"] = "zero denominator: %s" % entry["denominator_base"]
        return entry, []
    value = entry["numerator"] / den
    entry["value"] = round(value, 6)
    if entry["comparison"] == "le":
        entry["passed"] = value <= spec["threshold"]
    elif entry["comparison"] == "lt":
        entry["passed"] = value < spec["threshold"]
    else:
        raise ValueError("unknown comparison: %s" % entry["comparison"])
    return entry, missing


def _eval_purification(ruleset, snapshot, aggregates):
    """Compute the rule set's purification outputs.

    Returns (purification_dict, missing_fields). A standard that
    publishes no purification rule reports defined=False and nulls --
    never an invented figure.
    """
    spec = ruleset.get("purification") or {}
    out = {"defined": bool(spec.get("defined")),
           "ratio": None, "per_share": None,
           "ratio_definition": spec.get("ratio_definition"),
           "per_share_definition": spec.get("per_share_definition"),
           "notes_en": spec.get("notes_en"), "notes_ar": spec.get("notes_ar")}
    if not out["defined"]:
        return out, []
    missing = []
    rev, _ = _lookup(snapshot, aggregates, "total_revenue")
    nonc, _ = _lookup(snapshot, aggregates, "non_compliant_revenue")
    shares, _ = _lookup(snapshot, aggregates, "shares_outstanding")
    if rev is None:
        missing.append("total_revenue")
    if nonc is None:
        missing.append("non_compliant_revenue")
    # shares_outstanding is required only when the rule set defines
    # a per-share purification figure (issue #169: MSCI / FTSE /
    # Islamicly publish a dividend purification RATIO only).
    if spec.get("per_share_definition") and shares is None:
        missing.append("shares_outstanding")
    if missing:
        return out, missing
    if rev == 0:
        out["error"] = "zero denominator: total_revenue"
        return out, []
    out["ratio"] = round(nonc / rev, 6)
    if spec.get("per_share_definition"):
        out["per_share"] = round(nonc / shares, 6) if shares else None
    return out, missing


def screen(snapshot, ruleset, params=None):
    """Screen one snapshot under one rule set. Pure and deterministic."""
    params = _resolve_parameters(ruleset, params)
    aggregates = _market_aggregates(snapshot)
    missing = set()

    activity = snapshot.get("activity") or {}
    classification = activity.get("classification")
    if classification not in ACTIVITY_VALUES:
        classification = None
        missing.add("activity.classification")

    ratios = []
    any_failed = False
    any_uncomputable = False
    for spec in ruleset.get("ratios") or []:
        entry, miss = _eval_ratio(spec, snapshot, aggregates, ruleset, params)
        ratios.append(entry)
        missing.update(miss)
        if entry["passed"] is False:
            any_failed = True
        if entry["value"] is None:
            any_uncomputable = True

    purification, pur_missing = _eval_purification(ruleset, snapshot, aggregates)
    missing.update(pur_missing)
    if purification.get("error"):
        any_uncomputable = True

    if classification == "prohibited":
        verdict = "non-compliant"
    elif missing or any_uncomputable:
        verdict = "insufficient-data"
    elif any_failed:
        verdict = "non-compliant"
    elif ruleset.get("purification_affects_verdict") \
            and purification["ratio"]:
        verdict = "compliant-with-purification"
    else:
        verdict = "compliant"

    resolved_market = {name: val for name, (val, _src)
                       in aggregates.items()}
    return {
        "ticker": snapshot.get("ticker"),
        "standard": ruleset["standard_id"],
        "ruleset_version": ruleset["ruleset_version"],
        "engine_version": ENGINE_VERSION,
        "verdict": verdict,
        "screening_date": snapshot.get("screening_date"),
        "statement_period": snapshot.get("statement_period"),
        "parameters": params,
        "activity": {"classification": classification,
                     "evidence_source": activity.get("evidence_source")},
        "ratios": ratios,
        "purification": purification,
        "missing_inputs": sorted(missing),
        "inputs": {"financials": snapshot.get("financials") or {},
                   "market_aggregates": resolved_market,
                   "dividends": snapshot.get("dividends") or []},
        "framing_en": FRAMING_EN,
        "framing_ar": FRAMING_AR,
    }


def screen_table(snapshots, ruleset, params=None, generated_at=None):
    """Screen a universe under one rule set into a stored table."""
    rows = [screen(s, ruleset, params)
            for s in sorted(snapshots, key=lambda s: s.get("ticker") or "")]
    return {
        "schema": SCHEMA,
        "engine": ENGINE_PATH,
        "engine_version": ENGINE_VERSION,
        "generated_at": generated_at,
        "standard": {"id": ruleset["standard_id"],
                     "name_en": ruleset.get("name_en"),
                     "name_ar": ruleset.get("name_ar"),
                     "ruleset_version": ruleset["ruleset_version"],
                     "sources": ruleset.get("sources") or []},
        "framing_en": FRAMING_EN,
        "framing_ar": FRAMING_AR,
        "rows": rows,
    }


# ---------------------------------------------------------------- CLI

def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sc = sub.add_parser("screen", help="screen snapshots under rule sets")
    sc.add_argument("--inputs", required=True,
                    help="JSON file: one snapshot object or a list of them")
    sc.add_argument("--standard", action="append", default=None,
                    help="standard id (repeatable); default: all available")
    sc.add_argument("--variant", default=None,
                    help="value for a rule set's denominator_variant "
                         "parameter, where it defines one (AAOIFI: "
                         "avg36m|spot)")
    sc.add_argument("--out-dir", required=True,
                    help="directory for verdicts-<standard>.json tables")
    args = ap.parse_args(argv)

    try:
        with open(args.inputs, encoding="utf-8") as fh:
            data = json.load(fh)
        snapshots = data if isinstance(data, list) else [data]
        standards = args.standard or available_standards()
        params = {}
        if args.variant is not None:
            params["denominator_variant"] = args.variant
        tables = []
        for std in standards:
            ruleset = load_ruleset(std)
            tables.append(screen_table(snapshots, ruleset, params,
                                       generated_at=_now_iso()))
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as e:
        print("REFUSED: %s" % e, file=sys.stderr)
        return 2

    os.makedirs(args.out_dir, exist_ok=True)
    for table in tables:
        name = "verdicts-%s.json" % table["standard"]["id"].lower()
        path = os.path.join(args.out_dir, name)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(table, fh, ensure_ascii=False, indent=2,
                      sort_keys=True)
            fh.write("\n")
        counts = {}
        for row in table["rows"]:
            counts[row["verdict"]] = counts.get(row["verdict"], 0) + 1
        print("%s: %d rows -> %s (%s)"
              % (table["standard"]["id"], len(table["rows"]), path,
                 ", ".join("%s=%d" % kv for kv in sorted(counts.items()))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
