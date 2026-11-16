
---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 10.0 (egx-data/egxpy_poul.csv, 2026-11-15). Daily volatility σ 2.25% (egx-data/egxpy_poul.csv (σ60=0.0225, σ10=0.0186)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.66/day). News risk: **shock** — earnings event: Cairo Poultry stock: Nine-month profit drops 38.3% - ad-hoc-news.de; earnings event: القاهرة للدواجن تخفض أرباحها في تسعة أشهر - ArabFinance; earnings event: اليوم.. نهاية حق الحصول على التوزيع النقدي لـ القاهرة للدواجن - مجلة البوصلة الاقتصادية.
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (ledger): price-forecast ×0.993, technicals ×0.742, sentiment ×1.024, agent ×1, fundamentals ×1.

💰 **Corporate action:** dividend 1.9/share, ex-date 2026-11-16 — a mechanical ≈ -19.00% move is expected on the ex-date (not a market signal). Horizons spanning it are marked; the calibration ledger will score them dividend-adjusted.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ⬆ up | +2.26% | -2.71% … +7.23% | 0.30 |
| week (≈3 sessions) | ➡ flat | -0.61% | -8.81% … +7.58% | 0.30 |
| month (≈14 sessions) | ⬇ down | -1.54% | -19.98% … +16.90% | 0.30 |

Family scores (−1…+1): technicals +0.30, sentiment -0.06, agent —, fundamentals +0.40, price-forecast -0.22.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.
