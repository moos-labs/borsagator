# 🐊 Borsagator digest — walkforward-backtest

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 56.0 (pandas-ta/indicators.csv, 2024-12-31). Daily volatility σ 2.00% (pandas-ta/indicators.csv (σ60=0.0179, σ10=0.0200)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.66/day). News risk: **none** — 2-family backtest: news risk overlay disabled (issue #436).
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (base-v1): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ⬆ up | +3.19% | -0.28% … +6.66% | 0.37 |
| week (≈3 sessions) | ⬆ up | +6.20% | +0.25% … +12.15% | 0.38 |
| month (≈14 sessions) | ⬆ up | +10.80% | -1.68% … +23.29% | 0.42 |

Family scores (−1…+1): technicals -0.45, sentiment —, agent —, fundamentals —, price-forecast +0.95.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.
