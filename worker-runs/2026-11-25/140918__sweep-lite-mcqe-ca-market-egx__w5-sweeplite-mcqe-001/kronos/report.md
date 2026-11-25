# Kronos-small forecast — MCQE.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2026-09-28 to 2026-11-23 — 39 sessions
- Context supplied to Kronos: 39 sessions, no truncation needed (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2026-09-28) was accepted; no fallback needed.
- Last actual close: 175.97000122070312 on 2026-11-23
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-11-24: 175.9316
- 2026-11-25: 177.4073
- 2026-11-26: 176.6281
- 2026-11-29: 176.5109
- 2026-11-30: 175.3394
- 2026-12-01: 174.7911
- 2026-12-02: 174.1065
- 2026-12-03: 173.3029
- 2026-12-06: 175.3802
- 2026-12-07: 176.278
- 2026-12-08: 175.4835
- 2026-12-09: 174.4444
- 2026-12-10: 175.4248
- 2026-12-13: 175.2744
- 2026-12-14: 175.9485
- 2026-12-15: 172.4952
- 2026-12-16: 172.7054
- 2026-12-17: 172.4633
- 2026-12-20: 170.1692
- 2026-12-21: 168.9292
- 2026-12-22: 169.0974

**Change over the 21 sessions (last forecasted close vs last actual close): -3.91%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
