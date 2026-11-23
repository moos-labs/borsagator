# 🐊 Borsagator digest — walkforward-backtest

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 49.52199935913086 (pandas-ta/indicators.csv, 2023-12-29). Daily volatility σ 2.08% (pandas-ta/indicators.csv (σ60=0.0208, σ10=0.0145)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.69/day). News risk: **none** — 2-family backtest: news risk overlay disabled (issue #436).
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (base-v1): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ⬆ up | +2.96% | -0.10% … +6.02% | 0.56 |
| week (≈3 sessions) | ⬆ up | +9.40% | +4.03% … +14.78% | 0.54 |
| month (≈15 sessions) | ⬇ down | -22.66% | -35.88% … -9.44% | 0.44 |

Family scores (−1…+1): technicals +0.30, sentiment —, agent —, fundamentals —, price-forecast -1.00.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.
