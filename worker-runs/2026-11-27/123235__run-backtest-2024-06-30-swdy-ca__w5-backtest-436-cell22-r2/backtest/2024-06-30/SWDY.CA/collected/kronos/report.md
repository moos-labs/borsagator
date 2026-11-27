# Kronos-small forecast — SWDY.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2024-06-27 — 1345 sessions
- As-of cutoff: 2024-06-30 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1345 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 47.2599983215332 on 2024-06-27
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2024-06-30: 45.8296
- 2024-07-01: 45.1016
- 2024-07-02: 42.5755
- 2024-07-03: 41.2512
- 2024-07-04: 39.2516
- 2024-07-07: 37.2497
- 2024-07-08: 36.3201
- 2024-07-09: 34.8461
- 2024-07-10: 33.6357
- 2024-07-11: 32.3952
- 2024-07-14: 32.8312
- 2024-07-15: 31.9591
- 2024-07-16: 31.4887
- 2024-07-17: 31.0623
- 2024-07-18: 30.6671
- 2024-07-21: 30.2212
- 2024-07-22: 30.5381
- 2024-07-23: 30.3664
- 2024-07-24: 30.1476
- 2024-07-25: 29.9446
- 2024-07-28: 30.163

**Change over the 21 sessions (last forecasted close vs last actual close): -36.18%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
