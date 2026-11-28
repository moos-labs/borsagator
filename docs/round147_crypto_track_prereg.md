# Round 147: crypto track, pre-registration DESIGN draft (BTC/USD, ETH/USD)

Design only. No scorer, no data fetched into the repo, no cell scored. Written before any crypto row is scored. Source of the request: Moos Slack 1795860016.258059 (thread A), relayed to me by the parent agent, NOT read by me. Candidate shadow track only; never a width input, never `scripts/ensemble.py` or frozen v2 values. Facts below were checked live on 28 Nov 2026 (about 10:00 UTC) unless marked UNVERIFIED or relayed.

## 1. Universe (verified symbols)
Yahoo chart v8 (`https://query1.finance.yahoo.com/v8/finance/chart/<SYMBOL>?period1=...&period2=...&interval=1d`) answered for both symbols with `error: null`:

| Symbol | instrumentType | currency | exchange | timezone | first daily bar | daily bars returned | null closes | zero-volume bars |
|---|---|---|---|---|---|---|---|---|
| BTC-USD | CRYPTOCURRENCY | USD | CCC | UTC | 2014-09-17 | 4456 | 0 | 0 |
| ETH-USD | CRYPTOCURRENCY | USD | CCC | UTC | 2017-11-09 | 3307 | 0 | 0 |

- Both series have a bar for every calendar day, all 7 weekdays present, no gap over 1 day, no duplicate dates, bars stamped 00:00:00 UTC. Fields returned: open, high, low, close, volume and adjclose.
- Pitfall found: with `range=max` the API silently downsamples (BTC came back monthly, ETH weekly). The route must pass explicit `period1`/`period2` with `interval=1d`, and the fetch script asserts `meta.dataGranularity == "1d"` and refuses otherwise.
- Pitfall found: the last bar is the CURRENT day, partial (its close equalled `regularMarketPrice` at fetch time). A fetch keeps only bars whose date is strictly before the current UTC date.
- `exchangeName: CCC` is an aggregate quote, not a single exchange venue. UNVERIFIED: how Yahoo builds the CCC aggregate, so the series is a consolidated reference price, not a price anyone traded at (see risks).
- Out of scope now: any other coin. Adding one needs its own symbol check and a note here before use.

## 2. Data route and storage
- Scripted and LLM-free: one stdlib Python script (urllib, json, csv) calls the chart v8 endpoint above, validates, and writes CSV. No model in the loop, no scraping of rendered pages.
- Validation before write (each failure is a listed refusal, nothing partial written): `dataGranularity == "1d"`; all timestamps at 00:00:00 UTC; strictly increasing dates, no duplicates; no null in open/high/low/close; high >= max(open, close) and low <= min(open, close); close > 0; today's UTC date excluded; day-to-day date gap exactly 1 (a missing calendar day is listed, never filled).
- History depth (verified above): BTC 4456 bars from 2014-09-17; ETH 3307 bars from 2017-11-09. The minimum-history rule for a cutoff is 120 daily bars, the same as the EGX screens, which gives first usable cutoffs of about 2015-01-15 (BTC) and 2018-03-09 (ETH).
- Storage alongside the EGX captures: the EGX OHLCV captures live in the archive worktree under `ohlcv/yahoo/<TICKER>_CA.csv`, columns `date,high,low,close,volume,adjclose` (38 files, 9.3 MB in the checkout I read; no `open` column). Crypto goes in the same directory as `ohlcv/yahoo/BTC-USD.csv` and `ohlcv/yahoo/ETH-USD.csv` with the same columns PLUS `open`, kept as a separate column order so EGX readers are untouched. File naming (hyphen kept, no `_CA` suffix) is my choice. Size estimate: about 0.3 MB for BTC and 0.2 MB for ETH, so storage is not a constraint. Writes are append-only on a re-run (dates already stored are re-fetched and must match; a changed historical bar is listed, not overwritten).
- Adjclose is stored but never used: crypto has no splits or dividends. UNVERIFIED: whether adjclose equals close for every bar.

