# Round 98 (2): Wikipedia attention tilt, pre-registration DESIGN draft

Design only. No scorer, no data read, no implementation. Written before any attention series is joined to any cell. Source of the request: Moos Slack 1795840280.285049 (thread 1795818091.610649), relayed to me by the parent agent, not read by me. Candidate for the shadow tilt line only; never a width input, never ensemble.py or frozen values.

## Panel (the accepted coverage list)
17 names with an ar.wikipedia page and a pageview series, from the coverage check of 28 Nov 2026 (ar.wikipedia API, per-article daily pageviews, 2024-01-01 to 2026-11-22; created dates all before 2024 except MASR 2026-05-01):

COMI, ETEL, ORAS, TMGH, SWDY, JUFO, FAIT, HRHO, ORWE, EGAL, EFIH, ORHD, EGAS, AMOC, SKPC, EFID, MCQE.
- EFID has no returned series before 2024-10-17: its earlier days are MISSING, never zero.
- MCQE has 611 non-zero days of 964; zero-view days are real zeros, missing days are missing.
- MASR is dropped (page created 2026-05-01, no history for training cells). FAITA shares FAIT's page and is not a separate panel name.
- Names with no page, no name, or search-only absence are dropped and listed, never imputed: ACGC ATQA MPCO MTIE OCDI PHDC ARCC ETRS IFAP ISPH SAUD ADIB RMDA, and CLHO FAITA ICFC LCSW RACC (no Arabic name in EGX_COMPANIES). The page titles are listed in the table under "Panel page titles" below (live-verified 28 Nov 2026); they are pinned in the scorer's panel file before scoring.
- Known weakness: median daily views are 1 to 65, five names at 4 or fewer. Counts are small and noisy at a weekly horizon.

### Pageview API request (fixed, FIX-961k F1)
Endpoint: Wikimedia REST `metrics/pageviews/per-article/ar.wikipedia/{access}/{agent}/{title}/daily/{start}/{end}`, with access = `all-access` and agent = `user`, for BOTH the coverage check and scoring. Titles are the pinned titles in the table below, granularity `daily`, dates UTC. The agent filter `user` is a design choice of the author (not read from a Moos decision): it is the one that reproduces the stored coverage figure (MCQE 611 non-zero of 964 days, checked live 28 Nov 2026 on all-access/user; all-access/all-agents returns 964 of 964 non-zero for the same title and range, so that coverage note used `user`). No other access or agent filter is used, and a scorer that cannot fetch with exactly these two filters reports counts only.

