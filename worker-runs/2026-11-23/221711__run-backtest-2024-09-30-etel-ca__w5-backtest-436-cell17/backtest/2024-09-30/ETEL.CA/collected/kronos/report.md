# Kronos-small forecast — ETEL.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, sample_count=1)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2024-09-30 — 1407 sessions
- As-of cutoff: 2024-09-30 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1407 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 33.77000045776367 on 2024-09-30
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2024-10-01: 34.6821
- 2024-10-02: 34.8973
- 2024-10-03: 35.3682
- 2024-10-06: 36.3199
- 2024-10-07: 37.8228
- 2024-10-08: 37.9573
- 2024-10-09: 37.0376
- 2024-10-10: 36.9195
- 2024-10-13: 36.345
- 2024-10-14: 36.1444
- 2024-10-15: 34.2602
- 2024-10-16: 32.8709
- 2024-10-17: 32.3065
- 2024-10-20: 31.1911
- 2024-10-21: 31.0652
- 2024-10-22: 34.1248
- 2024-10-23: 35.1027
- 2024-10-24: 33.9369
- 2024-10-27: 33.8967
- 2024-10-28: 35.8357
- 2024-10-29: 37.5221

**Change over the 21 sessions (last forecasted close vs last actual close): +11.11%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
