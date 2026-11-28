# Round 98 (1b): EGX price-limit / halt state flag, pre-registration

Written and committed BEFORE any OHLCV row is read for flag counts or any scorer exists. Shadow challenger only: additive, no ensemble.py or frozen-value edits, never a width input. Source of the request and the ruling on the rule figures: Moos Slack 1795840280.285049 and 1795841110.607749 (thread 1795818091.610649), both relayed to me, not read by me.

## Rule figures (PROVISIONAL)
Per Moos's ruling, not waiting for the primary rulebook or decree text:
- Main market: daily limit 20% from the previous close; temporary halt at 10% (10-minute suspension, then trading resumes to the permitted ceiling or floor).
- SME market: 10% limit, 5% halt. D-list: 5% (relayed by Moos; I did NOT find a D-list figure in either page I opened).
Sources I OPENED (28 Nov 2026):
- EFG Hermes Trading Guide https://tg.efghermes.com/Market/GetById/1103: "Stock Limit Up/Down +/-20% from previous close. Open/Closing auction matching price criteria is +/-10% from the MVWAP of last EGP300k traded OR 0.5% of ADVT in the last 3 months"; "Market/Stock Suspension: 1) If a stock's MVWAP moves 10% from previous close, it gets suspended for 10 mins then it will resume trading to the permitted ceiling/floor. 2) If EGX100 reaches -10%, trading on all stocks gets suspended for 30 mins. If EGX100 moves a further -10% on the day, the bourse gets suspended for a period specified by the head of exchange." The page's date is not shown on what I read.
- FoudaLens https://foudalens.com/en/learn/daily-price-limits (dated 2026-09-30 in the search result): "According to press reports of EGX chairman decree 681 of 2021: on the main market the daily limit is 20% from the last close, with a temporary halt at 10%. On the SME market the limit is 10%, with a temporary halt at 5%." It says the markets were re-segmented and, per press reports, a new segmentation applied from 1 September 2026.
- Ahram Gate https://gate.ahram.org.eg/News/2935987.aspx (26 Aug 2021, Arabic news report on decree 681 of 2021, opened): article 1 as reported, price limits 20% of the last closing price for the main market with temporary suspension at 10%, and 10% for the SME market with temporary suspension at 5%; article 2: the moving price is a volume-weighted average over the last 30 minutes with executions of at least EGP 100k; article 3: closing auction before 2:30pm. Confirms the figures against the decree's own articles as a newspaper reports them.
All three are secondary (the Ahram piece is the nearest to the decree). The decree text and the EGX rulebook were NOT opened. A primary-source hunt runs in parallel; if the text turns up this doc is amended BEFORE scoring.

## Limitations stated up front
- Per-stock and per-segment variation: limits differ by segment (main, SME, D-list), and EGX re-segmented in Feb 2024 (enterpriseam.com, seen as a search snippet only, not opened) and from 1 Sep 2026 (FoudaLens, opened, "press reports"). This doc applies ONE rule to all 36 names for every date; names or dates under a different limit are mislabelled by that amount, and the scorer cannot tell.
- OHLCV is the Yahoo-sourced archive bars. Whether "previous close" there is the exchange's reference price, and whether split or dividend adjustments are applied, is not verified here.
- The 10% halt is defined on an intraday volume-weighted price (MVWAP); the OHLCV proxy uses the daily high or low, which can touch +-10% without a halt having occurred.

