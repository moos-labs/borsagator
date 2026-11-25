# 🐊 Borsagator digest — walkforward-backtest

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 38.0 (pandas-ta/indicators.csv, 2025-06-30). Daily volatility σ 1.51% (pandas-ta/indicators.csv (σ60=0.0151, σ10=0.0129)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.65/day). News risk: **none** — 2-family backtest: news risk overlay disabled (issue #436).
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (base-v1): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | +0.29% | -1.68% … +2.27% | 0.60 |
| week (≈3 sessions) | ➡ flat | +0.06% | -3.45% … +3.56% | 0.60 |
| month (≈14 sessions) | ⬇ down | -5.45% | -13.96% … +3.06% | 0.53 |

Family scores (−1…+1): technicals +0.20, sentiment —, agent —, fundamentals —, price-forecast -0.63.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.
