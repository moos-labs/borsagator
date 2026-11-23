# 🐊 Borsagator digest — walkforward-backtest

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 63.70000076293945 (pandas-ta/indicators.csv, 2024-09-30). Daily volatility σ 1.96% (pandas-ta/indicators.csv (σ60=0.0196, σ10=0.0152)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.65/day). News risk: **none** — 2-family backtest: news risk overlay disabled (issue #436).
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (base-v1): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ⬇ down | -1.52% | -5.85% … +2.81% | 0.53 |
| week (≈3 sessions) | ⬆ up | +7.66% | -2.71% … +18.03% | 0.52 |
| month (≈14 sessions) | ⬇ down | -8.53% | -19.87% … +2.81% | 0.51 |

Family scores (−1…+1): technicals +0.20, sentiment —, agent —, fundamentals —, price-forecast -0.75.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.
