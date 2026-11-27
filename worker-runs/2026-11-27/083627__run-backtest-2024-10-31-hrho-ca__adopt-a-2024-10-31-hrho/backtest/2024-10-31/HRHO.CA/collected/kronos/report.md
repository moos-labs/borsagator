# Kronos-small forecast — HRHO.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2024-10-31 — 1429 sessions
- As-of cutoff: 2024-10-31 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1429 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 22.139999389648438 on 2024-10-31
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2024-11-03: 21.925
- 2024-11-04: 21.7159
- 2024-11-05: 21.5472
- 2024-11-06: 21.3482
- 2024-11-07: 21.3975
- 2024-11-10: 21.2549
- 2024-11-11: 21.0414
- 2024-11-12: 20.7183
- 2024-11-13: 20.5489
- 2024-11-14: 20.5324
- 2024-11-17: 20.413
- 2024-11-18: 20.404
- 2024-11-19: 20.3767
- 2024-11-20: 20.4037
- 2024-11-21: 20.455
- 2024-11-24: 20.6325
- 2024-11-25: 20.7824
- 2024-11-26: 20.5701
- 2024-11-27: 20.6505
- 2024-11-28: 20.5856
- 2024-12-01: 20.4541

**Change over the 21 sessions (last forecasted close vs last actual close): -7.61%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
