# Kronos-small forecast — ADIB.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2026-09-28 to 2026-11-23 — 39 sessions
- Context supplied to Kronos: 39 sessions, no truncation needed (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2026-09-28) was accepted; no fallback needed.
- Last actual close: 46.43000030517578 on 2026-11-23
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-11-24: 46.0754
- 2026-11-25: 46.3305
- 2026-11-26: 46.5954
- 2026-11-29: 46.4738
- 2026-11-30: 46.7164
- 2026-12-01: 46.6752
- 2026-12-02: 46.6786
- 2026-12-03: 46.6282
- 2026-12-06: 46.7525
- 2026-12-07: 46.6348
- 2026-12-08: 47.1104
- 2026-12-09: 46.9019
- 2026-12-10: 47.0397
- 2026-12-13: 46.8135
- 2026-12-14: 47.0708
- 2026-12-15: 46.962
- 2026-12-16: 46.8454
- 2026-12-17: 47.0086
- 2026-12-20: 46.8393
- 2026-12-21: 46.8382
- 2026-12-22: 46.8002

**Change over the 21 sessions (last forecasted close vs last actual close): +0.80%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
