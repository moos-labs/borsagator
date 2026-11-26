# Kronos-small forecast — TMGH.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2026-02-12 — 1742 sessions
- As-of cutoff: 2026-02-13 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1742 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 88.87000274658203 on 2026-02-12
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-02-15: 86.5285
- 2026-02-16: 83.7171
- 2026-02-17: 83.8642
- 2026-02-18: 82.8422
- 2026-02-19: 82.7729
- 2026-02-22: 80.8232
- 2026-02-23: 80.6413
- 2026-02-24: 80.0678
- 2026-02-25: 79.9284
- 2026-02-26: 76.9335
- 2026-03-01: 76.1003
- 2026-03-02: 73.7274
- 2026-03-03: 72.7999
- 2026-03-04: 72.9957
- 2026-03-05: 70.8815
- 2026-03-08: 69.2887
- 2026-03-09: 67.8919
- 2026-03-10: 68.2136
- 2026-03-11: 67.2245
- 2026-03-12: 63.1943
- 2026-03-15: 66.205

**Change over the 21 sessions (last forecasted close vs last actual close): -25.50%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
