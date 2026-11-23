# Kronos-small forecast — NVDA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, sample_count=1)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-02 to 2024-06-28 — 1382 sessions
- As-of cutoff: 2024-06-30 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1382 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 123.54000091552734 on 2024-06-28
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2024-06-30: 135.197
- 2024-07-01: 103.9725
- 2024-07-02: 103.3202
- 2024-07-03: 74.1077
- 2024-07-04: 65.7714
- 2024-07-07: 55.1218
- 2024-07-08: 51.5321
- 2024-07-09: 32.9156
- 2024-07-10: 41.7558
- 2024-07-11: 38.3293
- 2024-07-14: 38.0788
- 2024-07-15: 43.8209
- 2024-07-16: 44.591
- 2024-07-17: 48.3207
- 2024-07-18: 43.8955
- 2024-07-21: 46.7591
- 2024-07-22: 44.958
- 2024-07-23: 46.4371
- 2024-07-24: 43.1635
- 2024-07-25: 40.2724
- 2024-07-28: 42.3917

**Change over the 21 sessions (last forecasted close vs last actual close): -65.69%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
