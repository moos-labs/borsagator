# Round 33 data check: macro-theme rows for the 2019-2023 window (availability only)

INS-IMPROVE-001 round 33 (Moos, Slack 1795746150.574969, relayed by the parent
agent; the author did not find that message in the loop thread or channel and
cites it as relayed). Data check only: no implementation, no cell scored, no
screen run.

## What the author could see, and what was relayed

- Looked in: every file listing of every remote branch of moos-labs/borsagator
  (main, the archive branch and all ins/* branches), the archive worktree at
  tip d6ab6b30 (ohlcv, harvest, sweeps, worker-runs), the author's /downloads
  and a filesystem-wide search for macro_matches, gdelt and gkg names. Result:
  the only GDELT files visible are the code, the alias and theme lookup CSVs
  and the docs. No shard output and no macro row is visible to the author. The
  shard outputs live in the shard agents' own sandboxes.
- Everything in the tables below is therefore relayed (shard agents, via the
  parent agent, also posted to Slack) and was not seen by the author. Counts
  are quoted as given and not re-derived, except the percentages and per-day
  means, which are arithmetic on the quoted figures.

## Coverage so far, per shard (macro rows; row counts before dedup)

| Year | Processed / total (as relayed) | Share | Dates covered | Days | Share of year | Macro rows by month |
|---|---|---|---|---|---|---|
| 2019 | 5,406 / 70,010 | 7.7% | 2019-01-01 to 01-29 | 29 | 7.9% | Jan 642,563 |
| 2020 | 7,632 / 64,783 | 11.8% | 2020-01-01 to 02-09 | 40 | 10.9% | Jan 869,866; Feb 158,467 |
| 2021 | 13,200 / 68,740 | 19.2% | 2021-01-01 to 03-10 | 69 | 18.9% | Jan 435,258; Feb 404,826; Mar 153,233 |
| 2022 | 3,072 / 70,000 | 4.4% | 2022-01-01 to 01-16 | 16 | 4.4% | Jan 164,893 |
| 2023 | 6,440 / 69,708 | 9.2% | 2023-01-01 to 02-03 | 34 | 9.3% | Jan 323,550; Feb 29,913 |

- Totals: 3,182,569 rows over 188 covered days out of 1,826 days in 2019-2023,
  which is 10.3%. The processed share of each shard tracks its covered-day
  share within 1 point, so the unit of "processed / total" behaves like the
  GKG files in date order. The relay does not name the unit.
- Mean rows per covered day (arithmetic): 2019 Jan 22,157; 2020 Jan 28,060,
  Feb 17,607 (9 days); 2021 Jan 14,040, Feb 14,458, Mar 15,323 (10 days); 2022
  Jan 10,306; 2023 Jan 10,437, Feb 9,971 (3 days). Partial months are not
  comparable with full ones, and the relay gives no per-day counts, so zero
  or thin days inside a covered span are not visible.
- Catch-up state of 2022 and 2023: 2022 is the thinnest (16 days, 4.4% of its
  files); 2023 has 34 days (9.2%). No year is past 20% of its files, and every
  shard covers a single contiguous run from 1 January, with nothing yet for
  the rest of any year.
- Fields: macro rows keep the exact matched theme tokens (`themes`,
  `theme_families`, `families`, `features`), not the raw Themes field. This
  agrees with the code on main (scripts/gdelt_gkg_filter.py: the macro row
  stores `sorted(matched)` at line 324, built from the full field passed at
  lines 315-317). So the macro channel keeps the full-field match, and any
  per-family count must be taken from the macro rows.

## Per-cutoff availability (availability for dates covered so far only)

This is availability for the dates covered so far, not for the 2019-2023
window as a whole. The check uses the theme_spike definition of the
INS-MACRO-NEWS-001 catalog, which compares a day's count with its trailing
30-day mean and standard deviation (docs/ins-macro-news-001-preregistration.md).
A cutoff on date D needs rows for the 30 days before D, all inside the covered
span (no earlier rows are known to exist).

| Year | First D with 30 covered days before it | Covered D that qualify |
|---|---|---|
| 2019 | none (29 covered days) | 0 |
| 2020 | 2020-01-31 | 10 calendar days (Jan 31 to Feb 9) |
| 2021 | 2021-01-31 | 39 calendar days (Jan 31 to Mar 10) |
| 2022 | none (16 covered days) | 0 |
| 2023 | 2023-01-31 | 4 calendar days (Jan 31 to Feb 3) |

- That is 53 calendar days, about 38 sessions (Sunday to Thursday), across the
  five years. The screens place a cutoff every 21 sessions per ticker and
  horizon, so on average roughly 2 distinct cutoff dates per ticker-horizon
  grid would see a full trailing window today. This is an expectation from
  arithmetic, not a count from the grid. A complete 2019-2023 run would give
  about 60 (5 x 252 / 21).
- Years 2019 and 2022 give no qualifying cutoff at all, and 2020, 2021 and 2023
  give them only in January and February or March. Nothing in the shards
  supports any per-cutoff claim for April through December of any year.

## What this does not establish

- That any shard's remaining files exist or will be processed, or when.
- Whether the covered spans contain gaps (no per-day counts were relayed).
- That the rows after dedup stay close to the pre-dedup counts above.
- Anything about a screen's result. Proposal A of
  docs/proposals-round-32.md is not GO'd and needs Muhammad's macro GO.
