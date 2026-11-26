# Kronos-small forecast — NVDA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-02 to 2026-03-31 — 1821 sessions
- As-of cutoff: 2026-03-31 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1821 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 174.39999389648438 on 2026-03-31
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-04-01: 176.7528
- 2026-04-02: 178.5271
- 2026-04-05: 180.7461
- 2026-04-06: 182.0194
- 2026-04-07: 184.6035
- 2026-04-08: 184.3961
- 2026-04-09: 184.5399
- 2026-04-12: 187.3119
- 2026-04-13: 188.2347
- 2026-04-14: 189.573
- 2026-04-15: 190.0161
- 2026-04-16: 190.4133
- 2026-04-19: 191.794
- 2026-04-20: 192.7753
- 2026-04-21: 191.7193
- 2026-04-22: 194.287
- 2026-04-23: 195.7216
- 2026-04-26: 194.247
- 2026-04-27: 195.5366
- 2026-04-28: 195.1421
- 2026-04-29: 192.8925

**Change over the 21 sessions (last forecasted close vs last actual close): +10.60%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
