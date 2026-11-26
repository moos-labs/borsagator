# Kronos-small forecast — SWDY.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2025-08-14 — 1617 sessions
- As-of cutoff: 2025-08-15 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1617 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 80.31999969482422 on 2025-08-14
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2025-08-17: 80.6392
- 2025-08-18: 79.8273
- 2025-08-19: 79.7483
- 2025-08-20: 80.3887
- 2025-08-21: 81.1106
- 2025-08-24: 80.8599
- 2025-08-25: 81.15
- 2025-08-26: 81.2077
- 2025-08-27: 81.0089
- 2025-08-28: 80.4145
- 2025-08-31: 80.2241
- 2025-09-01: 81.1472
- 2025-09-02: 81.6683
- 2025-09-03: 82.7977
- 2025-09-04: 83.4159
- 2025-09-07: 85.7126
- 2025-09-08: 85.1855
- 2025-09-09: 84.6064
- 2025-09-10: 85.3865
- 2025-09-11: 85.1257
- 2025-09-14: 87.0449

**Change over the 21 sessions (last forecasted close vs last actual close): +8.37%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
