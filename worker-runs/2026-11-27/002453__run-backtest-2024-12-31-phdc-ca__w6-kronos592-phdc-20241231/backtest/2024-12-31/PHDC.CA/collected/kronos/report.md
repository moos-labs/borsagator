# Kronos-small forecast — PHDC.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2024-12-31 — 1472 sessions
- As-of cutoff: 2024-12-31 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1472 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 6.539999961853027 on 2024-12-31
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2025-01-01: 6.4251
- 2025-01-02: 6.4065
- 2025-01-05: 6.3216
- 2025-01-06: 6.3162
- 2025-01-07: 6.272
- 2025-01-08: 6.2491
- 2025-01-09: 6.1935
- 2025-01-12: 6.1102
- 2025-01-13: 6.1228
- 2025-01-14: 5.9333
- 2025-01-15: 5.6649
- 2025-01-16: 5.7495
- 2025-01-19: 5.5802
- 2025-01-20: 5.3968
- 2025-01-21: 5.459
- 2025-01-22: 5.3722
- 2025-01-23: 5.3007
- 2025-01-26: 5.2786
- 2025-01-27: 5.2103
- 2025-01-28: 5.1343
- 2025-01-29: 4.9478

**Change over the 21 sessions (last forecasted close vs last actual close): -24.35%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
