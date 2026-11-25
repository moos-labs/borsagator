# 🐊 Borsagator digest — walkforward-backtest

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 84.30000305175781 (pandas-ta/indicators.csv, 2025-06-30). Daily volatility σ 1.65% (pandas-ta/indicators.csv (σ60=0.0161, σ10=0.0165)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.65/day). News risk: **none** — 2-family backtest: news risk overlay disabled (issue #436).
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (base-v1): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | +0.19% | -2.00% … +2.38% | 0.60 |
| week (≈3 sessions) | ➡ flat | +0.55% | -3.20% … +4.29% | 0.60 |
| month (≈14 sessions) | ⬇ down | -0.91% | -9.35% … +7.54% | 0.60 |

Family scores (−1…+1): technicals +0.20, sentiment —, agent —, fundamentals —, price-forecast -0.11.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.
