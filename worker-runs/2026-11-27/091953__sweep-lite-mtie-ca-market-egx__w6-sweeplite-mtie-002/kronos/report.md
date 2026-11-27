# Kronos-small forecast — MTIE.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2026-09-28 to 2026-11-25 — 41 sessions
- Context supplied to Kronos: 41 sessions, no truncation needed (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2026-09-28) was accepted; no fallback needed.
- Last actual close: 6.75 on 2026-11-25
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-11-26: 6.8359
- 2026-11-29: 6.7558
- 2026-11-30: 6.8283
- 2026-12-01: 6.8948
- 2026-12-02: 6.7609
- 2026-12-03: 6.8644
- 2026-12-06: 6.8452
- 2026-12-07: 6.9614
- 2026-12-08: 6.953
- 2026-12-09: 7.0428
- 2026-12-10: 7.0039
- 2026-12-13: 7.0334
- 2026-12-14: 6.9351
- 2026-12-15: 6.9933
- 2026-12-16: 6.922
- 2026-12-17: 6.9959
- 2026-12-20: 6.9229
- 2026-12-21: 6.9363
- 2026-12-22: 6.8493
- 2026-12-23: 6.9209
- 2026-12-24: 6.9951

**Change over the 21 sessions (last forecasted close vs last actual close): +3.63%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
