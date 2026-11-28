# FX and metals expansion (#972 phase 1): pre-registration

Written and committed BEFORE any scoring. This document scores nothing and contains no result. Spec: Moos Slack thread 1795858029.067639, message 1795865381.336299 (read in full by the author). Plan source: INS-FXMETALS-PLAN, Slack 1795857972.733689 and addendum 1795858167.876569 (read). Branch improve-151-fx-metals-harvest, harvest head 4322a624.

Items marked DESIGN CHOICE are the author's, for Moos's review. Anything not fixed by the spec or plan is marked OPEN and is not guessed.

## 1. Verified universe
FX, 13 series (Yahoo chart API, plan 1795857972.733689 section 1; author re-fetched all five not yet harvested on 2026-11-28, daily bars from 2019-01-01):
- Majors and crosses: EURUSD=X, GBPUSD=X, USDJPY=X, USDCHF=X, AUDUSD=X, USDCAD=X, EURGBP=X, EURJPY=X.
- EGP: EGP=X (USD/EGP), EUREGP=X, GBPEGP=X.
- Pegged controls: USDSAR=X, USDAED=X.
Derived, never fetched: SAR/EGP = USDEGP / USDSAR; AED/EGP = USDEGP / USDAED.
Not used (not found on Yahoo): XAUUSD=X, XAGUSD=X, XPTUSD=X, XPDUSD=X, SAREGP=X, AEDEGP=X. Frankfurter XAU/XAG removed.
Metals: GC=F and SI=F only, labelled "futures research proxy, not tradeable spot" in every table, file and chart. Platinum and palladium futures are out of phase 1.
Harvest gap (caveat): scripts/fetch_fx_metals_store.py at 4322a624 harvests 8 FX symbols (EGP=X, EUREGP=X, EURUSD=X, GBPUSD=X, JPY=X, CHF=X, AUDUSD=X, CAD=X). EURGBP, EURJPY, GBPEGP, USDSAR and USDAED are verified live but not yet in the harvest. Adding them is a separate build; no scoring uses them until harvested and hashed.

Derived files (built by the harvest script, labelled DERIVED-cross-rate-not-fetched, never fetched): SAREGP_DERIVED.csv = USDEGP close / USDSAR close; AEDEGP_DERIVED.csv = USDEGP close / USDAED close. Common-date rule: a date is kept only when both series have a positive close on the same session date; other dates are dropped and counted. Close only (a ratio's high/low cannot be built from two series' highs and lows, so those columns are empty and range scoring does not apply to these files). Inputs keep the harvest session dates unchanged; the section 2 session rules apply when scoring. The 2024-03-06 exclusion (section 3) applies to these files too.

## 2. Session rule
- Session = one UTC day of the API bar. A Sunday bar merges into the following Monday (Sunday open to Monday close; high and low over both).
- The Friday-close to Monday-open gap belongs to Monday's range.
- Day = next session, week = 5 sessions, month = 21 sessions.
- Futures keep Mon-Fri sessions and are never pooled with FX.
- Null-close and holiday sessions are dropped and counted (counts reported, nothing filled).
- DESIGN CHOICE: a Saturday bar (USDJPY has some) merges into the following Monday the same way as Sunday. Open = earliest bar's open, close = Monday's close, high/low = extremes. A merged session counts once.

## 3. Close and regime
- Frozen close: session date for futures via America/New_York zoneinfo (Yahoo meta.gmtoffset is a fixed -18000).
- Yahoo's final partial-day bar is dropped in score runs.
- EGP regime split at the March 2024 float. DESIGN CHOICE: boundary 2024-03-07 (first session after the float, as in the addendum); sessions before it are "pre-float". EGP pairs are reported with and without jump days.
- DESIGN CHOICE, jump day: a session whose absolute log close-to-close return exceeds 5 x the trailing 60-session median absolute return (needs 60 prior sessions), plus 2024-03-06 and 2024-03-07 by date. Fixed here, not tuned later.

