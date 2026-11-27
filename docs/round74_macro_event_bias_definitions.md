# Round 74: macro-event bias definitions (design only)

Doc only. No code, no scoring, no numbers computed from captures. These are proposals for Moos to accept or change BEFORE any scoring. Nothing here edits frozen v2 values or scripts/ensemble.py.

## Terms
- Capture: a ledger row with a cutoff session c, expressed as an offset relative to an event's session 0 (c = -2..+2 puts it inside that event's window).
- Horizon h: the capture's forecast horizon, S_h sessions after the cutoff.
- AAR(o): the index (EGX30) average abnormal return at offset o, from the event study.
- Frozen v2 half-width W_h: the capture's frozen v2 band half-width for horizon h, on the same row.

## 1. Which session's AAR
Use the capture's own offset AAR. For horizon h the bias covers the sessions still ahead of the cutoff inside the event window:
AAR_sum(h) = sum of AAR(o) for o in [max(c+1, -2), min(c+S_h, 2)].
If that range is empty (cutoff at +2 or later, or no overlap) the bias is 0. Sessions at or before the cutoff are already in the price and are never counted.

## 2. Index vs ticker AAR
Index EGX30 AAR. Reason: per-ticker event cells have too few events to estimate, and the descriptive study is index-only. A ticker-level version needs its own pre-registration.

## 3. Cap
bias = sign(AAR_sum) x min(|AAR_sum|, cap), cap = 0.25 x W_h.
Reasoning: the cap can never move a band edge by more than a quarter of the frozen half-width, so a mis-estimated AAR cannot dominate the band. The scheduled-CBE AARs in the descriptive study are about 0.1 to 0.4 percent per session while half-widths are several percent, so the cap should rarely bind; this is to be checked in counts only (how many captures hit the cap), before any scoring. Alternatives if Moos prefers: 0.5 x W_h, or a fixed log-return cap. The value is not fitted.

## 4. Point-in-time rule
- Scheduled meetings (date published before the capture): the full -2..+2 window applies to captures at any offset in it.
- Extraordinary meetings (special MPC, or a budget date not published before the capture): adjust only captures at or after session 0 (c >= 0), because before that the event was not knowable. Pre-session-0 captures get bias 0.
- Budget dates count as scheduled only if the presentation date was published before the capture; otherwise treated as extraordinary.
- Release-time: use the release rule Moos picks from the round-74 sensitivity table (before, page_time or after). Unknown-time rows follow the default `before`.
- Backtest AAR for a capture comes only from events strictly before that capture's event window (expanding, no look-ahead). Leave-one-event-out is descriptive only. Events of the same type pool; scheduled and extraordinary are separate cells.

## 5. Overlap rule (capture inside two event windows)
max-|bias|, then cap: take the AAR_sum with the larger absolute value, keep its sign, apply the cap. Reason: windows of close events share the same sessions and are correlated, so a sum double-counts; max-|bias| never exceeds the single-event cap. Alternative: sum then cap (larger effect, double-counts).

## 6. Not in scope
No band replay, no keep rule, no results. The power check says the >=10 cutoff-cluster KEEP bar is unreachable on the current grid, so scoring waits for event-window captures. Training cells 1-47, descriptive 48-90, clean scoring 91+ unchanged. Scope stays KEEP 5 YEARS.

## Decisions for Moos
1. Cap: 0.25 x W_h (or 0.5 x W_h, or fixed).
2. Release rule for the AARs: before, page_time or after.
3. Overlap: max-|bias| then cap (or sum then cap).
4. Budget dates: scheduled only if published before the capture.
