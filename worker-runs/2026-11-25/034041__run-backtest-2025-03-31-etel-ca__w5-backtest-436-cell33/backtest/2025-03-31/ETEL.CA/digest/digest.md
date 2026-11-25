# 🐊 Borsagator digest — walkforward-backtest

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 35.29999923706055 (pandas-ta/indicators.csv, 2025-03-27). Daily volatility σ 1.29% (pandas-ta/indicators.csv (σ60=0.0129, σ10=0.0083)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.66/day). News risk: **none** — 2-family backtest: news risk overlay disabled (issue #436).
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (base-v1): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | -0.37% | -2.04% … +1.29% | 0.60 |
| week (≈3 sessions) | ⬆ up | +1.87% | -1.51% … +5.25% | 0.53 |
| month (≈14 sessions) | ⬆ up | +2.07% | -4.77% … +8.91% | 0.60 |

Family scores (−1…+1): technicals -0.20, sentiment —, agent —, fundamentals —, price-forecast +0.29.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.
