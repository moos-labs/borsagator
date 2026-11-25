# Kronos-small forecast — HRHO.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2025-03-27 — 1532 sessions
- As-of cutoff: 2025-03-31 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1532 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 27.5 on 2025-03-27
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2025-03-30: 26.5327
- 2025-03-31: 25.9631
- 2025-04-01: 25.3195
- 2025-04-02: 24.4531
- 2025-04-03: 24.4882
- 2025-04-06: 23.5908
- 2025-04-07: 23.7249
- 2025-04-08: 23.1828
- 2025-04-09: 22.9902
- 2025-04-10: 22.676
- 2025-04-13: 22.5786
- 2025-04-14: 22.5239
- 2025-04-15: 22.488
- 2025-04-16: 22.367
- 2025-04-17: 22.3765
- 2025-04-20: 22.35
- 2025-04-21: 22.1236
- 2025-04-22: 22.25
- 2025-04-23: 22.1693
- 2025-04-24: 22.0894
- 2025-04-27: 22.0661

**Change over the 21 sessions (last forecasted close vs last actual close): -19.76%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
