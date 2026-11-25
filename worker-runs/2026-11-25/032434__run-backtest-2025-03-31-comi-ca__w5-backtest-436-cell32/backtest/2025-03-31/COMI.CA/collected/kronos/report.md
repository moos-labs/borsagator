# Kronos-small forecast — COMI.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2025-03-27 — 1532 sessions
- As-of cutoff: 2025-03-31 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1532 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 82.44999694824219 on 2025-03-27
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2025-03-30: 82.1491
- 2025-03-31: 82.8574
- 2025-04-01: 83.1073
- 2025-04-02: 83.4867
- 2025-04-03: 83.6342
- 2025-04-06: 83.9416
- 2025-04-07: 84.0222
- 2025-04-08: 83.3828
- 2025-04-09: 83.299
- 2025-04-10: 83.0
- 2025-04-13: 83.0518
- 2025-04-14: 82.7466
- 2025-04-15: 82.7789
- 2025-04-16: 82.763
- 2025-04-17: 82.3518
- 2025-04-20: 82.7998
- 2025-04-21: 83.1618
- 2025-04-22: 83.5263
- 2025-04-23: 84.1839
- 2025-04-24: 83.4677
- 2025-04-27: 82.9839

**Change over the 21 sessions (last forecasted close vs last actual close): +0.65%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
