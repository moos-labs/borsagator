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


def test_branch_state_tristate():
    # Issue #501: present / positively absent / lookup error are
    # three different answers, and the error is recorded.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        remote = make_remote(base)
        co = make_checkout(base, remote)
        state, err = worker._branch_state_on_origin(co, BRANCH)
        check("501: missing branch is positively ABSENT",
              state == worker.BRANCH_ABSENT and err is None)
        check("501: staging lands",
              worker._stage_guard_heartbeat(co, BRANCH, "ok", SLOT)
              is True)
        state, err = worker._branch_state_on_origin(co, BRANCH)
        check("501: staged branch is PRESENT",
              state == worker.BRANCH_PRESENT and err is None)
        git("-C", str(co), "remote", "set-url", "origin",
            str(base / "no-such-remote.git"))
        state, err = worker._branch_state_on_origin(co, BRANCH)
        check("501: broken remote is UNKNOWN, never absent",
              state == worker.BRANCH_UNKNOWN and err)
        check("501: the lookup error is recorded",
              worker.BRANCH_LOOKUP_ERROR == err)


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


def _stage_full_envelope(base, remote, ledger_doc):
    """Stage an envelope (heartbeat + ledger.json) on BRANCH from
    a scratch clone; returns the heartbeat doc staged."""
    scratch = base / "stage"
    git("clone", str(remote), str(scratch))
    git("-C", str(scratch), "config", "user.email",
        "test@borsagator.local")
    git("-C", str(scratch), "config", "user.name", "gator-test")
    hb = {"last_run_utc": "2026-11-22T10:47:05Z", "run_id": SLOT,
          "status": "ok", "workflow": "ledger-guard",
          "note": "full envelope"}
    (scratch / "ledger" / "guard-heartbeat.json").write_text(
        json.dumps(hb, indent=2) + "\n")
    (scratch / "ledger" / "ledger.json").write_text(
        json.dumps(ledger_doc, indent=2) + "\n")
    git("-C", str(scratch), "add", "ledger/")
    git("-C", str(scratch), "commit", "-m", "stage envelope")
    git("-C", str(scratch), "push", "origin",
        f"HEAD:refs/heads/{BRANCH}")
    return hb


def test_guard_envelope_full_content_equality():
    # Issue #498: confirmation enforces FULL expected-content
    # equality — the staged heartbeat landing on main is not
    # enough when the envelope's ledger outputs did not land
    # byte-identical with it.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        remote = make_remote(base)
        co = make_checkout(base, remote)
        hb = _stage_full_envelope(base, remote, {"v": 1})
        expected = worker._staged_guard_envelope(co, BRANCH)
        check("498: staged envelope read back with its blobs",
              expected is not None
              and expected["heartbeat"] == hb
              and "ledger/ledger.json" in expected["blobs"]
              and "ledger/guard-heartbeat.json" in expected["blobs"])
        # Land the heartbeat exactly, but a DIFFERENT ledger.json.
        land = base / "land"
        git("clone", str(remote), str(land))
        git("-C", str(land), "config", "user.email",
            "test@borsagator.local")
        git("-C", str(land), "config", "user.name", "gator-test")
        (land / "ledger" / "guard-heartbeat.json").write_text(
            json.dumps(hb, indent=2) + "\n")
        (land / "ledger" / "ledger.json").write_text(
            json.dumps({"v": 2}, indent=2) + "\n")
        git("-C", str(land), "add", "ledger/")
        git("-C", str(land), "commit", "-m", "tampered landing")
        git("-C", str(land), "push", "origin", "HEAD:main")
        check("498: heartbeat landed but ledger content differs "
              "— not confirmed",
              worker._guard_envelope_on_main(co, SLOT, expected)
              is None)
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        remote = make_remote(base)
        co = make_checkout(base, remote)
        hb = _stage_full_envelope(base, remote, {"v": 1})
        expected = worker._staged_guard_envelope(co, BRANCH)
        # Land the exact envelope (fast-forward main to it).
        land = base / "land"
        git("clone", str(remote), str(land))
        git("-C", str(land), "fetch", "origin",
            f"+refs/heads/{BRANCH}:refs/remotes/origin/stage")
        git("-C", str(land), "reset", "--hard",
            "refs/remotes/origin/stage")
        git("-C", str(land), "push", "origin", "HEAD:main")
        doc = worker._guard_envelope_on_main(co, SLOT, expected)
        check("498: exact envelope landing confirms",
              doc is not None and doc == hb)
        # A later main commit altering a ledger output (a newer
        # envelope superseding this one): the TIP no longer
        # carries this envelope — but PR #515 review
        # (INS-REVIEW-092, confirm at M not the tip) rules that
        # the later state must not rewrite this attempt's
        # verdict either: the envelope landed, in full, at its
        # merge commit, and history confirmation finds it there.
        (land / "ledger" / "ledger.json").write_text(
            json.dumps({"v": 3}, indent=2) + "\n")
        git("-C", str(land), "add", "ledger/")
        git("-C", str(land), "commit", "-m", "later envelope")
        git("-C", str(land), "push", "origin", "HEAD:main")
        check("498: later main state removes the envelope from "
              "the tip check",
              worker._guard_envelope_on_main(co, SLOT, expected)
              is None)
        doc = worker._guard_envelope_in_main_history(
            co, SLOT, expected)
        check("515: confirmation stands at the merge commit "
              "despite the later main state",
              doc is not None and doc == hb)


