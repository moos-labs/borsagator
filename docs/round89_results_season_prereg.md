# Round 89: results-season calendar flag, pre-registration (redefines the #946 flag)

Committed before any number is computed. Brief: Slack C0C8EBZEF9U 1795824592.459669 (relayed by Main, not read by the agent), option A approved. Additive: no ensemble.py, no frozen v2 value is edited.

## Redefinition of #946
#946 (docs/round87_disclosure_event_flag_spec.md) defined a flag from announced forward dates and was forward-only because no historical record of announced dates exists in the repo. This round replaces that definition with a regulatory deadline season: a window is flagged when the window overlaps the period in which a listed company must file its periodic statements. The season comes from a rule, not from announcements, so it exists for every cell. #946 is not changed and its forward-only spec stays valid for the announced-date flag.

## Primary rule (read as page image)
FRA, Listing and Delisting Rules of Securities on the Egyptian Exchange, latest amendment January 2026, PDF page 44 (printed page 74), https://fra.gov.eg/wp-content/uploads/2026/02/%d9%82%d9%88%d8%a7%d8%b9%d8%af-%d8%a7%d9%84%d9%82%d9%8a%d8%af-%d9%88%d8%a7%d9%84%d8%b4%d8%b7%d8%a8-%d9%8a%d9%86%d8%a7%d9%8a%d8%b1-2026.pdf :
- Art. 46(2): quarterly statements within 45 days at most of the end of the period.
- Art. 47: consolidated quarterly statements within 60 days.
- Art. 46(1): annual statements within 3 months of year end.
Caveat: the January 2026 text. The 45/60/90-day periods carry no amendment footnote on that page, but older versions were not read, so equality of the deadlines in 2023-2025 is a reading of this text, not a verified fact.

## Flag (fixed here, before any return is computed)
- Season for a quarter end Q (March 31, June 30, September 30): the dates Q+1 to Q+45 days. For December 31 (year end): Dec 31 + 1 to + 90 days. N = 45 is Art. 46(2), the rule every listed company has; the consolidated 60 days is NOT used (cutoff-date counts alone show it flags 16/17 day and 17/17 week and month windows, leaving no contrast). N is not changed after any result is seen.
- A window flags when cutoff date c < season end and window end e >= season start, where the window is (c, e], e = the h-th Egyptian business day (Sunday to Thursday, holidays ignored) after c, h sessions 1, 5, 21 (as #945).
- Structural counts on the 17 numbered-cell cutoffs, from dates only: flagged 12 (day), 13 (week), 13 (month) of 17.

## Fit, scoring, loop bar (same mechanics as #945)
Frozen v2 half-width is multiplied by m_flag for flagged rows and m_unflagged for the rest, per horizon, under the mean-width constraint (total v2 half-width unchanged), m_flag from the grid 0.70 to 1.50 step 0.05, lowest mean interval score, ties to 1.0. Minimum 5 flagged and 5 unflagged training rows per horizon, else not fitted (both 1.0). Fit on cells 1-47 only. Descriptive run: cells 48-90, no verdict word or key. Cells 91+: counts only below 10 cutoff clusters (no coverage, skill or CI printed or written). Bootstrap: cutoff-clustered, 5000 reps, seed 20261125 (repo defaults). KEEP only if on all horizons RangeSkill CI lower bound > 0 AND coverage CI overlaps [0.75, 0.85] with width <= 0.15 AND >= 10 cutoff clusters (benchmarks/loop_bar.py, copied unchanged from #945). Every capture or row that does not enter a run is listed as excluded with its reason.
