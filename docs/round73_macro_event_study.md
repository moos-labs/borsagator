# Round 73: macro-event calendar (primary-sourced) and descriptive event study

Task INS-IMPROVE-073 (Moos, Slack 1795786265.970709, read in full). Follow-up to the #929 design (docs/round72_macro_event_design.md; its section 7 secondary-source lists are superseded by this doc). DESCRIPTIVE: no p-value, no verdict word or key. The calendar commit precedes the code and every number.

## Scope
EGX30 Mubasher close (evaluation/index_regime/EGX30_mubasher_close.csv, 2019-01-02 to 2026-11-26). Moos's decision (Slack 1795786248.607069): whole CBE history with the 2021-09-05 regime split (round-16 rule); events on or after 2021-09-05 are 'post'. The series starts in 2019, so usable history is 2019 onward.

## Calendar (evaluation/macro_event/calendar_primary.json)
47 primary-sourced events: 39 scheduled CBE MPC decision days, 4 special CBE meetings (2020-03-16, 2022-03-21, 2022-10-27, 2024-03-06) and 4 budget presentations (2021-04-30, 2022-05-09, 2025-04-15, 2026-04-22). Primary = CBE press release or annual report, MoF release. Resolved: Mar 2024 = 6 Mar 2024 (special MPC, CBE release); Apr 2025 = 17 Apr 2025 (CBE release). The 2026-04-22 budget date is the date of the MoF release about the House presentation, not a separately stated session date.

Excluded (not sourced to a primary page), never filled from memory:
- CBE 2022-08-18: day only in secondary schedule; annual report confirms an Aug 2022 meeting
- CBE 2022-11-03: on the 2022 schedule, no primary source that it was held or cancelled
- CBE 2023-02-02: day only in secondary schedules; annual report confirms a Feb 2023 meeting
- CBE 2019-01 to 2020-02, 2020-05 to 2020-11, 2021-02 to 2021-07: no primary page found by search; CBE year tabs not rendered by the fetcher
- Budget 2023/24 (about 11 May 2023) and 2024/25 (23 Apr 2024): secondary only (Mada Masr, Al-Masry Al-Youm, Asharq Al-Awsat); MoF release dates not found
- Elections: presidential 2023 result (18 Dec 2023), Senate 2025, House 2025 results: elections.eg pages found (pres-2024-result, decisions 34/2025, 75, 79/2025, 1 and 2/2026) but the announcement date is not stated in the page text read; dates from Reuters/Ahram/Xinhua are secondary; excluded
- Elections 2020: not collected, no primary page read

## Method
Session 0 = first EGX30 session on or after the event date (time of day is not modelled; a release after the close would belong to the next session). Log returns. Window sessions -2..+2. Estimation sessions -60..-11 excluding any session inside another event's window. Abnormal return = return minus the estimation mean. Per type and regime: AAR per offset, mean CAR(-2,+2), and the LOEO min and max of the mean CAR. Events lacking 60 pre-sessions, 2 post-sessions or 20 estimation returns would be skipped and counted (none were).

## Results (descriptive)

| type | regime | n | AAR -2 | AAR -1 | AAR 0 | AAR +1 | AAR +2 | mean CAR | LOEO min..max |
|---|---|---|---|---|---|---|---|---|---|
| budget | post | 3 | +0.0113 | +0.0038 | -0.0054 | -0.0011 | +0.0028 | +0.0115 | +0.0016..+0.0173 |
| budget | pre | 1 | +0.0090 | -0.0083 | +0.0018 | +0.0073 | +0.0099 | +0.0198 | n=1 |
| cbe_scheduled | post | 37 | +0.0007 | -0.0039 | -0.0010 | -0.0027 | +0.0002 | -0.0067 | -0.0088..-0.0048 |
| cbe_scheduled | pre | 2 | -0.0010 | +0.0006 | +0.0005 | -0.0039 | +0.0063 | +0.0025 | -0.0017..+0.0068 |
| cbe_special | post | 3 | +0.0200 | +0.0093 | +0.0195 | +0.0201 | +0.0250 | +0.0939 | +0.0917..+0.0955 |
| cbe_special | pre | 1 | +0.0004 | -0.0971 | -0.0726 | -0.0235 | -0.0486 | -0.2414 | n=1 |

Reading limits: pre-split cells hold 1 to 2 events, so no pre/post comparison is supported. The three post-split special CBE meetings (2022-03-21, 2022-10-27, 2024-03-06) are devaluation or float events and are not a scheduled-decision effect. EGX30 index only; no per-ticker returns used.

No band replay and no keep rule is run (decision 2, 1795786248.607069). Reproduce: python3 benchmarks/macro_event_study.py --json evaluation/macro_event/macro_event_study_descriptive.json; tests: scripts/test_macro_event_study.py (20 checks).
