# Kronos-small forecast — TMGH.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2026-05-14 — 1801 sessions
- As-of cutoff: 2026-05-15 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1801 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 95.1500015258789 on 2026-05-14
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-05-17: 96.9264
- 2026-05-18: 96.7254
- 2026-05-19: 97.0757
- 2026-05-20: 96.4283
- 2026-05-21: 96.0126
- 2026-05-24: 95.1926
- 2026-05-25: 95.0081
- 2026-05-26: 92.3324
- 2026-05-27: 89.9362
- 2026-05-28: 87.0671
- 2026-05-31: 79.1805
- 2026-06-01: 71.7457
- 2026-06-02: 70.4231
- 2026-06-03: 68.8534
- 2026-06-04: 67.683
- 2026-06-07: 66.5362
- 2026-06-08: 66.4458
- 2026-06-09: 65.0548
- 2026-06-10: 64.8668
- 2026-06-11: 63.8626
- 2026-06-14: 64.1034

**Change over the 21 sessions (last forecasted close vs last actual close): -32.63%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
