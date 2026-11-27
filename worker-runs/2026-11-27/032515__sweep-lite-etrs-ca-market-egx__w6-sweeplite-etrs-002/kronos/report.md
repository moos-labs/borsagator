# Kronos-small forecast — ETRS.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2026-09-28 to 2026-11-24 — 40 sessions
- Context supplied to Kronos: 40 sessions, no truncation needed (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2026-09-28) was accepted; no fallback needed.
- Last actual close: 11.050000190734863 on 2026-11-24
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-11-25: 11.1729
- 2026-11-26: 11.1574
- 2026-11-29: 11.0719
- 2026-11-30: 11.0357
- 2026-12-01: 11.0311
- 2026-12-02: 10.9644
- 2026-12-03: 10.9201
- 2026-12-06: 10.8883
- 2026-12-07: 10.9201
- 2026-12-08: 10.8699
- 2026-12-09: 10.7804
- 2026-12-10: 10.8836
- 2026-12-13: 10.8487
- 2026-12-14: 10.7836
- 2026-12-15: 10.7458
- 2026-12-16: 10.7355
- 2026-12-17: 10.7398
- 2026-12-20: 10.6794
- 2026-12-21: 10.6754
- 2026-12-22: 10.6721
- 2026-12-23: 10.6145

**Change over the 21 sessions (last forecasted close vs last actual close): -3.94%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
