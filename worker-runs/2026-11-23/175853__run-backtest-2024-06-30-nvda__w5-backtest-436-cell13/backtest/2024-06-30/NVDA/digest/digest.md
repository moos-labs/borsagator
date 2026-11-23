# 🐊 Borsagator digest — walkforward-backtest

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 123.54000091552734 (pandas-ta/indicators.csv, 2024-06-28). Daily volatility σ 3.62% (pandas-ta/indicators.csv (σ60=0.0343, σ10=0.0362)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.69/day). News risk: **none** — 2-family backtest: news risk overlay disabled (issue #436).
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (base-v1): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ⬆ up | +6.60% | +0.29% … +12.91% | 0.42 |
| week (≈3 sessions) | ⬇ down | -30.45% | -39.93% … -20.96% | 0.53 |
| month (≈14 sessions) | ⬇ down | -45.02% | -65.26% … -24.78% | 0.54 |

Family scores (−1…+1): technicals -0.23, sentiment —, agent —, fundamentals —, price-forecast -1.00.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.
