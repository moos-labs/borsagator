# Kronos-small forecast — COMI.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2026-05-14 — 1801 sessions
- As-of cutoff: 2026-05-15 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1801 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 134.50999450683594 on 2026-05-14
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-05-17: 131.3783
- 2026-05-18: 130.4658
- 2026-05-19: 129.0072
- 2026-05-20: 126.2305
- 2026-05-21: 124.1863
- 2026-05-24: 121.7841
- 2026-05-25: 120.1732
- 2026-05-26: 117.2535
- 2026-05-27: 114.389
- 2026-05-28: 111.3778
- 2026-05-31: 112.7085
- 2026-06-01: 109.7475
- 2026-06-02: 110.0171
- 2026-06-03: 110.0815
- 2026-06-04: 109.7532
- 2026-06-07: 107.5894
- 2026-06-08: 108.2977
- 2026-06-09: 108.6653
- 2026-06-10: 107.166
- 2026-06-11: 106.6845
- 2026-06-14: 108.0177

**Change over the 21 sessions (last forecasted close vs last actual close): -19.70%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
