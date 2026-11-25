# Kronos-small forecast — POUL.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2026-09-28 to 2026-11-22 — 38 sessions
- Context supplied to Kronos: 38 sessions, no truncation needed (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2026-09-28) was accepted; no fallback needed.
- Last actual close: 7.03000020980835 on 2026-11-22
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-11-23: 7.1303
- 2026-11-24: 7.2756
- 2026-11-25: 7.4308
- 2026-11-26: 7.6934
- 2026-11-29: 7.8687
- 2026-11-30: 7.9642
- 2026-12-01: 8.0549
- 2026-12-02: 8.136
- 2026-12-03: 8.2757
- 2026-12-06: 8.3552
- 2026-12-07: 8.3961
- 2026-12-08: 8.6271
- 2026-12-09: 8.6852
- 2026-12-10: 8.7292
- 2026-12-13: 8.8378
- 2026-12-14: 8.9416
- 2026-12-15: 8.9858
- 2026-12-16: 9.0591
- 2026-12-17: 9.2159
- 2026-12-20: 9.2048
- 2026-12-21: 9.3557

**Change over the 21 sessions (last forecasted close vs last actual close): +33.08%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
