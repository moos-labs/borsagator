# Kronos-small forecast — SWDY.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2025-09-30 — 1649 sessions
- As-of cutoff: 2025-09-30 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1649 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 73.9000015258789 on 2025-09-30
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2025-10-01: 74.5569
- 2025-10-02: 74.7038
- 2025-10-05: 74.8088
- 2025-10-06: 76.0662
- 2025-10-07: 77.0644
- 2025-10-08: 77.3999
- 2025-10-09: 77.5162
- 2025-10-12: 77.3527
- 2025-10-13: 78.0388
- 2025-10-14: 79.3535
- 2025-10-15: 79.4583
- 2025-10-16: 79.7151
- 2025-10-19: 80.7244
- 2025-10-20: 82.2041
- 2025-10-21: 83.6878
- 2025-10-22: 85.1679
- 2025-10-23: 83.5076
- 2025-10-26: 84.2155
- 2025-10-27: 85.2271
- 2025-10-28: 86.9644
- 2025-10-29: 87.9686

**Change over the 21 sessions (last forecasted close vs last actual close): +19.04%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
