# Kronos-small forecast — ETEL.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2026-05-14 — 1801 sessions
- As-of cutoff: 2026-05-15 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1801 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 96.5999984741211 on 2026-05-14
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-05-17: 95.1869
- 2026-05-18: 93.8372
- 2026-05-19: 92.7074
- 2026-05-20: 90.1054
- 2026-05-21: 88.2966
- 2026-05-24: 83.7153
- 2026-05-25: 80.7541
- 2026-05-26: 78.6726
- 2026-05-27: 74.3556
- 2026-05-28: 72.8958
- 2026-05-31: 70.9977
- 2026-06-01: 69.7763
- 2026-06-02: 68.2561
- 2026-06-03: 67.6625
- 2026-06-04: 67.2458
- 2026-06-07: 67.9023
- 2026-06-08: 67.6665
- 2026-06-09: 66.1942
- 2026-06-10: 64.6117
- 2026-06-11: 63.461
- 2026-06-14: 61.7212

**Change over the 21 sessions (last forecasted close vs last actual close): -36.11%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
