# 🐊 Borsagator digest — walkforward-backtest

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 76.9800033569336 (pandas-ta/indicators.csv, 2024-03-31). Daily volatility σ 3.53% (pandas-ta/indicators.csv (σ60=0.0353, σ10=0.0157)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.66/day). News risk: **none** — 2-family backtest: news risk overlay disabled (issue #436).
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (base-v1): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ⬆ up | +1.68% | -3.44% … +6.80% | 0.57 |
| week (≈3 sessions) | ⬆ up | +3.10% | -5.74% … +11.93% | 0.57 |
| month (≈14 sessions) | ⬇ down | -4.80% | -21.75% … +12.14% | 0.60 |

Family scores (−1…+1): technicals -0.20, sentiment —, agent —, fundamentals —, price-forecast -0.21.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.
