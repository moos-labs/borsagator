# 🐊 Borsagator digest — walkforward-backtest

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 82.44999694824219 (pandas-ta/indicators.csv, 2025-03-27). Daily volatility σ 1.13% (pandas-ta/indicators.csv (σ60=0.0108, σ10=0.0113)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.66/day). News risk: **none** — 2-family backtest: news risk overlay disabled (issue #436).
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (base-v1): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | -0.30% | -1.76% … +1.16% | 0.60 |
| week (≈3 sessions) | ⬆ up | +1.07% | -1.70% … +3.85% | 0.59 |
| month (≈14 sessions) | ➡ flat | +0.46% | -5.14% … +6.06% | 0.60 |

Family scores (−1…+1): technicals -0.10, sentiment —, agent —, fundamentals —, price-forecast +0.08.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.
