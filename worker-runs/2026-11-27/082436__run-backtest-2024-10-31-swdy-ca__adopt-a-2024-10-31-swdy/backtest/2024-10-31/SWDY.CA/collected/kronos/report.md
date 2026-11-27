# Kronos-small forecast — SWDY.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2024-10-31 — 1429 sessions
- As-of cutoff: 2024-10-31 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1429 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 88.26000213623047 on 2024-10-31
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2024-11-03: 83.9715
- 2024-11-04: 79.393
- 2024-11-05: 76.2299
- 2024-11-06: 74.6709
- 2024-11-07: 68.9317
- 2024-11-10: 64.9318
- 2024-11-11: 57.4235
- 2024-11-12: 51.3423
- 2024-11-13: 48.1489
- 2024-11-14: 45.4362
- 2024-11-17: 41.5414
- 2024-11-18: 40.4293
- 2024-11-19: 38.2739
- 2024-11-20: 36.9956
- 2024-11-21: 35.0326
- 2024-11-24: 32.3612
- 2024-11-25: 31.368
- 2024-11-26: 31.9373
- 2024-11-27: 30.2731
- 2024-11-28: 30.7866
- 2024-12-01: 28.8782

**Change over the 21 sessions (last forecasted close vs last actual close): -67.28%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
