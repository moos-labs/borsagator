# 🐊 Borsagator — walk-forward backtest (v2)

> ⚠️ **Flattery warning:** Kronos-small (NeoQuasar/Kronos-small) is a pretrained model whose training data is historical market data. Backtest scores are therefore an UPPER BOUND on live skill, not an estimate of it. The forward ledger (issue #79) remains the only basis for accuracy claims (decision D4 unchanged).

> Out of scope for this backtest (design §5.2): sentiment/news (no complete historical headline archive exists), agent/LLM (training knowledge leaks the future), fundamentals (no verified point-in-time statement vintages), and validation / backtest-category tools (qlib, vectorbt, backtrader) which are not direction voters. Only price-forecast (Kronos) and technicals (pandas-ta voter + talib cross-check) are scored, separately and as a 2-family ensemble.

**Forecasts found: 786 · matured: 786 · pending: 0 · invalid: 0 · captures: 48**

No quality claim is made for any (entrant, horizon) cell with n < 10 matured rows. Backtest n never counts toward the forward ledger's D4 threshold (n ≥ 30 matured).

## By ticker

| Ticker | Found | Matured | Pending | Invalid |
|---|---|---|---|---|
| COMI.CA | 126 | 126 | 0 | 0 |
| ETEL.CA | 126 | 126 | 0 | 0 |
| HRHO.CA | 111 | 111 | 0 | 0 |
| NVDA | 186 | 186 | 0 | 0 |
| SWDY.CA | 111 | 111 | 0 | 0 |
| TMGH.CA | 126 | 126 | 0 | 0 |

## By entrant and horizon (matured only, gap-flagged rows excluded from skill)

| Entrant | Horizon | n | Hit rate | MAE pp | Range cov. | Hit vs B&H | MAE vs B&H | Hit vs index | MAE vs index |
|---|---|---|---|---|---|---|---|---|---|
| 2-family-ensemble | day | 48 | 0.375 | 3.2 | 0.646 | 0.063 | 1.45 | -0.6 | 2.75 |
| 2-family-ensemble | week | 48 | 0.354 | 8.46 | 0.521 | 0.292 | 3.89 | -0.1 | 11.99 |
| 2-family-ensemble | month | 48 | 0.25 | 18.1 | 0.417 | 0.167 | 8.51 | 0.3 | 22.99 |
| kronos-alone | day | 48 | 0.333 | 3.95 | 0.479 | 0.021 | 2.2 | -0.6 | 3.39 |
| kronos-alone | week | 48 | 0.5 | 10.91 | 0.354 | 0.438 | 6.34 | 0.1 | 17.85 |
| kronos-alone | month | 48 | 0.333 | 24.35 | 0.083 | 0.25 | 14.76 | 0.3 | 30.83 |
| family-technicals | day | 48 | 0.312 | 1.86 | 0.854 | 0.0 | 0.11 | -0.6 | 1.55 |
| family-technicals | week | 48 | 0.25 | 4.53 | 0.667 | 0.188 | -0.04 | -0.2 | 1.7 |
| family-technicals | month | 48 | 0.354 | 9.62 | 0.75 | 0.271 | 0.03 | 0.4 | 8.45 |
| buy-and-hold | day | 48 | 0.312 | 1.75 | 0.812 | 0.0 | 0.0 | -0.6 | 1.31 |
| buy-and-hold | week | 48 | 0.062 | 4.57 | 0.646 | 0.0 | 0.0 | -0.4 | 1.82 |
| buy-and-hold | month | 48 | 0.083 | 9.59 | 0.75 | 0.0 | 0.0 | 0.1 | 8.6 |
| index-baseline | day | 10 | 0.9 | 0.39 | — | 0.6 | -1.31 | 0.0 | 0.0 |
| index-baseline | week | 10 | 0.4 | 2.04 | — | 0.4 | -1.82 | 0.0 | 0.0 |
| index-baseline | month | 10 | 0.1 | 2.65 | — | -0.1 | -8.6 | 0.0 | 0.0 |
| naive-range | day | 48 | 0.312 | 1.75 | 0.812 | 0.0 | 0.0 | -0.6 | 1.31 |
| naive-range | week | 48 | 0.062 | 4.57 | 0.75 | 0.0 | 0.0 | -0.4 | 1.82 |
| naive-range | month | 48 | 0.083 | 9.59 | 0.812 | 0.0 | 0.0 | 0.1 | 8.6 |
| tilt-technicals | day | 12 | 0.333 | 2.37 | 0.583 | 0.0 | 0.0 | -1.0 | 0.57 |
| tilt-technicals | week | 12 | 0.083 | 4.47 | 0.667 | 0.0 | 0.22 | 0.0 | 0.62 |
| tilt-technicals | month | 12 | 0.083 | 14.37 | 0.583 | 0.0 | 0.29 | 0.0 | 2.38 |

Deltas vs buy-and-hold / index are computed on matched captures only (both the entrant and the baseline matured there); the paired n per cell is in backtest.json.

## RangeSkill gate vs naive-range (issue #594)

RangeSkill = 1 − mean interval score / naive mean interval score (Winkler, 80%). PASS needs RangeSkill > 0 with the paired-bootstrap 95% CI lower bound on the IS gap above 0 AND pooled coverage in 75–85% at n ≥ 30. Frozen v2 baseline on the 41 cells: RangeSkill −1.06 / −1.59 / −2.48 (day / week / month, at 1/5/14 sessions — month now scores at 21, so the adoption test re-measures it there).

| Entrant | Horizon | n | Mean IS | Naive IS | RangeSkill | Gap 95% CI | Coverage | Gate |
|---|---|---|---|---|---|---|---|---|
| 2-family-ensemble | day | 48 | 16.07 | 8.43 | -0.906 | [-19.09, -1.39] | 0.646 | FAIL |
| 2-family-ensemble | week | 48 | 53.15 | 21.78 | -1.44 | [-54.31, -12.66] | 0.521 | FAIL |
| 2-family-ensemble | month | 48 | 104.46 | 45.67 | -1.287 | [-92.62, -31.2] | 0.417 | FAIL |
| kronos-alone | day | 48 | 22.89 | 8.43 | -1.715 | [-36.18, -2.5] | 0.479 | FAIL |
| kronos-alone | week | 48 | 87.44 | 21.78 | -3.015 | [-107.33, -30.51] | 0.354 | FAIL |
| kronos-alone | month | 48 | 222.79 | 45.67 | -3.878 | [-239.66, -118.05] | 0.083 | FAIL |
| family-technicals | day | 48 | 8.84 | 8.43 | -0.049 | [-0.79, -0.11] | 0.854 | FAIL |
| family-technicals | week | 48 | 22.33 | 21.78 | -0.025 | [-2.39, 1.14] | 0.667 | FAIL |
| family-technicals | month | 48 | 46.12 | 45.67 | -0.01 | [-4.31, 2.58] | 0.75 | FAIL |
| buy-and-hold | day | 48 | 8.49 | 8.43 | -0.007 | [-0.16, 0.0] | 0.812 | FAIL |
| buy-and-hold | week | 48 | 22.61 | 21.78 | -0.038 | [-2.48, 0.7] | 0.646 | FAIL |
| buy-and-hold | month | 48 | 45.04 | 45.67 | 0.014 | [-2.18, 2.89] | 0.75 | FAIL |
| index-baseline | day | 10 | — | 7.79 | — | — | — | n<30 |
| index-baseline | week | 10 | — | 17.16 | — | — | — | n<30 |
| index-baseline | month | 10 | — | 47.99 | — | — | — | n<30 |
| naive-range | day | 48 | 8.43 | 8.43 | 0.0 | [0.0, 0.0] | 0.812 | FAIL |
| naive-range | week | 48 | 21.78 | 21.78 | 0.0 | [0.0, 0.0] | 0.75 | FAIL |
| naive-range | month | 48 | 45.67 | 45.67 | 0.0 | [0.0, 0.0] | 0.812 | FAIL |
| tilt-technicals | day | 12 | 11.92 | 11.26 | -0.059 | [-1.63, 0.14] | 0.583 | n<30 |
| tilt-technicals | week | 12 | 17.97 | 17.25 | -0.042 | [-1.92, 0.41] | 0.667 | n<30 |
| tilt-technicals | month | 12 | 76.16 | 72.4 | -0.052 | [-8.4, 0.39] | 0.583 | n<30 |

## Family skill (2-family ensemble rows only; mean of family_score × sign(realized), matured only)

| Family | Mean skill | n |
|---|---|---|
| ensemble (net_score) | -0.065 | 132 |
| price-forecast | -0.095 | 108 |
| technicals | +0.019 | 132 |

## Forecasts

| Ticker | As of | Horizon | Entrant | Dir | Expected % | Realized % | Hit | |Err| pp | In range | Adj | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| COMI.CA | 2023-12-29 | day | 2-family-ensemble | down | -32.71 | -0.40 | ❌ | 32.31 | ❌ |  | matured 2023-12-31 |
| COMI.CA | 2023-12-29 | week | 2-family-ensemble | down | -33.10 | +2.48 | ❌ | 35.58 | ❌ |  | matured 2024-01-08 |
| COMI.CA | 2023-12-29 | month | 2-family-ensemble | down | -36.57 | +20.78 | ❌ | 57.35 | ❌ |  | matured 2024-01-31 |
| COMI.CA | 2023-12-29 | day | kronos-alone | down | -52.99 | -0.40 | ❌ | 52.59 | ❌ |  | matured 2023-12-31 |
| COMI.CA | 2023-12-29 | week | kronos-alone | down | -52.40 | +2.48 | ❌ | 54.88 | ❌ |  | matured 2024-01-08 |
| COMI.CA | 2023-12-29 | month | kronos-alone | down | -54.63 | +20.78 | ❌ | 75.41 | ❌ |  | matured 2024-01-31 |
| COMI.CA | 2023-12-29 | day | family-technicals | flat | -0.53 | -0.40 | ✅ | 0.13 | ✅ |  | matured 2023-12-31 |
| COMI.CA | 2023-12-29 | week | family-technicals | down | -0.91 | +2.48 | ❌ | 3.39 | ✅ |  | matured 2024-01-08 |
| COMI.CA | 2023-12-29 | month | family-technicals | down | -1.97 | +20.78 | ❌ | 22.75 | ❌ |  | matured 2024-01-31 |
| COMI.CA | 2023-12-29 | day | buy-and-hold | flat | +0.00 | -0.40 | ✅ | 0.40 | ✅ |  | matured 2023-12-31 |
| COMI.CA | 2023-12-29 | week | buy-and-hold | flat | +0.00 | +2.48 | ❌ | 2.48 | ✅ |  | matured 2024-01-08 |
| COMI.CA | 2023-12-29 | month | buy-and-hold | flat | +0.00 | +20.78 | ❌ | 20.78 | ❌ |  | matured 2024-01-31 |
| COMI.CA | 2023-12-29 | day | naive-range | flat | +0.00 | -0.40 | ✅ | 0.40 | ✅ |  | matured 2023-12-31 |
| COMI.CA | 2023-12-29 | week | naive-range | flat | +0.00 | +2.48 | ❌ | 2.48 | ✅ |  | matured 2024-01-08 |
| COMI.CA | 2023-12-29 | month | naive-range | flat | +0.00 | +20.78 | ❌ | 20.78 | ❌ |  | matured 2024-01-31 |
| ETEL.CA | 2023-12-29 | day | 2-family-ensemble | flat | -0.66 | +2.67 | ❌ | 3.33 | ❌ |  | matured 2023-12-31 |
| ETEL.CA | 2023-12-29 | week | 2-family-ensemble | up | +2.36 | +3.52 | ✅ | 1.16 | ✅ |  | matured 2024-01-08 |
| ETEL.CA | 2023-12-29 | month | 2-family-ensemble | down | -17.72 | -0.30 | ❌ | 17.42 | ❌ |  | matured 2024-01-31 |
| ETEL.CA | 2023-12-29 | day | kronos-alone | down | -0.76 | +2.67 | ❌ | 3.43 | ❌ |  | matured 2023-12-31 |
| ETEL.CA | 2023-12-29 | week | kronos-alone | up | +3.22 | +3.52 | ✅ | 0.30 | ✅ |  | matured 2024-01-08 |
| ETEL.CA | 2023-12-29 | month | kronos-alone | down | -23.03 | -0.30 | ❌ | 22.73 | ❌ |  | matured 2024-01-31 |
| ETEL.CA | 2023-12-29 | day | family-technicals | flat | -0.20 | +2.67 | ❌ | 2.87 | ✅ |  | matured 2023-12-31 |
| ETEL.CA | 2023-12-29 | week | family-technicals | flat | -0.34 | +3.52 | ❌ | 3.86 | ✅ |  | matured 2024-01-08 |
| ETEL.CA | 2023-12-29 | month | family-technicals | flat | -0.74 | -0.30 | ✅ | 0.44 | ✅ |  | matured 2024-01-31 |
| ETEL.CA | 2023-12-29 | day | buy-and-hold | flat | +0.00 | +2.67 | ❌ | 2.67 | ✅ |  | matured 2023-12-31 |
| ETEL.CA | 2023-12-29 | week | buy-and-hold | flat | +0.00 | +3.52 | ❌ | 3.52 | ✅ |  | matured 2024-01-08 |
| ETEL.CA | 2023-12-29 | month | buy-and-hold | flat | +0.00 | -0.30 | ✅ | 0.30 | ✅ |  | matured 2024-01-31 |
| ETEL.CA | 2023-12-29 | day | naive-range | flat | +0.00 | +2.67 | ❌ | 2.67 | ✅ |  | matured 2023-12-31 |
| ETEL.CA | 2023-12-29 | week | naive-range | flat | +0.00 | +3.52 | ❌ | 3.52 | ✅ |  | matured 2024-01-08 |
| ETEL.CA | 2023-12-29 | month | naive-range | flat | +0.00 | -0.30 | ✅ | 0.30 | ✅ |  | matured 2024-01-31 |
| HRHO.CA | 2023-12-29 | day | 2-family-ensemble | up | +2.23 | -2.10 | ❌ | 4.33 | ❌ |  | matured 2023-12-31 |
| HRHO.CA | 2023-12-29 | week | 2-family-ensemble | up | +3.99 | +3.54 | ✅ | 0.45 | ✅ |  | matured 2024-01-08 |
| HRHO.CA | 2023-12-29 | month | 2-family-ensemble | up | +2.20 | +8.58 | ✅ | 6.38 | ✅ |  | matured 2024-01-31 |
| HRHO.CA | 2023-12-29 | day | kronos-alone | up | +3.06 | -2.10 | ❌ | 5.16 | ❌ |  | matured 2023-12-31 |
| HRHO.CA | 2023-12-29 | week | kronos-alone | up | +5.33 | +3.54 | ✅ | 1.79 | ✅ |  | matured 2024-01-08 |
| HRHO.CA | 2023-12-29 | month | kronos-alone | up | +3.03 | +8.58 | ✅ | 5.55 | ❌ |  | matured 2024-01-31 |
| HRHO.CA | 2023-12-29 | day | family-technicals | flat | -0.21 | -2.10 | ❌ | 1.89 | ✅ |  | matured 2023-12-31 |
| HRHO.CA | 2023-12-29 | week | family-technicals | flat | -0.36 | +3.54 | ❌ | 3.90 | ✅ |  | matured 2024-01-08 |
| HRHO.CA | 2023-12-29 | month | family-technicals | down | -0.78 | +8.58 | ❌ | 9.36 | ✅ |  | matured 2024-01-31 |
| HRHO.CA | 2023-12-29 | day | buy-and-hold | flat | +0.00 | -2.10 | ❌ | 2.10 | ✅ |  | matured 2023-12-31 |
| HRHO.CA | 2023-12-29 | week | buy-and-hold | flat | +0.00 | +3.54 | ❌ | 3.54 | ✅ |  | matured 2024-01-08 |
| HRHO.CA | 2023-12-29 | month | buy-and-hold | flat | +0.00 | +8.58 | ❌ | 8.58 | ✅ |  | matured 2024-01-31 |
| HRHO.CA | 2023-12-29 | day | naive-range | flat | +0.00 | -2.10 | ❌ | 2.10 | ✅ |  | matured 2023-12-31 |
| HRHO.CA | 2023-12-29 | week | naive-range | flat | +0.00 | +3.54 | ❌ | 3.54 | ✅ |  | matured 2024-01-08 |
| HRHO.CA | 2023-12-29 | month | naive-range | flat | +0.00 | +8.58 | ❌ | 8.58 | ✅ |  | matured 2024-01-31 |
| NVDA | 2023-12-29 | day | 2-family-ensemble | up | +2.96 | -2.73 | ❌ | 5.69 | ❌ |  | matured 2024-01-02 |
| NVDA | 2023-12-29 | week | 2-family-ensemble | up | +9.40 | +5.51 | ✅ | 3.89 | ✅ |  | matured 2024-01-08 |
| NVDA | 2023-12-29 | month | 2-family-ensemble | down | -22.66 | +24.24 | ❌ | 46.90 | ❌ |  | matured 2024-01-31 |
| NVDA | 2023-12-29 | day | kronos-alone | up | +3.76 | -2.73 | ❌ | 6.49 | ❌ |  | matured 2024-01-02 |
| NVDA | 2023-12-29 | week | kronos-alone | up | +13.31 | +5.51 | ✅ | 7.80 | ❌ |  | matured 2024-01-08 |
| NVDA | 2023-12-29 | month | kronos-alone | down | -33.12 | +24.24 | ❌ | 57.36 | ❌ |  | matured 2024-01-31 |
| NVDA | 2023-12-29 | day | family-technicals | flat | +0.32 | -2.73 | ❌ | 3.05 | ❌ |  | matured 2024-01-02 |
| NVDA | 2023-12-29 | week | family-technicals | flat | +0.55 | +5.51 | ❌ | 4.96 | ❌ |  | matured 2024-01-08 |
| NVDA | 2023-12-29 | month | family-technicals | up | +1.24 | +24.24 | ✅ | 23.00 | ❌ |  | matured 2024-01-31 |
| NVDA | 2023-12-29 | day | buy-and-hold | flat | +0.00 | -2.73 | ❌ | 2.73 | ❌ |  | matured 2024-01-02 |
| NVDA | 2023-12-29 | week | buy-and-hold | flat | +0.00 | +5.51 | ❌ | 5.51 | ❌ |  | matured 2024-01-08 |
| NVDA | 2023-12-29 | month | buy-and-hold | flat | +0.00 | +24.24 | ❌ | 24.24 | ❌ |  | matured 2024-01-31 |
| NVDA | 2023-12-29 | day | index-baseline | flat | +0.00 | -0.57 | ✅ | 0.57 | ❌ |  | matured 2024-01-02 |
| NVDA | 2023-12-29 | week | index-baseline | flat | +0.00 | -0.13 | ✅ | 0.13 | ❌ |  | matured 2024-01-08 |
| NVDA | 2023-12-29 | month | index-baseline | flat | +0.00 | +1.59 | ❌ | 1.59 | ❌ |  | matured 2024-01-31 |
| NVDA | 2023-12-29 | day | naive-range | flat | +0.00 | -2.73 | ❌ | 2.73 | ❌ |  | matured 2024-01-02 |
| NVDA | 2023-12-29 | week | naive-range | flat | +0.00 | +5.51 | ❌ | 5.51 | ✅ |  | matured 2024-01-08 |
| NVDA | 2023-12-29 | month | naive-range | flat | +0.00 | +24.24 | ❌ | 24.24 | ❌ |  | matured 2024-01-31 |
| SWDY.CA | 2023-12-29 | day | 2-family-ensemble | up | +4.80 | +1.36 | ✅ | 3.44 | ✅ |  | matured 2023-12-31 |
| SWDY.CA | 2023-12-29 | week | 2-family-ensemble | up | +4.22 | +4.09 | ✅ | 0.13 | ✅ |  | matured 2024-01-08 |
| SWDY.CA | 2023-12-29 | month | 2-family-ensemble | down | -31.30 | +12.55 | ❌ | 43.85 | ❌ |  | matured 2024-01-31 |
| SWDY.CA | 2023-12-29 | day | kronos-alone | up | +6.32 | +1.36 | ✅ | 4.96 | ✅ |  | matured 2023-12-31 |
| SWDY.CA | 2023-12-29 | week | kronos-alone | up | +5.16 | +4.09 | ✅ | 1.07 | ✅ |  | matured 2024-01-08 |
| SWDY.CA | 2023-12-29 | month | kronos-alone | down | -46.25 | +12.55 | ❌ | 58.80 | ❌ |  | matured 2024-01-31 |
| SWDY.CA | 2023-12-29 | day | family-technicals | flat | +0.42 | +1.36 | ❌ | 0.94 | ✅ |  | matured 2023-12-31 |
| SWDY.CA | 2023-12-29 | week | family-technicals | flat | +0.73 | +4.09 | ❌ | 3.36 | ✅ |  | matured 2024-01-08 |
| SWDY.CA | 2023-12-29 | month | family-technicals | up | +1.57 | +12.55 | ✅ | 10.98 | ✅ |  | matured 2024-01-31 |
| SWDY.CA | 2023-12-29 | day | buy-and-hold | flat | +0.00 | +1.36 | ❌ | 1.36 | ✅ |  | matured 2023-12-31 |
| SWDY.CA | 2023-12-29 | week | buy-and-hold | flat | +0.00 | +4.09 | ❌ | 4.09 | ✅ |  | matured 2024-01-08 |
| SWDY.CA | 2023-12-29 | month | buy-and-hold | flat | +0.00 | +12.55 | ❌ | 12.55 | ✅ |  | matured 2024-01-31 |
| SWDY.CA | 2023-12-29 | day | naive-range | flat | +0.00 | +1.36 | ❌ | 1.36 | ✅ |  | matured 2023-12-31 |
| SWDY.CA | 2023-12-29 | week | naive-range | flat | +0.00 | +4.09 | ❌ | 4.09 | ✅ |  | matured 2024-01-08 |
| SWDY.CA | 2023-12-29 | month | naive-range | flat | +0.00 | +12.55 | ❌ | 12.55 | ✅ |  | matured 2024-01-31 |
| TMGH.CA | 2023-12-29 | day | 2-family-ensemble | down | -7.23 | +1.26 | ❌ | 8.49 | ❌ |  | matured 2023-12-31 |
| TMGH.CA | 2023-12-29 | week | 2-family-ensemble | down | -17.33 | -0.84 | ✅ | 16.49 | ❌ |  | matured 2024-01-08 |
| TMGH.CA | 2023-12-29 | month | 2-family-ensemble | down | -42.23 | +38.36 | ❌ | 80.59 | ❌ |  | matured 2024-01-31 |
| TMGH.CA | 2023-12-29 | day | kronos-alone | down | -9.40 | +1.26 | ❌ | 10.66 | ❌ |  | matured 2023-12-31 |
| TMGH.CA | 2023-12-29 | week | kronos-alone | down | -23.89 | -0.84 | ✅ | 23.05 | ❌ |  | matured 2024-01-08 |
| TMGH.CA | 2023-12-29 | month | kronos-alone | down | -58.52 | +38.36 | ❌ | 96.88 | ❌ |  | matured 2024-01-31 |
| TMGH.CA | 2023-12-29 | day | family-technicals | flat | -0.36 | +1.26 | ❌ | 1.62 | ✅ |  | matured 2023-12-31 |
| TMGH.CA | 2023-12-29 | week | family-technicals | flat | -0.63 | -0.84 | ❌ | 0.21 | ✅ |  | matured 2024-01-08 |
| TMGH.CA | 2023-12-29 | month | family-technicals | down | -1.36 | +38.36 | ❌ | 39.72 | ❌ |  | matured 2024-01-31 |
| TMGH.CA | 2023-12-29 | day | buy-and-hold | flat | +0.00 | +1.26 | ❌ | 1.26 | ✅ |  | matured 2023-12-31 |
| TMGH.CA | 2023-12-29 | week | buy-and-hold | flat | +0.00 | -0.84 | ❌ | 0.84 | ✅ |  | matured 2024-01-08 |
| TMGH.CA | 2023-12-29 | month | buy-and-hold | flat | +0.00 | +38.36 | ❌ | 38.36 | ❌ |  | matured 2024-01-31 |
| TMGH.CA | 2023-12-29 | day | naive-range | flat | +0.00 | +1.26 | ❌ | 1.26 | ✅ |  | matured 2023-12-31 |
| TMGH.CA | 2023-12-29 | week | naive-range | flat | +0.00 | -0.84 | ❌ | 0.84 | ✅ |  | matured 2024-01-08 |
| TMGH.CA | 2023-12-29 | month | naive-range | flat | +0.00 | +38.36 | ❌ | 38.36 | ❌ |  | matured 2024-01-31 |
| NVDA | 2024-03-31 | day | 2-family-ensemble | down | -5.04 | +0.01 | ❌ | 5.05 | ❌ |  | matured 2024-04-01 |
| NVDA | 2024-03-31 | week | 2-family-ensemble | down | -43.92 | -2.60 | ✅ | 41.32 | ❌ |  | matured 2024-04-05 |
| NVDA | 2024-03-31 | month | 2-family-ensemble | down | -44.31 | -2.88 | ✅ | 41.43 | ❌ |  | matured 2024-04-29 |
| NVDA | 2024-03-31 | day | kronos-alone | down | -6.58 | +0.01 | ❌ | 6.59 | ✅ |  | matured 2024-04-01 |
| NVDA | 2024-03-31 | week | kronos-alone | down | -69.83 | -2.60 | ✅ | 67.23 | ❌ |  | matured 2024-04-05 |
| NVDA | 2024-03-31 | month | kronos-alone | down | -65.94 | -2.88 | ✅ | 63.06 | ❌ |  | matured 2024-04-29 |
| NVDA | 2024-03-31 | day | family-technicals | flat | -0.37 | +0.01 | ✅ | 0.38 | ✅ |  | matured 2024-04-01 |
| NVDA | 2024-03-31 | week | family-technicals | flat | -0.63 | -2.60 | ❌ | 1.97 | ✅ |  | matured 2024-04-05 |
| NVDA | 2024-03-31 | month | family-technicals | down | -1.37 | -2.88 | ✅ | 1.51 | ✅ |  | matured 2024-04-29 |
| NVDA | 2024-03-31 | day | buy-and-hold | flat | +0.00 | +0.01 | ✅ | 0.01 | ✅ |  | matured 2024-04-01 |
| NVDA | 2024-03-31 | week | buy-and-hold | flat | +0.00 | -2.60 | ❌ | 2.60 | ✅ |  | matured 2024-04-05 |
| NVDA | 2024-03-31 | month | buy-and-hold | flat | +0.00 | -2.88 | ❌ | 2.88 | ✅ |  | matured 2024-04-29 |
| NVDA | 2024-03-31 | day | index-baseline | flat | +0.00 | -0.20 | ✅ | 0.20 | ❌ |  | matured 2024-04-01 |
| NVDA | 2024-03-31 | week | index-baseline | flat | +0.00 | -0.95 | ❌ | 0.95 | ❌ |  | matured 2024-04-05 |
| NVDA | 2024-03-31 | month | index-baseline | flat | +0.00 | -2.63 | ❌ | 2.63 | ❌ |  | matured 2024-04-29 |
| NVDA | 2024-03-31 | day | naive-range | flat | +0.00 | +0.01 | ✅ | 0.01 | ✅ |  | matured 2024-04-01 |
| NVDA | 2024-03-31 | week | naive-range | flat | +0.00 | -2.60 | ❌ | 2.60 | ✅ |  | matured 2024-04-05 |
| NVDA | 2024-03-31 | month | naive-range | flat | +0.00 | -2.88 | ❌ | 2.88 | ✅ |  | matured 2024-04-29 |
| NVDA | 2024-06-30 | day | 2-family-ensemble | up | +6.60 | +0.62 | ❌ | 5.98 | ✅ |  | matured 2024-07-01 |
| NVDA | 2024-06-30 | week | 2-family-ensemble | down | -30.45 | +3.77 | ❌ | 34.22 | ❌ |  | matured 2024-07-08 |
| NVDA | 2024-06-30 | month | 2-family-ensemble | down | -45.02 | -16.04 | ✅ | 28.98 | ❌ |  | matured 2024-07-30 |
| NVDA | 2024-06-30 | day | kronos-alone | up | +9.44 | +0.62 | ❌ | 8.82 | ✅ |  | matured 2024-07-01 |
| NVDA | 2024-06-30 | week | kronos-alone | down | -46.76 | +3.77 | ❌ | 50.53 | ❌ |  | matured 2024-07-08 |
| NVDA | 2024-06-30 | month | kronos-alone | down | -65.69 | -16.04 | ✅ | 49.65 | ❌ |  | matured 2024-07-30 |
| NVDA | 2024-06-30 | day | family-technicals | flat | -0.43 | +0.62 | ✅ | 1.05 | ✅ |  | matured 2024-07-01 |
| NVDA | 2024-06-30 | week | family-technicals | flat | -0.75 | +3.77 | ❌ | 4.52 | ✅ |  | matured 2024-07-08 |
| NVDA | 2024-06-30 | month | family-technicals | down | -1.62 | -16.04 | ✅ | 14.42 | ✅ |  | matured 2024-07-30 |
| NVDA | 2024-06-30 | day | buy-and-hold | flat | +0.00 | +0.62 | ✅ | 0.62 | ✅ |  | matured 2024-07-01 |
| NVDA | 2024-06-30 | week | buy-and-hold | flat | +0.00 | +3.77 | ❌ | 3.77 | ✅ |  | matured 2024-07-08 |
| NVDA | 2024-06-30 | month | buy-and-hold | flat | +0.00 | -16.04 | ❌ | 16.04 | ✅ |  | matured 2024-07-30 |
| NVDA | 2024-06-30 | day | index-baseline | flat | +0.00 | +0.27 | ✅ | 0.27 | ❌ |  | matured 2024-07-01 |
| NVDA | 2024-06-30 | week | index-baseline | flat | +0.00 | +2.06 | ❌ | 2.06 | ❌ |  | matured 2024-07-08 |
| NVDA | 2024-06-30 | month | index-baseline | flat | +0.00 | -0.44 | ✅ | 0.44 | ❌ |  | matured 2024-07-30 |
| NVDA | 2024-06-30 | day | naive-range | flat | +0.00 | +0.62 | ✅ | 0.62 | ✅ |  | matured 2024-07-01 |
| NVDA | 2024-06-30 | week | naive-range | flat | +0.00 | +3.77 | ❌ | 3.77 | ✅ |  | matured 2024-07-08 |
| NVDA | 2024-06-30 | month | naive-range | flat | +0.00 | -16.04 | ❌ | 16.04 | ✅ |  | matured 2024-07-30 |
| COMI.CA | 2024-09-30 | day | 2-family-ensemble | up | +1.47 | +2.19 | ✅ | 0.72 | ✅ |  | matured 2024-10-01 |
| COMI.CA | 2024-09-30 | week | 2-family-ensemble | up | +3.82 | -1.18 | ❌ | 5.00 | ❌ |  | matured 2024-10-08 |
| COMI.CA | 2024-09-30 | month | 2-family-ensemble | flat | +0.65 | -5.63 | ❌ | 6.28 | ❌ |  | matured 2024-10-30 |
| COMI.CA | 2024-09-30 | day | kronos-alone | up | +2.01 | +2.19 | ✅ | 0.18 | ✅ |  | matured 2024-10-01 |
| COMI.CA | 2024-09-30 | week | kronos-alone | up | +5.40 | -1.18 | ❌ | 6.58 | ❌ |  | matured 2024-10-08 |
| COMI.CA | 2024-09-30 | month | kronos-alone | up | +0.95 | -5.63 | ❌ | 6.58 | ❌ |  | matured 2024-10-30 |
| COMI.CA | 2024-09-30 | day | family-technicals | flat | -0.11 | +2.19 | ❌ | 2.30 | ❌ |  | matured 2024-10-01 |
| COMI.CA | 2024-09-30 | week | family-technicals | flat | -0.19 | -1.18 | ❌ | 0.99 | ✅ |  | matured 2024-10-08 |
| COMI.CA | 2024-09-30 | month | family-technicals | flat | -0.42 | -5.63 | ❌ | 5.21 | ✅ |  | matured 2024-10-30 |
| COMI.CA | 2024-09-30 | day | buy-and-hold | flat | +0.00 | +2.19 | ❌ | 2.19 | ❌ |  | matured 2024-10-01 |
| COMI.CA | 2024-09-30 | week | buy-and-hold | flat | +0.00 | -1.18 | ❌ | 1.18 | ✅ |  | matured 2024-10-08 |
| COMI.CA | 2024-09-30 | month | buy-and-hold | flat | +0.00 | -5.63 | ❌ | 5.63 | ❌ |  | matured 2024-10-30 |
| COMI.CA | 2024-09-30 | day | naive-range | flat | +0.00 | +2.19 | ❌ | 2.19 | ❌ |  | matured 2024-10-01 |
| COMI.CA | 2024-09-30 | week | naive-range | flat | +0.00 | -1.18 | ❌ | 1.18 | ✅ |  | matured 2024-10-08 |
| COMI.CA | 2024-09-30 | month | naive-range | flat | +0.00 | -5.63 | ❌ | 5.63 | ✅ |  | matured 2024-10-30 |
| ETEL.CA | 2024-09-30 | day | 2-family-ensemble | up | +1.89 | +1.39 | ✅ | 0.50 | ✅ |  | matured 2024-10-01 |
| ETEL.CA | 2024-09-30 | week | 2-family-ensemble | up | +7.92 | -0.77 | ❌ | 8.69 | ❌ |  | matured 2024-10-08 |
| ETEL.CA | 2024-09-30 | month | 2-family-ensemble | up | +8.46 | -1.39 | ❌ | 9.85 | ❌ |  | matured 2024-10-30 |
| ETEL.CA | 2024-09-30 | day | kronos-alone | up | +2.70 | +1.39 | ✅ | 1.31 | ✅ |  | matured 2024-10-01 |
| ETEL.CA | 2024-09-30 | week | kronos-alone | up | +12.00 | -0.77 | ❌ | 12.77 | ❌ |  | matured 2024-10-08 |
| ETEL.CA | 2024-09-30 | month | kronos-alone | up | +11.11 | -1.39 | ❌ | 12.50 | ❌ |  | matured 2024-10-30 |
| ETEL.CA | 2024-09-30 | day | family-technicals | flat | -0.36 | +1.39 | ❌ | 1.75 | ✅ |  | matured 2024-10-01 |
| ETEL.CA | 2024-09-30 | week | family-technicals | flat | -0.63 | -0.77 | ❌ | 0.14 | ✅ |  | matured 2024-10-08 |
| ETEL.CA | 2024-09-30 | month | family-technicals | down | -1.36 | -1.39 | ✅ | 0.03 | ✅ |  | matured 2024-10-30 |
| ETEL.CA | 2024-09-30 | day | buy-and-hold | flat | +0.00 | +1.39 | ❌ | 1.39 | ✅ |  | matured 2024-10-01 |
| ETEL.CA | 2024-09-30 | week | buy-and-hold | flat | +0.00 | -0.77 | ❌ | 0.77 | ✅ |  | matured 2024-10-08 |
| ETEL.CA | 2024-09-30 | month | buy-and-hold | flat | +0.00 | -1.39 | ❌ | 1.39 | ✅ |  | matured 2024-10-30 |
| ETEL.CA | 2024-09-30 | day | naive-range | flat | +0.00 | +1.39 | ❌ | 1.39 | ✅ |  | matured 2024-10-01 |
| ETEL.CA | 2024-09-30 | week | naive-range | flat | +0.00 | -0.77 | ❌ | 0.77 | ✅ |  | matured 2024-10-08 |
| ETEL.CA | 2024-09-30 | month | naive-range | flat | +0.00 | -1.39 | ❌ | 1.39 | ✅ |  | matured 2024-10-30 |
| HRHO.CA | 2024-09-30 | day | 2-family-ensemble | down | -2.42 | +1.96 | ❌ | 4.38 | ❌ |  | matured 2024-10-01 |
| HRHO.CA | 2024-09-30 | week | 2-family-ensemble | down | -8.35 | -4.09 | ✅ | 4.26 | ✅ |  | matured 2024-10-08 |
| HRHO.CA | 2024-09-30 | month | 2-family-ensemble | down | -16.10 | -10.63 | ✅ | 5.47 | ✅ |  | matured 2024-10-30 |
| HRHO.CA | 2024-09-30 | day | kronos-alone | down | -2.93 | +1.96 | ❌ | 4.89 | ❌ |  | matured 2024-10-01 |
| HRHO.CA | 2024-09-30 | week | kronos-alone | down | -10.85 | -4.09 | ✅ | 6.76 | ❌ |  | matured 2024-10-08 |
| HRHO.CA | 2024-09-30 | month | kronos-alone | down | -19.81 | -10.63 | ✅ | 9.18 | ❌ |  | matured 2024-10-30 |
| HRHO.CA | 2024-09-30 | day | family-technicals | flat | -0.53 | +1.96 | ❌ | 2.49 | ✅ |  | matured 2024-10-01 |
| HRHO.CA | 2024-09-30 | week | family-technicals | down | -0.92 | -4.09 | ✅ | 3.17 | ✅ |  | matured 2024-10-08 |
| HRHO.CA | 2024-09-30 | month | family-technicals | down | -1.98 | -10.63 | ✅ | 8.65 | ✅ |  | matured 2024-10-30 |
| HRHO.CA | 2024-09-30 | day | buy-and-hold | flat | +0.00 | +1.96 | ❌ | 1.96 | ✅ |  | matured 2024-10-01 |
| HRHO.CA | 2024-09-30 | week | buy-and-hold | flat | +0.00 | -4.09 | ❌ | 4.09 | ✅ |  | matured 2024-10-08 |
| HRHO.CA | 2024-09-30 | month | buy-and-hold | flat | +0.00 | -10.63 | ❌ | 10.63 | ✅ |  | matured 2024-10-30 |
| HRHO.CA | 2024-09-30 | day | naive-range | flat | +0.00 | +1.96 | ❌ | 1.96 | ✅ |  | matured 2024-10-01 |
| HRHO.CA | 2024-09-30 | week | naive-range | flat | +0.00 | -4.09 | ❌ | 4.09 | ✅ |  | matured 2024-10-08 |
| HRHO.CA | 2024-09-30 | month | naive-range | flat | +0.00 | -10.63 | ❌ | 10.63 | ✅ |  | matured 2024-10-30 |
| NVDA | 2024-09-30 | day | 2-family-ensemble | down | -1.96 | -3.66 | ✅ | 1.70 | ✅ |  | matured 2024-10-01 |
| NVDA | 2024-09-30 | week | 2-family-ensemble | down | -15.04 | +5.17 | ❌ | 20.21 | ❌ |  | matured 2024-10-07 |
| NVDA | 2024-09-30 | month | 2-family-ensemble | down | -26.30 | +16.31 | ❌ | 42.61 | ❌ |  | matured 2024-10-29 |
| NVDA | 2024-09-30 | day | kronos-alone | down | -3.10 | -3.66 | ✅ | 0.56 | ✅ |  | matured 2024-10-01 |
| NVDA | 2024-09-30 | week | kronos-alone | down | -21.95 | +5.17 | ❌ | 27.12 | ❌ |  | matured 2024-10-07 |
| NVDA | 2024-09-30 | month | kronos-alone | down | -35.51 | +16.31 | ❌ | 51.82 | ❌ |  | matured 2024-10-29 |
| NVDA | 2024-09-30 | day | family-technicals | up | +0.94 | -3.66 | ❌ | 4.60 | ✅ |  | matured 2024-10-01 |
| NVDA | 2024-09-30 | week | family-technicals | up | +1.63 | +5.17 | ✅ | 3.54 | ✅ |  | matured 2024-10-07 |
| NVDA | 2024-09-30 | month | family-technicals | up | +3.53 | +16.31 | ✅ | 12.78 | ✅ |  | matured 2024-10-29 |
| NVDA | 2024-09-30 | day | buy-and-hold | flat | +0.00 | -3.66 | ❌ | 3.66 | ✅ |  | matured 2024-10-01 |
| NVDA | 2024-09-30 | week | buy-and-hold | flat | +0.00 | +5.17 | ❌ | 5.17 | ✅ |  | matured 2024-10-07 |
| NVDA | 2024-09-30 | month | buy-and-hold | flat | +0.00 | +16.31 | ❌ | 16.31 | ✅ |  | matured 2024-10-29 |
| NVDA | 2024-09-30 | day | index-baseline | flat | +0.00 | -0.93 | ❌ | 0.93 | ❌ |  | matured 2024-10-01 |
| NVDA | 2024-09-30 | week | index-baseline | flat | +0.00 | -1.15 | ❌ | 1.15 | ❌ |  | matured 2024-10-07 |
| NVDA | 2024-09-30 | month | index-baseline | flat | +0.00 | +1.22 | ❌ | 1.22 | ❌ |  | matured 2024-10-29 |
| NVDA | 2024-09-30 | day | naive-range | flat | +0.00 | -3.66 | ❌ | 3.66 | ✅ |  | matured 2024-10-01 |
| NVDA | 2024-09-30 | week | naive-range | flat | +0.00 | +5.17 | ❌ | 5.17 | ✅ |  | matured 2024-10-07 |
| NVDA | 2024-09-30 | month | naive-range | flat | +0.00 | +16.31 | ❌ | 16.31 | ✅ |  | matured 2024-10-29 |
| SWDY.CA | 2024-09-30 | day | 2-family-ensemble | flat | -0.63 | +5.05 | ❌ | 5.68 | ✅ |  | matured 2024-10-01 |
| SWDY.CA | 2024-09-30 | week | 2-family-ensemble | down | -12.69 | +30.34 | ❌ | 43.03 | ❌ |  | matured 2024-10-08 |
| SWDY.CA | 2024-09-30 | month | 2-family-ensemble | down | -36.87 | +20.12 | ❌ | 56.99 | ❌ |  | matured 2024-10-30 |
| SWDY.CA | 2024-09-30 | day | kronos-alone | flat | -0.72 | +5.05 | ❌ | 5.77 | ✅ |  | matured 2024-10-01 |
| SWDY.CA | 2024-09-30 | week | kronos-alone | down | -16.66 | +30.34 | ❌ | 47.00 | ❌ |  | matured 2024-10-08 |
| SWDY.CA | 2024-09-30 | month | kronos-alone | down | -50.73 | +20.12 | ❌ | 70.85 | ❌ |  | matured 2024-10-30 |
| SWDY.CA | 2024-09-30 | day | family-technicals | flat | -0.22 | +5.05 | ❌ | 5.27 | ✅ |  | matured 2024-10-01 |
| SWDY.CA | 2024-09-30 | week | family-technicals | flat | -0.38 | +30.34 | ❌ | 30.72 | ❌ |  | matured 2024-10-08 |
| SWDY.CA | 2024-09-30 | month | family-technicals | down | -0.83 | +20.12 | ❌ | 20.95 | ❌ |  | matured 2024-10-30 |
| SWDY.CA | 2024-09-30 | day | buy-and-hold | flat | +0.00 | +5.05 | ❌ | 5.05 | ✅ |  | matured 2024-10-01 |
| SWDY.CA | 2024-09-30 | week | buy-and-hold | flat | +0.00 | +30.34 | ❌ | 30.34 | ❌ |  | matured 2024-10-08 |
| SWDY.CA | 2024-09-30 | month | buy-and-hold | flat | +0.00 | +20.12 | ❌ | 20.12 | ✅ |  | matured 2024-10-30 |
| SWDY.CA | 2024-09-30 | day | naive-range | flat | +0.00 | +5.05 | ❌ | 5.05 | ✅ |  | matured 2024-10-01 |
| SWDY.CA | 2024-09-30 | week | naive-range | flat | +0.00 | +30.34 | ❌ | 30.34 | ❌ |  | matured 2024-10-08 |
| SWDY.CA | 2024-09-30 | month | naive-range | flat | +0.00 | +20.12 | ❌ | 20.12 | ✅ |  | matured 2024-10-30 |
| TMGH.CA | 2024-09-30 | day | 2-family-ensemble | down | -1.52 | -1.10 | ✅ | 0.42 | ✅ |  | matured 2024-10-01 |
| TMGH.CA | 2024-09-30 | week | 2-family-ensemble | up | +7.66 | -9.04 | ❌ | 16.70 | ❌ |  | matured 2024-10-08 |
| TMGH.CA | 2024-09-30 | month | 2-family-ensemble | down | -8.53 | -8.16 | ✅ | 0.37 | ✅ |  | matured 2024-10-30 |
| TMGH.CA | 2024-09-30 | day | kronos-alone | down | -2.12 | -1.10 | ✅ | 1.02 | ✅ |  | matured 2024-10-01 |
| TMGH.CA | 2024-09-30 | week | kronos-alone | up | +10.64 | -9.04 | ❌ | 19.68 | ❌ |  | matured 2024-10-08 |
| TMGH.CA | 2024-09-30 | month | kronos-alone | down | -11.00 | -8.16 | ✅ | 2.84 | ❌ |  | matured 2024-10-30 |
| TMGH.CA | 2024-09-30 | day | family-technicals | flat | +0.20 | -1.10 | ❌ | 1.30 | ✅ |  | matured 2024-10-01 |
| TMGH.CA | 2024-09-30 | week | family-technicals | flat | +0.35 | -9.04 | ❌ | 9.39 | ❌ |  | matured 2024-10-08 |
| TMGH.CA | 2024-09-30 | month | family-technicals | up | +0.75 | -8.16 | ❌ | 8.91 | ✅ |  | matured 2024-10-30 |
| TMGH.CA | 2024-09-30 | day | buy-and-hold | flat | +0.00 | -1.10 | ❌ | 1.10 | ✅ |  | matured 2024-10-01 |
| TMGH.CA | 2024-09-30 | week | buy-and-hold | flat | +0.00 | -9.04 | ❌ | 9.04 | ❌ |  | matured 2024-10-08 |
| TMGH.CA | 2024-09-30 | month | buy-and-hold | flat | +0.00 | -8.16 | ❌ | 8.16 | ✅ |  | matured 2024-10-30 |
| TMGH.CA | 2024-09-30 | day | naive-range | flat | +0.00 | -1.10 | ❌ | 1.10 | ✅ |  | matured 2024-10-01 |
| TMGH.CA | 2024-09-30 | week | naive-range | flat | +0.00 | -9.04 | ❌ | 9.04 | ❌ |  | matured 2024-10-08 |
| TMGH.CA | 2024-09-30 | month | naive-range | flat | +0.00 | -8.16 | ❌ | 8.16 | ✅ |  | matured 2024-10-30 |
| COMI.CA | 2024-12-31 | day | 2-family-ensemble | up | +0.99 | +0.78 | ✅ | 0.21 | ✅ |  | matured 2025-01-02 |
| COMI.CA | 2024-12-31 | week | 2-family-ensemble | up | +3.34 | -1.27 | ❌ | 4.61 | ❌ |  | matured 2025-01-09 |
| COMI.CA | 2024-12-31 | month | 2-family-ensemble | up | +7.28 | -2.74 | ❌ | 10.02 | ❌ |  | matured 2025-02-02 |
| COMI.CA | 2024-12-31 | day | kronos-alone | up | +1.37 | +0.78 | ✅ | 0.59 | ✅ |  | matured 2025-01-02 |
| COMI.CA | 2024-12-31 | week | kronos-alone | up | +4.46 | -1.27 | ❌ | 5.73 | ❌ |  | matured 2025-01-09 |
| COMI.CA | 2024-12-31 | month | kronos-alone | up | +9.36 | -2.74 | ❌ | 12.10 | ❌ |  | matured 2025-02-02 |
| COMI.CA | 2024-12-31 | day | family-technicals | flat | -0.13 | +0.78 | ❌ | 0.91 | ✅ |  | matured 2025-01-02 |
| COMI.CA | 2024-12-31 | week | family-technicals | flat | -0.22 | -1.27 | ❌ | 1.05 | ✅ |  | matured 2025-01-09 |
| COMI.CA | 2024-12-31 | month | family-technicals | flat | -0.48 | -2.74 | ❌ | 2.26 | ✅ |  | matured 2025-02-02 |
| COMI.CA | 2024-12-31 | day | buy-and-hold | flat | +0.00 | +0.78 | ❌ | 0.78 | ✅ |  | matured 2025-01-02 |
| COMI.CA | 2024-12-31 | week | buy-and-hold | flat | +0.00 | -1.27 | ❌ | 1.27 | ✅ |  | matured 2025-01-09 |
| COMI.CA | 2024-12-31 | month | buy-and-hold | flat | +0.00 | -2.74 | ❌ | 2.74 | ✅ |  | matured 2025-02-02 |
| COMI.CA | 2024-12-31 | day | naive-range | flat | +0.00 | +0.78 | ❌ | 0.78 | ✅ |  | matured 2025-01-02 |
| COMI.CA | 2024-12-31 | week | naive-range | flat | +0.00 | -1.27 | ❌ | 1.27 | ✅ |  | matured 2025-01-09 |
| COMI.CA | 2024-12-31 | month | naive-range | flat | +0.00 | -2.74 | ❌ | 2.74 | ✅ |  | matured 2025-02-02 |
| ETEL.CA | 2024-12-31 | day | 2-family-ensemble | flat | -0.45 | +4.50 | ❌ | 4.95 | ❌ |  | matured 2025-01-02 |
| ETEL.CA | 2024-12-31 | week | 2-family-ensemble | down | -0.95 | +6.37 | ❌ | 7.32 | ❌ |  | matured 2025-01-09 |
| ETEL.CA | 2024-12-31 | month | 2-family-ensemble | flat | +0.00 | +1.93 | ❌ | 1.93 | ✅ |  | matured 2025-02-02 |
| ETEL.CA | 2024-12-31 | day | kronos-alone | flat | -0.39 | +4.50 | ❌ | 4.89 | ❌ |  | matured 2025-01-02 |
| ETEL.CA | 2024-12-31 | week | kronos-alone | down | -0.93 | +6.37 | ❌ | 7.30 | ❌ |  | matured 2025-01-09 |
| ETEL.CA | 2024-12-31 | month | kronos-alone | flat | +0.48 | +1.93 | ❌ | 1.45 | ✅ |  | matured 2025-02-02 |
| ETEL.CA | 2024-12-31 | day | family-technicals | flat | -0.41 | +4.50 | ❌ | 4.91 | ❌ |  | matured 2025-01-02 |
| ETEL.CA | 2024-12-31 | week | family-technicals | flat | -0.70 | +6.37 | ❌ | 7.07 | ❌ |  | matured 2025-01-09 |
| ETEL.CA | 2024-12-31 | month | family-technicals | down | -1.52 | +1.93 | ❌ | 3.45 | ✅ |  | matured 2025-02-02 |
| ETEL.CA | 2024-12-31 | day | buy-and-hold | flat | +0.00 | +4.50 | ❌ | 4.50 | ❌ |  | matured 2025-01-02 |
| ETEL.CA | 2024-12-31 | week | buy-and-hold | flat | +0.00 | +6.37 | ❌ | 6.37 | ❌ |  | matured 2025-01-09 |
| ETEL.CA | 2024-12-31 | month | buy-and-hold | flat | +0.00 | +1.93 | ❌ | 1.93 | ✅ |  | matured 2025-02-02 |
| ETEL.CA | 2024-12-31 | day | naive-range | flat | +0.00 | +4.50 | ❌ | 4.50 | ❌ |  | matured 2025-01-02 |
| ETEL.CA | 2024-12-31 | week | naive-range | flat | +0.00 | +6.37 | ❌ | 6.37 | ❌ |  | matured 2025-01-09 |
| ETEL.CA | 2024-12-31 | month | naive-range | flat | +0.00 | +1.93 | ❌ | 1.93 | ✅ |  | matured 2025-02-02 |
| HRHO.CA | 2024-12-31 | day | 2-family-ensemble | down | -0.79 | +1.11 | ❌ | 1.90 | ✅ |  | matured 2025-01-02 |
| HRHO.CA | 2024-12-31 | week | 2-family-ensemble | up | +2.37 | +0.00 | ❌ | 2.37 | ✅ |  | matured 2025-01-09 |
| HRHO.CA | 2024-12-31 | month | 2-family-ensemble | up | +7.06 | +4.83 | ✅ | 2.23 | ✅ |  | matured 2025-02-02 |
| HRHO.CA | 2024-12-31 | day | kronos-alone | down | -0.82 | +1.11 | ❌ | 1.93 | ❌ |  | matured 2025-01-02 |
| HRHO.CA | 2024-12-31 | week | kronos-alone | up | +3.40 | +0.00 | ❌ | 3.40 | ❌ |  | matured 2025-01-09 |
| HRHO.CA | 2024-12-31 | month | kronos-alone | up | +9.42 | +4.83 | ✅ | 4.59 | ❌ |  | matured 2025-02-02 |
| HRHO.CA | 2024-12-31 | day | family-technicals | flat | -0.43 | +1.11 | ❌ | 1.54 | ✅ |  | matured 2025-01-02 |
| HRHO.CA | 2024-12-31 | week | family-technicals | flat | -0.75 | +0.00 | ✅ | 0.75 | ✅ |  | matured 2025-01-09 |
| HRHO.CA | 2024-12-31 | month | family-technicals | down | -1.61 | +4.83 | ❌ | 6.44 | ✅ |  | matured 2025-02-02 |
| HRHO.CA | 2024-12-31 | day | buy-and-hold | flat | +0.00 | +1.11 | ❌ | 1.11 | ✅ |  | matured 2025-01-02 |
| HRHO.CA | 2024-12-31 | week | buy-and-hold | flat | +0.00 | +0.00 | ✅ | 0.00 | ✅ |  | matured 2025-01-09 |
| HRHO.CA | 2024-12-31 | month | buy-and-hold | flat | +0.00 | +4.83 | ❌ | 4.83 | ✅ |  | matured 2025-02-02 |
| HRHO.CA | 2024-12-31 | day | naive-range | flat | +0.00 | +1.11 | ❌ | 1.11 | ✅ |  | matured 2025-01-02 |
| HRHO.CA | 2024-12-31 | week | naive-range | flat | +0.00 | +0.00 | ✅ | 0.00 | ✅ |  | matured 2025-01-09 |
| HRHO.CA | 2024-12-31 | month | naive-range | flat | +0.00 | +4.83 | ❌ | 4.83 | ✅ |  | matured 2025-02-02 |
| NVDA | 2024-12-31 | day | 2-family-ensemble | flat | +0.33 | +2.99 | ❌ | 2.66 | ✅ |  | matured 2025-01-02 |
| NVDA | 2024-12-31 | week | 2-family-ensemble | down | -4.76 | +4.33 | ❌ | 9.09 | ❌ |  | matured 2025-01-08 |
| NVDA | 2024-12-31 | month | 2-family-ensemble | down | -15.81 | -13.13 | ✅ | 2.68 | ✅ |  | matured 2025-02-03 |
| NVDA | 2024-12-31 | day | kronos-alone | flat | +0.34 | +2.99 | ❌ | 2.65 | ❌ |  | matured 2025-01-02 |
| NVDA | 2024-12-31 | week | kronos-alone | down | -6.31 | +4.33 | ❌ | 10.64 | ❌ |  | matured 2025-01-08 |
| NVDA | 2024-12-31 | month | kronos-alone | down | -21.14 | -13.13 | ✅ | 8.01 | ❌ |  | matured 2025-02-03 |
| NVDA | 2024-12-31 | day | family-technicals | flat | +0.18 | +2.99 | ❌ | 2.81 | ✅ |  | matured 2025-01-02 |
| NVDA | 2024-12-31 | week | family-technicals | flat | +0.30 | +4.33 | ❌ | 4.03 | ✅ |  | matured 2025-01-08 |
| NVDA | 2024-12-31 | month | family-technicals | flat | +0.66 | -13.13 | ❌ | 13.79 | ❌ |  | matured 2025-02-03 |
| NVDA | 2024-12-31 | day | buy-and-hold | flat | +0.00 | +2.99 | ❌ | 2.99 | ❌ |  | matured 2025-01-02 |
| NVDA | 2024-12-31 | week | buy-and-hold | flat | +0.00 | +4.33 | ❌ | 4.33 | ✅ |  | matured 2025-01-08 |
| NVDA | 2024-12-31 | month | buy-and-hold | flat | +0.00 | -13.13 | ❌ | 13.13 | ❌ |  | matured 2025-02-03 |
| NVDA | 2024-12-31 | day | index-baseline | flat | +0.00 | -0.22 | ✅ | 0.22 | ❌ |  | matured 2025-01-02 |
| NVDA | 2024-12-31 | week | index-baseline | flat | +0.00 | +0.62 | ✅ | 0.62 | ❌ |  | matured 2025-01-08 |
| NVDA | 2024-12-31 | month | index-baseline | flat | +0.00 | +1.92 | ❌ | 1.92 | ❌ |  | matured 2025-02-03 |
| NVDA | 2024-12-31 | day | naive-range | flat | +0.00 | +2.99 | ❌ | 2.99 | ❌ |  | matured 2025-01-02 |
| NVDA | 2024-12-31 | week | naive-range | flat | +0.00 | +4.33 | ❌ | 4.33 | ✅ |  | matured 2025-01-08 |
| NVDA | 2024-12-31 | month | naive-range | flat | +0.00 | -13.13 | ❌ | 13.13 | ✅ |  | matured 2025-02-03 |
| SWDY.CA | 2024-12-31 | day | 2-family-ensemble | up | +1.44 | +1.48 | ✅ | 0.04 | ✅ |  | matured 2025-01-02 |
| SWDY.CA | 2024-12-31 | week | 2-family-ensemble | up | +1.24 | +3.72 | ✅ | 2.48 | ✅ |  | matured 2025-01-09 |
| SWDY.CA | 2024-12-31 | month | 2-family-ensemble | down | -14.99 | +6.76 | ❌ | 21.75 | ❌ |  | matured 2025-02-02 |
| SWDY.CA | 2024-12-31 | day | kronos-alone | up | +1.86 | +1.48 | ✅ | 0.38 | ✅ |  | matured 2025-01-02 |
| SWDY.CA | 2024-12-31 | week | kronos-alone | up | +1.53 | +3.72 | ✅ | 2.19 | ✅ |  | matured 2025-01-09 |
| SWDY.CA | 2024-12-31 | month | kronos-alone | down | -19.79 | +6.76 | ❌ | 26.55 | ❌ |  | matured 2025-02-02 |
| SWDY.CA | 2024-12-31 | day | family-technicals | flat | +0.12 | +1.48 | ❌ | 1.36 | ✅ |  | matured 2025-01-02 |
| SWDY.CA | 2024-12-31 | week | family-technicals | flat | +0.20 | +3.72 | ❌ | 3.52 | ✅ |  | matured 2025-01-09 |
| SWDY.CA | 2024-12-31 | month | family-technicals | flat | +0.43 | +6.76 | ❌ | 6.33 | ✅ |  | matured 2025-02-02 |
| SWDY.CA | 2024-12-31 | day | buy-and-hold | flat | +0.00 | +1.48 | ❌ | 1.48 | ✅ |  | matured 2025-01-02 |
| SWDY.CA | 2024-12-31 | week | buy-and-hold | flat | +0.00 | +3.72 | ❌ | 3.72 | ✅ |  | matured 2025-01-09 |
| SWDY.CA | 2024-12-31 | month | buy-and-hold | flat | +0.00 | +6.76 | ❌ | 6.76 | ✅ |  | matured 2025-02-02 |
| SWDY.CA | 2024-12-31 | day | naive-range | flat | +0.00 | +1.48 | ❌ | 1.48 | ✅ |  | matured 2025-01-02 |
| SWDY.CA | 2024-12-31 | week | naive-range | flat | +0.00 | +3.72 | ❌ | 3.72 | ✅ |  | matured 2025-01-09 |
| SWDY.CA | 2024-12-31 | month | naive-range | flat | +0.00 | +6.76 | ❌ | 6.76 | ✅ |  | matured 2025-02-02 |
| TMGH.CA | 2024-12-31 | day | 2-family-ensemble | up | +3.19 | -1.34 | ❌ | 4.53 | ❌ |  | matured 2025-01-02 |
| TMGH.CA | 2024-12-31 | week | 2-family-ensemble | up | +6.20 | -6.25 | ❌ | 12.45 | ❌ |  | matured 2025-01-09 |
| TMGH.CA | 2024-12-31 | month | 2-family-ensemble | up | +10.80 | -3.57 | ❌ | 14.37 | ❌ |  | matured 2025-02-02 |
| TMGH.CA | 2024-12-31 | day | kronos-alone | up | +4.60 | -1.34 | ❌ | 5.94 | ❌ |  | matured 2025-01-02 |
| TMGH.CA | 2024-12-31 | week | kronos-alone | up | +8.80 | -6.25 | ❌ | 15.05 | ❌ |  | matured 2025-01-09 |
| TMGH.CA | 2024-12-31 | month | kronos-alone | up | +14.18 | -3.57 | ❌ | 17.75 | ❌ |  | matured 2025-02-02 |
| TMGH.CA | 2024-12-31 | day | family-technicals | flat | -0.46 | -1.34 | ❌ | 0.88 | ✅ |  | matured 2025-01-02 |
| TMGH.CA | 2024-12-31 | week | family-technicals | down | -0.80 | -6.25 | ✅ | 5.45 | ❌ |  | matured 2025-01-09 |
| TMGH.CA | 2024-12-31 | month | family-technicals | down | -1.72 | -3.57 | ✅ | 1.85 | ✅ |  | matured 2025-02-02 |
| TMGH.CA | 2024-12-31 | day | buy-and-hold | flat | +0.00 | -1.34 | ❌ | 1.34 | ✅ |  | matured 2025-01-02 |
| TMGH.CA | 2024-12-31 | week | buy-and-hold | flat | +0.00 | -6.25 | ❌ | 6.25 | ❌ |  | matured 2025-01-09 |
| TMGH.CA | 2024-12-31 | month | buy-and-hold | flat | +0.00 | -3.57 | ❌ | 3.57 | ✅ |  | matured 2025-02-02 |
| TMGH.CA | 2024-12-31 | day | naive-range | flat | +0.00 | -1.34 | ❌ | 1.34 | ✅ |  | matured 2025-01-02 |
| TMGH.CA | 2024-12-31 | week | naive-range | flat | +0.00 | -6.25 | ❌ | 6.25 | ❌ |  | matured 2025-01-09 |
| TMGH.CA | 2024-12-31 | month | naive-range | flat | +0.00 | -3.57 | ❌ | 3.57 | ✅ |  | matured 2025-02-02 |
| COMI.CA | 2025-03-31 | day | 2-family-ensemble | flat | -0.30 | -3.34 | ❌ | 3.04 | ❌ |  | matured 2025-04-03 |
| COMI.CA | 2025-03-31 | week | 2-family-ensemble | up | +1.07 | -7.82 | ❌ | 8.89 | ❌ |  | matured 2025-04-09 |
| COMI.CA | 2025-03-31 | month | 2-family-ensemble | flat | +0.46 | -2.97 | ❌ | 3.43 | ✅ |  | matured 2025-05-07 |
| COMI.CA | 2025-03-31 | day | kronos-alone | flat | -0.36 | -3.34 | ❌ | 2.98 | ❌ |  | matured 2025-04-03 |
| COMI.CA | 2025-03-31 | week | kronos-alone | up | +1.44 | -7.82 | ❌ | 9.26 | ❌ |  | matured 2025-04-09 |
| COMI.CA | 2025-03-31 | month | kronos-alone | flat | +0.65 | -2.97 | ❌ | 3.62 | ❌ |  | matured 2025-05-07 |
| COMI.CA | 2025-03-31 | day | family-technicals | flat | -0.06 | -3.34 | ❌ | 3.28 | ❌ |  | matured 2025-04-03 |
| COMI.CA | 2025-03-31 | week | family-technicals | flat | -0.10 | -7.82 | ❌ | 7.72 | ❌ |  | matured 2025-04-09 |
| COMI.CA | 2025-03-31 | month | family-technicals | flat | -0.22 | -2.97 | ❌ | 2.75 | ✅ |  | matured 2025-05-07 |
| COMI.CA | 2025-03-31 | day | buy-and-hold | flat | +0.00 | -3.34 | ❌ | 3.34 | ❌ |  | matured 2025-04-03 |
| COMI.CA | 2025-03-31 | week | buy-and-hold | flat | +0.00 | -7.82 | ❌ | 7.82 | ❌ |  | matured 2025-04-09 |
| COMI.CA | 2025-03-31 | month | buy-and-hold | flat | +0.00 | -2.97 | ❌ | 2.97 | ✅ |  | matured 2025-05-07 |
| COMI.CA | 2025-03-31 | day | naive-range | flat | +0.00 | -3.34 | ❌ | 3.34 | ❌ |  | matured 2025-04-03 |
| COMI.CA | 2025-03-31 | week | naive-range | flat | +0.00 | -7.82 | ❌ | 7.82 | ❌ |  | matured 2025-04-09 |
| COMI.CA | 2025-03-31 | month | naive-range | flat | +0.00 | -2.97 | ❌ | 2.97 | ✅ |  | matured 2025-05-07 |
| ETEL.CA | 2025-03-31 | day | 2-family-ensemble | flat | -0.37 | -0.71 | ✅ | 0.34 | ✅ |  | matured 2025-04-03 |
| ETEL.CA | 2025-03-31 | week | 2-family-ensemble | up | +1.87 | -4.33 | ❌ | 6.20 | ❌ |  | matured 2025-04-09 |
| ETEL.CA | 2025-03-31 | month | 2-family-ensemble | up | +2.07 | -0.28 | ❌ | 2.35 | ✅ |  | matured 2025-05-07 |
| ETEL.CA | 2025-03-31 | day | kronos-alone | flat | -0.43 | -0.71 | ✅ | 0.28 | ✅ |  | matured 2025-04-03 |
| ETEL.CA | 2025-03-31 | week | kronos-alone | up | +2.53 | -4.33 | ❌ | 6.86 | ❌ |  | matured 2025-04-09 |
| ETEL.CA | 2025-03-31 | month | kronos-alone | up | +2.77 | -0.28 | ❌ | 3.05 | ❌ |  | matured 2025-05-07 |
| ETEL.CA | 2025-03-31 | day | family-technicals | flat | -0.13 | -0.71 | ✅ | 0.58 | ✅ |  | matured 2025-04-03 |
| ETEL.CA | 2025-03-31 | week | family-technicals | flat | -0.23 | -4.33 | ❌ | 4.10 | ❌ |  | matured 2025-04-09 |
| ETEL.CA | 2025-03-31 | month | family-technicals | flat | -0.49 | -0.28 | ✅ | 0.21 | ✅ |  | matured 2025-05-07 |
| ETEL.CA | 2025-03-31 | day | buy-and-hold | flat | +0.00 | -0.71 | ✅ | 0.71 | ✅ |  | matured 2025-04-03 |
| ETEL.CA | 2025-03-31 | week | buy-and-hold | flat | +0.00 | -4.33 | ❌ | 4.33 | ❌ |  | matured 2025-04-09 |
| ETEL.CA | 2025-03-31 | month | buy-and-hold | flat | +0.00 | -0.28 | ✅ | 0.28 | ✅ |  | matured 2025-05-07 |
| ETEL.CA | 2025-03-31 | day | naive-range | flat | +0.00 | -0.71 | ✅ | 0.71 | ✅ |  | matured 2025-04-03 |
| ETEL.CA | 2025-03-31 | week | naive-range | flat | +0.00 | -4.33 | ❌ | 4.33 | ❌ |  | matured 2025-04-09 |
| ETEL.CA | 2025-03-31 | month | naive-range | flat | +0.00 | -0.28 | ✅ | 0.28 | ✅ |  | matured 2025-05-07 |
| HRHO.CA | 2025-03-31 | day | 2-family-ensemble | down | -2.74 | +0.00 | ❌ | 2.74 | ✅ |  | matured 2025-04-03 |
| HRHO.CA | 2025-03-31 | week | 2-family-ensemble | down | -7.78 | -5.05 | ✅ | 2.73 | ✅ |  | matured 2025-04-09 |
| HRHO.CA | 2025-03-31 | month | 2-family-ensemble | down | -14.70 | +1.82 | ❌ | 16.52 | ❌ |  | matured 2025-05-07 |
| HRHO.CA | 2025-03-31 | day | kronos-alone | down | -3.52 | +0.00 | ❌ | 3.52 | ✅ |  | matured 2025-04-03 |
| HRHO.CA | 2025-03-31 | week | kronos-alone | down | -10.95 | -5.05 | ✅ | 5.90 | ❌ |  | matured 2025-04-09 |
| HRHO.CA | 2025-03-31 | month | kronos-alone | down | -19.76 | +1.82 | ❌ | 21.58 | ❌ |  | matured 2025-05-07 |
| HRHO.CA | 2025-03-31 | day | family-technicals | flat | -0.22 | +0.00 | ✅ | 0.22 | ✅ |  | matured 2025-04-03 |
| HRHO.CA | 2025-03-31 | week | family-technicals | flat | -0.38 | -5.05 | ❌ | 4.67 | ❌ |  | matured 2025-04-09 |
| HRHO.CA | 2025-03-31 | month | family-technicals | down | -0.82 | +1.82 | ❌ | 2.64 | ✅ |  | matured 2025-05-07 |
| HRHO.CA | 2025-03-31 | day | buy-and-hold | flat | +0.00 | +0.00 | ✅ | 0.00 | ✅ |  | matured 2025-04-03 |
| HRHO.CA | 2025-03-31 | week | buy-and-hold | flat | +0.00 | -5.05 | ❌ | 5.05 | ❌ |  | matured 2025-04-09 |
| HRHO.CA | 2025-03-31 | month | buy-and-hold | flat | +0.00 | +1.82 | ❌ | 1.82 | ✅ |  | matured 2025-05-07 |
| HRHO.CA | 2025-03-31 | day | naive-range | flat | +0.00 | +0.00 | ✅ | 0.00 | ✅ |  | matured 2025-04-03 |
| HRHO.CA | 2025-03-31 | week | naive-range | flat | +0.00 | -5.05 | ❌ | 5.05 | ✅ |  | matured 2025-04-09 |
| HRHO.CA | 2025-03-31 | month | naive-range | flat | +0.00 | +1.82 | ❌ | 1.82 | ✅ |  | matured 2025-05-07 |
| NVDA | 2025-03-31 | day | 2-family-ensemble | up | +3.51 | +1.63 | ✅ | 1.88 | ✅ |  | matured 2025-04-01 |
| NVDA | 2025-03-31 | week | 2-family-ensemble | up | +10.16 | -9.91 | ❌ | 20.07 | ❌ |  | matured 2025-04-07 |
| NVDA | 2025-03-31 | month | 2-family-ensemble | up | +13.92 | +0.50 | ❌ | 13.42 | ✅ |  | matured 2025-04-30 |
| NVDA | 2025-03-31 | day | kronos-alone | up | +5.01 | +1.63 | ✅ | 3.38 | ❌ |  | matured 2025-04-01 |
| NVDA | 2025-03-31 | week | kronos-alone | up | +13.68 | -9.91 | ❌ | 23.59 | ❌ |  | matured 2025-04-07 |
| NVDA | 2025-03-31 | month | kronos-alone | up | +18.36 | +0.50 | ❌ | 17.86 | ❌ |  | matured 2025-04-30 |
| NVDA | 2025-03-31 | day | family-technicals | flat | -0.66 | +1.63 | ❌ | 2.29 | ✅ |  | matured 2025-04-01 |
| NVDA | 2025-03-31 | week | family-technicals | down | -1.14 | -9.91 | ✅ | 8.77 | ✅ |  | matured 2025-04-07 |
| NVDA | 2025-03-31 | month | family-technicals | down | -2.47 | +0.50 | ❌ | 2.97 | ✅ |  | matured 2025-04-30 |
| NVDA | 2025-03-31 | day | buy-and-hold | flat | +0.00 | +1.63 | ❌ | 1.63 | ✅ |  | matured 2025-04-01 |
| NVDA | 2025-03-31 | week | buy-and-hold | flat | +0.00 | -9.91 | ❌ | 9.91 | ❌ |  | matured 2025-04-07 |
| NVDA | 2025-03-31 | month | buy-and-hold | flat | +0.00 | +0.50 | ✅ | 0.50 | ✅ |  | matured 2025-04-30 |
| NVDA | 2025-03-31 | day | index-baseline | flat | +0.00 | +0.38 | ✅ | 0.38 | ❌ |  | matured 2025-04-01 |
| NVDA | 2025-03-31 | week | index-baseline | flat | +0.00 | -9.79 | ❌ | 9.79 | ❌ |  | matured 2025-04-07 |
| NVDA | 2025-03-31 | month | index-baseline | flat | +0.00 | -0.76 | ❌ | 0.76 | ❌ |  | matured 2025-04-30 |
| NVDA | 2025-03-31 | day | naive-range | flat | +0.00 | +1.63 | ❌ | 1.63 | ✅ |  | matured 2025-04-01 |
| NVDA | 2025-03-31 | week | naive-range | flat | +0.00 | -9.91 | ❌ | 9.91 | ✅ |  | matured 2025-04-07 |
| NVDA | 2025-03-31 | month | naive-range | flat | +0.00 | +0.50 | ✅ | 0.50 | ✅ |  | matured 2025-04-30 |
| SWDY.CA | 2025-03-31 | day | 2-family-ensemble | flat | -0.64 | -0.11 | ✅ | 0.53 | ✅ |  | matured 2025-04-03 |
| SWDY.CA | 2025-03-31 | week | 2-family-ensemble | flat | -0.23 | -6.38 | ❌ | 6.15 | ❌ |  | matured 2025-04-09 |
| SWDY.CA | 2025-03-31 | month | 2-family-ensemble | down | -3.84 | -0.77 | ✅ | 3.07 | ✅ |  | matured 2025-05-07 |
| SWDY.CA | 2025-03-31 | day | kronos-alone | flat | -0.61 | -0.11 | ✅ | 0.50 | ✅ |  | matured 2025-04-03 |
| SWDY.CA | 2025-03-31 | week | kronos-alone | flat | +0.03 | -6.38 | ❌ | 6.41 | ❌ |  | matured 2025-04-09 |
| SWDY.CA | 2025-03-31 | month | kronos-alone | down | -4.33 | -0.77 | ✅ | 3.56 | ✅ |  | matured 2025-05-07 |
| SWDY.CA | 2025-03-31 | day | family-technicals | flat | -0.44 | -0.11 | ✅ | 0.33 | ✅ |  | matured 2025-04-03 |
| SWDY.CA | 2025-03-31 | week | family-technicals | down | -0.76 | -6.38 | ✅ | 5.62 | ❌ |  | matured 2025-04-09 |
| SWDY.CA | 2025-03-31 | month | family-technicals | down | -1.64 | -0.77 | ✅ | 0.87 | ✅ |  | matured 2025-05-07 |
| SWDY.CA | 2025-03-31 | day | buy-and-hold | flat | +0.00 | -0.11 | ✅ | 0.11 | ✅ |  | matured 2025-04-03 |
| SWDY.CA | 2025-03-31 | week | buy-and-hold | flat | +0.00 | -6.38 | ❌ | 6.38 | ❌ |  | matured 2025-04-09 |
| SWDY.CA | 2025-03-31 | month | buy-and-hold | flat | +0.00 | -0.77 | ❌ | 0.77 | ✅ |  | matured 2025-05-07 |
| SWDY.CA | 2025-03-31 | day | naive-range | flat | +0.00 | -0.11 | ✅ | 0.11 | ✅ |  | matured 2025-04-03 |
| SWDY.CA | 2025-03-31 | week | naive-range | flat | +0.00 | -6.38 | ❌ | 6.38 | ✅ |  | matured 2025-04-09 |
| SWDY.CA | 2025-03-31 | month | naive-range | flat | +0.00 | -0.77 | ❌ | 0.77 | ✅ |  | matured 2025-05-07 |
| TMGH.CA | 2025-03-31 | day | 2-family-ensemble | down | -0.83 | -2.20 | ✅ | 1.37 | ✅ |  | matured 2025-04-03 |
| TMGH.CA | 2025-03-31 | week | 2-family-ensemble | up | +6.05 | -11.68 | ❌ | 17.73 | ❌ |  | matured 2025-04-09 |
| TMGH.CA | 2025-03-31 | month | 2-family-ensemble | up | +13.18 | +0.75 | ✅ | 12.43 | ❌ |  | matured 2025-05-07 |
| TMGH.CA | 2025-03-31 | day | kronos-alone | down | -0.87 | -2.20 | ✅ | 1.33 | ✅ |  | matured 2025-04-03 |
| TMGH.CA | 2025-03-31 | week | kronos-alone | up | +8.65 | -11.68 | ❌ | 20.33 | ❌ |  | matured 2025-04-09 |
| TMGH.CA | 2025-03-31 | month | kronos-alone | up | +18.15 | +0.75 | ✅ | 17.40 | ❌ |  | matured 2025-05-07 |
| TMGH.CA | 2025-03-31 | day | family-technicals | flat | -0.43 | -2.20 | ❌ | 1.77 | ✅ |  | matured 2025-04-03 |
| TMGH.CA | 2025-03-31 | week | family-technicals | down | -0.75 | -11.68 | ✅ | 10.93 | ❌ |  | matured 2025-04-09 |
| TMGH.CA | 2025-03-31 | month | family-technicals | down | -1.62 | +0.75 | ❌ | 2.37 | ✅ |  | matured 2025-05-07 |
| TMGH.CA | 2025-03-31 | day | buy-and-hold | flat | +0.00 | -2.20 | ❌ | 2.20 | ✅ |  | matured 2025-04-03 |
| TMGH.CA | 2025-03-31 | week | buy-and-hold | flat | +0.00 | -11.68 | ❌ | 11.68 | ❌ |  | matured 2025-04-09 |
| TMGH.CA | 2025-03-31 | month | buy-and-hold | flat | +0.00 | +0.75 | ❌ | 0.75 | ✅ |  | matured 2025-05-07 |
| TMGH.CA | 2025-03-31 | day | naive-range | flat | +0.00 | -2.20 | ❌ | 2.20 | ✅ |  | matured 2025-04-03 |
| TMGH.CA | 2025-03-31 | week | naive-range | flat | +0.00 | -11.68 | ❌ | 11.68 | ❌ |  | matured 2025-04-09 |
| TMGH.CA | 2025-03-31 | month | naive-range | flat | +0.00 | +0.75 | ❌ | 0.75 | ✅ |  | matured 2025-05-07 |
| COMI.CA | 2025-06-30 | day | 2-family-ensemble | flat | +0.19 | +0.78 | ❌ | 0.59 | ✅ |  | matured 2025-07-01 |
| COMI.CA | 2025-06-30 | week | 2-family-ensemble | flat | +0.55 | -0.36 | ✅ | 0.91 | ✅ |  | matured 2025-07-09 |
| COMI.CA | 2025-06-30 | month | 2-family-ensemble | down | -0.91 | +11.63 | ❌ | 12.54 | ❌ |  | matured 2025-08-03 |
| COMI.CA | 2025-06-30 | day | kronos-alone | flat | +0.16 | +0.78 | ❌ | 0.62 | ✅ |  | matured 2025-07-01 |
| COMI.CA | 2025-06-30 | week | kronos-alone | flat | +0.58 | -0.36 | ✅ | 0.94 | ✅ |  | matured 2025-07-09 |
| COMI.CA | 2025-06-30 | month | kronos-alone | down | -1.34 | +11.63 | ❌ | 12.97 | ❌ |  | matured 2025-08-03 |
| COMI.CA | 2025-06-30 | day | family-technicals | flat | +0.17 | +0.78 | ❌ | 0.61 | ✅ |  | matured 2025-07-01 |
| COMI.CA | 2025-06-30 | week | family-technicals | flat | +0.29 | -0.36 | ✅ | 0.65 | ✅ |  | matured 2025-07-09 |
| COMI.CA | 2025-06-30 | month | family-technicals | flat | +0.63 | +11.63 | ❌ | 11.00 | ❌ |  | matured 2025-08-03 |
| COMI.CA | 2025-06-30 | day | buy-and-hold | flat | +0.00 | +0.78 | ❌ | 0.78 | ✅ |  | matured 2025-07-01 |
| COMI.CA | 2025-06-30 | week | buy-and-hold | flat | +0.00 | -0.36 | ✅ | 0.36 | ✅ |  | matured 2025-07-09 |
| COMI.CA | 2025-06-30 | month | buy-and-hold | flat | +0.00 | +11.63 | ❌ | 11.63 | ❌ |  | matured 2025-08-03 |
| COMI.CA | 2025-06-30 | day | naive-range | flat | +0.00 | +0.78 | ❌ | 0.78 | ✅ |  | matured 2025-07-01 |
| COMI.CA | 2025-06-30 | week | naive-range | flat | +0.00 | -0.36 | ✅ | 0.36 | ✅ |  | matured 2025-07-09 |
| COMI.CA | 2025-06-30 | month | naive-range | flat | +0.00 | +11.63 | ❌ | 11.63 | ❌ |  | matured 2025-08-03 |
| ETEL.CA | 2025-06-30 | day | 2-family-ensemble | flat | +0.29 | -0.32 | ✅ | 0.61 | ✅ |  | matured 2025-07-01 |
| ETEL.CA | 2025-06-30 | week | 2-family-ensemble | flat | +0.06 | +0.92 | ❌ | 0.86 | ✅ |  | matured 2025-07-09 |
| ETEL.CA | 2025-06-30 | month | 2-family-ensemble | down | -5.45 | +7.89 | ❌ | 13.34 | ❌ |  | matured 2025-08-03 |
| ETEL.CA | 2025-06-30 | day | kronos-alone | flat | +0.31 | -0.32 | ✅ | 0.63 | ✅ |  | matured 2025-07-01 |
| ETEL.CA | 2025-06-30 | week | kronos-alone | flat | -0.04 | +0.92 | ❌ | 0.96 | ✅ |  | matured 2025-07-09 |
| ETEL.CA | 2025-06-30 | month | kronos-alone | down | -7.06 | +7.89 | ❌ | 14.95 | ❌ |  | matured 2025-08-03 |
| ETEL.CA | 2025-06-30 | day | family-technicals | flat | +0.15 | -0.32 | ✅ | 0.47 | ✅ |  | matured 2025-07-01 |
| ETEL.CA | 2025-06-30 | week | family-technicals | flat | +0.27 | +0.92 | ❌ | 0.65 | ✅ |  | matured 2025-07-09 |
| ETEL.CA | 2025-06-30 | month | family-technicals | flat | +0.58 | +7.89 | ❌ | 7.31 | ❌ |  | matured 2025-08-03 |
| ETEL.CA | 2025-06-30 | day | buy-and-hold | flat | +0.00 | -0.32 | ✅ | 0.32 | ✅ |  | matured 2025-07-01 |
| ETEL.CA | 2025-06-30 | week | buy-and-hold | flat | +0.00 | +0.92 | ❌ | 0.92 | ✅ |  | matured 2025-07-09 |
| ETEL.CA | 2025-06-30 | month | buy-and-hold | flat | +0.00 | +7.89 | ❌ | 7.89 | ❌ |  | matured 2025-08-03 |
| ETEL.CA | 2025-06-30 | day | naive-range | flat | +0.00 | -0.32 | ✅ | 0.32 | ✅ |  | matured 2025-07-01 |
| ETEL.CA | 2025-06-30 | week | naive-range | flat | +0.00 | +0.92 | ❌ | 0.92 | ✅ |  | matured 2025-07-09 |
| ETEL.CA | 2025-06-30 | month | naive-range | flat | +0.00 | +7.89 | ❌ | 7.89 | ✅ |  | matured 2025-08-03 |
| HRHO.CA | 2025-06-30 | day | 2-family-ensemble | flat | -0.55 | -1.76 | ❌ | 1.21 | ✅ |  | matured 2025-07-01 |
| HRHO.CA | 2025-06-30 | week | 2-family-ensemble | down | -1.75 | -6.64 | ✅ | 4.89 | ✅ |  | matured 2025-07-09 |
| HRHO.CA | 2025-06-30 | month | 2-family-ensemble | down | -5.51 | -9.23 | ✅ | 3.72 | ✅ |  | matured 2025-08-03 |
| HRHO.CA | 2025-06-30 | day | kronos-alone | flat | -0.42 | -1.76 | ❌ | 1.34 | ✅ |  | matured 2025-07-01 |
| HRHO.CA | 2025-06-30 | week | kronos-alone | down | -1.82 | -6.64 | ✅ | 4.82 | ❌ |  | matured 2025-07-09 |
| HRHO.CA | 2025-06-30 | month | kronos-alone | down | -6.26 | -9.23 | ✅ | 2.97 | ✅ |  | matured 2025-08-03 |
| HRHO.CA | 2025-06-30 | day | family-technicals | flat | -0.59 | -1.76 | ❌ | 1.17 | ✅ |  | matured 2025-07-01 |
| HRHO.CA | 2025-06-30 | week | family-technicals | down | -1.02 | -6.64 | ✅ | 5.62 | ✅ |  | matured 2025-07-09 |
| HRHO.CA | 2025-06-30 | month | family-technicals | down | -2.21 | -9.23 | ✅ | 7.02 | ✅ |  | matured 2025-08-03 |
| HRHO.CA | 2025-06-30 | day | buy-and-hold | flat | +0.00 | -1.76 | ❌ | 1.76 | ✅ |  | matured 2025-07-01 |
| HRHO.CA | 2025-06-30 | week | buy-and-hold | flat | +0.00 | -6.64 | ❌ | 6.64 | ✅ |  | matured 2025-07-09 |
| HRHO.CA | 2025-06-30 | month | buy-and-hold | flat | +0.00 | -9.23 | ❌ | 9.23 | ✅ |  | matured 2025-08-03 |
| HRHO.CA | 2025-06-30 | day | naive-range | flat | +0.00 | -1.76 | ❌ | 1.76 | ✅ |  | matured 2025-07-01 |
| HRHO.CA | 2025-06-30 | week | naive-range | flat | +0.00 | -6.64 | ❌ | 6.64 | ✅ |  | matured 2025-07-09 |
| HRHO.CA | 2025-06-30 | month | naive-range | flat | +0.00 | -9.23 | ❌ | 9.23 | ✅ |  | matured 2025-08-03 |
| NVDA | 2025-06-30 | day | 2-family-ensemble | up | +2.52 | -2.97 | ❌ | 5.49 | ❌ |  | matured 2025-07-01 |
| NVDA | 2025-06-30 | week | 2-family-ensemble | flat | -0.30 | +1.27 | ❌ | 1.57 | ✅ |  | matured 2025-07-08 |
| NVDA | 2025-06-30 | month | 2-family-ensemble | down | -22.99 | +13.47 | ❌ | 36.46 | ❌ |  | matured 2025-07-30 |
| NVDA | 2025-06-30 | day | kronos-alone | up | +3.24 | -2.97 | ❌ | 6.21 | ❌ |  | matured 2025-07-01 |
| NVDA | 2025-06-30 | week | kronos-alone | flat | -0.53 | +1.27 | ❌ | 1.80 | ✅ |  | matured 2025-07-08 |
| NVDA | 2025-06-30 | month | kronos-alone | down | -29.96 | +13.47 | ❌ | 43.43 | ❌ |  | matured 2025-07-30 |
| NVDA | 2025-06-30 | day | family-technicals | flat | +0.19 | -2.97 | ❌ | 3.16 | ✅ |  | matured 2025-07-01 |
| NVDA | 2025-06-30 | week | family-technicals | flat | +0.33 | +1.27 | ❌ | 0.94 | ✅ |  | matured 2025-07-08 |
| NVDA | 2025-06-30 | month | family-technicals | flat | +0.71 | +13.47 | ❌ | 12.76 | ✅ |  | matured 2025-07-30 |
| NVDA | 2025-06-30 | day | buy-and-hold | flat | +0.00 | -2.97 | ❌ | 2.97 | ✅ |  | matured 2025-07-01 |
| NVDA | 2025-06-30 | week | buy-and-hold | flat | +0.00 | +1.27 | ❌ | 1.27 | ✅ |  | matured 2025-07-08 |
| NVDA | 2025-06-30 | month | buy-and-hold | flat | +0.00 | +13.47 | ❌ | 13.47 | ✅ |  | matured 2025-07-30 |
| NVDA | 2025-06-30 | day | index-baseline | flat | +0.00 | -0.11 | ✅ | 0.11 | ❌ |  | matured 2025-07-01 |
| NVDA | 2025-06-30 | week | index-baseline | flat | +0.00 | +0.33 | ✅ | 0.33 | ❌ |  | matured 2025-07-08 |
| NVDA | 2025-06-30 | month | index-baseline | flat | +0.00 | +2.55 | ❌ | 2.55 | ❌ |  | matured 2025-07-30 |
| NVDA | 2025-06-30 | day | naive-range | flat | +0.00 | -2.97 | ❌ | 2.97 | ✅ |  | matured 2025-07-01 |
| NVDA | 2025-06-30 | week | naive-range | flat | +0.00 | +1.27 | ❌ | 1.27 | ✅ |  | matured 2025-07-08 |
| NVDA | 2025-06-30 | month | naive-range | flat | +0.00 | +13.47 | ❌ | 13.47 | ✅ |  | matured 2025-07-30 |
| SWDY.CA | 2025-06-30 | day | 2-family-ensemble | flat | +0.75 | -0.09 | ✅ | 0.84 | ✅ |  | matured 2025-07-01 |
| SWDY.CA | 2025-06-30 | week | 2-family-ensemble | up | +2.04 | +0.91 | ✅ | 1.13 | ✅ |  | matured 2025-07-09 |
| SWDY.CA | 2025-06-30 | month | 2-family-ensemble | up | +6.50 | -0.77 | ❌ | 7.27 | ✅ |  | matured 2025-08-03 |
| SWDY.CA | 2025-06-30 | day | kronos-alone | up | +1.13 | -0.09 | ❌ | 1.22 | ✅ |  | matured 2025-07-01 |
| SWDY.CA | 2025-06-30 | week | kronos-alone | up | +2.85 | +0.91 | ✅ | 1.94 | ✅ |  | matured 2025-07-09 |
| SWDY.CA | 2025-06-30 | month | kronos-alone | up | +8.54 | -0.77 | ❌ | 9.31 | ❌ |  | matured 2025-08-03 |
| SWDY.CA | 2025-06-30 | day | family-technicals | flat | -0.27 | -0.09 | ✅ | 0.18 | ✅ |  | matured 2025-07-01 |
| SWDY.CA | 2025-06-30 | week | family-technicals | flat | -0.48 | +0.91 | ❌ | 1.39 | ✅ |  | matured 2025-07-09 |
| SWDY.CA | 2025-06-30 | month | family-technicals | down | -1.03 | -0.77 | ✅ | 0.26 | ✅ |  | matured 2025-08-03 |
| SWDY.CA | 2025-06-30 | day | buy-and-hold | flat | +0.00 | -0.09 | ✅ | 0.09 | ✅ |  | matured 2025-07-01 |
| SWDY.CA | 2025-06-30 | week | buy-and-hold | flat | +0.00 | +0.91 | ❌ | 0.91 | ✅ |  | matured 2025-07-09 |
| SWDY.CA | 2025-06-30 | month | buy-and-hold | flat | +0.00 | -0.77 | ❌ | 0.77 | ✅ |  | matured 2025-08-03 |
| SWDY.CA | 2025-06-30 | day | naive-range | flat | +0.00 | -0.09 | ✅ | 0.09 | ✅ |  | matured 2025-07-01 |
| SWDY.CA | 2025-06-30 | week | naive-range | flat | +0.00 | +0.91 | ❌ | 0.91 | ✅ |  | matured 2025-07-09 |
| SWDY.CA | 2025-06-30 | month | naive-range | flat | +0.00 | -0.77 | ❌ | 0.77 | ✅ |  | matured 2025-08-03 |
| TMGH.CA | 2025-06-30 | day | 2-family-ensemble | up | +0.96 | -0.99 | ❌ | 1.95 | ✅ |  | matured 2025-07-01 |
| TMGH.CA | 2025-06-30 | week | 2-family-ensemble | up | +2.97 | +2.20 | ✅ | 0.77 | ✅ |  | matured 2025-07-09 |
| TMGH.CA | 2025-06-30 | month | 2-family-ensemble | up | +9.04 | -4.05 | ❌ | 13.09 | ❌ |  | matured 2025-08-03 |
| TMGH.CA | 2025-06-30 | day | kronos-alone | up | +0.95 | -0.99 | ❌ | 1.94 | ❌ |  | matured 2025-07-01 |
| TMGH.CA | 2025-06-30 | week | kronos-alone | up | +3.39 | +2.20 | ✅ | 1.19 | ✅ |  | matured 2025-07-09 |
| TMGH.CA | 2025-06-30 | month | kronos-alone | up | +10.68 | -4.05 | ❌ | 14.73 | ❌ |  | matured 2025-08-03 |
| TMGH.CA | 2025-06-30 | day | family-technicals | flat | +0.62 | -0.99 | ❌ | 1.61 | ✅ |  | matured 2025-07-01 |
| TMGH.CA | 2025-06-30 | week | family-technicals | up | +1.07 | +2.20 | ✅ | 1.13 | ✅ |  | matured 2025-07-09 |
| TMGH.CA | 2025-06-30 | month | family-technicals | up | +2.31 | -4.05 | ❌ | 6.36 | ✅ |  | matured 2025-08-03 |
| TMGH.CA | 2025-06-30 | day | buy-and-hold | flat | +0.00 | -0.99 | ❌ | 0.99 | ✅ |  | matured 2025-07-01 |
| TMGH.CA | 2025-06-30 | week | buy-and-hold | flat | +0.00 | +2.20 | ❌ | 2.20 | ✅ |  | matured 2025-07-09 |
| TMGH.CA | 2025-06-30 | month | buy-and-hold | flat | +0.00 | -4.05 | ❌ | 4.05 | ✅ |  | matured 2025-08-03 |
| TMGH.CA | 2025-06-30 | day | naive-range | flat | +0.00 | -0.99 | ❌ | 0.99 | ✅ |  | matured 2025-07-01 |
| TMGH.CA | 2025-06-30 | week | naive-range | flat | +0.00 | +2.20 | ❌ | 2.20 | ✅ |  | matured 2025-07-09 |
| TMGH.CA | 2025-06-30 | month | naive-range | flat | +0.00 | -4.05 | ❌ | 4.05 | ✅ |  | matured 2025-08-03 |
| COMI.CA | 2025-09-30 | day | 2-family-ensemble | down | -1.09 | +1.00 | ❌ | 2.09 | ✅ |  | matured 2025-10-01 |
| COMI.CA | 2025-09-30 | week | 2-family-ensemble | down | -2.92 | +3.96 | ❌ | 6.88 | ❌ |  | matured 2025-10-07 |
| COMI.CA | 2025-09-30 | month | 2-family-ensemble | down | -8.95 | +4.45 | ❌ | 13.40 | ❌ |  | matured 2025-10-30 |
| COMI.CA | 2025-09-30 | day | kronos-alone | down | -1.53 | +1.00 | ❌ | 2.53 | ❌ |  | matured 2025-10-01 |
| COMI.CA | 2025-09-30 | week | kronos-alone | down | -3.91 | +3.96 | ❌ | 7.87 | ❌ |  | matured 2025-10-07 |
| COMI.CA | 2025-09-30 | month | kronos-alone | down | -11.50 | +4.45 | ❌ | 15.95 | ❌ |  | matured 2025-10-30 |
| COMI.CA | 2025-09-30 | day | family-technicals | flat | +0.16 | +1.00 | ❌ | 0.84 | ✅ |  | matured 2025-10-01 |
| COMI.CA | 2025-09-30 | week | family-technicals | flat | +0.28 | +3.96 | ❌ | 3.68 | ❌ |  | matured 2025-10-07 |
| COMI.CA | 2025-09-30 | month | family-technicals | flat | +0.61 | +4.45 | ❌ | 3.84 | ✅ |  | matured 2025-10-30 |
| COMI.CA | 2025-09-30 | day | buy-and-hold | flat | +0.00 | +1.00 | ❌ | 1.00 | ✅ |  | matured 2025-10-01 |
| COMI.CA | 2025-09-30 | week | buy-and-hold | flat | +0.00 | +3.96 | ❌ | 3.96 | ❌ |  | matured 2025-10-07 |
| COMI.CA | 2025-09-30 | month | buy-and-hold | flat | +0.00 | +4.45 | ❌ | 4.45 | ✅ |  | matured 2025-10-30 |
| COMI.CA | 2025-09-30 | day | naive-range | flat | +0.00 | +1.00 | ❌ | 1.00 | ✅ |  | matured 2025-10-01 |
| COMI.CA | 2025-09-30 | week | naive-range | flat | +0.00 | +3.96 | ❌ | 3.96 | ✅ |  | matured 2025-10-07 |
| COMI.CA | 2025-09-30 | month | naive-range | flat | +0.00 | +4.45 | ❌ | 4.45 | ✅ |  | matured 2025-10-30 |
| ETEL.CA | 2025-09-30 | day | 2-family-ensemble | down | -2.97 | +0.00 | ❌ | 2.97 | ✅ |  | matured 2025-10-01 |
| ETEL.CA | 2025-09-30 | week | 2-family-ensemble | down | -5.76 | -6.24 | ✅ | 0.48 | ✅ |  | matured 2025-10-07 |
| ETEL.CA | 2025-09-30 | month | 2-family-ensemble | down | -21.24 | -1.76 | ✅ | 19.48 | ❌ |  | matured 2025-10-30 |
| ETEL.CA | 2025-09-30 | day | kronos-alone | down | -3.88 | +0.00 | ❌ | 3.88 | ❌ |  | matured 2025-10-01 |
| ETEL.CA | 2025-09-30 | week | kronos-alone | down | -7.41 | -6.24 | ✅ | 1.17 | ✅ |  | matured 2025-10-07 |
| ETEL.CA | 2025-09-30 | month | kronos-alone | down | -30.16 | -1.76 | ✅ | 28.40 | ❌ |  | matured 2025-10-30 |
| ETEL.CA | 2025-09-30 | day | family-technicals | flat | -0.11 | +0.00 | ✅ | 0.11 | ✅ |  | matured 2025-10-01 |
| ETEL.CA | 2025-09-30 | week | family-technicals | flat | -0.19 | -6.24 | ❌ | 6.05 | ❌ |  | matured 2025-10-07 |
| ETEL.CA | 2025-09-30 | month | family-technicals | flat | -0.41 | -1.76 | ❌ | 1.35 | ✅ |  | matured 2025-10-30 |
| ETEL.CA | 2025-09-30 | day | buy-and-hold | flat | +0.00 | +0.00 | ✅ | 0.00 | ✅ |  | matured 2025-10-01 |
| ETEL.CA | 2025-09-30 | week | buy-and-hold | flat | +0.00 | -6.24 | ❌ | 6.24 | ❌ |  | matured 2025-10-07 |
| ETEL.CA | 2025-09-30 | month | buy-and-hold | flat | +0.00 | -1.76 | ❌ | 1.76 | ✅ |  | matured 2025-10-30 |
| ETEL.CA | 2025-09-30 | day | naive-range | flat | +0.00 | +0.00 | ✅ | 0.00 | ✅ |  | matured 2025-10-01 |
| ETEL.CA | 2025-09-30 | week | naive-range | flat | +0.00 | -6.24 | ❌ | 6.24 | ❌ |  | matured 2025-10-07 |
| ETEL.CA | 2025-09-30 | month | naive-range | flat | +0.00 | -1.76 | ❌ | 1.76 | ✅ |  | matured 2025-10-30 |
| HRHO.CA | 2025-09-30 | day | 2-family-ensemble | flat | +0.00 | -0.67 | ✅ | 0.67 | ✅ |  | matured 2025-10-01 |
| HRHO.CA | 2025-09-30 | week | 2-family-ensemble | flat | +0.00 | -0.11 | ✅ | 0.11 | ✅ |  | matured 2025-10-07 |
| HRHO.CA | 2025-09-30 | month | 2-family-ensemble | flat | +0.00 | +5.08 | ❌ | 5.08 | ✅ |  | matured 2025-10-30 |
| HRHO.CA | 2025-09-30 | day | kronos-alone | down | -0.85 | -0.67 | ❌ | 0.18 | ✅ |  | matured 2025-10-01 |
| HRHO.CA | 2025-09-30 | week | kronos-alone | flat | -0.64 | -0.11 | ✅ | 0.53 | ✅ |  | matured 2025-10-07 |
| HRHO.CA | 2025-09-30 | month | kronos-alone | down | -1.53 | +5.08 | ❌ | 6.61 | ❌ |  | matured 2025-10-30 |
| HRHO.CA | 2025-09-30 | day | family-technicals | flat | +0.15 | -0.67 | ✅ | 0.82 | ✅ |  | matured 2025-10-01 |
| HRHO.CA | 2025-09-30 | week | family-technicals | flat | +0.34 | -0.11 | ✅ | 0.45 | ✅ |  | matured 2025-10-07 |
| HRHO.CA | 2025-09-30 | month | family-technicals | flat | +0.70 | +5.08 | ❌ | 4.38 | ✅ |  | matured 2025-10-30 |
| HRHO.CA | 2025-09-30 | day | buy-and-hold | flat | +0.00 | -0.67 | ✅ | 0.67 | ✅ |  | matured 2025-10-01 |
| HRHO.CA | 2025-09-30 | week | buy-and-hold | flat | +0.00 | -0.11 | ✅ | 0.11 | ✅ |  | matured 2025-10-07 |
| HRHO.CA | 2025-09-30 | month | buy-and-hold | flat | +0.00 | +5.08 | ❌ | 5.08 | ✅ |  | matured 2025-10-30 |
| HRHO.CA | 2025-09-30 | day | naive-range | flat | +0.00 | -0.67 | ✅ | 0.67 | ✅ |  | matured 2025-10-01 |
| HRHO.CA | 2025-09-30 | week | naive-range | flat | +0.00 | -0.11 | ✅ | 0.11 | ✅ |  | matured 2025-10-07 |
| HRHO.CA | 2025-09-30 | month | naive-range | flat | +0.00 | +5.08 | ❌ | 5.08 | ✅ |  | matured 2025-10-30 |
| HRHO.CA | 2025-09-30 | day | tilt-technicals | flat | +0.00 | -0.67 | ✅ | 0.67 | ✅ |  | matured 2025-10-01 |
| HRHO.CA | 2025-09-30 | week | tilt-technicals | flat | +0.17 | -0.11 | ✅ | 0.28 | ✅ |  | matured 2025-10-07 |
| HRHO.CA | 2025-09-30 | month | tilt-technicals | flat | +0.35 | +5.08 | ❌ | 4.73 | ✅ |  | matured 2025-10-30 |
| NVDA | 2025-09-30 | day | 2-family-ensemble | flat | -0.60 | +0.35 | ✅ | 0.95 | ✅ |  | matured 2025-10-01 |
| NVDA | 2025-09-30 | week | 2-family-ensemble | down | -5.57 | -0.83 | ✅ | 4.74 | ✅ |  | matured 2025-10-07 |
| NVDA | 2025-09-30 | month | 2-family-ensemble | down | -18.05 | +10.97 | ❌ | 29.02 | ❌ |  | matured 2025-10-29 |
| NVDA | 2025-09-30 | day | kronos-alone | down | -0.92 | +0.35 | ❌ | 1.27 | ✅ |  | matured 2025-10-01 |
| NVDA | 2025-09-30 | week | kronos-alone | down | -7.40 | -0.83 | ✅ | 6.57 | ❌ |  | matured 2025-10-07 |
| NVDA | 2025-09-30 | month | kronos-alone | down | -25.12 | +10.97 | ❌ | 36.09 | ❌ |  | matured 2025-10-29 |
| NVDA | 2025-09-30 | day | family-technicals | flat | +0.23 | +0.35 | ✅ | 0.12 | ✅ |  | matured 2025-10-01 |
| NVDA | 2025-09-30 | week | family-technicals | flat | +0.39 | -0.83 | ❌ | 1.22 | ✅ |  | matured 2025-10-07 |
| NVDA | 2025-09-30 | month | family-technicals | up | +0.85 | +10.97 | ✅ | 10.12 | ✅ |  | matured 2025-10-29 |
| NVDA | 2025-09-30 | day | buy-and-hold | flat | +0.00 | +0.35 | ✅ | 0.35 | ✅ |  | matured 2025-10-01 |
| NVDA | 2025-09-30 | week | buy-and-hold | flat | +0.00 | -0.83 | ❌ | 0.83 | ✅ |  | matured 2025-10-07 |
| NVDA | 2025-09-30 | month | buy-and-hold | flat | +0.00 | +10.97 | ❌ | 10.97 | ❌ |  | matured 2025-10-29 |
| NVDA | 2025-09-30 | day | index-baseline | flat | +0.00 | +0.34 | ✅ | 0.34 | ❌ |  | matured 2025-10-01 |
| NVDA | 2025-09-30 | week | index-baseline | flat | +0.00 | +0.39 | ✅ | 0.39 | ❌ |  | matured 2025-10-07 |
| NVDA | 2025-09-30 | month | index-baseline | flat | +0.00 | +3.02 | ❌ | 3.02 | ❌ |  | matured 2025-10-29 |
| NVDA | 2025-09-30 | day | naive-range | flat | +0.00 | +0.35 | ✅ | 0.35 | ✅ |  | matured 2025-10-01 |
| NVDA | 2025-09-30 | week | naive-range | flat | +0.00 | -0.83 | ❌ | 0.83 | ✅ |  | matured 2025-10-07 |
| NVDA | 2025-09-30 | month | naive-range | flat | +0.00 | +10.97 | ❌ | 10.97 | ✅ |  | matured 2025-10-29 |
| SWDY.CA | 2025-09-30 | day | 2-family-ensemble | flat | +0.00 | -0.08 | ✅ | 0.08 | ✅ |  | matured 2025-10-01 |
| SWDY.CA | 2025-09-30 | week | 2-family-ensemble | flat | +0.00 | +2.61 | ❌ | 2.61 | ✅ |  | matured 2025-10-07 |
| SWDY.CA | 2025-09-30 | month | 2-family-ensemble | flat | +0.00 | +2.65 | ❌ | 2.65 | ✅ |  | matured 2025-10-30 |
| SWDY.CA | 2025-09-30 | day | kronos-alone | up | +0.89 | -0.08 | ❌ | 0.97 | ❌ |  | matured 2025-10-01 |
| SWDY.CA | 2025-09-30 | week | kronos-alone | up | +4.28 | +2.61 | ✅ | 1.67 | ✅ |  | matured 2025-10-07 |
| SWDY.CA | 2025-09-30 | month | kronos-alone | up | +19.04 | +2.65 | ✅ | 16.39 | ❌ |  | matured 2025-10-30 |
| SWDY.CA | 2025-09-30 | day | family-technicals | flat | +0.08 | -0.08 | ✅ | 0.16 | ✅ |  | matured 2025-10-01 |
| SWDY.CA | 2025-09-30 | week | family-technicals | flat | +0.18 | +2.61 | ❌ | 2.43 | ✅ |  | matured 2025-10-07 |
| SWDY.CA | 2025-09-30 | month | family-technicals | flat | +0.37 | +2.65 | ❌ | 2.28 | ✅ |  | matured 2025-10-30 |
| SWDY.CA | 2025-09-30 | day | buy-and-hold | flat | +0.00 | -0.08 | ✅ | 0.08 | ✅ |  | matured 2025-10-01 |
| SWDY.CA | 2025-09-30 | week | buy-and-hold | flat | +0.00 | +2.61 | ❌ | 2.61 | ✅ |  | matured 2025-10-07 |
| SWDY.CA | 2025-09-30 | month | buy-and-hold | flat | +0.00 | +2.65 | ❌ | 2.65 | ✅ |  | matured 2025-10-30 |
| SWDY.CA | 2025-09-30 | day | naive-range | flat | +0.00 | -0.08 | ✅ | 0.08 | ✅ |  | matured 2025-10-01 |
| SWDY.CA | 2025-09-30 | week | naive-range | flat | +0.00 | +2.61 | ❌ | 2.61 | ✅ |  | matured 2025-10-07 |
| SWDY.CA | 2025-09-30 | month | naive-range | flat | +0.00 | +2.65 | ❌ | 2.65 | ✅ |  | matured 2025-10-30 |
| SWDY.CA | 2025-09-30 | day | tilt-technicals | flat | +0.00 | -0.08 | ✅ | 0.08 | ✅ |  | matured 2025-10-01 |
| SWDY.CA | 2025-09-30 | week | tilt-technicals | flat | +0.09 | +2.61 | ❌ | 2.52 | ✅ |  | matured 2025-10-07 |
| SWDY.CA | 2025-09-30 | month | tilt-technicals | flat | +0.18 | +2.65 | ❌ | 2.47 | ✅ |  | matured 2025-10-30 |
| TMGH.CA | 2025-09-30 | day | 2-family-ensemble | down | -1.78 | +0.49 | ❌ | 2.27 | ❌ |  | matured 2025-10-01 |
| TMGH.CA | 2025-09-30 | week | 2-family-ensemble | down | -2.52 | -1.13 | ✅ | 1.39 | ✅ |  | matured 2025-10-07 |
| TMGH.CA | 2025-09-30 | month | 2-family-ensemble | down | -1.67 | +1.11 | ❌ | 2.78 | ✅ |  | matured 2025-10-30 |
| TMGH.CA | 2025-09-30 | day | kronos-alone | down | -2.43 | +0.49 | ❌ | 2.92 | ❌ |  | matured 2025-10-01 |
| TMGH.CA | 2025-09-30 | week | kronos-alone | down | -3.38 | -1.13 | ✅ | 2.25 | ❌ |  | matured 2025-10-07 |
| TMGH.CA | 2025-09-30 | month | kronos-alone | down | -2.28 | +1.11 | ❌ | 3.39 | ❌ |  | matured 2025-10-30 |
| TMGH.CA | 2025-09-30 | day | family-technicals | flat | +0.14 | +0.49 | ✅ | 0.35 | ✅ |  | matured 2025-10-01 |
| TMGH.CA | 2025-09-30 | week | family-technicals | flat | +0.25 | -1.13 | ❌ | 1.38 | ✅ |  | matured 2025-10-07 |
| TMGH.CA | 2025-09-30 | month | family-technicals | flat | +0.53 | +1.11 | ❌ | 0.58 | ✅ |  | matured 2025-10-30 |
| TMGH.CA | 2025-09-30 | day | buy-and-hold | flat | +0.00 | +0.49 | ✅ | 0.49 | ✅ |  | matured 2025-10-01 |
| TMGH.CA | 2025-09-30 | week | buy-and-hold | flat | +0.00 | -1.13 | ❌ | 1.13 | ✅ |  | matured 2025-10-07 |
| TMGH.CA | 2025-09-30 | month | buy-and-hold | flat | +0.00 | +1.11 | ❌ | 1.11 | ✅ |  | matured 2025-10-30 |
| TMGH.CA | 2025-09-30 | day | naive-range | flat | +0.00 | +0.49 | ✅ | 0.49 | ✅ |  | matured 2025-10-01 |
| TMGH.CA | 2025-09-30 | week | naive-range | flat | +0.00 | -1.13 | ❌ | 1.13 | ✅ |  | matured 2025-10-07 |
| TMGH.CA | 2025-09-30 | month | naive-range | flat | +0.00 | +1.11 | ❌ | 1.11 | ✅ |  | matured 2025-10-30 |
| COMI.CA | 2025-12-31 | day | 2-family-ensemble | flat | +0.00 | -2.41 | ❌ | 2.41 | ❌ |  | matured 2026-01-04 |
| COMI.CA | 2025-12-31 | week | 2-family-ensemble | flat | +0.00 | +5.31 | ❌ | 5.31 | ❌ |  | matured 2026-01-11 |
| COMI.CA | 2025-12-31 | month | 2-family-ensemble | flat | +0.00 | +29.13 | ❌ | 29.13 | ❌ |  | matured 2026-02-03 |
| COMI.CA | 2025-12-31 | day | kronos-alone | flat | +0.05 | -2.41 | ❌ | 2.46 | ❌ |  | matured 2026-01-04 |
| COMI.CA | 2025-12-31 | week | kronos-alone | down | -0.81 | +5.31 | ❌ | 6.12 | ❌ |  | matured 2026-01-11 |
| COMI.CA | 2025-12-31 | month | kronos-alone | down | -6.87 | +29.13 | ❌ | 36.00 | ❌ |  | matured 2026-02-03 |
| COMI.CA | 2025-12-31 | day | family-technicals | flat | -0.28 | -2.41 | ❌ | 2.13 | ✅ |  | matured 2026-01-04 |
| COMI.CA | 2025-12-31 | week | family-technicals | flat | -0.62 | +5.31 | ❌ | 5.93 | ❌ |  | matured 2026-01-11 |
| COMI.CA | 2025-12-31 | month | family-technicals | down | -1.27 | +29.13 | ❌ | 30.40 | ❌ |  | matured 2026-02-03 |
| COMI.CA | 2025-12-31 | day | buy-and-hold | flat | +0.00 | -2.41 | ❌ | 2.41 | ❌ |  | matured 2026-01-04 |
| COMI.CA | 2025-12-31 | week | buy-and-hold | flat | +0.00 | +5.31 | ❌ | 5.31 | ❌ |  | matured 2026-01-11 |
| COMI.CA | 2025-12-31 | month | buy-and-hold | flat | +0.00 | +29.13 | ❌ | 29.13 | ❌ |  | matured 2026-02-03 |
| COMI.CA | 2025-12-31 | day | naive-range | flat | +0.00 | -2.41 | ❌ | 2.41 | ❌ |  | matured 2026-01-04 |
| COMI.CA | 2025-12-31 | week | naive-range | flat | +0.00 | +5.31 | ❌ | 5.31 | ❌ |  | matured 2026-01-11 |
| COMI.CA | 2025-12-31 | month | naive-range | flat | +0.00 | +29.13 | ❌ | 29.13 | ❌ |  | matured 2026-02-03 |
| COMI.CA | 2025-12-31 | day | tilt-technicals | flat | +0.00 | -2.41 | ❌ | 2.41 | ❌ |  | matured 2026-01-04 |
| COMI.CA | 2025-12-31 | week | tilt-technicals | flat | -0.31 | +5.31 | ❌ | 5.62 | ❌ |  | matured 2026-01-11 |
| COMI.CA | 2025-12-31 | month | tilt-technicals | flat | -0.63 | +29.13 | ❌ | 29.76 | ❌ |  | matured 2026-02-03 |
| ETEL.CA | 2025-12-31 | day | 2-family-ensemble | flat | +0.00 | -0.70 | ✅ | 0.70 | ✅ |  | matured 2026-01-04 |
| ETEL.CA | 2025-12-31 | week | 2-family-ensemble | flat | +0.00 | +7.95 | ❌ | 7.95 | ❌ |  | matured 2026-01-11 |
| ETEL.CA | 2025-12-31 | month | 2-family-ensemble | flat | +0.00 | +26.58 | ❌ | 26.58 | ❌ |  | matured 2026-02-03 |
| ETEL.CA | 2025-12-31 | day | kronos-alone | flat | -0.25 | -0.70 | ✅ | 0.45 | ✅ |  | matured 2026-01-04 |
| ETEL.CA | 2025-12-31 | week | kronos-alone | down | -3.89 | +7.95 | ❌ | 11.84 | ❌ |  | matured 2026-01-11 |
| ETEL.CA | 2025-12-31 | month | kronos-alone | down | -45.43 | +26.58 | ❌ | 72.01 | ❌ |  | matured 2026-02-03 |
| ETEL.CA | 2025-12-31 | day | family-technicals | flat | -0.36 | -0.70 | ✅ | 0.34 | ✅ |  | matured 2026-01-04 |
| ETEL.CA | 2025-12-31 | week | family-technicals | down | -0.81 | +7.95 | ❌ | 8.76 | ❌ |  | matured 2026-01-11 |
| ETEL.CA | 2025-12-31 | month | family-technicals | down | -1.67 | +26.58 | ❌ | 28.25 | ❌ |  | matured 2026-02-03 |
| ETEL.CA | 2025-12-31 | day | buy-and-hold | flat | +0.00 | -0.70 | ✅ | 0.70 | ✅ |  | matured 2026-01-04 |
| ETEL.CA | 2025-12-31 | week | buy-and-hold | flat | +0.00 | +7.95 | ❌ | 7.95 | ❌ |  | matured 2026-01-11 |
| ETEL.CA | 2025-12-31 | month | buy-and-hold | flat | +0.00 | +26.58 | ❌ | 26.58 | ❌ |  | matured 2026-02-03 |
| ETEL.CA | 2025-12-31 | day | naive-range | flat | +0.00 | -0.70 | ✅ | 0.70 | ✅ |  | matured 2026-01-04 |
| ETEL.CA | 2025-12-31 | week | naive-range | flat | +0.00 | +7.95 | ❌ | 7.95 | ❌ |  | matured 2026-01-11 |
| ETEL.CA | 2025-12-31 | month | naive-range | flat | +0.00 | +26.58 | ❌ | 26.58 | ❌ |  | matured 2026-02-03 |
| ETEL.CA | 2025-12-31 | day | tilt-technicals | flat | +0.00 | -0.70 | ✅ | 0.70 | ✅ |  | matured 2026-01-04 |
| ETEL.CA | 2025-12-31 | week | tilt-technicals | flat | -0.41 | +7.95 | ❌ | 8.36 | ❌ |  | matured 2026-01-11 |
| ETEL.CA | 2025-12-31 | month | tilt-technicals | down | -0.83 | +26.58 | ❌ | 27.41 | ❌ |  | matured 2026-02-03 |
| HRHO.CA | 2025-12-31 | day | 2-family-ensemble | flat | +0.00 | -0.48 | ✅ | 0.48 | ✅ |  | matured 2026-01-04 |
| HRHO.CA | 2025-12-31 | week | 2-family-ensemble | flat | +0.00 | +7.54 | ❌ | 7.54 | ❌ |  | matured 2026-01-11 |
| HRHO.CA | 2025-12-31 | month | 2-family-ensemble | flat | +0.00 | +17.54 | ❌ | 17.54 | ❌ |  | matured 2026-02-03 |
| HRHO.CA | 2025-12-31 | day | kronos-alone | up | +1.03 | -0.48 | ❌ | 1.51 | ❌ |  | matured 2026-01-04 |
| HRHO.CA | 2025-12-31 | week | kronos-alone | up | +5.37 | +7.54 | ✅ | 2.17 | ❌ |  | matured 2026-01-11 |
| HRHO.CA | 2025-12-31 | month | kronos-alone | up | +9.30 | +17.54 | ✅ | 8.24 | ❌ |  | matured 2026-02-03 |
| HRHO.CA | 2025-12-31 | day | family-technicals | flat | +0.29 | -0.48 | ✅ | 0.77 | ✅ |  | matured 2026-01-04 |
| HRHO.CA | 2025-12-31 | week | family-technicals | flat | +0.66 | +7.54 | ❌ | 6.88 | ❌ |  | matured 2026-01-11 |
| HRHO.CA | 2025-12-31 | month | family-technicals | up | +1.35 | +17.54 | ✅ | 16.19 | ❌ |  | matured 2026-02-03 |
| HRHO.CA | 2025-12-31 | day | buy-and-hold | flat | +0.00 | -0.48 | ✅ | 0.48 | ✅ |  | matured 2026-01-04 |
| HRHO.CA | 2025-12-31 | week | buy-and-hold | flat | +0.00 | +7.54 | ❌ | 7.54 | ❌ |  | matured 2026-01-11 |
| HRHO.CA | 2025-12-31 | month | buy-and-hold | flat | +0.00 | +17.54 | ❌ | 17.54 | ❌ |  | matured 2026-02-03 |
| HRHO.CA | 2025-12-31 | day | naive-range | flat | +0.00 | -0.48 | ✅ | 0.48 | ✅ |  | matured 2026-01-04 |
| HRHO.CA | 2025-12-31 | week | naive-range | flat | +0.00 | +7.54 | ❌ | 7.54 | ❌ |  | matured 2026-01-11 |
| HRHO.CA | 2025-12-31 | month | naive-range | flat | +0.00 | +17.54 | ❌ | 17.54 | ❌ |  | matured 2026-02-03 |
| HRHO.CA | 2025-12-31 | day | tilt-technicals | flat | +0.00 | -0.48 | ✅ | 0.48 | ✅ |  | matured 2026-01-04 |
| HRHO.CA | 2025-12-31 | week | tilt-technicals | flat | +0.33 | +7.54 | ❌ | 7.21 | ❌ |  | matured 2026-01-11 |
| HRHO.CA | 2025-12-31 | month | tilt-technicals | flat | +0.67 | +17.54 | ❌ | 16.87 | ❌ |  | matured 2026-02-03 |
| NVDA | 2025-12-31 | day | 2-family-ensemble | flat | +0.00 | +1.26 | ❌ | 1.26 | ✅ |  | matured 2026-01-02 |
| NVDA | 2025-12-31 | week | 2-family-ensemble | flat | +0.00 | -0.78 | ❌ | 0.78 | ✅ |  | matured 2026-01-08 |
| NVDA | 2025-12-31 | month | 2-family-ensemble | flat | +0.00 | -0.48 | ✅ | 0.48 | ✅ |  | matured 2026-02-02 |
| NVDA | 2025-12-31 | day | kronos-alone | flat | +0.05 | +1.26 | ❌ | 1.21 | ✅ |  | matured 2026-01-02 |
| NVDA | 2025-12-31 | week | kronos-alone | down | -2.96 | -0.78 | ✅ | 2.18 | ❌ |  | matured 2026-01-08 |
| NVDA | 2025-12-31 | month | kronos-alone | down | -4.15 | -0.48 | ❌ | 3.67 | ❌ |  | matured 2026-02-02 |
| NVDA | 2025-12-31 | day | family-technicals | flat | +0.54 | +1.26 | ❌ | 0.72 | ✅ |  | matured 2026-01-02 |
| NVDA | 2025-12-31 | week | family-technicals | up | +1.21 | -0.78 | ❌ | 1.99 | ✅ |  | matured 2026-01-08 |
| NVDA | 2025-12-31 | month | family-technicals | up | +2.48 | -0.48 | ❌ | 2.96 | ✅ |  | matured 2026-02-02 |
| NVDA | 2025-12-31 | day | buy-and-hold | flat | +0.00 | +1.26 | ❌ | 1.26 | ✅ |  | matured 2026-01-02 |
| NVDA | 2025-12-31 | week | buy-and-hold | flat | +0.00 | -0.78 | ❌ | 0.78 | ✅ |  | matured 2026-01-08 |
| NVDA | 2025-12-31 | month | buy-and-hold | flat | +0.00 | -0.48 | ✅ | 0.48 | ✅ |  | matured 2026-02-02 |
| NVDA | 2025-12-31 | day | index-baseline | flat | +0.00 | +0.19 | ✅ | 0.19 | ❌ |  | matured 2026-01-02 |
| NVDA | 2025-12-31 | week | index-baseline | flat | +0.00 | +1.11 | ❌ | 1.11 | ❌ |  | matured 2026-01-08 |
| NVDA | 2025-12-31 | month | index-baseline | flat | +0.00 | +1.91 | ❌ | 1.91 | ❌ |  | matured 2026-02-02 |
| NVDA | 2025-12-31 | day | naive-range | flat | +0.00 | +1.26 | ❌ | 1.26 | ✅ |  | matured 2026-01-02 |
| NVDA | 2025-12-31 | week | naive-range | flat | +0.00 | -0.78 | ❌ | 0.78 | ✅ |  | matured 2026-01-08 |
| NVDA | 2025-12-31 | month | naive-range | flat | +0.00 | -0.48 | ✅ | 0.48 | ✅ |  | matured 2026-02-02 |
| NVDA | 2025-12-31 | day | tilt-technicals | flat | +0.00 | +1.26 | ❌ | 1.26 | ✅ |  | matured 2026-01-02 |
| NVDA | 2025-12-31 | week | tilt-technicals | flat | +0.60 | -0.78 | ❌ | 1.38 | ✅ |  | matured 2026-01-08 |
| NVDA | 2025-12-31 | month | tilt-technicals | up | +1.24 | -0.48 | ❌ | 1.72 | ✅ |  | matured 2026-02-02 |
| SWDY.CA | 2025-12-31 | day | 2-family-ensemble | flat | +0.00 | -1.60 | ❌ | 1.60 | ✅ |  | matured 2026-01-04 |
| SWDY.CA | 2025-12-31 | week | 2-family-ensemble | flat | +0.00 | +2.84 | ❌ | 2.84 | ✅ |  | matured 2026-01-11 |
| SWDY.CA | 2025-12-31 | month | 2-family-ensemble | flat | +0.00 | +2.25 | ❌ | 2.25 | ✅ |  | matured 2026-02-03 |
| SWDY.CA | 2025-12-31 | day | kronos-alone | flat | +0.26 | -1.60 | ❌ | 1.86 | ❌ |  | matured 2026-01-04 |
| SWDY.CA | 2025-12-31 | week | kronos-alone | up | +3.75 | +2.84 | ✅ | 0.91 | ✅ |  | matured 2026-01-11 |
| SWDY.CA | 2025-12-31 | month | kronos-alone | up | +8.07 | +2.25 | ✅ | 5.82 | ❌ |  | matured 2026-02-03 |
| SWDY.CA | 2025-12-31 | day | family-technicals | flat | +0.45 | -1.60 | ❌ | 2.05 | ✅ |  | matured 2026-01-04 |
| SWDY.CA | 2025-12-31 | week | family-technicals | up | +1.00 | +2.84 | ✅ | 1.84 | ✅ |  | matured 2026-01-11 |
| SWDY.CA | 2025-12-31 | month | family-technicals | up | +2.05 | +2.25 | ✅ | 0.20 | ✅ |  | matured 2026-02-03 |
| SWDY.CA | 2025-12-31 | day | buy-and-hold | flat | +0.00 | -1.60 | ❌ | 1.60 | ✅ |  | matured 2026-01-04 |
| SWDY.CA | 2025-12-31 | week | buy-and-hold | flat | +0.00 | +2.84 | ❌ | 2.84 | ✅ |  | matured 2026-01-11 |
| SWDY.CA | 2025-12-31 | month | buy-and-hold | flat | +0.00 | +2.25 | ❌ | 2.25 | ✅ |  | matured 2026-02-03 |
| SWDY.CA | 2025-12-31 | day | naive-range | flat | +0.00 | -1.60 | ❌ | 1.60 | ✅ |  | matured 2026-01-04 |
| SWDY.CA | 2025-12-31 | week | naive-range | flat | +0.00 | +2.84 | ❌ | 2.84 | ✅ |  | matured 2026-01-11 |
| SWDY.CA | 2025-12-31 | month | naive-range | flat | +0.00 | +2.25 | ❌ | 2.25 | ✅ |  | matured 2026-02-03 |
| SWDY.CA | 2025-12-31 | day | tilt-technicals | flat | +0.00 | -1.60 | ❌ | 1.60 | ✅ |  | matured 2026-01-04 |
| SWDY.CA | 2025-12-31 | week | tilt-technicals | flat | +0.50 | +2.84 | ❌ | 2.34 | ✅ |  | matured 2026-01-11 |
| SWDY.CA | 2025-12-31 | month | tilt-technicals | up | +1.02 | +2.25 | ✅ | 1.23 | ✅ |  | matured 2026-02-03 |
| TMGH.CA | 2025-12-31 | day | 2-family-ensemble | flat | +0.00 | -3.75 | ❌ | 3.75 | ❌ |  | matured 2026-01-04 |
| TMGH.CA | 2025-12-31 | week | 2-family-ensemble | flat | +0.00 | -2.51 | ❌ | 2.51 | ✅ |  | matured 2026-01-11 |
| TMGH.CA | 2025-12-31 | month | 2-family-ensemble | flat | +0.00 | +10.55 | ❌ | 10.55 | ✅ |  | matured 2026-02-03 |
| TMGH.CA | 2025-12-31 | day | kronos-alone | down | -2.12 | -3.75 | ✅ | 1.63 | ❌ |  | matured 2026-01-04 |
| TMGH.CA | 2025-12-31 | week | kronos-alone | down | -3.68 | -2.51 | ✅ | 1.17 | ✅ |  | matured 2026-01-11 |
| TMGH.CA | 2025-12-31 | month | kronos-alone | down | -17.01 | +10.55 | ❌ | 27.56 | ❌ |  | matured 2026-02-03 |
| TMGH.CA | 2025-12-31 | day | family-technicals | flat | +0.28 | -3.75 | ❌ | 4.03 | ❌ |  | matured 2026-01-04 |
| TMGH.CA | 2025-12-31 | week | family-technicals | flat | +0.62 | -2.51 | ❌ | 3.13 | ✅ |  | matured 2026-01-11 |
| TMGH.CA | 2025-12-31 | month | family-technicals | up | +1.27 | +10.55 | ✅ | 9.28 | ✅ |  | matured 2026-02-03 |
| TMGH.CA | 2025-12-31 | day | buy-and-hold | flat | +0.00 | -3.75 | ❌ | 3.75 | ❌ |  | matured 2026-01-04 |
| TMGH.CA | 2025-12-31 | week | buy-and-hold | flat | +0.00 | -2.51 | ❌ | 2.51 | ✅ |  | matured 2026-01-11 |
| TMGH.CA | 2025-12-31 | month | buy-and-hold | flat | +0.00 | +10.55 | ❌ | 10.55 | ✅ |  | matured 2026-02-03 |
| TMGH.CA | 2025-12-31 | day | naive-range | flat | +0.00 | -3.75 | ❌ | 3.75 | ❌ |  | matured 2026-01-04 |
| TMGH.CA | 2025-12-31 | week | naive-range | flat | +0.00 | -2.51 | ❌ | 2.51 | ✅ |  | matured 2026-01-11 |
| TMGH.CA | 2025-12-31 | month | naive-range | flat | +0.00 | +10.55 | ❌ | 10.55 | ✅ |  | matured 2026-02-03 |
| TMGH.CA | 2025-12-31 | day | tilt-technicals | flat | +0.00 | -3.75 | ❌ | 3.75 | ❌ |  | matured 2026-01-04 |
| TMGH.CA | 2025-12-31 | week | tilt-technicals | flat | +0.31 | -2.51 | ❌ | 2.82 | ✅ |  | matured 2026-01-11 |
| TMGH.CA | 2025-12-31 | month | tilt-technicals | flat | +0.63 | +10.55 | ❌ | 9.92 | ✅ |  | matured 2026-02-03 |
| COMI.CA | 2026-03-31 | day | 2-family-ensemble | flat | +0.00 | +3.13 | ❌ | 3.13 | ❌ |  | matured 2026-04-01 |
| COMI.CA | 2026-03-31 | week | 2-family-ensemble | flat | +0.00 | +0.83 | ❌ | 0.83 | ✅ |  | matured 2026-04-07 |
| COMI.CA | 2026-03-31 | month | 2-family-ensemble | flat | +0.00 | +12.40 | ❌ | 12.40 | ✅ |  | matured 2026-05-03 |
| COMI.CA | 2026-03-31 | day | kronos-alone | flat | +0.48 | +3.13 | ❌ | 2.65 | ❌ |  | matured 2026-04-01 |
| COMI.CA | 2026-03-31 | week | kronos-alone | flat | +0.47 | +0.83 | ❌ | 0.36 | ✅ |  | matured 2026-04-07 |
| COMI.CA | 2026-03-31 | month | kronos-alone | down | -10.46 | +12.40 | ❌ | 22.86 | ❌ |  | matured 2026-05-03 |
| COMI.CA | 2026-03-31 | day | family-technicals | flat | -0.52 | +3.13 | ❌ | 3.65 | ✅ |  | matured 2026-04-01 |
| COMI.CA | 2026-03-31 | week | family-technicals | down | -1.16 | +0.83 | ❌ | 1.99 | ✅ |  | matured 2026-04-07 |
| COMI.CA | 2026-03-31 | month | family-technicals | down | -2.38 | +12.40 | ❌ | 14.78 | ✅ |  | matured 2026-05-03 |
| COMI.CA | 2026-03-31 | day | buy-and-hold | flat | +0.00 | +3.13 | ❌ | 3.13 | ✅ |  | matured 2026-04-01 |
| COMI.CA | 2026-03-31 | week | buy-and-hold | flat | +0.00 | +0.83 | ❌ | 0.83 | ✅ |  | matured 2026-04-07 |
| COMI.CA | 2026-03-31 | month | buy-and-hold | flat | +0.00 | +12.40 | ❌ | 12.40 | ✅ |  | matured 2026-05-03 |
| COMI.CA | 2026-03-31 | day | naive-range | flat | +0.00 | +3.13 | ❌ | 3.13 | ✅ |  | matured 2026-04-01 |
| COMI.CA | 2026-03-31 | week | naive-range | flat | +0.00 | +0.83 | ❌ | 0.83 | ✅ |  | matured 2026-04-07 |
| COMI.CA | 2026-03-31 | month | naive-range | flat | +0.00 | +12.40 | ❌ | 12.40 | ✅ |  | matured 2026-05-03 |
| COMI.CA | 2026-03-31 | day | tilt-technicals | flat | +0.00 | +3.13 | ❌ | 3.13 | ❌ |  | matured 2026-04-01 |
| COMI.CA | 2026-03-31 | week | tilt-technicals | flat | -0.45 | +0.83 | ❌ | 1.28 | ✅ |  | matured 2026-04-07 |
| COMI.CA | 2026-03-31 | month | tilt-technicals | down | -0.91 | +12.40 | ❌ | 13.31 | ✅ |  | matured 2026-05-03 |
| ETEL.CA | 2026-03-31 | day | 2-family-ensemble | flat | +0.00 | +7.52 | ❌ | 7.52 | ❌ |  | matured 2026-04-01 |
| ETEL.CA | 2026-03-31 | week | 2-family-ensemble | flat | +0.00 | +11.85 | ❌ | 11.85 | ❌ |  | matured 2026-04-07 |
| ETEL.CA | 2026-03-31 | month | 2-family-ensemble | flat | +0.00 | +18.97 | ❌ | 18.97 | ✅ |  | matured 2026-05-03 |
| ETEL.CA | 2026-03-31 | day | kronos-alone | down | -0.87 | +7.52 | ❌ | 8.39 | ❌ |  | matured 2026-04-01 |
| ETEL.CA | 2026-03-31 | week | kronos-alone | down | -7.67 | +11.85 | ❌ | 19.52 | ❌ |  | matured 2026-04-07 |
| ETEL.CA | 2026-03-31 | month | kronos-alone | down | -24.49 | +18.97 | ❌ | 43.46 | ❌ |  | matured 2026-05-03 |
| ETEL.CA | 2026-03-31 | day | family-technicals | flat | -0.40 | +7.52 | ❌ | 7.92 | ❌ |  | matured 2026-04-01 |
| ETEL.CA | 2026-03-31 | week | family-technicals | down | -0.89 | +11.85 | ❌ | 12.74 | ❌ |  | matured 2026-04-07 |
| ETEL.CA | 2026-03-31 | month | family-technicals | down | -1.83 | +18.97 | ❌ | 20.80 | ✅ |  | matured 2026-05-03 |
| ETEL.CA | 2026-03-31 | day | buy-and-hold | flat | +0.00 | +7.52 | ❌ | 7.52 | ❌ |  | matured 2026-04-01 |
| ETEL.CA | 2026-03-31 | week | buy-and-hold | flat | +0.00 | +11.85 | ❌ | 11.85 | ❌ |  | matured 2026-04-07 |
| ETEL.CA | 2026-03-31 | month | buy-and-hold | flat | +0.00 | +18.97 | ❌ | 18.97 | ✅ |  | matured 2026-05-03 |
| ETEL.CA | 2026-03-31 | day | naive-range | flat | +0.00 | +7.52 | ❌ | 7.52 | ❌ |  | matured 2026-04-01 |
| ETEL.CA | 2026-03-31 | week | naive-range | flat | +0.00 | +11.85 | ❌ | 11.85 | ❌ |  | matured 2026-04-07 |
| ETEL.CA | 2026-03-31 | month | naive-range | flat | +0.00 | +18.97 | ❌ | 18.97 | ✅ |  | matured 2026-05-03 |
| ETEL.CA | 2026-03-31 | day | tilt-technicals | flat | +0.00 | +7.52 | ❌ | 7.52 | ❌ |  | matured 2026-04-01 |
| ETEL.CA | 2026-03-31 | week | tilt-technicals | flat | -0.45 | +11.85 | ❌ | 12.30 | ❌ |  | matured 2026-04-07 |
| ETEL.CA | 2026-03-31 | month | tilt-technicals | down | -0.91 | +18.97 | ❌ | 19.88 | ✅ |  | matured 2026-05-03 |
| NVDA | 2026-03-31 | day | 2-family-ensemble | flat | +0.00 | +0.77 | ❌ | 0.77 | ✅ |  | matured 2026-04-01 |
| NVDA | 2026-03-31 | week | 2-family-ensemble | flat | +0.00 | +4.40 | ❌ | 4.40 | ✅ |  | matured 2026-04-08 |
| NVDA | 2026-03-31 | month | 2-family-ensemble | flat | +0.00 | +14.43 | ❌ | 14.43 | ❌ |  | matured 2026-04-30 |
| NVDA | 2026-03-31 | day | kronos-alone | up | +1.35 | +0.77 | ✅ | 0.58 | ✅ |  | matured 2026-04-01 |
| NVDA | 2026-03-31 | week | kronos-alone | up | +5.85 | +4.40 | ✅ | 1.45 | ✅ |  | matured 2026-04-08 |
| NVDA | 2026-03-31 | month | kronos-alone | up | +10.60 | +14.43 | ✅ | 3.83 | ✅ |  | matured 2026-04-30 |
| NVDA | 2026-03-31 | day | family-technicals | flat | -0.48 | +0.77 | ❌ | 1.25 | ✅ |  | matured 2026-04-01 |
| NVDA | 2026-03-31 | week | family-technicals | down | -1.08 | +4.40 | ❌ | 5.48 | ✅ |  | matured 2026-04-08 |
| NVDA | 2026-03-31 | month | family-technicals | down | -2.21 | +14.43 | ❌ | 16.64 | ❌ |  | matured 2026-04-30 |
| NVDA | 2026-03-31 | day | buy-and-hold | flat | +0.00 | +0.77 | ❌ | 0.77 | ✅ |  | matured 2026-04-01 |
| NVDA | 2026-03-31 | week | buy-and-hold | flat | +0.00 | +4.40 | ❌ | 4.40 | ✅ |  | matured 2026-04-08 |
| NVDA | 2026-03-31 | month | buy-and-hold | flat | +0.00 | +14.43 | ❌ | 14.43 | ✅ |  | matured 2026-04-30 |
| NVDA | 2026-03-31 | day | index-baseline | flat | +0.00 | +0.72 | ✅ | 0.72 | ❌ |  | matured 2026-04-01 |
| NVDA | 2026-03-31 | week | index-baseline | flat | +0.00 | +3.90 | ❌ | 3.90 | ❌ |  | matured 2026-04-08 |
| NVDA | 2026-03-31 | month | index-baseline | flat | +0.00 | +10.42 | ❌ | 10.42 | ❌ |  | matured 2026-04-30 |
| NVDA | 2026-03-31 | day | naive-range | flat | +0.00 | +0.77 | ❌ | 0.77 | ✅ |  | matured 2026-04-01 |
| NVDA | 2026-03-31 | week | naive-range | flat | +0.00 | +4.40 | ❌ | 4.40 | ✅ |  | matured 2026-04-08 |
| NVDA | 2026-03-31 | month | naive-range | flat | +0.00 | +14.43 | ❌ | 14.43 | ❌ |  | matured 2026-04-30 |
| NVDA | 2026-03-31 | day | tilt-technicals | flat | +0.00 | +0.77 | ❌ | 0.77 | ✅ |  | matured 2026-04-01 |
| NVDA | 2026-03-31 | week | tilt-technicals | flat | -0.47 | +4.40 | ❌ | 4.87 | ✅ |  | matured 2026-04-08 |
| NVDA | 2026-03-31 | month | tilt-technicals | down | -0.95 | +14.43 | ❌ | 15.38 | ❌ |  | matured 2026-04-30 |
| TMGH.CA | 2026-03-31 | day | 2-family-ensemble | flat | +0.00 | +6.03 | ❌ | 6.03 | ❌ |  | matured 2026-04-01 |
| TMGH.CA | 2026-03-31 | week | 2-family-ensemble | flat | +0.00 | +4.28 | ❌ | 4.28 | ✅ |  | matured 2026-04-07 |
| TMGH.CA | 2026-03-31 | month | 2-family-ensemble | flat | +0.00 | +28.86 | ❌ | 28.86 | ❌ |  | matured 2026-05-03 |
| TMGH.CA | 2026-03-31 | day | kronos-alone | up | +1.69 | +6.03 | ✅ | 4.34 | ❌ |  | matured 2026-04-01 |
| TMGH.CA | 2026-03-31 | week | kronos-alone | up | +7.12 | +4.28 | ✅ | 2.84 | ✅ |  | matured 2026-04-07 |
| TMGH.CA | 2026-03-31 | month | kronos-alone | up | +9.43 | +28.86 | ✅ | 19.43 | ❌ |  | matured 2026-05-03 |
| TMGH.CA | 2026-03-31 | day | family-technicals | flat | -0.38 | +6.03 | ❌ | 6.41 | ❌ |  | matured 2026-04-01 |
| TMGH.CA | 2026-03-31 | week | family-technicals | down | -0.84 | +4.28 | ❌ | 5.12 | ✅ |  | matured 2026-04-07 |
| TMGH.CA | 2026-03-31 | month | family-technicals | down | -1.73 | +28.86 | ❌ | 30.59 | ❌ |  | matured 2026-05-03 |
| TMGH.CA | 2026-03-31 | day | buy-and-hold | flat | +0.00 | +6.03 | ❌ | 6.03 | ❌ |  | matured 2026-04-01 |
| TMGH.CA | 2026-03-31 | week | buy-and-hold | flat | +0.00 | +4.28 | ❌ | 4.28 | ✅ |  | matured 2026-04-07 |
| TMGH.CA | 2026-03-31 | month | buy-and-hold | flat | +0.00 | +28.86 | ❌ | 28.86 | ❌ |  | matured 2026-05-03 |
| TMGH.CA | 2026-03-31 | day | naive-range | flat | +0.00 | +6.03 | ❌ | 6.03 | ❌ |  | matured 2026-04-01 |
| TMGH.CA | 2026-03-31 | week | naive-range | flat | +0.00 | +4.28 | ❌ | 4.28 | ✅ |  | matured 2026-04-07 |
| TMGH.CA | 2026-03-31 | month | naive-range | flat | +0.00 | +28.86 | ❌ | 28.86 | ❌ |  | matured 2026-05-03 |
| TMGH.CA | 2026-03-31 | day | tilt-technicals | flat | +0.00 | +6.03 | ❌ | 6.03 | ❌ |  | matured 2026-04-01 |
| TMGH.CA | 2026-03-31 | week | tilt-technicals | flat | -0.42 | +4.28 | ❌ | 4.70 | ✅ |  | matured 2026-04-07 |
| TMGH.CA | 2026-03-31 | month | tilt-technicals | down | -0.86 | +28.86 | ❌ | 29.72 | ❌ |  | matured 2026-05-03 |

## Data gaps & notes

- rescore592/2023-12-29/COMI.CA: tilt-technicals day: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2023-12-29/COMI.CA: tilt-technicals week: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2023-12-29/COMI.CA: tilt-technicals month: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2023-12-29/COMI.CA: ensemble.json has no sigma60_daily — naive-range built from sigma_daily as proxy (#594)
- rescore592/2023-12-29/COMI.CA: index-baseline unavailable — index fetch failed: Yahoo chart fetch failed for ^EGX30 after 3 attempts: HTTP Error 404: Not Found
- rescore592/2023-12-29/ETEL.CA: tilt-technicals day: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2023-12-29/ETEL.CA: tilt-technicals week: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2023-12-29/ETEL.CA: tilt-technicals month: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2023-12-29/ETEL.CA: ensemble.json has no sigma60_daily — naive-range built from sigma_daily as proxy (#594)
- rescore592/2023-12-29/ETEL.CA: index-baseline unavailable — index fetch failed: Yahoo chart fetch failed for ^EGX30 after 3 attempts: HTTP Error 404: Not Found
- rescore592/2023-12-29/HRHO.CA: tilt-technicals day: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2023-12-29/HRHO.CA: tilt-technicals week: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2023-12-29/HRHO.CA: tilt-technicals month: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2023-12-29/HRHO.CA: ensemble.json has no sigma60_daily — naive-range built from sigma_daily as proxy (#594)
- rescore592/2023-12-29/HRHO.CA: index-baseline unavailable — index fetch failed: Yahoo chart fetch failed for ^EGX30 after 3 attempts: HTTP Error 404: Not Found
- rescore592/2023-12-29/NVDA: tilt-technicals day: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2023-12-29/NVDA: tilt-technicals week: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2023-12-29/NVDA: tilt-technicals month: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2023-12-29/NVDA: ensemble.json has no sigma60_daily — naive-range built from sigma_daily as proxy (#594)
- rescore592/2023-12-29/SWDY.CA: tilt-technicals day: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2023-12-29/SWDY.CA: tilt-technicals week: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2023-12-29/SWDY.CA: tilt-technicals month: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2023-12-29/SWDY.CA: ensemble.json has no sigma60_daily — naive-range built from sigma_daily as proxy (#594)
- rescore592/2023-12-29/SWDY.CA: index-baseline unavailable — index fetch failed: Yahoo chart fetch failed for ^EGX30 after 3 attempts: HTTP Error 404: Not Found
- rescore592/2023-12-29/TMGH.CA: tilt-technicals day: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2023-12-29/TMGH.CA: tilt-technicals week: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2023-12-29/TMGH.CA: tilt-technicals month: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2023-12-29/TMGH.CA: ensemble.json has no sigma60_daily — naive-range built from sigma_daily as proxy (#594)
- rescore592/2023-12-29/TMGH.CA: index-baseline unavailable — index fetch failed: Yahoo chart fetch failed for ^EGX30 after 3 attempts: HTTP Error 404: Not Found
- rescore592/2024-03-31/NVDA: tilt-technicals day: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2024-03-31/NVDA: tilt-technicals week: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2024-03-31/NVDA: tilt-technicals month: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2024-03-31/NVDA: ensemble.json has no sigma60_daily — naive-range built from sigma_daily as proxy (#594)
- rescore592/2024-06-30/NVDA: tilt-technicals day: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2024-06-30/NVDA: tilt-technicals week: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2024-06-30/NVDA: tilt-technicals month: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2024-06-30/NVDA: ensemble.json has no sigma60_daily — naive-range built from sigma_daily as proxy (#594)
- rescore592/2024-09-30/COMI.CA: tilt-technicals day: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2024-09-30/COMI.CA: tilt-technicals week: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2024-09-30/COMI.CA: tilt-technicals month: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2024-09-30/COMI.CA: ensemble.json has no sigma60_daily — naive-range built from sigma_daily as proxy (#594)
- rescore592/2024-09-30/COMI.CA: index-baseline unavailable — index fetch failed: Yahoo chart fetch failed for ^EGX30 after 3 attempts: HTTP Error 404: Not Found
- rescore592/2024-09-30/ETEL.CA: tilt-technicals day: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2024-09-30/ETEL.CA: tilt-technicals week: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2024-09-30/ETEL.CA: tilt-technicals month: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2024-09-30/ETEL.CA: ensemble.json has no sigma60_daily — naive-range built from sigma_daily as proxy (#594)
- rescore592/2024-09-30/ETEL.CA: index-baseline unavailable — index fetch failed: Yahoo chart fetch failed for ^EGX30 after 3 attempts: HTTP Error 404: Not Found
- rescore592/2024-09-30/HRHO.CA: tilt-technicals day: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2024-09-30/HRHO.CA: tilt-technicals week: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2024-09-30/HRHO.CA: tilt-technicals month: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2024-09-30/HRHO.CA: ensemble.json has no sigma60_daily — naive-range built from sigma_daily as proxy (#594)
- rescore592/2024-09-30/HRHO.CA: index-baseline unavailable — index fetch failed: Yahoo chart fetch failed for ^EGX30 after 3 attempts: HTTP Error 404: Not Found
- rescore592/2024-09-30/NVDA: tilt-technicals day: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2024-09-30/NVDA: tilt-technicals week: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2024-09-30/NVDA: tilt-technicals month: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2024-09-30/NVDA: ensemble.json has no sigma60_daily — naive-range built from sigma_daily as proxy (#594)
- rescore592/2024-09-30/SWDY.CA: tilt-technicals day: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2024-09-30/SWDY.CA: tilt-technicals week: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2024-09-30/SWDY.CA: tilt-technicals month: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2024-09-30/SWDY.CA: ensemble.json has no sigma60_daily — naive-range built from sigma_daily as proxy (#594)
- rescore592/2024-09-30/SWDY.CA: index-baseline unavailable — index fetch failed: Yahoo chart fetch failed for ^EGX30 after 3 attempts: HTTP Error 404: Not Found
- rescore592/2024-09-30/TMGH.CA: tilt-technicals day: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2024-09-30/TMGH.CA: tilt-technicals week: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2024-09-30/TMGH.CA: tilt-technicals month: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2024-09-30/TMGH.CA: ensemble.json has no sigma60_daily — naive-range built from sigma_daily as proxy (#594)
- rescore592/2024-09-30/TMGH.CA: index-baseline unavailable — index fetch failed: Yahoo chart fetch failed for ^EGX30 after 3 attempts: HTTP Error 404: Not Found
- rescore592/2024-12-31/COMI.CA: tilt-technicals day: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2024-12-31/COMI.CA: tilt-technicals week: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2024-12-31/COMI.CA: tilt-technicals month: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2024-12-31/COMI.CA: ensemble.json has no sigma60_daily — naive-range built from sigma_daily as proxy (#594)
- rescore592/2024-12-31/COMI.CA: index-baseline unavailable — index fetch failed: Yahoo chart fetch failed for ^EGX30 after 3 attempts: HTTP Error 404: Not Found
- rescore592/2024-12-31/ETEL.CA: tilt-technicals day: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2024-12-31/ETEL.CA: tilt-technicals week: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2024-12-31/ETEL.CA: tilt-technicals month: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2024-12-31/ETEL.CA: ensemble.json has no sigma60_daily — naive-range built from sigma_daily as proxy (#594)
- rescore592/2024-12-31/ETEL.CA: index-baseline unavailable — index fetch failed: Yahoo chart fetch failed for ^EGX30 after 3 attempts: HTTP Error 404: Not Found
- rescore592/2024-12-31/HRHO.CA: tilt-technicals day: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2024-12-31/HRHO.CA: tilt-technicals week: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2024-12-31/HRHO.CA: tilt-technicals month: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2024-12-31/HRHO.CA: ensemble.json has no sigma60_daily — naive-range built from sigma_daily as proxy (#594)
- rescore592/2024-12-31/HRHO.CA: index-baseline unavailable — index fetch failed: Yahoo chart fetch failed for ^EGX30 after 3 attempts: HTTP Error 404: Not Found
- rescore592/2024-12-31/NVDA: tilt-technicals day: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2024-12-31/NVDA: tilt-technicals week: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2024-12-31/NVDA: tilt-technicals month: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2024-12-31/NVDA: ensemble.json has no sigma60_daily — naive-range built from sigma_daily as proxy (#594)
- rescore592/2024-12-31/SWDY.CA: tilt-technicals day: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2024-12-31/SWDY.CA: tilt-technicals week: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2024-12-31/SWDY.CA: tilt-technicals month: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2024-12-31/SWDY.CA: ensemble.json has no sigma60_daily — naive-range built from sigma_daily as proxy (#594)
- rescore592/2024-12-31/SWDY.CA: index-baseline unavailable — index fetch failed: Yahoo chart fetch failed for ^EGX30 after 3 attempts: HTTP Error 404: Not Found
- rescore592/2024-12-31/TMGH.CA: tilt-technicals day: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2024-12-31/TMGH.CA: tilt-technicals week: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2024-12-31/TMGH.CA: tilt-technicals month: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2024-12-31/TMGH.CA: ensemble.json has no sigma60_daily — naive-range built from sigma_daily as proxy (#594)
- rescore592/2024-12-31/TMGH.CA: index-baseline unavailable — index fetch failed: Yahoo chart fetch failed for ^EGX30 after 3 attempts: HTTP Error 404: Not Found
- rescore592/2025-03-31/COMI.CA: tilt-technicals day: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2025-03-31/COMI.CA: tilt-technicals week: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2025-03-31/COMI.CA: tilt-technicals month: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2025-03-31/COMI.CA: ensemble.json has no sigma60_daily — naive-range built from sigma_daily as proxy (#594)
- rescore592/2025-03-31/COMI.CA: index-baseline unavailable — index fetch failed: Yahoo chart fetch failed for ^EGX30 after 3 attempts: HTTP Error 404: Not Found
- rescore592/2025-03-31/ETEL.CA: tilt-technicals day: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2025-03-31/ETEL.CA: tilt-technicals week: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2025-03-31/ETEL.CA: tilt-technicals month: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2025-03-31/ETEL.CA: ensemble.json has no sigma60_daily — naive-range built from sigma_daily as proxy (#594)
- rescore592/2025-03-31/ETEL.CA: index-baseline unavailable — index fetch failed: Yahoo chart fetch failed for ^EGX30 after 3 attempts: HTTP Error 404: Not Found
- rescore592/2025-03-31/HRHO.CA: tilt-technicals day: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2025-03-31/HRHO.CA: tilt-technicals week: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2025-03-31/HRHO.CA: tilt-technicals month: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2025-03-31/HRHO.CA: ensemble.json has no sigma60_daily — naive-range built from sigma_daily as proxy (#594)
- rescore592/2025-03-31/HRHO.CA: index-baseline unavailable — index fetch failed: Yahoo chart fetch failed for ^EGX30 after 3 attempts: HTTP Error 404: Not Found
- rescore592/2025-03-31/NVDA: tilt-technicals day: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2025-03-31/NVDA: tilt-technicals week: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2025-03-31/NVDA: tilt-technicals month: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2025-03-31/NVDA: ensemble.json has no sigma60_daily — naive-range built from sigma_daily as proxy (#594)
- rescore592/2025-03-31/SWDY.CA: tilt-technicals day: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2025-03-31/SWDY.CA: tilt-technicals week: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2025-03-31/SWDY.CA: tilt-technicals month: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2025-03-31/SWDY.CA: ensemble.json has no sigma60_daily — naive-range built from sigma_daily as proxy (#594)
- rescore592/2025-03-31/SWDY.CA: index-baseline unavailable — index fetch failed: Yahoo chart fetch failed for ^EGX30 after 3 attempts: HTTP Error 404: Not Found
- rescore592/2025-03-31/TMGH.CA: tilt-technicals day: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2025-03-31/TMGH.CA: tilt-technicals week: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2025-03-31/TMGH.CA: tilt-technicals month: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2025-03-31/TMGH.CA: ensemble.json has no sigma60_daily — naive-range built from sigma_daily as proxy (#594)
- rescore592/2025-03-31/TMGH.CA: index-baseline unavailable — index fetch failed: Yahoo chart fetch failed for ^EGX30 after 3 attempts: HTTP Error 404: Not Found
- rescore592/2025-06-30/COMI.CA: tilt-technicals day: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2025-06-30/COMI.CA: tilt-technicals week: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2025-06-30/COMI.CA: tilt-technicals month: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2025-06-30/COMI.CA: ensemble.json has no sigma60_daily — naive-range built from sigma_daily as proxy (#594)
- rescore592/2025-06-30/COMI.CA: index-baseline unavailable — index fetch failed: Yahoo chart fetch failed for ^EGX30 after 3 attempts: HTTP Error 404: Not Found
- rescore592/2025-06-30/ETEL.CA: tilt-technicals day: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2025-06-30/ETEL.CA: tilt-technicals week: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2025-06-30/ETEL.CA: tilt-technicals month: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2025-06-30/ETEL.CA: ensemble.json has no sigma60_daily — naive-range built from sigma_daily as proxy (#594)
- rescore592/2025-06-30/ETEL.CA: index-baseline unavailable — index fetch failed: Yahoo chart fetch failed for ^EGX30 after 3 attempts: HTTP Error 404: Not Found
- rescore592/2025-06-30/HRHO.CA: tilt-technicals day: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2025-06-30/HRHO.CA: tilt-technicals week: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2025-06-30/HRHO.CA: tilt-technicals month: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2025-06-30/HRHO.CA: ensemble.json has no sigma60_daily — naive-range built from sigma_daily as proxy (#594)
- rescore592/2025-06-30/HRHO.CA: index-baseline unavailable — index fetch failed: Yahoo chart fetch failed for ^EGX30 after 3 attempts: HTTP Error 404: Not Found
- rescore592/2025-06-30/NVDA: tilt-technicals day: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2025-06-30/NVDA: tilt-technicals week: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2025-06-30/NVDA: tilt-technicals month: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2025-06-30/NVDA: ensemble.json has no sigma60_daily — naive-range built from sigma_daily as proxy (#594)
- rescore592/2025-06-30/SWDY.CA: tilt-technicals day: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2025-06-30/SWDY.CA: tilt-technicals week: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2025-06-30/SWDY.CA: tilt-technicals month: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2025-06-30/SWDY.CA: ensemble.json has no sigma60_daily — naive-range built from sigma_daily as proxy (#594)
- rescore592/2025-06-30/SWDY.CA: index-baseline unavailable — index fetch failed: Yahoo chart fetch failed for ^EGX30 after 3 attempts: HTTP Error 404: Not Found
- rescore592/2025-06-30/TMGH.CA: tilt-technicals day: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2025-06-30/TMGH.CA: tilt-technicals week: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2025-06-30/TMGH.CA: tilt-technicals month: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2025-06-30/TMGH.CA: ensemble.json has no sigma60_daily — naive-range built from sigma_daily as proxy (#594)
- rescore592/2025-06-30/TMGH.CA: index-baseline unavailable — index fetch failed: Yahoo chart fetch failed for ^EGX30 after 3 attempts: HTTP Error 404: Not Found
- rescore592/2025-09-30/COMI.CA: tilt-technicals day: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2025-09-30/COMI.CA: tilt-technicals week: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2025-09-30/COMI.CA: tilt-technicals month: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2025-09-30/COMI.CA: ensemble.json has no sigma60_daily — naive-range built from sigma_daily as proxy (#594)
- rescore592/2025-09-30/COMI.CA: index-baseline unavailable — index fetch failed: Yahoo chart fetch failed for ^EGX30 after 3 attempts: HTTP Error 404: Not Found
- rescore592/2025-09-30/ETEL.CA: tilt-technicals day: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2025-09-30/ETEL.CA: tilt-technicals week: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2025-09-30/ETEL.CA: tilt-technicals month: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2025-09-30/ETEL.CA: ensemble.json has no sigma60_daily — naive-range built from sigma_daily as proxy (#594)
- rescore592/2025-09-30/ETEL.CA: index-baseline unavailable — index fetch failed: Yahoo chart fetch failed for ^EGX30 after 3 attempts: HTTP Error 404: Not Found
- rescore592/2025-09-30/HRHO.CA: index-baseline unavailable — index fetch failed: Yahoo chart fetch failed for ^EGX30 after 3 attempts: HTTP Error 404: Not Found
- rescore592/2025-09-30/NVDA: tilt-technicals day: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2025-09-30/NVDA: tilt-technicals week: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2025-09-30/NVDA: tilt-technicals month: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2025-09-30/NVDA: ensemble.json has no sigma60_daily — naive-range built from sigma_daily as proxy (#594)
- rescore592/2025-09-30/SWDY.CA: index-baseline unavailable — index fetch failed: Yahoo chart fetch failed for ^EGX30 after 3 attempts: HTTP Error 404: Not Found
- rescore592/2025-09-30/TMGH.CA: tilt-technicals day: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2025-09-30/TMGH.CA: tilt-technicals week: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2025-09-30/TMGH.CA: tilt-technicals month: no usable tilt_centre_pct — horizon skipped (#689)
- rescore592/2025-09-30/TMGH.CA: ensemble.json has no sigma60_daily — naive-range built from sigma_daily as proxy (#594)
- rescore592/2025-09-30/TMGH.CA: index-baseline unavailable — index fetch failed: Yahoo chart fetch failed for ^EGX30 after 3 attempts: HTTP Error 404: Not Found
- rescore592/2025-12-31/COMI.CA: index-baseline unavailable — index fetch failed: Yahoo chart fetch failed for ^EGX30 after 3 attempts: HTTP Error 404: Not Found
- rescore592/2025-12-31/ETEL.CA: index-baseline unavailable — index fetch failed: Yahoo chart fetch failed for ^EGX30 after 3 attempts: HTTP Error 404: Not Found
- rescore592/2025-12-31/HRHO.CA: index-baseline unavailable — index fetch failed: Yahoo chart fetch failed for ^EGX30 after 3 attempts: HTTP Error 404: Not Found
- rescore592/2025-12-31/SWDY.CA: index-baseline unavailable — index fetch failed: Yahoo chart fetch failed for ^EGX30 after 3 attempts: HTTP Error 404: Not Found
- rescore592/2025-12-31/TMGH.CA: index-baseline unavailable — index fetch failed: Yahoo chart fetch failed for ^EGX30 after 3 attempts: HTTP Error 404: Not Found
- rescore592/2026-03-31/COMI.CA: index-baseline unavailable — index fetch failed: Yahoo chart fetch failed for ^EGX30 after 3 attempts: HTTP Error 404: Not Found
- rescore592/2026-03-31/ETEL.CA: index-baseline unavailable — index fetch failed: Yahoo chart fetch failed for ^EGX30 after 3 attempts: HTTP Error 404: Not Found
- rescore592/2026-03-31/TMGH.CA: index-baseline unavailable — index fetch failed: Yahoo chart fetch failed for ^EGX30 after 3 attempts: HTTP Error 404: Not Found

_Backtest scores are an upper bound on live skill (see the warning above). The forward ledger remains the only basis for accuracy claims._
