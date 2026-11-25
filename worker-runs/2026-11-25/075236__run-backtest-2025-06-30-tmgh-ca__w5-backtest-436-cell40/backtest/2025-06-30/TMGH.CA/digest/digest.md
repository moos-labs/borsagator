# 🐊 Borsagator digest — walkforward-backtest

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 55.54999923706055 (pandas-ta/indicators.csv, 2025-06-30). Daily volatility σ 2.68% (pandas-ta/indicators.csv (σ60=0.0198, σ10=0.0268)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.65/day). News risk: **none** — 2-family backtest: news risk overlay disabled (issue #436).
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (base-v1): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ⬆ up | +0.96% | -2.69% … +4.62% | 0.60 |
| week (≈3 sessions) | ⬆ up | +2.97% | -3.08% … +9.03% | 0.60 |
| month (≈14 sessions) | ⬆ up | +9.04% | -4.02% … +22.09% | 0.60 |

Family scores (−1…+1): technicals +0.45, sentiment —, agent —, fundamentals —, price-forecast +0.53.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.
