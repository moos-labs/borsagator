# Kronos-small forecast — POUL.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, sample_count=1)
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

- 2026-11-23: 7.1234
- 2026-11-24: 7.1161
- 2026-11-25: 7.2674
- 2026-11-26: 7.4545
- 2026-11-29: 7.4878
- 2026-11-30: 7.6416
- 2026-12-01: 7.5467
- 2026-12-02: 7.6763
- 2026-12-03: 8.6191
- 2026-12-06: 8.7098
- 2026-12-07: 8.4284
- 2026-12-08: 8.4974
- 2026-12-09: 8.3999
- 2026-12-10: 8.5385
- 2026-12-13: 8.4093
- 2026-12-14: 8.449
- 2026-12-15: 8.6438
- 2026-12-16: 9.4238
- 2026-12-17: 9.5579
- 2026-12-20: 9.5803
- 2026-12-21: 9.4439

**Change over the 21 sessions (last forecasted close vs last actual close): +34.34%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
