# Proposal round 32: after the B result and the panel-23 triage (proposals only)

INS-IMPROVE-001 round 32 item 1 (Moos, Slack 1795745102.498389, relayed by
the parent agent; the author did not find that message in the loop thread
or channel and cites it as relayed). Nothing here is GO'd, scored or
registered. Research is paused per the same relay, so this round fetched no
new source: every source below is either named as already checked in an
earlier merged document, or marked UNVERIFIED. Panel 23 itself was not
available to the author; its two points are taken from the relayed triage
text only.

## What the B result says (#857, merged)

- Volume state (log1p of the 20-bar mean volume, market-wide zero-volume days
  excluded from the mean and kept in the eligibility count, per-cutoff
  eligibility from #855) widens or narrows the v2 band by exp(beta x z).
  Family 12, Holm over 12, 35 of 36 tickers used.
- Every one of the 12 deltas against frozen v2 is negative, from -0.003
  (beta 0.10 post month) to -0.054 (beta 0.20 post day). Delta p 0.73 to
  1.00, every Holm-adjusted p 1.000. Beta 0.20 post-day RangeSkill is -0.040
  against v2's +0.014.
- Together with the paired deltas of #854 (all 48 deltas in [-0.024,
  +0.007], two readings at Holm 0.024 with deltas +0.0007 and +0.0006), the
  pattern is the one the round-25 proposal predicted: signals built from the
  names' own series, the EGX cross section, or global price factors do not
  separate from frozen v2. Only information from outside those price and
  volume series is left, so such routes weigh heaviest below.

## Panel-23 triage (as relayed)

- Commodity route: dropped as a duplicate. It is the already-screened
  family of #849 (EEM, BZ=F, GC=F). BZ=F post-day RangeSkill was 0.016 against
  v2's 0.015, and the paired delta of #854 puts the best commodity reading
  (BZ=F post week) at +0.0007, under 0.001 of RangeSkill. Re-running it with
  a different factor name adds nothing.
- WDI surprise: not runnable as stated. The World Bank WDI table has no
  consensus-forecast column (relayed), so a "surprise" (actual minus
  expectation) has no expectation to subtract. It is UNVERIFIED until a real
  point-in-time consensus-forecast source is named and checked. An
  actual-only WDI series is a level, not a surprise, and is also published
  with a lag that the PIT rule would have to price in.

## Proposal A: GDELT macro-theme rows as a width input (new information)

- Source: the GDELT GKG stream already in the repo's harness
  (scripts/gdelt_gkg_filter.py, alias table, pilot report
  docs/gdelt-gkg-pilot-2024-05.md). The pilot covered 2024-05 only. The pilot
  report says a full 2019-2026 run is viable. The author did NOT verify that
  2019-2023 rows exist in the store, so the usable fitting history for any
  screen on this source is at most 2019 to 2023-12-28, not the 2014 start of
  the price store.
- Feature (the same theme-volume signal as column 3 of the INS-MACRO-NEWS-001
  catalog, theme_spike): z of the macro-theme daily record count against its
  own earlier values, from records stamped strictly before the cutoff day;
  band = v2 x exp(beta x clip(z, -3, 3)), beta in the fixed grid (0.10,
  0.20), not fitted. Family 2 betas x 3 horizons x 2 regimes = 12, Holm over
  12; both p and the paired delta against v2 are printed.
- Input for the count (specified by this document): the macro-theme count
  reads the COMPLETE Themes field of each GKG record, from the raw GKG row or
  from a macro export that does not truncate it. It must not read the
  `themes` value of the company-matched export on main, which keeps only the
  first 500 characters (scripts/gdelt_gkg_filter.py line 214); a macro tag
  after that point would be missing and the z-score undercounted without an
  error. Whether the macro capture channel of #846 keeps the full field is
  not checked here and must be confirmed before any run.
- Relation to the held work: this is a screen on the same feed, not the
  INS-MACRO-NEWS-001 event-study implementation. It does not start before
  Muhammad's GO on that implementation and the lead's feed is available.
- Honest limit: 2019 to 2023 gives few independent macro regimes, and the
  round-24 news-width harness (screen_news_width.py) has not been scored
  against v2 with the paired delta, so there is no prior result on this feed
  to lean on.

## Proposal B: consensus-forecast surprise (source UNVERIFIED, cannot run)

- Idea: surprise = released value minus the consensus forecast stored before
  release, as a width input around announcement days.
- Source: none verified. A usable source must store forecasts as published
  before each release (vintages), not revised history. The author names none
  and fetched none, because research is paused.
- Step 0 (when research resumes): find and verify one such source for Egypt
  or for the global releases the EGX names respond to, and check that its
  forecast timestamps precede the release. Without that, no screen.
- Honest limit: even with a source, the number of releases with a stored
  consensus in 2014-2023 for Egypt is small.

## Pre-registration rules for every screen proposed here

- Per-cutoff eligibility from #855 (last 120 bars before D, prior bars only).
- A ticker with fewer than 120 bars dated before D is not eligible at D and
  contributes nothing to its own earlier-cutoff history. This case was
  implemented in #857 (the first cutoff, at 120 bars, fails because only 119
  bars precede D) but was not stated in its docstring. Every new
  pre-registration states it.
- Holiday bars: market-wide zero-volume days are excluded from any
  volume-based mean and kept in eligibility counts, as ruled for B.
- The paired delta against v2 is printed next to p; delta and its interval
  print at 3 significant digits (#856 and the #857 follow-up).
- Keep rule: the loop bar of the brief (T2 RangeSkill >= +0.10 on every
  horizon with the month CI lower bound > 0, relative to frozen v2 on the same
  rows), not a Holm p against 0. No screen is a keep or an adoption by
  itself.

## Ranking

1. A, once the GDELT feed for 2019-2023 is confirmed present and Muhammad has
   given the macro GO. 2. B, only after a source is verified. The commodity
   route and the WDI surprise are closed as stated. C (calendar) stays parked.
