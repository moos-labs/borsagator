# Conversion-profit scoring on the FX hold-out (INS-IMPROVE-158)

Numbers only. Rule: evaluation/pre_registration_fx_metals.md section 12 (written before scoring). Hold-out 2026-01-01 to last matured session (asof 2026-11-28). 5000 reps, seed 20261125. Costs are unverified working assumptions: majors 0.07% and EGP 0.2% round trip; section 6 grid 0.1/0.5/1/2 also shown.

Cells: 247 total, 65 scored (n>=30 and >=10 clusters), 21 counts only, 161 abstain (training rows under 30).
Scored cells with conservative edge > registered cost: 0. By grid value: 0.1: 0, 0.5: 0, 1: 0, 2: 0.

## Highest conservative edges (%, gain after direction fitted on training; cost in last column)

| cell | n | clusters | mean gain | conservative edge | cost |
|---|---|---|---|---|---|
| GBPEGP|day|dow0 | 47 | 11 | 0.338 | 0.058 | 0.20 |
| EURJPY|day|dow0 | 47 | 11 | 0.092 | 0.008 | 0.07 |
| USDCHF|day|dow3 | 47 | 11 | 0.081 | -0.050 | 0.07 |
| EURGBP|day|dow2 | 47 | 11 | -0.004 | -0.057 | 0.07 |
| USDCAD|day|dow2 | 47 | 11 | 0.019 | -0.058 | 0.07 |
| EURGBP|day|dow1 | 47 | 11 | 0.002 | -0.062 | 0.07 |
| USDJPY|day|dow0 | 47 | 11 | 0.028 | -0.064 | 0.07 |
| USDCAD|day|dow0 | 47 | 11 | -0.011 | -0.087 | 0.07 |

## Triangular cycles (identity residual, hold-out, direction fitted on training)

| direct leg | n | clusters | mean residual gain % | conservative edge % | cycle cost % |
|---|---|---|---|---|---|
| EUREGP | 206 | 11 | 0.0058 | -0.0248 | 0.300 |
| EURGBP | 206 | 11 | 0.0074 | 0.0060 | 0.105 |
| EURJPY | 206 | 11 | 0.0063 | 0.0051 | 0.105 |
| GBPEGP | 206 | 11 | 0.0100 | 0.0066 | 0.300 |

Caveats: Friday sessions are thin in the hold-out data (Yahoo dates many Friday bars as Sunday; the registered session rule merges Sunday into Monday), so the Friday bucket is counts only. Month-start and month-of-year buckets are counts only or abstain (training rows under 30). The triangular residual is a close-timing difference between separately quoted series, not a tradable gain. Per-cell numbers: evaluation/fx_conversion_run.json.
