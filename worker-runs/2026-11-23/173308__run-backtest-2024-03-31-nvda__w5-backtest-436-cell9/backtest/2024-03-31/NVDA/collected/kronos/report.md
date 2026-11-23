# Kronos-small forecast — NVDA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, sample_count=1)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-02 to 2024-03-28 — 1319 sessions
- As-of cutoff: 2024-03-31 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1319 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 90.35600280761719 on 2024-03-28
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2024-03-31: 84.4101
- 2024-04-01: 85.9236
- 2024-04-02: 86.5008
- 2024-04-03: 51.9002
- 2024-04-04: 27.261
- 2024-04-07: 26.8245
- 2024-04-08: 27.0856
- 2024-04-09: 27.9286
- 2024-04-10: 29.7748
- 2024-04-11: 30.1471
- 2024-04-14: 31.1088
- 2024-04-15: 32.007
- 2024-04-16: 33.0252
- 2024-04-17: 34.4098
- 2024-04-18: 32.1771
- 2024-04-21: 34.2286
- 2024-04-22: 33.4892
- 2024-04-23: 29.9321
- 2024-04-24: 30.6737
- 2024-04-25: 28.9938
- 2024-04-28: 30.7758

**Change over the 21 sessions (last forecasted close vs last actual close): -65.94%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
