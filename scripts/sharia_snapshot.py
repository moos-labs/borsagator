#!/usr/bin/env python3
"""Sharia snapshot extraction rule: interest-type income, wherever presented
(issue #330, follow-up to #326 run 1).

The as-harvested ``non_compliant_revenue`` numerator took only the
finance-income line. Interest-type income presented elsewhere was missed,
and the miss was verdict-changing (comparison run 1,
``hidden_files/issue-172/comparison-run-1.md``):

- TMGH (H1 2026): EGP 2,092,779,078 of amortised-cost investment income
  sits in *other income* (note 33). As harvested 3.17% of revenue, on
  substance 10.11% -- fails the MSCI/FTSE and EGX33 income screens.
- PHDC (H1 2026): EGP 523,193,960 of notes-receivable discount unwinding
  sits in *other revenues*. As harvested 2.33%, on substance 5.01% --
  fails the MSCI/FTSE income screen.

THE RULE. ``non_compliant_revenue`` is the sum of every interest-type
income line in the statements, classified per line:

1. Inside the finance-income line/note: count the INTEREST COMPONENTS
   only (the pre-#330 treatment, unchanged). Bank credit interest,
   time-deposit interest, and returns on amortised-cost investments
   presented there count; anything else in the note does not.
2. Outside finance income: count every interest-type line -- income
   from financial investments at amortised cost in other income, and
   amortisation/unwinding of discount on notes receivable in other
   revenues -- plus any similar line, each with its basis recorded.

NOT interest-type, and excluded with the reason recorded: fair-value
gains (FVPL / FVOCI), gains on sale of investments, and the
present-value discount line *inside* a finance-income note.

OPEN NOTE -- TMGH vs PHDC discount lines. The two discount lines are
treated differently by this rule because of WHERE they are presented:
TMGH's "Present value discount" (EGP 78,975,498, note 35, inside
finance income) stays excluded under leg 1, while PHDC's
"Amortization of discount on notes receivables" (EGP 523,193,960,
other revenues, outside finance income) is included under leg 2.
That is what reproduces run 1's substance figures (TMGH 10.11%,
PHDC 5.01%) exactly. If a future harvest shows TMGH's line is the
same unwinding of a customer-notes discount, leg 1 should be
revisited -- the line is carried explicitly in every breakdown, so
that revisit is a one-line change, not a re-harvest.

Every line is classified explicitly: ``build_non_compliant_revenue``
returns the total plus a per-line breakdown (label, amount, presented
in, included or not, category, reason). The breakdown is stored on the
rebuilt snapshot as ``non_compliant_revenue_breakdown`` and written
out in the snapshot provenance, so a reviewer can see which statement
line contributed what. No figure is invented here: the regression
cases use the evidence figures from the #326 provenance files only.

A snapshot's as-harvested numerator is kept alongside as
``non_compliant_revenue_as_harvested`` so both bases stay measurable
-- run 2 of #326 re-measures on the rebuilt snapshots; the old
figures (TMGH 3.17%, PHDC 2.33%) must still reproduce from the
lines the original harvest counted (flagged ``as_harvested`` on the
line: TMGH's finance-income interest components, PHDC's
interest-income line).

Stdlib only, deterministic, no network. Inputs are plain data
structures (statement lines as harvested), so the rule is testable
offline and reusable by any harvester.

Usage:
    python3 scripts/sharia_snapshot.py --help
    python3 scripts/test_sharia_snapshot.py
"""

import argparse
import json
import os
import sys

RULE_VERSION = "1.0.0"
RULE_ISSUE = 330
RULE_EVIDENCE = ("moos-labs/borsagator issue #330; evidence: "
                 "hidden_files/issue-172/comparison-run-1.md and the "
                 "TMGH/PHDC H1-2026 snapshot provenance files")

FRAMING_EN = ("Screening result under the named standard only, computed "
              "from the company's published financials. This is not a "
              "fatwa, and not religious or investment advice.")

# ---------------------------------------------------------------- rule table
# kind -> (included, category, reason). The category is the audit label
# written into the snapshot breakdown; the reason is the human-readable
# justification for that line's treatment.

