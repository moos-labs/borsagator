# Long-history band-model screen: design and first-arm pre-registration (INS-IMPROVE-007 item 1)

Descriptive only, under the screening exclusion rule. Authority: Moos's
triage of INS-IMPROVE-007 (Slack 1795711928.215329): item 1 GO first,
pre-register per arm, descriptive only. Machinery: benchmarks/screen_band_models.py
(this PR), built on the #771 screen mode.

## Design
- Data: per-ticker daily OHLC for the EGX names plus NVDA, from the data
  deliverable (--history DIR, TICKER.csv: Date,Open,High,Low,Close). A
  ticker needs at least 120 + 60 bars after the regime start to enter.
- Pseudo-cutoffs every 21 sessions after 120 bars, per ticker. Horizons
  1 / 5 / 21 sessions. Windows never overlap for the month horizon and
  overlap only through the shared market factor for day and week.
- Exclusion rule: bars after 2023-12-28 are dropped before any window is
  built. No verdict-cell window, no ledger row, and neither the 91-102
  holdout nor block F1 (all cutoffs after 2023-12-28) is touched.
- Regimes: split at 2021-09-05 (price-limit change, from the decree 681
  research note). Pairs are tagged pre (window ends before the break) or
  post (the 60-session sigma lookback starts on or after it); straddling
  pairs are dropped; regimes are scored and read separately, never
  pooled. The post regime runs 2021-09-05 + 60 sessions to 2023-12-28,
  about 2 years (roughly 500 sessions), so at step 21 each ticker gives about 24 pseudo
  cutoffs; with 33+ names the post regime has far more than the 10
  cutoff clusters the CI audit (#774) recommends.
- Effective n: pseudo-cutoff dates are the clusters. Raw n and clusters
  are printed together. The coverage leg is read as the cutoff-clustered
  coverage CI overlapping [0.75, 0.85] (the #775 rule) and the point
  value is printed too.

## Arm 1 (pre-registered before any long-history run)
Arm 1 is park60: Parkinson 60-session sigma with the frozen v2 k table
(day 1.15, week 1.28, month 1.20), nothing fitted, against frozen v2
(s60) on the same windows.
- Why this arm first: A (#767) showed a 1-47 in-sample edge that
  reversed out of sample on cells 48-78 (RangeSkill -0.060/-0.032/-0.058
  vs v2 -0.023/-0.001/-0.022). A long history of independent windows
  tests whether the reversal was noise or a real result.
- Read per horizon, post regime first, pre regime second:
  "supports" = RangeSkill cutoff-cluster CI lower bound > 0 AND coverage
  CI overlaps [0.75, 0.85] AND at least 10 clusters; "against" =
  RangeSkill CI upper bound < 0; otherwise "inconclusive". A "supports"
  in both regimes on at least two horizons is what would justify a clean
  test on F1 and 91-102. It is never an adoption and never a verdict.
- Multiple testing: five arms (s20, ewma94, blend2060, park60, gk60) x
  three horizons x two regimes = 30 readings are produced by the script.
  Only arm 1 is pre-registered as the primary; the others are exploratory
  and any "supports" among them is read against the count of 30, plus
  the 7 shadow challengers already tried (A-F, item 4).
- Nothing is fitted. If a later arm needs a k fit, it fits on the pre
  regime only and is scored on the post regime, and is its own
  pre-registered item.

## Not in this screen
Per-ticker HAR, GARCH and pooled-scale arms (C, D, F) keep their own
screens (#771 template). Kronos and any engine arm stay out (weight 0).
