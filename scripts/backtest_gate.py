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
CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/%s"
USER_AGENT = "Mozilla/5.0"


def parse_iso(s):
    try:
        return date.fromisoformat(str(s)[:10])
    except Exception:
        return None


def fetch_chart(ticker, period1=0, period2=None, attempts=3):
    """Yahoo chart API: daily bars + dividend/split events.
    Returns (rows, events, events_available, events_error) where
    rows are {"date": ISO, "close": float} sorted by date and
    events are [{"type": "dividend"|"split", "ex_date": ISO,
    "dps"|"ratio"}]. events_available is False when the feed is
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
    for stamp, close in zip(stamps, closes):
        if close is None:
            continue
        try:
            import datetime as _dt
            d = _dt.datetime.fromtimestamp(
                stamp, tz=_dt.timezone.utc)
            try:
                import zoneinfo
                d = d.astimezone(zoneinfo.ZoneInfo(tz_name))
            except Exception:
                pass
            rows.append({"date": d.date().isoformat(),
                         "close": float(close)})
        except Exception:
            continue
    rows.sort(key=lambda r: r["date"])
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
    return rows, events, events_available, events_error


def unpack_fetch(result):
    """(rows, events, events_available, events_error) from a
    fetcher result — older/test fetchers return the 3-tuple
    without events_error, which reads as None (clean)."""
    if len(result) == 4:
        return result
    rows, events, ok = result
    return rows, events, ok, None


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
                series_start=None, events_error=None):
    """Pure admission decision (design §4). `rows` are
    {"date", "close"} sorted by date; `latest_cutoff` is the last
    cutoff the ticker must cover. `series_start` is the first
    usable session after a corporate discontinuity (POUL.CA:
    2026-09-28) — earlier rows are dropped before every check.
    `events_error` (from fetch_chart) reports a feed parsing
    failure separately from a verified empty feed. History-quality
    checks (depth, gap, flat-run) use only bars on/before the
    cutoff — bars after it cannot reject the ticker; coverage
    (history reaching the cutoff at all) is checked against the
    full fetched series instead. Returns the gate record
    (JSON-serialisable)."""
    ticker = (ticker or "").upper()
    cutoff = parse_iso(latest_cutoff)
    usable = [r for r in rows
              if parse_iso(r["date"]) is not None
              and (cutoff is None or parse_iso(r["date"]) <= cutoff)
              and (series_start is None
                   or parse_iso(r["date"]) >= parse_iso(series_start))]
    fetched = [r for r in rows
               if parse_iso(r["date"]) is not None
               and (series_start is None
                    or parse_iso(r["date"]) >= parse_iso(series_start))]
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
            tail_missed = max(0, round(tail_days * 5 / 7) - 1)
            if tail_missed > MAX_GAP_SESSIONS_EST:
                reasons.append(
                    "history ends %s, ~%d sessions before the "
                    "latest cutoff %s, over the %d-session limit"
                    % (last, tail_missed, latest_cutoff,
                       MAX_GAP_SESSIONS_EST))
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
            "series_start": series_start}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ticker", required=True)
    ap.add_argument("--latest-cutoff", required=True,
                    help="Last cutoff the ticker must cover (YYYY-MM-DD).")
    ap.add_argument("--series-start", default=None,
                    help="First usable session after a corporate "
                         "discontinuity (POUL.CA: 2026-09-28).")
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
        rows, _events, events_available, events_error = \
            unpack_fetch(fetch_chart(args.ticker))
    rec = gate_ticker(args.ticker, rows, events_available,
                      args.latest_cutoff, args.series_start,
                      events_error)
    print(json.dumps(rec, indent=1))
    return 0 if rec["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
