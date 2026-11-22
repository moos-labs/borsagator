#!/usr/bin/env python3
"""Regression tests for issue #443 (PR-based ledger publish, 2026-11-22).

The old guard pushed the ledger and its heartbeat directly to
main; branch protection requires the close-gate check, which a
worker-pushed commit never carries, so every push was declined
("protected branch hook declined") and the ledger went stale
from 2026-11-20. The guard now stages ONE envelope commit
(validated ledger + the run's heartbeat) on a per-run branch
publish/ledger-<job-id>; the ledger-publish relay PRs it into
main; the worker marks the slot done only after the envelope's
heartbeat is confirmed ON MAIN (issue #434's done-gate, with the
relay in the middle).

Hang-proofing is the second half of the issue: on 2026-11-22 the
0847Z guard slot was claimed at 08:50:57Z and produced NO outcome
for over an hour while other jobs completed — the old bare
subprocess.run(timeout=...) kills only the publisher process on
expiry, and a surviving grandchild holding the output pipes can
block the output collect indefinitely. The publisher now runs
under sh_group (whole process group killed and verified empty),
the confirmation wait is bounded, and every exit leaves a
durable bus record or a confirmed heartbeat. The timeout test
below reproduces the pipe-holding grandchild shape and proves
the guard still completes (with a publish-timeout record).

The relay itself is GitHub Actions; here a simulator thread
plays it against the local remote (watch for the staging
branch, fast-forward main to it, delete the branch) so the
worker side is exercised end to end. Stdlib only; no network.

Run: python3 worker/test_worker_443.py (exit 0 = all pass).
"""
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="gator443-test-"))
os.environ["GATOR_ROOT"] = str(_TMP)
os.environ.pop("GATOR_BUS_URL", None)

_HERE = Path(os.path.abspath(__file__)).parent
sys.path.insert(0, str(_HERE))

import worker  # noqa: E402

PASSED = 0
PUSHED = []

GIT_ENV = dict(os.environ,
               GIT_AUTHOR_NAME="gator-test",
               GIT_AUTHOR_EMAIL="test@borsagator.local",
               GIT_COMMITTER_NAME="gator-test",
               GIT_COMMITTER_EMAIL="test@borsagator.local")

SLOT = "guard-2026-11-22T1047Z"
BRANCH = "publish/ledger-" + SLOT


def check(name, cond):
    global PASSED
    if cond:
        PASSED += 1
        print(f"  ok: {name}")
    else:
        print(f"FAIL: {name}")
        raise SystemExit(1)


def fake_push_bus(message):
    PUSHED.append(message)
    return True


def git(*args, cwd=None, check_rc=True):
    r = subprocess.run(["git"] + list(args), cwd=cwd, env=GIT_ENV,
                       capture_output=True, text=True, timeout=120)
    if check_rc and r.returncode != 0:
        raise AssertionError(f"git {args}: {r.stderr}")
    return r


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


def branch_heartbeat(remote, branch):
    r = git("--git-dir", str(remote), "show",
            f"{branch}:ledger/guard-heartbeat.json")
    return json.loads(r.stdout)


def setup_bus(tmp):
    worker.BUS = tmp / "bus"
    worker.OUT = tmp / "out"
    q = worker.BUS / "queue"
    q.mkdir(parents=True, exist_ok=True)
    (q / "queue.json").write_text("[]")
    (q / "claims").mkdir(exist_ok=True)
    (q / "done").mkdir(exist_ok=True)
    worker.push_bus = fake_push_bus
    PUSHED.clear()


# --- relay simulator -------------------------------------------------

class RelaySim(threading.Thread):
    """Plays the ledger-publish relay against the local remote:
    when the staging branch appears, fast-forward main to it
    (the merge) and delete the branch."""

    def __init__(self, base, remote, branch):
        super().__init__(daemon=True)
        self.base = base
        self.remote = remote
        self.branch = branch
        self.stop_flag = threading.Event()
        self.merges = 0

    def run(self):
        sim = self.base / "relaysim"
        git("clone", str(self.remote), str(sim))
        git("-C", str(sim), "config", "user.email",
            "test@borsagator.local")
        git("-C", str(sim), "config", "user.name", "gator-test")
        while not self.stop_flag.is_set():
            r = git("--git-dir", str(self.remote), "for-each-ref",
                    f"refs/heads/{self.branch}", check_rc=False)
            if r.stdout.strip():
                git("-C", str(sim), "fetch", "origin",
                    f"+refs/heads/{self.branch}:refs/remotes/origin/stage")
                git("-C", str(sim), "reset", "--hard",
                    "refs/remotes/origin/stage")
                git("-C", str(sim), "push", "origin", "HEAD:main")
                git("-C", str(sim), "push", "origin",
                    f":refs/heads/{self.branch}")
                self.merges += 1
            self.stop_flag.wait(0.2)


# --- stub publishers ---------------------------------------------------