## 3. Session rule for 24/7 trading (fixed before any scoring)
- A session is a UTC calendar day. Every calendar day, weekends included, is a session with a bar. Weekend = NO gap: Saturday and Sunday bars are ordinary sessions, there is no weekend carry, no Friday-to-Monday merge, and no weekend closure.
- Week = 7 sessions (my choice, not yet Moos'). Justification: the series has all 7 weekdays every week, so a 5-session week would be 5 calendar days (a window that ends mid-week and ignores the weekend bars that do exist), while 7 sessions is exactly one calendar week for every cutoff and keeps the weekly cluster independent of the weekday of the cutoff. The cost of choosing 7 is a different effective horizon than the EGX week (5 sessions), so cross-track comparisons are by calendar length, not by session count.
- Day = 1 session. Month = 30 sessions (my choice; it replaces the EGX 21 trading sessions, which is about one calendar month; 30 sessions is the same calendar span). Alternative left open: 28 sessions (4 whole weeks). I pick 30 only because it matches a calendar month; say if 28 is preferred.
- Cutoff = a UTC date C. Features use bars dated <= C-1 only (point in time, same as the EGX rule that a row uses only data published before the cutoff). The realised close for horizon h is the close of the bar dated C-1+h, so the day horizon realises at C, the week at C+6, the month at C+29. Cutoffs are listed with their realisation date; a row without that bar yet has no realised close and is excluded, listed individually.
- Because every day is a session, annualisation constants and any trading-day multiplier from the EGX code (5 sessions per week, 21 per month, 252 per year) are NOT reused for crypto; the scorer takes the horizon lengths 1, 7, 30 as explicit constants.

## 4. Horizons, v2 and challengers
- Horizons: day (1), week (7), month (30). All three are reported, none dropped.
- Frozen v2 is the reference: its interval construction in `scripts/ensemble.py` is not edited. Adapting it means running the same unchanged code on a crypto OHLCV series with the horizon lengths above. UNVERIFIED: whether `ensemble.py` runs on crypto series as is (it has EGX/US specific paths I have not read for this draft); if it does not, the adaptation is a separate documented wrapper that does not touch ensemble.py, and its output defines "frozen v2 on crypto" before any scoring.
- Challengers: any challenger is adapted by its own pre-registration note before it is scored; this document registers none. Closed or parked routes stay closed for crypto unless a note reopens them.
- Windows by date, fixed now (my proposal, flagged): training = cutoffs before 2024-01-01; descriptive = cutoffs 2024-01-01 to 2025-12-31; clean scoring = cutoffs on or after 2026-01-01. Caveat that must travel: every crypto bar up to today is already public, so no historical cell is truly "untouched" in the EGX sense. Only cutoffs whose realised close comes AFTER this document is committed are forward data. I therefore propose the keep rule counts only cells whose cutoff is after the commit date of this document, and that the clean window above is descriptive until that rule is met. This is a decision for Moos.

## 5. Keep rule
KEEP is the standing loop CI bar only (as in the #966/#961 pre-registrations; confirmed by Moos in the 147 corrections, relayed by the parent, not read by me): KEEP only if, on ALL horizons (day, week, month), on untouched cells, (a) the RangeSkill difference (challenger minus frozen v2 on the same rows) has a cutoff-clustered 95 percent CI lower bound above 0, AND (b) the coverage CI overlaps [0.75, 0.85] with width at most 0.15, AND (c) at least 10 fully mature cutoff clusters. Fewer than 10 clusters: counts only, no statistic. No KEEP is an adoption by itself.
- The +0.10 in the original dispatch is NOT part of KEEP, neither an addition nor a replacement. It is the product-level LAUNCH GATE target: a point estimate of RangeSkill of +0.10, tracked and reported separately from KEEP. Meeting it does not make a KEEP and a KEEP does not meet it. The scorer reports the point estimate in its own labelled line ("launch-gate target +0.10, point estimate") and attaches no verdict word to either.
- Clusters: one cluster is one cutoff date with every intended row (asset x horizon) holding a realised close. Non-overlapping windows need cutoff spacing of at least the horizon: day 1, week 7, month 30 sessions. At one cutoff per 30 days, 10 fully mature month clusters need 300 days of forward data; at one per 7 days, 10 week clusters need 70 days. The month horizon therefore gates the whole track; the cutoff spacing is my proposal (one cutoff every 30 days), open for Moos.
- Pooling: BTC and ETH are 2 rows per cutoff and horizon and are strongly correlated; they count as one cluster per cutoff, never as 2 independent clusters.
- Bootstrap defaults: 5000 reps, seed 20261125. Descriptive output carries no verdict word.

## 6. Pair-conversion matrix (shape only, no number asserted that is not sourced)
Slots: BTC, ETH, USD, EGP. A cell is a directed conversion from slot X to slot Y; the quantity per cell is
net edge (X to Y) = predicted move of Y relative to X over the horizon, minus the cost of the conversion (half-spread each side plus fee plus any retail margin), all in percent of notional, before any decision.

| from \ to | BTC | ETH | USD | EGP |
|---|---|---|---|---|
| BTC | n/a | BTC/ETH via two USD legs or direct pair | BTC/USD | BTC to USD to EGP |
| ETH | ETH/BTC | n/a | ETH/USD | ETH to USD to EGP |
| USD | BTC/USD | ETH/USD | n/a | USD/EGP retail |
| EGP | EGP to USD to BTC | EGP to USD to ETH | EGP/USD retail | n/a |

- Only BTC/USD and ETH/USD are forecast by this track. USD/EGP and the EGP legs enter as COST only, not as a forecast (a USD/EGP move forecast is a separate route and is not registered here).
- EGP retail cost: 0.2 percent round trip. This is a WORKING ASSUMPTION, unverified against real spreads. Origin: a note from Moos in the Slack thread, channel C0C8EBZEF9U, message ts 1795859571.618019 (thread 1795858029.067639), which I read on 28 Nov 2026. It says the figure was measured from egrates.com on 2026-11-28 11:52: Egyptian bank USD/EGP spreads uniformly 0.10 EGP (buy about 54.77, sell about 54.87 at CIB, NBE, Banque Misr, QNB, NBK and most others; CBE reference spread 0.139) on a mid of about 54.82, which is a round trip of about 0.18 percent, rounded up to 0.2 percent, replacing an earlier 0.8 percent assumption; one stale outlier bank (a two-week-old off-market quote) was excluded. Nobody on our side has re-verified that measurement: I did not fetch egrates.com or any bank quote, and the 0.18 percent is a DERIVED CALCULATION (0.10 EGP spread / 54.82 mid, taken from the egrates.com note by Moos), not a fetched quote. The figure is a bank USD/EGP quoted spread; it is not a measured cost of an EGP retail route to or from crypto. It is applied once per round trip (0.2 percent total across the EGP legs), not per direction, and refreshed quarterly per the merged plan (the plan itself I have not read; the quarterly refresh is stated by Moos).
- Crypto spread and fee cost must be sourced, not assumed. One live top-of-book snapshot, public tickers, about 10:00:45 UTC on 28 Nov 2026 (single instant, one snapshot, NOT a distribution):

| Venue and pair | bid | ask | spread (bp of mid) |
|---|---|---|---|
| Coinbase BTC-USD | 59476.34 | 59476.35 | 0.0017 |
| Coinbase ETH-USD | 1650.45 | 1650.57 | 0.7270 |
| Kraken XBTUSD | 59495.5 | 59495.6 | 0.0168 |
| Kraken ETHUSD | 1650.42 | 1650.43 | 0.0606 |

  Sources: `https://api.exchange.coinbase.com/products/BTC-USD/ticker`, `.../ETH-USD/ticker`; `https://api.kraken.com/0/public/Ticker?pair=XBTUSD` and `ETHUSD` (first bid and ask). A top-of-book spread at one instant is a floor for small size, not an executable cost: it excludes the exchange taker fee, size impact, and the off-ramp to EGP. UNVERIFIED: the taker fee schedule of any venue, the cost of the actual route an Egyptian retail holder uses, and the spread distribution over time. Before any pair-conversion edge is computed, the cost table needs a sourced, dated fee schedule and a repeated spread sample (hourly over at least 7 days, stored, with the percentiles reported). Until then the matrix reports the predicted move only and the cost cells stay EMPTY with the reason "cost not sourced"; nothing is imputed.
- Yahoo CCC close vs the Coinbase/Kraken mid: Yahoo `regularMarketPrice` BTC 59489.75 and ETH 1651.01 versus the mid prices above (BTC 59476.35 Coinbase, 59495.55 Kraken; ETH 1650.51 Coinbase, 1650.425 Kraken). At that one instant the reference price differs from a venue mid by about 1 to 4 bp (BTC +2.2 bp vs Coinbase, -1.0 bp vs Kraken; ETH +3.0 bp vs Coinbase, +3.5 bp vs Kraken; the quotes were taken seconds apart, so part of this is timing); this is one comparison, and the reference series is a consolidated price, not an execution price.

## 7. Risks (to be carried in every report)
- Exchange vs spot: the Yahoo CCC series is an aggregate reference, not a venue price, and no one can trade at it. Venue prices differ (the snapshot shows differences between venues), exchange outages, withdrawal limits and venue failure are not in the data, and a venue can go down with the position on it. The forecast evaluates a reference series; any realised conversion is at a venue.
- Stablecoin depeg: the USD slot here is true USD. If the route passes through a USD stablecoin, a depeg is an unmodelled cost; no stablecoin is in the universe and none is scored. UNVERIFIED: whether the EGP retail route uses a stablecoin leg.
- 24/7 regime: there is no overnight, no weekend, no circuit breaker, no auction, and no scheduled-announcement gap, so EGX-style gap and session assumptions do not transfer; volatility clusters at hours the EGX frame has no analogue for; the series has structural breaks (2017 and 2020-21 booms, 2022 drawdown, ETF era from 2024) so a cell window mixes regimes. History is short for ETH (from 2017-11-09) and a UTC-midnight bar boundary is itself a convention.
- Regulatory and access: access for an Egyptian retail holder and the legality of the EGP conversion are not examined here. UNVERIFIED and out of scope for the forecast, but they bear on the pair-conversion matrix.
- Data: the chart v8 endpoint is unofficial; schema or granularity can change (the `range=max` downsampling above is the example), so the fetch asserts granularity and is re-validated on each run.

## 8. Open decisions (for Moos)
1. (Resolved: keep rule is the loop CI bar only; +0.10 is the launch-gate point estimate, section 5.) 2. Week = 7 and month = 30 sessions, or 5 and 21 (section 3). 3. Window split and the "only cutoffs after this commit are untouched" rule (section 4). 4. Cutoff spacing of 30 days (section 5). 5. (Resolved as a working assumption with origin and quarterly refresh, section 6; still unverified by us.) 6. File naming for the stored series (section 2).

## 9. What this document does not do
No data was written to the repository. No score, correlation, backtest or forecast was computed. The Yahoo and venue pulls above are descriptive checks of the data route (symbols, granularity, gaps, spreads), not outcomes. Nothing here edits `scripts/ensemble.py` or any frozen value.
