# Kronos-small forecast — TMGH.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, sample_count=1)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2024-03-31 — 1294 sessions
- As-of cutoff: 2024-03-31 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1294 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 61.5 on 2024-03-31
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2024-04-01: 59.2946
- 2024-04-02: 61.4425
- 2024-04-03: 66.1783
- 2024-04-04: 69.8929
- 2024-04-07: 68.9521
- 2024-04-08: 50.2437
- 2024-04-09: 21.7758
- 2024-04-10: 16.5345
- 2024-04-11: 15.9261
- 2024-04-14: 14.9913
- 2024-04-15: 15.0645
- 2024-04-16: 15.1618
- 2024-04-17: 16.8594
- 2024-04-18: 16.6727
- 2024-04-21: 15.0038
- 2024-04-22: 16.1411
- 2024-04-23: 14.3262
- 2024-04-24: 14.2924
- 2024-04-25: 13.27
- 2024-04-28: 11.6266
- 2024-04-29: 12.7592

**Change over the 21 sessions (last forecasted close vs last actual close): -79.25%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
