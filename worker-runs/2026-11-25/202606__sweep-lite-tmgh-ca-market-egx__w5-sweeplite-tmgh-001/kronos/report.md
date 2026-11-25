# Kronos-small forecast — TMGH.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2026-09-28 to 2026-11-23 — 39 sessions
- Context supplied to Kronos: 39 sessions, no truncation needed (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2026-09-28) was accepted; no fallback needed.
- Last actual close: 79.5 on 2026-11-23
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-11-24: 80.0516
- 2026-11-25: 80.56
- 2026-11-26: 80.9232
- 2026-11-29: 81.0292
- 2026-11-30: 80.8816
- 2026-12-01: 81.6653
- 2026-12-02: 81.6522
- 2026-12-03: 81.6142
- 2026-12-06: 81.3938
- 2026-12-07: 82.1283
- 2026-12-08: 81.8081
- 2026-12-09: 82.4998
- 2026-12-10: 82.1412
- 2026-12-13: 81.703
- 2026-12-14: 82.1858
- 2026-12-15: 81.9427
- 2026-12-16: 82.0935
- 2026-12-17: 82.0128
- 2026-12-20: 82.5472
- 2026-12-21: 82.7409
- 2026-12-22: 82.36

**Change over the 21 sessions (last forecasted close vs last actual close): +3.60%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
