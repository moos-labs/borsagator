# Kronos-small forecast — ORWE.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2025-06-30 — 1587 sessions
- As-of cutoff: 2025-06-30 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1587 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 23.90999984741211 on 2025-06-30
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2025-07-01: 24.1186
- 2025-07-02: 24.2346
- 2025-07-03: 24.3419
- 2025-07-06: 24.5509
- 2025-07-07: 24.6224
- 2025-07-08: 24.6854
- 2025-07-09: 24.7554
- 2025-07-10: 25.0489
- 2025-07-13: 25.137
- 2025-07-14: 24.9296
- 2025-07-15: 24.8302
- 2025-07-16: 24.5734
- 2025-07-17: 24.8681
- 2025-07-20: 24.4545
- 2025-07-21: 24.593
- 2025-07-22: 24.7215
- 2025-07-23: 24.6323
- 2025-07-24: 24.7473
- 2025-07-27: 25.1437
- 2025-07-28: 25.1212
- 2025-07-29: 24.827

**Change over the 21 sessions (last forecasted close vs last actual close): +3.84%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