def test_guard_envelope_persisted_survives_branch_deletion():
    # Issue #499: the expected envelope is persisted (heartbeat
    # content, blob hashes, envelope commit) before confirmation,
    # and confirmation stands on that record + the merge evidence
    # after the relay deletes the staging branch.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        setup_bus(base)
        remote = make_remote(base)
        co = make_checkout(base, remote)
        check("499: staging lands",
              worker._stage_guard_heartbeat(co, BRANCH, "ok", SLOT)
              is True)
        record = worker._load_persisted_guard_envelope(SLOT)
        tip = git("--git-dir", str(remote), "rev-parse",
                  BRANCH).stdout.strip()
        check("499: envelope record persisted at staging time",
              record is not None)
        check("499: record names the envelope commit",
              record.get("envelope_commit") == tip)
        check("499: record carries heartbeat content + blob hashes",
              record["heartbeat"].get("run_id") == SLOT
              and record["heartbeat"].get("status") == "ok"
              and "ledger/guard-heartbeat.json" in record["blobs"])
        # Land the envelope on main, then delete the branch —
        # the relay's order (merge, evidence, delete).
        land = base / "land"
        git("clone", str(remote), str(land))
        git("-C", str(land), "fetch", "origin",
            f"+refs/heads/{BRANCH}:refs/remotes/origin/stage")
        git("-C", str(land), "reset", "--hard",
            "refs/remotes/origin/stage")
        git("-C", str(land), "push", "origin", "HEAD:main")
        git("--git-dir", str(remote), "update-ref", "-d",
            f"refs/heads/{BRANCH}")
        check("499: branch is gone after deletion",
              git("--git-dir", str(remote), "rev-parse", BRANCH,
                  check_rc=False).returncode != 0)
        check("499: staged read can no longer see the envelope",
              worker._staged_guard_envelope(co, BRANCH) is None)
        doc = worker._confirm_guard_envelope(
            co, SLOT, BRANCH, timeout_s=5, poll_s=0.2)
        check("499: confirmation stands on the persisted record",
              doc is not None and doc.get("run_id") == SLOT
              and doc.get("status") == "ok")


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


