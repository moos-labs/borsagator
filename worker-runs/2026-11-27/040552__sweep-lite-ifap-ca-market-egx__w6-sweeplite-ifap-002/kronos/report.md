# Kronos-small forecast — IFAP.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2026-09-28 to 2026-11-24 — 40 sessions
- Context supplied to Kronos: 40 sessions, no truncation needed (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2026-09-28) was accepted; no fallback needed.
- Last actual close: 15.789999961853027 on 2026-11-24
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-11-25: 15.9947
- 2026-11-26: 16.0002
- 2026-11-29: 15.9592
- 2026-11-30: 15.9925
- 2026-12-01: 16.0619
- 2026-12-02: 16.1117
- 2026-12-03: 16.1148
- 2026-12-06: 16.2329
- 2026-12-07: 16.1417
- 2026-12-08: 16.1789
- 2026-12-09: 16.2548
- 2026-12-10: 16.149
- 2026-12-13: 16.3948
- 2026-12-14: 16.2266
- 2026-12-15: 16.3946
- 2026-12-16: 16.3758
- 2026-12-17: 16.2799
- 2026-12-20: 16.5095
- 2026-12-21: 16.3715
- 2026-12-22: 16.5778
- 2026-12-23: 16.4295

**Change over the 21 sessions (last forecasted close vs last actual close): +4.05%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
