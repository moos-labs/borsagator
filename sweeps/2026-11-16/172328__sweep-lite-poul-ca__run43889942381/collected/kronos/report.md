# Kronos-small forecast — POUL.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, sample_count=1)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2026-09-28 to 2026-11-12 — 33 sessions
- Preferred post-merger context (from 2026-09-28) was accepted; no fallback needed.
- Last actual close: 10.149999618530273 on 2026-11-12
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-11-15: 10.3096
- 2026-11-16: 10.5707
- 2026-11-17: 10.4402
- 2026-11-18: 10.3698
- 2026-11-19: 9.8933
- 2026-11-22: 9.8916
- 2026-11-23: 10.0787
- 2026-11-24: 9.831
- 2026-11-25: 9.7517
- 2026-11-26: 9.9083
- 2026-11-29: 9.7498
- 2026-11-30: 9.4996
- 2026-12-01: 9.5607
- 2026-12-02: 9.5343
- 2026-12-03: 9.5379
- 2026-12-06: 9.5842
- 2026-12-07: 9.714
- 2026-12-08: 9.8885
- 2026-12-09: 9.8961
- 2026-12-10: 9.7582
- 2026-12-13: 9.6256

**Change over the 21 sessions (last forecasted close vs last actual close): -5.17%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
