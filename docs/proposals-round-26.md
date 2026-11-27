# Proposal round 26: after the A and B screens (proposals only)

INS-IMPROVE-001, next proposal round after the hold was lifted (Muhammad,
Slack 1795741772.231139, relayed). Nothing here is GO'd, scored or
registered. Figures are from my own merged-branch runs on 2026-11-27
(PRs #847-#849, Yahoo close store at archive tip d6ab6b30, windows end
<= 2023-12-28, post-2021-09-05 regime unless stated); I re-read the code
paths named below.

## What the A and B screens say

- Proposal A (USD/EGP stress, #848): no reading beats frozen v2.
  Post-break RangeSkill day / week / month, beta 0.10: 0.010 vs v2 0.015,
  -0.002 vs 0.000, -0.001 vs -0.004; beta 0.20: -0.009 vs 0.015, -0.015 vs
  0.000, -0.006 vs -0.004. Smallest Holm-adjusted p 0.300.
- Proposal B (EEM / Brent / gold, #849): post-day RangeSkill 0.015 / 0.016
  / 0.016 vs v2 0.015. Four readings have Holm-adjusted p < 0.05 (BZ=F post
  day 0.017, BZ=F post week 0.009, EEM post day 0.022, GC=F post day 0.017).
- Method finding. `screen_band_models.reading_p` (used by every screen
  since round 24) tests H0 "RangeSkill of the candidate <= 0" through the
  cutoff-clustered bootstrap. It is a test of the candidate on its own, not
  of the candidate against frozen v2. When v2 itself scores 0.015 on post
  day, a candidate that equals v2 gets a small p. So a small Holm p in
  these screens can only restate v2's own skill; the three B readings above
  differ from v2 by about 0.001. The keep rule Muhammad set is relative to
  v2 on the same rows (P1), and the screens do not yet print that.

## Proposal A: paired delta against v2 for the round 24-26 screens (no new data)

- Source: none new. Reuses `screen_pairs` of `screen_market_factor.py`
  (18 readings), `screen_exog_factor.py` (18) and `screen_fx_stress.py`
  (12); the pair dicts already carry `is_v2` and `is_ch` on the same rows.
- Statistic: RangeSkill(candidate) minus RangeSkill(v2) on the same rows,
  cutoff-clustered bootstrap (same `R._boot` resampling, same seed
  constant), one-sided p for H0 delta <= 0, Phipson-Smyth +1. Family: the
  48 readings of the three screens (18 + 18 + 12), Holm over 48. Numbers
  only, no verdict key.
- Cost: under an hour; the screens run in about 20-30 s each. The
  existing `RangeSkill` definition is reused unchanged, so the delta is
  comparable with the printed columns.
- Value: it separates "better than v2" from "good in itself" for every
  screen already run, before any cell is scored. It is the check the
  A/B result above calls for, and it costs no data.
- Honest limit: with the 36-ticker store the delta CI will be wide
  (differences are about 0.001-0.02); the likely result is that nothing
  clears zero, which would close routes A and B and the round-24 screen
  with the right statistic.

## Proposal B: volume and turnover state as a width input (store data, non-price)

- Source (verified in the archive store, ohlcv/yahoo/*_CA.csv, column
  `volume`): 29 of 36 tickers have a non-zero volume on at least 90% of
  bars; 7 do not (ORAS_CA has non-zero volume on 3% of bars). The Yahoo
  `volume` column is a daily share count and is dated with its bar.
  Source of the claim: a direct count over the CSVs on 2026-11-27, not
  an external document.
- PIT rule: at a cutoff on date D use only bars dated before D (as the
  EGP=X screen).
- Feature: z of log(1 + mean volume over the last 20 bars) against the
  same ticker's earlier cutoffs (at least 8, else 0), band = v2 x
  exp(beta x clip(z, -3, 3)), beta in (0.10, 0.20), fixed grid, not
  fitted. Same builder as `screen_fx_stress.py`; tickers with less than
  90% non-zero-volume bars are excluded by rule, stated before the run.
  Family 12 = 2 betas x 3 horizons x 2 regimes, Holm over 12; the delta
  statistic from Proposal A is reported next to the existing p.
- Honest limit: this is still the names' own series (volume, not price),
  and low-liquidity names make volume a noisy proxy. Cheapest to run
  after A, because it reuses the same delta code.

## Proposal C: Ramadan and Eid calendar flag (source NOT yet verified)

- Idea: sessions around Ramadan and the Eid holidays have fewer sessions
  and a different trading pattern; widen or narrow windows that contain
  them. Information is deterministic and PIT-clean by construction (the
  calendar is known in advance).
- Source status: unverified. A civil (tabular) Islamic calendar gives
  dates within about one day of the observed ones; an official EGX
  holiday list per year would be exact. I have not fetched either, so I
  do not name one. First step is to verify a source for 2014-2023 and
  check it against the store's missing-session dates (a gap of 3+ days
  in the bar index around known holidays is a free check).
- Honest limit: about ten Ramadan periods in the history, so independent
  clusters are few. Rank low until the source is verified.

## Proposals C and D of round 25 (unchanged)

GDELT macro-theme rows (step 1 is #846; its screen follows the macro
rows) and the tilt forward confirmation (#827) are unchanged from
`docs/proposals-round-25.md`.

## Ranking and suggested order

1. A (paired delta): no new data, answers whether any screened route beats
   v2. 2. B (volume): one hour after A, same machinery. 3. C (calendar):
   after a source is verified. GDELT macro and the tilt confirmation run
   in parallel as before. Each of A and B needs its own pre-registration
   (family, grid, Holm) before it is run, and none is scored on cells
   until a screen earns it.
