#!/usr/bin/env python3
"""Ticker admission gate for the #436 walk-forward backtest
(design §4).

A ticker enters the backtest sample only if the Yahoo chart API
returns >= 3 years of daily bars ending at the latest cutoff, with
no gap > 10 sessions, no stale-flat segment, and a retrievable
dividend/split event feed. The gate — not the design document — is
the authority on which tickers qualify; a failed ticker is
excluded WITH the reason, never silently dropped and never
replaced mid-run. The gate result per ticker is recorded in the
run manifest.

The gate applies the shared history floor (2019-01-01): rows
before it are dropped before every admission check, so a
pre-2019 anomaly (the stale-flat segment that motivated the
flat-run check) can no longer reject a ticker — the
full-history anomaly statistics are kept in the record as
non-failing diagnostics. The floor composes with a corporate
SERIES_START: the effective lower bound is the later of the two.

`history_needed_from` is NOT the floor: it is the plan-depth
bound (3 years before the latest cutoff). Admission evaluates
history through the latest cutoff, so for a cell whose own
cutoff is earlier the cohort is future-informed relative to
that cell — the record says so in `cohort_note` instead of
hiding it.

Stdlib only. The fetch hits Yahoo's chart API (the same endpoint
the pandas-ta / talib runners use); `gate_ticker()` itself is pure
and takes rows, so the tests run it on fixtures with no network.
"""
import argparse
import json
import math
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))

MIN_HISTORY_YEARS = 3
MAX_GAP_SESSIONS_EST = 10
# A calendar gap of N days holds ~N*5/7 sessions (EGX trades
# Sun-Thu, US Mon-Fri — both 5/7 density). 10 missed sessions is
# ~14 calendar days; the fail line is set at 21 days (~15 missed
# sessions) so ordinary holiday stretches never trip it, and the
# estimated missed count is reported for the record.
MAX_GAP_DAYS = 21
# Longest run of identical consecutive closes that still counts as
# a live series. The pre-2019 POUL segment (the stale-flat case
# that motivated this check) ran flat for months; a genuine
# limit-locked stretch is days, not weeks.
FLAT_RUN_LIMIT = 20

# Shared history floor (INS-REVIEW-025 / #446): rows before
# 2019-01-01 are dropped before every admission check — the
# same floor the runners apply to their indicator frames
# (backtest.py DROP_BEFORE, Kronos/pandas-ta clean/drop-before).
# The standalone gate CLI defaults to it; gate_ticker() takes
# it as an explicit optional argument instead.
HISTORY_FLOOR_DEFAULT = "2019-01-01"
CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/%s"
USER_AGENT = "Mozilla/5.0"


def parse_iso(s):
    try:
        return date.fromisoformat(str(s)[:10])
    except Exception:
        return None


def _absent_date(value):
    """True when a history_floor / series_start value intentionally
    means "no constraint": None, an empty string, or the CLI's
    'none' (case-insensitive). Distinct from an invalid value,
    which _invalid_date_reason() rejects by name."""
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == "" or value.strip().lower() == "none"
    return False


def _invalid_date_reason(value, name):
    """Reason string when a non-empty history_floor /
    series_start value is not a parseable YYYY-MM-DD date,
    else None. parse_iso() returns None for garbage, so
    without this check an invalid floor silently became no
    floor (INS-REVIEW-029)."""
    if _absent_date(value):
        return None
    if parse_iso(value) is None:
        return ("invalid %s %r (expected YYYY-MM-DD date, or "
                "none to disable)" % (name, value))
    return None


