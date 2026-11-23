# 🐊 Borsagator digest — walkforward-backtest

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 121.44000244140625 (pandas-ta/indicators.csv, 2024-09-30). Daily volatility σ 4.09% (pandas-ta/indicators.csv (σ60=0.0409, σ10=0.0214)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.69/day). News risk: **none** — 2-family backtest: news risk overlay disabled (issue #436).
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (base-v1): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ⬇ down | -1.96% | -8.26% … +4.34% | 0.51 |
| week (≈3 sessions) | ⬇ down | -15.04% | -27.22% … -2.87% | 0.38 |
| month (≈14 sessions) | ⬇ down | -26.30% | -52.06% … -0.55% | 0.41 |

Family scores (−1…+1): technicals +0.45, sentiment —, agent —, fundamentals —, price-forecast -1.00.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.
