# Kronos-small forecast — TMGH.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2024-10-31 — 1429 sessions
- As-of cutoff: 2024-10-31 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1429 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 59.11000061035156 on 2024-10-31
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2024-11-03: 57.7028
- 2024-11-04: 58.079
- 2024-11-05: 58.8438
- 2024-11-06: 58.4188
- 2024-11-07: 59.8042
- 2024-11-10: 59.6986
- 2024-11-11: 59.3517
- 2024-11-12: 59.9322
- 2024-11-13: 59.8335
- 2024-11-14: 60.092
- 2024-11-17: 63.5324
- 2024-11-18: 62.5811
- 2024-11-19: 62.3993
- 2024-11-20: 64.0697
- 2024-11-21: 66.285
- 2024-11-24: 64.7345
- 2024-11-25: 66.0205
- 2024-11-26: 67.957
- 2024-11-27: 67.1023
- 2024-11-28: 64.9931
- 2024-12-01: 64.7613

**Change over the 21 sessions (last forecasted close vs last actual close): +9.56%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
