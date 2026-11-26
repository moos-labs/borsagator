# Kronos-small forecast — COMI.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2026-09-30 — 1892 sessions
- As-of cutoff: 2026-09-30 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1892 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 126.30000305175781 on 2026-09-30
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-10-01: 125.5671
- 2026-10-04: 127.0311
- 2026-10-05: 129.5724
- 2026-10-06: 129.167
- 2026-10-07: 130.6245
- 2026-10-08: 132.065
- 2026-10-11: 132.1839
- 2026-10-12: 132.4074
- 2026-10-13: 133.257
- 2026-10-14: 133.603
- 2026-10-15: 134.9546
- 2026-10-18: 134.1271
- 2026-10-19: 133.8328
- 2026-10-20: 133.1799
- 2026-10-21: 133.3271
- 2026-10-22: 133.3701
- 2026-10-25: 134.2994
- 2026-10-26: 134.2684
- 2026-10-27: 134.1566
- 2026-10-28: 134.2056
- 2026-10-29: 134.8598

**Change over the 21 sessions (last forecasted close vs last actual close): +6.78%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
