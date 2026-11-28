# Round 104: lower-edge shrinkage challenger, scored on WEEK only (pre-registration)

Status: pre-registration, committed before any 91+ cell is read. Decision to build this design: Moos (Slack 1795853725.590089, relayed to the author, not read by the author). Design and code: the author.

## Why this exists, and what is post hoc
The #966 challenger (one shared pair, a = 0.1, b = 1.0, frozen) showed a week RangeSkill diff of +0.107 on cells 48-90 (descriptive), with day -0.002 and month -0.062. This challenger narrows the claim to the week horizon. **The week-only scope is a POST HOC choice, made after seeing the cells 48-90 descriptive.** It is not derived from the training window. Day and month are reported as COUNTS ONLY and are never KEEP-eligible. The design does not lower any gate: a per-horizon fit is not possible (42 covered rows per horizon is below the 100-row gate), and that gate is not loosened after seeing the result.

## Design (fixed now)
- Interval: lower edge = a x (-half) + (1 - a) x q_lo; upper edge = the frozen v2 upper edge (b = 1 fixed). q_lo, half, baseline window and crossed-edge fallback (v2 interval, listed row by row) are exactly as in the #966 pre-registration. The #966 mixing code is reused unchanged.
- One parameter a, fit on the POOLED covered rows (day, week, month) of cells 1-47 only, never on scored cells. Grid 0, 0.05, ..., 1.0 (21 values), objective mean interval score (the repo's winkler_is, the score RangeSkill uses), ties to the larger a.
- Covered rows: same rules as #966 (realised close dated before the freeze date 2025-08-15, short-history rule). Gate: at least 100 pooled covered rows, otherwise no fit, counts only. Post-fix count on the archive: 124 pooled covered rows (day 42, week 42, month 40), after the #966 reference-set fix (Amendment 3 there). Pooled rows from one name and cutoff share realised paths, so they are not independent (author caveat).
- Fit result on cells 1-47 (author run): a = 0.1, from 124 covered rows. The pair-level result matches the #966 fit (the #966 fit also put b at the grid edge, 1.0).
- Descriptive on cells 48-90: week n = 43, 8 cutoffs, challenger RangeSkill +0.106, v2 -0.000, diff CI [0.068, 0.142], coverage 0.814 (CI [0.689, 0.932]). Descriptive only, not evidence for KEEP.

## Scoring rule (untouched 91+ cells, week rows only)
- Data: cells 91+ only, first read after this document is merged. No verdict-cell origin is loaded before then.
- Statistics: challenger-minus-v2 mean RangeSkill and the challenger's pooled coverage, each with a 95% two-sided percentile bootstrap CI resampling cutoff dates with replacement, 5000 reps, seed 20261125, default reps only (other values refused before loading).
- KEEP needs all four: (1) lower bound of the RS-diff CI > 0; (2) the coverage CI overlaps [0.75, 0.85]; (3) coverage CI width <= 0.15; (4) at least 10 fully mature cutoff clusters.
- Cluster counting: a cutoff cluster counts only when every intended row of that cutoff (one week row per capture of that cutoff) has a realised close; a partly mature cluster does not count, and the single KEEP decision uses only clusters fully mature at the decision date. No eligibility filter applies to the intended set: a captured ticker whose week row is dropped (capture rejection, v2_sigma missing, or no realised close) stays intended, so its cluster is not mature. The rule is week-only. Rows without a realised close are excluded from scoring entirely and listed individually.
- Fewer than 10 fully mature clusters: COUNTS ONLY, no coverage, skill or CI printed or written.
- Day and month: counts only. A KEEP is not an adoption.

## Code and tests
benchmarks/score_week_lower_edge.py (modes fit, describe, score), scripts/test_week_lower_edge.py (12 checks: pooled 99/100 boundary, all horizons pooled, freeze date, tie to larger a, b fixed, cluster maturity, counts-only below 10 clusters, refusals; mutants on the gate, tie rule, maturity rule and cluster threshold are caught).

## Known limits
- Same overlapping-path and small-panel limits as #966 (6 names, 8 cutoffs in 48-90, NVDA is a US name).
- Few untouched clusters exist today, so no KEEP is reachable until the forward weekly schedule accrues at least 10 fully mature clusters.
