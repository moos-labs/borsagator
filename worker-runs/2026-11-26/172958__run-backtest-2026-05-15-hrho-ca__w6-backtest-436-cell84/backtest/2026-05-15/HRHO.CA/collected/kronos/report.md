# Kronos-small forecast — HRHO.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2026-05-14 — 1801 sessions
- As-of cutoff: 2026-05-15 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1801 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 28.559999465942383 on 2026-05-14
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-05-17: 28.8062
- 2026-05-18: 28.7593
- 2026-05-19: 28.868
- 2026-05-20: 29.0135
- 2026-05-21: 28.9738
- 2026-05-24: 29.0711
- 2026-05-25: 28.9868
- 2026-05-26: 29.0389
- 2026-05-27: 28.8924
- 2026-05-28: 28.8684
- 2026-05-31: 28.8923
- 2026-06-01: 29.2076
- 2026-06-02: 29.2057
- 2026-06-03: 29.0442
- 2026-06-04: 29.0239
- 2026-06-07: 28.9596
- 2026-06-08: 28.8535
- 2026-06-09: 28.9293
- 2026-06-10: 28.9791
- 2026-06-11: 28.676
- 2026-06-14: 28.8252

**Change over the 21 sessions (last forecasted close vs last actual close): +0.93%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
