# Kronos-small forecast — SWDY.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2024-12-31 — 1472 sessions
- As-of cutoff: 2024-12-31 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1472 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 75.87999725341797 on 2024-12-31
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2025-01-01: 77.2883
- 2025-01-02: 76.3516
- 2025-01-05: 76.7992
- 2025-01-06: 75.9758
- 2025-01-07: 77.04
- 2025-01-08: 76.607
- 2025-01-09: 77.2264
- 2025-01-12: 77.9088
- 2025-01-13: 77.6977
- 2025-01-14: 77.2425
- 2025-01-15: 75.0729
- 2025-01-16: 74.1049
- 2025-01-19: 71.9391
- 2025-01-20: 69.3749
- 2025-01-21: 67.9382
- 2025-01-22: 69.089
- 2025-01-23: 64.1839
- 2025-01-26: 64.0515
- 2025-01-27: 62.4683
- 2025-01-28: 60.8455
- 2025-01-29: 60.8652

**Change over the 21 sessions (last forecasted close vs last actual close): -19.79%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
