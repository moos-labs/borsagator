# Round 72: scheduled macro-event adjustment route, design and pre-registration

Status: DESIGN ONLY. No return, abnormal return or score is computed in this
document or its commit. Task: INS-IMPROVE-072 item 2 (Moos, Slack
1795785741.851629, read in full; panel round 35 idea ranked 3). Descriptive
first, no verdict word or key. Nothing edits scripts/ensemble.py or frozen
values. Kronos stays gated at weight 0.

## 1. Event types and calendar (public sources only)

Window: 5 years, 2021-11-27 to 2026-11-27 (decision for Moos: the CBE page
tabs go back to 2005, so 5 years is a cut, not a source limit).

| Type | Event date definition | Status of the calendar |
|---|---|---|
| CBE MPC decision | decision day (Thursday) | 2026: 8 dates taken from the CBE schedule as reported by press and aggregators (12 Feb, 2 Apr, 21 May, 9 Jul, 20 Aug, 24 Sep, 29 Oct, 17 Dec). Dec 2023 to Dec 2025: aggregator list (wealthbranch.com) with 16 dates; two are ambiguous (Mar 2024 decision shown 5 Mar 20:30 vs 6 Mar; Apr 2025 shown 17 and 18 Apr). 2021 to Nov 2023 not yet collected. PRIMARY page (cbe.org.eg/en/monetary-policy/mpc-meetings-schedule) shows year tabs that the fetcher does not render, so each date must be read from the CBE page or CBE press release before use. Extraordinary meetings count only if CBE announced them. |
| Budget announcement | date the finance minister presents the draft budget to the House (not parliamentary approval) | MoF release: 2025/26 presented 15 Apr 2025 (mof.gov.eg press release dated 15 Apr 2025); approvals 17 Jun 2025 (Ahram, 19 Jun 2025) and 22 Jun 2026. Presentation dates for 2021/22 to 2024/25 and 2026/27 still to collect from MoF. |
| Election release | National Elections Authority results announcement, per round | Senate 2025 round 1 held 4 Aug 2025 (IFES), House 2025 round 1 held 10 Nov 2025 (IFES). Results announcement dates and the 2023 presidential and any 2021 to 2024 releases still to collect from elections.eg. |

Each calendar row stores: type, date, time of day if public, source URL,
whether the release is pre-market (EGX session Sun to Thu), and
announcement-vs-schedule flag. Dates that cannot be sourced to a primary page
are excluded and listed, never filled from memory.

## 2. Event study (descriptive)

