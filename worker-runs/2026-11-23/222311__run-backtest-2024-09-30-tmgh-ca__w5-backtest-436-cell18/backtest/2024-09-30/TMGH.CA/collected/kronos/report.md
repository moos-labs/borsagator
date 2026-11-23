# Kronos-small forecast — TMGH.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, sample_count=1)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2024-09-30 — 1407 sessions
- As-of cutoff: 2024-09-30 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1407 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 63.70000076293945 on 2024-09-30
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2024-10-01: 62.348
- 2024-10-02: 63.8335
- 2024-10-03: 64.4521
- 2024-10-06: 63.9295
- 2024-10-07: 70.4769
- 2024-10-08: 74.3923
- 2024-10-09: 74.8049
- 2024-10-10: 72.2864
- 2024-10-13: 73.2173
- 2024-10-14: 63.5105
- 2024-10-15: 56.959
- 2024-10-16: 59.5277
- 2024-10-17: 63.5666
- 2024-10-20: 58.7079
- 2024-10-21: 60.5255
- 2024-10-22: 59.1246
- 2024-10-23: 57.7087
- 2024-10-24: 57.6978
- 2024-10-27: 54.3738
- 2024-10-28: 53.2248
- 2024-10-29: 56.6904

**Change over the 21 sessions (last forecasted close vs last actual close): -11.00%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
