# Kronos-small forecast — ORWE.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2024-09-30 — 1407 sessions
- As-of cutoff: 2024-09-30 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1407 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 24.0 on 2024-09-30
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2024-10-01: 23.8196
- 2024-10-02: 23.3739
- 2024-10-03: 23.5056
- 2024-10-06: 23.3755
- 2024-10-07: 23.4047
- 2024-10-08: 23.3098
- 2024-10-09: 23.1152
- 2024-10-10: 23.6829
- 2024-10-13: 23.7628
- 2024-10-14: 23.3686
- 2024-10-15: 22.9255
- 2024-10-16: 23.0057
- 2024-10-17: 22.9436
- 2024-10-20: 22.8146
- 2024-10-21: 22.727
- 2024-10-22: 22.0961
- 2024-10-23: 22.2311
- 2024-10-24: 22.2992
- 2024-10-27: 22.3854
- 2024-10-28: 22.5026
- 2024-10-29: 22.6191

**Change over the 21 sessions (last forecasted close vs last actual close): -5.75%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
