# Kronos-small forecast — TMGH.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2025-11-13 — 1680 sessions
- As-of cutoff: 2025-11-14 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1680 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 71.5999984741211 on 2025-11-13
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2025-11-16: 71.5712
- 2025-11-17: 70.1805
- 2025-11-18: 69.2717
- 2025-11-19: 69.1772
- 2025-11-20: 68.2555
- 2025-11-23: 68.6529
- 2025-11-24: 68.0627
- 2025-11-25: 67.0728
- 2025-11-26: 65.265
- 2025-11-27: 63.2857
- 2025-11-30: 63.2879
- 2025-12-01: 63.3901
- 2025-12-02: 62.1864
- 2025-12-03: 62.0725
- 2025-12-04: 62.9747
- 2025-12-07: 62.8016
- 2025-12-08: 62.4802
- 2025-12-09: 62.1599
- 2025-12-10: 61.4718
- 2025-12-11: 59.8717
- 2025-12-14: 61.118

**Change over the 21 sessions (last forecasted close vs last actual close): -14.64%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