EGP float check (added after the harvest extension; data from the 2026-11-28 live harvest, 10y pull): the close series first prints the new level on 2024-03-07 for all three EGP pairs (USDEGP close 30.8722 on 03-06, 49.5302 on 03-07, log return +0.4727; EUREGP 33.5270 to 53.9800, +0.4763; GBPEGP 39.2351 to 63.0666, +0.4746). The 2024-03-06 bar itself carries post-float high and low (USDEGP high 50.7791, low 49.4149) with a stale pre-float close (30.8722). So close-to-close jump = 2024-03-07, consistent with a one-day stale close on the float day (CBE float 2024-03-06). Consequence: the 2024-03-06 high-low range is a post-float range sitting beside a pre-float close, so 03-06 is excluded from all scoring (it is already a fixed jump day above). The rule above holds unchanged.

## 4. Forecast
- Frozen v2 (scripts/ensemble.py, untouched) plus challengers on log-range (high-low) bands, same RangeSkill and coverage definitions as scripts/backtest_score.py (RangeSkill = 1 - mean Winkler 80% interval score / naive-range score).
- FX and metals each get their own pooled fit. No EGX parameter is carried over.
- DESIGN CHOICE, challengers: the naive-range and random-walk baselines and the #966 shrinkage candidate only, fixed before scoring. No closed route (width, volatility, conformal, ACI, GARCH-FHS, log-HAR, centre drift) is re-proposed.

## 5. Roll exclusion (futures proxy)
roll_window = +/-5 calendar days around first-notice and last-trade dates, all 12 months for silver (SI=F splices monthly: 0 mismatches at 4322a624). Last trade = third last weekday (CME rulebook ch.113 gold, ch.112 silver); first notice = last business day of the prior month (third-party sources, consistent with the 2025-11-28 GC splice). Scorers drop the return ending on a flagged date. Recorded limitations: first-notice rule is third-party; CME holiday list unsourced. Narrow to +/-3 only if usable rows become a constraint.

## 6. Conversion-profit scoring
- Convert X to Y at slot start, hold to t+h, measure in EGP and USD. Net = gross log return minus round-trip cost. Act only when |predicted move| exceeds cost; otherwise abstain (counted).
- Slots: day, week, month starts, plus day-of-week and month-of-year buckets.
- Cost grid 0.1 / 0.5 / 1 / 2 % round trip, every result labelled by grid value, until a dated retail USD/EGP buy/sell card is sourced. No zero-cost result is reported as profit. The 0.2% EGP retail round trip is an unverified working assumption.
- Benchmarks: hold-USD, hold-EGP, convert-at-slot-start. Skill = net minus benchmark, block-bootstrap CI.
- Product stays spot-only. Metals profit claims are not made. Taqabud: spot legs only, settlement by account credit valid, nothing deferred.

## 7. Hold-out
One untouched FX hold-out, fixed by date here. DESIGN CHOICE: sessions dated 2026-01-01 to the last matured session at scoring time. Training and descriptive work use sessions before 2026-01-01 only. Reasoning: leaves 2019-2025 for training (post-float EGP 2024-03-07 to 2025-12-31, about 1.8 years) and about eleven months held out; cluster count, not rows, is the bottleneck. Alternative for Moos: 2025-07-01 (longer hold-out, shorter post-float training). Never load a hold-out row before a fresh note.

## 8. Acceptance bar (same as EGX)
KEEP needs RangeSkill >= +0.10, coverage CI overlapping 0.75-0.85, n >= 30 matured rows and >= 10 cutoff clusters (a cluster counts only when every intended row has a realised close; gate per horizon). Keep rule relative to frozen v2 on the same rows; no KEEP is an adoption by itself. Under 10 mature clusters, output is counts only. A null result is reported as a result.

## 9. First descriptive cell set (no scoring in this task)
EURUSD, USDJPY, EGP=X (post-float only for EGP). Output when later run: v2 vs random-walk and range baselines, numbers only (n, mean interval score, RangeSkill, coverage, bootstrap 5000 reps seed 20261125), no verdict word. From plan item 6.5.

## 10. Open items
- Retail USD/EGP buy/sell card: unsourced.
- Spot metals source: none free and verified (FRED serves no LBMA; IBA/MyLBMA licence is a Muhammad decision, not pursued).
- Harvest of the five missing FX symbols.

