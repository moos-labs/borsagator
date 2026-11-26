# Kronos-small forecast — TMGH.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2025-08-14 — 1617 sessions
- As-of cutoff: 2025-08-15 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1617 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 55.5 on 2025-08-14
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2025-08-17: 54.4148
- 2025-08-18: 55.0104
- 2025-08-19: 54.8824
- 2025-08-20: 55.3101
- 2025-08-21: 55.4863
- 2025-08-24: 55.9935
- 2025-08-25: 55.039
- 2025-08-26: 55.1404
- 2025-08-27: 55.3523
- 2025-08-28: 55.1324
- 2025-08-31: 55.99
- 2025-09-01: 57.1964
- 2025-09-02: 56.5831
- 2025-09-03: 56.3671
- 2025-09-04: 57.4064
- 2025-09-07: 58.1613
- 2025-09-08: 58.1996
- 2025-09-09: 58.0362
- 2025-09-10: 57.895
- 2025-09-11: 57.3597
- 2025-09-14: 57.8182

**Change over the 21 sessions (last forecasted close vs last actual close): +4.18%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
