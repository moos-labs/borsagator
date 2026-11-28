# Round 98 (2): Wikipedia attention tilt, pre-registration DESIGN draft

Design only. No scorer, no data read, no implementation. Written before any attention series is joined to any cell. Source of the request: Moos Slack 1795840280.285049 (thread 1795818091.610649), relayed to me by the parent agent, not read by me. Candidate for the shadow tilt line only; never a width input, never ensemble.py or frozen values.

## Panel (the accepted coverage list)
17 names with an ar.wikipedia page and a pageview series, from the coverage check of 28 Nov 2026 (ar.wikipedia API, per-article daily pageviews, 2024-01-01 to 2026-11-22; created dates all before 2024 except MASR 2026-05-01):
COMI, ETEL, ORAS, TMGH, SWDY, JUFO, FAIT, HRHO, ORWE, EGAL, EFIH, ORHD, EGAS, AMOC, SKPC, EFID, MCQE.
- EFID has no returned series before 2024-10-17: its earlier days are MISSING, never zero.
- MCQE has 611 non-zero days of 964; zero-view days are real zeros, missing days are missing.
- MASR is dropped (page created 2026-05-01, no history for training cells). FAITA shares FAIT's page and is not a separate panel name.
- Names with no page, no name, or search-only absence are dropped and listed, never imputed: ACGC ATQA MPCO MTIE OCDI PHDC ARCC ETRS IFAP ISPH SAUD ADIB RMDA, and CLHO FAITA ICFC LCSW RACC (no Arabic name in EGX_COMPANIES). The page titles are the ones the coverage run used; they are pinned in the scorer's panel file before scoring.
- Known weakness: median daily views are 1 to 65, five names at 4 or fewer. Counts are small and noisy at a weekly horizon.

## Feature (fixed now)
For cutoff date C and name i: A(i,C) = log((S7 + 1) / (S28/4 + 1)), where S7 is the sum of daily views for the 7 days C-7 .. C-1 and S28 the sum for the 28 days C-28 .. C-1. Strictly before the cutoff day (point in time). Cross-sectional centre: A is demeaned per cutoff across the names that have it. Tilt = k * rank-scaled A, with the tilt scale k fitted on training cells only (below). Direction is not assumed: the sign of the slope is estimated on training and then frozen.

## Lookback and minimum-history rule (up front)
A cell is scorable for a name only if all 28 days C-28..C-1 exist in that name's series (no missing days). Series start 2024-01-01, so any cutoff before 2024-01-29 fails. Rule applies per (cell, name), not per cell.

## Drop rule for the 2023-12-29 training cells
The 7 training cells with cutoff 2023-12-29 (no pageview history at all, per Moos) are DROPPED from the fit. Any other training cell whose cutoff is before 2024-01-29 is dropped by the same rule. Every dropped cell and every dropped (cell, name) pair is listed individually with its cutoff and reason, in the doc that the scorer emits; none is imputed or back-filled. I have not read the cell calendar for this draft, so the exact count of additional dropped training cells is UNKNOWN until the scorer runs the listing step (a calendar read, not an outcome read).

## Windows
- Fit: cells 1-47 only, covered (cell, name) pairs only. Fit the slope k and its sign.
- Descriptive: cells 48-90. Counts and paired delta vs frozen v2 on the same rows, no verdict word.
- Score: cells 91+ only, never loaded before this doc is merged. No verdict-cell origin is read for smoke tests (use pre-2025-10-20 contexts).

## Loop bar for the scored window
Challenger and v2 on the same rows. KEEP-eligible only if: RangeSkill cutoff-clustered CI lower bound of (challenger minus v2) > 0, AND coverage CI overlaps [0.75, 0.85] with width <= 0.15, AND >= 10 cutoff clusters. Fewer than 10 clusters: COUNTS ONLY (counts and reasons, no statistic). Bootstrap 5000 reps, seed 20261125, clusters = cutoff dates. Quote only default-rep CIs. Cells 91+ currently hold fewer than 10 clusters, so the planned surface is the forward weekly schedule (#953) accruing clusters.

## Tests (when built)
Fixed synthetic series and cells, *main* guard, Suite class, mutation checks with boundary mutants for: lookback off-by-one (C-1 vs C), 28-day completeness, 2024-01-29 boundary, +1 smoothing, missing versus zero, per-cutoff demeaning, window gating (47/48, 90/91).

## Open decisions for Moos
1. Whether a panel of 17 names at these view counts is worth building (the pageview medians are low).
2. Lookback 7 over 28 days is my proposal, not a tuned choice; say if you want a different fixed pair before the doc is merged.
3. Whether the en.wikipedia pages (only 8 names have an ar-en link) are in or out: proposed OUT.