def test_guard_stale_same_id_heartbeat_does_not_confirm():
    # PR review finding on #491: an earlier attempt of the same
    # job staged an envelope whose relay merge landed only AFTER
    # that attempt's confirmation window expired, leaving a
    # heartbeat with this run_id on main. A later attempt whose
    # own envelope never lands must NOT confirm against that
    # stale heartbeat — confirmation requires the on-main doc to
    # be THIS attempt's staged envelope (run_id + last_run_utc).
    with tempfile.TemporaryDirectory() as td:
        co, remote, sim = _guard_setup(td, STUB_FAIL,
                                       simulate_relay=False)
        stale = Path(td) / "stale"
        git("clone", str(remote), str(stale))
        git("-C", str(stale), "config", "user.email",
            "test@borsagator.local")
        git("-C", str(stale), "config", "user.name", "gator-test")
        (stale / "ledger" / "guard-heartbeat.json").write_text(
            json.dumps(
                {"last_run_utc": "2026-11-22T09:00:00Z",
                 "run_id": SLOT, "status": "ok",
                 "workflow": "ledger-guard",
                 "note": "earlier attempt"}, indent=2) + "\n")
        git("-C", str(stale), "add", "ledger/guard-heartbeat.json")
        git("-C", str(stale), "commit", "-m", "stale heartbeat")
        git("-C", str(stale), "push", "origin", "HEAD:main")
        worker.GUARD_CONFIRM_TIMEOUT_S = 2
        ok = worker.run_ledger_guard({"id": SLOT,
                                      "job": "ledger-guard"})
        check("guard: stale same-id heartbeat does not confirm "
              "a later attempt", ok is False)
        fail = json.loads(
            (worker.BUS / "queue" / "ledger-failure.json").read_text())
        check("guard: stale-confirm refusal recorded as "
              "envelope-unconfirmed",
              fail.get("kind") == "envelope-unconfirmed")
        live = main_heartbeat(remote)
        check("guard: main still carries the stale heartbeat",
              live.get("last_run_utc") == "2026-11-22T09:00:00Z")


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


def test_guard_envelope_attempt_binding():
    # PR #515 review: a persisted envelope record is bound to
    # the attempt that produced it. Exact-content equality
    # proves which content is on main, not which attempt
    # produced it — a later attempt (reclaim, new claim) whose
    # own envelope never lands must NOT confirm on the earlier
    # attempt's record.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        setup_bus(base)
        remote = make_remote(base)
        co = make_checkout(base, remote)
        claims = worker.BUS / "queue" / "claims"
        (claims / f"{SLOT}.json").write_text(json.dumps(
            {"worker": "worker-5", "at": "2026-11-22T10:00:00Z",
             "job": "ledger-guard"}))
        attempt_a = worker._guard_attempt_id(SLOT)
        check("515: attempt id comes from the claim record",
              attempt_a == "worker-5@2026-11-22T10:00:00Z")
        check("515: staging lands",
              worker._stage_guard_heartbeat(
                  co, BRANCH, "ok", SLOT, attempt_id=attempt_a)
              is True)
        record = worker._load_persisted_guard_envelope(
            SLOT, attempt_id=attempt_a)
        check("515: the producing attempt can load its record",
              record is not None
              and record.get("attempt_id") == attempt_a)
        other = "worker-5@2026-11-22T11:00:00Z"
        check("515: a later attempt cannot load the earlier "
              "attempt's record",
              worker._load_persisted_guard_envelope(
                  SLOT, attempt_id=other) is None)


def test_guard_envelope_local_copy_survives_rejected_push():
    # PR #515 review: when the bus push is rejected, the record
    # must survive OUTSIDE the resettable bus clone, and loading
    # it retries publication without rerunning the job.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        setup_bus(base)
        local = worker._pending_envelope_path(SLOT)
        local.unlink(missing_ok=True)
        env = {"heartbeat": {"run_id": SLOT, "status": "ok",
                             "last_run_utc":
                             "2026-11-22T10:47:05Z"},
               "blobs": {"ledger/guard-heartbeat.json": "a" * 40},
               "commit": "b" * 40}
        worker.push_bus = lambda message: False
        try:
            worker._persist_guard_envelope(SLOT, BRANCH, env)
        finally:
            worker.push_bus = fake_push_bus
        check("515: rejected bus push leaves the durable local "
              "copy in place", local.exists())
        # The bus copy never landed (and a sync would reset it
        # away): remove it to simulate the reset.
        worker._guard_envelope_record_path(SLOT).unlink(
            missing_ok=True)
        record = worker._load_persisted_guard_envelope(SLOT)
        check("515: load falls back to the durable local copy",
              record is not None
              and record["heartbeat"]["run_id"] == SLOT)
        check("515: load retried publication onto the bus",
              worker._guard_envelope_record_path(SLOT).exists())


