# Kronos-small forecast — SWDY.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2025-03-27 — 1532 sessions
- As-of cutoff: 2025-03-31 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1532 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 81.5 on 2025-03-27
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2025-03-30: 80.9989
- 2025-03-31: 80.3839
- 2025-04-01: 79.3491
- 2025-04-02: 79.6785
- 2025-04-03: 81.5212
- 2025-04-06: 81.3239
- 2025-04-07: 79.8599
- 2025-04-08: 80.0944
- 2025-04-09: 80.1399
- 2025-04-10: 81.0101
- 2025-04-13: 78.698
- 2025-04-14: 80.0922
- 2025-04-15: 79.1705
- 2025-04-16: 77.3363
- 2025-04-17: 77.3901
- 2025-04-20: 79.0935
- 2025-04-21: 78.4437
- 2025-04-22: 78.1935
- 2025-04-23: 77.5312
- 2025-04-24: 75.0762
- 2025-04-27: 77.9751

**Change over the 21 sessions (last forecasted close vs last actual close): -4.33%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
