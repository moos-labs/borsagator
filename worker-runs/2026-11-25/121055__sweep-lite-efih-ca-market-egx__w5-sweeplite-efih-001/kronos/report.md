# Kronos-small forecast — EFIH.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2026-09-28 to 2026-11-23 — 39 sessions
- Context supplied to Kronos: 39 sessions, no truncation needed (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2026-09-28) was accepted; no fallback needed.
- Last actual close: 24.799999237060547 on 2026-11-23
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-11-24: 24.9019
- 2026-11-25: 24.7563
- 2026-11-26: 24.3581
- 2026-11-29: 24.4568
- 2026-11-30: 24.7264
- 2026-12-01: 24.5066
- 2026-12-02: 24.6064
- 2026-12-03: 24.534
- 2026-12-06: 24.8337
- 2026-12-07: 24.7514
- 2026-12-08: 24.7209
- 2026-12-09: 24.6434
- 2026-12-10: 24.4597
- 2026-12-13: 24.4035
- 2026-12-14: 24.243
- 2026-12-15: 24.3881
- 2026-12-16: 24.2975
- 2026-12-17: 24.2364
- 2026-12-20: 24.2681
- 2026-12-21: 24.1516
- 2026-12-22: 24.4503

**Change over the 21 sessions (last forecasted close vs last actual close): -1.41%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
