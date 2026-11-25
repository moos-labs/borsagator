# Kronos-small forecast — NVDA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-02 to 2025-03-31 — 1570 sessions
- As-of cutoff: 2025-03-31 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1570 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 108.37999725341797 on 2025-03-31
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2025-04-01: 113.8121
- 2025-04-02: 114.8188
- 2025-04-03: 118.5699
- 2025-04-06: 121.2913
- 2025-04-07: 123.208
- 2025-04-08: 124.3151
- 2025-04-09: 126.1916
- 2025-04-10: 127.1462
- 2025-04-13: 125.6237
- 2025-04-14: 126.5298
- 2025-04-15: 126.1327
- 2025-04-16: 126.0422
- 2025-04-17: 127.0625
- 2025-04-20: 125.6968
- 2025-04-21: 126.4185
- 2025-04-22: 124.4189
- 2025-04-23: 126.0702
- 2025-04-24: 126.7584
- 2025-04-27: 128.3557
- 2025-04-28: 127.803
- 2025-04-29: 128.2775

**Change over the 21 sessions (last forecasted close vs last actual close): +18.36%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