STUB_OK = '''
import json, os, subprocess, sys
branch = sys.argv[sys.argv.index("--publish-branch") + 1]
doc = {"last_run_utc": "2026-11-22T10:47:05Z",
       "run_id": os.environ.get("LEDGER_RUN_ID"),
       "status": "ok", "workflow": "ledger-guard", "note": "stub"}
p = os.path.join("ledger", "guard-heartbeat.json")
os.makedirs("ledger", exist_ok=True)
with open(p, "w") as f:
    json.dump(doc, f, indent=2)
    f.write("\\n")
def g(*a):
    r = subprocess.run(["git"] + list(a), capture_output=True,
                       text=True)
    if r.returncode != 0:
        print(r.stderr, file=sys.stderr)
        sys.exit(3)
g("add", "ledger/")
g("commit", "-m", "Ledger: stub envelope (#64)")
g("push", "origin", "HEAD:refs/heads/" + branch)
print("staged on " + branch)
'''

STUB_FAIL = '''
import sys
print("publisher boom: degraded run", file=sys.stderr)
sys.exit(1)
'''

STUB_HANG = '''
import subprocess, sys, time
# A grandchild that inherits the output pipes and outlives us —
# the 2026-11-22 stall shape. sh_group must kill the whole group;
# a bare subprocess.run timeout would block on these pipes.
subprocess.Popen([sys.executable, "-c",
                  "import time; time.sleep(120)"])
time.sleep(120)
'''


def _guard_setup(tmp, stub, simulate_relay=True):
    base = Path(tmp)
    remote = make_remote(base)
    co = make_checkout(base, remote)
    p = co / "scripts" / "ledger_publish.py"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(stub)
    setup_bus(base / "bus-tmp")
    worker._ensure_main_checkout = lambda: co
    worker.scripts_match = lambda a, b, names: True
    worker.GUARD_CONFIRM_TIMEOUT_S = 30
    worker.GUARD_CONFIRM_POLL_S = 0.2
    sim = None
    if simulate_relay:
        sim = RelaySim(base, remote, BRANCH)
        sim.start()
    return co, remote, sim


def _stop(sim):
    if sim is not None:
        sim.stop_flag.set()
        sim.join(timeout=10)


# --- _guard_branch -----------------------------------------------------

def test_branch_names():
    check("branch: slot id maps into the publish/ledger- namespace",
          worker._guard_branch(SLOT) == BRANCH)
    check("branch: manual id maps the same way",
          worker._guard_branch("manual-guard-2026-11-22-001")
          == "publish/ledger-manual-guard-2026-11-22-001")
    check("branch: crafted id cannot escape the namespace",
          worker._guard_branch("../evil ref")
          == "publish/ledger--evil-ref")


# --- _stage_guard_heartbeat ---------------------------------------------

def test_stage_heartbeat_lands_branch():
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        remote = make_remote(base)
        co = make_checkout(base, remote)
        ok = worker._stage_guard_heartbeat(co, BRANCH, "failed", SLOT)
        check("stage: heartbeat-only envelope lands on the branch",
              ok is True)
        live = branch_heartbeat(remote, BRANCH)
        check("stage: branch heartbeat carries the job id",
              live.get("run_id") == SLOT)
        check("stage: branch heartbeat status is failed",
              live.get("status") == "failed")
        check("stage: main is untouched by staging",
              main_heartbeat(remote).get("last_run_utc")
              == "2026-11-20T14:55:37Z")


def test_stage_heartbeat_never_overwrites_existing_branch():
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        remote = make_remote(base)
        co = make_checkout(base, remote)
        check("stage: first staging lands",
              worker._stage_guard_heartbeat(co, BRANCH, "ok", SLOT)
              is True)
        tip = git("--git-dir", str(remote), "rev-parse",
                  BRANCH).stdout.strip()
        check("stage: existing branch counts as staged",
              worker._stage_guard_heartbeat(co, BRANCH, "failed",
                                            SLOT) is True)
        check("stage: existing branch tip is unchanged",
              git("--git-dir", str(remote), "rev-parse",
                  BRANCH).stdout.strip() == tip)
        check("stage: existing envelope keeps its ok status",
              branch_heartbeat(remote, BRANCH).get("status") == "ok")


def test_stage_heartbeat_broken_remote_returns_false():
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        remote = make_remote(base)
        co = make_checkout(base, remote)
        git("-C", str(co), "remote", "set-url", "origin",
            str(base / "no-such-remote.git"))
        check("stage: broken remote returns False",
              worker._stage_guard_heartbeat(co, BRANCH, "failed",
                                            SLOT) is False)


# --- run_ledger_guard ----------------------------------------------------

