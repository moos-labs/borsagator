# Proposal A readiness (round 34): macro-screen cutoff dates, availability criterion, check-script design

INS-IMPROVE-001 round 34 (Moos, Slack 1795746735.813499, relayed by the parent
agent; the author did not find that message in the loop thread or channel and
cites it as relayed). Docs only: no implementation, no cell scored, no screen
run. Proposal A (GDELT macro-theme volume as a width input,
docs/proposals-round-32.md) is NOT GO'd and still waits on Muhammad's macro GO.
Nothing here starts it.

## 1. The macro-screen cutoff dates in 2019-2023

Definition (specified by this document): the macro screen reuses the existing
screen grid unchanged. For each of the 36 store tickers and each horizon, the
pseudo-cutoffs are every STEP = 21 sessions starting at MIN_HIST = 120 bars,
as_of date D = the date of the last usable bar (screen_band_models.screen_pairs
and screen_market_factor.load, Yahoo close store at archive tip d6ab6b30, bars
after 2023-12-28 dropped, a cutoff needs its full horizon of 1, 5 or 21 sessions
inside the store). A macro-screen cutoff is such a (ticker, horizon, D) with
D from 2019-01-01 to the last bar of the window. Pre/post 2021-09-05 regime
labelling is unchanged.

Counts read from the store by the author (the same grid code the screens use,
36 tickers):

| Year | Distinct D (all horizons) | Day | Week | Month |
|---|---|---|---|---|
| 2019 | 149 | 149 | 149 | 149 |
| 2020 | 145 | 145 | 145 | 145 |
| 2021 | 153 | 153 | 153 | 153 |
| 2022 | 161 | 161 | 161 | 161 |
| 2023 | 161 | 161 | 158 | 147 |

- 769 distinct D dates in total (2019-01-01 to 2023-12-26). They are many
  because each ticker's grid starts at its own 121st bar, so the grids are
  offset from each other. D is a Cairo session date (Sunday to Thursday).
- 6,027 (ticker, horizon, D) cutoffs in all: day 2,022, week 2,019, month
  1,986. Per ticker-horizon grid the median is 58 (min 19, a late-starting
  ticker; max 59). So "about 60 per grid" for a full run is the median.
- A cutoff's rows are limited to what the news screen already uses as point in
  time: GKG rows stamped strictly before 00:00 UTC of D. Rows stamped on D are
  never a feature.

## 2. Per-cutoff availability criterion

Moos's rule (as relayed): macro rows present for the full [t-5, t-1] window plus
the cutoff day. Defined here, with t = D:

- C1 (the relayed criterion): every calendar day in [D-5, D] is COVERED.
- C2 (extra, for the theme_spike width input of Proposal A): every calendar
  day in [D-30, D-1] is also COVERED, because theme_spike compares a day with
  its trailing 30-day mean and standard deviation
  (docs/ins-macro-news-001-preregistration.md). A Proposal A cutoff would need
  C1 and C2. This is the author's addition, to be confirmed.
- COVERED is a coverage test, not a row-count test. A UTC day is covered only
  when every GKG file the master lists carry for that date has been processed
  by the macro channel (listed in STATE/macro_done.txt), for both streams
  (english and translation). A covered day with zero macro rows is reported as
  an anomaly count, not as uncovered, and a day with some but not all files is
  PARTIAL and counts as not covered.
- D's own day is in C1 as a completeness check only (the shard has reached D).
  Its rows are not used, per the point-in-time rule above. Whether D's day
  should be required at all is Moos's call and is flagged here, not decided.
- Why coverage and not row counts: with 15-minute files, 96 per stream per day
  (70,010 files for 2019 is about 2 x 96 x 365, an inference from the relayed
  count, not stated in the relay), a day with half its files gives a plausible
  but wrong count, and the day's count is the signal.

Worked example on the relayed spans (round 33, #862), assuming no gaps in them:

- C1 holds for 65 distinct D dates (first 2019-01-06, last 2023-02-02).
- C1 and C2 hold for 25 distinct D dates (first 2020-02-03, last 2023-02-02).
- Of the 6,027 grid cutoffs, 513 pass C1 (8.5%) and 219 pass C1 and C2 (3.6%,
  about 2 per ticker-horizon grid, matching the round-33 estimate).
- This is availability for the dates covered so far, not for 2019-2023.

## 3. Check-script design (one command once the shards complete)

Design only; the script is not written in this PR. Proposed file
`benchmarks/check_macro_availability.py` (stdlib only, descriptive, no verdict
word or key), with a test file registered in main() and an `__main__` guard.

    python3 benchmarks/check_macro_availability.py \
        --history DIR --master FILE [--master-translation FILE] \
        --state DIR [--state DIR ...] --macro-matches FILE [FILE ...] \
        [--start 2019-01-01] [--end 2023-12-28] [--json OUT]

Inputs and what each gives:

- `--history`: the Yahoo close store. Builds the cutoff grid of section 1
  with the screens' own functions, so the grid cannot drift from the screens.
- `--master` and `--master-translation`: the GDELT master lists the filter
  already takes. Expected file count per UTC date and stream, from the 14-digit
  timestamp prefix of `.gkg.csv.zip` names (the filter's own `list_files`
  rule, imported not copied).
- `--state` (repeatable, one per shard): `STATE/macro_done.txt`. The union of
  file names is the processed set; duplicates across shards are counted once
  and reported.
- `--macro-matches` (repeatable): `macro_matches.jsonl`. Gives per-day row
  counts from the `date` field (YYYYMMDDhhmmss), counting distinct
  (`gkg_record_id`, `url`) as the filter does, so the zero-row anomaly and the
  rows-per-day figures are exact.

Steps: build the per-day coverage table (expected, processed, state COVERED,
PARTIAL or MISSING); build the cutoff grid; flag each cutoff C1 and C1+C2
using the table only; write the outputs.

Output (stdout and JSON): per year and per horizon, the number of cutoffs, the
number passing C1 and C1+C2, and the distinct D count passing; the covered, partial and missing day
counts per year; first and last covered day per shard; covered days with zero
rows; processed names not found in the master list (a mismatch between
shards and master); a fixed sentence "availability for the dates covered, not
a screen result". It exits 0 whatever it finds, since it describes.

Tests planned (fixed synthetic inputs, assertions through the script's
functions and CLI output): per-day coverage with a missing file making a day
PARTIAL; a day covered with zero rows reported as an anomaly; C1 passes at a
boundary and fails when D-5 is partial; C1 passes while C2 fails at a day with
29 prior covered days and passes at 30; rows stamped on D do not change
coverage; duplicate names across two shards counted once; the same grid as
`screen_pairs` (cutoff count equals the grid's on a fixed series). Mutants to
check: coverage replaced by row-count, window off by one on either side, D's
day dropped, union replaced by one shard.

## Not decided here

- Whether D itself belongs in C1 (relayed as yes).
- Whether the width input needs C2, or only the event window needs C1.
- Anything about Proposal A's result or its GO.
