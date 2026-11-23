# 🐊 Borsagator digest — walkforward-backtest

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 23.850000381469727 (pandas-ta/indicators.csv, 2023-12-28). Daily volatility σ 4.72% (pandas-ta/indicators.csv (σ60=0.0472, σ10=0.0288)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.67/day). News risk: **none** — 2-family backtest: news risk overlay disabled (issue #436).
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (base-v1): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ⬇ down | -7.23% | -14.51% … +0.06% | 0.50 |
| week (≈3 sessions) | ⬇ down | -17.33% | -29.88% … -4.78% | 0.51 |
| month (≈14 sessions) | ⬇ down | -42.23% | -68.98% … -15.48% | 0.52 |

Family scores (−1…+1): technicals -0.15, sentiment —, agent —, fundamentals —, price-forecast -1.00.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.
