# Kronos-small forecast — OCDI.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2026-09-28 to 2026-11-25 — 41 sessions
- Context supplied to Kronos: 41 sessions, no truncation needed (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2026-09-28) was accepted; no fallback needed.
- Last actual close: 23.600000381469727 on 2026-11-25
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-11-26: 23.2363
- 2026-11-29: 23.2661
- 2026-11-30: 23.2505
- 2026-12-01: 23.6802
- 2026-12-02: 23.7376
- 2026-12-03: 23.8618
- 2026-12-06: 23.869
- 2026-12-07: 23.9846
- 2026-12-08: 24.0801
- 2026-12-09: 24.1505
- 2026-12-10: 24.042
- 2026-12-13: 23.9343
- 2026-12-14: 23.9817
- 2026-12-15: 23.9977
- 2026-12-16: 23.8474
- 2026-12-17: 23.904
- 2026-12-20: 23.9861
- 2026-12-21: 24.1747
- 2026-12-22: 24.2849
- 2026-12-23: 24.4869
- 2026-12-24: 24.3572

**Change over the 21 sessions (last forecasted close vs last actual close): +3.21%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
