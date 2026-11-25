# Kronos-small forecast — TMGH.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2025-09-30 — 1649 sessions
- As-of cutoff: 2025-09-30 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1649 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 56.880001068115234 on 2025-09-30
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2025-10-01: 55.4959
- 2025-10-02: 55.476
- 2025-10-05: 55.4566
- 2025-10-06: 55.0745
- 2025-10-07: 54.9566
- 2025-10-08: 55.2474
- 2025-10-09: 55.1978
- 2025-10-12: 55.2745
- 2025-10-13: 55.3157
- 2025-10-14: 55.263
- 2025-10-15: 55.576
- 2025-10-16: 55.1703
- 2025-10-19: 55.4115
- 2025-10-20: 55.2378
- 2025-10-21: 55.0068
- 2025-10-22: 54.6151
- 2025-10-23: 54.6507
- 2025-10-26: 55.2522
- 2025-10-27: 55.3245
- 2025-10-28: 56.0483
- 2025-10-29: 55.5847

**Change over the 21 sessions (last forecasted close vs last actual close): -2.28%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
