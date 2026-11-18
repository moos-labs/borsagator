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

Issue #156: a stale heartbeat alone is NOT a dead guard. The
guard shares the `borsagator-ledger-publish` concurrency group
with the whole orchestrate job, so a guard tick queues behind a
running sweep (up to the sweep's 350-minute timeout) while the
heartbeat ages past the 90-minute threshold — a legitimate long
sweep used to produce a false "Ledger guard dead" signal. The
watchdog therefore asks the Actions API whether a ledger-guard
run is currently queued / waiting / in progress: while one is
pending, no signal is filed and no open signal is closed (the
guard has not proven itself alive yet — the heartbeat is still
stale). A maximum-latency alarm bounds the suppression: if the
heartbeat is older than MAX_LATENCY_MINUTES even with a guard
run pending, the signal fires anyway — a queued guard that never
lands is a real outage, not a long sweep. The latency cap is
derived from the two job timeouts: sweep 350 min + guard 30 min
+ 40 min scheduling/push slack = 420 min.

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
from ledger_publish import (ORG, REPO, SIGNAL_LABEL, ensure_signal_label,
                            find_open_signal_issues, _comment_issue,
                            _create_issue, _close_issue, _gh_token, gh_api)

STALE_MINUTES_DEFAULT = 90
# Issue #156: maximum heartbeat age tolerated while a guard run is
# pending — sweep timeout 350 min + guard timeout 30 min + 40 min
# scheduling/push slack. Past this, a queued guard is a real outage.
MAX_LATENCY_MINUTES_DEFAULT = 420
GUARD_WORKFLOW = "ledger-guard.yml"
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


def pending_guard_runs(token):
    """Non-completed ledger-guard runs (most recent first), each as
    {"id", "status", "created_at", "html_url"} — or None when the
    Actions API could not be read (no token / transport error /
    non-200). A run waiting on the shared borsagator-ledger-publish
    concurrency group shows up here while the sweep holding the lock
    is still running: that is a queued guard, not a dead one (issue
    #156). Any status other than "completed" counts as pending, so
    the exact label GitHub reports for a concurrency-waiting run
    ("waiting", "queued", ...) does not matter. Returns [] when the
    API answered and no guard run is pending."""
    if token is None:
        return None
    try:
        status, data = gh_api(
            "GET",
            f"/repos/{ORG}/{REPO}/actions/workflows/"
            f"{GUARD_WORKFLOW}/runs?per_page=5",
            token=token)
    except Exception as e:  # noqa: BLE001 — transport failure
        log(f"guard-run lookup failed ({e}) — treating as unknown")
        return None
    if status != 200 or not isinstance(data, dict):
        log(f"guard-run lookup failed (HTTP {status}) — "
            "treating as unknown")
        return None
    return [{"id": r.get("id"), "status": r.get("status"),
             "created_at": r.get("created_at"),
             "html_url": r.get("html_url")}
            for r in data.get("workflow_runs", [])
            if (r.get("status") or "") != "completed"]


def _pending_detail(pending):
    """One-line description of the oldest pending guard run (the
    list is most-recent-first, so the oldest waited longest)."""
    oldest = pending[-1]
    rid = oldest.get("id")
    if rid is None:
        return "a guard run is pending (forced)"
    return (f"guard run {rid} ({oldest.get('status')}, created "
            f"{oldest.get('created_at')}) is pending — queued "
            f"behind a running sweep or mid-run")


def check(heartbeat_path, now, stale_minutes, pending_runs=None,
          max_latency_minutes=MAX_LATENCY_MINUTES_DEFAULT):
    """Pure check: returns (state, why, last, status). No API calls.
    state is "fresh" (heartbeat within threshold), "suppressed"
    (stale heartbeat but a guard run is pending — issue #156), or
    "dead" (signal the outage).
    pending_runs: None = unknown (API not consulted / failed) — the
    old age-only decision stands, i.e. fail-safe towards paging;
    [] = no guard run pending; non-empty = a guard run is
    queued/running. A missing or unreadable heartbeat is always
    "dead": there is no baseline to measure latency against, and
    in production the file already exists, so its absence is itself
    worth paging about (a pending run writes it within ~30 min and
    the next tick clears the signal)."""
    last, status, error = read_heartbeat(heartbeat_path)
    if last is None:
        return "dead", error, None, status
    age_min = (now - last).total_seconds() / 60
    if age_min <= stale_minutes:
        return "fresh", (f"guard heartbeat fresh: "
                         f"{last.strftime('%Y-%m-%d %H:%M UTC')} "
                         f"({age_min:.0f} min ago, status {status})"), \
            last, status
    stale_why = (f"last guard heartbeat "
                 f"{last.strftime('%Y-%m-%d %H:%M UTC')} "
                 f"({age_min:.0f} min ago, status {status}) — "
                 f"older than the {stale_minutes}-minute threshold")
    if pending_runs:
        detail = _pending_detail(pending_runs)
        if age_min > max_latency_minutes:
            return "dead", (f"{stale_why}; {detail}, but the "
                            f"heartbeat is older than the "
                            f"{max_latency_minutes}-minute maximum "
                            f"latency — a queued guard that never "
                            f"lands is a real outage"), last, status
        return "suppressed", (f"{stale_why}, but {detail} — no "
                              f"dead-guard signal while a guard "
                              f"execution is pending (maximum latency "
                              f"{max_latency_minutes} min)"), last, status
    return "dead", stale_why, last, status


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
    ap.add_argument("--max-latency-minutes", type=int,
                    default=MAX_LATENCY_MINUTES_DEFAULT,
                    help="fire anyway when the heartbeat is older than "
                         "this even with a guard run pending (issue "
                         "#156; default: 420 = 350-min sweep timeout + "
                         "30-min guard timeout + 40 min slack)")
    ap.add_argument("--guard-pending", choices=("yes", "no"),
                    default=None,
                    help="force the pending-guard state instead of "
                         "querying the Actions API (tests / manual "
                         "runs): 'yes' = a guard run is queued or "
                         "running, 'no' = none is")
    ap.add_argument("--signal-out", default=None,
                    help="write the would-be signal payload JSON here "
                         "instead of calling the GitHub API (dry run)")
    a = ap.parse_args()
    now = parse_ts(a.now) if a.now else datetime.now(timezone.utc)
    if now is None:
        log(f"cannot parse --now {a.now!r}")
        return 2
    if a.guard_pending == "yes":
        pending = [{"id": None, "status": None, "created_at": None,
                    "html_url": None}]
    elif a.guard_pending == "no":
        pending = []
    else:
        pending = pending_guard_runs(_gh_token())
    state, why, last, status = check(a.heartbeat, now, a.stale_minutes,
                                     pending_runs=pending,
                                     max_latency_minutes=
                                     a.max_latency_minutes)
    if state == "fresh":
        log(why)
        ok = clear_dead_guard(_gh_token(), now, a.signal_out)
        return 0 if ok else 1
    if state == "suppressed":
        # Issue #156: a queued guard has not proven itself alive
        # yet — the heartbeat is still stale — so an open
        # dead-guard issue stays open until a fresh heartbeat
        # arrives; only the false page is suppressed.
        log(f"SUPPRESSED: {why}")
        return 0
    log(f"GUARD DEAD: {why}")
    ok = signal_dead_guard(_gh_token(), why, now, last, status,
                           a.stale_minutes, a.signal_out)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
