# Kronos-small forecast — COMI.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2024-01-31 — 1252 sessions
- As-of cutoff: 2024-01-31 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1252 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 88.0999984741211 on 2024-01-31
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2024-02-01: 85.9937
- 2024-02-04: 84.4985
- 2024-02-05: 83.9811
- 2024-02-06: 81.786
- 2024-02-07: 81.1081
- 2024-02-08: 81.0073
- 2024-02-11: 79.3939
- 2024-02-12: 76.6555
- 2024-02-13: 73.6396
- 2024-02-14: 71.5861
- 2024-02-15: 67.9821
- 2024-02-18: 66.743
- 2024-02-19: 66.4301
- 2024-02-20: 63.801
- 2024-02-21: 63.6332
- 2024-02-22: 62.9514
- 2024-02-25: 61.8924
- 2024-02-26: 62.3498
- 2024-02-27: 59.9037
- 2024-02-28: 59.4935
- 2024-02-29: 59.3905

**Change over the 21 sessions (last forecasted close vs last actual close): -32.59%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
