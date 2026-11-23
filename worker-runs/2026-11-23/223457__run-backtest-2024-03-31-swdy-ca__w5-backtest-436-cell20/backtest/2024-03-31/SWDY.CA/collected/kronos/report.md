# Kronos-small forecast — SWDY.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, sample_count=1)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2024-03-31 — 1294 sessions
- As-of cutoff: 2024-03-31 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1294 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 31.5 on 2024-03-31
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2024-04-01: 30.6937
- 2024-04-02: 30.6639
- 2024-04-03: 30.2952
- 2024-04-04: 30.8
- 2024-04-07: 32.2978
- 2024-04-08: 32.1093
- 2024-04-09: 30.6012
- 2024-04-10: 30.021
- 2024-04-11: 29.3341
- 2024-04-14: 27.8044
- 2024-04-15: 28.0286
- 2024-04-16: 29.8805
- 2024-04-17: 30.3552
- 2024-04-18: 29.5869
- 2024-04-21: 28.7389
- 2024-04-22: 30.1416
- 2024-04-23: 29.386
- 2024-04-24: 28.5959
- 2024-04-25: 27.1665
- 2024-04-28: 29.1086
- 2024-04-29: 29.0274

**Change over the 21 sessions (last forecasted close vs last actual close): -7.85%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
