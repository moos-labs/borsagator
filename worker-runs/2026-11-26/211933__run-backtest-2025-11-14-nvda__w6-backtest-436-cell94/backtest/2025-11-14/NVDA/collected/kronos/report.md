# Kronos-small forecast — NVDA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-02 to 2025-11-14 — 1729 sessions
- As-of cutoff: 2025-11-14 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1729 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 190.1699981689453 on 2025-11-14
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2025-11-16: 190.2165
- 2025-11-17: 185.0511
- 2025-11-18: 181.4185
- 2025-11-19: 178.7971
- 2025-11-20: 177.5483
- 2025-11-23: 176.7358
- 2025-11-24: 171.8324
- 2025-11-25: 166.2958
- 2025-11-26: 165.3633
- 2025-11-27: 161.5926
- 2025-11-30: 161.6357
- 2025-12-01: 158.3176
- 2025-12-02: 158.5882
- 2025-12-03: 159.7155
- 2025-12-04: 157.6305
- 2025-12-07: 156.4063
- 2025-12-08: 156.3392
- 2025-12-09: 156.0788
- 2025-12-10: 155.6155
- 2025-12-11: 154.6227
- 2025-12-14: 155.3426

**Change over the 21 sessions (last forecasted close vs last actual close): -18.31%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
