# 🐊 Borsagator digest — walkforward-backtest

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 20.700000762939453 (pandas-ta/indicators.csv, 2024-12-31). Daily volatility σ 1.87% (pandas-ta/indicators.csv (σ60=0.0185, σ10=0.0187)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.66/day). News risk: **none** — 2-family backtest: news risk overlay disabled (issue #436).
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (base-v1): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ⬇ down | -0.79% | -3.32% … +1.74% | 0.60 |
| week (≈3 sessions) | ⬆ up | +2.37% | -2.73% … +7.47% | 0.48 |
| month (≈14 sessions) | ⬆ up | +7.06% | -4.07% … +18.19% | 0.47 |

Family scores (−1…+1): technicals -0.45, sentiment —, agent —, fundamentals —, price-forecast +0.67.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.
