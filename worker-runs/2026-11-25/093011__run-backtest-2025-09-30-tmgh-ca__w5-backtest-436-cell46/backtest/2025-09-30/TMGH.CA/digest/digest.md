# 🐊 Borsagator digest — walkforward-backtest

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 56.880001068115234 (pandas-ta/indicators.csv, 2025-09-30). Daily volatility σ 1.39% (pandas-ta/indicators.csv (σ60=0.0139, σ10=0.0084)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.66/day). News risk: **none** — 2-family backtest: news risk overlay disabled (issue #436).
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (base-v1): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ⬇ down | -1.78% | -4.03% … +0.47% | 0.45 |
| week (≈3 sessions) | ⬇ down | -2.52% | -6.27% … +1.22% | 0.50 |
| month (≈14 sessions) | ⬇ down | -1.67% | -8.94% … +5.60% | 0.60 |

Family scores (−1…+1): technicals +0.20, sentiment —, agent —, fundamentals —, price-forecast -0.22.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.