def fetch_chart(ticker, period1=0, period2=None, attempts=3):
    """Yahoo chart API: daily bars + dividend/split events.
    Returns (rows, events, events_available, events_error,
    dropped_dates) where
    rows are {"date": ISO, "close": float} sorted by date and
    events are [{"type": "dividend"|"split", "ex_date": ISO,
    "dps"|"ratio"}]. dropped_dates lists the session dates of
    bars dropped for a null, unparseable or non-finite close —
    a dropped bar must never silently shift the sessions that
    follow it (see fetch_realised). events_available is False when the feed is
    absent AND when any event record was dropped as unparseable —
    a partially-dropped feed is not a verified feed (a dropped
    dividend would otherwise be scored as an ordinary price move).
    events_error names the dropped records (None when the feed
    parsed cleanly). A failed fetch raises RuntimeError after
    `attempts` tries with backoff; a fetch that succeeds but
    carries no events still reports events_available False (the
    gate then fails the ticker — an unretrievable events feed must
    not be scored unadjusted, design §2.3)."""
    if period2 is None:
        period2 = int(time.time()) + 86400
    url = (CHART_URL % ticker
           + "?period1=%d&period2=%d&interval=1d&events=div,split"
           % (period1, period2))
    last_exc = None
    for attempt in range(attempts):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=30) as r:
                payload = json.loads(r.read().decode("utf-8"))
            break
        except Exception as e:  # noqa: BLE001 - retry, then raise
            last_exc = e
            if attempt < attempts - 1:
                time.sleep(2.0 * (attempt + 1))
    else:
        raise RuntimeError(
            "Yahoo chart fetch failed for %s after %d attempts: %s"
            % (ticker, attempts, last_exc))
    chart = payload.get("chart") or {}
    if chart.get("error"):
        raise RuntimeError("Yahoo chart error for %s: %s"
                           % (ticker, chart["error"]))
    results = chart.get("result") or []
    if not results:
        raise RuntimeError("Yahoo chart returned no result for %s"
                           % ticker)
    result = results[0]
    stamps = result.get("timestamp") or []
    quote = (result.get("indicators") or {}).get("quote") or [{}]
    closes = quote[0].get("close") or []
    meta = result.get("meta") or {}
    tz_name = meta.get("exchangeTimezoneName") or "UTC"
    rows = []
    dropped_dates = []
    for stamp, close in zip(stamps, closes):
        try:
            import datetime as _dt
            d = _dt.datetime.fromtimestamp(
                stamp, tz=_dt.timezone.utc)
            try:
                import zoneinfo
                d = d.astimezone(zoneinfo.ZoneInfo(tz_name))
            except Exception:
                pass
            day = d.date().isoformat()
        except Exception:
            continue
        # A bar whose close is null, unparseable or non-finite
        # is dropped from rows — but its DATE is recorded in
        # dropped_dates and returned with the fetch. Dropping
        # it silently would shift every later session one
        # position earlier for any consumer that counts
        # sessions by position (the realised scorer does):
        # fetch_realised blocks a cell whose realised window
        # contains a dropped date instead of scoring a horizon
        # on the wrong session's close.
        if close is None:
            dropped_dates.append(day)
            continue
        try:
            close_f = float(close)
        except Exception:
            dropped_dates.append(day)
            continue
        if not math.isfinite(close_f):
            # A NaN/inf close is not a bar: kept, it would
            # count toward realised maturity and be written
            # to realised.json as a bare NaN token.
            dropped_dates.append(day)
            continue
        rows.append({"date": day, "close": close_f})
    rows.sort(key=lambda r: r["date"])
    dropped_dates.sort()
    events = []
    dropped = []
    ev = (result.get("events") or {})
    for ts, div in (ev.get("dividend") or {}).items():
        try:
            dps = float(div.get("amount"))
            if not math.isfinite(dps):
                raise ValueError("non-finite dividend amount")
            import datetime as _dt
            d = _dt.datetime.fromtimestamp(
                int(ts), tz=_dt.timezone.utc).date().isoformat()
        except Exception:
            # Unparseable amount or timestamp: the record is
            # dropped AND the feed is marked failed (see below) —
            # never silently treated as "no dividend".
            dropped.append("dividend@%s" % ts)
            continue
        events.append({"type": "dividend", "ex_date": d, "dps": dps})
    for ts, split in (ev.get("split") or {}).items():
        try:
            import datetime as _dt
            d = _dt.datetime.fromtimestamp(
                int(ts), tz=_dt.timezone.utc).date().isoformat()
            num, den = split.get("numerator"), split.get("denominator")
            if num is None or den is None:
                raise ValueError("split without numerator/denominator")
        except Exception:
            dropped.append("split@%s" % ts)
            continue
        events.append({"type": "split", "ex_date": d,
                       "ratio": "%s:%s" % (num, den)})
    events.sort(key=lambda e: (e["ex_date"], e["type"]))
    events_error = (None if not dropped else
                    "%d event record(s) unparseable and dropped: %s"
                    % (len(dropped), ", ".join(dropped[:5])))
    events_available = bool(ev) and not dropped
    return rows, events, events_available, events_error, dropped_dates


