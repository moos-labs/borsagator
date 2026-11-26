# Kronos-small forecast — HRHO.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2025-11-13 — 1680 sessions
- As-of cutoff: 2025-11-14 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1680 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 27.989999771118164 on 2025-11-13
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2025-11-16: 27.9246
- 2025-11-17: 27.8545
- 2025-11-18: 27.8416
- 2025-11-19: 27.7286
- 2025-11-20: 28.2141
- 2025-11-23: 28.0263
- 2025-11-24: 27.9974
- 2025-11-25: 28.2926
- 2025-11-26: 28.259
- 2025-11-27: 28.4899
- 2025-11-30: 28.5039
- 2025-12-01: 28.8139
- 2025-12-02: 28.2897
- 2025-12-03: 28.1736
- 2025-12-04: 28.0945
- 2025-12-07: 28.2712
- 2025-12-08: 28.3028
- 2025-12-09: 28.4451
- 2025-12-10: 28.3623
- 2025-12-11: 27.842
- 2025-12-14: 27.9309

**Change over the 21 sessions (last forecasted close vs last actual close): -0.21%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
