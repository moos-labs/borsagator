# 🐊 Borsagator digest — walkforward-backtest

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 35.54999923706055 (pandas-ta/indicators.csv, 2024-03-31). Daily volatility σ 2.54% (pandas-ta/indicators.csv (σ60=0.0254, σ10=0.0204)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.66/day). News risk: **none** — 2-family backtest: news risk overlay disabled (issue #436).
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (base-v1): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | -0.11% | -3.61% … +3.39% | 0.60 |
| week (≈3 sessions) | ⬆ up | +5.05% | -2.01% … +12.10% | 0.46 |
| month (≈14 sessions) | ⬆ up | +3.20% | -10.37% … +16.77% | 0.59 |

Family scores (−1…+1): technicals -0.30, sentiment —, agent —, fundamentals —, price-forecast +0.24.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.