def unpack_fetch(result):
    """(rows, events, events_available, events_error,
    dropped_dates) from a fetcher result — older/test fetchers
    return the 3-tuple without events_error (reads as None,
    clean) or the 4-tuple without dropped_dates (reads as no
    dropped bars)."""
    if len(result) == 5:
        return result
    if len(result) == 4:
        rows, events, ok, err = result
        return rows, events, ok, err, []
    rows, events, ok = result
    return rows, events, ok, None, []


def longest_flat_run(rows):
    """Longest run of identical consecutive closes."""
    best = cur = 1
    prev = None
    for r in rows:
        if prev is not None and r["close"] == prev:
            cur += 1
            best = max(best, cur)
        else:
            cur = 1
        prev = r["close"]
    return best if rows else 0


def max_gap(rows):
    """(max_gap_days, estimated missed sessions) between consecutive
    bars. The estimate is gap_days * 5/7 rounded, minus the one
    session the gap itself spans."""
    worst_days, worst_missed = 0, 0
    for a, b in zip(rows, rows[1:]):
        da, db = parse_iso(a["date"]), parse_iso(b["date"])
        if not da or not db:
            continue
        gap = (db - da).days
        missed = max(0, round(gap * 5 / 7) - 1)
        if gap > worst_days:
            worst_days, worst_missed = gap, missed
    return worst_days, worst_missed


