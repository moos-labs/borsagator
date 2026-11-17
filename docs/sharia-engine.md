# Sharia screening engine (issue #168)

Borsagator screens a ticker's **own published financials** under a named
Sharia standard. It never copies another site's verdicts.

> **Framing (binding).** Every output of this engine is a per-standard
> **screening result** — "screened under standard X" — never a fatwa and
> never religious or investment advice.
>
> نتيجة فحص وفق المعيار المذكور فقط، محسوبة من القوائم المالية المنشورة
> للشركة. ليست فتوى، وليست نصيحة دينية أو استثمارية.
>
> The framing lines ship in English and Arabic inside every emitted
> table and every verdict row; final wording is reviewed under issue #77.

## Pieces

| Piece | Path |
|---|---|
| Engine (data model, rule evaluation, CLI) | `scripts/sharia_engine.py` |
| Rule sets (declarative JSON, one file per standard) | `scripts/sharia_rules/aaoifi.json`, `scripts/sharia_rules/egx33.json` |
| Covered-universe input snapshot | `scripts/sharia_fixtures/covered_universe.json` |
| Stored verdict tables (generated, committed) | `sharia/verdicts-aaoifi.json`, `sharia/verdicts-egx33.json` |
| Tests | `scripts/test_sharia_engine.py` |

## Verdicts

`compliant` · `compliant-with-purification` (only where the standard's
purification definition affects the verdict) · `non-compliant` ·
`insufficient-data`.

`insufficient-data` is a first-class verdict: a rule set's required
inputs are **derived from its own ratio and purification definitions**,
and any missing one is named in the row (`missing_inputs`) — never
guessed, never a silent pass. One deliberate precedence: a **prohibited**
activity classification is decisive for `non-compliant` under both
shipped standards even when financial inputs are also missing (they are
still named in the row).

Every verdict row carries its inputs (financials as provided, resolved
market aggregates, dividend events), the statement period, the active
rule-set parameters (e.g. the AAOIFI denominator variant), and the
engine + rule-set versions — auditable after the fact.

## Rule sets shipped

**AAOIFI** — Sharia Standard 21, as operationalised by Musaffa and by
Faisal Securities. Non-permissible income ≤ 5% of revenue;
interest-bearing debt ≤ 30%; interest-bearing assets/deposits ≤ 30%.
The two published operationalisations differ only in the denominator,
so it is a rule-set **parameter** (`denominator_variant`):

- `avg36m` (default) — trailing 36-month average market value (Musaffa)
- `spot` — spot market capitalisation at the screening date (Faisal)

Purification is defined: ratio = non-permissible revenue ÷ total
revenue; per share = non-permissible revenue ÷ shares outstanding. A
passing company with non-permissible revenue > 0 is
`compliant-with-purification`.

**EGX33** — EGX Sharia Supervisory Committee methodology (grounded in
AAOIFI Std 21; Ostool adopts it verbatim). Articles must not state
riba/alcohol/pork objectives and the main activity must be permissible;
interest-bearing borrowing ≤ 33% and interest-bearing investments ≤ 33%
of **the greater of total assets or average market value in the review
period**; liquid assets ≤ 70% of total assets; non-compliant income
≤ 5% of revenue. EGX publishes no purification rule, so this rule set
reports none.

**Documented conflict (not silently resolved):** June 2024 launch
coverage reported the EGX33 income limit as 10%. The methodology text
quoted by the committee's vice-chair and EGX's August 2025 review
release state 5%. The rule set encodes **5%** as operative and records
the 10% figure in its `documented_conflicts`.

## Data model

One snapshot per ticker per statement period: activity classification
(with evidence source), the financials fields listed in the engine
docstring, market aggregates and/or a market-cap series (explicit
aggregates win; otherwise the engine derives spot / trailing-36-month
average / review-period average from the series), and dividend events.
Live wiring of these inputs rides on issues #78 (EGX33 universe), #109
(dividend/disclosure events) and #110 (fundamentals reconciliation);
the engine itself does no network I/O.

Today's covered universe is POUL.CA only, and its fleet data carries
just shares outstanding (1,789,351,397) plus the Nov 2026 dividend
event — so the stored tables honestly read `insufficient-data` for both
standards, naming every missing input. That is the designed behaviour,
not an error.

## Run it

```bash
python3 scripts/sharia_engine.py screen \
    --inputs scripts/sharia_fixtures/covered_universe.json \
    --out-dir sharia/
python3 scripts/test_sharia_engine.py
```

## Report Model section (issue #170)

The Report Model compiler (`scripts/compile_model.py`) projects
these stored tables into every model's `sharia` block: per selected
standard the verdict, the ratio table, the purification figures,
the statement period, the rule-set version and the denominator
variant where the rule set has one — plus a disagreement flag and
the **average purification ratio** across the selected standards
that define one. A standard that defines no purification rule
(EGX33) is excluded from the average, and the exclusion is listed
in the block with its reason — never hidden. The compile job takes
the selection as `--sharia-standards AAOIFI,EGX33`; no selection
means all implemented standards, and an unknown or unimplemented
standard refuses the compile instead of being silently dropped.
`delta.model_to_view` carries the block through to the renderer
unread by the diff core (the `levels` pattern). The block is
additive, so the model schema stays `borsagator-report-model/1`.
Tests: `scripts/test_compile_model_sharia.py`.

## Adding a standard

Add one JSON file to `scripts/sharia_rules/` (activity screen, ratio
definitions with numerator/denominator/threshold, parameters,
purification definition, sources, documented conflicts) plus tests.
No engine-code change. The remaining published packs (MSCI Islamic,
FTSE Shariah, S&P Shariah / DJIM) are scoped in the follow-up issue of
this series; entry/exit buffers are already reserved in the schema for
standards that define them.

## Decisions taken where the issue left room

- Required inputs are derived from each rule set, not hard-coded —
  e.g. `shares_outstanding` is required under AAOIFI (its purification
  per-share output needs it) and not under EGX33 (no purification rule,
  no ratio uses it).
- A zero denominator (e.g. total revenue of 0) makes the ratio
  uncomputable and the verdict `insufficient-data`, with the reason on
  the ratio entry — it never divides and never passes silently.
- The 36-month average is over the 36 calendar months ending on the
  screening date, computed from whatever series points fall inside the
  window (the input pipeline owns series completeness).
