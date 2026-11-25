# 🐊 Borsagator digest — walkforward-backtest

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 134.2899932861328 (pandas-ta/indicators.csv, 2024-12-31). Daily volatility σ 2.29% (pandas-ta/indicators.csv (σ60=0.0229, σ10=0.0192)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.69/day). News risk: **none** — 2-family backtest: news risk overlay disabled (issue #436).
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (base-v1): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | +0.33% | -2.66% … +3.31% | 0.60 |
| week (≈3 sessions) | ⬇ down | -4.76% | -10.98% … +1.45% | 0.49 |
| month (≈14 sessions) | ⬇ down | -15.81% | -29.52% … -2.10% | 0.47 |

Family scores (−1…+1): technicals +0.15, sentiment —, agent —, fundamentals —, price-forecast -1.00.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.
