# 🐊 Borsagator digest — walkforward-backtest

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 72.94000244140625 (pandas-ta/indicators.csv, 2023-12-28). Daily volatility σ 2.29% (pandas-ta/indicators.csv (σ60=0.0229, σ10=0.0157)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.67/day). News risk: **none** — 2-family backtest: news risk overlay disabled (issue #436).
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (base-v1): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ⬇ down | -32.71% | -41.04% … -24.37% | 0.57 |
| week (≈3 sessions) | ⬇ down | -33.10% | -38.85% … -27.36% | 0.57 |
| month (≈14 sessions) | ⬇ down | -36.57% | -48.86% … -24.28% | 0.58 |

Family scores (−1…+1): technicals -0.45, sentiment —, agent —, fundamentals —, price-forecast -1.00.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.
