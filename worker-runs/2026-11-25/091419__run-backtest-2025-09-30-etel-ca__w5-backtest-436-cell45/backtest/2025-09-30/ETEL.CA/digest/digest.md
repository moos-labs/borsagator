# 🐊 Borsagator digest — walkforward-backtest

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 51.0 (pandas-ta/indicators.csv, 2025-09-30). Daily volatility σ 2.12% (pandas-ta/indicators.csv (σ60=0.0212, σ10=0.0145)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.66/day). News risk: **none** — 2-family backtest: news risk overlay disabled (issue #436).
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (base-v1): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ⬇ down | -2.97% | -6.22% … +0.28% | 0.51 |
| week (≈3 sessions) | ⬇ down | -5.76% | -11.45% … -0.07% | 0.50 |
| month (≈14 sessions) | ⬇ down | -21.24% | -33.36% … -9.12% | 0.51 |

Family scores (−1…+1): technicals -0.10, sentiment —, agent —, fundamentals —, price-forecast -1.00.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.
