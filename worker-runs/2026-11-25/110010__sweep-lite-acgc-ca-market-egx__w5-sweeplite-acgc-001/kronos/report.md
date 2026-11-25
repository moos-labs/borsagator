# Kronos-small forecast — ACGC.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2026-09-28 to 2026-11-23 — 39 sessions
- Context supplied to Kronos: 39 sessions, no truncation needed (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2026-09-28) was accepted; no fallback needed.
- Last actual close: 13.5 on 2026-11-23
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-11-24: 13.5688
- 2026-11-25: 13.6455
- 2026-11-26: 13.663
- 2026-11-29: 13.6425
- 2026-11-30: 13.7348
- 2026-12-01: 13.6677
- 2026-12-02: 13.6253
- 2026-12-03: 13.5895
- 2026-12-06: 13.5535
- 2026-12-07: 13.524
- 2026-12-08: 13.5919
- 2026-12-09: 13.5987
- 2026-12-10: 13.4983
- 2026-12-13: 13.5962
- 2026-12-14: 13.5358
- 2026-12-15: 13.4448
- 2026-12-16: 13.6281
- 2026-12-17: 13.4582
- 2026-12-20: 13.4337
- 2026-12-21: 13.3302
- 2026-12-22: 13.234

**Change over the 21 sessions (last forecasted close vs last actual close): -1.97%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
