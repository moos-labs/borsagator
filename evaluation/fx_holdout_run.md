# FX hold-out run (numbers only)

Hold-out sessions 2026-01-01 to the last matured session (asof UTC date 2026-11-28, partial day dropped). v2 k {'day': 1.15, 'week': 1.28, 'month': 1.2} (frozen, not refit), naive k 1.2816, 5000 reps, seed 20261125, whole-cluster resampling, cluster = calendar month of the cutoff.

Zero-move gate (RangeSkill of a [0,0] band vs naive; positive = stop):

- EURUSD day all_rows n=186: -1.0665
- EURUSD week all_rows n=38: -0.9847
- EURUSD month all_rows n=9: -1.1960
- USDJPY day all_rows n=186: -0.7324
- USDJPY week all_rows n=38: -0.7977
- USDJPY month all_rows n=9: -1.0849
- USDEGP day all_rows n=186: -0.6914
- USDEGP day jump_days_excluded n=1: -0.8351
- USDEGP week all_rows n=38: -1.0084
- USDEGP month all_rows n=9: -0.9735
- SAREGP_DERIVED day all_rows n=186: -0.6550
- SAREGP_DERIVED day jump_days_excluded n=1: -1.4559
- SAREGP_DERIVED week all_rows n=38: -0.9868
- SAREGP_DERIVED month all_rows n=9: -0.6648
- AEDEGP_DERIVED day all_rows n=186: -0.6918
- AEDEGP_DERIVED day jump_days_excluded n=1: -0.8460
- AEDEGP_DERIVED week all_rows n=38: -1.0119
- AEDEGP_DERIVED month all_rows n=9: -0.9746

| Cell | Horizon/rows | n | mature clusters | RangeSkill [CI] | cov v2 [CI] | rule |
|---|---|---|---|---|---|---|
| EURUSD | day/all_rows | 186 | 10 | -0.0048 [-0.0355, 0.0324] | 0.758 [0.657, 0.856] | NOT KEEP-ELIGIBLE |
| EURUSD | week/all_rows | 38 | 10 | -0.0003 [-0.0007, 0.0001] | 0.684 [0.513, 0.833] | NOT KEEP-ELIGIBLE |
| EURUSD | month/all_rows | 9 | 9 | counts only | counts only | COUNTS ONLY (fewer than 10 mature clusters) |
| USDJPY | day/all_rows | 186 | 10 | 0.0178 [-0.0046, 0.0464] | 0.839 [0.764, 0.911] | NOT KEEP-ELIGIBLE |
| USDJPY | week/all_rows | 38 | 10 | 0.0002 [-0.0002, 0.0008] | 0.842 [0.718, 0.949] | NOT KEEP-ELIGIBLE |
| USDJPY | month/all_rows | 9 | 9 | counts only | counts only | COUNTS ONLY (fewer than 10 mature clusters) |
| USDEGP | day/all_rows | 186 | 10 | 0.0112 [-0.0078, 0.0370] | 0.796 [0.720, 0.868] | NOT KEEP-ELIGIBLE |
| USDEGP | day/jump_days_excluded | 1 | 1 | counts only | counts only | COUNTS ONLY (fewer than 10 mature clusters) |
| USDEGP | week/all_rows | 38 | 10 | -0.0001 [-0.0005, 0.0005] | 0.737 [0.615, 0.875] | NOT KEEP-ELIGIBLE |
| USDEGP | week/jump_days_excluded | 0 | 0 | counts only | counts only | no matured rows |
| USDEGP | month/all_rows | 9 | 9 | counts only | counts only | COUNTS ONLY (fewer than 10 mature clusters) |
| USDEGP | month/jump_days_excluded | 0 | 0 | counts only | counts only | no matured rows |
| SAREGP_DERIVED | day/all_rows | 186 | 10 | 0.0059 [-0.0072, 0.0212] | 0.774 [0.721, 0.825] | DESCRIPTIVE ONLY (derived cross-rate) |
| SAREGP_DERIVED | day/jump_days_excluded | 1 | 1 | counts only | counts only | COUNTS ONLY (fewer than 10 mature clusters) |
| SAREGP_DERIVED | week/all_rows | 38 | 10 | -0.0002 [-0.0007, 0.0004] | 0.711 [0.590, 0.838] | DESCRIPTIVE ONLY (derived cross-rate) |
| SAREGP_DERIVED | week/jump_days_excluded | 0 | 0 | counts only | counts only | no matured rows |
| SAREGP_DERIVED | month/all_rows | 9 | 9 | counts only | counts only | COUNTS ONLY (fewer than 10 mature clusters) |
| SAREGP_DERIVED | month/jump_days_excluded | 0 | 0 | counts only | counts only | no matured rows |
| AEDEGP_DERIVED | day/all_rows | 186 | 10 | 0.0112 [-0.0078, 0.0369] | 0.796 [0.720, 0.868] | DESCRIPTIVE ONLY (derived cross-rate) |
| AEDEGP_DERIVED | day/jump_days_excluded | 1 | 1 | counts only | counts only | COUNTS ONLY (fewer than 10 mature clusters) |
| AEDEGP_DERIVED | week/all_rows | 38 | 10 | -0.0001 [-0.0005, 0.0005] | 0.737 [0.615, 0.875] | DESCRIPTIVE ONLY (derived cross-rate) |
| AEDEGP_DERIVED | week/jump_days_excluded | 0 | 0 | counts only | counts only | no matured rows |
| AEDEGP_DERIVED | month/all_rows | 9 | 9 | counts only | counts only | COUNTS ONLY (fewer than 10 mature clusters) |
| AEDEGP_DERIVED | month/jump_days_excluded | 0 | 0 | counts only | counts only | no matured rows |

SAREGP_DERIVED: {"common_dates_kept": 236, "dropped_total": 0, "dropped_usdegp_only": 0, "dropped_usdsar_only": 0, "overlap_rate_common_over_union": 1.0, "overlap_rate_common_over_usdegp": 1.0, "usdegp_dates": 236, "usdsar_dates": 236, "window": ["2026-01-01", "before 2026-11-28"]}

AEDEGP_DERIVED: {"common_dates_kept": 236, "dropped_total": 0, "dropped_usdaed_only": 0, "dropped_usdegp_only": 0, "overlap_rate_common_over_union": 1.0, "overlap_rate_common_over_usdegp": 1.0, "usdaed_dates": 236, "usdegp_dates": 236, "window": ["2026-01-01", "before 2026-11-28"]}
