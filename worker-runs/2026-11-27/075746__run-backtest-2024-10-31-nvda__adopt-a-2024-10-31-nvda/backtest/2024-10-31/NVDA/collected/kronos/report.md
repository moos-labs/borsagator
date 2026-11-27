# Kronos-small forecast — NVDA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-02 to 2024-10-31 — 1469 sessions
- As-of cutoff: 2024-10-31 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1469 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 132.75999450683594 on 2024-10-31
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2024-11-03: 139.5322
- 2024-11-04: 135.4571
- 2024-11-05: 133.9049
- 2024-11-06: 127.4153
- 2024-11-07: 121.8404
- 2024-11-10: 112.3052
- 2024-11-11: 111.4619
- 2024-11-12: 103.6934
- 2024-11-13: 97.595
- 2024-11-14: 95.1226
- 2024-11-17: 93.8535
- 2024-11-18: 94.0166
- 2024-11-19: 93.169
- 2024-11-20: 94.2843
- 2024-11-21: 94.6191
- 2024-11-24: 94.5196
- 2024-11-25: 90.434
- 2024-11-26: 90.0879
- 2024-11-27: 88.0864
- 2024-11-28: 89.1387
- 2024-12-01: 87.2931

**Change over the 21 sessions (last forecasted close vs last actual close): -34.25%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
