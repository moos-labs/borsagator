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
For cutoff date C and name i: A(i,C) = log((S7 + 1) / (S28/4 + 1)), where S7 is the sum of daily views for the 7 days C-7 .. C-1 and S28 the sum for the 28 days C-28 .. C-1. Strictly before the cutoff day (point in time). Lookback 7 over 28 is FIXED (Moos decision, Slack 1795841110.607749, relayed, not read).

## Rank scaling (exact)
- Eligible names at cutoff C: panel names that pass the minimum-history rule below and have a v2 centre and positive v2 half-width for the cell. Let n = their count. If n < 6 the cutoff gets no tilt (k-shift 0) and is listed with the reason "n<6".
- z is computed ONLY for cutoffs with n >= 6. For n = 1 to 5 (and n = 0) z is never computed, so the division by (n-1)/2 cannot occur; those cutoffs get the v2 interval unchanged.
- r(i) = average rank of A(i,C) among the n eligible names, ascending, 1..n. Ties get the average of the ranks they span (exact float equality of A after rounding to 12 decimals).
- z(i) = (r(i) - (n+1)/2) / ((n-1)/2). Range [-1, +1], mean 0, so a cutoff with n names has the lowest-attention name at -1 and the highest at +1.
- Tilt: the v2 interval centre moves by d(i) = k * z(i) * w(i), where w(i) is the v2 half-width for that cell. The interval is moved, not widened: both edges shift by d(i), the width is unchanged. Non-eligible names keep the v2 interval unchanged.

## Slope fitting (exact, before any scoring)
- Target: y(i,C) = (realised close - v2 centre) / w(i), the standardised miss of the v2 centre, in half-width units. Baseline treatment of v2: v2 is the k = 0 arm; its centre and half-width are read as stored for the cell and are never refit.
- Covered-pair rule (explicit): a training pair (cell, name) is COVERED, and enters the fit, only if its cutoff has n >= 6 eligible names (so z is defined) and the name is one of those n. Pairs from cutoffs with n < 6, including n = 2 to 5, are EXCLUDED from both sums and do NOT count toward the 100-pair threshold; they are listed individually with cutoff, n and reason "n<6". They contribute nothing to the fit, and at scoring time they are scored with the v2 interval unchanged.
- Objective: least squares through the origin on the covered pairs from cells 1-47 under that rule: k_hat = sum(z*y) / sum(z*z). No intercept, equal weight per pair.
- Sign is estimated and then frozen. Magnitude is clipped to |k| <= 0.25 half-widths (a design constant fixed now, not tuned). If sum(z*z) = 0 or fewer than 100 covered training pairs (by the covered-pair rule above) exist, no tilt is fit and the run reports counts only.
- The frozen k is the only fitted value; cells 48-90 and 91+ are never used to change it.

## Lookback and minimum-history rule (up front)
A cell is scorable for a name only if all 28 days C-28..C-1 exist in that name's series (no missing days). Series start 2024-01-01, so any cutoff before 2024-01-29 fails. Rule applies per (cell, name), not per cell.

## Drop rule for the 2023-12-29 training cells
The 7 training cells with cutoff 2023-12-29 (no pageview history at all, per Moos) are DROPPED from the fit. Any other training cell whose cutoff is before 2024-01-29 is dropped by the same rule. Every dropped cell and every dropped (cell, name) pair is listed individually with its cutoff and reason, in the doc that the scorer emits; none is imputed or back-filled. I have not read the cell calendar for this draft, so the exact count of additional dropped training cells is UNKNOWN until the scorer runs the listing step (a calendar read, not an outcome read).

## Windows
- Fit: cells 1-47 only, covered (cell, name) pairs only. Fit the slope k and its sign.
- Descriptive: cells 48-90. Counts and paired delta vs frozen v2 on the same rows, no verdict word.
- Score: cells 91+ only, never loaded before this doc is merged. No verdict-cell origin is read for smoke tests (use pre-2025-10-20 contexts).

## Interval definitions
Both intervals are 95% two-sided percentile bootstrap intervals, resampling CUTOFF DATES (the cluster) with replacement, 5000 repetitions, seed 20261125; every row of a drawn cutoff date is carried with it. Report only these default-rep CIs.
- Challenger-minus-v2 interval: statistic = mean over rows of (RangeSkill of the tilted interval minus RangeSkill of v2) on the same rows.
- Coverage interval: statistic = pooled share of scored rows whose realised value lies inside the tilted interval. Width = upper minus lower.

## Loop bar for the scored window
KEEP-eligible only if: the lower bound of the challenger-minus-v2 interval is > 0, AND the coverage interval overlaps [0.75, 0.85] with width <= 0.15, AND >= 10 cutoff clusters. Fewer than 10 clusters: COUNTS ONLY (counts and reasons, no statistic).

## Decision time (one point)
KEEP is evaluated ONCE: when the forward weekly schedule (#953) first reaches 10 scored cutoff clusters in cells 91+. Before that, only counts are printed. After that single decision, later cluster counts (for example 20, 30) are printed as descriptive confirmation only and cannot create a KEEP; a changed decision needs a new registration doc. If Moos prefers an anytime-valid procedure or a split of the error budget over several looks instead, that replaces this section before the scorer is written.

## Tests (when built)
Fixed synthetic series and cells, *main* guard, Suite class, mutation checks with boundary mutants for: lookback off-by-one (C-1 vs C), 28-day completeness, 2024-01-29 boundary, +1 smoothing, missing versus zero, per-cutoff demeaning, window gating (47/48, 90/91).

## Decisions recorded (Moos, Slack 1795841110.607749, relayed, not read)
Panel shadow build GO; lookback 7 over 28 fixed; en.wikipedia pages OUT. Review fixes: rank scaling, slope fitting, decision time and CI definition are specified above (CodeRabbit review 6095846338 findings 1-4, relayed, not read by me).
