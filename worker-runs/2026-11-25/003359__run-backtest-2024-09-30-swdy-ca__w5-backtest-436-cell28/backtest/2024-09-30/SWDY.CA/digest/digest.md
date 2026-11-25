# 🐊 Borsagator digest — walkforward-backtest

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 72.5 (pandas-ta/indicators.csv, 2024-09-30). Daily volatility σ 4.33% (pandas-ta/indicators.csv (σ60=0.0433, σ10=0.0402)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.65/day). News risk: **none** — 2-family backtest: news risk overlay disabled (issue #436).
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (base-v1): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | -0.63% | -6.52% … +5.26% | 0.60 |
| week (≈3 sessions) | ⬇ down | -12.69% | -24.33% … -1.04% | 0.50 |
| month (≈14 sessions) | ⬇ down | -36.87% | -61.66% … -12.08% | 0.51 |

Family scores (−1…+1): technicals -0.10, sentiment —, agent —, fundamentals —, price-forecast -1.00.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.
