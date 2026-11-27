# Kronos-small forecast — SKPC.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2026-09-28 to 2026-11-25 — 41 sessions
- Context supplied to Kronos: 41 sessions, no truncation needed (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2026-09-28) was accepted; no fallback needed.
- Last actual close: 14.760000228881836 on 2026-11-25
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-11-26: 14.8229
- 2026-11-29: 14.7718
- 2026-11-30: 14.9522
- 2026-12-01: 14.999
- 2026-12-02: 14.9245
- 2026-12-03: 14.8505
- 2026-12-06: 14.8659
- 2026-12-07: 14.8564
- 2026-12-08: 14.9216
- 2026-12-09: 14.9765
- 2026-12-10: 14.7469
- 2026-12-13: 14.77
- 2026-12-14: 14.6164
- 2026-12-15: 14.6898
- 2026-12-16: 14.7745
- 2026-12-17: 14.7718
- 2026-12-20: 14.6966
- 2026-12-21: 14.8305
- 2026-12-22: 14.832
- 2026-12-23: 14.8795
- 2026-12-24: 14.8106

**Change over the 21 sessions (last forecasted close vs last actual close): +0.34%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
