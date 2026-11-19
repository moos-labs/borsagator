# Kronos-small forecast — POUL.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, sample_count=1)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2026-09-28 to 2026-11-16 — 34 sessions
- Preferred post-merger context (from 2026-09-28) was accepted; no fallback needed.
- Last actual close: 8.020000457763672 on 2026-11-16
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-11-17: 8.4299
- 2026-11-18: 8.9487
- 2026-11-19: 8.9395
- 2026-11-22: 8.8856
- 2026-11-23: 9.2327
- 2026-11-24: 9.369
- 2026-11-25: 9.8036
- 2026-11-26: 9.8889
- 2026-11-29: 9.7787
- 2026-11-30: 9.8965
- 2026-12-01: 9.7372
- 2026-12-02: 9.8596
- 2026-12-03: 9.5399
- 2026-12-06: 9.6317
- 2026-12-07: 9.5663
- 2026-12-08: 9.7705
- 2026-12-09: 9.5258
- 2026-12-10: 9.2792
- 2026-12-13: 9.3683
- 2026-12-14: 9.2834
- 2026-12-15: 9.2756

**Change over the 21 sessions (last forecasted close vs last actual close): +15.66%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
