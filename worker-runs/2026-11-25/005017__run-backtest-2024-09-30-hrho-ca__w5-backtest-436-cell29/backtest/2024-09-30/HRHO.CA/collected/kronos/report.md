# Kronos-small forecast — HRHO.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2024-09-30 — 1407 sessions
- As-of cutoff: 2024-09-30 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1407 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 24.450000762939453 on 2024-09-30
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2024-10-01: 23.7337
- 2024-10-02: 23.4064
- 2024-10-03: 22.6746
- 2024-10-06: 22.197
- 2024-10-07: 21.7967
- 2024-10-08: 21.2784
- 2024-10-09: 20.9823
- 2024-10-10: 20.609
- 2024-10-13: 20.447
- 2024-10-14: 20.1694
- 2024-10-15: 20.2211
- 2024-10-16: 19.7642
- 2024-10-17: 19.7952
- 2024-10-20: 19.5487
- 2024-10-21: 19.3603
- 2024-10-22: 19.4355
- 2024-10-23: 19.4825
- 2024-10-24: 19.4335
- 2024-10-27: 19.3496
- 2024-10-28: 19.5953
- 2024-10-29: 19.6064

**Change over the 21 sessions (last forecasted close vs last actual close): -19.81%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
