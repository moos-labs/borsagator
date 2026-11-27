# Kronos-small forecast — PHDC.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2026-09-28 to 2026-11-25 — 41 sessions
- Context supplied to Kronos: 41 sessions, no truncation needed (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2026-09-28) was accepted; no fallback needed.
- Last actual close: 11.350000381469727 on 2026-11-25
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-11-26: 11.4008
- 2026-11-29: 11.4034
- 2026-11-30: 11.3539
- 2026-12-01: 11.5442
- 2026-12-02: 11.5167
- 2026-12-03: 11.5377
- 2026-12-06: 11.5422
- 2026-12-07: 11.5386
- 2026-12-08: 11.5741
- 2026-12-09: 11.541
- 2026-12-10: 11.4891
- 2026-12-13: 11.4881
- 2026-12-14: 11.4325
- 2026-12-15: 11.4376
- 2026-12-16: 11.5937
- 2026-12-17: 11.5759
- 2026-12-20: 11.4938
- 2026-12-21: 11.7096
- 2026-12-22: 11.6771
- 2026-12-23: 11.5167
- 2026-12-24: 11.5296

**Change over the 21 sessions (last forecasted close vs last actual close): +1.58%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
