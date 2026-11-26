# 🐊 Borsagator digest — walkforward-backtest

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 139.27000427246094 (pandas-ta/indicators.csv, 2026-08-13). Daily volatility σ 1.46% (pandas-ta/indicators.csv (σ60=0.0146, σ10=0.0054)). Kronos forecast rows are trading sessions — horizons read the row at the ledger's session count directly (price-series density 0.67/day). News risk: **none** — 2-family backtest: news risk overlay disabled (issue #436).
Ranges are the calibrated range (issue #594): centre 0, half-width k × σ60 × √(ledger sessions), k = 1.15 / 1.28 / 1.20. The risk overlay widens the range only (multiplier untested). Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (base-v1): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | +0.00% | -1.67% … +1.67% | 0.60 |
| week | ➡ flat | +0.00% | -4.17% … +4.17% | 0.60 |
| month | ➡ flat | +0.00% | -8.00% … +8.00% | 0.60 |

Family scores (−1…+1): technicals -0.15, sentiment —, agent —, fundamentals —, price-forecast -0.69.
Headline is the centre-0 range; family tilts are shadow challengers (tilt_centre_pct in ensemble.json), adopted only if they pass the RangeSkill gate (#594).
