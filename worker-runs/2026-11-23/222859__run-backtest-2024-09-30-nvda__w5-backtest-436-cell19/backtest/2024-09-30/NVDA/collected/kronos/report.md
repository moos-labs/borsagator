# Kronos-small forecast — NVDA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, sample_count=1)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-02 to 2024-09-30 — 1446 sessions
- As-of cutoff: 2024-09-30 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1446 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 121.44000244140625 on 2024-09-30
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2024-10-01: 117.6745
- 2024-10-02: 112.9726
- 2024-10-03: 110.2785
- 2024-10-06: 97.6903
- 2024-10-07: 94.7854
- 2024-10-08: 84.8732
- 2024-10-09: 76.1433
- 2024-10-10: 64.2141
- 2024-10-13: 63.3224
- 2024-10-14: 66.7157
- 2024-10-15: 62.6751
- 2024-10-16: 67.2128
- 2024-10-17: 68.2047
- 2024-10-20: 65.678
- 2024-10-21: 65.6055
- 2024-10-22: 74.3121
- 2024-10-23: 76.4011
- 2024-10-24: 71.666
- 2024-10-27: 65.6337
- 2024-10-28: 58.4132
- 2024-10-29: 78.3181

**Change over the 21 sessions (last forecasted close vs last actual close): -35.51%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