## Flag definitions (fixed now, operational on OHLCV)
Let P0 = previous session's close, in the same series.
- LIMIT-HIT day: |close - P0| / P0 >= 0.195 (near-limit reading, threshold 19.5% per the #773 convention as relayed by Moos; #773 not opened by me).
- HALT-PROXY day: high / P0 - 1 >= 0.10 OR low / P0 - 1 <= -0.10.
- NO-TRADE day: volume == 0 OR volume is missing for the session. A session with no bar row at all stays listed as missing (it is not a no-trade day).
Every flag is computed from bars strictly before the cutoff session. Window: the 20 sessions before cutoff C.

## Missing bars (explicit rule, fixed before any fit or scoring)
- A session is MISSING for a name when the session date has a bar for at least one other name in the 36-name archive panel but no bar row for this name. (There is no separate exchange calendar in this doc; the panel's own dates are the session list.)
- P0 for a session is the close of the session immediately before it in that list. If that previous session is missing for the name, P0 is UNKNOWN and every flag for the next session (LIMIT-HIT, HALT-PROXY) is UNKNOWN. A missing close is never inferred, carried forward, interpolated or taken from an adjusted series.
- Unknown flags are never treated as unflagged. A (cutoff, name) pair is scorable only if all 21 sessions needed (the 20 window sessions plus the one before the first, for its P0) have a bar row. Any pair for which ANY of those 21 sessions is missing, whether inside the 20-session window or the P0 session just before it, is NON-SCORABLE and EXCLUDED from the fit and from scoring (v2 is dropped on the same row, so the comparison stays on the same rows). The exclusion applies to every non-scorable pair, including one whose only gap is the P0 session (its P0 is unknown, so it is never eligible for the fit). Each is listed individually with cutoff, name, the missing session dates, and the reason "missing bar in window" or "missing P0 session" (both labels apply if both occur). A missing-volume bar that has a close is not a missing session; it is a NO-TRADE day (above).

## State and shadow challenger (fixed now)
- s(i,C): sign (+1 or -1) of the return (close/P0 - 1) on the most recent LIMIT-HIT or HALT-PROXY day in the 20-session window; 0 if there is none. If that most recent flagged day has a return of exactly 0 (possible only for a halt-proxy day: its high touching +10%, or its low touching -10%, on one side only or on both sides, with the close at P0; a LIMIT-HIT day cannot have a zero return because |ret| >= 19.5%), s = 0: no direction, and the scorer does NOT fall back to an earlier flagged day.
- Centre shift: d(i) = k * s(i,C) * w(i), with w the v2 half-width for the cell. The interval is moved, not widened. Hypothesis (not a finding): a censored or halted move continues in its direction the next week.
- NO-TRADE days are reported as counts only per name and window; they do not enter the shift.
- k: least squares through the origin on training pairs with s != 0: target y = (realised close - v2 centre) / w, k = sum(s*y) / sum(s*s), cells 1-47 only. Sign is estimated then frozen, |k| <= 0.25 (fixed constant, not tuned). If fewer than 30 flagged training pairs exist, NO k is fit and the run is COUNTS ONLY.
- v2 is the k = 0 arm, read as stored, never refit.

## Windows
Fit: cells 1-47. Descriptive: cells 48-90 (counts and paired delta vs v2 on the same rows, no verdict word). Score: cells 91+ only, never loaded before this doc is merged. Never load a verdict-cell origin for smoke tests (use contexts before 2025-10-20).

## Intervals, loop bar and decision time
95% two-sided percentile bootstrap, resampling cutoff dates with replacement, 5000 reps, seed 20261125; challenger-minus-v2 mean RangeSkill and the challenger's pooled coverage, quote only default-rep CIs. The coverage interval is the challenger's ABSOLUTE pooled coverage (share of scored rows whose realised value lies inside the tilted interval), not a challenger-minus-v2 difference; challenger-minus-v2 mean RangeSkill is the only comparative metric. KEEP-eligible only if the lower bound of the challenger-minus-v2 interval > 0 AND the coverage interval overlaps [0.75, 0.85] with width <= 0.15 AND >= 10 cutoff clusters; fewer = COUNTS ONLY. KEEP is evaluated once, when the forward weekly schedule (#953) first reaches 10 scored clusters; later looks are descriptive only.

## Tests (when 1c is accepted)
Fixed synthetic bars, *main* guard, Suite class, mutation checks with boundary mutants: 19.5% boundary (0.194999, 0.195), +-10% halt proxy boundary, strictly-before-cutoff, 20-session window edge, zero-volume versus missing, sign of most recent flag, 30-pair minimum, 47/48 and 90/91 window gating. Build only after Moos accepts this doc.

## Open
Primary rule text (parallel hunt). Whether the single rule across segments is acceptable. Whether the flagged training pair count reaches 30 is unknown until the fit step reads cells 1-47 (not read for this doc).
