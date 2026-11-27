# Kronos-small forecast — SAUD.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2026-09-28 to 2026-11-25 — 41 sessions
- Context supplied to Kronos: 41 sessions, no truncation needed (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2026-09-28) was accepted; no fallback needed.
- Last actual close: 21.950000762939453 on 2026-11-25
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-11-26: 21.964
- 2026-11-29: 21.9311
- 2026-11-30: 21.8426
- 2026-12-01: 21.9274
- 2026-12-02: 21.9547
- 2026-12-03: 21.8486
- 2026-12-06: 21.8328
- 2026-12-07: 21.6702
- 2026-12-08: 21.8998
- 2026-12-09: 21.7652
- 2026-12-10: 21.4717
- 2026-12-13: 21.6697
- 2026-12-14: 21.7156
- 2026-12-15: 21.439
- 2026-12-16: 21.5911
- 2026-12-17: 21.8333
- 2026-12-20: 21.3132
- 2026-12-21: 21.2078
- 2026-12-22: 21.2945
- 2026-12-23: 21.2588
- 2026-12-24: 21.3928

**Change over the 21 sessions (last forecasted close vs last actual close): -2.54%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