def test_guard_confirm_deadline_honoured_before_accepting():
    # PR #515 review: a confirmation pass that finds the
    # document only AFTER its deadline must not return success.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        setup_bus(base)
        co = base / "checkout"
        co.mkdir()
        env = {"heartbeat": {"run_id": SLOT, "status": "ok"},
               "blobs": {}, "commit": "c" * 40}
        orig_staged = worker._staged_guard_envelope
        orig_persist = worker._persist_guard_envelope
        orig_on_main = worker._guard_envelope_on_main

        def slow_on_main(checkout, job_id, expected):
            time.sleep(0.4)
            return {"run_id": SLOT, "status": "ok"}

        worker._staged_guard_envelope = lambda c, b: env
        worker._persist_guard_envelope = lambda *a, **k: env
        worker._guard_envelope_on_main = slow_on_main
        try:
            doc = worker._confirm_guard_envelope(
                co, SLOT, BRANCH, timeout_s=0.1, poll_s=0.05)
        finally:
            worker._staged_guard_envelope = orig_staged
            worker._persist_guard_envelope = orig_persist
            worker._guard_envelope_on_main = orig_on_main
        check("515: document found after the deadline is NOT "
              "accepted", doc is None)


def test_persist_failure_blocks_handoff():
    # INS-REVIEW-093: a required durable local write failure
    # must BLOCK the handoff, not be swallowed — _persist
    # returns None and staging reports failure without pushing.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        setup_bus(base)
        remote = make_remote(base)
        co = make_checkout(base, remote)
        blocker = base / "blocker"
        blocker.write_text("a file, not a directory\n")
        orig = worker._pending_envelope_path
        worker._pending_envelope_path = \
            lambda job_id: blocker / f"{job_id}.json"
        try:
            env = {"heartbeat": {"run_id": SLOT, "status": "ok",
                                 "last_run_utc":
                                 "2026-11-22T10:47:05Z"},
                   "blobs": {"ledger/guard-heartbeat.json":
                             "a" * 40},
                   "commit": "b" * 40}
            check("093: failed durable write makes _persist "
                  "return None",
                  worker._persist_guard_envelope(
                      SLOT, BRANCH, env) is None)
            check("093: staging refuses the handoff when the "
                  "durable record cannot be established",
                  worker._stage_guard_heartbeat(
                      co, BRANCH, "failed", SLOT) is False)
            r = git("--git-dir", str(remote), "rev-parse",
                    "--verify", "-q", BRANCH, check_rc=False)
            check("093: no staging push happened after the "
                  "persistence failure", r.returncode != 0)
        finally:
            worker._pending_envelope_path = orig


def _seed_extra_ledger_file(base, remote, name="ledger/old.json",
                            doc=None):
    """Add an extra ledger file to main — the pre-envelope state
    a deletion envelope later removes."""
    seed = base / "seed-extra"
    git("clone", str(remote), str(seed))
    git("-C", str(seed), "config", "user.email",
        "test@borsagator.local")
    git("-C", str(seed), "config", "user.name", "gator-test")
    p = seed / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc or {"legacy": True}, indent=2)
                 + "\n")
    git("-C", str(seed), "add", name)
    git("-C", str(seed), "commit", "-m", "seed extra ledger file")
    git("-C", str(seed), "push", "origin", "HEAD:main")