def gate_ticker(ticker, rows, events_available, latest_cutoff,
                series_start=None, events_error=None,
                history_floor=None):
    """Pure admission decision (design §4). `rows` are
    {"date", "close"} sorted by date; `latest_cutoff` is the last
    cutoff the ticker must cover. `series_start` is the first
    usable session after a corporate discontinuity (POUL.CA:
    2026-09-28) — earlier rows are dropped before every check.
    `history_floor` is the shared history floor (2019-01-01):
    rows before it are dropped before every check too, and the
    effective lower bound is the later of the two floors — a
    later series_start wins over an earlier floor and vice
    versa. A malformed non-empty history_floor or
    series_start is rejected by name (a failed record whose
    reason names the bad value) instead of silently dropping
    the constraint; None, an empty string and the CLI's
    'none' mean no constraint. `events_error` (from fetch_chart)
    reports a feed
    parsing failure separately from a verified empty feed.
    History-quality checks (depth, gap, flat-run) use only bars
    on/before the cutoff and on/after the effective floor —
    bars after the cutoff cannot reject the ticker; coverage
    (history reaching the cutoff at all) is checked against the
    full fetched series instead. The admission fields (rows,
    first_date, longest_flat_run, max_gap_*) are window-relative:
    they describe the floored window, not the archived raw
    series. The pre-floor anomaly statistics are retained as
    non-failing diagnostics (full_history_*) — they are recorded
    and never reject. `history_needed_from` is the plan-depth
    bound (3 years before the latest cutoff), not the floor;
    admission through the latest cutoff makes cohort selection
    future-informed relative to an earlier cell cutoff, which
    the record discloses in `cohort_note` instead of hiding.
    Returns the gate record (JSON-serialisable)."""
    ticker = (ticker or "").upper()
    cutoff = parse_iso(latest_cutoff)
    # Reject a malformed non-empty floor / series_start
    # explicitly (INS-REVIEW-029): parse_iso() returns None
    # for garbage, and the old code silently dropped the
    # constraint — an invalid floor silently became no floor
    # and an invalid series_start silently lost the
    # corporate-history constraint. Intentional None, an empty
    # string and the CLI's 'none' still mean "no constraint"
    # and are distinct from invalid input. The rejection is a
    # named record (passed False), not an exception, so the
    # CLI and run_cell report it the same way as any other
    # gate failure.
    bad_date = (_invalid_date_reason(history_floor,
                                     "history_floor")
                or _invalid_date_reason(series_start,
                                        "series_start"))
    if bad_date is not None:
        # No admission window was computed: the admitted
        # fields stay empty and the raw-series diagnostics
        # still describe what was fetched.
        full_history = [r for r in rows
                        if parse_iso(r["date"]) is not None
                        and (cutoff is None
                             or parse_iso(r["date"]) <= cutoff)]
        full_flat = longest_flat_run(full_history)
        full_gap_days, full_gap_missed = max_gap(full_history)
        try:
            need_first = (
                cutoff - timedelta(days=366 * MIN_HISTORY_YEARS)
                ).isoformat() if cutoff is not None else None
        except Exception:
            need_first = None
        return {"ticker": ticker, "passed": False,
                "reasons": [bad_date],
                "rows": 0,
                "first_date": None, "last_date": None,
                "history_needed_from": need_first,
                "max_gap_days": 0,
                "max_gap_sessions_est": 0,
                "longest_flat_run": 0,
                "events_available": bool(events_available),
                "events_parse_error": events_error,
                "series_start": series_start,
                "history_floor": None,
                "full_history_rows": len(full_history),
                "full_history_first_date": (
                    full_history[0]["date"] if full_history else None),
                "full_history_longest_flat_run": full_flat,
                "full_history_max_gap_days": full_gap_days,
                "full_history_max_gap_sessions_est": full_gap_missed,
                "cohort_note": (
                    "No admission window was computed: the "
                    "history_floor / series_start value was "
                    "rejected (see reasons).")}
    # Effective lower bound: the later of the shared history
    # floor and the corporate series_start (either may be absent).
    floor_dates = [parse_iso(history_floor),
                   parse_iso(series_start)]
    floor_dates = [d for d in floor_dates if d is not None]
    effective_floor = max(floor_dates) if floor_dates else None
    usable = [r for r in rows
              if parse_iso(r["date"]) is not None
              and (cutoff is None or parse_iso(r["date"]) <= cutoff)
              and (effective_floor is None
                   or parse_iso(r["date"]) >= effective_floor)]
    fetched = [r for r in rows
               if parse_iso(r["date"]) is not None
               and (effective_floor is None
                    or parse_iso(r["date"]) >= effective_floor)]
    reasons = []
    first = usable[0]["date"] if usable else None
    last = usable[-1]["date"] if usable else None
    fetched_last = fetched[-1]["date"] if fetched else None
    need_first = None
    if cutoff is not None:
        try:
            need_first = (cutoff - timedelta(days=366 * MIN_HISTORY_YEARS)
                          ).isoformat()
        except Exception:
            need_first = None
    depth_ok = bool(first and need_first and first <= need_first)
    # Cohort disclosure (INS-REVIEW-025 / #446): admission
    # evaluates history through the latest cutoff, so for a cell
    # whose own cutoff is earlier the cohort is future-informed
    # relative to that cell. history_needed_from is the
    # plan-depth bound, not the gate's history floor.
    if cutoff is not None:
        cohort_note = (
            "Admission evaluates history through the latest "
            "cutoff %s; for a cell whose own cutoff is earlier, "
            "cohort selection uses data after that cell's cutoff "
            "(future-informed relative to the cell). "
            "history_needed_from %s is the plan-depth bound "
            "(3 years before the latest cutoff), not the gate's "
            "history floor."
            % (latest_cutoff, need_first))
    else:
        cohort_note = ("No latest cutoff was given, so no plan-depth "
                       "bound or cohort window applies.")
    if not usable:
        reasons.append("no usable history rows")
    elif not depth_ok:
        reasons.append(
            "history starts %s, later than the %d-year minimum %s"
            % (first, MIN_HISTORY_YEARS, need_first))
    if usable and cutoff is not None and (
            fetched_last is None or parse_iso(fetched_last) < cutoff):
        reasons.append("history ends %s, before the latest cutoff %s"
                       % (fetched_last, latest_cutoff))
    gap_days, gap_missed = max_gap(usable)
    if gap_missed > MAX_GAP_SESSIONS_EST:
        reasons.append(
            "max session gap ~%d sessions (%d calendar days), "
            "over the %d-session limit"
            % (gap_missed, gap_days, MAX_GAP_SESSIONS_EST))
    # The coverage check above only sees the fetched series'
    # last bar: history ending June 2 and resuming July 1
    # passes it for a June 30 cutoff, and max_gap only
    # measures gaps *inside* the usable rows. Check the tail
    # from the last usable bar through the cutoff with the
    # same session estimate, so a non-session cutoff (a
    # weekend) stays valid while a missing month is rejected.
    # Gaps starting after the cutoff are still ignored — the
    # tail is measured on usable rows only.
    if usable and cutoff is not None:
        tail_start = parse_iso(last)
        if tail_start is not None and tail_start < cutoff:
            tail_days = (cutoff - tail_start).days
            # No "- 1" here (unlike max_gap): the tail runs
            # from the last observed bar to the cutoff, and no
            # observed session closes it — subtracting one
            # admitted a ~11-session tail at the 10 limit.
            tail_missed = max(0, round(tail_days * 5 / 7))
            if tail_missed > MAX_GAP_SESSIONS_EST:
                reasons.append(
                    "history ends %s, ~%d sessions before the "
                    "latest cutoff %s, over the %d-session limit"
                    % (last, tail_missed, latest_cutoff,
                       MAX_GAP_SESSIONS_EST))
    # Full-history anomaly statistics, retained as NON-FAILING
    # diagnostics: every fetched bar on/before the cutoff, with
    # no lower bound — the pre-floor anomaly stays visible in
    # the record even though it no longer rejects.
    full_history = [r for r in rows
                    if parse_iso(r["date"]) is not None
                    and (cutoff is None
                         or parse_iso(r["date"]) <= cutoff)]
    full_flat = longest_flat_run(full_history)
    full_gap_days, full_gap_missed = max_gap(full_history)
    flat = longest_flat_run(usable)
    if flat > FLAT_RUN_LIMIT:
        reasons.append(
            "stale-flat segment: %d consecutive identical closes, "
            "over the %d-session limit" % (flat, FLAT_RUN_LIMIT))
    if not events_available:
        if events_error:
            reasons.append(
                "dividend/split events feed parsing failed: %s"
                % events_error)
        else:
            reasons.append("dividend/split events feed not retrievable")
    return {"ticker": ticker, "passed": not reasons,
            "reasons": reasons,
            "rows": len(usable),
            "first_date": first, "last_date": last,
            "history_needed_from": need_first,
            "max_gap_days": gap_days,
            "max_gap_sessions_est": gap_missed,
            "longest_flat_run": flat,
            "events_available": bool(events_available),
            "events_parse_error": events_error,
            "series_start": series_start,
            "history_floor": (effective_floor.isoformat()
                              if effective_floor is not None
                              else None),
            "full_history_rows": len(full_history),
            "full_history_first_date": (
                full_history[0]["date"] if full_history else None),
            "full_history_longest_flat_run": full_flat,
            "full_history_max_gap_days": full_gap_days,
            "full_history_max_gap_sessions_est": full_gap_missed,
            "cohort_note": cohort_note}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ticker", required=True)
    ap.add_argument("--latest-cutoff", required=True,
                    help="Last cutoff the ticker must cover (YYYY-MM-DD).")
    ap.add_argument("--series-start", default=None,
                    help="First usable session after a corporate "
                         "discontinuity (POUL.CA: 2026-09-28).")
    ap.add_argument("--history-floor",
                    default=HISTORY_FLOOR_DEFAULT,
                    help="Shared history floor (YYYY-MM-DD, default "
                         "2019-01-01): drop earlier sessions before "
                         "every admission check. Pass 'none' to "
                         "disable the floor (pre-fix behaviour).")
    ap.add_argument("--history-csv", default=None,
                    help="Offline mode: CSV with date,close columns "
                         "instead of a Yahoo fetch.")
    ap.add_argument("--events-available", action="store_true",
                    help="Offline mode: assert the events feed is "
                         "retrievable (default False when --history-csv "
                         "is used without this flag).")
    args = ap.parse_args(argv)
    events_error = None
    if args.history_csv:
        import csv
        rows = []
        with open(args.history_csv, newline="",
                  encoding="utf-8") as f:
            for r in csv.DictReader(f):
                try:
                    rows.append({"date": str(r["date"])[:10],
                                 "close": float(r["close"])})
                except Exception:
                    continue
        rows.sort(key=lambda r: r["date"])
        events_available = args.events_available
    else:
        rows, _events, events_available, events_error, _dropped = \
            unpack_fetch(fetch_chart(args.ticker))
    history_floor = (None
                     if (args.history_floor or "").lower() == "none"
                     else args.history_floor)
    rec = gate_ticker(args.ticker, rows, events_available,
                      args.latest_cutoff, args.series_start,
                      events_error, history_floor=history_floor)
    print(json.dumps(rec, indent=1))
    return 0 if rec["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
