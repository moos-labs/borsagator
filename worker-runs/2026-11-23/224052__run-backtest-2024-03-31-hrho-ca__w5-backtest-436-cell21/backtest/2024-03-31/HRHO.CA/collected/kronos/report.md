# Kronos-small forecast — HRHO.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, sample_count=1)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2024-03-31 — 1294 sessions
- As-of cutoff: 2024-03-31 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1294 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 17.350000381469727 on 2024-03-31
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2024-04-01: 17.6405
- 2024-04-02: 17.9879
- 2024-04-03: 18.0317
- 2024-04-04: 18.3555
- 2024-04-07: 18.9985
- 2024-04-08: 18.9644
- 2024-04-09: 18.46
- 2024-04-10: 18.332
- 2024-04-11: 18.0305
- 2024-04-14: 17.638
- 2024-04-15: 16.945
- 2024-04-16: 16.2642
- 2024-04-17: 15.9617
- 2024-04-18: 15.381
- 2024-04-21: 16.0027
- 2024-04-22: 16.933
- 2024-04-23: 17.3257
- 2024-04-24: 16.7335
- 2024-04-25: 16.7008
- 2024-04-28: 17.6381
- 2024-04-29: 18.4189

**Change over the 21 sessions (last forecasted close vs last actual close): +6.16%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
