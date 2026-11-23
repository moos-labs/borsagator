# 🐊 Borsagator digest — walkforward-backtest

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 36.66999816894531 (pandas-ta/indicators.csv, 2023-12-28). Daily volatility σ 2.58% (pandas-ta/indicators.csv (σ60=0.0258, σ10=0.0196)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.67/day). News risk: **none** — 2-family backtest: news risk overlay disabled (issue #436).
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (base-v1): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | -0.66% | -3.97% … +2.65% | 0.60 |
| week (≈3 sessions) | ⬆ up | +2.36% | -4.05% … +8.78% | 0.58 |
| month (≈14 sessions) | ⬇ down | -17.72% | -32.38% … -3.06% | 0.52 |

Family scores (−1…+1): technicals -0.15, sentiment —, agent —, fundamentals —, price-forecast -1.00.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.
