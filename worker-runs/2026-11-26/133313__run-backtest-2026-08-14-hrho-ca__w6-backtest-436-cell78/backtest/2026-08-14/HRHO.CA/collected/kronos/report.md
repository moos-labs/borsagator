# Kronos-small forecast — HRHO.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2026-08-13 — 1859 sessions
- As-of cutoff: 2026-08-14 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1859 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 26.65999984741211 on 2026-08-13
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-08-16: 27.015
- 2026-08-17: 27.0206
- 2026-08-18: 26.9812
- 2026-08-19: 27.1534
- 2026-08-20: 27.0687
- 2026-08-23: 27.1383
- 2026-08-24: 27.3353
- 2026-08-25: 27.3108
- 2026-08-26: 27.3086
- 2026-08-27: 27.5048
- 2026-08-30: 27.4481
- 2026-08-31: 27.5386
- 2026-09-01: 27.6855
- 2026-09-02: 27.6034
- 2026-09-03: 27.7717
- 2026-09-06: 27.8182
- 2026-09-07: 27.9705
- 2026-09-08: 28.0451
- 2026-09-09: 28.153
- 2026-09-10: 27.9355
- 2026-09-13: 27.6679

**Change over the 21 sessions (last forecasted close vs last actual close): +3.78%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
