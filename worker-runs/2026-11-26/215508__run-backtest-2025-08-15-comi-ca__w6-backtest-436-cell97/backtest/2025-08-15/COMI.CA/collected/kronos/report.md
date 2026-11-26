# Kronos-small forecast — COMI.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2025-08-14 — 1617 sessions
- As-of cutoff: 2025-08-15 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1617 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 98.30000305175781 on 2025-08-14
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2025-08-17: 97.2896
- 2025-08-18: 96.9109
- 2025-08-19: 96.236
- 2025-08-20: 96.0093
- 2025-08-21: 95.4135
- 2025-08-24: 95.2932
- 2025-08-25: 96.1178
- 2025-08-26: 95.6808
- 2025-08-27: 94.6779
- 2025-08-28: 93.0782
- 2025-08-31: 92.2258
- 2025-09-01: 91.5712
- 2025-09-02: 91.2596
- 2025-09-03: 91.0257
- 2025-09-04: 90.3525
- 2025-09-07: 88.8799
- 2025-09-08: 88.9209
- 2025-09-09: 87.9451
- 2025-09-10: 88.2081
- 2025-09-11: 87.9877
- 2025-09-14: 86.9162

**Change over the 21 sessions (last forecasted close vs last actual close): -11.58%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
