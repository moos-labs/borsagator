# Kronos-small forecast — COMI.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2026-03-31 — 1772 sessions
- As-of cutoff: 2026-03-31 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1772 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 121.0 on 2026-03-31
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-04-01: 121.576
- 2026-04-02: 120.7223
- 2026-04-05: 120.4088
- 2026-04-06: 120.5217
- 2026-04-07: 121.5656
- 2026-04-08: 122.9132
- 2026-04-09: 122.6711
- 2026-04-12: 122.0055
- 2026-04-13: 123.1289
- 2026-04-14: 122.4445
- 2026-04-15: 121.8759
- 2026-04-16: 121.8287
- 2026-04-19: 118.0177
- 2026-04-20: 119.0811
- 2026-04-21: 116.3929
- 2026-04-22: 116.1505
- 2026-04-23: 114.3195
- 2026-04-26: 112.1838
- 2026-04-27: 112.1196
- 2026-04-28: 108.62
- 2026-04-29: 108.3459

**Change over the 21 sessions (last forecasted close vs last actual close): -10.46%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
