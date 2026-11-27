"""Round 73: descriptive macro-event study on the EGX30 (Mubasher close). stdlib.

Design: docs/round72_macro_event_design.md (section 2), calendar:
evaluation/macro_event/calendar_primary.json (primary-sourced dates only).
DESCRIPTIVE: no p-value, no verdict word or key. Session 0 = the first
EGX30 session on or after the event date. Window offsets -2..+2 sessions.
Log return r_t = ln(close_t / close_{t-1}). Estimation window: sessions
-60..-11 relative to session 0, excluding any session inside another
event's -2..+2 window (any type). Abnormal return = r_t minus the mean
estimation return. Per event type and regime (split 2021-09-05, events on
or after the split are 'post'): AAR per offset, mean CAR(-2,+2), and the
leave-one-event-out (LOEO) spread of the mean CAR (min and max over the
events left out). Events lacking 60 pre-sessions or 2 post-sessions, or
with fewer than 20 usable estimation returns, are skipped and counted.
"""
import argparse
import csv
import json
import math
import os

OFFSETS = (-2, -1, 0, 1, 2)
EST_LO, EST_HI = -60, -11
MIN_EST = 20
SPLIT = "2021-09-05"


def load_series(path):
    rows = [(r["date"], float(r["close"])) for r in csv.DictReader(open(path))]
    rows.sort()
    return rows


def log_returns(series):
    return [(series[i][0], math.log(series[i][1] / series[i - 1][1])) for i in range(1, len(series))]


def session0(dates, d):
    for i, x in enumerate(dates):
        if x >= d:
            return i
    return None


def session_after(dates, d):
    """First session strictly after calendar date d (an after-close release counts for it)."""
    for i, x in enumerate(dates):
        if x > d:
            return i
    return None


CLOSE_HHMM = "14:30"   # EGX close, Cairo time (assumed; the rule below uses it as the boundary)


def is_after_close(e, rule):
    """before: never shifted (default; unknown-time rows stay on the event date).
    page_time: shifted when the row carries a page_time >= CLOSE_HHMM (unknown stays before).
    after: every event shifted."""
    if rule == "after":
        return True
    if rule == "page_time":
        t = e.get("page_time")
        return bool(t) and t >= CLOSE_HHMM
    return False


def study(series, events, split=SPLIT, rule="before"):
    rets = log_returns(series)          # index i of rets = return on session dates_r[i]
    dates = [d for d, _ in rets]
    r = [x for _, x in rets]
    idx = [session_after(dates, e["date"]) if is_after_close(e, rule) else session0(dates, e["date"])
           for e in events]
    blocked = set()
    for i in idx:
        if i is not None:
            blocked.update(range(i - 2, i + 3))
    cars = {}
    skipped = {}
    for e, i in zip(events, idx):
        key = (e["type"], "post" if e["date"] >= split else "pre")
        if i is None or i + 2 >= len(r) or i + EST_LO < 0:
            skipped[key] = skipped.get(key, 0) + 1
            continue
        est = [r[j] for j in range(i + EST_LO, i + EST_HI + 1) if j not in blocked]
        if len(est) < MIN_EST:
            skipped[key] = skipped.get(key, 0) + 1
            continue
        mu = sum(est) / len(est)
        ab = {o: r[i + o] - mu for o in OFFSETS}
        cars.setdefault(key, []).append((e["date"], ab, sum(ab.values())))
    out = {}
    for key in sorted(set(cars) | set(skipped)):
        ev = cars.get(key, [])
        n = len(ev)
        row = {"n_events": n, "n_skipped": skipped.get(key, 0)}
        if n:
            row["aar_by_offset"] = {str(o): sum(a[o] for _, a, _ in ev) / n for o in OFFSETS}
            row["mean_car"] = sum(c for _, _, c in ev) / n
            if n > 1:
                loo = [(sum(c for _, _, c in ev) - ev[k][2]) / (n - 1) for k in range(n)]
                row["loeo_mean_car_min"] = min(loo)
                row["loeo_mean_car_max"] = max(loo)
            else:
                row["loeo_mean_car_min"] = row["loeo_mean_car_max"] = None
            row["event_dates"] = [d for d, _, _ in ev]
        out["%s|%s" % key] = row
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--series", default="evaluation/index_regime/EGX30_mubasher_close.csv")
    ap.add_argument("--calendar", default="evaluation/macro_event/calendar_primary.json")
    ap.add_argument("--json")
    ap.add_argument("--release-rule", choices=["before", "page_time", "after"], default="before")
    a = ap.parse_args(argv)
    cal = json.load(open(a.calendar))
    res = {"basis": cal["basis"], "regime_split": SPLIT, "windows": "sessions -2..+2",
           "estimation": "sessions -60..-11", "n_calendar_events": len(cal["events"]),
           "release_rule": a.release_rule,
           "results": study(load_series(a.series), cal["events"], SPLIT, a.release_rule)}
    txt = json.dumps(res, indent=1)
    if a.json:
        open(a.json, "w").write(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()
