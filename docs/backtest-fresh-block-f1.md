# Fresh untouched backtest block F1 (INS-IMPROVE-007 item 2), pre-declared

Declared before any F1 cell exists or is scored. Authority: Moos's GO on
INS-IMPROVE-007 (Slack 1795711411.066929), item 2 with the condition
"pre-declare the fresh untouched block before any scoring, cutoffs
spaced at least a month apart".

## Block
- Tickers: COMI, ETEL, TMGH, NVDA (US control), SWDY, HRHO (same six as
  cells 1-102; ORAS and POUL stay excluded).
- Cutoffs, all Fridays, 91 days apart, each earlier than cell 91-102
  (2025-08-15 and 2025-11-14) and than every cell 1-90 cutoff:
  2025-05-16, 2025-02-14, 2024-11-15, 2024-08-16, 2024-05-17, 2024-02-16.
- Rows: 6 cutoffs x 6 tickers = 36 per horizon (day, week, month), which
  meets the T1 floor of 30 per horizon with 6 cutoff clusters.
- Spacing: 91 days between cutoffs, so month windows (21 sessions) never
  overlap and week windows never overlap.
- Dispatch is the cycle's. Cell numbers are assigned by the cycle; the
  block is identified by these cutoff dates, not by cell number.

## Status rules
- F1 is untouched until ONE scoring of frozen rules. No fit, tuning,
  inspection of realised values or descriptive run may use F1 rows
  before that scoring. Fits stay on cells 1-47.
- The 91-102 block remains the frozen holdout for backtest verdicts; F1
  is a different, older block and does not replace it. Neither block is
  scored in a descriptive run.
- Every F1 cutoff is after 2023-12-28, so F1 windows never overlap the
  long-history screen (item 1), whose windows end on or before that date.
- Price history needed per capture: about 250 bars before each cutoff
  (earliest 2024-02-16 needs data from about 2023-02). The long OHLC
  deliverable must cover that or the cycle's price fetch must.

## Rules to be applied (frozen before scoring)
- Frozen v2 (V2_BAND_K day 1.15, week 1.28, month 1.20) is the
  comparison; any challenger is scored with its pre-registered frozen
  file, one scoring, no refit.
- Keep rule: round 3 rule with the coverage leg as merged at scoring
  time (#775: cutoff-clustered coverage CI overlaps [0.75, 0.85]).
  If #775 is unmerged then, report both the point and the overlap.
- Report effective n (cutoff clusters) beside raw n. Minimum 10 cutoff
  clusters is recommended by the CI audit (#774); F1 has 6, so a
  verdict on F1 alone stays INSUFFICIENT for CI purposes and F1 is read
  together with 91-102 only as a pooled count of 12 cutoffs, scored
  once at the end.
- Challengers tried before F1 is scored: A, B, C, D, E, F, item 4
  rolling conformal, and the item 1 estimators (s20, ewma94, blend2060,
  park60, gk60). Any "win" is read against that count.
- Kronos gate stays at weight 0.