def test_guard_success_envelope_confirmed_is_done():
    with tempfile.TemporaryDirectory() as td:
        co, remote, sim = _guard_setup(td, STUB_OK)
        try:
            ok = worker.run_ledger_guard(
                {"id": SLOT, "job": "ledger-guard"})
        finally:
            _stop(sim)
        check("guard: staged + relayed envelope is done", ok is True)
        check("guard: the relay simulator merged once",
              sim.merges == 1)
        check("guard: no failure record on success",
              not (worker.BUS / "queue"
                   / "ledger-failure.json").exists())
        live = main_heartbeat(remote)
        check("guard: heartbeat on main carries the job id",
              live.get("run_id") == SLOT)
        check("guard: heartbeat on main is ok",
              live.get("status") == "ok")


def test_guard_publisher_failure_stages_failed_envelope():
    with tempfile.TemporaryDirectory() as td:
        co, remote, sim = _guard_setup(td, STUB_FAIL)
        try:
            ok = worker.run_ledger_guard(
                {"id": SLOT, "job": "ledger-guard"})
        finally:
            _stop(sim)
        check("guard: publisher failed + failed envelope landed "
              "is done", ok is True)
        fail = json.loads(
            (worker.BUS / "queue" / "ledger-failure.json").read_text())
        check("guard: publisher failure recorded as publish-failed",
              fail.get("kind") == "publish-failed")
        check("guard: failure record names the slot",
              fail.get("job_id") == SLOT)
        live = main_heartbeat(remote)
        check("guard: failed-run heartbeat carries status failed",
              live.get("status") == "failed")
        check("guard: failed-run heartbeat carries the job id",
              live.get("run_id") == SLOT)


def test_guard_publisher_timeout_is_killed_and_recorded():
    with tempfile.TemporaryDirectory() as td:
        co, remote, sim = _guard_setup(td, STUB_HANG)
        worker.GUARD_PUBLISH_TIMEOUT_S = 3
        started = time.monotonic()
        try:
            ok = worker.run_ledger_guard(
                {"id": SLOT, "job": "ledger-guard"})
        finally:
            _stop(sim)
            worker.GUARD_PUBLISH_TIMEOUT_S = 1800
        elapsed = time.monotonic() - started
        check("guard: timed-out publisher does not hang the guard "
              "(group killed, pipes freed)", elapsed < 60)
        check("guard: timeout + failed envelope landed is done",
              ok is True)
        fail = json.loads(
            (worker.BUS / "queue" / "ledger-failure.json").read_text())
        check("guard: timeout recorded as publish-timeout",
              fail.get("kind") == "publish-timeout")
        check("guard: failed heartbeat landed after the timeout",
              main_heartbeat(remote).get("status") == "failed")


def test_guard_unconfirmed_envelope_refuses_done():
    with tempfile.TemporaryDirectory() as td:
        co, remote, sim = _guard_setup(td, STUB_OK,
                                       simulate_relay=False)
        worker.GUARD_CONFIRM_TIMEOUT_S = 2
        ok = worker.run_ledger_guard({"id": SLOT,
                                      "job": "ledger-guard"})
        check("guard: envelope that never lands refuses done",
              ok is False)
        fail = json.loads(
            (worker.BUS / "queue" / "ledger-failure.json").read_text())
        check("guard: refusal recorded as envelope-unconfirmed",
              fail.get("kind") == "envelope-unconfirmed")
        missed = worker.BUS / "queue" / "missed-2026-11-22T1047Z.json"
        check("guard: missed marker written", missed.exists())
        check("guard: missed marker names the slot + #443",
              SLOT in missed.read_text()
              and "#443" in missed.read_text())
        check("guard: main still carries the seed heartbeat",
              main_heartbeat(remote).get("last_run_utc")
              == "2026-11-20T14:55:37Z")


def test_guard_d2_refusal_records_and_stages_failed_heartbeat():
    with tempfile.TemporaryDirectory() as td:
        co, remote, sim = _guard_setup(td, STUB_OK)
        worker.scripts_match = lambda a, b, names: False
        try:
            ok = worker.run_ledger_guard(
                {"id": SLOT, "job": "ledger-guard"})
        finally:
            _stop(sim)
        check("guard: D2 refusal is not done", ok is False)
        fail = json.loads(
            (worker.BUS / "queue" / "ledger-failure.json").read_text())
        check("guard: D2 refusal recorded as setup-failed",
              fail.get("kind") == "setup-failed")
        live = main_heartbeat(remote)
        check("guard: refusal heartbeat landed via the relay",
              live.get("run_id") == SLOT
              and live.get("status") == "failed")


def main():
    test_branch_names()
    test_stage_heartbeat_lands_branch()
    test_stage_heartbeat_never_overwrites_existing_branch()
    test_stage_heartbeat_broken_remote_returns_false()
    test_guard_success_envelope_confirmed_is_done()
    test_guard_publisher_failure_stages_failed_envelope()
    test_guard_publisher_timeout_is_killed_and_recorded()
    test_guard_unconfirmed_envelope_refuses_done()
    test_guard_d2_refusal_records_and_stages_failed_heartbeat()
    print(f"\n{PASSED} checks passed")


if __name__ == "__main__":
    main()
