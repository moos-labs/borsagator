# Kronos-small forecast — POUL.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, sample_count=1)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2026-09-28 to 2026-11-11 — 32 sessions
- Preferred post-merger context (from 2026-09-28) was accepted; no fallback needed.
- Last actual close: 10.199999809265137 on 2026-11-11
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-11-12: 10.3072
- 2026-11-15: 10.0478
- 2026-11-16: 10.1564
- 2026-11-17: 9.9865
- 2026-11-18: 9.9812
- 2026-11-19: 10.0948
- 2026-11-22: 10.1678
- 2026-11-23: 9.9944
- 2026-11-24: 10.031
- 2026-11-25: 10.2802
- 2026-11-26: 10.2104
- 2026-11-29: 10.1632
- 2026-11-30: 10.2414
- 2026-12-01: 9.8155
- 2026-12-02: 9.6822
- 2026-12-03: 9.8167
- 2026-12-06: 9.8312
- 2026-12-07: 9.56
- 2026-12-08: 9.8687
- 2026-12-09: 9.8142
- 2026-12-10: 9.7086

**Change over the 21 sessions (last forecasted close vs last actual close): -4.82%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
