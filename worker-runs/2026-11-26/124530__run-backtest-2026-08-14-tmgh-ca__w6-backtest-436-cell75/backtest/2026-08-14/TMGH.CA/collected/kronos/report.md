# Kronos-small forecast — TMGH.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2026-08-13 — 1859 sessions
- As-of cutoff: 2026-08-14 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1859 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 97.80000305175781 on 2026-08-13
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-08-16: 97.9627
- 2026-08-17: 98.3152
- 2026-08-18: 98.7582
- 2026-08-19: 99.002
- 2026-08-20: 99.387
- 2026-08-23: 98.0737
- 2026-08-24: 98.1914
- 2026-08-25: 97.3288
- 2026-08-26: 96.9416
- 2026-08-27: 95.5969
- 2026-08-30: 95.0432
- 2026-08-31: 93.9418
- 2026-09-01: 93.2757
- 2026-09-02: 90.4753
- 2026-09-03: 89.5144
- 2026-09-06: 88.8557
- 2026-09-07: 88.2213
- 2026-09-08: 87.8724
- 2026-09-09: 87.2634
- 2026-09-10: 86.2253
- 2026-09-13: 85.7094

**Change over the 21 sessions (last forecasted close vs last actual close): -12.36%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
