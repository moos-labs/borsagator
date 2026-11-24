# 🐊 Borsagator digest — walkforward-backtest

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 78.5 (pandas-ta/indicators.csv, 2024-12-31). Daily volatility σ 1.24% (pandas-ta/indicators.csv (σ60=0.0124, σ10=0.0104)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.66/day). News risk: **none** — 2-family backtest: news risk overlay disabled (issue #436).
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (base-v1): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ⬆ up | +0.99% | -0.94% … +2.91% | 0.52 |
| week (≈3 sessions) | ⬆ up | +3.34% | -0.19% … +6.86% | 0.44 |
| month (≈14 sessions) | ⬆ up | +7.28% | -0.20% … +14.76% | 0.46 |

Family scores (−1…+1): technicals -0.20, sentiment —, agent —, fundamentals —, price-forecast +1.00.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.
