# 🐊 Borsagator digest — walkforward-backtest

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 157.99000549316406 (pandas-ta/indicators.csv, 2025-06-30). Daily volatility σ 3.61% (pandas-ta/indicators.csv (σ60=0.0361, σ10=0.0149)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.68/day). News risk: **none** — 2-family backtest: news risk overlay disabled (issue #436).
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (base-v1): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ⬆ up | +2.52% | -2.50% … +7.53% | 0.60 |
| week (≈3 sessions) | ➡ flat | -0.30% | -8.58% … +7.99% | 0.60 |
| month (≈14 sessions) | ⬇ down | -22.99% | -44.43% … -1.55% | 0.48 |

Family scores (−1…+1): technicals +0.10, sentiment —, agent —, fundamentals —, price-forecast -1.00.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.
