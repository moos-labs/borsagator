# Kronos-small forecast — NVDA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-02 to 2024-05-30 — 1362 sessions
- As-of cutoff: 2024-05-30 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1362 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 110.5 on 2024-05-30
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2024-06-02: 114.0865
- 2024-06-03: 110.3794
- 2024-06-04: 106.3211
- 2024-06-05: 93.2512
- 2024-06-06: 82.823
- 2024-06-09: 69.5632
- 2024-06-10: 65.3566
- 2024-06-11: 61.5678
- 2024-06-12: 60.1638
- 2024-06-13: 54.8401
- 2024-06-16: 54.9833
- 2024-06-17: 52.3431
- 2024-06-18: 48.694
- 2024-06-19: 50.0753
- 2024-06-20: 49.0464
- 2024-06-23: 45.8125
- 2024-06-24: 46.3444
- 2024-06-25: 46.0755
- 2024-06-26: 45.2442
- 2024-06-27: 46.5279
- 2024-06-30: 46.3071

**Change over the 21 sessions (last forecasted close vs last actual close): -58.09%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
