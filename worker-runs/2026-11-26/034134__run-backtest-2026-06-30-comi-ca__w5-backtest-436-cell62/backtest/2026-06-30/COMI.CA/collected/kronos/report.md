# Kronos-small forecast — COMI.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2026-06-30 — 1829 sessions
- As-of cutoff: 2026-06-30 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1829 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 127.5 on 2026-06-30
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-07-01: 128.5195
- 2026-07-02: 128.5207
- 2026-07-05: 128.6548
- 2026-07-06: 129.642
- 2026-07-07: 131.1234
- 2026-07-08: 130.4296
- 2026-07-09: 129.8091
- 2026-07-12: 130.2563
- 2026-07-13: 131.045
- 2026-07-14: 130.2942
- 2026-07-15: 131.1107
- 2026-07-16: 129.6761
- 2026-07-19: 126.6547
- 2026-07-20: 124.728
- 2026-07-21: 124.496
- 2026-07-22: 124.867
- 2026-07-23: 124.5305
- 2026-07-26: 121.938
- 2026-07-27: 121.0225
- 2026-07-28: 121.0049
- 2026-07-29: 118.2883

**Change over the 21 sessions (last forecasted close vs last actual close): -7.22%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