RULE_TABLE = {
    # -- included: interest components of the finance-income line/note
    "credit_interest": (
        True, "finance_income_interest",
        "Interest on bank current accounts, finance-income note."),
    "time_deposit_interest": (
        True, "finance_income_interest",
        "Interest on time deposits, finance-income note."),
    "amortised_cost_investment_income": (
        True, "interest_type_income",
        "Yield / returns on financial investments at amortised cost "
        "(treasury bills, government bonds, time deposits) -- counted "
        "wherever presented: finance income, other income, or other "
        "revenues."),
    "discount_unwinding_notes_receivable": (
        True, "interest_type_income",
        "Amortisation / unwinding of discount on notes receivable -- "
        "implicit interest on deferred customer payments, counted "
        "wherever presented outside the finance-income note."),
    "interest_like_other": (
        True, "interest_type_income",
        "Other line identified as interest-type; the line's 'basis' "
        "must name the evidence (note / statement wording)."),
    # -- excluded: not interest-type
    "present_value_discount": (
        False, "excluded_not_interest",
        "Present-value discount line inside a finance-income note: "
        "leg 1 of the rule counts the note's interest components only, "
        "and this line is not one. See the OPEN NOTE in the module "
        "docstring (TMGH note 35, EGP 78,975,498)."),
    "fvpl_gain": (
        False, "excluded_not_interest",
        "Fair-value gain on financial investments at FVPL -- a "
        "revaluation gain, not interest."),
    "fvoci_gain": (
        False, "excluded_not_interest",
        "Fair-value gain on financial investments at FVOCI -- a "
        "revaluation gain, not interest."),
    "sale_gain": (
        False, "excluded_not_interest",
        "Gain on sale of investments -- a disposal gain, not interest."),
    "other_non_interest": (
        False, "excluded_not_interest",
        "Line identified as not interest-type; the line's 'basis' "
        "must name why."),
}

INCLUDED_KINDS = frozenset(k for k, v in RULE_TABLE.items() if v[0])
EXCLUDED_KINDS = frozenset(k for k, v in RULE_TABLE.items() if not v[0])
# Kinds whose inclusion/exclusion needs a per-line basis note.
BASIS_REQUIRED_KINDS = frozenset(
    ("interest_like_other", "other_non_interest"))


def classify_line(line):
    """Classify one harvested statement line.

    ``line`` is a dict with:
      label         -- the statement line's wording, verbatim-ish
      amount_egp    -- integer EGP, exact as printed (never thousands)
      presented_in  -- where the line is presented, e.g.
                       "finance income (note 35)" or
                       "other income (note 33)"
      kind          -- one of the RULE_TABLE keys (the harvester's
                       judgement, recorded here so it is reviewable)
      basis         -- required for interest_like_other /
                       other_non_interest: the evidence for the call
      note          -- optional: statement note number / reference
      as_harvested  -- optional bool: True iff the original (#326)
                       harvest counted this line in
                       non_compliant_revenue

    Returns a breakdown record: the line as given plus
    ``included`` (bool), ``category`` and ``reason``. Raises
    ValueError on an unknown kind, a missing basis where one is
    required, or a non-integer / negative amount -- the rule fails
    loudly rather than silently dropping a line.
    """
    kind = line.get("kind")
    if kind not in RULE_TABLE:
        raise ValueError(
            "unknown interest-income kind %r (label %r); known kinds: %s"
            % (kind, line.get("label"), sorted(RULE_TABLE)))
    if kind in BASIS_REQUIRED_KINDS and not (line.get("basis") or "").strip():
        raise ValueError(
            "kind %r (label %r) needs a 'basis' naming the evidence"
            % (kind, line.get("label")))
    amount = line.get("amount_egp")
    if not isinstance(amount, int) or isinstance(amount, bool):
        raise ValueError(
            "line %r: amount_egp must be an integer EGP value, got %r"
            % (line.get("label"), amount))
    if amount < 0:
        raise ValueError(
            "line %r: negative amount_egp %r -- re-check the harvest "
            "(a credit line presented as a negative is a harvest error)"
            % (line.get("label"), amount))
    included, category, reason = RULE_TABLE[kind]
    if line.get("as_harvested") and not included:
        raise ValueError(
            "line %r: flagged as_harvested but kind %r is excluded -- "
            "the original harvest cannot have counted an excluded line"
            % (line.get("label"), kind))
    record = {
        "label": line.get("label"),
        "amount_egp": amount,
        "presented_in": line.get("presented_in"),
        "kind": kind,
        "included": included,
        "category": category,
        "reason": reason,
    }
    if line.get("as_harvested"):
        record["as_harvested"] = True
    if line.get("note"):
        record["note"] = line["note"]
    if line.get("basis"):
        record["basis"] = line["basis"]
    return record


