# Proposal round 25: new-information routes (proposals only)

INS-IMPROVE-001 round 25 item 2 (brief: Muhammad's Slack message
1795738752.880149). Nothing here is GO'd, scored or registered. One
point-in-time (PIT) data source is named per proposal, and each source was
checked live on 2026-11-27 unless marked otherwise. No source is invented.

## Where the numbers stand (figures from Muhammad's brief, not re-run by me)

- Forward ledger, 55 matured rows: ensemble hit day 3/28 (0.107), week 0/15,
  month 0/0, pooled 7%, net skill -0.249 (was -0.298 at n=36).
- Adoption re-run at n=55: DO NOT ADOPT stands.
- Route 2 market-factor screen (#838, reproduced by Muhammad): negative.
  Smallest Holm-adjusted p 0.081. The EGX-internal factor does not beat the
  frozen width.
- Tilt forward confirmation (#827) is live as a design; no matured
  tilt-bearing forward rows exist yet (14 tilt-bearing sweep dirs at
  archive tip d6ab6b30, all pending).

Read: everything built from the names' own prices or from the EGX cross
section has been tried and fails to separate. The remaining routes bring
information that is outside those series. I rank them by (a) is the source
verified and PIT-clean, (b) can it be fitted on the 2014-2023 history
without touching a verdict cell, (c) how many independent regime clusters
the history gives it.

## Proposal A: USD/EGP stress as a width input (cheapest, runnable now)

- Source (verified): Yahoo chart API, symbol `EGP=X`, daily close.
  Fetched `https://query1.finance.yahoo.com/v8/finance/chart/EGP%3DX`
  for 2014-01-01 to 2023-12-28: 2,607 daily bars, 3 null closes, first
  bar 2014-01-01, last 2023-12-28. Same API and field layout as
  `scripts/fetch_ohlcv_store.py`. Caveat: this is a market quote
  series, not the CBE official rate; the two differ around devaluations.
- PIT rule: a cutoff on EGX date D uses only `EGP=X` closes dated before D
  (strictly previous session), so the quote's intraday timing never leaks.
- Feature: z of the 20-session realised stdev of EGP=X log returns, against
  its own earlier values (expanding, as in `screen_news_width.py`). Band =
  v2 x exp(beta x clip(z, -3, 3)), beta in a fixed grid, not fitted.
- Cheapest first test: reuse `screen_news_width.py`'s pair builder with
  this feature in place of the news z (an hour of work), run on the same
  screen (windows end <= 2023-12-28, pre/post 2021-09-05 split, STEP 21,
  Holm over betas x horizons x regimes).
- Honest limit: the 2014-2023 history has few devaluation episodes (the
  float of 2016-11 and the 2022 moves). Clusters are cutoff dates (hundreds),
  but the signal rests on a handful of regimes, so a positive screen would
  still need the forward ledger.

## Proposal B: global risk and commodity factors as width inputs

- Sources (verified, same API and dates): `EEM` (2,514 bars, 0 nulls),
  `BZ=F` Brent futures (2,515 bars, 4 nulls), `GC=F` gold futures (2,515
  bars, 3 nulls), all 2014-01-02 to 2023-12-27.
- PIT rule: EEM, Brent and gold close after the EGX session, so a cutoff on
  date D uses closes dated D-1 or earlier.
- Feature: trailing 20-session stdev of each series' log returns, and the
  ticker's trailing beta to it, in the sigma_from decomposition of
  `screen_market_factor.py` (market factor replaced by the external factor
  and lagged one session).
- Cheapest first test: swap the factor source in `screen_market_factor.py`;
  family 3 factors x 3 horizons x 2 regimes = 18, Holm.
- Honest limit: Route 2 found the EGX-wide factor adds nothing; EGX names
  may have low beta to EEM or Brent, in which case this fails the same way.
  The screen is cheap and answers it.

## Proposal C: GDELT macro-theme rows (already GO'd as step 1, INS-MACRO-NEWS-001)

- Source (verified): GDELT GKG 2.0 files listed in
  `http://data.gdeltproject.org/gdeltv2/masterfilelist.txt` (reachable, 301
  to https). The full 2019-2026 backfill is running in shards (checkpoints
  at 2:07-2:18 EET were 1,944 of 64,783 files for 2020, 2,376 of 68,740
  for 2021; progress figures are the shard agents' own, relayed).
- PIT rule: the file's ingestion timestamp (the timestamp in the GKG file
  name) bounds availability, never dates read from article text. For the
  harness (#839 rebased) the conservative rule is: strictly before 00:00:00
  UTC of the cutoff day.
- Feature: macro-theme count and tone per day as a market-level width
  input (market-level, not per ticker, so it is not limited by alias
  matching quality).
- Cheapest first test: after the macro rows land, the same screen as A with
  the macro z. Blocked on the backfill and the point-in-time close check.

## Proposal D (not new information, listed so the ranking is complete)

Tilt forward confirmation (#827). It needs the cycle's wide, near-daily
sweeps; about 11 / 15 / 31 sessions (day / week / month) after
registration. Cheapest step: confirm that every sweep the cycle runs keeps
`tilt_centre_pct` in `ensemble.json`.

## Ranking and suggested order

1. A: verified source, 1-hour test, answers whether macro stress carries
   width information. 2. B: one swap in the Route 2 screen. 3. C: waits for
   the backfill, highest ceiling because it is the only route with
   forward-ledger-compatible text information. 4. D: running in parallel.
Each of A, B and C needs its own pre-registration (family, grid, Holm)
before it is run, and none is scored on cells until a screen earns it.
