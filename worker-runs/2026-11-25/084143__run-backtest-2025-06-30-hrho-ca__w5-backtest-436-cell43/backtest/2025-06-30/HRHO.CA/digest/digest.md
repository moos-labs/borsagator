# 🐊 Borsagator digest — walkforward-backtest

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 26.209999084472656 (pandas-ta/indicators.csv, 2025-06-30). Daily volatility σ 3.85% (pandas-ta/indicators.csv (σ60=0.0290, σ10=0.0385)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.65/day). News risk: **none** — 2-family backtest: news risk overlay disabled (issue #436).
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (base-v1): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | -0.55% | -5.78% … +4.68% | 0.60 |
| week (≈3 sessions) | ⬇ down | -1.75% | -10.62% … +7.12% | 0.60 |
| month (≈14 sessions) | ⬇ down | -5.51% | -24.29% … +13.26% | 0.60 |

Family scores (−1…+1): technicals -0.30, sentiment —, agent —, fundamentals —, price-forecast -0.22.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.
