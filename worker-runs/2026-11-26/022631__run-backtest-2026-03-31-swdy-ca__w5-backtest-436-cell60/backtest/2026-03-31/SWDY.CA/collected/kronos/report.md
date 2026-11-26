# Kronos-small forecast — SWDY.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2026-03-31 — 1772 sessions
- As-of cutoff: 2026-03-31 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1772 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 78.0 on 2026-03-31
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-04-01: 77.3029
- 2026-04-02: 77.1151
- 2026-04-05: 77.103
- 2026-04-06: 76.7941
- 2026-04-07: 76.9511
- 2026-04-08: 77.3096
- 2026-04-09: 77.2934
- 2026-04-12: 77.2349
- 2026-04-13: 77.2288
- 2026-04-14: 77.5247
- 2026-04-15: 77.4607
- 2026-04-16: 77.3929
- 2026-04-19: 77.7671
- 2026-04-20: 77.344
- 2026-04-21: 77.0709
- 2026-04-22: 76.6889
- 2026-04-23: 76.9205
- 2026-04-26: 76.71
- 2026-04-27: 76.6037
- 2026-04-28: 76.7165
- 2026-04-29: 76.1013

**Change over the 21 sessions (last forecasted close vs last actual close): -2.43%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
