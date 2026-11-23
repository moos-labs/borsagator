# 🐊 Borsagator digest — walkforward-backtest

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 28.610000610351562 (pandas-ta/indicators.csv, 2023-12-28). Daily volatility σ 2.74% (pandas-ta/indicators.csv (σ60=0.0274, σ10=0.0196)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.67/day). News risk: **none** — 2-family backtest: news risk overlay disabled (issue #436).
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (base-v1): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ⬆ up | +4.80% | -2.22% … +11.83% | 0.54 |
| week (≈3 sessions) | ⬆ up | +4.22% | -2.21% … +10.65% | 0.60 |
| month (≈14 sessions) | ⬇ down | -31.30% | -48.14% … -14.46% | 0.44 |

Family scores (−1…+1): technicals +0.30, sentiment —, agent —, fundamentals —, price-forecast -1.00.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.