def _stage_envelope(base, remote, ledger_doc, delete=()):
    """Stage an envelope on BRANCH from a scratch clone: fresh
    heartbeat + ledger.json, minus the `delete` paths. Returns
    (heartbeat doc, stage tip, staged ledger blob map)."""
    scratch = base / "stage2"
    git("clone", str(remote), str(scratch))
    git("-C", str(scratch), "config", "user.email",
        "test@borsagator.local")
    git("-C", str(scratch), "config", "user.name", "gator-test")
    hb = {"last_run_utc": "2026-11-22T10:47:05Z", "run_id": SLOT,
          "status": "ok", "workflow": "ledger-guard",
          "note": "deleting envelope"}
    (scratch / "ledger" / "guard-heartbeat.json").write_text(
        json.dumps(hb, indent=2) + "\n")
    (scratch / "ledger" / "ledger.json").write_text(
        json.dumps(ledger_doc, indent=2) + "\n")
    for rel in delete:
        git("-C", str(scratch), "rm", "-q", rel)
    git("-C", str(scratch), "add", "ledger/")
    git("-C", str(scratch), "commit", "-m", "stage envelope")
    git("-C", str(scratch), "push", "origin",
        f"HEAD:refs/heads/{BRANCH}")
    tip = git("--git-dir", str(remote), "rev-parse",
              BRANCH).stdout.strip()
    blobs = {}
    r = git("--git-dir", str(remote), "ls-tree", "-r", tip,
            "--", "ledger/")
    for line in r.stdout.splitlines():
        meta, _, path = line.partition("\t")
        parts = meta.split()
        if len(parts) == 3 and parts[1] == "blob" and path:
            blobs[path] = parts[2]
    return hb, tip, blobs


def _merge_clone(base, remote):
    land = base / "land2"
    git("clone", str(remote), str(land))
    git("-C", str(land), "config", "user.email",
        "test@borsagator.local")
    git("-C", str(land), "config", "user.name", "gator-test")
    git("-C", str(land), "fetch", "origin",
        f"+refs/heads/{BRANCH}:refs/remotes/origin/stage")
    return land


def test_history_retained_deletion_merge_refused():
    # INS-REVIEW-105 item 1: a real two-parent merge whose tree
    # RETAINS a file the envelope deleted. Every staged blob is
    # present at the merge, so presence-only equality passes —
    # but the relay refuses this landing, and worker
    # confirmation accepted it via the side-parent stage commit
    # (plain git log traverses side parents). Tip and history
    # must both refuse.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        remote = make_remote(base)
        co = make_checkout(base, remote)
        _seed_extra_ledger_file(base, remote)
        hb, tip, _ = _stage_envelope(
            base, remote, {"v": 1}, delete=("ledger/old.json",))
        expected = worker._staged_guard_envelope(co, BRANCH)
        check("105: staged envelope read back with its commit",
              expected is not None and expected["commit"] == tip)
        land = _merge_clone(base, remote)
        git("-C", str(land), "merge", "--no-commit", "--no-ff",
            "refs/remotes/origin/stage")
        # Retain the deleted file in the merge result.
        git("-C", str(land), "checkout", "HEAD", "--",
            "ledger/old.json")
        git("-C", str(land), "commit", "-m",
            "merge retaining the deletion")
        git("-C", str(land), "push", "origin", "HEAD:main")
        parents = git("--git-dir", str(remote), "rev-list",
                      "--parents", "-n", "1",
                      "main").stdout.split()
        check("105: fixture landing is a two-parent merge of "
              "the stage commit",
              len(parents) == 3 and parents[2] == tip)
        check("105: tip check refuses a landing that retains "
              "a deleted file",
              worker._guard_envelope_on_main(co, SLOT, expected)
              is None)
        check("105: history refuses the retained-deletion "
              "merge (no side-parent confirmation)",
              worker._guard_envelope_in_main_history(
                  co, SLOT, expected) is None)


def test_history_reachable_stage_without_landing_refused():
    # INS-REVIEW-105 item 1: the stage commit is the second
    # parent of a first-parent merge whose tree (merge -s ours)
    # never carried the envelope. Reachability — even as a
    # merge's second parent — is not a landing when the merge's
    # own tree does not carry the envelope.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        remote = make_remote(base)
        co = make_checkout(base, remote)
        hb, tip, _ = _stage_envelope(base, remote, {"v": 1})
        expected = worker._staged_guard_envelope(co, BRANCH)
        land = _merge_clone(base, remote)
        git("-C", str(land), "merge", "-s", "ours", "--no-ff",
            "refs/remotes/origin/stage", "-m", "merge (ours)")
        git("-C", str(land), "push", "origin", "HEAD:main")
        r = git("--git-dir", str(remote), "merge-base",
                "--is-ancestor", tip, "main", check_rc=False)
        check("105: fixture really has the stage reachable "
              "from main", r.returncode == 0)
        check("105: tip carries no envelope (fixture sanity)",
              worker._guard_envelope_on_main(co, SLOT, expected)
              is None)
        check("105: history refuses a merely reachable stage "
              "commit",
              worker._guard_envelope_in_main_history(
                  co, SLOT, expected) is None)