## 11. First cell set as run (INS-IMPROVE-155)
Output: evaluation/fx_first_cells_descriptive.md/.json, produced by scripts/score_fx_descriptive.py from the 2026-11-28 harvest (not committed). Design choices made at run time (author's, for review): training block 2019-01-01 to 2025-12-31 only, hold-out rows dropped at load and never read; interval is on the h-session log close-to-close move (not on the window high-low range, which is not scored in this cut); v2 = frozen EGX k (1.15/1.28/1.20) times sigma60 times sqrt(h), not refit, naive k 1.2816; non-overlapping cutoffs every h sessions after 60 sessions of history; cluster = calendar month of the cutoff; EGP from 2024-03-07, 03-06 excluded, jump-day variant drops a row when a flagged jump falls in its sigma or realised window. No FX-fit challenger, #966 shrinkage or hold-out run here.

## 12. Conversion-profit scoring rule (INS-IMPROVE-158), written before any hold-out row is scored
Spec: Moos dispatch Slack 1795858029.067639 ts 1795870057.032869 (read): score which pair conversions over which time slot could gain, FX hold-out data, cost grid majors 0.07% and EGP retail 0.2%, triangular A->B->C->A versus direct, "worth it" = conservative (lower) edge gain > cost. Section 6 stays the parent rule. Items marked DESIGN CHOICE are the author's.
- Cost (DESIGN CHOICE on reading): the dispatch grid value is the ROUND-TRIP cost of a convert-and-hold-and-convert-back, majors 0.07%, any EGP pair (USDEGP, EUREGP, GBPEGP, SAREGP_DERIVED, AEDEGP_DERIVED) 0.2%. One leg = half. The section 6 grid 0.1/0.5/1/2% is also reported, labelled, for every cell. The 0.07% and 0.2% values are unverified working assumptions (no dated card sourced).
- Series: 8 majors/crosses and 5 EGP pairs (EGP post-float sessions only, 2024-03-06 excluded, all-rows variant only). Training = sessions before 2026-01-01; hold-out = sessions dated 2026-01-01 to the last matured session, partial UTC day dropped.
- Slots (DESIGN CHOICE): (a) day-of-week: h=1 session, start session weekday Mon..Fri (5 buckets); (b) week start: h=5, Monday start sessions; (c) month start: h=21, first session of each calendar month; (d) month-of-year: the month-start rows split by calendar month (counts only, expected under 10 clusters per bucket).
- Direction (fit on training only): d = sign of the training mean log return of that pair and slot bucket (d=+1 hold the quote currency of the pair name's base, i.e. long base; -1 short base). A bucket with fewer than 30 training rows abstains (counted).
- Edge: hold-out gain_i = d x 100 x log(close_end / close_start), in %. Conservative edge = 2.5th percentile of the bootstrap mean (iid over rows, 5000 reps, seed 20261125). lower_gt_cost = (conservative edge > cost). Rows with unrealised close are not scored.
- Gate (section 8 style): n >= 30 matured rows and >= 10 mature clusters (cluster = calendar month of the start session) per bucket, else counts only.
- Benchmarks reported alongside (numbers, no verdict): mean gross log return of always-long-base and always-short-base on the same hold-out rows.
- Triangular versus direct (DESIGN CHOICE): triangles EURJPY vs EURUSD x USDJPY; EURGBP vs EURUSD / GBPUSD; EUREGP vs EURUSD x USDEGP; GBPEGP vs GBPUSD x USDEGP. residual_t = log(direct close) - log(path close product) on dates where all three series have a session, in the hold-out. Direction fixed from the training mean residual sign. The cycle A->B->C->A executed at one instant has zero gross return except this residual; it uses 3 legs (cost 1.5 x the round-trip value of its class, the EGP value when any leg is EGP) against 1 round trip for direct. Gain compared as conservative edge (same bootstrap) of d x residual in % versus the cycle cost. The residual is a close-timing difference between independently quoted series (section 1 EURUSD check: gaps up to 0.57%), so it is reported as an identity residual, not a tradable gain.
- No zero-cost result is reported as profit. Metals are not used. No verdict word in the output; the boolean field lower_gt_cost is the pre-registered rule.
