# Kronos-small forecast — SAUD.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2026-09-28 to 2026-11-23 — 39 sessions
- Context supplied to Kronos: 39 sessions, no truncation needed (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2026-09-28) was accepted; no fallback needed.
- Last actual close: 22.6299991607666 on 2026-11-23
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-11-24: 22.6954
- 2026-11-25: 22.691
- 2026-11-26: 22.5323
- 2026-11-29: 22.5413
- 2026-11-30: 22.4624
- 2026-12-01: 22.4828
- 2026-12-02: 22.5603
- 2026-12-03: 22.6393
- 2026-12-06: 22.5789
- 2026-12-07: 22.4943
- 2026-12-08: 22.3907
- 2026-12-09: 22.3179
- 2026-12-10: 22.1486
- 2026-12-13: 22.1948
- 2026-12-14: 22.3061
- 2026-12-15: 22.029
- 2026-12-16: 21.9898
- 2026-12-17: 21.8379
- 2026-12-20: 21.8222
- 2026-12-21: 21.3954
- 2026-12-22: 21.6369

**Change over the 21 sessions (last forecasted close vs last actual close): -4.39%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
