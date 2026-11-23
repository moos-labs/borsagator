# 🐊 Borsagator digest — walkforward-backtest

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 16.670000076293945 (pandas-ta/indicators.csv, 2023-12-28). Daily volatility σ 2.03% (pandas-ta/indicators.csv (σ60=0.0203, σ10=0.0128)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.67/day). News risk: **none** — 2-family backtest: news risk overlay disabled (issue #436).
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (base-v1): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ⬆ up | +2.23% | -0.98% … +5.43% | 0.48 |
| week (≈3 sessions) | ⬆ up | +3.99% | -1.52% … +9.50% | 0.49 |
| month (≈14 sessions) | ⬆ up | +2.20% | -8.34% … +12.75% | 0.60 |

Family scores (−1…+1): technicals -0.20, sentiment —, agent —, fundamentals —, price-forecast +0.20.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.
