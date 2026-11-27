# Kronos-small forecast — LCSW.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2026-09-28 to 2026-11-25 — 41 sessions
- Context supplied to Kronos: 41 sessions, no truncation needed (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2026-09-28) was accepted; no fallback needed.
- Last actual close: 41.38999938964844 on 2026-11-25
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-11-26: 41.1314
- 2026-11-29: 40.6797
- 2026-11-30: 40.6886
- 2026-12-01: 40.8066
- 2026-12-02: 40.7262
- 2026-12-03: 40.3108
- 2026-12-06: 40.1455
- 2026-12-07: 39.8915
- 2026-12-08: 39.8814
- 2026-12-09: 39.5117
- 2026-12-10: 39.2358
- 2026-12-13: 38.9876
- 2026-12-14: 38.5919
- 2026-12-15: 38.044
- 2026-12-16: 38.048
- 2026-12-17: 37.5515
- 2026-12-20: 37.3465
- 2026-12-21: 36.8024
- 2026-12-22: 36.798
- 2026-12-23: 36.6377
- 2026-12-24: 36.1717

**Change over the 21 sessions (last forecasted close vs last actual close): -12.61%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
