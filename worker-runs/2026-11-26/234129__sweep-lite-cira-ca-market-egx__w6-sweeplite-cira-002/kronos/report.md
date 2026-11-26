# Kronos-small forecast — CIRA.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2026-09-28 to 2026-11-24 — 40 sessions
- Context supplied to Kronos: 40 sessions, no truncation needed (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2026-09-28) was accepted; no fallback needed.
- Last actual close: 38.45000076293945 on 2026-11-24
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-11-25: 38.5511
- 2026-11-26: 38.4854
- 2026-11-29: 38.3335
- 2026-11-30: 38.7216
- 2026-12-01: 38.7037
- 2026-12-02: 38.74
- 2026-12-03: 38.666
- 2026-12-06: 38.6503
- 2026-12-07: 38.8686
- 2026-12-08: 38.9752
- 2026-12-09: 38.1997
- 2026-12-10: 38.4928
- 2026-12-13: 38.3487
- 2026-12-14: 38.1359
- 2026-12-15: 38.1642
- 2026-12-16: 37.9369
- 2026-12-17: 37.8651
- 2026-12-20: 37.9431
- 2026-12-21: 37.3555
- 2026-12-22: 37.3221
- 2026-12-23: 37.1121

**Change over the 21 sessions (last forecasted close vs last actual close): -3.48%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
