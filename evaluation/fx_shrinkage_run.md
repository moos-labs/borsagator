# #966 shrinkage challenger on the FX hold-out (INS-IMPROVE-159)

Numbers only. Rule: evaluation/pre_registration_fx_metals.md section 13 (written before any shrinkage value was computed). Hold-out 2026-01-01 to the last matured session (asof 2026-11-28). 5000 reps, seed 20261125. Fit on sessions before 2026-01-01 only.

Fit: one shared pair on 4047 pooled covered training rows (EURUSD, USDJPY, USDEGP x day/week/month): a = 0.85, b = 0.85. Mean training interval score 2.4642, against 2.4662 at a = b = 1 (frozen v2). Zero-move gate: passed on every cell.

| cell | horizon/rows | n | clusters | RS challenger | RS v2 | delta | delta CI95 | coverage ch / v2 | crossed | label |
|---|---|---|---|---|---|---|---|---|---|---|
| AEDEGP_DERIVED | day/all_rows | 186 | 10 | 0.0169 | 0.0112 | +0.0057 | [-0.0060, 0.0220] | 0.769 / 0.796 | 0 | DESCRIPTIVE ONLY (derived cross-rate) |
| AEDEGP_DERIVED | day/jump_days_excluded | 1 | 1 | counts only | | | | | 0 | COUNTS ONLY (fewer than 10 mature clusters) |
| AEDEGP_DERIVED | month/all_rows | 9 | 9 | counts only | | | | | 0 | COUNTS ONLY (fewer than 10 mature clusters) |
| AEDEGP_DERIVED | month/jump_days_excluded | 0 | 0 | counts only | | | | | 0 | COUNTS ONLY (fewer than 10 mature clusters) |
| AEDEGP_DERIVED | week/all_rows | 38 | 10 | -0.0100 | -0.0001 | -0.0099 | [-0.0353, 0.0228] | 0.711 / 0.737 | 0 | DESCRIPTIVE ONLY (derived cross-rate) |
| AEDEGP_DERIVED | week/jump_days_excluded | 0 | 0 | counts only | | | | | 0 | COUNTS ONLY (fewer than 10 mature clusters) |
| EURUSD | day/all_rows | 186 | 10 | 0.0068 | -0.0048 | +0.0116 | [-0.0018, 0.0258] | 0.769 / 0.758 | 0 | NOT KEEP-ELIGIBLE |
| EURUSD | month/all_rows | 9 | 9 | counts only | | | | | 0 | COUNTS ONLY (fewer than 10 mature clusters) |
| EURUSD | week/all_rows | 38 | 10 | 0.0105 | -0.0003 | +0.0108 | [-0.0157, 0.0358] | 0.711 / 0.684 | 0 | NOT KEEP-ELIGIBLE |
| SAREGP_DERIVED | day/all_rows | 186 | 10 | 0.0044 | 0.0059 | -0.0015 | [-0.0130, 0.0119] | 0.742 / 0.774 | 0 | DESCRIPTIVE ONLY (derived cross-rate) |
| SAREGP_DERIVED | day/jump_days_excluded | 1 | 1 | counts only | | | | | 0 | COUNTS ONLY (fewer than 10 mature clusters) |
| SAREGP_DERIVED | month/all_rows | 9 | 9 | counts only | | | | | 0 | COUNTS ONLY (fewer than 10 mature clusters) |
| SAREGP_DERIVED | month/jump_days_excluded | 0 | 0 | counts only | | | | | 0 | COUNTS ONLY (fewer than 10 mature clusters) |
| SAREGP_DERIVED | week/all_rows | 38 | 10 | -0.0156 | -0.0002 | -0.0154 | [-0.0475, 0.0248] | 0.684 / 0.711 | 0 | DESCRIPTIVE ONLY (derived cross-rate) |
| SAREGP_DERIVED | week/jump_days_excluded | 0 | 0 | counts only | | | | | 0 | COUNTS ONLY (fewer than 10 mature clusters) |
| USDEGP | day/all_rows | 186 | 10 | 0.0160 | 0.0112 | +0.0047 | [-0.0069, 0.0214] | 0.763 / 0.796 | 0 | NOT KEEP-ELIGIBLE |
| USDEGP | day/jump_days_excluded | 1 | 1 | counts only | | | | | 0 | COUNTS ONLY (fewer than 10 mature clusters) |
| USDEGP | month/all_rows | 9 | 9 | counts only | | | | | 0 | COUNTS ONLY (fewer than 10 mature clusters) |
| USDEGP | month/jump_days_excluded | 0 | 0 | counts only | | | | | 0 | COUNTS ONLY (fewer than 10 mature clusters) |
| USDEGP | week/all_rows | 38 | 10 | -0.0098 | -0.0001 | -0.0097 | [-0.0348, 0.0231] | 0.711 / 0.737 | 0 | NOT KEEP-ELIGIBLE |
| USDEGP | week/jump_days_excluded | 0 | 0 | counts only | | | | | 0 | COUNTS ONLY (fewer than 10 mature clusters) |
| USDJPY | day/all_rows | 186 | 10 | 0.0155 | 0.0178 | -0.0023 | [-0.0123, 0.0048] | 0.849 / 0.839 | 0 | NOT KEEP-ELIGIBLE |
| USDJPY | month/all_rows | 9 | 9 | counts only | | | | | 0 | COUNTS ONLY (fewer than 10 mature clusters) |
| USDJPY | week/all_rows | 38 | 10 | 0.0003 | 0.0002 | +0.0002 | [-0.0059, 0.0079] | 0.842 / 0.842 | 0 | NOT KEEP-ELIGIBLE |

Counts-only rows: fewer than 10 fully mature monthly clusters (month horizon, and the jump-excluded EGP rows, which keep one or no mature cluster). Per-cell detail and listings: evaluation/fx_shrinkage_run.json. Design choices (log-percent baseline moves, pooled fit over the three non-derived cells, one shared pair): section 13.
