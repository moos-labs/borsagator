# Forward confirmation for a technicals-tilt adoption (design)

INS-IMPROVE-001 round 23 item 2 (brief: Moos Slack 1795736150.489689).
Design only: no scorer, ledger or frozen value changes in this PR. The
rule below is a proposal for Muhammad's and the cycle's ruling, not a
registered rule.

## What the backtest reading is, and is not

On cells 73-102 (n=30 per horizon, 5 cutoffs, 6 tickers) the tilt reads
as week +0.015 and month +0.033 RangeSkill vs the naive band, day -0.003
(`benchmarks/score_tilt_technicals_594.py`). `benchmarks/audit_tilt_keep.py`
(round 23 item 1) shows the reading fails the 10-cluster bar, the
ticker-block view and the 0.15 coverage cap, and that the sign-flip leg
cannot pass at 5 clusters (smallest p 1/32). Per Muhammad's round-8
ruling it is therefore a lead, not an adoption. Forward confirmation is
the only fresh evidence: cells 73-102 are seen and are never pooled into
the forward verdict.

## What a forward test can use today (checked on main 2d9920ee and the
archive branch, 2026-11-27)

- `ledger/ledger.json` rows do NOT carry the tilt. `tilt_centre_pct` lives
  in each sweep's `ensemble.json` (`horizons.<h>.tilt_centre_pct`), found
  from the ledger row's `sweep` path (`sweeps/<date>/<dir>/ensemble.json`).
- Only a few sweep directories carry it, and the count grows with each
  sweep: 10 when this doc was first written, 12 at one later archive tip,
  14 at archive tip d6ab6b30 (2026-11-25: 5, 2026-11-26: 9, counted by
  reading `horizons.<h>.tilt_centre_pct` in every
  `sweeps/*/*/ensemble.json`). The 6 pending rows per horizon below are
  from the first 10 and were not re-joined for the later count. Of the 204 ledger rows, 6 per horizon (day, week, month,
  all still pending) join to a tilt-bearing sweep. None of the 48 matured
  rows does, so there is no forward history to score today.
- On the 10 day-horizon blocks the tilt moves the centre by -0.12 to
  +0.38 pp against band half-widths of 2.6 to 6.5 pp (observation from
  the 10 files, not a general claim): the tilt is a small re-centring.
- The ledger's published row has no sigma, so the naive band cannot be
  rebuilt from the ledger. The tilt band is the published band
  re-centred (`backtest_score.py`: `tilt +/- (range_high - range_low) / 2`),
  so it has the same width as the published band and only the centre
  differs.

## Proposed forward rows

A ledger row enters when ALL hold: `status == "matured"`, no
`dividend_gap`, its sweep's `ensemble.json` has a numeric
`tilt_centre_pct` for that horizon, and its `as_of` is on or after the
registration date. The join is read-only (no `ledger.py` change); a row
whose sweep file cannot be read is counted as an exclusion, never
dropped silently. Tilt band = published band re-centred on the tilt.

## Proposed statistic and rule (per horizon, then all three)

RangeSkill_fwd = 1 - mean Winkler(tilt band) / mean Winkler(published
band), alpha 0.2, same rows. The published band is the frozen v2 band,
so this is the "relative to frozen v2 on the same rows" comparison the
loop already requires, and since widths are equal it isolates the centre.

On one scoring at the pre-declared n, per horizon:
1. n >= 30 matured forward rows, >= 10 distinct tickers counted across
   all forward rows of that horizon (not per sweep), >= 10 cutoff
   clusters (distinct `as_of`). The cluster count is the binding limit,
   not n.
2. RangeSkill_fwd cutoff-clustered 95% CI lower bound > 0.
3. Coverage of the tilt band: cutoff-clustered CI overlaps
   [0.75, 0.85] with width <= 0.15 (`coverage_ci_ok`).
4. Reported beside, not gated: ticker-block CI, effective n, the
   `ci_audit` jackknife / sign-flip / wild CIs (sign-flip is attainable
   at 10 clusters, smallest p 1/1024).
5. Multiple testing: Holm across the 3 horizons (family 3). The p-value,
   defined here before registration, follows the loop convention
   (#805): one-sided bootstrap p from the same cutoff-clustered draws as
   the CI. Null: RangeSkill_fwd = 0. Alternative: RangeSkill_fwd > 0.
   p = (1 + #{draws with resampled RangeSkill <= 0}) / (1 + B), B =
   5000 (Phipson-Smyth +1, so p is never 0). Ties (draw exactly 0) count
   against the tilt, i.e. as <= 0. The Holm step-down compares the sorted
   p to 0.05/3, 0.05/2, 0.05/1. If Muhammad prefers a two-sided p or a
   different tie rule, that is an open ruling (below); this default is
   proposed, not ruled.
Adoption needs all three horizons to pass 1-3 and the Holm-adjusted p
< 0.05 on each. A day-horizon failure blocks adoption of the tilt as one
object; a horizon-specific tilt is a different, separately pre-registered
claim.

## Freeze and no-peeking

- Registration freezes the tilt definition at the `scripts/ensemble.py`
  commit hash named in the registration message. Any change to the tilt
  restarts the clock; rows from before the change are dropped.
- The scorer prints counts only (rows, tickers, clusters per horizon)
  until step 1 holds, as the sentiment ledger scorers do. One scoring,
  no re-fit, no re-scoring on a later, larger sample under the same
  registration.
- Seed fixed (`A.DEFAULT_SEED`), reps 5000.

## How long it takes (arithmetic, assumptions stated)

Assumption: one tilt-bearing sweep per EGX session (Sunday to Thursday),
at least 10 tickers across the forward rows of each horizon (the
tickers can rotate between sweeps), starting the next session after
registration. That cadence is the cycle's, and the tilt-bearing sweeps
so far are 5 to 9 tickers per date. Cutoff clusters needed = 10, so the 10th
cutoff is session 10. Verdict sessions after registration: day about 11,
week about 15, month about 31 (10th cutoff plus 1, 5 and 21 sessions).
With one sweep date per week these become 10 weeks for day, plus the
horizon. Fewer than 10 distinct tickers across the forward rows of a horizon
blocks rule 1 whatever the dates. Tickers per sweep do not need to reach
10 if the sweeps rotate through at least 10 between them.

## Prerequisites (cycle items, not done here)

1. A wide, daily-or-near-daily sweep cadence that keeps `tilt_centre_pct`
   in `ensemble.json` (it is present now).
2. A read-only forward tilt scorer implementing the join and rule above
   (a separate PR once the rule is ruled on).
3. A ruling on the open points: published-band comparison (vs naive-band
   in the backtest), Holm family of 3, all-horizons requirement, and
   MIN_CUTOFFS raise to 10 for future verdicts, and the p-value
   definition in rule 5 (one-sided, +1, ties against the tilt).