def test_history_real_merge_confirms_and_survives_supersede():
    # INS-REVIEW-105 item 1, positive control: a genuine merge
    # landing (two parents, second parent = the stage commit,
    # deletions absent, nothing introduced beyond the manifest)
    # confirms — and still confirms at M after a later envelope
    # supersedes it on the tip.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        remote = make_remote(base)
        co = make_checkout(base, remote)
        _seed_extra_ledger_file(base, remote)
        hb, tip, _ = _stage_envelope(
            base, remote, {"v": 1}, delete=("ledger/old.json",))
        expected = worker._staged_guard_envelope(co, BRANCH)
        land = _merge_clone(base, remote)
        git("-C", str(land), "merge", "--no-ff",
            "refs/remotes/origin/stage", "-m", "merge envelope")
        git("-C", str(land), "push", "origin", "HEAD:main")
        doc = worker._guard_envelope_on_main(co, SLOT, expected)
        check("105: a real merge landing confirms at the tip",
              doc is not None and doc == hb)
        (land / "ledger" / "ledger.json").write_text(
            json.dumps({"v": 2}, indent=2) + "\n")
        git("-C", str(land), "add", "ledger/")
        git("-C", str(land), "commit", "-m", "later envelope")
        git("-C", str(land), "push", "origin", "HEAD:main")
        check("105: superseded envelope leaves the tip check",
              worker._guard_envelope_on_main(co, SLOT, expected)
              is None)
        doc = worker._guard_envelope_in_main_history(
            co, SLOT, expected)
        check("105: confirmation stands at the verified merge "
              "after supersede", doc is not None and doc == hb)


def test_existing_branch_cross_attempt_adoption_refused():
    # INS-REVIEW-105 item 2: attempt A stages a branch and its
    # record; attempt B (a reclaim) must not adopt the branch,
    # rebind the record, or confirm on A's envelope.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        setup_bus(base)
        remote = make_remote(base)
        co = make_checkout(base, remote)
        claims = worker.BUS / "queue" / "claims"
        (claims / f"{SLOT}.json").write_text(json.dumps(
            {"worker": "worker-5", "at": "2026-11-22T10:00:00Z",
             "job": "ledger-guard"}))
        attempt_a = worker._guard_attempt_id(SLOT)
        attempt_b = "worker-5@2026-11-22T11:00:00Z"
        check("105: attempt A stages its envelope",
              worker._stage_guard_heartbeat(
                  co, BRANCH, "ok", SLOT, attempt_id=attempt_a)
              is True)
        tip = git("--git-dir", str(remote), "rev-parse",
                  BRANCH).stdout.strip()
        check("105: attempt B cannot adopt A's existing branch",
              worker._stage_guard_heartbeat(
                  co, BRANCH, "failed", SLOT,
                  attempt_id=attempt_b) is False)
        check("105: the branch is untouched by B's refusal",
              git("--git-dir", str(remote), "rev-parse",
                  BRANCH).stdout.strip() == tip
              and branch_heartbeat(remote, BRANCH).get("status")
              == "ok")
        record = worker._existing_envelope_record(SLOT)
        check("105: the record still belongs to attempt A",
              record is not None
              and record.get("attempt_id") == attempt_a)
        check("105: attempt B cannot confirm on A's envelope",
              worker._confirm_guard_envelope(
                  co, SLOT, BRANCH, timeout_s=1.5, poll_s=0.2,
                  attempt_id=attempt_b) is None)


