# Kronos-small forecast — FAIT.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2026-09-28 to 2026-11-23 — 39 sessions
- Context supplied to Kronos: 39 sessions, no truncation needed (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2026-09-28) was accepted; no fallback needed.
- Last actual close: 45.369998931884766 on 2026-11-23
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-11-24: 45.3894
- 2026-11-25: 45.6072
- 2026-11-26: 45.7296
- 2026-11-29: 46.0775
- 2026-11-30: 46.123
- 2026-12-01: 45.9756
- 2026-12-02: 45.8936
- 2026-12-03: 45.7557
- 2026-12-06: 45.7926
- 2026-12-07: 45.6566
- 2026-12-08: 45.2445
- 2026-12-09: 45.1548
- 2026-12-10: 45.0055
- 2026-12-13: 44.8269
- 2026-12-14: 44.8673
- 2026-12-15: 44.6376
- 2026-12-16: 44.5131
- 2026-12-17: 44.3343
- 2026-12-20: 44.0861
- 2026-12-21: 44.3094
- 2026-12-22: 44.0159

**Change over the 21 sessions (last forecasted close vs last actual close): -2.98%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
