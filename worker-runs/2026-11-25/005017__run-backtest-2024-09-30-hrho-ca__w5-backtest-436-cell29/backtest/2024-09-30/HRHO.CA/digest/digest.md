# 🐊 Borsagator digest — walkforward-backtest

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 24.450000762939453 (pandas-ta/indicators.csv, 2024-09-30). Daily volatility σ 2.59% (pandas-ta/indicators.csv (σ60=0.0259, σ10=0.0202)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.65/day). News risk: **none** — 2-family backtest: news risk overlay disabled (issue #436).
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (base-v1): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ⬇ down | -2.42% | -5.87% … +1.03% | 0.60 |
| week (≈3 sessions) | ⬇ down | -8.35% | -14.90% … -1.79% | 0.56 |
| month (≈14 sessions) | ⬇ down | -16.10% | -30.12% … -2.09% | 0.57 |

Family scores (−1…+1): technicals -0.40, sentiment —, agent —, fundamentals —, price-forecast -1.00.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.
