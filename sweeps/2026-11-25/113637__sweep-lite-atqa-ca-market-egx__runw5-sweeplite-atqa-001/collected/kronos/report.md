# Kronos-small forecast — ATQA.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2026-09-28 to 2026-11-23 — 39 sessions
- Context supplied to Kronos: 39 sessions, no truncation needed (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2026-09-28) was accepted; no fallback needed.
- Last actual close: 10.050000190734863 on 2026-11-23
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-11-24: 10.1674
- 2026-11-25: 10.1851
- 2026-11-26: 10.1432
- 2026-11-29: 9.9974
- 2026-11-30: 9.9694
- 2026-12-01: 10.0747
- 2026-12-02: 10.0403
- 2026-12-03: 9.9721
- 2026-12-06: 10.0287
- 2026-12-07: 10.0395
- 2026-12-08: 10.1485
- 2026-12-09: 10.0821
- 2026-12-10: 10.0569
- 2026-12-13: 10.0098
- 2026-12-14: 10.1111
- 2026-12-15: 9.9934
- 2026-12-16: 9.7713
- 2026-12-17: 9.6255
- 2026-12-20: 9.6643
- 2026-12-21: 9.6432
- 2026-12-22: 9.5135

**Change over the 21 sessions (last forecasted close vs last actual close): -5.34%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
