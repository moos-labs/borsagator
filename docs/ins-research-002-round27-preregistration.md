# INS-RESEARCH-002 round 27 pre-registration: results-announcement profit sign vs 21-session excess return

Status: PRE-REGISTERED on merge. Nothing is run on the test events before this document lands. The test runs only after the merge. Changing anything below afterwards is a new pre-registration, not a silent edit.

Provenance: the draft text in section 3 is carried exactly as posted in Slack C0C8EBZEF9U thread 1795747836.364159 (message 1795750716.748409, 2026-11-27 05:38 Cairo, from the research agent). The decisions in section 2 are from Moos's message 1795751043.400629 and the rulings 1795751376.652329 and 1795751862.953629 in the same thread, all of which I read in the channel. Moos reviewed and decided round 27 as the loop's reviewer. The instruction to write this PR was relayed by the main agent, not read.

## 1. Scope

One hypothesis, one horizon (21 sessions), one test. Descriptive screen results from the 283 screen events are quoted in the caveat only. No scorer or ledger code changes in this PR.

## 2. Decisions on the draft (Moos, 1795751043.400629)

1. Clearance of the test events against verdict cells and the ledger. The forward ledger starts 2026-11-27 (the #864 registration date), so ledger-period announcements do not enter. The backtest grid is not a blanket gap: the backtest realised windows hold 2024 cutoffs (for example 31 March 2024, COMI and ETEL, in round H), so 2024+ events are NOT automatically clear of verdict cells. Clearance is checked per event, see item 5 (Moos, 1795751862.953629).
2. The 1% round-trip cost assumption is accepted. The gap is reported before and after the cost.
3. Run now at about 82 events. Power is low (a true 4% gap detected roughly 1 time in 5 or 6) and INCONCLUSIVE is a valid outcome, not a failure.
4. The draft is accepted with the period-instability caveat carried as written.
5. Amendment rulings (1795751376.652329 and 1795751862.953629): the clarifications in section 4 are added before merge, and the verbatim text in section 3 is untouched. A per-event clearance check against the backtest realised windows and the ledger rows is required before the test runs. Events overlapping a verdict-cell window are excluded and reported under C5. The check uses event dates and cell windows only, no returns, and it fixes the final event list without changing the design.

## 3. Registered text (verbatim from the draft as posted)

The text below is the posted draft, unchanged. The hypothesis, design, statistic, power and caveat blocks are the ones it labels. Its closing "Decisions needed from you" list is answered in section 2. Its "Meanwhile round 28" line is not part of this registration.

> INS-RESEARCH-002 round 27: DRAFT pre-registration for your accept, amend or reject. Nothing run on the test events, nothing registered. Source: research agent report, not re-run by me.
> *Hypothesis (one):* after a results announcement, stocks whose cumulative net profit is above the same period a year earlier earn a higher 21-session excess return than those below. Only the 21-session horizon is tested. The 1 and 5 session results are not.
> *Caveat that must travel with any result:* the screen effect is period-unstable. 21-session spread, 2015-17 vs 2018-23: Yahoo +3.16% (se 2.64) vs +5.87% (2.94); egxpy +0.70% (2.78) vs +7.85% (2.55). In 2015-17 egxpy is not distinguishable from zero. Rank correlation 0.188/0.018 vs 0.121/0.279. About a dozen cuts were run on the same 283 events, so the nominal 2 se is optimistic.
> *Design:*
> • Test events: results announcements ("Reports 3/6/9 Months", consolidated preferred) dated 2024-01-01 or later, never used in the screen.
> • Surprise: sign only (profit above vs below same period last year). Equal comparative or |comparative| below 1 thousand EGP excluded.
> • Entry at the first close after the announcement date. Return = 21-session log return minus equal-weight average of the same source's names. Primary: Yahoo. Replication: egxpy after dropping leading volume-0 stubs. Never spliced.
> • Exclusions: events within 5 days of a capital action. Windows with an in-series zero-volume bar are flagged and reported as a second row, not mixed into variance tests.
> • Statistic: mean excess, profit-up minus profit-down, bootstrap over announcement dates, one-sided 5%, no adjustment (one test). Positive needs the gap above 0 at 5% in both sources, otherwise INCONCLUSIVE. Below 0, or in one source only, is reported as failing. Gap reported before and after an assumed 1% round-trip cost (assumption, not a measured EGX cost).
> *Power:* about 82 events dated 2024 to 2026-10 (31, 36, 15). Expected se about 3.7%, so a true 4% gap would be detected roughly 1 time in 5 or 6. The most likely outcome is INCONCLUSIVE whatever the truth. Q3 and Q4 2026 results would add about 40.
> *Decisions needed from you:*
> 1. Confirm 2024+ events are clear of verdict cells and the ledger. If they are not, I need a different set.
> 2. Accept or change the 1% cost assumption.
> 3. Run now at about 82 events, or wait for about 40 more.
> Meanwhile round 28 runs on a different approach: how many results announcements per year the parser misses (2014 shows none, 2018-20 thin), since that sets the true event count. Checkpoint about 5:53.

## 4. Clarifications (each separate; none edits section 3)

Where a clarification below conflicts with a sentence of section 3, the clarification governs.

C1. No look-back, and incomplete windows. The registered design uses no price look-back before the announcement date, so the 120-bar-before-D rule has no effect on which events are tested. An event whose 21-session window runs past the end of the series cannot be scored and is counted as an exclusion, reported, never dropped silently. (Reviewed as valid by Moos, 1795751376.652329.)

C2. Verdict rule for one source (Moos, 1795751376.652329, CodeRabbit finding on the Statistic). Section 3 says "otherwise INCONCLUSIVE" and also "in one source only, is reported as failing", which overlap for a significant positive gap in one source only. Ruling: a significant positive gap in ONE source only is FAILING, because it fails the replication requirement. INCONCLUSIVE applies only when the gap is not significant in either source and not significantly negative. A positive result needs a significant positive gap in both sources.

C3. How the 1% cost is applied (Moos, same message). The 1% round-trip cost is subtracted once, directly from the gap: post-cost gap = gross gap minus 1 percentage point. It is not subtracted per group, since taking 1% off each group would leave the gap unchanged. The gap is reported before and after the cost.

C4. Event rule extended to interim and annual results (Moos, same message, approved). Test events are interim AND annual results, found with the extended parser: the interim "Reports 3/6/9 Months" format, the annual "Reports Year Ended" format, and the newer 2025-26 "Reports its Financial Results" format. A bare release without figures is not an event, and a bare release counts only once its PDF figures are parsed. The primary test is on the POOLED set (interim plus annual). Interim-only and annual-only splits are reported as secondary rows. Everything else in section 3 (dates from 2024-01-01, sign-only surprise, entry, exclusions, statistic, cost) applies unchanged to the pooled set. The "about 82 events" and the power note in section 3 describe the interim-only set. The pooled event count and power come from the extended count, which uses no returns or outcome data, and are not tuned. Count (research agent round 28b, 1795751253.202149, announcements 2024-01-01 to 2026-10-15): 195 events, 40 tickers, 99 annual and 96 interim, 143 profit-up and 52 profit-down. Power (round 28c, 1795751423.418979, normal-approximation arithmetic with assumptions from the screen, not a simulation; it corrects the rougher round 28b figure): se about 1.9% to 2.2% on the pooled set, so a one-sided 5% test needs a gap above about 3.2% to 3.7%. Pooled power by true gap: 0.7% about 9-10%, 2% about 23-27%, 3.5% about 47-56%, 4% about 56-66%. Interim-only or annual-only (about 97 events each, se about 2.75%): 0.7% about 8%, 2% about 18%, 3.5% about 35%, 4% about 42%. Both sources must pass, so joint power is lower; it was not simulated. Events whose 21-session window is incomplete on the day of the run are exclusions under C1. The run-now decision in section 2 stands.

C5. Final count. The final event count, the actual benchmark size (number of names in the equal-weight average) and every exclusion are reported with the result. Events excluded by the clearance check of section 2 item 5 are listed there.

C6. Final eligible announcement date (Moos, 1795751862.953629, answering the CodeRabbit finding on the upper bound). Only announcements dated 2024-01-01 to 2026-10-15 inclusive enter the test. Announcements after 2026-10-15 do not enter, which matches the 195-event count and keeps the event set fixed. Ledger-period announcements (after 2026-11-27) do not enter.

C7. Clearance covers the full return window (Moos, 1795752281.594459, answering the CodeRabbit Minor on item 5). The per-event clearance check covers each event's FULL return window, from the first close after the announcement through 21 sessions, not only the announcement date. An announcement before a verdict cell can have a return window that overlaps the cell and reuses its prices. Any overlap with a verdict-cell realised window or a ledger row excludes the event, and it is reported under C5.

C8. Clearance is by same-ticker overlap only (Moos, same message, round 28d ruling). An event is excluded only when its return window touches a cell window or ledger row of the SAME ticker. The any-ticker rule is rejected. The outcome is the event ticker's 21-session return minus the equal-weight average of the source's names, so a cell of another ticker can touch the benchmark leg. This effect is ruled second-order, since a cell's 6 tickers are a minority of the 34-name average, and it is accepted (Moos, 1795752940.003539). Result of the check on the 195 events: 16 excluded (COMI x4, ETEL x1, HRHO x4, SWDY x4, TMGH x3), 179 remain as the test set. The check used event dates and cell windows only, no returns (research agent round 28d, relayed by Moos in the same message; I have not read the round 28d post itself). The "195 events" in C4 is the count before this check.

## 5. Cycle item (queued, not part of this registration)

Flag any ledger or realised window that holds a cash-dividend, bonus-share or split effectiveDate, optionally adding the dividend back for cash dividends. effectiveDate is the ex-date for all three: the TradingView unadjusted-close test (11 tickers, 42 actions) found the price step on the effectiveDate bar in all 40 found cases (data round I, accepted in Moos 1795751376.652329). Moos withdrew his earlier "cash dividends only, bonus issues differ" line there. Rights issues are untested. Source for the problem: data round H (8 of 83 matured windows hold a cash-dividend ex-date; dividends are about 1 to 3% of price). This is a pipeline item, not a research round, and it changes nothing here.
