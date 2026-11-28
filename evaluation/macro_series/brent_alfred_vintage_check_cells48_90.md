# Brent ALFRED as-of-cutoff check, descriptive cutoffs (cells 48-90)

Source: ALFRED CSV per cutoff, https://alfred.stlouisfed.org/graph/alfredgraph.csv?id=DCOILBRENTEU&cosd=2024-01-01&vintage_date=CUTOFF. Stored: evaluation/macro_series/brent_daily.csv (published = observed + 3 days). Window 63 days, theta 5 percent, relative.

| Cutoff | Stored usable obs | In vintage | Absent from vintage | Value differs | Stored last / ref | Vintage last / ref | Signal stored | Signal vintage |
|---|---|---|---|---|---|---|---|---|
| 2025-09-30 | 441 | 437 | 4 | 0 | 2025-09-26 71.15 / 2025-07-25 69.23 | 2025-09-22 66.87 / 2025-07-21 71.92 | 0 | -1 |
| 2025-12-31 | 504 | 504 | 0 | 0 | 2025-12-24 63.70 / 2025-10-22 62.28 | same | 0 | 0 |
| 2026-02-13 | 535 | 534 | 1 | 0 | 2026-02-10 71.01 / 2025-12-09 62.62 | 2026-02-09 71.19 / 2025-12-08 63.30 | 1 | 1 |
| 2026-03-31 | 568 | 564 | 4 | 0 | 2026-03-27 121.47 / 2026-01-23 68.16 | 2026-03-23 103.79 / 2026-01-19 66.91 | 1 | 1 |
| 2026-05-15 | 597 | 596 | 1 | 0 | 2026-05-12 111.37 / 2026-03-10 89.84 | 2026-05-11 106.11 / 2026-03-09 94.35 | 1 | 1 |
| 2026-06-30 | 629 | 625 | 4 | 0 | 2026-06-26 70.16 / 2026-04-24 111.86 | 2026-06-22 76.49 / 2026-04-20 103.40 | -1 | -1 |
| 2026-08-14 | 661 | 661 | 0 | 0 | 2026-08-11 93.26 / 2026-06-09 94.15 | same | 0 | 0 |
| 2026-09-30 | 693 | 693 | 0 | 0 | 2026-09-25 116.01 / 2026-07-24 100.31 | same | 1 | 1 |

Revisions: 0 of 4614 observation-vintage pairs differ. Availability: vintage lacks recent days. One cutoff (2025-09-30) crosses the threshold under vintage availability.
