#!/usr/bin/env python3
"""Verdict-diff report for the Sharia screening engine (issue #169).

Compares the stored verdict tables (issue #168's engine output)
across standards for the same tickers: where a standard disagrees
with a baseline standard (AAOIFI / EGX33) on a DETERMINATE verdict,
the disagreement is reported with the flipping ratio(s) named --
the ratio(s) whose pass/fail outcome differs between the two rows
and therefore drives the different verdict. A disagreement with no
flipping ratio is a purification-treatment difference (one
standard's passing verdict carries a purification duty the other's
does not) and is labelled as such, never left unexplained.

Pairs where either side is ``insufficient-data`` are NOT
disagreements: they are listed as indeterminate, with the verdicts
shown, because a missing input is an absence of a verdict, not a
dissent (the same rule the Report Model section applies, #170).

Framing (binding): every output is a per-standard SCREENING
result -- never a fatwa, never religious or investment advice.

Usage:
    sharia_diff.py --tables-dir sharia/
                   [--out-json sharia/verdict-diff.json]
                   [--out-md sharia/verdict-diff.md]

Exit codes: 0 = report written; 2 = bad input.
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sharia_engine as se

SCHEMA = "borsagator-sharia-diff/1"
BASELINES = ("AAOIFI", "EGX33")
DETERMINATE = ("compliant", "compliant-with-purification",
               "non-compliant")


def _row_index(table):
    return {row["ticker"]: row for row in table.get("rows") or []}


def flipping_ratios(row_a, row_b):
    """Ratio ids whose outcome differs between two verdict rows.

    A ratio flips when its ``passed`` flag differs across the rows,
    or when it exists in only one row and FAILED there (a screen
    one standard applies and the other does not, failing, is what
    drives the stricter verdict). Ratios uncomputable on either
    side (passed None) never flip -- that pair is indeterminate
    anyway and is filtered out before this is called.
    """
    by_a = {r["id"]: r for r in row_a.get("ratios") or []}
    by_b = {r["id"]: r for r in row_b.get("ratios") or []}
    out = []
    for rid in sorted(set(by_a) | set(by_b)):
        ra, rb = by_a.get(rid), by_b.get(rid)
        if ra is not None and rb is not None:
            if ra.get("passed") != rb.get("passed"):
                out.append(rid)
        else:
            only = ra if ra is not None else rb
            if only.get("passed") is False:
                out.append(rid)
    return out


def diff_pair(ticker, standard, row_s, baseline, row_b):
    """One (standard, baseline) comparison for one ticker.

    Returns a disagreement dict, an indeterminate dict, or None
    when the two determinate verdicts agree.
    """
    vs, vb = row_s.get("verdict"), row_b.get("verdict")
    pair = {"ticker": ticker, "standard": standard,
            "baseline": baseline,
            "standard_verdict": vs, "baseline_verdict": vb}
    if vs not in DETERMINATE or vb not in DETERMINATE:
        pair["reason"] = ("insufficient-data on one or both sides: "
                          "an absence of a verdict, not a dissent")
        return ("indeterminate", pair)
    if vs == vb:
        return None
    flips = flipping_ratios(row_s, row_b)
    drivers = ["ratio: %s" % rid for rid in flips]
    if not flips:
        drivers.append("purification-treatment: the standards "
                       "differ in whether a passing verdict carries "
                       "a purification duty")
    pair["flipping_ratios"] = flips
    pair["drivers"] = drivers
    return ("disagreement", pair)


def build_diff(tables, baselines=BASELINES, generated_at=None):
    """Build the diff report from {standard_id: verdict table}."""
    indexes = {std: _row_index(t) for std, t in tables.items()}
    tickers = sorted({t for idx in indexes.values() for t in idx})
    standards = sorted(tables)
    verdicts = {t: {std: (indexes[std].get(t) or {}).get("verdict")
                    for std in standards}
                for t in tickers}
    disagreements, indeterminate = [], []
    for ticker in tickers:
        for std in standards:
            if std in baselines:
                continue
            row_s = indexes[std].get(ticker)
            if row_s is None:
                continue
            for base in baselines:
                row_b = indexes.get(base, {}).get(ticker)
                if row_b is None:
                    continue
                outcome = diff_pair(ticker, std, row_s, base, row_b)
                if outcome is None:
                    continue
                kind, pair = outcome
                (disagreements if kind == "disagreement"
                 else indeterminate).append(pair)
    return {
        "schema": SCHEMA,
        "generated_at": generated_at,
        "framing_en": se.FRAMING_EN,
        "framing_ar": se.FRAMING_AR,
        "baselines": list(baselines),
        "standards": standards,
        "tickers": tickers,
        "verdicts": verdicts,
        "disagreements": disagreements,
        "indeterminate": indeterminate,
    }


def render_md(report):
    lines = [
        "# Sharia verdict diff — new packs vs AAOIFI / EGX33 "
        "(issue #169)",
        "",
        "> %s" % report["framing_en"],
        ">",
        "> %s" % report["framing_ar"],
        "",
        "Generated: %s" % report["generated_at"],
        "",
        "## Verdicts over the covered universe",
        "",
        "| Ticker | %s |" % " | ".join(report["standards"]),
        "|---|%s|" % "|".join("---" for _ in report["standards"]),
    ]
    for ticker in report["tickers"]:
        cells = [report["verdicts"][ticker].get(std) or "—"
                 for std in report["standards"]]
        lines.append("| %s | %s |" % (ticker, " | ".join(cells)))
    lines += ["", "## Disagreements (determinate verdicts only)", ""]
    if report["disagreements"]:
        for d in report["disagreements"]:
            lines.append(
                "- **%s** — %s: %s vs %s (%s). Flipping ratio(s): %s."
                % (d["ticker"], d["standard"], d["standard_verdict"],
                   d["baseline_verdict"], d["baseline"],
                   ", ".join(d["flipping_ratios"]) or "none"))
            for drv in d["drivers"]:
                lines.append("  - driver: %s" % drv)
    else:
        lines.append(
            "No determinate disagreements: no ticker in the covered "
            "universe currently carries determinate verdicts on both "
            "sides of any compared pair (see the indeterminate list "
            "below). The flipping-ratio machinery is proven on "
            "hand-computed fixtures in scripts/test_sharia_packs.py.")
    lines += ["", "## Indeterminate pairs (insufficient-data)", ""]
    if report["indeterminate"]:
        for p in report["indeterminate"]:
            lines.append("- %s — %s: %s vs %s (%s). %s"
                         % (p["ticker"], p["standard"],
                            p["standard_verdict"],
                            p["baseline_verdict"], p["baseline"],
                            p["reason"]))
    else:
        lines.append("None.")
    lines.append("")
    return "\n".join(lines)


def load_tables(tables_dir):
    tables = {}
    for name in sorted(os.listdir(tables_dir)):
        if name.startswith("verdicts-") and name.endswith(".json"):
            with open(os.path.join(tables_dir, name),
                      encoding="utf-8") as fh:
                table = json.load(fh)
            tables[table["standard"]["id"]] = table
    return tables


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tables-dir", required=True,
                    help="directory holding verdicts-<standard>.json")
    ap.add_argument("--out-json", default=None)
    ap.add_argument("--out-md", default=None)
    args = ap.parse_args(argv)
    try:
        tables = load_tables(args.tables_dir)
        if not tables:
            raise ValueError("no verdict tables in %s" % args.tables_dir)
        generated = datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ")
        report = build_diff(tables, generated_at=generated)
    except (ValueError, KeyError, TypeError,
            json.JSONDecodeError) as e:
        print("REFUSED: %s" % e, file=sys.stderr)
        return 2
    if args.out_json:
        with open(args.out_json, "w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=2,
                      sort_keys=True)
            fh.write("\n")
    if args.out_md:
        with open(args.out_md, "w", encoding="utf-8") as fh:
            fh.write(render_md(report))
    print("diff over %d tickers, %d standards: %d disagreements, "
          "%d indeterminate pairs"
          % (len(report["tickers"]), len(report["standards"]),
             len(report["disagreements"]),
             len(report["indeterminate"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
