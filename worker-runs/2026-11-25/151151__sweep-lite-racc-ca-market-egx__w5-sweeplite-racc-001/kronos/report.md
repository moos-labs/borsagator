# Kronos-small forecast — RACC.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2026-09-28 to 2026-11-23 — 39 sessions
- Context supplied to Kronos: 39 sessions, no truncation needed (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2026-09-28) was accepted; no fallback needed.
- Last actual close: 7.75 on 2026-11-23
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-11-24: 7.7324
- 2026-11-25: 7.7141
- 2026-11-26: 7.6886
- 2026-11-29: 7.6717
- 2026-11-30: 7.7014
- 2026-12-01: 7.637
- 2026-12-02: 7.6131
- 2026-12-03: 7.6231
- 2026-12-06: 7.796
- 2026-12-07: 7.6889
- 2026-12-08: 7.732
- 2026-12-09: 7.7134
- 2026-12-10: 7.7069
- 2026-12-13: 7.6794
- 2026-12-14: 7.6035
- 2026-12-15: 7.5861
- 2026-12-16: 7.6458
- 2026-12-17: 7.5611
- 2026-12-20: 7.6186
- 2026-12-21: 7.7503
- 2026-12-22: 7.6429

**Change over the 21 sessions (last forecasted close vs last actual close): -1.38%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
