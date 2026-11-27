#!/usr/bin/env python3
"""Which cutoffs change the MPC-window flag if a decision date counts only
when it was public strictly before the cutoff date (round 87 follow-up).
Reads evaluation/macro_series/mpc_calendar_publication.json and the
realised series (cbe_decisions.json). Descriptive, no score, no verdict.

Usage: mpc_publication_check.py --captures DIR ...   (cutoffs from dir names)
"""
import argparse
import datetime
import json
import os
import re
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PUB = os.path.join(ROOT, "evaluation", "macro_series", "mpc_calendar_publication.json")
SERIES = os.path.join(ROOT, "evaluation", "macro_series", "cbe_decisions.json")
SESSIONS = {"day": 1, "week": 5, "month": 21}
HORIZONS = ("day", "week", "month")
EGX_WEEKEND = (4, 5)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _d(x):
    return datetime.date.fromisoformat(str(x)[:10])


def window_end(c, sessions):
    d = _d(c)
    n = 0
    while n < sessions:
        d += datetime.timedelta(days=1)
        if d.weekday() not in EGX_WEEKEND:
            n += 1
    return d


def known_dates(cutoff, pub):
    """Decision dates public strictly before the cutoff date."""
    c = _d(cutoff)
    out = set()
    for y in pub["years"].values():
        if _d(y["first_public_on_or_before"]) < c:
            out.update(y["dates"])
    for x in pub["cancelled"]:
        if _d(x["announced"]) < c:
            out.discard(x["date"])
    for x in pub["special"]:
        if _d(x["announced"]) < c:
            out.add(x["date"])
    return out


def flag(cutoff, horizon, dates):
    c = _d(cutoff)
    e = window_end(cutoff, SESSIONS[horizon])
    return any(c < _d(d) <= e for d in dates)


def compare(cutoffs, series_dates, pub):
    rows = []
    for c in sorted(set(cutoffs)):
        kn = known_dates(c, pub)
        for h in HORIZONS:
            a = flag(c, h, series_dates)
            b = flag(c, h, kn)
            rows.append({"cutoff": c, "horizon": h, "series_flag": a,
                         "published_flag": b, "changes": a != b})
    return rows


def cutoff_of(path):
    """The date path component of a capture dir, or None."""
    parts = [p for p in path.split(os.sep) if DATE_RE.match(p)]
    return parts[-1] if parts else None


def discover_cutoffs(roots, find=None, cell_number=None):
    """Cutoff dates of NUMBERED cells only (unnumbered captures never score)."""
    if find is None:
        sys.path.insert(0, ROOT + "/scripts")
        sys.path.insert(0, HERE)
        import score_adoption_594 as A
        find, cell_number = A.find_captures, A.cell_number
    out = set()
    for c in find(roots, None):
        if cell_number(c) is not None and cutoff_of(c):
            out.add(cutoff_of(c))
    return sorted(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--captures", nargs="+", required=True)
    a = ap.parse_args(argv)
    cutoffs = discover_cutoffs(a.captures)
    if not cutoffs:
        print("refusing: no cutoff dates found under %s" % " ".join(a.captures))
        return 2
    pub = json.load(open(PUB))
    series = sorted({r["published_date"][:10] for r in json.load(open(SERIES))})
    rows = compare(cutoffs, series, pub)
    print("numbered-cell cutoffs: %d, rows: %d" % (len(cutoffs), len(rows)))
    for r in rows:
        if r["series_flag"] or r["published_flag"]:
            print("%s %-5s series=%s published=%s%s" % (
                r["cutoff"], r["horizon"], r["series_flag"], r["published_flag"],
                "  CHANGES" if r["changes"] else ""))
    print("rows that change flag: %d" % sum(r["changes"] for r in rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
