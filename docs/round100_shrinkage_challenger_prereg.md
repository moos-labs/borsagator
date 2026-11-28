# Round 100: shrinkage of frozen v2 toward a per-name empirical-quantile baseline, pre-registration

Status: REGISTRATION, written before any shrinkage value is computed or scored. Origin: INS-IMPROVE-100 item 3 (Moos, Slack 1795847457.168009, relayed to the author, not read by the author; full text relayed by the parent). The author chose every design constant below unless it says otherwise. Moos accepted the width-family adjacency: this changes the combination, not v2's input. Nothing here edits scripts/ensemble.py or any frozen value. Shadow challenger only, not an adoption.

## What was read, and what was not
- Opened this round: benchmarks/score_adoption_594.py `range_skill` (RangeSkill = 1 - mean interval score of the arm / mean interval score of the naive-range entrant), benchmarks/replay_band_candidates.py `build_rows` and `half_pct`, scripts/ensemble.py lines 94 and 1540 (V2_BAND_K = day 1.15, week 1.28, month 1.20; half = V2_BAND_K x vol60_h x RISK_MULT). So v2 is the band [-half, +half] around 0 in percent, and RangeSkill is scored against the stored naive-range band. The claim "v2 is near the baseline" is NOT used anywhere in this document.
- Not opened: the OHLCV layout under the archive (ohlcv/yahoo) beyond its directory name, and the 1-47 cell calendar. Both are read by the scorer's listing step, which prints counts before any statistic.

## Baseline, defined from scratch (author's choice)
For name i, horizon h in {day, week, month}, cutoff C with base date B (the cutoff close, as in the capture):
- Sessions per horizon: S_h = 1, 5, 21 (the repo's SESSIONS table, the same one `half_pct` uses).
- Realised moves: for every session t in the name's OHLCV close series, m(t) = 100 x (close(t + S_h) / close(t) - 1). Overlapping windows, simple percent move, same unit as `real` in the rows.
- Window: the 250 most recent sessions ending on or before B whose END close is dated on or before B (so every m(t) used had matured at B; nothing after B is read). Fewer than 125 usable moves: the (name, cutoff, horizon) pair is excluded from the challenger with reason "short history" and listed individually.
- Quantiles: q_lo = 10th percentile and q_hi = 90th percentile of those moves, linear interpolation between order statistics (index (n-1) x p, standard definition). 10/90 is the author's choice to match the 0.75-0.85 coverage target of the loop bar; it is a fixed constant and is never tuned.
- Dividend-gap rows and immature rows follow the existing row builder (rows with a dividend gap or not matured are not rows).

## Challenger (exact)
Frozen v2 edges: L_v2 = -half, U_v2 = +half, half = the stored v2 half-width in percent (computed by the existing `half_pct`, never refit).
Challenger edges per horizon h: L = a_h x L_v2 + (1 - a_h) x q_lo, U = b_h x U_v2 + (1 - b_h) x q_hi, with two weights per horizon, a_h and b_h in [0, 1] (so 6 weights in total, 2 per horizon). If the resulting L >= U the row is scored with the v2 interval and listed with reason "crossed edges".
Weights are frozen after the fit, one pair per horizon, shared by all names and cutoffs.

## Fit (cells 1-47 only)
- Objective: mean interval score (the repo's `winkler_is`, the same score RangeSkill uses) of the challenger over covered training rows of horizon h, minimised over the grid a, b in {0, 0.05, ..., 1.0} (21 x 21 per horizon). Ties go to the larger weight (nearer v2). Grid and tie rule are the author's, fixed now.
- Covered rows: horizon-h rows from cells 1-47 that have a realised close, that pass the "short history" rule, and whose realised close is dated BEFORE 2025-08-15 (freeze-date rule, applied here by the author because the same leak was found in #961: cells 44-47 realise about 2025-10-29/30, after the earliest scored cutoff 2025-08-15). Rows failing a rule are excluded from the fit, do not count toward the threshold, and are listed individually with cutoff, name, horizon and reason ("no realised close", "close after freeze date", "short history").
- Fewer than 100 covered rows for a horizon: no weights are fit for that horizon, the challenger is skipped there, and the run reports counts only. The covered-row count per horizon is printed first.
- Cells 48-90 and 91+ never change a weight.

## Windows
- Fit: cells 1-47. Descriptive: cells 48-90, counts and paired RangeSkill delta (challenger minus frozen v2, same rows), coverage, cutoff-clustered bootstrap, no verdict word. Score: untouched cells 91+ only, never loaded before this document is merged. No verdict-cell origin is read for smoke tests (use pre-2025-10-20 contexts).

## Intervals and loop bar
95% percentile bootstrap resampling CUTOFF DATES with replacement, 5000 reps, seed 20261125, default reps only (any other `--reps` refused before loading inputs). A horizon is KEPT only when, on untouched cells, (1) the challenger-minus-v2 RangeSkill cutoff-clustered CI lower bound > 0, (2) the cutoff-clustered coverage CI overlaps [0.75, 0.85] with width <= 0.15, and (3) at least 10 cutoff clusters back the horizon (a cluster counts only when every intended row of that cutoff has a realised close; a partly mature cluster does not count, and the single KEEP decision uses only clusters fully mature at the decision date). Fewer than 10 clusters: COUNTS ONLY, no coverage, skill or CI printed or written. Rows with no realised close are excluded from scoring entirely and listed individually. A KEEP is not an adoption. Cells 91+ hold few clusters today, so no KEEP is reachable until the forward weekly schedule (#953) accrues clusters.

## Known limits (author)
- Per-name quantiles from 250 overlapping sessions are noisy for the month horizon (about 12 independent windows); the 125-move rule only guarantees overlapping count.
- The baseline uses the name's own recent unconditional moves, so it is a width-and-centre object. Adjacency to the closed width family is accepted by Moos; the argument for it is only that six weights replace re-estimation of volatility.
- The panel is about 6 to 8 large-cap names; descriptive read has 8 cutoff dates.
- Weights are shared across names. The fit cannot use any cell whose realised close post-dates 2025-08-15.

## Listing-step result (a calendar and count read, no outcome scored; added after the build)
Running `fit` on the archive (cells 1-47, panel including NVDA) gave 138 usable rows, 46 per horizon, of which 42 per horizon are covered after the freeze-date rule (4 per horizon have a realised close on or after 2025-08-15). Each horizon is below the registered 100 covered rows, so under the rule above NO weights are fit and the challenger is COUNTS ONLY on every horizon. The 100 threshold was copied from #961; it cannot be met per horizon with this panel. This is reported, not changed: lowering the threshold, pooling horizons, or sharing one weight pair across horizons are each a change to this registration and need a decision.
