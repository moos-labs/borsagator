# Kronos-small forecast — NVDA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, sample_count=1)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-02 to 2023-12-29 — 1258 sessions
- As-of cutoff: 2023-12-29 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1258 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 49.52199935913086 on 2023-12-29
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2023-12-31: 51.3844
- 2024-01-01: 52.7655
- 2024-01-02: 54.4705
- 2024-01-03: 52.3875
- 2024-01-04: 56.1152
- 2024-01-07: 53.6072
- 2024-01-08: 48.6409
- 2024-01-09: 46.8211
- 2024-01-10: 40.7294
- 2024-01-11: 40.384
- 2024-01-14: 36.9967
- 2024-01-15: 35.6421
- 2024-01-16: 34.9085
- 2024-01-17: 34.2548
- 2024-01-18: 31.9316
- 2024-01-21: 31.5571
- 2024-01-22: 36.7296
- 2024-01-23: 28.5523
- 2024-01-24: 28.7666
- 2024-01-25: 30.633
- 2024-01-28: 33.1193

**Change over the 21 sessions (last forecasted close vs last actual close): -33.12%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
