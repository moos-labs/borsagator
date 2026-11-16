#!/usr/bin/env python3
"""Ledger guard watchdog (issue #128).

The guard schedule missed 9 straight hourly ticks (#115) with
nothing in-repo noticing — the misses were only visible from outside
GitHub. The guard now writes a timestamped heartbeat on every
completed run (ledger/guard-heartbeat.json, see ledger-guard.yml);
this watchdog reads it and pages when the guard is dead.

Runs from .github/workflows/ledger-guard-watchdog.yml every 30
minutes. It fires when no guard heartbeat is younger than 90
minutes: a healthy guard runs hourly, so a live guard's heartbeat
is at most ~65 minutes old — 90 minutes leaves ~25 minutes of
slack for a slow run, and a 30-minute cadence means a dead guard
is noticed within 2 hours of its last heartbeat (90 + 30).

The signal is the same durable issue the publisher files
(`ledger-failure` label, never a digest issue — see
scripts/ledger_publish.py): a dedicated "Ledger guard dead" issue
is filed, or commented on if one is already open. When the
heartbeat is fresh again, an open guard-dead issue is closed with
a recovery comment. Publish-failure issues are NOT touched here —
the publisher owns those; a current ledger says nothing about
guard liveness.

Exit codes: 0 when the check ran (signal filed, or none needed);
1 when a needed signal could not be filed (no token / API failure)
so the run goes red instead of silently swallowing the page.
--signal-out writes the would-be signal payload as JSON instead of
calling the API (dry run / tests — it cannot dedup, so a stale
heartbeat always yields a "create" payload there).
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ledger_publish import (SIGNAL_LABEL, ensure_signal_label,
                            find_open_signal_issues, _comment_issue,
                            _create_issue, _close_issue, _gh_token)

STALE_MINUTES_DEFAULT = 90
GUARD_TITLE_PREFIX = "⚠️ Ledger guard dead"
HEARTBEAT_DEFAULT = "ledger/guard-heartbeat.json"


def log(msg):
    print(f"[ledger-guard-watch] {msg}", flush=True)


def parse_ts(s):
    """Parse an ISO-8601 UTC timestamp (with or without a trailing
    Z). Returns an aware datetime or None."""
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def read_heartbeat(path):
    """Returns (last_run_dt|None, status|None, error|None). A missing
    or unreadable heartbeat is an error, never a fresh one — a guard
    that never wrote a heartbeat has never proven itself alive."""
    try:
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
    except FileNotFoundError:
        return None, None, ("heartbeat file missing — no guard run "
                            "has written one yet")
    except Exception as e:
        return None, None, f"heartbeat file unreadable: {e}"
    dt = parse_ts(doc.get("last_run_utc"))
    if dt is None:
        return None, doc.get("status"), ("heartbeat has no parseable "
                                         "last_run_utc")
    return dt, doc.get("status"), None


def guard_dead_title_body(why, now, last, status, stale_minutes):
    last_line = (f"Last heartbeat: "
                 f"{last.strftime('%Y-%m-%d %H:%M UTC')} "
                 f"(status {status})" if last
                 else "Last heartbeat: never written")
    body = (f"⚠️ No completed ledger-guard run has been observed for "
            f"over {stale_minutes} minutes. The committed ledger on "
            f"`main` is only refreshed by the guard between sweeps, so "
            f"a dead guard leaves it stale with no red run.\n\n"
            f"{last_line}\n"
            f"**Checked:** {now.strftime('%Y-%m-%d %H:%M UTC')}\n"
            f"**Detail:** {why}\n\n"
            "This issue is the durable signal for #128 — the guard's "
            "hourly schedule is the retry path for failed ledger "
            "publishes, so a dead guard is load-bearing (see #115). "
            "It is NOT a digest issue: the digest watch only closes "
            "digest issues, and board-sync only skips digest issues — "
            "this one stays open until a fresh heartbeat appears. The "
            "watchdog closes it automatically with a recovery comment "
            "when the guard is alive again.\n\n"
            # WSJF 6.0 is the board's auto-promote threshold: a dead
            # retry path leaves every publish failure unretried.
            "WSJF: 6.0")
    return GUARD_TITLE_PREFIX, body


def _recovery_comment(now):
    return (f"✅ Guard heartbeat fresh again "
            f"({now.strftime('%Y-%m-%d %H:%M UTC')}) — the guard is "
            f"alive, closing this dead-guard signal.")


def check(heartbeat_path, now, stale_minutes):
    """Pure check: returns (stale, why, last, status). No API calls."""
    last, status, error = read_heartbeat(heartbeat_path)
    if last is None:
        return True, error, None, status
    age_min = (now - last).total_seconds() / 60
    if age_min > stale_minutes:
        return True, (f"last guard heartbeat "
                      f"{last.strftime('%Y-%m-%d %H:%M UTC')} "
                      f"({age_min:.0f} min ago, status {status}) — "
                      f"older than the {stale_minutes}-minute "
                      f"threshold"), last, status
    return False, (f"guard heartbeat fresh: "
                   f"{last.strftime('%Y-%m-%d %H:%M UTC')} "
                   f"({age_min:.0f} min ago, status {status})"), last, status


def signal_dead_guard(token, why, now, last, status, stale_minutes,
                      signal_out=None):
    """Ensure an open guard-dead signal issue exists (create, or
    comment on the open one). Returns True on success."""
    title, body = guard_dead_title_body(why, now, last, status,
                                        stale_minutes)
    if signal_out:
        payload = {"action": "create", "title": title, "body": body,
                   "labels": [SIGNAL_LABEL], "issue_number": None,
                   "reason": why}
        with open(signal_out, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        log(f"dry run: guard-dead signal payload written to {signal_out}")
        return True
    if token is None:
        log("no GH_TOKEN — cannot file the guard-dead signal")
        return False
    try:
        ensure_signal_label(token)
        existing = find_open_signal_issues(token, GUARD_TITLE_PREFIX)
        if existing:
            number = existing[0]["number"]
            if _comment_issue(token, number,
                              f"⚠️ Guard still dead "
                              f"({now.strftime('%Y-%m-%d %H:%M UTC')}).\n\n"
                              f"**Detail:** {why}"):
                log(f"guard-dead signal: recurrence noted on open "
                    f"issue #{number}")
                return True
            return False
        number = _create_issue(token, title, body)
        if number:
            log(f"guard-dead signal: issue #{number} filed")
            return True
        return False
    except Exception as e:
        log(f"guard-dead signal: filing failed ({e})")
        return False


def clear_dead_guard(token, now, signal_out=None):
    """Close any open guard-dead signal issue now the heartbeat is
    fresh. Returns True when nothing is left open (or there was
    nothing to close)."""
    if signal_out:
        payload = {"action": "none", "title": None, "body": None,
                   "labels": [SIGNAL_LABEL], "issue_number": None,
                   "reason": "heartbeat fresh — no signal needed"}
        with open(signal_out, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        log(f"dry run: heartbeat fresh, no signal — wrote {signal_out}")
        return True
    if token is None:
        log("heartbeat fresh, but no GH_TOKEN — cannot verify whether "
            "a guard-dead issue is still open")
        return True
    try:
        existing = find_open_signal_issues(token, GUARD_TITLE_PREFIX)
        ok = True
        for it in existing:
            if _close_issue(token, it["number"],
                            _recovery_comment(now)):
                log(f"guard-dead signal: closed issue #{it['number']} "
                    f"(guard alive again)")
            else:
                ok = False
        return ok
    except Exception as e:
        log(f"guard-dead signal: clearing failed ({e})")
        return False


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--heartbeat", default=HEARTBEAT_DEFAULT,
                    help="heartbeat JSON to read (default: "
                         "ledger/guard-heartbeat.json)")
    ap.add_argument("--now", default=None,
                    help="ISO UTC timestamp to check against "
                         "(default: now; tests only)")
    ap.add_argument("--stale-minutes", type=int,
                    default=STALE_MINUTES_DEFAULT,
                    help="fire when the heartbeat is older than this "
                         "(default: 90)")
    ap.add_argument("--signal-out", default=None,
                    help="write the would-be signal payload JSON here "
                         "instead of calling the GitHub API (dry run)")
    a = ap.parse_args()
    now = parse_ts(a.now) if a.now else datetime.now(timezone.utc)
    if now is None:
        log(f"cannot parse --now {a.now!r}")
        return 2
    stale, why, last, status = check(a.heartbeat, now, a.stale_minutes)
    if not stale:
        log(why)
        ok = clear_dead_guard(_gh_token(), now, a.signal_out)
        return 0 if ok else 1
    log(f"GUARD DEAD: {why}")
    ok = signal_dead_guard(_gh_token(), why, now, last, status,
                           a.stale_minutes, a.signal_out)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
