# Sharia accuracy benchmark — first run (2026-11-18)

> Screening result under the named standard only, computed from the company's published financials. This is not a fatwa, and not religious or investment advice.
> نتيجة فحص وفق المعيار المذكور فقط، محسوبة من القوائم المالية المنشورة للشركة. ليست فتوى، وليست نصيحة دينية أو استثمارية.

Issue #172. Our Sharia engine (per-standard screening results) scored against the published classifications of Musaffa (AAOIFI), Faisal Securities (AAOIFI, spot market cap), Ostool (EGX33) and EGX33 index membership (ground truth), plus a purification comparison.

Covered universe: POUL.CA · Engine version: 1.0.0 · Generated: 2026-11-17T22:09:13Z

## Verdict agreement

| Source — standard | Status | Universe tickers | Determinate pairs | Agreement | Our insufficient-data |
|---|---|---|---|---|---|
| musaffa — AAOIFI (avg36m) | ok | 1 | 0 | — | 1 |
| faisal — AAOIFI (spot) | unavailable | 1 | — | — | — |
| ostool — EGX33 | ok | 1 | 0 | — | 1 |
| egx33 — EGX33 | ok | 1 | 0 | — | 1 |

Agreement % is shown as — wherever there are no determinate pairs: a percentage over zero pairs would be a fabricated accuracy figure.

## Per-ticker rows

### musaffa — AAOIFI (avg36m)

- **POUL.CA** — ours: `insufficient-data` · theirs: `non-compliant` (NOT HALAL) · outcome: `our-insufficient-data`
  Not comparable: our engine returned insufficient-data (missing inputs: activity.classification, avg_market_value_36m, interest_bearing_assets, interest_bearing_debt, non_compliant_revenue, total_revenue). Counted separately, never as agreement or disagreement.

### faisal — AAOIFI (spot)

Source unavailable at freeze time: Attempted 2026-11-18: the report PDF named in the issue (fbcbrokerage.com, dated 2024-03-31, financials through 2023-09-30) could not be retrieved with the fetch tooling available to this run — the fetch failed on the Arabic filename URL with a resolution error, and the run did not fall back to another route. No rows are recorded and none were fabricated. The parser (parse_faisal_text) is implemented and unit-tested against a synthetic excerpt; the next freeze should retry retrieval of the PDF.

### ostool — EGX33

- **POUL.CA** — ours: `insufficient-data` · theirs: `non-compliant` (غير متوافق) · outcome: `our-insufficient-data`
  Not comparable: our engine returned insufficient-data (missing inputs: activity.classification, avg_market_value_review_period, cash_and_liquid_assets, interest_bearing_assets, interest_bearing_debt, non_compliant_revenue, total_assets, total_revenue). Counted separately, never as agreement or disagreement.
  Hypothesis (not our engine's computation): on Ostool's own published percentages, this ticker breaches the EGX33 limits on interest-bearing deposits 40.0% > limit 33.0%; prohibited income 5.5% > limit 5.0%. If our input pipeline (issues #78/#110) lands equivalent financials, our EGX33 screen would be expected to reach the same verdict. Our engine has NOT computed this — its verdict today is insufficient-data.

### egx33 — EGX33

- **POUL.CA** — ours: `insufficient-data` · theirs: `non-compliant` (not an EGX33 constituent (derived from the complete frozen list)) · outcome: `our-insufficient-data`
  Not comparable: our engine returned insufficient-data (missing inputs: activity.classification, avg_market_value_review_period, cash_and_liquid_assets, interest_bearing_assets, interest_bearing_debt, non_compliant_revenue, total_assets, total_revenue). Counted separately, never as agreement or disagreement.

## Purification comparison

Comparable pairs: 0 · mean abs diff: None · max abs diff: None · mean rel diff: None
- POUL.CA — ostool publishes 5.5% (Ostool's published prohibited-income % — the non-compliant revenue share that AAOIFI-style purification applies to dividends.) Our purification ratio is not computable yet (engine verdict insufficient-data); the published figure is recorded for the first scored run.
- Witness musaffa: Musaffa publishes no per-stock purification ratio on its public stock pages (checked at freeze time); its purification figures sit behind its calculator/account.
- Witness nour_borsa: Attempted 2026-11-18: nourborsa.com's homepage renders as a JavaScript application shell and its per-stock Sharia/purification data sits behind the site's login; a web search surfaced no public per-stock page for POUL.CA. No login was attempted and nothing was scraped behind one. Recorded as an unavailable purification witness for this run.

## Method notes

- Scored against frozen snapshots in sharia/benchmark/sources/ (per-row source URL + retrieval date), never against a moving page.
- Our verdicts are re-computed by the engine from the covered-universe inputs at score time, per comparison configuration (AAOIFI avg36m / AAOIFI spot / EGX33).
- insufficient-data on our side is its own bucket, never agreement or disagreement; agreement % is null when there are no determinate pairs.
- No accuracy claim is made from this benchmark (issues #77/#79 rule): with the covered universe at one ticker and its balance-sheet inputs not yet wired (issues #78/#110), every comparison currently lands in the insufficient-data bucket — that IS the measured result.