Return series: EGX30 close from evaluation/index_regime/EGX30_mubasher_close.csv
(Mubasher basis only; Yahoo is never mixed in) and per-ticker closes from the
replay captures where held. Event window: sessions -2..+2 around the event
session (session 0 = first EGX session at or after the release; release after
the close counts to the next session). Abnormal return = session log return
minus the same-ticker (or index) mean over a non-event estimation window
(sessions -60..-11 relative to the event, excluding other events' windows).
Average abnormal return (AAR) per event type and per window session, plus
the cumulative -2/+2 value. Cross-event dispersion is reported with a
leave-one-event-out (LOEO) spread; no p-value, no verdict word.

## 3. Sign-adjusted bias on frozen v2

Frozen v2 centre is 0. The bias moves the centre on event days only:
  centre_e = sign(AAR_type) x min(|AAR_type|, cap) estimated LEAVING OUT the
  scored event (LOEO), applied only to captures whose cutoff session is
  within the -2..+2 window of an event of that type.
Band half-width stays the frozen v2 half-width. No fit on cells 48 onward:
the training window for any fitted quantity is cells 1-47 only (event dates
before the first scored cutoff may feed AAR; the AAR itself never uses a
scored row's own forward move). Cells 48-90 descriptive only; clean block
cells 91+.

## 4. Pre-registered keep rule (loop bar), fixed before any number

KEEP needs all of: RangeSkill (vs frozen v2, same rows) cutoff-clustered CI
lower bound > 0 on every horizon; cutoff-clustered coverage CI overlapping
[0.75, 0.85] with width <= 0.15; >= 10 cutoff clusters of EVENT-WINDOW
captures on cells >= 91; >= 30 rows and >= 5 tickers per horizon. Fewer
clusters than 10 is reported as a count, never as a pass or fail. Any
descriptive run (cells 48-102, LOEO) prints no verdict word or key. One
scoring only.

## 5. Power check (counts only, no returns)

Using the 24 CBE dates in section 1 and the 97 scored cells on main
(aa2b4a060), cutoff dates inside a +-2 session window of a CBE decision:
- cells 1-47: 42 cells, 8 cutoffs, 1 cutoff in window (4 cells)
- cells 48-90: 43 cells, 8 cutoffs, 2 cutoffs in window (8 cells)
- cells 91-102: 12 cells, 2 cutoffs, 0 cutoffs in window
- cells 48-102: 55 cells, 10 cutoffs, 2 in window (8 cells)
So the loop bar (>= 10 event-window cutoff clusters on cells >= 91) cannot be
reached on the current grid, and the backtest holds 3 event-window cutoffs
in total. Budget and election events add dates but not cutoffs. The route is
therefore evaluable only through (a) the EGX30 and per-ticker event study
(no band scoring) or (b) new captures scheduled at event windows. Option (b)
is a capture-planning change and is NOT started here.

## 6. Decisions requested from Moos

1. Window: keep 5 years, or use the whole CBE history on the CBE page.
2. Accept the power check as a reason to run the event study descriptively
   only and not build the sign-adjusted band replay until event-window
   captures exist.
3. Approve collecting the missing primary dates (CBE 2021 to Nov 2023,
   MoF presentations, elections.eg results) as the next step before any
   return is computed.

## 7. Calendar collection update (doc only, no return computed)

Scope kept at 5 years (2021-11-27 to 2026-11-27), per Moos (Slack
1795786179.511379). Dates marked PRIMARY were read from a CBE press release
or CBE annual report; SECONDARY from press or an aggregator and still to be
confirmed from a primary page. Nothing below uses memory.

### 7.1 CBE MPC decision days
Resolved ambiguities:
- Mar 2024: **6 Mar 2024**, special MPC meeting. PRIMARY: CBE "Special MPC
  Press Release 6 March 2024" (cbe.org.eg/en/news-publications/news/2024/03/06/05/42/special-mpc-press-release-6-march-2024)
  and annual report 2023/24 ("special meeting held on March 6, 2024"). The
  aggregator's 5 Mar 20:30 entry is wrong for the event date; release was on
  the morning of 6 Mar, the pound float and 600 bp hike are the same event.
- Apr 2025: **17 Apr 2025**. PRIMARY: CBE "MPC Press Release 17 April 2025"
  (cbe.org.eg/en/news-publications/news/2025/04/17/15/09/mpc-press-release-17-april-2025).
  The aggregator's 18 Apr row is a duplicate and is dropped.

Collected for the window start (2021-11-27) to Dec 2023:
| Date | Kind | Source status |
|---|---|---|
| 2021-12-16 | scheduled | PRIMARY, CBE annual report 2021/22 ("August 5, September 16, October 28, and December 16, 2021") |
| 2022-02-03 | scheduled | PRIMARY, same report |
| 2022-03-21 | special (100 bp hike; scheduled 24 Mar cancelled) | PRIMARY, CBE press release (mpc-meetin_6_en.pdf) and annual report |
| 2022-05-19 | scheduled (+200 bp) | PRIMARY, annual report 2021/22 |
| 2022-06-23 | scheduled | PRIMARY, annual report 2021/22 |
| 2022-08-18 | scheduled | SECONDARY (Amwal Al Ghad 2022 schedule); annual report 2022/23 confirms an Aug 2022 meeting |
| 2022-09-22 | scheduled | PRIMARY, annual report 2022/23 ("second meeting on September 22nd, 2022") |
| 2022-10-27 | special (+200 bp) | PRIMARY, annual reports 2021/22 and 2022/23 |
| 2022-11-03 | scheduled on the published calendar | UNRESOLVED: on the 2022 schedule (Amwal Al Ghad) but no primary source found that it was held or cancelled; excluded until read from the CBE page |
| 2022-12-22 | scheduled (+300 bp) | PRIMARY, annual report 2022/23 |
| 2023-02-02 | scheduled (hold) | SECONDARY (Amwal Al Ghad 2023 schedule, Enterprise 5 Feb 2023); annual report 2022/23 confirms a February 2023 hold; day to confirm |
| 2023-03-30 | scheduled (+200 bp) | PRIMARY, annual report 2022/23 |
| 2023-05-18 | scheduled | SECONDARY (Amwal 2023 schedule, Enterprise calendar) |
| 2023-06-22 | scheduled (hold) | PRIMARY, CBE press release (cbe.org.eg/ar/news-publications/news/2023/06/22/17/52/mpc-press-release-22-june-2023) |
| 2023-08-03 | scheduled (+100 bp) | PRIMARY, annual report 2022/23 |
| 2023-09-21 | scheduled (hold) | PRIMARY, CBE press release (mpc-press-release--21-september-2023.pdf) |
| 2023-11-02 | scheduled (hold) | PRIMARY, CBE press release (mpc-press-release--2-november-2023.pdf) |
| 2023-12-21 | scheduled (hold) | PRIMARY, CBE press release (news/2023/12/21/15/46/mpc-press-release-21-december-2023) |

Note: the aggregator showed 28 Sep 2023 nowhere; the CBE release gives 21 Sep.
Still SECONDARY and to confirm from CBE releases before use: 2024 (1 Feb,
23 May, 18 Jul, 5 Sep, 17 Oct, 21 Nov, 26 Dec), 2025 (20 Feb, 22 May, 10 Jul,
28 Aug, 2 Oct, 20 Nov, 25 Dec), 2026 (8 dates; 12 Feb is the cut).
Special meetings (21 Mar 2022, 27 Oct 2022, 6 Mar 2024) are flagged
"special" and are analysed separately from scheduled decisions.

### 7.2 Budget announcement (draft presented to the House)
| FY | Presented | Source status |
|---|---|---|
| 2022/23 | 9 May 2022 | PRIMARY MoF release (mof.gov.eg, 9 May 2022) and Reuters 9 May 2022 |
| 2023/24 | about 11 May 2023 | SECONDARY (Mada Masr 11 May 2023; Al-Masry Al-Youm 12 May 2023 reports the session); exact day to confirm from MoF |
| 2024/25 | 23 Apr 2024 | SECONDARY (Asharq Al-Awsat, Al-Masry Al-Youm 23 Apr 2024); MoF release to confirm |
| 2025/26 | 15 Apr 2025 | PRIMARY MoF release (15 Apr 2025) |
| 2026/27 | NOT FOUND | presentation date not located; final approval 22 Jun 2026 (Ahram, Zawya). To read from MoF. |
Final House approvals (not the event date): 2025/26 on 17 Jun 2025, 2026/27 on 22 Jun 2026.

### 7.3 Election releases
| Event | Date | Source status |
|---|---|---|
| Presidential result 2023 | 18 Dec 2023 (NEA announcement) | SECONDARY, Reuters 18 Dec 2023, Ahram Online 18 Dec 2023, presidency.eg 18 Dec 2023 |
| Senate 2025 | round 1 vote 4 Aug 2025; runoff results published in the Official Gazette by 4 Sep 2025 | SECONDARY (IFES id 4959; Al-Masdar 4 Sep 2025); NEA results-announcement dates to read from elections.eg |
| House 2025 | round 1 vote 10 Nov 2025; final results 10 Jan 2026 | SECONDARY (IFES id 5001; Ahram Online and Xinhua 10 Jan 2026); round results dates to read from elections.eg |
| 2020 elections | Oct to Dec 2020 | OUTSIDE the 5-year window, not collected |

Open items before any return is computed: primary confirmation of the
SECONDARY rows, the 2022-11-03 held/cancelled status, the 2026/27 budget
presentation date, NEA announcement dates per round. No abnormal return or
score has been computed; section 5 counts still use the earlier 24-date list.
