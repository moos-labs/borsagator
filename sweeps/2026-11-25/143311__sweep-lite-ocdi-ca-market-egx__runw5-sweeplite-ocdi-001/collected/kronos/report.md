# Kronos-small forecast — OCDI.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2026-09-28 to 2026-11-23 — 39 sessions
- Context supplied to Kronos: 39 sessions, no truncation needed (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2026-09-28) was accepted; no fallback needed.
- Last actual close: 23.31999969482422 on 2026-11-23
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-11-24: 23.4263
- 2026-11-25: 23.4585
- 2026-11-26: 23.3299
- 2026-11-29: 23.7403
- 2026-11-30: 23.8604
- 2026-12-01: 24.1607
- 2026-12-02: 23.9055
- 2026-12-03: 23.9612
- 2026-12-06: 24.2094
- 2026-12-07: 24.4686
- 2026-12-08: 24.3649
- 2026-12-09: 24.7083
- 2026-12-10: 24.6208
- 2026-12-13: 24.6786
- 2026-12-14: 24.7455
- 2026-12-15: 24.5094
- 2026-12-16: 24.5553
- 2026-12-17: 24.7171
- 2026-12-20: 24.5764
- 2026-12-21: 24.6575
- 2026-12-22: 24.571

**Change over the 21 sessions (last forecasted close vs last actual close): +5.36%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
