# Round 98 (4): sector-leader distinction note

Note only. No implementation, no scoring, no data read. Source of the request: Moos Slack 1795840280.285049, relayed to me, not read by me.

## Where the market-factors route closed (sources I opened)
- docs/proposals-round-25.md (origin/main): "Route 2 market-factor screen (#838, reproduced by Muhammad): negative. Smallest Holm-adjusted p 0.081. The EGX-internal factor does not beat the frozen width." The factor there is an EGX-wide factor used in a width decomposition (screen_market_factor.py: sigma_from decomposition, 18 tests, Holm).
- docs/proposals-round-32.md (origin/main): the commodity and external factor family (#849: EEM, BZ=F, GC=F) screened as width inputs; "BZ=F post-day RangeSkill 0.016 against v2's 0.015" and the paired delta of #854 puts the best reading at +0.0007, under 0.001 RangeSkill. Closed as a duplicate.
I have not opened #838, #849 or #854 themselves; the lines above are the docs' own statements.

## What differs
The closed routes feed a market-wide or external factor into the WIDTH (scale) of the interval. The sector-leader idea is a CENTRE tilt from one named stock's prior-week return onto its sector followers, conditioned on the sector, not a market-wide factor. A market factor moves all names together, so within-cutoff it carries no cross-sectional information; a leader return is a within-sector cross-sectional signal. It is also not volatility or width.

## Why it could work where that failed (a hypothesis, not a finding)
If news reaches the large, liquid leader first (COMI for banks, TMGH for real estate), followers' next-week centre may lag it. The market-factor screens could not see that, because the common factor is already inside v2's width and has no follower-specific content. The honest risk: the leader's return is correlated with the market factor, so the effect may already be absorbed (same failure as Route 2), and followers in the same sector may be few.

## Sector map (PROPOSED, fixed and listed here before any scoring)
Grouping is from the company names in EGX_COMPANIES (origin/main worker/egx_harvest.py), NOT from an EGX sector classification; it must be pinned to an EGX or Yahoo sector field I open before scoring. Leader = the largest name in the group, to be fixed by an opened market-cap source, not chosen later.
- Banks: leader COMI; followers ADIB, FAIT, SAUD. (FAITA is the USD line of FAIT, excluded.)
- Real estate: leader TMGH; followers MASR, OCDI, ORHD, PHDC.
- Petroleum-sector companies: SKPC, AMOC, EGAS; leader unresolved (no market-cap source opened).
- Cement: ARCC, MCQE; leader unresolved.
- Food: JUFO, EFID; leader JUFO (proposed).
- Pharma: ISPH, RMDA; leader unresolved.
- Singletons or unclear (no leader, excluded): ETEL, HRHO, EFIH, SWDY, EGAL, ATQA, ORAS, ACGC, ORWE, MPCO, IFAP, ETRS, MTIE, CLHO, ICFC, LCSW, RACC.
A group with fewer than 2 followers is dropped, listed with its reason.

## Registration sketch under the loop bar
Feature: prior-week log return of the leader, lagged to the cutoff (strictly before the cutoff day, same price source as v2). Slope per sector fit on cells 1-47 only, sign estimated then frozen; descriptive on 48-90; scored 91+ only. KEEP-eligible only if RangeSkill cutoff-clustered CI lower bound (challenger minus v2) > 0 AND coverage CI overlaps [0.75, 0.85] with width <= 0.15 AND >= 10 cutoff clusters; fewer = COUNTS ONLY. Bootstrap 5000 reps, seed 20261125. Leaders' own rows are excluded from the tilt. No ensemble.py or frozen edits.

## Open decisions for Moos
1. Whether this counts as different enough from the closed market-factor route (my argument above is a hypothesis).
2. Sector classification source and leader selection source.
