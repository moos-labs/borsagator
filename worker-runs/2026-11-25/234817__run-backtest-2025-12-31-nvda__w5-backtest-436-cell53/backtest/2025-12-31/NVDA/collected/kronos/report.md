# Kronos-small forecast — NVDA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-02 to 2025-12-31 — 1760 sessions
- As-of cutoff: 2025-12-31 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1760 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 186.5 on 2025-12-31
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-01-01: 186.5897
- 2026-01-04: 184.1833
- 2026-01-05: 180.1927
- 2026-01-06: 178.9614
- 2026-01-07: 180.9721
- 2026-01-08: 178.2292
- 2026-01-11: 177.4169
- 2026-01-12: 176.6524
- 2026-01-13: 178.887
- 2026-01-14: 176.5436
- 2026-01-15: 176.425
- 2026-01-18: 176.2533
- 2026-01-19: 176.6738
- 2026-01-20: 173.1642
- 2026-01-21: 176.8402
- 2026-01-22: 172.798
- 2026-01-25: 174.6145
- 2026-01-26: 172.6725
- 2026-01-27: 177.9965
- 2026-01-28: 174.826
- 2026-01-29: 178.7572

**Change over the 21 sessions (last forecasted close vs last actual close): -4.15%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
