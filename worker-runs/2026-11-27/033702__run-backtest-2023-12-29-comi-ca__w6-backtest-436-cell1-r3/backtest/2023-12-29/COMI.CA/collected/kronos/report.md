# Kronos-small forecast — COMI.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2023-12-28 — 1231 sessions
- As-of cutoff: 2023-12-29 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1231 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 72.94000244140625 on 2023-12-28
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2023-12-31: 72.8202
- 2024-01-01: 73.1616
- 2024-01-02: 71.9711
- 2024-01-03: 71.2769
- 2024-01-04: 70.1024
- 2024-01-07: 70.6127
- 2024-01-08: 67.9832
- 2024-01-09: 67.7815
- 2024-01-10: 65.6016
- 2024-01-11: 64.8408
- 2024-01-14: 65.2251
- 2024-01-15: 64.3384
- 2024-01-16: 63.3379
- 2024-01-17: 62.9237
- 2024-01-18: 61.5996
- 2024-01-21: 60.3137
- 2024-01-22: 59.1793
- 2024-01-23: 59.117
- 2024-01-24: 58.2916
- 2024-01-25: 57.9506
- 2024-01-28: 56.9867

**Change over the 21 sessions (last forecasted close vs last actual close): -21.87%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