### Pageview vintage (fixed, FIX-961l M1)
The design fetches the full daily series once from the current Wikimedia API, with no dated snapshot, so a fetched count is the count as corrected today, not necessarily the count that existed at the cutoff. Per the CodeRabbit review 6097786559 (relayed, not read by me, and not re-verified here), Wikimedia corrected pageview data from 20 March 2025 with a new bot-detection heuristic and finished the backfill on 8 October 2025. CHOICE (the author's, for Moos to review): option (b), exclusion. Option (a), dated snapshots captured at or before each cutoff, cannot be built for past cutoffs, because no snapshot of those dates exists.
- Rule: a cutoff C is EXCLUDED, for every name and every horizon, if C < 2025-10-08 AND its 28-day lookback C-28 .. C-1 contains a day on or after 2025-03-20. Reason "pageview vintage": the lookback holds a day that was corrected after C.
- Consequence by dates: the lookback of C ends at C-1, so C is excluded exactly when C-1 >= 2025-03-20, that is C from 2025-03-21 through 2025-10-07 inclusive. This includes the earliest scored cutoff 2025-08-15 and any later cutoff before 2025-10-08. Cutoffs on or after 2025-10-08 are not excluded by this rule: the backfill was finished before them, so the series fetched later carries the same heuristic the cutoff-day series would have had. Cutoffs with C <= 2025-03-20 are not excluded.
- Every excluded cutoff is listed individually in the registration and in the scorer output with its cutoff date and reason "pageview vintage", and none counts toward the 100-pair threshold or the 10-cluster threshold. The two boundary dates (2025-03-20, 2025-10-08) are constants fixed here from the review; if they are wrong, the registration must be amended BEFORE the freeze.
- Every fetch records its fetch date in the scorer output.

### Panel page titles (added for FIX-961j, live check 28 Nov 2026)
Exact ar.wikipedia article titles for the panel, so the mapping is reproducible before the registration freeze. Method (mine): for each ticker, the Arabic EGX name from `EGX_COMPANIES` in `worker/egx_harvest.py` was searched live on ar.wikipedia (MediaWiki API `list=search`, namespace 0, top 4), the candidate title was then fetched with `prop=info|extracts|pageprops` (page exists, is not a redirect, is not a disambiguation page, and its introduction names the company). All 18 rows below passed that check on 28 Nov 2026; the page text was read, not guessed. Where the EGX name is not itself the article title, the article was chosen from the search results and the intro (COMI: the bare EGX name redirects to a disambiguation page, so the article is the "(مصر)" page; TMGH: `طلعت مصطفى` is the person's page, the company page is `مجموعة طلعت مصطفى`; EGAS: `غاز مصر (شركة)`).

| Ticker | EGX Arabic name (EGX_COMPANIES, worker/egx_harvest.py) | ar.wikipedia page title (verified) | pageid | Wikidata |
|---|---|---|---|---|
| COMI | البنك التجاري الدولي | البنك التجاري الدولي (مصر) | 316534 | Q5152506 |
| ETEL | المصرية للاتصالات | المصرية للاتصالات | 236024 | Q1583794 |
| ORAS | اوراسكوم كونستراكشون بي ال سي | أوراسكوم كونستراكشون | 194889 | Q1370287 |
| TMGH | طلعت مصطفى | مجموعة طلعت مصطفى | 260944 | Q7678762 |
| SWDY | السويدي اليكتريك | السويدي اليكتريك | 896999 | Q5367528 |
| JUFO | جهينة للصناعات الغذائية | جهينة للصناعات الغذائية | 2813167 | Q15229827 |
| FAIT | بنك فيصل الاسلامي المصري | بنك فيصل الإسلامي المصري | 122632 | Q6745525 |
| HRHO | المجموعة المالية هيرمس | المجموعة المالية هيرميس القابضة | 4948746 | Q1299174 |
| ORWE | النساجون الشرقيون للسجاد | النساجون الشرقيون | 157839 | Q12194339 |
| EGAL | مصر للالومنيوم | مصر للألومنيوم | 40995 | Q310138 |
| EFIH | اي فاينانس للاستثمارات المالية والرقمية | إي فاينانس للاستثمارات المالية والرقمية | 9032746 | Q115764917 |
| ORHD | اوراسكوم للتنمية مصر | أوراسكوم للتنمية مصر | 194902 | Q1761055 |
| EGAS | غاز مصر | غاز مصر (شركة) | 1532310 | Q12229329 |
| AMOC | الإسكندرية للزيوت المعدنية | أموك | 1517779 | Q12180616 |
| SKPC | سيدى كرير للبتروكيماويات - سيدبك | سيدبك | 1534652 | Q12217565 |
| EFID | ايديتا للصناعات الغذائية | إيديتا | 3298300 | Q108248560 |
| MCQE | مصر للاسمنت - قنا | مصر للأسمنت – قنا | 1272869 | Q12179762 |
| MASR | مدينة مصر للاسكان والتعمير | مدينة مصر للإسكان والتعمير | 10398486 | Q129003775 |

Count reconciliation: the panel above is 17 names (COMI to MCQE). The review's 18 is the same 17 plus MASR, which has a page (listed last, verified) but is DROPPED because its page was created 2026-05-01 and has no history for the training cells. FAITA shares the FAIT page and is not a separate name. So 17 are kept and 1 is dropped; no name is unaccounted for.

UNVERIFIED: the coverage run of 28 Nov 2026 (the source of the "17 with a pageview series" list) left no title list in the repository or its outputs, so that the titles above are exactly the ones that run queried is UNVERIFIED. They are what a live lookup returns today; the 17-name panel and the per-name pageview availability (EFID gap, MCQE zero days, MASR creation date) are carried over from the coverage note above and were not re-run here. Pageview series are not re-fetched in this edit.

## Feature (fixed now)
For cutoff date C and name i: A(i,C) = log((S7 + 1) / (S28/4 + 1)), where S7 is the sum of daily views for the 7 days C-7 .. C-1 and S28 the sum for the 28 days C-28 .. C-1. Strictly before the cutoff day, and point in time only under the vintage rule above (cutoffs whose lookback holds a day corrected after the cutoff are excluded). Lookback 7 over 28 is FIXED (Moos decision, Slack 1795841110.607749, relayed, not read).

## Rank scaling (exact)
- Eligible names at cutoff C: panel names that pass the minimum-history rule below and have a v2 centre and a positive v2 half-width for that name's cell at cutoff C. Let n = their count. If n < 6 the cutoff gets no tilt (k-shift 0) and is listed with the reason "n<6".
- z is computed ONLY for cutoffs with n >= 6. For n = 1 to 5 (and n = 0) z is never computed, so the division by (n-1)/2 cannot occur; those cutoffs get the v2 interval unchanged.
- r(i) = average rank of A(i,C) among the n eligible names, ascending, 1..n. Ties get the average of the ranks they span (exact float equality of A after rounding to 12 decimals).
- z(i) = (r(i) - (n+1)/2) / ((n-1)/2). Range [-1, +1], mean 0. The endpoints -1 and +1 apply ONLY when the extreme attention values are untied (the lowest-attention name then sits at -1 and the highest at +1). With tied ranks, which use the average rank, values fall inside the endpoints, and z = 0 for every name when all attention values are tied (for example six names at average rank 3.5).
- Tilt: the v2 interval centre moves by d(i) = k * z(i) * w(i), where w(i) is the v2 half-width for that cell. The interval is moved, not widened: both edges shift by d(i), the width is unchanged. Non-eligible names keep the v2 interval unchanged.

## Slope fitting (exact, before any scoring)
- Target: y(i,C) = (realised close - v2 centre) / w(i), the standardised miss of the v2 centre, in half-width units. Baseline treatment of v2: v2 is the k = 0 arm; its centre and half-width are read as stored for the cell and are never refit.
- Covered-pair rule (explicit): a training pair (cell, name) is COVERED, and enters the fit, only if its cutoff has n >= 6 eligible names (so z is defined) and the name is one of those n, AND the pair has a realised close (y is undefined without it and nothing is imputed). Pairs from cutoffs with n < 6, including n = 2 to 5, are EXCLUDED from both sums and do NOT count toward the 100-pair threshold; they are listed individually with cutoff, n and reason "n<6". Eligible pairs with no realised close (for example an immature cell) are likewise excluded from both fit sums, do NOT count toward the 100-pair threshold, and are listed individually with cutoff, name and reason "no realised close". They contribute nothing to the fit.
- Freeze-date rule (explicit): every realised close used for fitting must be dated BEFORE 2025-08-15, the earliest scored cutoff. A training pair whose realised close is dated on or after 2025-08-15 (for example cells 44-47, realised about 2025-10-29/30) has no usable close for the fit and is excluded from both sums, does not count toward the 100-pair threshold, and is listed individually with cutoff, name and reason "close after freeze date". If this restriction leaves fewer than 100 covered pairs, the tilt fit is skipped under the counts-only rule below, and the number of covered pairs left is counted and reported.
- Scoring membership (explicit): a pair with no realised close has no realised value and cannot enter RangeSkill or the coverage denominator. It is EXCLUDED FROM SCORING ENTIRELY: no RangeSkill contribution, no coverage contribution, listed individually with cutoff, name and reason "no realised close". A cutoff cluster counts toward the 10-cluster threshold ONLY when every intended row of that cutoff (every (name, horizon) pair the scorer would score at that cutoff, after the eligibility rules) has a realised close. A partly mature cluster does not count, so the single KEEP decision uses only clusters fully mature at the decision date; rows of a partly mature cluster stay listed individually with reason "cluster not fully mature" and are not scored until the cluster is fully mature.
- Objective: least squares through the origin on the covered pairs from cells 1-47 under that rule: k_hat = sum(z*y) / sum(z*z). No intercept, equal weight per pair.
- Sign is estimated and then frozen. Magnitude is clipped to |k| <= 0.25 half-widths (a design constant fixed now, not tuned). If sum(z*z) = 0 or fewer than 100 covered training pairs (by the covered-pair rule above) exist, no tilt is fit and the run reports counts only.
- The frozen k is the only fitted value; cells 48-90 and 91+ are never used to change it.

## Lookback and minimum-history rule (up front)
A cell is scorable for a name only if all 28 days C-28..C-1 are AVAILABLE for that name (below). Series start 2024-01-01, so any cutoff before 2024-01-29 fails. Rule applies per (cell, name), not per cell.

### Zero versus missing (fixed, FIX-961k F2)
The API may omit zero-view days, and an omitted day can also be data that was never loaded, so an omitted day is classified by an independently checkable rule, applied by the scorer BEFORE covered pairs are counted. For cutoff C, F(i), Z(i) and the LOADED set are computed from the fetched series (all-access/user, one fetch for the whole range) TRUNCATED to days strictly before C (FIX-961l M2): a day on or after C is never used as confirming evidence. Let F(i) be the first and Z(i) the last returned day of name i in that truncated series. Let the LOADED set be the days before C on which the API returns a row for at least one OTHER panel name (the panel itself is the check that the day was loaded; a row with 0 views counts as a returned row).
- A returned day is available with its returned value (a returned 0 is a real zero).
- An omitted day D is a CONFIRMED ZERO (value 0, available) only if F(i) <= D <= Z(i) AND D is in the LOADED set.
- An omitted day whose only confirming evidence lies on or after C (for example a later returned row for name i, or a later row for another name) is UNAVAILABLE, not zero.
- Every other omitted day is UNAVAILABLE: a day before F(i) (the EFID gap before 2024-10-17 is unavailable by this rule, never zero), a day after Z(i), or a day that is not in the LOADED set (nothing loaded for any other name).
- A (cell, name) pair is covered only if all 28 days C-28..C-1 are available. The scorer lists each excluded pair with cutoff, name, and the first unavailable day, reason "28-day history unavailable".
- Verifiable by anyone re-fetching the same 17 series with the same two filters; the rule adds no parameter and changes no panel, no 28-day length, no slope fit and no number in Amendment 1. The 2025-08-15 freeze and the n >= 6 and 100-pair rules are untouched.

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

## Amendment 1 (pooled slope fit across horizons)
Decision (Moos, Slack 1795850259.729959, relayed to the author, not read by the author): the slope is fit POOLED across the three horizons. One shared slope k_hat = sum(z*y) / sum(z*z) over the pooled covered pairs of all horizons from cells 1-47, same covered-pair rule, freeze-date rule, |k| <= 0.25 clip and no-intercept least squares as above. The gate is 100 covered pairs pooled (fewer, or sum(z*z) = 0: counts only). Pooled covered-pair count (author computation from the archive rows and OHLCV closes, after dropping the 2023-12-29 cutoff, the 2025-09-30 cutoff having 4 names and no close before the freeze date): 6 cutoffs x 6 names = 36 per horizon, 108 pooled. This is an upper bound until pageview completeness for all 6 names is checked at fit time (n >= 6 needs all 6 eligible). Per-horizon descriptive deltas on cells 48-90 and in scoring are still reported separately using the one shared slope, each on its own eligible covered-pair sample, whose actual size is printed with the result. The 36 per horizon quoted in this amendment is the TRAINING sample (cells 1-47: 6 cutoffs x 6 names); it is not a cap and not a selection rule for descriptive or scoring windows. Every eligible pair in a window is used (a pair is eligible by the covered-pair and no-close rules above), with no subsampling. Non-independence caveat (author): the day, week and month rows of the same name and cutoff share realised paths, so the 108 pooled pairs are not independent. The loop bar is unchanged: any KEEP needs untouched 91+ cells with >= 10 fully mature cutoff clusters.
