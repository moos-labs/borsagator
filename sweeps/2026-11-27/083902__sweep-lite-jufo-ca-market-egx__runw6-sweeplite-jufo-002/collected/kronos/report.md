# Kronos-small forecast — JUFO.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2026-09-28 to 2026-11-25 — 41 sessions
- Context supplied to Kronos: 41 sessions, no truncation needed (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2026-09-28) was accepted; no fallback needed.
- Last actual close: 21.850000381469727 on 2026-11-25
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-11-26: 22.1045
- 2026-11-29: 22.2218
- 2026-11-30: 22.3655
- 2026-12-01: 22.8622
- 2026-12-02: 22.541
- 2026-12-03: 22.6718
- 2026-12-06: 22.7198
- 2026-12-07: 22.9073
- 2026-12-08: 23.0826
- 2026-12-09: 23.2146
- 2026-12-10: 22.9258
- 2026-12-13: 22.7866
- 2026-12-14: 22.7873
- 2026-12-15: 22.8983
- 2026-12-16: 22.8487
- 2026-12-17: 22.9861
- 2026-12-20: 22.9589
- 2026-12-21: 23.1695
- 2026-12-22: 23.2929
- 2026-12-23: 23.4276
- 2026-12-24: 23.2596

**Change over the 21 sessions (last forecasted close vs last actual close): +6.45%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
