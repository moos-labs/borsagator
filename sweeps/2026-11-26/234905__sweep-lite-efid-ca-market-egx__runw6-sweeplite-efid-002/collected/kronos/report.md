# Kronos-small forecast — EFID.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2026-09-28 to 2026-11-24 — 40 sessions
- Context supplied to Kronos: 40 sessions, no truncation needed (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2026-09-28) was accepted; no fallback needed.
- Last actual close: 20.399999618530273 on 2026-11-24
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-11-25: 20.4607
- 2026-11-26: 20.3166
- 2026-11-29: 20.2589
- 2026-11-30: 20.2682
- 2026-12-01: 20.2235
- 2026-12-02: 20.3147
- 2026-12-03: 20.0034
- 2026-12-06: 20.121
- 2026-12-07: 19.8959
- 2026-12-08: 19.775
- 2026-12-09: 19.5126
- 2026-12-10: 19.5756
- 2026-12-13: 19.5353
- 2026-12-14: 19.3456
- 2026-12-15: 19.262
- 2026-12-16: 19.2214
- 2026-12-17: 19.1813
- 2026-12-20: 19.1101
- 2026-12-21: 19.0665
- 2026-12-22: 18.9159
- 2026-12-23: 18.7332

**Change over the 21 sessions (last forecasted close vs last actual close): -8.17%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
