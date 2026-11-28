# Crypto round 147, first descriptive run (frozen v2 vs naive)

Window: cutoffs 2024-01-01 to 2025-12-31 every 30 days; reps 5000, seed 20261125; cutoff-clustered 95% percentile CIs. Descriptive: no verdict word, no KEEP. BTC+ETH pooled counts one cluster per cutoff.

| horizon | asset | n | clusters | RangeSkill vs naive | CI95 | coverage v2 | coverage CI95 |
|---|---|---|---|---|---|---|---|
| day (1) | BTC-USD | 25 | 25 | +0.006 | [-0.048, +0.074] | 0.800 | [0.640, 0.960] |
| day (1) | ETH-USD | 25 | 25 | +0.011 | [-0.033, +0.077] | 0.800 | [0.640, 0.960] |
| day (1) | BTC+ETH pooled | 50 | 25 | +0.009 | [-0.037, +0.070] | 0.800 | [0.640, 0.940] |
| week (7) | BTC-USD | 25 | 25 | +0.000 | [-0.000, +0.001] | 0.880 | [0.760, 1.000] |
| week (7) | ETH-USD | 25 | 25 | +0.001 | [-0.000, +0.001] | 0.880 | [0.760, 1.000] |
| week (7) | BTC+ETH pooled | 50 | 25 | +0.001 | [-0.000, +0.001] | 0.880 | [0.760, 0.980] |
| month (30) | BTC-USD | 25 | 25 | +0.012 | [-0.011, +0.054] | 0.840 | [0.680, 0.960] |
| month (30) | ETH-USD | 25 | 25 | -0.019 | [-0.045, +0.017] | 0.680 | [0.480, 0.840] |
| month (30) | BTC+ETH pooled | 50 | 25 | -0.007 | [-0.028, +0.026] | 0.760 | [0.600, 0.900] |

Launch-gate target +0.10, point estimate (reported separately from the loop CI bar; no label attached):
- day BTC-USD: +0.006
- day ETH-USD: +0.011
- day BTC+ETH pooled: +0.009
- week BTC-USD: +0.000
- week ETH-USD: +0.001
- week BTC+ETH pooled: +0.001
- month BTC-USD: +0.012
- month ETH-USD: -0.019
- month BTC+ETH pooled: -0.007

Excluded rows (0):
