# 🐊 Borsagator digest — walkforward-backtest

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 84.5 (pandas-ta/indicators.csv, 2024-09-30). Daily volatility σ 1.09% (pandas-ta/indicators.csv (σ60=0.0109, σ10=0.0081)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.65/day). News risk: **none** — 2-family backtest: news risk overlay disabled (issue #436).
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (base-v1): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ⬆ up | +1.47% | -0.32% … +3.25% | 0.44 |
| week (≈3 sessions) | ⬆ up | +3.82% | +0.71% … +6.93% | 0.44 |
| month (≈14 sessions) | ➡ flat | +0.65% | -4.95% … +6.24% | 0.60 |

Family scores (−1…+1): technicals -0.20, sentiment —, agent —, fundamentals —, price-forecast +0.12.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.
