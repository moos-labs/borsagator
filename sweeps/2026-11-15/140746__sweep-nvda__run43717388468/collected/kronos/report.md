# Kronos-small forecast — NVDA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, sample_count=1)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2026-09-28 to 2026-11-13 — 35 sessions
- Preferred post-merger context (from 2026-09-28) was accepted; no fallback needed.
- Last actual close: 162.85000610351562 on 2026-11-13
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-11-15: 178.319
- 2026-11-16: 185.4368
- 2026-11-17: 181.2659
- 2026-11-18: 181.2057
- 2026-11-19: 176.425
- 2026-11-22: 174.6347
- 2026-11-23: 178.24
- 2026-11-24: 180.8266
- 2026-11-25: 177.8522
- 2026-11-26: 177.9104
- 2026-11-29: 175.4079
- 2026-11-30: 178.5417
- 2026-12-01: 176.962
- 2026-12-02: 174.9137
- 2026-12-03: 176.0223
- 2026-12-06: 178.386
- 2026-12-07: 180.479
- 2026-12-08: 181.405
- 2026-12-09: 179.12
- 2026-12-10: 179.4845
- 2026-12-13: 180.6044

**Change over the 21 sessions (last forecasted close vs last actual close): +10.90%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
