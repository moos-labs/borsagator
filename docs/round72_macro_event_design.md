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
