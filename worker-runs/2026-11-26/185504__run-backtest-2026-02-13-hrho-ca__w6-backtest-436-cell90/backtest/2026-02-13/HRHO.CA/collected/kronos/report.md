# Kronos-small forecast — HRHO.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2026-02-12 — 1742 sessions
- As-of cutoff: 2026-02-13 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1742 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 30.100000381469727 on 2026-02-12
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-02-15: 29.8698
- 2026-02-16: 29.545
- 2026-02-17: 29.4823
- 2026-02-18: 29.7508
- 2026-02-19: 29.6617
- 2026-02-22: 29.3703
- 2026-02-23: 29.1194
- 2026-02-24: 29.2491
- 2026-02-25: 29.2037
- 2026-02-26: 28.7276
- 2026-03-01: 28.9621
- 2026-03-02: 28.8831
- 2026-03-03: 28.476
- 2026-03-04: 27.9721
- 2026-03-05: 28.2809
- 2026-03-08: 28.1207
- 2026-03-09: 28.1873
- 2026-03-10: 28.2763
- 2026-03-11: 28.1243
- 2026-03-12: 27.7998
- 2026-03-15: 28.0986

**Change over the 21 sessions (last forecasted close vs last actual close): -6.65%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
