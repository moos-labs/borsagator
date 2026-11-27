# Kronos-small forecast — OLFI.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2026-09-28 to 2026-11-25 — 41 sessions
- Context supplied to Kronos: 41 sessions, no truncation needed (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2026-09-28) was accepted; no fallback needed.
- Last actual close: 20.3799991607666 on 2026-11-25
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-11-26: 20.3106
- 2026-11-29: 20.2965
- 2026-11-30: 20.3217
- 2026-12-01: 20.3635
- 2026-12-02: 20.4508
- 2026-12-03: 20.1688
- 2026-12-06: 20.1966
- 2026-12-07: 20.056
- 2026-12-08: 20.0262
- 2026-12-09: 20.2186
- 2026-12-10: 20.2071
- 2026-12-13: 20.2623
- 2026-12-14: 20.2412
- 2026-12-15: 20.1626
- 2026-12-16: 20.1795
- 2026-12-17: 19.8904
- 2026-12-20: 19.8543
- 2026-12-21: 19.7719
- 2026-12-22: 19.8283
- 2026-12-23: 19.8212
- 2026-12-24: 19.7879

**Change over the 21 sessions (last forecasted close vs last actual close): -2.91%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
