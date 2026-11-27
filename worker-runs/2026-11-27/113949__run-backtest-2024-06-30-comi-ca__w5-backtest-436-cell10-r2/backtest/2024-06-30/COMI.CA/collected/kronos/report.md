# Kronos-small forecast — COMI.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2024-06-27 — 1345 sessions
- As-of cutoff: 2024-06-30 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1345 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 77.4000015258789 on 2024-06-27
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2024-06-30: 76.0393
- 2024-07-01: 76.4454
- 2024-07-02: 76.6279
- 2024-07-03: 76.5095
- 2024-07-04: 76.2786
- 2024-07-07: 76.8426
- 2024-07-08: 75.8622
- 2024-07-09: 75.9082
- 2024-07-10: 75.6549
- 2024-07-11: 74.6992
- 2024-07-14: 74.1951
- 2024-07-15: 74.9546
- 2024-07-16: 76.0025
- 2024-07-17: 75.431
- 2024-07-18: 74.9722
- 2024-07-21: 75.845
- 2024-07-22: 75.3725
- 2024-07-23: 75.595
- 2024-07-24: 75.0963
- 2024-07-25: 74.9935
- 2024-07-28: 74.5815

**Change over the 21 sessions (last forecasted close vs last actual close): -3.64%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
