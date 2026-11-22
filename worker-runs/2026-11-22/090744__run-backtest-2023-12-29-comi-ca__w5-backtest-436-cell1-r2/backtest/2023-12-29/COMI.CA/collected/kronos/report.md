# Kronos-small forecast — COMI.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, sample_count=1)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2023-12-28 — 1231 sessions
- As-of cutoff: 2023-12-29 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 72.94000244140625 on 2023-12-28
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2023-12-31: 34.2927
- 2024-01-01: 34.7282
- 2024-01-02: 33.8731
- 2024-01-03: 34.6551
- 2024-01-04: 34.7159
- 2024-01-07: 33.6846
- 2024-01-08: 32.7039
- 2024-01-09: 33.0807
- 2024-01-10: 34.62
- 2024-01-11: 32.2812
- 2024-01-14: 32.6694
- 2024-01-15: 33.9503
- 2024-01-16: 33.4713
- 2024-01-17: 32.3372
- 2024-01-18: 33.424
- 2024-01-21: 33.0366
- 2024-01-22: 32.205
- 2024-01-23: 33.423
- 2024-01-24: 33.0298
- 2024-01-25: 32.1803
- 2024-01-28: 33.0913

**Change over the 21 sessions (last forecasted close vs last actual close): -54.63%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
