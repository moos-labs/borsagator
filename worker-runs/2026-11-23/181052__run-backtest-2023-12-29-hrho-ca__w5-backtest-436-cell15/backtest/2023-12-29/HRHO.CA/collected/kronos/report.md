# Kronos-small forecast — HRHO.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, sample_count=1)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2023-12-28 — 1231 sessions
- As-of cutoff: 2023-12-29 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1231 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 16.670000076293945 on 2023-12-28
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2023-12-31: 17.1806
- 2024-01-01: 17.207
- 2024-01-02: 16.9613
- 2024-01-03: 17.1381
- 2024-01-04: 17.559
- 2024-01-07: 17.4947
- 2024-01-08: 17.0187
- 2024-01-09: 16.8968
- 2024-01-10: 16.6036
- 2024-01-11: 16.5078
- 2024-01-14: 15.6442
- 2024-01-15: 15.0294
- 2024-01-16: 15.1759
- 2024-01-17: 15.7995
- 2024-01-18: 16.1435
- 2024-01-21: 16.4131
- 2024-01-22: 16.4579
- 2024-01-23: 16.2695
- 2024-01-24: 16.0915
- 2024-01-25: 16.5731
- 2024-01-28: 17.1746

**Change over the 21 sessions (last forecasted close vs last actual close): +3.03%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
