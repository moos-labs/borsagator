# Kronos-small forecast — TMGH.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2026-09-28 to 2026-11-25 — 41 sessions
- Context supplied to Kronos: 41 sessions, no truncation needed (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2026-09-28) was accepted; no fallback needed.
- Last actual close: 78.94999694824219 on 2026-11-25
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-11-26: 79.1515
- 2026-11-29: 79.0992
- 2026-11-30: 79.5265
- 2026-12-01: 80.7711
- 2026-12-02: 80.6353
- 2026-12-03: 81.1871
- 2026-12-06: 80.6605
- 2026-12-07: 80.4502
- 2026-12-08: 80.5807
- 2026-12-09: 80.6615
- 2026-12-10: 80.5042
- 2026-12-13: 80.5797
- 2026-12-14: 80.8053
- 2026-12-15: 80.5854
- 2026-12-16: 81.8317
- 2026-12-17: 81.765
- 2026-12-20: 81.1086
- 2026-12-21: 82.0113
- 2026-12-22: 82.0894
- 2026-12-23: 82.3121
- 2026-12-24: 82.2037

**Change over the 21 sessions (last forecasted close vs last actual close): +4.12%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
