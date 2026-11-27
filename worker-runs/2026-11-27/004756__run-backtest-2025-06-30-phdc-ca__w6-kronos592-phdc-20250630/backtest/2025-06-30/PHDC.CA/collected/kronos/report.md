# Kronos-small forecast — PHDC.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2025-06-30 — 1587 sessions
- As-of cutoff: 2025-06-30 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1587 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 9.0 on 2025-06-30
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2025-07-01: 8.6437
- 2025-07-02: 8.3694
- 2025-07-03: 7.918
- 2025-07-06: 7.6307
- 2025-07-07: 7.5175
- 2025-07-08: 7.1913
- 2025-07-09: 7.0382
- 2025-07-10: 6.8987
- 2025-07-13: 6.8529
- 2025-07-14: 6.7011
- 2025-07-15: 6.6784
- 2025-07-16: 6.5166
- 2025-07-17: 6.4102
- 2025-07-20: 6.1575
- 2025-07-21: 6.1564
- 2025-07-22: 6.2495
- 2025-07-23: 6.0896
- 2025-07-24: 5.9995
- 2025-07-27: 6.0062
- 2025-07-28: 6.0143
- 2025-07-29: 6.0037

**Change over the 21 sessions (last forecasted close vs last actual close): -33.29%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
