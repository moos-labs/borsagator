# Kronos-small forecast — PHDC.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2026-02-12 — 1742 sessions
- As-of cutoff: 2026-02-13 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1742 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 8.850000381469727 on 2026-02-12
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-02-15: 8.7326
- 2026-02-16: 8.6852
- 2026-02-17: 8.6751
- 2026-02-18: 8.7084
- 2026-02-19: 8.6796
- 2026-02-22: 8.7054
- 2026-02-23: 8.7044
- 2026-02-24: 8.831
- 2026-02-25: 8.7569
- 2026-02-26: 8.7504
- 2026-03-01: 8.7663
- 2026-03-02: 8.8449
- 2026-03-03: 8.7579
- 2026-03-04: 8.7066
- 2026-03-05: 8.702
- 2026-03-08: 8.7561
- 2026-03-09: 8.6883
- 2026-03-10: 8.6966
- 2026-03-11: 8.5684
- 2026-03-12: 8.4602
- 2026-03-15: 8.4026

**Change over the 21 sessions (last forecasted close vs last actual close): -5.06%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
