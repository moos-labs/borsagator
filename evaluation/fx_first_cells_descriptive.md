# FX first descriptive cell set (numbers only)

Training block only (sessions 2019-01-01 to before 2026-01-01; EGP from 2024-03-07, 2024-03-06 excluded). Cutoffs every h sessions (non-overlapping), cluster = calendar month of the cutoff. Bands are +/- k x sigma60 x sqrt(h) on the h-session log close-to-close move (pp); v2 k = frozen EGX values {'day': 1.15, 'week': 1.28, 'month': 1.2}, not refit; naive k = 1.2816. Bootstrap: 5000 reps, seed 20261125, whole-cluster resampling.

| Cell | Horizon / rows | n | clusters | v2 IS | naive IS | RangeSkill v2 vs naive [95% CI] | cov v2 [CI] | cov naive [CI] | RW mean abs move pp | share up |
|---|---|---|---|---|---|---|---|---|---|---|
| EURUSD | day/all_rows | 1549 | 82 | 1.6942 | 1.6954 | 0.0007 [-0.0084, 0.0106] | 0.773 [0.748, 0.798] | 0.821 [0.799, 0.844] | 0.3620 | 0.491 |
| EURUSD | week/all_rows | 309 | 82 | 3.6786 | 3.6792 | 0.0002 [-0.0000, 0.0004] | 0.825 [0.776, 0.869] | 0.825 [0.776, 0.869] | 0.7880 | 0.485 |
| EURUSD | month/all_rows | 73 | 70 | 7.1286 | 7.1062 | -0.0032 [-0.0250, 0.0214] | 0.781 [0.681, 0.873] | 0.795 [0.699, 0.880] | 1.6877 | 0.534 |
| USDJPY | day/all_rows | 1549 | 82 | 2.1308 | 2.1396 | 0.0041 [-0.0058, 0.0145] | 0.778 [0.747, 0.808] | 0.819 [0.791, 0.846] | 0.4309 | 0.531 |
| USDJPY | week/all_rows | 309 | 82 | 4.7381 | 4.7384 | 0.0001 [-0.0001, 0.0003] | 0.799 [0.748, 0.848] | 0.799 [0.748, 0.848] | 0.9811 | 0.557 |
| USDJPY | month/all_rows | 73 | 70 | 9.8545 | 9.8569 | 0.0002 [-0.0196, 0.0232] | 0.781 [0.676, 0.873] | 0.795 [0.694, 0.882] | 1.9671 | 0.562 |
| USDEGP | day/all_rows | 351 | 19 | 1.1396 | 1.1623 | 0.0195 [0.0010, 0.0426] | 0.835 [0.785, 0.883] | 0.852 [0.798, 0.906] | 0.1955 | 0.464 |
| USDEGP | day/jump_days_excluded | 96 | 7 | 1.1138 | 1.1608 | 0.0405 [0.0041, 0.0744] | 0.875 [0.782, 0.939] | 0.896 [0.800, 0.962] | 0.1871 | 0.531 |
| USDEGP | week/all_rows | 70 | 19 | 2.3273 | 2.3287 | 0.0006 [0.0003, 0.0010] | 0.900 [0.843, 0.957] | 0.900 [0.843, 0.957] | 0.4448 | 0.414 |
| USDEGP | week/jump_days_excluded | 18 | 6 | 2.6124 | 2.6139 | 0.0006 [0.0000, 0.0012] | 0.889 [0.750, 1.000] | 0.889 [0.750, 1.000] | 0.4723 | 0.556 |
| USDEGP | month/all_rows | 16 | 16 | 4.5597 | 4.5772 | 0.0038 [-0.0461, 0.0637] | 0.812 [0.625, 1.000] | 0.812 [0.625, 1.000] | 1.0798 | 0.500 |
| USDEGP | month/jump_days_excluded | 3 | 3 | 5.0373 | 5.3799 | 0.0637 [0.0637, 0.0637] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 0.9011 | 0.667 |
