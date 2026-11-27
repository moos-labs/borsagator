# Round 87 follow-up: were the MPC decision dates public before each cutoff? (check only, no change to #945)

Question: the MPC-window screen (PR #945) flags a window from the realised decision series. Which cells change flag if a date counts only when it was public strictly before the cutoff date?

## Result
Numbered cells use 17 distinct cutoff dates (2023-12-29 to 2026-09-30). Across 17 cutoffs x 3 horizons, 0 rows change flag. Run: `python3 benchmarks/mpc_publication_check.py --captures <archive>` (data: evaluation/macro_series/mpc_calendar_publication.json).

Why the answer does not depend on the exact publication date: each year's first meeting (2024-02-01, 2025-02-20, 2026-02-12) lies more than 21 sessions after the last cutoff of the year before (2023-12-29, 2024-12-31, 2025-12-31), so no cutoff has a next-year date in its window before that year's calendar was out. Every other in-window date belongs to a calendar published the previous December or earlier. The only unscheduled change in the span, the special meeting of 2024-03-06 (and the cancelled 2024-03-28 meeting), lies in no numbered cell's window (cutoffs 2023-12-29 and 2024-03-31). The flag set is the same under both rules for every numbered cell.

## Per-year calendar and when it became public
| Year | Scheduled dates | First public on or before | Evidence (kind) |
|---|---|---|---|
| 2024 | 1 Feb, 28 Mar, 23 May, 18 Jul, 5 Sep, 17 Oct, 21 Nov, 26 Dec | 2023-12-22 | https://www.almasryalyoum.com/news/details/3059375 (secondary, reports the CBE statement); https://www.masrawy.com/news/news-banking/details/2023/12/23/2514029/ (secondary, all 8 dates) |
| 2025 | 20 Feb, 17 Apr, 22 May, 10 Jul, 28 Aug, 2 Oct, 20 Nov, 25 Dec | 2024-12-28 | https://almalnews.com/1928572/ (secondary, says the CBE announced it on its website) |
| 2026 | 12 Feb, 2 Apr, 21 May, 9 Jul, 20 Aug, 24 Sep, 29 Oct, 17 Dec | 2025-12-29 | https://www.elwatannews.com/news/details/8198821 (secondary); https://www.elnabaa.net/1151778 (secondary, all 8 dates) |

Every realised decision in the series from 2024-02-01 on matches a scheduled date, except 2024-03-06 (special, announced the day it was held: https://www.cbe.org.eg/en/news-publications/news/2024/03/06/05/42/special-mpc-press-release-6-march-2024) and the scheduled 2024-03-28 meeting, which was cancelled (https://www.cbe.org.eg/en/news-publications/news/2024/03/20/11/52/press-release-the-mpc-meeting-scheduled-for-28-march-2024-has-been-cancelled, 2024-03-20, primary).

## What is and is not primary
- Primary: the CBE press releases for each decision (the series source URLs), the 2024-03-06 special release and the 2024-03-20 cancellation notice.
- Not primary: the dates the yearly calendars became public. The CBE schedule page (https://www.cbe.org.eg/en/monetary-policy/mpc-meetings-schedule) draws its year tabs with a script and shows no publication date to the fetcher. The Wayback snapshot of 2023-11-10 (http://web.archive.org/web/20231110182034/https://www.cbe.org.eg/en/monetary-policy/mpc-meetings-schedule) lists year tabs from 2023 down, no 2024 tab, which bounds the 2024 calendar as not public by 2023-11-10. Later snapshots returned a request-rejected page, so no primary bound exists for the 2025 and 2026 calendars. Publication dates above are the dates of the earliest press reports I found, and the real first publication may be earlier. This does not change the result, for the reason given above.
- The 2026-12-17 meeting is outside the decision series (not yet held), so it does not enter any cell.
