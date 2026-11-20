#!/usr/bin/env python3
"""Regression tests for issue #434 (guard 1547Z follow-up, 2026-11-20).

Two silent failures, one day:

(a) The worker marked ledger-guard slots done even when the
heartbeat push never landed. `run_ledger_guard` ignored the
return value of `_write_guard_heartbeat` and returned True
whenever the publisher had run, so guard-2026-11-20T1547Z,
1647Z and 1747Z all read done while `ledger/guard-heartbeat.json`
on main still said 14:55:37Z — no heartbeat commit, no deploy-guard
run, no error anywhere. The fix: a slot is done only when its
heartbeat commit is confirmed on main (fetch + compare after the
push, with retries for a rejected push); otherwise the slot stays
un-done and the failure is recorded (ledger-failure.json +
missed-<slot> marker).

(b) The worker-side watchdog — the backstop for exactly this —
never paged. `guard_pending_from_bus` treated any guard id in the
append-only queue.json that was not done as "a guard run is
pending", so the never-completed 2026-11-19T0647Z slot suppressed
every watchdog page forever (watch-1630Z/1700Z/1730Z all completed
with no guard-alert.json while the heartbeat aged past 90 min).
The fix: only a slot within the claim-staleness horizon counts as
pending. The watchdog's own delivery is also verified now: a watch
job whose alert push fails stays un-done instead of reading done.

The deploy-guard `:23` schedule is documented as best-effort only
(#115/#142 history; 1 schedule run in the last 50 as of 2026-11-20)
— the relied-upon backstop is the fixed watchdog + the guard's
done-gate, not the cron.

Harness-first: the poison-slot, retry, empty-diff and watchdog
tests FAIL on pristine main and PASS on the fixed tree. Stdlib
only; the heartbeat tests run against real local git remotes
(no network, no credentials).

Run: python3 worker/test_worker_434.py (exit 0 = all pass).
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

_TMP = Path(tempfile.mkdtemp(prefix="gator434-test-"))
os.environ["GATOR_ROOT"] = str(_TMP)
os.environ.pop("GATOR_BUS_URL", None)

_HERE = Path(os.path.abspath(__file__)).parent
_REPO = _HERE.parent
sys.path.insert(0, str(_HERE))

import worker  # noqa: E402

PASSED = 0
PUSHED = []

GIT_ENV = dict(os.environ,
               GIT_AUTHOR_NAME="gator-test",
               GIT_AUTHOR_EMAIL="test@borsagator.local",
               GIT_COMMITTER_NAME="gator-test",
               GIT_COMMITTER_EMAIL="test@borsagator.local")

NOW = datetime(2026, 11, 20, 18, 0, tzinfo=timezone.utc)
POISON = "guard-2026-11-19T0647Z"      # never completed, still in queue
RECENT = "guard-2026-11-20T1747Z"      # 73 min old at NOW
SLOT = "guard-2026-11-20T1847Z"


def check(name, cond):
    global PASSED
    assert cond, name
    PASSED += 1
    print(f"pass: {name}")


def fake_push_bus(message):
    PUSHED.append(message)
    return True


def failing_push_bus(message):
    PUSHED.append(message)
    return False


def git(*args, cwd=None, check=True):
    return subprocess.run(["git"] + list(args), cwd=cwd, env=GIT_ENV,
                          capture_output=True, text=True, timeout=120,
                          check=check)


def make_remote(base):
    """Bare remote with a seeded main carrying a stale heartbeat."""
    remote = base / "remote.git"
    git("init", "--bare", "-b", "main", str(remote))
    seed = base / "seed"
    git("clone", str(remote), str(seed))
    git("-C", str(seed), "config", "user.email",
        "test@borsagator.local")
    git("-C", str(seed), "config", "user.name", "gator-test")
    hb = seed / "ledger" / "guard-heartbeat.json"
    hb.parent.mkdir(parents=True, exist_ok=True)
    hb.write_text(json.dumps(
        {"last_run_utc": "2026-11-20T14:55:37Z", "run_id": None,
         "status": "ok", "workflow": "ledger-guard",
         "note": "seed"}, indent=2) + "\n")
    git("-C", str(seed), "add", "ledger/guard-heartbeat.json")
    git("-C", str(seed), "commit", "-m", "seed heartbeat")
    git("-C", str(seed), "push", "origin", "HEAD:main")
    return remote


def make_checkout(base, remote):
    co = base / "checkout"
    git("clone", str(remote), str(co))
    git("-C", str(co), "config", "user.email", "moos@sherbeeny.com")
    git("-C", str(co), "config", "user.name", "borsagator-ledger")
    return co


def main_heartbeat(remote):
    r = git("--git-dir", str(remote), "show",
            "main:ledger/guard-heartbeat.json")
    return json.loads(r.stdout)


def write_publisher(checkout, exit_code):
    p = checkout / "scripts" / "ledger_publish.py"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f"import sys\nsys.exit({exit_code})\n")


def setup_bus(tmp, queue_entries, done_ids=(), claim_ids=()):
    worker.BUS = tmp / "bus"
    worker.OUT = tmp / "out"
    q = worker.BUS / "queue"
    q.mkdir(parents=True, exist_ok=True)
    (q / "queue.json").write_text(json.dumps(queue_entries))
    (q / "claims").mkdir(exist_ok=True)
    for cid in claim_ids:
        (q / "claims" / f"{cid}.json").write_text(json.dumps(
            {"id": cid, "at": worker.now()}))
    (q / "done").mkdir(exist_ok=True)
    for did in done_ids:
        (q / "done" / f"{did}.json").write_text(json.dumps(
            {"id": did, "at": worker.now()}))
    worker.push_bus = fake_push_bus
    PUSHED.clear()


# --- (b) guard_pending_from_bus -------------------------------------

def test_pending_poison_slot_is_not_pending():
    check("pending: 36h-old un-done slot is NOT pending",
          worker.guard_pending_from_bus([POISON], [], [], now=NOW)
          is False)


def test_pending_recent_slot_is_pending():
    check("pending: 73-min-old un-done slot IS pending",
          worker.guard_pending_from_bus([RECENT], [], [], now=NOW)
          is True)


def test_pending_done_slot_is_not_pending():
    check("pending: recent slot with a done record is NOT pending",
          worker.guard_pending_from_bus([RECENT], [], [RECENT],
                                        now=NOW) is False)


def test_pending_boundary():
    slot = "guard-2026-11-20T1200Z"
    check("pending: slot 5h59m old IS pending",
          worker.guard_pending_from_bus(
              [slot], [], [],
              now=datetime(2026, 11, 20, 17, 59,
                           tzinfo=timezone.utc)) is True)
    check("pending: slot 6h01m old is NOT pending",
          worker.guard_pending_from_bus(
              [slot], [], [],
              now=datetime(2026, 11, 20, 18, 1,
                           tzinfo=timezone.utc)) is False)


def test_pending_unparsable_guard_id_is_not_pending():
    check("pending: unparsable guard id is NOT pending (fail-safe "
          "towards paging)",
          worker.guard_pending_from_bus(["guard-junk"], [], [],
                                        now=NOW) is False)
    check("pending: non-guard ids never count",
          worker.guard_pending_from_bus(["sweep-1"], [], [],
                                        now=NOW) is False)


# --- (a) _write_guard_heartbeat --------------------------------------

def test_heartbeat_push_lands_and_verifies():
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        remote = make_remote(base)
        co = make_checkout(base, remote)
        ok = worker._write_guard_heartbeat(co, "ok", SLOT)
        check("heartbeat: push lands and verifies", ok is True)
        live = main_heartbeat(remote)
        check("heartbeat: on-main run_id is the job id",
              live.get("run_id") == SLOT)
        check("heartbeat: on-main status is ok",
              live.get("status") == "ok")


def test_heartbeat_push_retries_after_rejection():
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        remote = make_remote(base)
        co = make_checkout(base, remote)
        real_sh = worker.sh
        pushes = {"n": 0}

        def flaky_sh(cmd, cwd=None, env=None, timeout=3600):
            if "push origin HEAD:main" in cmd:
                pushes["n"] += 1
                if pushes["n"] == 1:
                    return subprocess.CompletedProcess(
                        cmd, 1, "", "rejected: non-fast-forward")
            return real_sh(cmd, cwd=cwd, env=env, timeout=timeout)

        worker.sh = flaky_sh
        try:
            ok = worker._write_guard_heartbeat(co, "ok", SLOT)
        finally:
            worker.sh = real_sh
        check("heartbeat: rejected push is retried and lands",
              ok is True)
        check("heartbeat: push attempted twice", pushes["n"] == 2)
        check("heartbeat: retried push is on main",
              main_heartbeat(remote).get("run_id") == SLOT)


def test_heartbeat_total_push_failure_returns_false():
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        remote = make_remote(base)
        co = make_checkout(base, remote)
        git("-C", str(co), "remote", "set-url", "origin",
            str(base / "no-such-remote.git"))
        ok = worker._write_guard_heartbeat(co, "ok", SLOT)
        check("heartbeat: broken remote returns False", ok is False)
        live = main_heartbeat(remote)
        check("heartbeat: nothing landed on main after failure",
              live.get("last_run_utc") == "2026-11-20T14:55:37Z")


def test_heartbeat_empty_diff_only_counts_when_verified():
    # Same job, same frozen second, healthy remote: the second
    # write stages nothing — it counts only because the on-main
    # content already matches. Break the remote afterwards and the
    # same duplicate must NOT count (the old code returned True on
    # the diff alone, unverified).
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        remote = make_remote(base)
        co = make_checkout(base, remote)
        frozen = datetime(2026, 11, 20, 18, 47, 30,
                          tzinfo=timezone.utc)

        class Frozen(datetime):
            @classmethod
            def now(cls, tz=None):
                return frozen

        real_dt = worker.datetime
        worker.datetime = Frozen
        try:
            first = worker._write_guard_heartbeat(co, "ok", SLOT)
            second = worker._write_guard_heartbeat(co, "ok", SLOT)
        finally:
            worker.datetime = real_dt
        check("heartbeat: first write lands", first is True)
        check("heartbeat: same-second duplicate verifies on main",
              second is True)
        git("-C", str(co), "remote", "set-url", "origin",
            str(base / "no-such-remote.git"))
        worker.datetime = Frozen
        try:
            third = worker._write_guard_heartbeat(co, "ok", SLOT)
        finally:
            worker.datetime = real_dt
        check("heartbeat: duplicate with unverifiable remote is "
              "False, not a free True", third is False)


# --- (a) run_ledger_guard --------------------------------------------

def _guard_setup(tmp, exit_code, break_remote=False):
    base = Path(tmp)
    remote = make_remote(base)
    co = make_checkout(base, remote)
    write_publisher(co, exit_code)
    if break_remote:
        git("-C", str(co), "remote", "set-url", "origin",
            str(base / "no-such-remote.git"))
    setup_bus(base / "bus-tmp", [])
    worker._ensure_main_checkout = lambda: co
    worker.scripts_match = lambda a, b, names: True
    return co, remote


def test_guard_returns_false_when_push_fails():
    with tempfile.TemporaryDirectory() as td:
        co, remote = _guard_setup(td, 0, break_remote=True)
        job = {"id": SLOT, "job": "ledger-guard"}
        ok = worker.run_ledger_guard(job)
        check("guard: push failure refuses done", ok is False)
        fail = json.loads(
            (worker.BUS / "queue" / "ledger-failure.json").read_text())
        check("guard: failure recorded as heartbeat-push-failed",
              fail.get("kind") == "heartbeat-push-failed")
        check("guard: failure record names the slot",
              fail.get("job_id") == SLOT)
        missed = worker.BUS / "queue" / "missed-2026-11-20T1847Z.json"
        check("guard: missed marker written",
              missed.exists())
        check("guard: missed marker names the slot + #434",
              SLOT in missed.read_text() and "#434" in missed.read_text())
        check("guard: no heartbeat landed on main",
              main_heartbeat(remote).get("last_run_utc")
              == "2026-11-20T14:55:37Z")


def test_guard_returns_true_when_push_lands():
    with tempfile.TemporaryDirectory() as td:
        co, remote = _guard_setup(td, 0)
        job = {"id": SLOT, "job": "ledger-guard"}
        ok = worker.run_ledger_guard(job)
        check("guard: landed push is done", ok is True)
        check("guard: no failure record on success",
              not (worker.BUS / "queue"
                   / "ledger-failure.json").exists())
        check("guard: heartbeat on main carries the job id",
              main_heartbeat(remote).get("run_id") == SLOT)


def test_guard_publisher_failed_but_heartbeat_lands_is_done():
    with tempfile.TemporaryDirectory() as td:
        co, remote = _guard_setup(td, 1)
        job = {"id": SLOT, "job": "ledger-guard"}
        ok = worker.run_ledger_guard(job)
        check("guard: publisher failed + heartbeat landed is done",
              ok is True)
        fail = json.loads(
            (worker.BUS / "queue" / "ledger-failure.json").read_text())
        check("guard: publisher failure still recorded",
              fail.get("kind") == "publish-failed")
        check("guard: failed-run heartbeat carries status failed",
              main_heartbeat(remote).get("status") == "failed")


# --- (b) run_ledger_watchdog ------------------------------------------

def _watch_setup(tmp, queue_entries, done_ids=(), claim_ids=()):
    base = Path(tmp)
    remote = make_remote(base)
    co = make_checkout(base, remote)
    (co / "scripts").mkdir(parents=True, exist_ok=True)
    for name in ("ledger_guard_watch.py", "ledger_publish.py",
                 "ledger.py"):
        shutil.copy(_REPO / "scripts" / name,
                    co / "scripts" / name)
    # Heartbeat 150 min old at real now: stale (> 90) but inside
    # the 420-minute maximum latency, so the pending decision is
    # what the test exercises — never the clock. (The seed's fixed
    # 14:55Z timestamp would age past 420 min within hours and
    # make the suppression test time-bombed.)
    stale = (datetime.now(timezone.utc).replace(microsecond=0)
             - timedelta(minutes=150))
    (co / "ledger" / "guard-heartbeat.json").write_text(json.dumps(
        {"last_run_utc": stale.strftime("%Y-%m-%dT%H:%M:%SZ"),
         "run_id": None, "status": "ok", "workflow": "ledger-guard",
         "note": "test"}, indent=2) + "\n")
    setup_bus(base / "bus-tmp", queue_entries, done_ids, claim_ids)
    worker._ensure_main_checkout = lambda: co
    worker.scripts_match = lambda a, b, names: True
    return co, remote


def recent_slot():
    """A guard slot ~1 h old at real now (queued, claimed, not
    done) — pending under the fixed rule at any run time."""
    now = datetime.now(timezone.utc)
    slot = now.replace(minute=47, second=0, microsecond=0)
    if slot > now:
        slot -= timedelta(hours=1)
    return slot.strftime("guard-%Y-%m-%dT%H%MZ")


def test_watchdog_pages_when_stale_and_poison_slot_present():
    # The 2026-11-20 replay: heartbeat stale, the never-completed
    # 2026-11-19T0647Z slot still in queue.json, the recent guard
    # slot done. The watchdog must page anyway.
    with tempfile.TemporaryDirectory() as td:
        recent = recent_slot()
        co, remote = _watch_setup(
            td,
            [{"id": POISON, "job": "ledger-guard",
              "added": "2026-11-19T06:51:00+00:00"},
             {"id": recent, "job": "ledger-guard",
              "added": "2026-11-20T17:51:00+00:00"}],
            done_ids=[recent])
        job = {"id": "watch-2026-11-20T1800Z",
               "job": "ledger-watchdog"}
        ok = worker.run_ledger_watchdog(job)
        check("watchdog: check runs", ok is True)
        alert = json.loads(
            (worker.BUS / "queue" / "guard-alert.json").read_text())
        check("watchdog: stale heartbeat pages despite poison slot",
              alert.get("state") == "dead")
        check("watchdog: alert names the watch job",
              alert.get("job_id") == job["id"])


def test_watchdog_suppressed_when_recent_guard_pending():
    with tempfile.TemporaryDirectory() as td:
        recent = recent_slot()
        co, remote = _watch_setup(
            td,
            [{"id": recent, "job": "ledger-guard",
              "added": "2026-11-20T17:51:00+00:00"}],
            claim_ids=[recent])
        job = {"id": "watch-2026-11-20T1800Z",
               "job": "ledger-watchdog"}
        ok = worker.run_ledger_watchdog(job)
        check("watchdog: suppressed check still returns True",
              ok is True)
        check("watchdog: suppressed check writes no alert",
              not (worker.BUS / "queue"
                   / "guard-alert.json").exists())


def test_watchdog_returns_false_when_alert_push_fails():
    with tempfile.TemporaryDirectory() as td:
        recent = recent_slot()
        co, remote = _watch_setup(
            td,
            [{"id": POISON, "job": "ledger-guard",
              "added": "2026-11-19T06:51:00+00:00"},
             {"id": recent, "job": "ledger-guard",
              "added": "2026-11-20T17:51:00+00:00"}],
            done_ids=[recent])
        worker.push_bus = failing_push_bus
        job = {"id": "watch-2026-11-20T1800Z",
               "job": "ledger-watchdog"}
        ok = worker.run_ledger_watchdog(job)
        check("watchdog: failed alert push refuses done",
              ok is False)


TESTS = [
    test_pending_poison_slot_is_not_pending,
    test_pending_recent_slot_is_pending,
    test_pending_done_slot_is_not_pending,
    test_pending_boundary,
    test_pending_unparsable_guard_id_is_not_pending,
    test_heartbeat_push_lands_and_verifies,
    test_heartbeat_push_retries_after_rejection,
    test_heartbeat_total_push_failure_returns_false,
    test_heartbeat_empty_diff_only_counts_when_verified,
    test_guard_returns_false_when_push_fails,
    test_guard_returns_true_when_push_lands,
    test_guard_publisher_failed_but_heartbeat_lands_is_done,
    test_watchdog_pages_when_stale_and_poison_slot_present,
    test_watchdog_suppressed_when_recent_guard_pending,
    test_watchdog_returns_false_when_alert_push_fails,
]

if __name__ == "__main__":
    for fn in TESTS:
        fn()
    print(f"{PASSED} checks passed ({len(TESTS)} tests)")
    sys.exit(0)
