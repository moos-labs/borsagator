# Kronos-small forecast — NVDA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, sample_count=1)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2026-09-28 to 2026-11-12 — 34 sessions
- Preferred post-merger context (from 2026-09-28) was accepted; no fallback needed.
- Last actual close: 166.19000244140625 on 2026-11-12
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-11-15: 164.5126
- 2026-11-16: 168.362
- 2026-11-17: 178.8213
- 2026-11-18: 180.0482
- 2026-11-19: 183.1477
- 2026-11-22: 188.9698
- 2026-11-23: 199.9629
- 2026-11-24: 202.1423
- 2026-11-25: 208.8699
- 2026-11-26: 207.485
- 2026-11-29: 206.2346
- 2026-11-30: 212.6936
- 2026-12-01: 209.15
- 2026-12-02: 193.3512
- 2026-12-03: 205.1258
- 2026-12-06: 203.5452
- 2026-12-07: 207.9647
- 2026-12-08: 200.0515
- 2026-12-09: 202.9686
- 2026-12-10: 204.7584
- 2026-12-13: 208.8533

**Change over the 21 sessions (last forecasted close vs last actual close): +25.67%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
