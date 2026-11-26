# Kronos-small forecast — NVDA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-02 to 2026-05-15 — 1853 sessions
- As-of cutoff: 2026-05-15 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1853 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 225.32000732421875 on 2026-05-15
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-05-17: 220.965
- 2026-05-18: 218.0677
- 2026-05-19: 215.5433
- 2026-05-20: 213.0066
- 2026-05-21: 210.7416
- 2026-05-24: 208.2912
- 2026-05-25: 205.9166
- 2026-05-26: 205.7163
- 2026-05-27: 205.2054
- 2026-05-28: 201.7675
- 2026-05-31: 200.8902
- 2026-06-01: 200.7424
- 2026-06-02: 199.0387
- 2026-06-03: 198.3306
- 2026-06-04: 199.6937
- 2026-06-07: 198.8615
- 2026-06-08: 193.0182
- 2026-06-09: 192.5515
- 2026-06-10: 194.133
- 2026-06-11: 189.6882
- 2026-06-14: 188.0007

**Change over the 21 sessions (last forecasted close vs last actual close): -16.56%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
