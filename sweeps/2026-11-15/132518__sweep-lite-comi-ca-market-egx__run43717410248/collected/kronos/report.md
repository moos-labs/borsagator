# Kronos-small forecast — COMI.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, sample_count=1)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2026-09-28 to 2026-11-11 — 32 sessions
- Preferred post-merger context (from 2026-09-28) was accepted; no fallback needed.
- Last actual close: 130.33999633789062 on 2026-11-11
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-11-12: 128.2495
- 2026-11-15: 128.3866
- 2026-11-16: 132.5928
- 2026-11-17: 133.1829
- 2026-11-18: 129.0414
- 2026-11-19: 129.8684
- 2026-11-22: 129.9093
- 2026-11-23: 127.4008
- 2026-11-24: 124.5031
- 2026-11-25: 123.7932
- 2026-11-26: 123.6359
- 2026-11-29: 121.7719
- 2026-11-30: 121.5063
- 2026-12-01: 121.9459
- 2026-12-02: 122.4536
- 2026-12-03: 123.7855
- 2026-12-06: 120.9548
- 2026-12-07: 120.4805
- 2026-12-08: 122.1275
- 2026-12-09: 122.9719
- 2026-12-10: 121.3395

**Change over the 21 sessions (last forecasted close vs last actual close): -6.91%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
