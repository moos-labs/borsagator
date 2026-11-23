# Kronos-small forecast — TMGH.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, sample_count=1)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2023-12-28 — 1231 sessions
- As-of cutoff: 2023-12-29 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1231 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 23.850000381469727 on 2023-12-28
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2023-12-31: 21.609
- 2024-01-01: 22.4729
- 2024-01-02: 21.4314
- 2024-01-03: 20.2801
- 2024-01-04: 18.1526
- 2024-01-07: 15.3315
- 2024-01-08: 13.8835
- 2024-01-09: 11.9014
- 2024-01-10: 11.482
- 2024-01-11: 10.6482
- 2024-01-14: 10.2484
- 2024-01-15: 11.2626
- 2024-01-16: 11.5782
- 2024-01-17: 11.0871
- 2024-01-18: 10.7627
- 2024-01-21: 9.8452
- 2024-01-22: 9.3105
- 2024-01-23: 9.681
- 2024-01-24: 9.8167
- 2024-01-25: 9.3506
- 2024-01-28: 9.8921

**Change over the 21 sessions (last forecasted close vs last actual close): -58.52%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
