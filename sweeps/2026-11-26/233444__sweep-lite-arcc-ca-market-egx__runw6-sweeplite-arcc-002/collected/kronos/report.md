# Kronos-small forecast — ARCC.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2026-09-28 to 2026-11-24 — 40 sessions
- Context supplied to Kronos: 40 sessions, no truncation needed (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2026-09-28) was accepted; no fallback needed.
- Last actual close: 67.02999877929688 on 2026-11-24
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-11-25: 67.0848
- 2026-11-26: 67.0996
- 2026-11-29: 66.7037
- 2026-11-30: 66.9282
- 2026-12-01: 66.7404
- 2026-12-02: 67.048
- 2026-12-03: 66.8431
- 2026-12-06: 67.0103
- 2026-12-07: 67.4502
- 2026-12-08: 66.6881
- 2026-12-09: 66.073
- 2026-12-10: 66.2637
- 2026-12-13: 66.3421
- 2026-12-14: 65.9365
- 2026-12-15: 66.0979
- 2026-12-16: 66.1666
- 2026-12-17: 65.7588
- 2026-12-20: 64.2859
- 2026-12-21: 64.4115
- 2026-12-22: 64.381
- 2026-12-23: 64.5525

**Change over the 21 sessions (last forecasted close vs last actual close): -3.70%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
