# INS-RESEARCH-002 round 27 pre-registration: results-announcement profit sign vs 21-session excess return

Status: PRE-REGISTERED on merge. Nothing is run on the test events before this document lands. The test runs only after the merge. Changing anything below afterwards is a new pre-registration, not a silent edit.

Provenance: the draft text in section 3 is carried exactly as posted in Slack C0C8EBZEF9U thread 1795747836.364159 (message 1795750716.748409, 2026-11-27 05:38 Cairo, from the research agent). The decisions in section 2 are from Moos's message 1795751043.400629 in the same thread, which I read in the channel. The instruction to write this PR was relayed by the main agent, not read.

## 1. Scope

One hypothesis, one horizon (21 sessions), one test. Descriptive screen results from the 283 screen events are quoted in the caveat only. No scorer or ledger code changes in this PR.

## 2. Decisions on the draft (Moos, 1795751043.400629)

1. 2024+ events are clear of verdict cells and the ledger: CONFIRMED. The backtest grid ends 2023-12-26 and the forward ledger starts 2026-11-27 (the #864 registration date), so the test events (2024-01 to 2026-10) fall in the gap.
2. The 1% round-trip cost assumption is accepted. The gap is reported before and after the cost.
3. Run now at about 82 events. Power is low (a true 4% gap detected roughly 1 time in 5 or 6) and INCONCLUSIVE is a valid outcome, not a failure.
4. The draft is accepted with the period-instability caveat carried as written.

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

## 4. Clarifications that add nothing to the registered text

- The registered design uses no price look-back before the announcement date, so the 120-bar-before-D rule has no effect on which events are tested. An event whose 21-session window runs past the end of the series cannot be scored and is counted as an exclusion, reported, never dropped silently. This restates how the registered return is defined; it does not change a threshold.
- The test events are the ones the draft counts (about 82, dated 2024-01-01 to 2026-10). The final count and every exclusion are reported with the result.

## 5. Cycle item (queued, not part of this registration)

Flag any ledger or realised window that holds a cash-dividend effectiveDate (the ex-date, per data round G), optionally adding the dividend back. Source: Moos 1795751043.400629 (data round H, cash dividends are about 1 to 3% of price, 8 of 83 matured windows contain one). Cash dividends only: bonus issues differ. This is a pipeline item, not a research round, and it changes nothing here.
