# 🐊 Borsagator digest — walkforward-backtest

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 53.099998474121094 (pandas-ta/indicators.csv, 2025-03-27). Daily volatility σ 1.88% (pandas-ta/indicators.csv (σ60=0.0188, σ10=0.0077)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.66/day). News risk: **none** — 2-family backtest: news risk overlay disabled (issue #436).
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (base-v1): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ⬇ down | -0.83% | -3.50% … +1.84% | 0.60 |
| week (≈3 sessions) | ⬆ up | +6.05% | +0.47% … +11.63% | 0.38 |
| month (≈14 sessions) | ⬆ up | +13.18% | +1.37% … +24.99% | 0.41 |

Family scores (−1…+1): technicals -0.45, sentiment —, agent —, fundamentals —, price-forecast +1.00.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.
