# Kronos-small forecast — POUL.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, sample_count=1)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2026-09-28 to 2026-11-10 — 31 sessions
- Preferred post-merger context (from 2026-09-28) was accepted; no fallback needed.
- Last actual close: 10.289999961853027 on 2026-11-10
- Forecast horizon: next 10 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-11-11: 10.1493
- 2026-11-12: 10.1198
- 2026-11-15: 10.1349
- 2026-11-16: 10.0744
- 2026-11-17: 10.0076
- 2026-11-18: 10.0331
- 2026-11-19: 10.0117
- 2026-11-22: 9.9279
- 2026-11-23: 9.9529
- 2026-11-24: 9.5423

**Change over the 10 sessions (last forecasted close vs last actual close): -7.27%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
