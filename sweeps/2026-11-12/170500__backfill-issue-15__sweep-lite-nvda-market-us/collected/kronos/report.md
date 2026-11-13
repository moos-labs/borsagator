# Kronos-small forecast — NVDA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, sample_count=1)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2026-09-28 to 2026-11-12 — 34 sessions
- Preferred post-merger context (from 2026-09-28) was accepted; no fallback needed.
- Last actual close: 163.86000061035156 on 2026-11-12
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-11-15: 163.2189
- 2026-11-16: 167.2445
- 2026-11-17: 178.1218
- 2026-11-18: 179.6983
- 2026-11-19: 182.795
- 2026-11-22: 187.9946
- 2026-11-23: 198.9886
- 2026-11-24: 193.5955
- 2026-11-25: 201.6273
- 2026-11-26: 205.1223
- 2026-11-29: 202.0752
- 2026-11-30: 211.057
- 2026-12-01: 208.1104
- 2026-12-02: 204.0983
- 2026-12-03: 205.967
- 2026-12-06: 203.1234
- 2026-12-07: 207.4018
- 2026-12-08: 199.6972
- 2026-12-09: 202.6288
- 2026-12-10: 204.3751
- 2026-12-13: 208.4591

**Change over the 21 sessions (last forecasted close vs last actual close): +27.22%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
