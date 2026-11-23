# 🐊 Borsagator digest — walkforward-backtest

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 17.350000381469727 (pandas-ta/indicators.csv, 2024-03-31). Daily volatility σ 3.46% (pandas-ta/indicators.csv (σ60=0.0301, σ10=0.0346)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.66/day). News risk: **none** — 2-family backtest: news risk overlay disabled (issue #436).
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (base-v1): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ⬆ up | +1.12% | -3.79% … +6.03% | 0.59 |
| week (≈3 sessions) | ⬆ up | +7.12% | -2.35% … +16.59% | 0.48 |
| month (≈14 sessions) | ⬆ up | +4.55% | -13.61% … +22.70% | 0.60 |

Family scores (−1…+1): technicals -0.20, sentiment —, agent —, fundamentals —, price-forecast +0.24.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.
