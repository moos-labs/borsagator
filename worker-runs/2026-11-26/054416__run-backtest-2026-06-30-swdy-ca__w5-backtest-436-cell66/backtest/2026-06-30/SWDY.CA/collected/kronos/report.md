# Kronos-small forecast — SWDY.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2026-06-30 — 1829 sessions
- As-of cutoff: 2026-06-30 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1829 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 86.01000213623047 on 2026-06-30
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-07-01: 86.6479
- 2026-07-02: 86.4846
- 2026-07-05: 86.5816
- 2026-07-06: 86.7639
- 2026-07-07: 86.8829
- 2026-07-08: 86.5143
- 2026-07-09: 86.6157
- 2026-07-12: 86.0256
- 2026-07-13: 85.7367
- 2026-07-14: 84.8146
- 2026-07-15: 87.0136
- 2026-07-16: 86.6305
- 2026-07-19: 85.5194
- 2026-07-20: 84.9912
- 2026-07-21: 83.0376
- 2026-07-22: 82.3438
- 2026-07-23: 80.9265
- 2026-07-26: 78.1194
- 2026-07-27: 80.2634
- 2026-07-28: 78.8407
- 2026-07-29: 79.8546

**Change over the 21 sessions (last forecasted close vs last actual close): -7.16%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
