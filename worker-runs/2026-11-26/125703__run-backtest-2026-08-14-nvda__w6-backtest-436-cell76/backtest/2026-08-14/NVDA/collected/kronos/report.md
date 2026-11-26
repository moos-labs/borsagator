# Kronos-small forecast — NVDA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-02 to 2026-08-14 — 1915 sessions
- As-of cutoff: 2026-08-14 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1915 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 225.16000366210938 on 2026-08-14
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-08-16: 228.9676
- 2026-08-17: 227.4513
- 2026-08-18: 229.1075
- 2026-08-19: 228.1033
- 2026-08-20: 225.07
- 2026-08-23: 224.6362
- 2026-08-24: 224.1154
- 2026-08-25: 224.8233
- 2026-08-26: 221.3182
- 2026-08-27: 219.2426
- 2026-08-30: 215.6019
- 2026-08-31: 218.8014
- 2026-09-01: 215.309
- 2026-09-02: 214.9761
- 2026-09-03: 214.1512
- 2026-09-06: 210.8923
- 2026-09-07: 207.7645
- 2026-09-08: 207.775
- 2026-09-09: 206.4904
- 2026-09-10: 203.2354
- 2026-09-13: 202.048

**Change over the 21 sessions (last forecasted close vs last actual close): -10.26%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
