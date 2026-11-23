# 🐊 Borsagator digest — walkforward-backtest

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 90.35600280761719 (pandas-ta/indicators.csv, 2024-03-28). Daily volatility σ 3.07% (pandas-ta/indicators.csv (σ60=0.0307, σ10=0.0163)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.69/day). News risk: **none** — 2-family backtest: news risk overlay disabled (issue #436).
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (base-v1): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ⬇ down | -5.04% | -9.70% … -0.37% | 0.52 |
| week (≈3 sessions) | ⬇ down | -43.92% | -51.95% … -35.89% | 0.53 |
| month (≈14 sessions) | ⬇ down | -44.31% | -61.44% … -27.18% | 0.54 |

Family scores (−1…+1): technicals -0.23, sentiment —, agent —, fundamentals —, price-forecast -1.00.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.
