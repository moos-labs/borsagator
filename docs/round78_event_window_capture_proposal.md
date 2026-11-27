# Round 78 (b): event-window capture proposal (doc only)

Proposal only. No runs, no scoring, no enqueue: the cycle decides. Pattern: the #749 plan (backtest/extension_plan_2026-08-14.json): one cutoff date, six tickers COMI.CA, ETEL.CA, TMGH.CA, NVDA, SWDY.CA, HRHO.CA, a documented exception for any non-quarter-end cutoff, and held-back cutoffs only after the first batch scores clean.

## Next scheduled CBE meeting after 29 Oct 2026
Thursday 17 Dec 2026 (the eighth and last of 2026). Weekday checked by calculation: 2026-12-17 is a Thursday. Sources (secondary, read by the agent): Daily News Egypt, 10 Jan 2026 (https://dailynewsegypt.com/2026/01/10/annual-urban-inflation-in-egypt-stabilises-at-12-3-in-december-2025/) lists the 2026 meetings including 17 December; Elwatan News, 16 Nov 2026 (https://www.elwatannews.com/news/details/8397351) says the eighth and last meeting is Thursday 17 December 2026 under the official schedule. NOT primary: the CBE schedule page (https://www.cbe.org.eg/en/monetary-policy/mpc-meetings-schedule) shows year tabs the fetcher does not render, so the date is not yet read from a CBE page. Confirm it there (or from the CBE press release) before the cycle enqueues. A scheduled meeting, so the round-74 rule applies: the full -2..+2 window may be used at any capture offset.

## Session map (EGX trades Sunday to Thursday; Friday and Saturday closed)
| offset | date | weekday |
|---|---|---|
| -2 | 2026-12-15 | Tuesday |
| -1 | 2026-12-16 | Wednesday |
| 0 | 2026-12-17 | Thursday (decision day) |
| +1 | 2026-12-20 | Sunday |
| +2 | 2026-12-21 | Monday |
Holidays in this range were not checked; the cycle should confirm there is no market closure.

## Proposed cell set
Cutoffs at offsets -2, -1, 0, +1 (c = +2 leaves no session ahead in the window, bias 0, so it adds nothing). Six tickers, per #749.
- cutoffs: 2026-12-15, 2026-12-16, 2026-12-17, 2026-12-20
- 4 cutoffs x 6 tickers = 24 cells, cell numbers to be assigned by the cycle after the current last cell.
- Each is a mid-quarter cutoff: documented exception as in #749 (the quarter-end cutoffs are all used). Independence: windows of the four cutoffs overlap each other by construction (same event); they are ONE event, so the scorer must treat them as one cluster family, not four independent clusters. Cutoff clusters here are at most 4, which stays below the 10-cluster KEEP bar; the purpose is the first scorable captures for the round-75 bias counts, descriptive only.
- Month-horizon forecasts from these cutoffs run to about mid-January 2027 and overlap the next scheduled windows; only the day and week horizons are cleanly attributable to the event.
- Capture time: the cutoffs at offsets -2 and -1 are taken before the decision, offset 0 at the close of decision day, +1 after. The release time of the 17 Dec decision is unsettled (rounds 75 to 77), so a capture at c=0 may or may not include the decision; this is flagged, not resolved.

## Held back
Nothing else is proposed. A second event (next 2027 meeting, budget presentation in spring) only after this batch scores clean.
