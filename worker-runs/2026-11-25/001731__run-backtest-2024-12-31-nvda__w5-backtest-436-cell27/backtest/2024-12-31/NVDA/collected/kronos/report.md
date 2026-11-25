# Kronos-small forecast — NVDA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-02 to 2024-12-31 — 1510 sessions
- As-of cutoff: 2024-12-31 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1510 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 134.2899932861328 on 2024-12-31
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2025-01-01: 134.7448
- 2025-01-02: 132.2467
- 2025-01-05: 127.0854
- 2025-01-06: 125.5767
- 2025-01-07: 125.8117
- 2025-01-08: 123.2705
- 2025-01-09: 120.1729
- 2025-01-12: 118.1245
- 2025-01-13: 112.6079
- 2025-01-14: 114.2631
- 2025-01-15: 116.1909
- 2025-01-16: 112.3009
- 2025-01-19: 109.4391
- 2025-01-20: 108.3569
- 2025-01-21: 104.5695
- 2025-01-22: 106.3312
- 2025-01-23: 105.118
- 2025-01-26: 100.0586
- 2025-01-27: 103.0502
- 2025-01-28: 104.3183
- 2025-01-29: 105.8989

**Change over the 21 sessions (last forecasted close vs last actual close): -21.14%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
