# Kronos-small forecast — NVDA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-02 to 2026-09-30 — 1947 sessions
- As-of cutoff: 2026-09-30 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1947 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 228.3800048828125 on 2026-09-30
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-10-01: 228.4148
- 2026-10-04: 228.1044
- 2026-10-05: 226.2333
- 2026-10-06: 226.1807
- 2026-10-07: 225.7059
- 2026-10-08: 223.1888
- 2026-10-11: 222.4859
- 2026-10-12: 223.1126
- 2026-10-13: 222.4376
- 2026-10-14: 221.7223
- 2026-10-15: 221.8358
- 2026-10-18: 219.6966
- 2026-10-19: 216.5087
- 2026-10-20: 216.3542
- 2026-10-21: 216.2999
- 2026-10-22: 215.2113
- 2026-10-25: 210.8393
- 2026-10-26: 208.9042
- 2026-10-27: 207.7173
- 2026-10-28: 205.5041
- 2026-10-29: 204.305

**Change over the 21 sessions (last forecasted close vs last actual close): -10.54%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
