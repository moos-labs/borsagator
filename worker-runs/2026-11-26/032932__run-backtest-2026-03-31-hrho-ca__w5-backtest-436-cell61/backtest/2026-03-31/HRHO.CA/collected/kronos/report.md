# Kronos-small forecast — HRHO.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2019-01-01 to 2026-03-31 — 1772 sessions
- As-of cutoff: 2026-03-31 (walk-forward backtest, borsagator #436 — every session after the cutoff was dropped before the model ran; context ends at the cutoff)
- Context supplied to Kronos: 1772 sessions, truncated to the last 512 before predict() (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2019-01-01) was accepted; no fallback needed.
- Last actual close: 25.15999984741211 on 2026-03-31
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-04-01: 25.235
- 2026-04-02: 25.4323
- 2026-04-05: 25.6741
- 2026-04-06: 25.507
- 2026-04-07: 25.6302
- 2026-04-08: 25.9554
- 2026-04-09: 26.4604
- 2026-04-12: 26.5646
- 2026-04-13: 26.3518
- 2026-04-14: 26.7451
- 2026-04-15: 26.9081
- 2026-04-16: 26.7627
- 2026-04-19: 26.9866
- 2026-04-20: 27.3059
- 2026-04-21: 27.2672
- 2026-04-22: 27.164
- 2026-04-23: 27.398
- 2026-04-26: 27.5949
- 2026-04-27: 27.7087
- 2026-04-28: 27.7829
- 2026-04-29: 27.564

**Change over the 21 sessions (last forecasted close vs last actual close): +9.55%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.
