# 🐊 Borsagator digest — walkforward-backtest

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 24.920000076293945 (pandas-ta/indicators.csv, 2025-12-31). Daily volatility σ 1.44% (pandas-ta/indicators.csv (σ60=0.0144, σ10=0.0071)). Kronos forecast rows are trading sessions — horizons read the row at the ledger's session count directly (price-series density 0.67/day). News risk: **none** — 2-family backtest: news risk overlay disabled (issue #436).
Ranges are the calibrated range (issue #594): centre 0, half-width k × σ60 × √(ledger sessions), k = 1.15 / 1.28 / 1.20. The risk overlay widens the range only (multiplier untested). Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (base-v1): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | +0.00% | -1.65% … +1.65% | 0.60 |
| week | ➡ flat | +0.00% | -4.11% … +4.11% | 0.60 |
| month | ➡ flat | +0.00% | -7.90% … +7.90% | 0.60 |

Family scores (−1…+1): technicals +0.40, sentiment —, agent —, fundamentals —, price-forecast +0.71.
Headline is the centre-0 range; family tilts are shadow challengers (tilt_centre_pct in ensemble.json), adopted only if they pass the RangeSkill gate (#594).
