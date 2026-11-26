# Kronos-small forecast — ETEL.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2026-09-30 — 1892 sessions
- As-of cutoff: 2026-09-30 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1892 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 134.0 on 2026-09-30
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-10-01: 134.9764
- 2026-10-04: 132.5575
- 2026-10-05: 132.4224
- 2026-10-06: 129.8324
- 2026-10-07: 128.66
- 2026-10-08: 127.3508
- 2026-10-11: 125.057
- 2026-10-12: 121.9071
- 2026-10-13: 118.2815
- 2026-10-14: 120.5127
- 2026-10-15: 115.6906
- 2026-10-18: 111.3915
- 2026-10-19: 105.9801
- 2026-10-20: 99.5757
- 2026-10-21: 100.1385
- 2026-10-22: 98.242
- 2026-10-25: 97.5741
- 2026-10-26: 95.1991
- 2026-10-27: 92.769
- 2026-10-28: 92.3273
- 2026-10-29: 89.3754

**Change over the 21 sessions (last forecasted close vs last actual close): -33.30%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
