# Kronos-small forecast — TMGH.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2026-09-30 — 1892 sessions
- As-of cutoff: 2026-09-30 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1892 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 86.9800033569336 on 2026-09-30
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-10-01: 87.7881
- 2026-10-04: 88.6961
- 2026-10-05: 89.5949
- 2026-10-06: 91.1728
- 2026-10-07: 92.4241
- 2026-10-08: 93.4381
- 2026-10-11: 94.7219
- 2026-10-12: 96.4555
- 2026-10-13: 97.6145
- 2026-10-14: 102.8358
- 2026-10-15: 106.4143
- 2026-10-18: 106.0896
- 2026-10-19: 107.8844
- 2026-10-20: 113.7756
- 2026-10-21: 111.5303
- 2026-10-22: 108.8992
- 2026-10-25: 101.3806
- 2026-10-26: 101.4067
- 2026-10-27: 99.0548
- 2026-10-28: 97.8466
- 2026-10-29: 95.0396

**Change over the 21 sessions (last forecasted close vs last actual close): +9.27%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
