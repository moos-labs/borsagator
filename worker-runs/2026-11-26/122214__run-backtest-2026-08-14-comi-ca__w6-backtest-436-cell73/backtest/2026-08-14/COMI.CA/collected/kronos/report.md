# Kronos-small forecast — COMI.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2026-08-13 — 1859 sessions
- As-of cutoff: 2026-08-14 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1859 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 139.27000427246094 on 2026-08-13
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-08-16: 139.8369
- 2026-08-17: 138.9535
- 2026-08-18: 139.3075
- 2026-08-19: 138.6694
- 2026-08-20: 138.1293
- 2026-08-23: 136.4049
- 2026-08-24: 136.0735
- 2026-08-25: 137.5799
- 2026-08-26: 137.398
- 2026-08-27: 137.7332
- 2026-08-30: 135.4986
- 2026-08-31: 135.4261
- 2026-09-01: 133.0783
- 2026-09-02: 132.5942
- 2026-09-03: 130.8266
- 2026-09-06: 130.7265
- 2026-09-07: 130.0759
- 2026-09-08: 130.4621
- 2026-09-09: 129.207
- 2026-09-10: 126.9528
- 2026-09-13: 126.4418

**Change over the 21 sessions (last forecasted close vs last actual close): -9.21%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
