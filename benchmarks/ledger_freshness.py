#!/usr/bin/env python3
"""Shared freshness helper for the ledger scorers (issue #791, round 10;
the brief is Moos's Slack 1795723578.685389, the scope is the cycle's
triage comment on #791).

Every scorer that reads ledger/ledger.json forecasts_detail prints one
line with the ledger's newest as_of, newest maturity_date (any row) and
newest maturity_date of a MATURED row, and adds the same fields to its
JSON output under "freshness". Dates only, no scores, so the line is safe
in the counts-only default output. Nothing here is a verdict.

Optional --max-age-days N (default off): age = today minus the newest
MATURED row's maturity_date. When the age is above N, or the ledger has
no matured row so its age cannot be established, the scorer refuses: it
prints the reason to stderr and exits 2 before scoring. --today
YYYY-MM-DD fixes "today" for reproducible runs; default is the local
date. Dates are compared as ISO calendar dates, no timezone logic.
"""
import datetime as dt
import sys

sys.dont_write_bytecode = True
REFUSE_CODE = 2


def add_args(ap):
    ap.add_argument("--max-age-days", type=int, default=None,
                    help="refuse when the newest matured row's maturity "
                         "date is more than N days before --today "
                         "(default off)")
    ap.add_argument("--today", default=None,
                    help="YYYY-MM-DD, default the local date")


def _date(s):
    try:
        return dt.date.fromisoformat(str(s)[:10])
    except (TypeError, ValueError):
        return None


def summary(rows):
    """Newest as_of / maturity_date / matured maturity_date (ISO strings
    or None) and the row count. Unparseable dates are ignored."""
    as_of = [d for d in (_date(r.get("as_of")) for r in rows) if d]
    mat = [d for d in (_date(r.get("maturity_date")) for r in rows) if d]
    mmat = [d for d in (_date(r.get("maturity_date")) for r in rows
                        if r.get("status") == "matured") if d]

    def top(xs):
        return max(xs).isoformat() if xs else None
    return {"rows": len(rows), "newest_as_of": top(as_of),
            "newest_maturity_date": top(mat),
            "newest_matured_maturity_date": top(mmat)}


def age_days(fr, today):
    d = _date(fr["newest_matured_maturity_date"])
    return None if d is None else (today - d).days


def line(fr):
    return ("ledger freshness: rows %d, newest as_of %s, newest "
            "maturity_date %s, newest matured maturity_date %s"
            % (fr["rows"], fr["newest_as_of"] or "none",
               fr["newest_maturity_date"] or "none",
               fr["newest_matured_maturity_date"] or "none"))


def check(rows, max_age_days=None, today=None):
    """Return (freshness dict, refusal message or None)."""
    fr = summary(rows)
    t = _date(today) if today else dt.date.today()
    if today and t is None:
        return fr, "--today must be YYYY-MM-DD"
    if max_age_days is None:
        return fr, None
    age = age_days(fr, t)
    if age is None:
        return fr, ("ledger refused: no matured row, so its age cannot "
                    "be established (--max-age-days %d)" % max_age_days)
    fr["age_days"] = age
    if age > max_age_days:
        return fr, ("ledger refused: newest matured maturity_date %s is "
                    "%d days before %s, over --max-age-days %d"
                    % (fr["newest_matured_maturity_date"], age,
                       t.isoformat(), max_age_days))
    return fr, None


def gate(rows, args):
    """Scorer entry point: print the line; return (freshness, exit code
    or None). The caller returns the code when it is not None."""
    fr, why = check(rows, args.max_age_days, args.today)
    if why:
        print(line(fr))
        print(why, file=sys.stderr)
        return fr, REFUSE_CODE
    print(line(fr))
    return fr, None
