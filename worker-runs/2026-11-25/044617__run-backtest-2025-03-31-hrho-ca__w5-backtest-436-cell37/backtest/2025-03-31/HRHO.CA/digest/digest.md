# 🐊 Borsagator digest — walkforward-backtest

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 27.5 (pandas-ta/indicators.csv, 2025-03-27). Daily volatility σ 1.84% (pandas-ta/indicators.csv (σ60=0.0184, σ10=0.0120)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.66/day). News risk: **none** — 2-family backtest: news risk overlay disabled (issue #436).
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (base-v1): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ⬇ down | -2.74% | -5.51% … +0.03% | 0.53 |
| week (≈3 sessions) | ⬇ down | -7.78% | -12.59% … -2.98% | 0.53 |
| month (≈14 sessions) | ⬇ down | -14.70% | -24.95% … -4.45% | 0.54 |

Family scores (−1…+1): technicals -0.23, sentiment —, agent —, fundamentals —, price-forecast -1.00.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.
