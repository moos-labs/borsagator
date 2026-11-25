# Kronos-small forecast — ICFC.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2026-09-28 to 2026-11-23 — 39 sessions
- Context supplied to Kronos: 39 sessions, no truncation needed (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2026-09-28) was accepted; no fallback needed.
- Last actual close: 26.100000381469727 on 2026-11-23
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-11-24: 26.262
- 2026-11-25: 26.1745
- 2026-11-26: 26.0691
- 2026-11-29: 25.4453
- 2026-11-30: 25.5019
- 2026-12-01: 25.2613
- 2026-12-02: 25.3858
- 2026-12-03: 25.0174
- 2026-12-06: 24.9671
- 2026-12-07: 24.7622
- 2026-12-08: 24.6726
- 2026-12-09: 24.8421
- 2026-12-10: 24.7807
- 2026-12-13: 24.7273
- 2026-12-14: 24.3705
- 2026-12-15: 24.3173
- 2026-12-16: 24.4283
- 2026-12-17: 24.2184
- 2026-12-20: 23.9374
- 2026-12-21: 23.295
- 2026-12-22: 23.4672

**Change over the 21 sessions (last forecasted close vs last actual close): -10.09%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
