# Kronos-small forecast — ORWE.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2024-12-31 — 1472 sessions
- As-of cutoff: 2024-12-31 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1472 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 25.0 on 2024-12-31
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2025-01-01: 24.6109
- 2025-01-02: 24.4568
- 2025-01-05: 24.4837
- 2025-01-06: 24.2537
- 2025-01-07: 24.2728
- 2025-01-08: 24.5682
- 2025-01-09: 24.4105
- 2025-01-12: 23.8741
- 2025-01-13: 24.1906
- 2025-01-14: 24.3685
- 2025-01-15: 24.1971
- 2025-01-16: 24.0906
- 2025-01-19: 24.3297
- 2025-01-20: 24.0686
- 2025-01-21: 24.2761
- 2025-01-22: 24.1826
- 2025-01-23: 24.2608
- 2025-01-26: 24.3188
- 2025-01-27: 24.7986
- 2025-01-28: 24.4035
- 2025-01-29: 24.5818

**Change over the 21 sessions (last forecasted close vs last actual close): -1.67%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
