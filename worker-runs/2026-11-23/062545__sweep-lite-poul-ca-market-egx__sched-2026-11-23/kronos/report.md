# Kronos-small forecast — POUL.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, sample_count=1)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2026-09-28 to 2026-11-18 — 36 sessions
- Preferred post-merger context (from 2026-09-28) was accepted; no fallback needed.
- Last actual close: 7.699999809265137 on 2026-11-18
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-11-19: 8.0612
- 2026-11-22: 8.3511
- 2026-11-23: 8.2999
- 2026-11-24: 8.6054
- 2026-11-25: 8.5482
- 2026-11-26: 8.6574
- 2026-11-29: 8.653
- 2026-11-30: 8.5087
- 2026-12-01: 8.6304
- 2026-12-02: 8.6554
- 2026-12-03: 8.7059
- 2026-12-06: 8.7092
- 2026-12-07: 9.0429
- 2026-12-08: 9.2048
- 2026-12-09: 9.1417
- 2026-12-10: 9.0548
- 2026-12-13: 9.1331
- 2026-12-14: 9.3878
- 2026-12-15: 9.0817
- 2026-12-16: 8.9538
- 2026-12-17: 8.9139

**Change over the 21 sessions (last forecasted close vs last actual close): +15.76%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