def test_confirm_persist_failure_returns_none():
    # INS-REVIEW-105 item 4: _confirm_guard_envelope ignored a
    # None from _persist_guard_envelope and confirmed anyway.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        setup_bus(base)
        co = base / "checkout"
        co.mkdir()
        env = {"heartbeat": {"run_id": SLOT, "status": "ok"},
               "blobs": {}, "commit": "c" * 40}
        orig_staged = worker._staged_guard_envelope
        orig_persist = worker._persist_guard_envelope
        orig_on_main = worker._guard_envelope_on_main
        worker._staged_guard_envelope = lambda c, b: env
        worker._persist_guard_envelope = lambda *a, **k: None
        worker._guard_envelope_on_main = \
            lambda c, j, e: {"run_id": SLOT, "status": "ok"}
        try:
            doc = worker._confirm_guard_envelope(
                co, SLOT, BRANCH, timeout_s=5, poll_s=0.05)
        finally:
            worker._staged_guard_envelope = orig_staged
            worker._persist_guard_envelope = orig_persist
            worker._guard_envelope_on_main = orig_on_main
        check("105: confirmation fails closed when the durable "
              "record cannot be established", doc is None)


def test_publisher_death_record_recovery():
    # INS-REVIEW-105 item 4: the publisher writes its durable
    # record BEFORE its staging push, so when the publisher is
    # interrupted (killed) before the worker captures the staged
    # envelope — no worker-written record, no bus copy — the
    # publisher's own record still lets a restarted worker
    # confirm the landing. (The 093 test only checked the
    # record existed after a NORMAL publisher completion.)
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        setup_bus(base)
        remote = make_remote(base)
        co = make_checkout(base, remote)
        _seed_extra_ledger_file(base, remote)
        hb, tip, blobs = _stage_envelope(
            base, remote, {"v": 1}, delete=("ledger/old.json",))
        # The publisher's record, in exactly the shape
        # scripts/ledger_publish.py writes before its push.
        attempt = "worker-5@2026-11-22T10:00:00Z"
        record = {"job_id": SLOT, "branch": BRANCH,
                  "envelope_commit": tip, "heartbeat": hb,
                  "blobs": blobs, "attempt_id": attempt,
                  "persisted_at": "2026-11-22T10:47:01Z"}
        lp = worker._pending_envelope_path(SLOT)
        lp.parent.mkdir(parents=True, exist_ok=True)
        lp.write_text(json.dumps(record, indent=1))
        check("105: no bus copy of the publisher's record "
              "exists (the worker never captured it)",
              not worker._guard_envelope_record_path(
                  SLOT).exists())
        # The relay lands the envelope and deletes the branch.
        land = _merge_clone(base, remote)
        git("-C", str(land), "merge", "--no-ff",
            "refs/remotes/origin/stage", "-m", "merge envelope")
        git("-C", str(land), "push", "origin", "HEAD:main")
        git("--git-dir", str(remote), "update-ref", "-d",
            f"refs/heads/{BRANCH}")
        # A later envelope supersedes it on the tip, so only
        # the verified merge in history can confirm it.
        (land / "ledger" / "ledger.json").write_text(
            json.dumps({"v": 2}, indent=2) + "\n")
        git("-C", str(land), "add", "ledger/")
        git("-C", str(land), "commit", "-m", "later envelope")
        git("-C", str(land), "push", "origin", "HEAD:main")
        doc = worker._confirm_guard_envelope(
            co, SLOT, BRANCH, timeout_s=5, poll_s=0.2,
            attempt_id=attempt)
        check("105: confirmation recovers from the dead "
              "publisher's durable record alone",
              doc is not None and doc == hb)


