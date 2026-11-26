# Dense day-horizon cells (INS-IMPROVE-007 item 5), cell definitions

Design only, day horizon only. Authority: Moos's triage of INS-IMPROVE-007
(Slack 1795711928.215329): item 5 GO as design, needs cell definitions.
Nothing is dispatched or scored by this document.

## Why day only
A day forecast covers one session, so successive day windows never
overlap. Dense cutoffs therefore add near-independent day scores per
name. Week and month windows overlap under dense cutoffs and would look
like more data without being it, so they are excluded.

## Two tiers
**Tier S, engine-free (screen).** Every session of the long-history
deliverable, per ticker, day horizon only, same exclusion rule and
regime split as item 1 (windows end on or before 2023-12-28; split at
2021-09-05). This is the screen_band_models machinery at step 1 instead
of 21 for the day horizon. Descriptive only. Effective n is the number of
distinct cutoff dates (cross-sectional correlation) and is printed beside
raw n. Cost: arithmetic on stored OHLC, minutes.

**Tier C, engine cells (cycle dispatch).** A fresh block D5:
- Tickers: COMI, ETEL, TMGH, NVDA (control), SWDY, HRHO (same six).
- Cutoffs: every EGX session Sunday to Thursday from 2025-06-01 to
  2025-06-26 inclusive, 20 sessions (verified: 2025-06-01 is a Sunday,
  2025-06-26 a Thursday). A session with no close in price.csv (holiday)
  is dropped as it appears; NVDA uses its own sessions on the same dates.
- Cell = one (ticker, cutoff date) with horizon day (1 session). 6 names x
  up to 20 sessions = up to 120 day rows, 20 cutoff clusters.
- Realised value: close of the next session after the cutoff over the
  cutoff close, as in the backtest (#436).
- Disjointness: D5 realised sessions (2025-06-02 to 2025-06-29) do not
  intersect block F1 (cutoffs 2024-02-16 to 2025-05-16, windows start the
  next Sunday after each), the 91-102 holdout (2025-08-15, 2025-11-14),
  cells 1-90, or any ledger row. The one near case is F1's 2025-05-16
  cutoff, whose day window is 2025-05-18; D5 starts 2025-06-01.
- Cell numbers and dispatch are the cycle's. D5 is untouched until one
  scoring of frozen rules; no descriptive peek.
- Rules: frozen v2 is the comparison. The keep rule is the round 3 rule
  with the #775 coverage leg, scored on the day horizon only; the 10
  cluster minimum from #774 is met (20 clusters), and a KEEP on D5 alone
  is not an adoption (needs the audit plus forward confirmation).

## Caveats
- 20 consecutive sessions sit in one regime (one month). Day coverage on
  D5 is a calibration check, not evidence across regimes; Tier S supplies
  the regimes. The two tiers answer different questions.
- Overlapping vol clustering across consecutive days means 20 clusters
  are not 20 independent regimes; effective n is reported as clusters and
  the audit's small-k warnings still apply.
- EGX holidays in June 2025 (for example Eid al-Adha) are not verified
  here; the data decides which sessions exist.
- Challengers tried before D5 is scored: A-F, item 4 rolling conformal,
  and the five item 1 estimators.
