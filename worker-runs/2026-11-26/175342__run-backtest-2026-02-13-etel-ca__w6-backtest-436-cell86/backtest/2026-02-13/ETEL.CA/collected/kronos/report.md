# Kronos-small forecast — ETEL.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2026-02-12 — 1742 sessions
- As-of cutoff: 2026-02-13 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1742 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 94.94000244140625 on 2026-02-12
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-02-15: 97.5911
- 2026-02-16: 89.8429
- 2026-02-17: 82.4817
- 2026-02-18: 55.4716
- 2026-02-19: 48.4675
- 2026-02-22: 46.6141
- 2026-02-23: 44.4293
- 2026-02-24: 41.1898
- 2026-02-25: 41.2031
- 2026-02-26: 40.786
- 2026-03-01: 39.9905
- 2026-03-02: 39.758
- 2026-03-03: 38.0744
- 2026-03-04: 39.2538
- 2026-03-05: 38.0592
- 2026-03-08: 37.9703
- 2026-03-09: 38.7464
- 2026-03-10: 38.6339
- 2026-03-11: 39.369
- 2026-03-12: 38.2353
- 2026-03-15: 39.0797

**Change over the 21 sessions (last forecasted close vs last actual close): -58.84%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
