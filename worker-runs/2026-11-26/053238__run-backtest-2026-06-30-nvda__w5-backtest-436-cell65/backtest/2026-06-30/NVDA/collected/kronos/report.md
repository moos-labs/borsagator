# Kronos-small forecast — NVDA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-02 to 2026-06-30 — 1883 sessions
- As-of cutoff: 2026-06-30 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1883 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 200.08999633789062 on 2026-06-30
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-07-01: 199.2104
- 2026-07-02: 198.2717
- 2026-07-05: 199.408
- 2026-07-06: 198.9756
- 2026-07-07: 202.0269
- 2026-07-08: 200.3568
- 2026-07-09: 201.6289
- 2026-07-12: 200.3125
- 2026-07-13: 203.0261
- 2026-07-14: 202.8582
- 2026-07-15: 199.8356
- 2026-07-16: 199.2028
- 2026-07-19: 199.481
- 2026-07-20: 200.0594
- 2026-07-21: 201.18
- 2026-07-22: 202.4302
- 2026-07-23: 197.8117
- 2026-07-26: 197.3619
- 2026-07-27: 198.2095
- 2026-07-28: 197.5254
- 2026-07-29: 192.005

**Change over the 21 sessions (last forecasted close vs last actual close): -4.04%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
