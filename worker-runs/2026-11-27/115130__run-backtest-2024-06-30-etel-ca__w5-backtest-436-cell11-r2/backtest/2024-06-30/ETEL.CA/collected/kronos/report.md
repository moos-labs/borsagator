# Kronos-small forecast — ETEL.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2024-06-27 — 1345 sessions
- As-of cutoff: 2024-06-30 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1345 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 31.15999984741211 on 2024-06-27
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2024-06-30: 30.9663
- 2024-07-01: 31.4938
- 2024-07-02: 32.1708
- 2024-07-03: 32.3859
- 2024-07-04: 33.0742
- 2024-07-07: 33.0854
- 2024-07-08: 33.5533
- 2024-07-09: 32.9907
- 2024-07-10: 33.0358
- 2024-07-11: 33.3828
- 2024-07-14: 33.4705
- 2024-07-15: 33.4407
- 2024-07-16: 33.7614
- 2024-07-17: 33.8722
- 2024-07-18: 33.4361
- 2024-07-21: 33.2035
- 2024-07-22: 34.0571
- 2024-07-23: 34.4627
- 2024-07-24: 34.8653
- 2024-07-25: 34.3371
- 2024-07-28: 34.7961

**Change over the 21 sessions (last forecasted close vs last actual close): +11.67%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