def build_non_compliant_revenue(lines):
    """Apply the #330 rule to a list of harvested statement lines.

    Returns (total_egp, breakdown) where breakdown is the per-line
    classification list (classify_line output, in input order).
    The total is the sum of the included lines only.
    """
    breakdown = [classify_line(line) for line in lines]
    total = sum(r["amount_egp"] for r in breakdown if r["included"])
    return total, breakdown


def as_harvested_total(lines):
    """The pre-#330 numerator: the lines the original harvest counted,
    flagged ``as_harvested`` on the line (for TMGH: the interest
    components of the finance-income note; for PHDC: the company's
    interest-income line on the face of the income statement). Used to
    reproduce the as-harvested figures (TMGH 3.17%, PHDC 2.33%) from
    the same harvested lines, so both bases stay measurable on one
    input.
    """
    breakdown = [classify_line(line) for line in lines]
    return sum(r["amount_egp"] for r in breakdown
               if r["included"] and r.get("as_harvested"))


def income_ratio_pct(non_compliant_revenue, total_revenue):
    """Non-compliant income as a percentage of total revenue, or None
    on a zero / missing denominator (never divides, never passes
    silently -- mirrors the engine's zero-denominator rule)."""
    if not total_revenue:
        return None
    return 100.0 * non_compliant_revenue / total_revenue


def rebuild_snapshot(snapshot, lines):
    """Return a copy of ``snapshot`` rebuilt under the #330 rule.

    Sets financials.non_compliant_revenue to the rule total, keeps the
    finance-income-only figure as
    financials.non_compliant_revenue_as_harvested, and stores the
    per-line classification as the top-level
    ``non_compliant_revenue_breakdown`` plus rule metadata in
    ``non_compliant_revenue_rule``. All other fields are copied
    unchanged. The input snapshot is not mutated.
    """
    total, breakdown = build_non_compliant_revenue(lines)
    as_harvested = as_harvested_total(lines)
    rebuilt = json.loads(json.dumps(snapshot))  # deep copy, stdlib only
    rebuilt.setdefault("financials", {})["non_compliant_revenue"] = total
    rebuilt["financials"]["non_compliant_revenue_as_harvested"] = as_harvested
    rebuilt["non_compliant_revenue_breakdown"] = breakdown
    rebuilt["non_compliant_revenue_rule"] = {
        "rule": "interest-type income wherever presented (issue #330)",
        "rule_version": RULE_VERSION,
        "evidence": RULE_EVIDENCE,
    }
    return rebuilt


# ------------------------------------------------------------------- CLI

def _load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Apply the #330 interest-income rule to harvested "
                    "statement lines, or rebuild a snapshot under it.")
    sub = parser.add_subparsers(dest="command", required=True)
    p_sum = sub.add_parser(
        "sum", help="sum harvested lines under the rule (JSON list in, "
                    "total + breakdown out)")
    p_sum.add_argument("--lines", required=True,
                       help="JSON file: list of statement lines")
    p_rebuild = sub.add_parser(
        "rebuild", help="rebuild a snapshot JSON under the rule")
    p_rebuild.add_argument("--snapshot", required=True,
                           help="snapshot JSON file (list or single dict)")
    p_rebuild.add_argument("--lines", required=True,
                           help="JSON file: list of statement lines")
    p_rebuild.add_argument("--out", required=True,
                           help="output JSON path")
    args = parser.parse_args(argv)

    lines = _load_json(args.lines)
    if args.command == "sum":
        total, breakdown = build_non_compliant_revenue(lines)
        print(json.dumps(
            {"non_compliant_revenue": total,
             "as_harvested": as_harvested_total(lines),
             "breakdown": breakdown}, indent=1, ensure_ascii=False))
        return 0
    snapshot = _load_json(args.snapshot)
    if isinstance(snapshot, list):
        if len(snapshot) != 1:
            print("rebuild expects a single-snapshot file (list of 1)",
                  file=sys.stderr)
            return 2
        snapshot = snapshot[0]
    rebuilt = rebuild_snapshot(snapshot, lines)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump([rebuilt], fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("rebuilt %s: non_compliant_revenue=%d (as-harvested=%d)"
          % (rebuilt.get("ticker"),
             rebuilt["financials"]["non_compliant_revenue"],
             rebuilt["financials"]["non_compliant_revenue_as_harvested"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
