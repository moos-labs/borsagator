# Kronos-small forecast — PHDC.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2024-09-30 — 1407 sessions
- As-of cutoff: 2024-09-30 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1407 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 6.650000095367432 on 2024-09-30
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2024-10-01: 6.3448
- 2024-10-02: 5.9951
- 2024-10-03: 5.6047
- 2024-10-06: 5.3899
- 2024-10-07: 5.1513
- 2024-10-08: 4.8858
- 2024-10-09: 4.7272
- 2024-10-10: 4.4302
- 2024-10-13: 4.5508
- 2024-10-14: 4.4033
- 2024-10-15: 4.337
- 2024-10-16: 4.2203
- 2024-10-17: 4.2246
- 2024-10-20: 4.1211
- 2024-10-21: 4.0635
- 2024-10-22: 4.0835
- 2024-10-23: 3.991
- 2024-10-24: 4.064
- 2024-10-27: 4.0869
- 2024-10-28: 3.9905
- 2024-10-29: 3.9907

**Change over the 21 sessions (last forecasted close vs last actual close): -39.99%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
