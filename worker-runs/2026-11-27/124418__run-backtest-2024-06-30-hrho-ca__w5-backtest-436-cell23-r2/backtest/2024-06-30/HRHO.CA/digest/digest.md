# 🐊 Borsagator digest — walkforward-backtest

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 19.700000762939453 (pandas-ta/indicators.csv, 2024-06-27). Daily volatility σ 2.85% (pandas-ta/indicators.csv (σ60=0.0285, σ10=0.0220)). Kronos forecast rows are trading sessions — horizons read the row at the ledger's session count directly (price-series density 0.65/day). News risk: **none** — 2-family backtest: news risk overlay disabled (issue #436).
Ranges are the calibrated range (issue #594): centre 0, half-width k × σ60 × √(ledger sessions), k = 1.15 / 1.28 / 1.20. The risk overlay widens the range only (multiplier untested). Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (base-v1): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | +0.00% | -3.28% … +3.28% | 0.60 |
| week | ➡ flat | +0.00% | -8.16% … +8.16% | 0.60 |
| month | ➡ flat | +0.00% | -15.69% … +15.69% | 0.60 |

Family scores (−1…+1): technicals -0.10, sentiment —, agent —, fundamentals —, price-forecast -0.40.
Headline is the centre-0 range; family tilts are shadow challengers (tilt_centre_pct in ensemble.json), adopted only if they pass the RangeSkill gate (#594).
