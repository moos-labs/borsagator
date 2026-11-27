# Kronos-small forecast — MASR.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2026-09-28 to 2026-11-25 — 41 sessions
- Context supplied to Kronos: 41 sessions, no truncation needed (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2026-09-28) was accepted; no fallback needed.
- Last actual close: 6.230000019073486 on 2026-11-25
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-11-26: 6.2087
- 2026-11-29: 6.249
- 2026-11-30: 6.2574
- 2026-12-01: 6.2995
- 2026-12-02: 6.272
- 2026-12-03: 6.3096
- 2026-12-06: 6.4357
- 2026-12-07: 6.4463
- 2026-12-08: 6.4576
- 2026-12-09: 6.4349
- 2026-12-10: 6.4363
- 2026-12-13: 6.4498
- 2026-12-14: 6.4738
- 2026-12-15: 6.4313
- 2026-12-16: 6.3941
- 2026-12-17: 6.3713
- 2026-12-20: 6.3661
- 2026-12-21: 6.5551
- 2026-12-22: 6.5725
- 2026-12-23: 6.5626
- 2026-12-24: 6.6301

**Change over the 21 sessions (last forecasted close vs last actual close): +6.42%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
