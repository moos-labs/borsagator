# 🐊 Borsagator digest — walkforward-backtest

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 186.5800018310547 (pandas-ta/indicators.csv, 2025-09-30). Daily volatility σ 2.22% (pandas-ta/indicators.csv (σ60=0.0174, σ10=0.0222)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.68/day). News risk: **none** — 2-family backtest: news risk overlay disabled (issue #436).
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (base-v1): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | -0.60% | -3.73% … +2.53% | 0.60 |
| week (≈3 sessions) | ⬇ down | -5.57% | -11.85% … +0.71% | 0.44 |
| month (≈14 sessions) | ⬇ down | -18.05% | -31.47% … -4.64% | 0.46 |

Family scores (−1…+1): technicals +0.20, sentiment —, agent —, fundamentals —, price-forecast -1.00.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.
