# Kronos-small forecast — SWDY.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2024-01-31 — 1252 sessions
- As-of cutoff: 2024-01-31 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1252 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 32.20000076293945 on 2024-01-31
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2024-02-01: 31.4587
- 2024-02-04: 31.1256
- 2024-02-05: 30.6583
- 2024-02-06: 30.0095
- 2024-02-07: 28.7481
- 2024-02-08: 28.1975
- 2024-02-11: 26.1862
- 2024-02-12: 25.8459
- 2024-02-13: 25.8648
- 2024-02-14: 24.9262
- 2024-02-15: 24.4526
- 2024-02-18: 24.3244
- 2024-02-19: 23.7055
- 2024-02-20: 23.4003
- 2024-02-21: 23.5092
- 2024-02-22: 22.9767
- 2024-02-25: 22.2587
- 2024-02-26: 21.5967
- 2024-02-27: 20.9712
- 2024-02-28: 20.6495
- 2024-02-29: 20.2523

**Change over the 21 sessions (last forecasted close vs last actual close): -37.10%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
