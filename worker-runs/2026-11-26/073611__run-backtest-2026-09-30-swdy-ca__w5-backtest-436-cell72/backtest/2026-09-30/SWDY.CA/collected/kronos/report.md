# Kronos-small forecast — SWDY.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2026-09-30 — 1892 sessions
- As-of cutoff: 2026-09-30 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1892 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 105.0 on 2026-09-30
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-10-01: 103.7459
- 2026-10-04: 100.6623
- 2026-10-05: 101.9414
- 2026-10-06: 99.5615
- 2026-10-07: 98.0388
- 2026-10-08: 97.5456
- 2026-10-11: 95.7033
- 2026-10-12: 95.5617
- 2026-10-13: 93.6289
- 2026-10-14: 92.6311
- 2026-10-15: 91.863
- 2026-10-18: 90.2946
- 2026-10-19: 89.7124
- 2026-10-20: 88.1433
- 2026-10-21: 87.8389
- 2026-10-22: 87.2168
- 2026-10-25: 85.0337
- 2026-10-26: 82.9454
- 2026-10-27: 83.4047
- 2026-10-28: 81.8281
- 2026-10-29: 80.8882

**Change over the 21 sessions (last forecasted close vs last actual close): -22.96%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
