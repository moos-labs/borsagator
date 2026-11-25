# 🐊 Borsagator digest — walkforward-backtest

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 75.06999969482422 (pandas-ta/indicators.csv, 2025-06-30). Daily volatility σ 1.79% (pandas-ta/indicators.csv (σ60=0.0176, σ10=0.0179)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.65/day). News risk: **none** — 2-family backtest: news risk overlay disabled (issue #436).
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (base-v1): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | +0.75% | -1.89% … +3.38% | 0.55 |
| week (≈3 sessions) | ⬆ up | +2.04% | -2.63% … +6.71% | 0.53 |
| month (≈14 sessions) | ⬆ up | +6.50% | -3.79% … +16.80% | 0.51 |

Family scores (−1…+1): technicals -0.30, sentiment —, agent —, fundamentals —, price-forecast +0.64.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.
