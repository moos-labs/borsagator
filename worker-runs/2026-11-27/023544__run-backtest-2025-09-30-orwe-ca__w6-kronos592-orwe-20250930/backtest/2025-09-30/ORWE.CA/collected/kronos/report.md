# Kronos-small forecast — ORWE.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2025-09-30 — 1649 sessions
- As-of cutoff: 2025-09-30 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1649 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 22.049999237060547 on 2025-09-30
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2025-10-01: 21.9741
- 2025-10-02: 21.9361
- 2025-10-05: 21.8982
- 2025-10-06: 21.9398
- 2025-10-07: 22.1676
- 2025-10-08: 22.027
- 2025-10-09: 21.8809
- 2025-10-12: 21.8199
- 2025-10-13: 21.8892
- 2025-10-14: 21.7973
- 2025-10-15: 21.9064
- 2025-10-16: 22.0644
- 2025-10-19: 22.0091
- 2025-10-20: 21.8444
- 2025-10-21: 21.7737
- 2025-10-22: 21.8501
- 2025-10-23: 21.6602
- 2025-10-26: 21.405
- 2025-10-27: 21.7082
- 2025-10-28: 21.5475
- 2025-10-29: 21.42

**Change over the 21 sessions (last forecasted close vs last actual close): -2.86%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
