# Kronos-small forecast — POUL.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, sample_count=1)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2026-09-28 to 2026-11-09 — 30 sessions
- Preferred post-merger context (from 2026-09-28) was accepted; no fallback needed.
- Last actual close: 9.989999771118164 on 2026-11-09
- Forecast horizon: next 10 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-11-10: 9.8744
- 2026-11-11: 9.9424
- 2026-11-12: 10.053
- 2026-11-15: 10.0618
- 2026-11-16: 10.0862
- 2026-11-17: 10.0598
- 2026-11-18: 10.0195
- 2026-11-19: 10.0658
- 2026-11-22: 10.0125
- 2026-11-23: 9.9802

**Change over the 10 sessions (last forecasted close vs last actual close): -0.10%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
