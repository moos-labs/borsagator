# Kronos-small forecast — COMI.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2025-06-30 — 1587 sessions
- As-of cutoff: 2025-06-30 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1587 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 84.30000305175781 on 2025-06-30
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2025-07-01: 84.435
- 2025-07-02: 84.2418
- 2025-07-03: 84.7418
- 2025-07-06: 84.4279
- 2025-07-07: 84.7902
- 2025-07-08: 84.968
- 2025-07-09: 85.2374
- 2025-07-10: 84.3787
- 2025-07-13: 84.1504
- 2025-07-14: 83.5417
- 2025-07-15: 83.03
- 2025-07-16: 82.4112
- 2025-07-17: 83.1195
- 2025-07-20: 83.1105
- 2025-07-21: 83.3236
- 2025-07-22: 83.3749
- 2025-07-23: 82.4348
- 2025-07-24: 83.0236
- 2025-07-27: 82.0893
- 2025-07-28: 83.5925
- 2025-07-29: 83.1669

**Change over the 21 sessions (last forecasted close vs last actual close): -1.34%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
