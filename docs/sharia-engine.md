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
| Rule sets (declarative JSON, one file per standard) | `scripts/sharia_rules/aaoifi.json`, `scripts/sharia_rules/egx33.json`, `scripts/sharia_rules/msci.json`, `scripts/sharia_rules/msci_m.json`, `scripts/sharia_rules/ftse.json`, `scripts/sharia_rules/islamicly.json` |
| Draft-disabled rule sets (pin gate unmet, NOT loaded) | `scripts/sharia_rules_draft/sp_shariah.json`, `scripts/sharia_rules_draft/djim.json` |
| Covered-universe input snapshot | `scripts/sharia_fixtures/covered_universe.json` |
| Stored verdict tables (generated, committed) | `sharia/verdicts-<standard>.json` |
| Tests | `scripts/test_sharia_engine.py` |
| Standard-pack tests (issue #169) | `scripts/test_sharia_packs.py` |
| Verdict-diff report (issue #169) | `scripts/sharia_diff.py`, `sharia/verdict-diff.json`, `sharia/verdict-diff.md` |
| Purification calculator (issue #171) | `scripts/sharia_purification.py` |
| Calculator tests | `scripts/test_sharia_purification.py` |
| Accuracy benchmark vs Musaffa / Faisal / Ostool / EGX33 (issue #172) | `scripts/sharia_benchmark.py`, `docs/sharia-benchmark.md` |
| Zakat calculator + benchmark vs published calculators (issue #173) | `scripts/sharia_zakat.py`, `scripts/sharia_zakat_methods/`, `docs/sharia-zakat.md` |

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

**MSCI** — MSCI Islamic Index Series Methodology (May 2025),
encoded from MSCI's own published methodology document.
Business screen: more than 5% cumulative revenue (interest income
included, against total income) from alcohol, tobacco/cannabis,
pork, conventional financial services, defence/weapons, gambling,
music, hotels, cinema or adult entertainment excludes the stock.
Ratios vs **total assets**: total debt ≤ 33.33%; cash +
interest-bearing securities ≤ 33.33%; accounts receivable + cash
≤ 70%. The methodology's entry/exit buffers (30%/35%; 46%/none)
govern index membership, so they are recorded per ratio as
`buffers` metadata — the encoded threshold is the Financial Ratio
Threshold. Purification is defined (§2.3): MSCI's dividend
adjustment factor means the share of a dividend to purify is the
non-permissible income share — the engine's ratio. MSCI publishes
no per-share figure, so the rule set defines a ratio only.

**MSCI_M** — the MSCI Islamic **M-Series** (same methodology,
§2.2.2): the same numerators against the trailing **36-month
average market capitalisation** instead of total assets, with the
receivables-and-cash threshold at **49%** (entry buffer 46%; the
M-Series table publishes no exit buffers). It ships as its own
rule-set file, mirroring MSCI's two-series structure, because the
engine's parameter mechanism swaps a denominator only and cannot
also change a threshold.

**FTSE** — FTSE Shariah (screening by Yasaar Limited, fatwa-
certified by Yasaar's Shariah Supervisory Board), encoded from
FTSE Russell's own published criteria (index factsheet, data as
at 30 Oct 2026; Board Opinion, 2025-02-03) — Kashif's summary of
this standard is imprecise and was used only as a cross-check.
Sector screen (conventional finance, alcohol, pork/non-halal
food, entertainment, tobacco, weapons/defence), then ratios vs
**total assets**, all "less than": debt < 33.333%; cash +
interest-bearing items < 33.333%; accounts receivable + cash
< 50%; and total interest and non-compliant income "should not
exceed" 5% of revenue (the one non-strict comparison). Dividend
purification is defined (Yasaar calculates the percentage of
dividends derived from interest income or prohibited activities);
no per-share figure is published. One wording conflict is
documented: the Board Opinion words the cash limit "should not
exceed" where the current factsheets say "less than" — the
factsheets' strict reading is operative.

**ISLAMICLY** — Islamicly's own criteria (in-house Shariah
Advisory Board; "in convergence with AAOIFI"), encoded from
Islamicly's published screening page. All ratios vs the
**36-month average market value of equity**, all strict: debt
< 30%; accounts receivable < 49%; non-permissible revenue
(incl. all interest income) < 5%; and a published dividend
purification (DP) ratio = non-permissible revenue / total
revenue. **Documented conflict:** the page states the cash +
interest-bearing securities ratio as 33% in its Cash Compliance
section and as < 30% in its Leverage Compliance section. The
operative value is **< 30%** — the Leverage section states the
operative compliance inequality, it is the stricter of the
provider's two figures, and it matches the AAOIFI limit
Islamicly claims convergence with; the 33% figure is recorded
in `documented_conflicts`.

**Draft-disabled: SP_SHARIAH and DJIM.** Issue #169's pin gate
requires S&P DJI's own current methodology before encoding.
Those documents live on spglobal.com, which could not be
fetched from the build environment, and the rulebooks changed
materially on 2026-09-21 (debt/cash limits 33% → 30%), while
secondary summaries conflict on whether the accounts-receivable
screen survives the revision. The packs therefore ship as
explicitly disabled drafts in `scripts/sharia_rules_draft/`
(status + reason + the unpinned secondary reports recorded);
the engine never loads that directory, the Report Model refuses
them like any unimplemented standard, and no figure in them is
encoded as a ratio.

**Verdict diff (issue #169).** `scripts/sharia_diff.py` compares
the stored tables across standards: every determinate
disagreement of a new pack with AAOIFI / EGX33 is reported with
the flipping ratio named (`sharia/verdict-diff.json` /
`.md`). Over today's covered universe every standard is
insufficient-data on POUL.CA, so the stored diff honestly
reports zero determinate disagreements and lists the pairs as
indeterminate; the flipping-ratio machinery is proven on
hand-computed fixtures in `scripts/test_sharia_packs.py`
(including the canonical MSCI-vs-MSCI_M flip on identical
financials, driven by `receivables_and_cash`).

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
event — so the stored tables honestly read `insufficient-data` for
every implemented standard, naming every missing input. That is the
designed behaviour, not an error.

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

## Purification calculator (issue #171)

`scripts/sharia_purification.py` works out what a holder must
purify for one holding — ticker snapshot, share count, buy date,
sell date (or still holding, with an explicit as-of date) —
under each selected standard, with no manual dividend entry.
It consumes the engine's outputs only (the purification ratio
and per-share figure from a screen of the same snapshot); it
re-derives no screening ratio.

**Components.** What each standard purifies is declared by its
rule set. The *dividend component* applies where the rule set's
`purification.defined` is true: for every dividend whose
entitlement falls inside the holding window, dividend per
share × purification ratio × shares held. The *capital
component* is declared per rule set in
`purification.capital_component` (the declaration issue #171
requires each rule set to carry): where it applies — AAOIFI,
per Kashif's documentation that purification applies to
capital gains as well as dividends and Musaffa's AAOIFI
practice of purifying the non-permissible portion of income —
it is the statement period's non-permissible income per share
accrued over the holding days: per share × days held / days in
the statement period. EGX33 publishes no purification rule at
all, so under EGX33 the result is `total: null` with status
`no-purification-rule` — never a zero, which would claim
nothing is owed under a rule that does not exist. The
declaration is additive rule-set metadata for this consumer:
no screening rule changed, so `ruleset_version` stays 1.0.0.

**Entitlement convention (stated, not assumed):** a dividend
belongs to the holding iff the holder bought *before* its
ex-date and was still holding on it — `buy_date < ex_date <=
window end`. Buying on the ex-date itself is not entitled
(those shares trade without the dividend); selling on the
ex-date keeps the entitlement. Every event in the stream is
listed in the output, entitled or not, with the reason in
Arabic and English.

**Honesty on gaps.** A snapshot's event list is bounded by its
screening date: a window running past it is computed from the
events known, marked `partial`, and the uncovered range is
named. A snapshot with no dividend field at all yields no
dividend figure and no total. Missing engine figures surface
as `insufficient-data` with the missing inputs named. Two
method decisions are flagged on the output, never silent:
`days held` is the calendar-day difference between buy date
and window end, and the capital accrual fraction is capped at
one full statement period when the holding runs longer (a
single period's snapshot is available), with the cap named on
the component. Results are produced side by side per standard
with a `rule_differences` list naming how the selected
standards' purification rules differ. Tests:
`scripts/test_sharia_purification.py` (the POUL Nov 2026
worked example is its first test).

## Zakat calculator (issue #173)

`scripts/sharia_zakat.py` computes zakat al-mal on one share
holding under a named, published method — the methods are
declared as data in `scripts/sharia_zakat_methods/`, the same
pattern as the rule sets. **TRADING**: trade goods, zakat on
the market value at the valuation date plus declared
still-held cash dividends (IslamWeb 84386; Dar Al-Ifta Egypt
2110; Kashif's trader-zakat calculator). **INVESTMENT**:
AAOIFI Sharia Standard No. 35 — zakat on the holder's share
of the company's zakatable assets, computed from this data
model as `(cash_and_liquid_assets + accounts_receivable) /
shares_outstanding` per share; paid-out dividends are the
holder's cash and are never added to the share base. Every
moving parameter (price, nisab metal price, calendar, hawl
basis) is an explicit input with source and date; missing
company figures return `insufficient-data` with the inputs
named, and no estimation proxy (NZF 25% / ZakatCalc 30%) is
ever substituted silently. The benchmark
(`scripts/sharia_zakat_benchmark.py`, `docs/sharia-zakat.md`)
matches both published worked examples it could run
(Tedawal exactly; AskZakariya within the source's own
rounding) and records Kashif's and Borsa Halal's calculators
as unavailable with the attempts on record.

## Adding a standard

Add one JSON file to `scripts/sharia_rules/` (activity screen, ratio
definitions with numerator/denominator/threshold, parameters,
purification definition, sources, documented conflicts) plus tests.
A ratio's numerator may name one field or a list of fields to sum
(MSCI's and FTSE's composite numerators), and a purification
definition may be ratio-only (`per_share_definition` null) where
the standard publishes no per-share figure — both forms were added
with issue #169 and every earlier rule set evaluates identically
under them. Entry/exit buffers are recorded as per-ratio `buffers`
metadata where a standard defines them (MSCI); they govern index
membership, not the screening threshold. The packs added in
issue #169 (MSCI, MSCI_M, FTSE, Islamicly) needed no other
engine change; S&P Shariah / DJIM remain draft-disabled under
`scripts/sharia_rules_draft/` until their pin gate is met.

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
