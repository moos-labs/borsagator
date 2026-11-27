#!/usr/bin/env python3
"""Point-in-time check for the disclosure-event flag (round 87 rank 2).
Spec: docs/round87_disclosure_event_flag_spec.md. Check only: no fit, no score.
"""
import datetime
import sys

sys.dont_write_bytecode = True
SESSIONS = {"day": 1, "week": 5, "month": 21}
EGX_WEEKEND = (4, 5)  # Friday, Saturday


def _d(x):
    return datetime.date.fromisoformat(str(x)[:10])


def window_end(cutoff, sessions):
    d = _d(cutoff)
    n = 0
    while n < sessions:
        d += datetime.timedelta(days=1)
        if d.weekday() not in EGX_WEEKEND:
            n += 1
    return d


def classify(announced, forward, cutoff, horizon, verified=True, stale=False):
    """Return (flags, reason). flags is True only when the record is
    verified, not stale, announced strictly before the cutoff date, and
    its forward date lies in (cutoff, window end]."""
    if not verified:
        return False, "not verified"
    if stale:
        return False, "stale"
    if not announced:
        return False, "missing announced"
    if not forward:
        return False, "missing forward date"
    c, a, f = _d(cutoff), _d(announced), _d(forward)
    if not a < c:
        return False, "announced on or after the cutoff date"
    if not c < f <= window_end(c, SESSIONS[horizon]):
        return False, "forward date outside the window"
    return True, "flags"


if __name__ == "__main__":
    print(__doc__)
    sys.exit(0)
