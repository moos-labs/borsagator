# 🐊 Borsagator digest — walkforward-backtest

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 61.5 (pandas-ta/indicators.csv, 2024-03-31). Daily volatility σ 6.36% (pandas-ta/indicators.csv (σ60=0.0636, σ10=0.0417)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.66/day). News risk: **none** — 2-family backtest: news risk overlay disabled (issue #436).
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (base-v1): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ⬇ down | -3.16% | -11.43% … +5.12% | 0.60 |
| week (≈3 sessions) | ⬆ up | +8.68% | -8.41% … +25.77% | 0.50 |
| month (≈14 sessions) | ⬇ down | -57.75% | -92.50% … -23.01% | 0.56 |

Family scores (−1…+1): technicals -0.35, sentiment —, agent —, fundamentals —, price-forecast -1.00.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.
