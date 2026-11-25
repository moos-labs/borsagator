# Kronos-small forecast — ETEL.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2025-12-31 — 1714 sessions
- As-of cutoff: 2025-12-31 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1714 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 65.7699966430664 on 2025-12-31
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-01-01: 65.6079
- 2026-01-04: 64.9973
- 2026-01-05: 65.0205
- 2026-01-06: 64.6094
- 2026-01-07: 63.209
- 2026-01-08: 63.424
- 2026-01-11: 63.2269
- 2026-01-12: 59.3222
- 2026-01-13: 57.4974
- 2026-01-14: 53.3197
- 2026-01-15: 45.5194
- 2026-01-18: 40.6439
- 2026-01-19: 42.0028
- 2026-01-20: 39.4814
- 2026-01-21: 39.6132
- 2026-01-22: 38.1872
- 2026-01-25: 37.6003
- 2026-01-26: 37.1625
- 2026-01-27: 36.6403
- 2026-01-28: 36.0424
- 2026-01-29: 35.8878

**Change over the 21 sessions (last forecasted close vs last actual close): -45.43%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