def test_remote_record_mismatch_keeps_local_copy():
    # INS-REVIEW-105 item 3: origin/queue already carries
    # attempt A's record at this job's path. Attempt B persists
    # its own record; B's bus push never lands it (fake push),
    # and the existence-only read-back used to see A's record
    # and delete B's durable local copy. The local copy must
    # survive, and a later load for B must not be hidden by the
    # stale bus record.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        remote = base / "bus-remote.git"
        git("init", "--bare", "-b", "queue", str(remote))
        seed = base / "bus-seed"
        git("clone", str(remote), str(seed))
        git("-C", str(seed), "config", "user.email",
            "test@borsagator.local")
        git("-C", str(seed), "config", "user.name", "gator-test")
        rec_a = {"job_id": SLOT, "branch": BRANCH,
                 "envelope_commit": "a" * 40,
                 "heartbeat": {"run_id": SLOT, "status": "ok"},
                 "blobs": {"ledger/guard-heartbeat.json":
                           "a" * 40},
                 "attempt_id": "worker-5@2026-11-22T10:00:00Z",
                 "persisted_at": "2026-11-22T10:00:01Z"}
        p = seed / "queue" / "envelopes" / f"{SLOT}.json"
        p.parent.mkdir(parents=True)
        p.write_text(json.dumps(rec_a, indent=1))
        (seed / "queue" / "claims").mkdir(exist_ok=True)
        (seed / "queue" / "done").mkdir(exist_ok=True)
        (seed / "queue" / "queue.json").write_text("[]")
        git("-C", str(seed), "add", "queue/")
        git("-C", str(seed), "commit", "-m", "seed bus")
        git("-C", str(seed), "push", "origin", "HEAD:queue")
        bus = base / "busclone"
        git("clone", "-b", "queue", "--single-branch",
            str(remote), str(bus))
        worker.BUS = bus
        worker.OUT = base / "out"
        worker.push_bus = fake_push_bus
        PUSHED.clear()
        local = worker._pending_envelope_path(SLOT)
        local.unlink(missing_ok=True)
        env_b = {"heartbeat": {"run_id": SLOT, "status": "ok",
                               "last_run_utc":
                               "2026-11-22T11:47:05Z"},
                 "blobs": {"ledger/guard-heartbeat.json":
                           "b" * 40},
                 "commit": "b" * 40}
        rec = worker._persist_guard_envelope(
            SLOT, BRANCH, env_b,
            attempt_id="worker-5@2026-11-22T11:00:00Z")
        check("105: persist returns B's record", rec is not None)
        check("105: B's durable local copy survives the remote "
              "holding A's record", local.exists()
              and json.loads(local.read_text()).get("attempt_id")
              == "worker-5@2026-11-22T11:00:00Z")
        remote_rec = worker._remote_envelope_record(SLOT)
        check("105: the remote still carries A's record",
              remote_rec is not None
              and remote_rec.get("attempt_id")
              == "worker-5@2026-11-22T10:00:00Z")
        # Simulate sync_bus resetting the bus clone to the
        # committed (stale A) state.
        git("-C", str(bus), "reset", "--hard", "origin/queue")
        got_b = worker._load_persisted_guard_envelope(
            SLOT, attempt_id="worker-5@2026-11-22T11:00:00Z")
        check("105: stale bus record does not hide B's local "
              "record", got_b is not None
              and got_b.get("envelope_commit") == "b" * 40)
        git("-C", str(bus), "reset", "--hard", "origin/queue")
        got_a = worker._load_persisted_guard_envelope(
            SLOT, attempt_id="worker-5@2026-11-22T10:00:00Z")
        check("105: attempt A still loads its own record",
              got_a is not None
              and got_a.get("envelope_commit") == "a" * 40)


def main():
    test_branch_names()
    test_persist_failure_blocks_handoff()
    test_guard_envelope_attempt_binding()
    test_guard_envelope_local_copy_survives_rejected_push()
    test_guard_confirm_deadline_honoured_before_accepting()
    test_branch_state_tristate()
    test_stage_heartbeat_lands_branch()
    test_stage_heartbeat_never_overwrites_existing_branch()
    test_stage_heartbeat_broken_remote_returns_false()
    test_guard_envelope_full_content_equality()
    test_guard_envelope_persisted_survives_branch_deletion()
    test_guard_success_envelope_confirmed_is_done()
    test_guard_publisher_failure_stages_failed_envelope()
    test_guard_publisher_timeout_is_killed_and_recorded()
    test_guard_unconfirmed_envelope_refuses_done()
    test_guard_stale_same_id_heartbeat_does_not_confirm()
    test_guard_d2_refusal_records_and_stages_failed_heartbeat()
    test_history_real_merge_confirms_and_survives_supersede()
    test_history_retained_deletion_merge_refused()
    test_history_reachable_stage_without_landing_refused()
    test_existing_branch_cross_attempt_adoption_refused()
    test_confirm_persist_failure_returns_none()
    test_publisher_death_record_recovery()
    test_remote_record_mismatch_keeps_local_copy()
    print(f"\n{PASSED} checks passed")


if __name__ == "__main__":
    main()
