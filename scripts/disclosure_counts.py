#!/usr/bin/env python3
"""Per-ticker per-session news-disclosure counts for the forward ledger
(INS-IMPROVE-007 / Moos round 12-13: news_count, has_disclosure).

Additive, optional, stdlib only. Reads the Mubasher announcement harvest
the cycle places under #768: one JSONL file per ticker, ann2/<TICKER>.jsonl,
each line {"id": str, "headline": str, "date": "DD-Mon-YYYY HH:MM",
"text": str, "attachments": [url, ...]}. The ticker is the file name
(POUL.jsonl -> POUL.CA); the line carries no ticker field. The directory
is a parameter (env LEDGER_DISCLOSURE_DIR); when it is unset or empty
nothing is added to any ledger row.

SESSION-DATE RULE (PENDING Moos's confirmation, stated here so it is
checkable): the Mubasher time is read as Cairo local time (the API does
not state a timezone; hours cluster 08-10 and 14-15, consistent with
Cairo, UNVERIFIED). EGX trades Sunday to Thursday and closes 14:30.
An item stamped at or before 14:30 on a trading day belongs to that
day's session; an item stamped after 14:30, or on Friday or Saturday,
belongs to the next trading day. No holiday calendar is applied (a
holiday session is not skipped), and the Mubasher time can trail the
EGX time by up to a day (POUL dividend example), so counts are a lower
bound on news timing accuracy until the 20-item EGX check is done.

Duplicates: items sharing an id within a ticker count once.
news_count is the number of distinct items assigned to the session;
has_disclosure is news_count > 0. Both are written only for tickers
that have a harvest file, so a ticker with no file carries no key (a
missing key is "not measured", never zero).
"""
import datetime as dt
import json
import os

CLOSE = (14, 30)
TRADING_DAYS = {6, 0, 1, 2, 3}      # Sun, Mon, Tue, Wed, Thu (weekday())
_MON = {m: i + 1 for i, m in enumerate(
    "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split())}


def parse_stamp(s):
    """'12-Nov-2026 08:44' -> datetime, or None."""
    try:
        d, m, rest = str(s).strip().split("-", 2)
        y, hm = rest.split(" ")
        hh, mm = hm.split(":")
        return dt.datetime(int(y), _MON[m.title()[:3]], int(d),
                           int(hh), int(mm))
    except (ValueError, KeyError, AttributeError):
        return None


def session_date(stamp):
    """ISO date of the session an item belongs to (rule in the module
    doc), or None for an unparseable stamp."""
    t = stamp if isinstance(stamp, dt.datetime) else parse_stamp(stamp)
    if t is None:
        return None
    d = t.date()
    after_close = (t.hour, t.minute) > CLOSE
    if d.weekday() not in TRADING_DAYS or after_close:
        d += dt.timedelta(days=1)
    while d.weekday() not in TRADING_DAYS:
        d += dt.timedelta(days=1)
    return d.isoformat()


def load_counts(directory):
    """{ledger_ticker: {session_iso: n}} from DIR/<T>.jsonl. A ticker
    with a readable file but no usable item maps to {} (measured, zero
    items). Unreadable files and bad lines are skipped."""
    out = {}
    if not directory or not os.path.isdir(directory):
        return out
    for fn in sorted(os.listdir(directory)):
        if not fn.lower().endswith(".jsonl"):
            continue
        t = os.path.splitext(fn)[0].upper()
        ticker = t if t == "NVDA" or "." in t else t + ".CA"
        seen, per = set(), {}
        try:
            with open(os.path.join(directory, fn), encoding="utf-8") as f:
                for line in f:
                    try:
                        rec = json.loads(line)
                    except ValueError:
                        continue
                    sd = session_date(rec.get("date"))
                    rid = str(rec.get("id") or "")
                    if sd is None or (rid and rid in seen):
                        continue
                    seen.add(rid)
                    per[sd] = per.get(sd, 0) + 1
        except OSError:
            continue
        out[ticker] = per
    return out


def annotate_rows(rows, counts):
    """Add news_count (int) and has_disclosure (bool) to each row whose
    ticker has a harvest file, keyed by the row's as_of session. Rows
    of other tickers are untouched. Returns the number annotated."""
    n = 0
    for r in rows:
        per = counts.get(r.get("ticker"))
        if per is None:
            continue
        c = per.get(str(r.get("as_of"))[:10], 0)
        r["news_count"] = c
        r["has_disclosure"] = c > 0
        n += 1
    return n
