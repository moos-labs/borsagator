# Next experiments after the n=55 numbers (proposal, round 23 item 3)

INS-IMPROVE-001 round 23 item 3 (brief: Moos Slack 1795736150.489689).
Proposals only: nothing here is GO'd, scored or registered. Ranked routes
are directions for Muhammad and the cycle to rule on. Numbers marked
(Moos) are from his 01:35 Slack post and were not re-run by me; numbers
marked (#812) and (#806) are from my merged/open PRs.

## What the n=55 numbers say (cells 48-102, 6 tickers, 10 cutoffs)

- Frozen v2 vs naive (Moos): RangeSkill day -0.016, week -0.001, month
  -0.013, coverage 0.691 / 0.782 / 0.673. Day and month under-cover the
  0.75-0.85 target; week sits on naive. No adoption.
- Every re-shaping of the same information fails to separate from v2 on
  RangeSkill (Moos: Parkinson, ACI, log-HAR, GARCH-FHS, centre drift).
  ACI is the only coverage lever and it costs skill.
- Pooled empirical quantiles (#812, cells 48-90 only, 8 clusters): coverage
  0.744 / 0.907 / 0.721 and RangeSkill +0.019 / +0.036 / +0.050, every CI
  contains 0. Training residuals are right-skewed (month Q10 -0.90, Q90
  +2.10 in units of sigma x sqrt(sessions)). This is still the same
  information (price history), re-shaped.
- With 8 to 10 clusters the keep legs have little power even in the
  training-calibrated world (#806: both legs held in 2.0% / 0.8% / 6.3%
  of replicates at 8 clusters under the 0.15 cap). More re-shapings of
  price history cannot settle at this n; they can only be screened on the
  long history, where the cluster count is large.

Read: the price-history route is exhausted at the evidence we can gather
on cells. The heavy routes below add information the price series does
not contain, and each can be FIT on pre-2023-12-29 history so the
cells stay untouched.

## Ranked routes

Heaviest = new information, fittable on long history, cells untouched.

1. News volume and tone from GDELT GKG as a width input. Matching
   precision is not re-verified here (see PR #820). The full 2019-2026
   run is in progress (429 of 543,568 files at 01:22 on 2026-11-27, ETA
   6 to 7 days, per the GDELT agent's report, not re-run by me). Design:
   per ticker and cutoff, count and mean tone of matched rows over the 5
   sessions before the cutoff, standardised within ticker; band half =
   k x s60 x sqrt(sessions) x exp(beta x clip(z_news, -3, 3)), one k per
   horizon and one beta. The multiplier is always positive (the earlier
   (1 + beta x z) form goes negative, e.g. beta 0.5 and z -3 gives -0.5);
   beta = 0 reproduces the frozen width, fit on the post-2021-09-05 long history (windows ending
   <= 2023-12-28) with the Yahoo close, scored on cells 48-90 descriptive
   then 91+ for any reading. Holm across the screen's readings.
   Prerequisite: the full-run output, the one matching rule frozen, and
   a point-in-time check that GKG timestamps precede the EGX close of the
   cutoff day (not yet verified).
2. Market-wide factor from our own 36 tickers (executable now, no new
   data). Equal-weight close-to-close index of the Yahoo store, its
   trailing 20-session volatility, and each name's trailing beta, as a
   width input: s_adj = sqrt(own idiosyncratic var + beta^2 x market
   var). The per-name s60 mixes the two and lags market regime changes.
   Fit on the post-regime long history, same screen machinery as
   `screen_band_models.py` (family size fixed in advance). Information
   not in a single name's own series, no external dependency. The EGX30
   index itself has no scripted history route (T4, Moos).
3. Earnings and disclosure calendar as an event flag (needs G1/G2; same
   point-in-time rule as route 1: a flag may use a disclosure only if its
   publication timestamp precedes the EGX close of the cutoff day, and the
   check is verified before any cell is scored):
   widen windows that contain a results release. Blocked on a historical
   disclosures dataset; the INS-DATA surveys did not deliver one I can
   cite here. Rank low until a dataset is verified.
4. Macro regime flags (USD/EGP, CBE rate, G5): few regime events in the
   post-2021 window (a handful of devaluation episodes), so the fit has
   almost no independent clusters. Rank low.
5. Forward sentiment ledger: unchanged. Needs a second wide sweep to
   mature (Muhammad, Slack 1795723155.629979); MIN_CUTOFFS 2 stays until the cycle rules.

Re-shaping routes (same information), only if the above stall:
6. Pooled quantiles with the cell-weighted fit or per-regime fit. The
   verdict window 91-102 has about 12 rows per horizon on 2 cutoffs, so
   no pooled-quantile reading is possible there; it waits for the
   forward ledger or new cells.
7. Tilt forward confirmation: see `docs/tilt-forward-confirmation-design.md`
   (round 23 item 2). It is a confirmation step, not a new experiment.

## Suggested next GO, if any

Route 2 first: it can run today on the Yahoo store with the existing
screen harness and gives a result in the same hour. Route 1 starts the
harness now against a synthetic news fixture and switches to the real
matches when the run finishes. Both are fit before any cell is scored.
