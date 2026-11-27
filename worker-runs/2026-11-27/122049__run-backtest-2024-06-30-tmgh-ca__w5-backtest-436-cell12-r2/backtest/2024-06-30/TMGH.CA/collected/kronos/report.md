# Kronos-small forecast — TMGH.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2024-06-27 — 1345 sessions
- As-of cutoff: 2024-06-30 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1345 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 56.88999938964844 on 2024-06-27
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2024-06-30: 57.2434
- 2024-07-01: 58.0087
- 2024-07-02: 58.4843
- 2024-07-03: 59.7031
- 2024-07-04: 57.8144
- 2024-07-07: 57.4708
- 2024-07-08: 58.0361
- 2024-07-09: 57.4599
- 2024-07-10: 58.7663
- 2024-07-11: 59.7448
- 2024-07-14: 57.103
- 2024-07-15: 56.5029
- 2024-07-16: 51.9225
- 2024-07-17: 47.8082
- 2024-07-18: 47.4951
- 2024-07-21: 45.1952
- 2024-07-22: 43.9884
- 2024-07-23: 42.3148
- 2024-07-24: 41.5819
- 2024-07-25: 39.5678
- 2024-07-28: 39.0579

**Change over the 21 sessions (last forecasted close vs last actual close): -31.34%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
