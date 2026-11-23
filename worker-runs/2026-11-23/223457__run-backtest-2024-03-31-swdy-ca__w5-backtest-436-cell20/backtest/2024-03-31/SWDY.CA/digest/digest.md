# 🐊 Borsagator digest — walkforward-backtest

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 31.5 (pandas-ta/indicators.csv, 2024-03-31). Daily volatility σ 5.11% (pandas-ta/indicators.csv (σ60=0.0482, σ10=0.0511)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.66/day). News risk: **none** — 2-family backtest: news risk overlay disabled (issue #436).
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (base-v1): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ⬇ down | -2.14% | -8.77% … +4.49% | 0.60 |
| week (≈3 sessions) | ⬆ up | +1.65% | -10.61% … +13.91% | 0.60 |
| month (≈14 sessions) | ⬇ down | -6.71% | -31.23% … +17.82% | 0.60 |

Family scores (−1…+1): technicals -0.20, sentiment —, agent —, fundamentals —, price-forecast -0.21.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.
