# Kronos-small forecast — TMGH.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2026-06-30 — 1829 sessions
- As-of cutoff: 2026-06-30 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1829 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 94.48999786376953 on 2026-06-30
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-07-01: 95.6309
- 2026-07-02: 95.9836
- 2026-07-05: 97.3926
- 2026-07-06: 98.8749
- 2026-07-07: 99.3679
- 2026-07-08: 100.6668
- 2026-07-09: 100.9091
- 2026-07-12: 99.7218
- 2026-07-13: 100.7928
- 2026-07-14: 99.9312
- 2026-07-15: 97.9537
- 2026-07-16: 94.4258
- 2026-07-19: 91.0251
- 2026-07-20: 88.3983
- 2026-07-21: 84.0456
- 2026-07-22: 82.7124
- 2026-07-23: 76.6782
- 2026-07-26: 75.0166
- 2026-07-27: 71.4185
- 2026-07-28: 69.9368
- 2026-07-29: 68.7515

**Change over the 21 sessions (last forecasted close vs last actual close): -27.24%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
