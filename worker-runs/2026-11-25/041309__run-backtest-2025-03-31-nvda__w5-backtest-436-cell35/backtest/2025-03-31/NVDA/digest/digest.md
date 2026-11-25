# 🐊 Borsagator digest — walkforward-backtest

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 108.37999725341797 (pandas-ta/indicators.csv, 2025-03-31). Daily volatility σ 4.29% (pandas-ta/indicators.csv (σ60=0.0429, σ10=0.0245)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.69/day). News risk: **none** — 2-family backtest: news risk overlay disabled (issue #436).
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (base-v1): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ⬆ up | +3.51% | -3.17% … +10.20% | 0.50 |
| week (≈3 sessions) | ⬆ up | +10.16% | -2.09% … +22.41% | 0.43 |
| month (≈14 sessions) | ⬆ up | +13.92% | -10.51% … +38.36% | 0.52 |

Family scores (−1…+1): technicals -0.30, sentiment —, agent —, fundamentals —, price-forecast +0.57.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.
