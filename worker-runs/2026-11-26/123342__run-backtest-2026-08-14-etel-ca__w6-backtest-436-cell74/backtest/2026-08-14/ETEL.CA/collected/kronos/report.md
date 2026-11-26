# Kronos-small forecast — ETEL.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2026-08-13 — 1859 sessions
- As-of cutoff: 2026-08-14 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1859 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 114.0 on 2026-08-13
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-08-16: 114.0251
- 2026-08-17: 113.1549
- 2026-08-18: 113.4229
- 2026-08-19: 111.3767
- 2026-08-20: 110.7708
- 2026-08-23: 109.5969
- 2026-08-24: 103.9734
- 2026-08-25: 102.0583
- 2026-08-26: 98.1681
- 2026-08-27: 89.8686
- 2026-08-30: 85.4487
- 2026-08-31: 84.695
- 2026-09-01: 82.7025
- 2026-09-02: 81.3543
- 2026-09-03: 80.1329
- 2026-09-06: 81.5057
- 2026-09-07: 82.4277
- 2026-09-08: 82.1455
- 2026-09-09: 76.3386
- 2026-09-10: 75.2369
- 2026-09-13: 76.086

**Change over the 21 sessions (last forecasted close vs last actual close): -33.26%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
