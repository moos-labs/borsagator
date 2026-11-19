#!/usr/bin/env python3
"""Regression test for issue #149 (panel round 12, F5): successful
jobs had no durable completion state before six-hour claim
reclamation. Claims were the only done-state; reclaim_stale_claims
deleted any claim older than 6 h, while queue.json is append-only,
so a completed job became runnable again >6 h after its last
refresh.

The fix: _execute writes a done record (queue/done/<id>.json,
carrying the archive commit) only after a successful publish;
reclaim_stale_claims reclaims only unfinished attempts; the main
loop and claim() skip done jobs.

Issue #216 changed HOW the done record reaches the bus: _mark_done
no longer writes into BUS/queue/done/ via push_bus (single-shot,
lost in a queue-push race, swallowed by the next sync_bus reset).
It stages a crash-durable receipt in ROOT/pending-done and publishes
it through a DEDICATED clone (BUS_PUB) against a fresh queue base
with bounded retries, verified on origin/queue. So this test sets
up a real local bare bus repo (GATOR_BUS_URL), makes BUS a real
clone of it, and asserts the marker lands on origin/queue — the
stubbed push_bus no longer carries done markers.

Run: python3 worker/test_worker_149.py   (stdlib only, no network)
Fails on unmodified main: done/_mark_done do not exist, and the
completed-job checks fail (a done job is re-runnable after reclaim).
"""
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from contextlib import redirect_stderr
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TMP = Path(tempfile.mkdtemp(prefix="test149-"))
os.environ["GATOR_ROOT"] = str(TMP / "gator")

spec = importlib.util.spec_from_file_location(
    "worker149", REPO / "worker" / "worker.py")
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)
worker.CODE = REPO

# --- Issue #216: the bus is a real local git remote ------------------
# _publish_done clones BUS_PUB from GATOR_BUS_URL, so the bus needs a
# real bare repo; BUS itself is a real clone so sync_bus() can pull a
# published marker into the worktree. push_bus stays stubbed (claim /
# reclaim / publish-failure paths still use it; done markers do not).
BUS_BARE = TMP / "bus.git"
subprocess.run(["git", "init", "-q", "--bare", str(BUS_BARE)], check=True)
_seed = TMP / "seed-bus-queue"
subprocess.run(["git", "clone", "-q", str(BUS_BARE), str(_seed)],
               check=True)
subprocess.run(["git", "-C", str(_seed), "checkout", "-q", "-b", "queue"],
               check=True)
(_seed / "queue").mkdir(parents=True, exist_ok=True)
(_seed / "queue" / "queue.json").write_text("[]")
for _args in (["add", "-A"], ["commit", "-qm", "seed"]):
    subprocess.run(["git", "-C", str(_seed),
                    "-c", "user.email=test@borsagator.local",
                    "-c", "user.name=test"] + _args, check=True)
subprocess.run(["git", "-C", str(_seed), "push", "-q", "origin", "queue"],
               check=True)
BUS_URL = str(BUS_BARE)
os.environ["GATOR_BUS_URL"] = BUS_URL
worker.sync_bus()


def origin_done(job_id):
    """The done record as it stands on origin/queue (None if absent)."""
    r = subprocess.run(["git", "--git-dir", str(BUS_BARE), "show",
                        f"queue:queue/done/{job_id}.json"],
                       capture_output=True, text=True)
    return json.loads(r.stdout) if r.returncode == 0 else None

CSV = ("Date,Open,High,Low,Close,Volume\n"
       "2026-11-09,9.80,9.90,9.70,9.85,1000\n"
       "2026-11-10,9.85,10.00,9.80,9.95,1100\n"
       "2026-11-11,9.95,10.10,9.90,10.05,1200\n"
       "2026-11-12,10.05,10.20,10.00,10.15,1300\n"
       "2026-11-13,10.15,10.30,10.10,10.25,1400\n"
       "2026-11-14,10.25,10.40,10.20,10.35,1500\n")

PUSHED = []
FAIL_NEXT_PUSH = []


def fake_push_bus(message):
    PUSHED.append(message)
    if FAIL_NEXT_PUSH:
        FAIL_NEXT_PUSH.pop()
        return False
    return True


worker.push_bus = fake_push_bus

CHECKS = []


def check(name, ok, detail=""):
    CHECKS.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}: {name}"
          + (f" — {detail}" if detail and not ok else ""))
    return ok


def claims_dir():
    d = worker.BUS / "queue" / "claims"
    d.mkdir(parents=True, exist_ok=True)
    return d


def done_dir():
    d = worker.BUS / "queue" / "done"
    d.mkdir(parents=True, exist_ok=True)
    return d


def stamp_claim(job_id, job_text, hours_ago):
    at = (datetime.now(timezone.utc)
          - timedelta(hours=hours_ago)).isoformat()
    (claims_dir() / f"{job_id}.json").write_text(json.dumps(
        {"worker": "borsagator-worker-5", "at": at, "job": job_text}))


def stamp_done(job_id, job_text, archive="abc123"):
    (done_dir() / f"{job_id}.json").write_text(json.dumps(
        {"worker": "borsagator-worker-5", "at": worker.now(),
         "job": job_text, "archive": archive}))


def main_loop_runnable(job):
    """The main loop's exact per-job decision (worker.py main()):
    a job with ANY local completion evidence - done record, pending
    or corrupt receipt - is skipped; an unclaimed, unfinished job
    is claimed and executed. Mirrors worker.py:1934-1943."""
    if worker._done_or_pending(job["id"]):
        return False
    if not worker.claimed(job["id"]):
        return True
    return False


# --- Issue #236: publication-clone URL selection is observable ------
# Isolate BOTH paths: do not remove/reconfigure the suite's real BUS
# or BUS_PUB. This also keeps the #235 drain tests independent.
def test_pub_clone_sources():
    saved_bus, saved_pub = worker.BUS, worker.BUS_PUB
    saved_url = os.environ.get("GATOR_BUS_URL")
    warning = ("_ensure_pub_clone: WARNING: GATOR_BUS_URL unset or empty; "
               "using BUS origin remote for publication clone\n")
    missing = ("_ensure_pub_clone: no bus URL (GATOR_BUS_URL unset "
               "and BUS has no origin remote)\n")

    def attempt():
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            result = worker._ensure_pub_clone()
        return result, stderr.getvalue()

    def pub_origin():
        r = subprocess.run(
            ["git", "-C", str(worker.BUS_PUB), "remote", "get-url", "origin"],
            capture_output=True, text=True)
        return r.stdout.strip() if r.returncode == 0 else None

    try:
        worker.BUS = TMP / "bus-236"
        subprocess.run(["git", "init", "-q", str(worker.BUS)], check=True)
        wrong_origin = str(TMP / "must-not-be-used.git")
        subprocess.run(["git", "-C", str(worker.BUS), "remote", "add",
                        "origin", wrong_origin], check=True)
        worker.BUS_PUB = TMP / "pub-236-explicit"
        os.environ["GATOR_BUS_URL"] = BUS_URL
        result, stderr = attempt()
        check("URL explicit: clone succeeds despite differing BUS origin",
              result is True)
        check("URL explicit: clone origin is env URL, not BUS origin",
              pub_origin() == BUS_URL and BUS_URL != wrong_origin)
        check("URL explicit: no fallback warning", stderr == "", repr(stderr))

        subprocess.run(["git", "-C", str(worker.BUS), "remote", "set-url",
                        "origin", BUS_URL], check=True)
        for mode in ("unset", "empty"):
            worker.BUS_PUB = TMP / f"pub-236-{mode}"
            os.environ.pop("GATOR_BUS_URL", None)
            if mode == "empty":
                os.environ["GATOR_BUS_URL"] = ""
            result, stderr = attempt()
            check(f"URL {mode}: fallback clone succeeds", result is True)
            check(f"URL {mode}: clone origin is BUS origin",
                  pub_origin() == BUS_URL)
            check(f"URL {mode}: exact URL-free warning on stderr",
                  stderr == warning, repr(stderr))
            result, stderr = attempt()
            check(f"URL {mode}: existing clone reused without warning",
                  result is True and stderr == "", repr(stderr))

        worker.BUS_PUB = TMP / "pub-236-missing"
        os.environ.pop("GATOR_BUS_URL", None)
        subprocess.run(["git", "-C", str(worker.BUS), "remote", "remove",
                        "origin"], check=True)
        result, stderr = attempt()
        check("URL missing: initialization returns False", result is False)
        check("URL missing: exact existing diagnostic, no fallback warning",
              stderr == missing, repr(stderr))
        check("URL missing: no publication clone or staging clone created",
              not worker.BUS_PUB.exists()
              and not worker.BUS_PUB.with_name(
                  worker.BUS_PUB.name + ".tmp-clone").exists())
    finally:
        worker.BUS, worker.BUS_PUB = saved_bus, saved_pub
        if saved_url is None:
            os.environ.pop("GATOR_BUS_URL", None)
        else:
            os.environ["GATOR_BUS_URL"] = saved_url


test_pub_clone_sources()


# --- 1-3. A completed job (done record + 7 h-old claim) -------------
job_done = {"id": "w3-selftest-001", "job": "run yahooquery POUL.CA"}
stamp_claim(job_done["id"], job_done["job"], 7)
stamp_done(job_done["id"], job_done["job"], archive="deadbeef")
worker.reclaim_stale_claims()
check("completed job: stale claim cleaned up by reclaim",
      not worker.claimed(job_done["id"]))
check("completed job: done record survives reclaim",
      worker.done(job_done["id"]))
check("completed job: main loop does NOT re-run it after reclaim",
      not main_loop_runnable(job_done))
check("completed job: claim() refuses it",
      worker.claim(job_done) is False
      and not worker.claimed(job_done["id"]))

# --- 4-5. An abandoned job (7 h-old claim, NO done record) ----------
job_abandoned = {"id": "w5-r3-news-001",
                 "job": "run news-disclosure POUL.CA"}
stamp_claim(job_abandoned["id"], job_abandoned["job"], 7)
worker.reclaim_stale_claims()
check("abandoned job: stale claim is reclaimed",
      not worker.claimed(job_abandoned["id"]))
check("abandoned job: main loop DOES pick it up again",
      main_loop_runnable(job_abandoned)
      and not worker.done(job_abandoned["id"]))

# --- 6-7. Reclaim leaves fresh and unparseable claims alone ---------
job_fresh = {"id": "w5-canary-yq-004", "job": "run yahooquery POUL.CA"}
stamp_claim(job_fresh["id"], job_fresh["job"], 0.5)
(claims_dir() / "broken.json").write_text("{not json")
worker.reclaim_stale_claims()
check("fresh claim (<6 h) untouched by reclaim",
      worker.claimed(job_fresh["id"]))
check("unparseable claim left alone (a human looks)",
      (claims_dir() / "broken.json").exists())

# --- 8-10. The real _execute path writes done only on success -------
SHA = "deadbeef" * 5  # 40-hex fake archive commit


def fake_run_tool(tool, ticker, template, ref, repo):
    results = worker.RUNNERS / tool / "results"
    results.mkdir(parents=True, exist_ok=True)
    (results / "POUL.CA.csv").write_text(CSV)
    (results / "run.log").write_text(f"{tool} stub ok\n")
    return "ok", f"{tool} stub log\n"


def fake_publish_ok(job, workdir, manifest):
    return SHA


def fake_publish_fail(job, workdir, manifest):
    return False


worker.run_tool = fake_run_tool
REAL_PUBLISH = worker.publish

job_sweep = {"id": "test-149-sweep", "job": "sweep-lite POUL.CA market=EGX"}
worker.publish = fake_publish_ok
worker._execute(job_sweep)
# Issue #216: _mark_done no longer writes into BUS/queue/done/ via the
# stubbed push_bus — it stages a receipt in the outbox and publishes it
# through the dedicated BUS_PUB clone, so the marker lands on
# origin/queue and the outbox drains.
data = origin_done(job_sweep["id"])
check("sweep-lite publish success: done record on origin/queue",
      data is not None)
if data is not None:
    check("sweep-lite done record carries the archive commit + job",
          data.get("archive") == SHA and data.get("job") == job_sweep["job"]
          and data.get("at"),
          f"record={data}")
check("sweep-lite publish success: outbox drained",
      not list(worker.PENDING_DONE.glob("*.json")))
check("sweep-lite publish success: done marker does NOT go through push_bus",
      f"done {job_sweep['id']}" not in PUSHED)
# The worker sees the job as done only after a sync pulls the marker
# into BUS. sync_bus() resets the worktree, which drops the stamped
# claims/done files from sections 1-7 — re-stamp the one section 13
# still needs (its claims are re-stamped there).
worker.sync_bus()
check("sweep-lite publish success: done() True after sync_bus",
      worker.done(job_sweep["id"]))
stamp_done(job_done["id"], job_done["job"], archive="deadbeef")


def fake_run_harvest(job, workdir):
    return {"egx-harvest": "ok"}


worker.run_harvest = fake_run_harvest
job_harvest = {"id": "test-149-harvest", "job": "harvest-egx POUL"}
worker._execute(job_harvest)
data_h = origin_done(job_harvest["id"])
check("harvest publish success: done record on origin with archive sha",
      data_h is not None and data_h.get("archive") == SHA)

job_fail = {"id": "test-149-fail", "job": "run yahooquery POUL.CA"}
worker.publish = fake_publish_fail
PUSHED.clear()
worker._execute(job_fail)
check("failed publish: NO done record written",
      not (done_dir() / f"{job_fail['id']}.json").exists()
      and f"done {job_fail['id']}" not in PUSHED)
check("failed publish: error file written, no done record",
      (claims_dir() / f"{job_fail['id']}.error.json").is_file()
      and not worker.done(job_fail["id"]))

# --- 11. A failed done-publication is loud, returns False, and the ---
# receipt is retained + gates local re-execution (#216) ------------
# Break publication deterministically: point the bus URL at a path that
# does not exist and drop the publication clone, so _ensure_pub_clone
# cannot establish BUS_PUB. (FAIL_NEXT_PUSH no longer reaches
# _mark_done — done markers do not go through push_bus anymore.
# The 5 bounded retries take ~30 s of backoff; that is the cost of
# the retry budget, not a hang.)
os.environ["GATOR_BUS_URL"] = str(TMP / "no-such-bus.git")
shutil.rmtree(worker.BUS_PUB, ignore_errors=True)
check("_mark_done returns False when publication fails",
      worker._mark_done({"id": "test-149-pushfail",
                         "job": "run yahooquery POUL.CA"}, SHA) is False)
check("failed _mark_done retains the receipt in the outbox",
      (worker.PENDING_DONE / "test-149-pushfail.json").is_file())
check("failed _mark_done gates local re-execution",
      worker._done_or_pending("test-149-pushfail"))
check("pending receipt: main-loop replica does NOT re-run it",
      not main_loop_runnable({"id": "test-149-pushfail",
                              "job": "run yahooquery POUL.CA"}))
os.environ["GATOR_BUS_URL"] = BUS_URL

# --- 12. The real publish() returns the archive commit SHA ---------
seed = TMP / "seed-bus"
subprocess.run(["git", "init", "-q", "-b", "main", str(seed)],
               check=True)
subprocess.run(["git", "-C", str(seed), "config", "user.email",
                "test@borsagator.local"], check=True)
subprocess.run(["git", "-C", str(seed), "config", "user.name",
                "test"], check=True)
(seed / "README").write_text("seed\n")
subprocess.run(["git", "-C", str(seed), "add", "-A"], check=True)
subprocess.run(["git", "-C", str(seed), "commit", "-qm", "seed"],
               check=True)
subprocess.run(["git", "-C", str(seed), "branch", "archive"], check=True)
os.environ["GATOR_BUS_URL"] = str(seed)
worker.publish = REAL_PUBLISH
workdir = TMP / "pub-work"
workdir.mkdir(parents=True, exist_ok=True)
(workdir / "result.txt").write_text("ok\n")
job_pub = {"id": "test-149-pub", "job": "run yahooquery POUL.CA"}
sha = worker.publish(job_pub, workdir, {"job": job_pub, "tools": {}})
tip = subprocess.run(
    ["git", "-C", str(seed), "rev-parse", "archive"],
    capture_output=True, text=True, check=True).stdout.strip()
check("real publish() returns the archive commit SHA",
      isinstance(sha, str) and re.fullmatch(r"[0-9a-f]{40}", sha or "")
      and sha == tip,
      f"publish returned {sha!r}, archive tip {tip[:12]}")
os.environ["GATOR_BUS_URL"] = BUS_URL  # section 12 borrowed the var

# --- 13. Full cycle: done job skipped, abandoned job picked up ------
q = [{"id": job_done["id"], "job": job_done["job"]},
     {"id": job_abandoned["id"], "job": job_abandoned["job"]}]
(worker.BUS / "queue" / "queue.json").write_text(json.dumps(q, indent=1))
stamp_claim(job_done["id"], job_done["job"], 7)
stamp_claim(job_abandoned["id"], job_abandoned["job"], 7)
worker.reclaim_stale_claims()
runnable = [j["id"] for j in worker.read_queue()
            if main_loop_runnable(j)]
check("full cycle: only the abandoned job is runnable after reclaim",
      runnable == [job_abandoned["id"]],
      f"runnable={runnable}")

# --- 14. The REAL main() loop gates on _done_or_pending ----------
# Sections 1-13 exercise a local REPLICA of the loop decision; a
# future edit removing the _done_or_pending gate from main() would
# leave them green. Here we drive ONE ACTUAL CYCLE of worker.main():
# cycle helpers are stubbed to no-ops, read_queue() is real, and
# time.sleep raises a sentinel to stop after one pass (sleep sits
# outside the loop's try/except, so the sentinel escapes main()).
# Deterministic regression: a job with ONLY a pending receipt (no
# done record, no claim) is queued ahead of a clean job. The old
# replica and an ungated main() both call it runnable; the gate
# must skip it and run the clean job instead.
class _CycleDone(Exception):
    pass


def _stop_after_one_cycle(_seconds):
    raise _CycleDone()


job_pending = {"id": "test-149-loop-pending",
               "job": "run yahooquery POUL.CA"}
job_clean = {"id": "test-149-loop-clean",
             "job": "run yahooquery POUL.CA"}
(worker.PENDING_DONE / f"{job_pending['id']}.json").write_text(
    json.dumps({"id": job_pending["id"], "job": job_pending["job"],
                "archive": SHA, "at": worker.now()}))
(worker.BUS / "queue" / "queue.json").write_text(
    json.dumps([job_pending, job_clean], indent=1))
LOOP_CALLS = {"claim": [], "execute": []}


def loop_claim(job):
    LOOP_CALLS["claim"].append(job["id"])
    return True


def loop_execute(job):
    LOOP_CALLS["execute"].append(job["id"])


_SAVED = {n: getattr(worker, n) for n in (
    "self_update", "sync_bus", "flush_pending_done",
    "run_schedule_check", "reclaim_stale_claims", "prune_out",
    "heartbeat", "claim", "execute")}
_REAL_SLEEP = worker.time.sleep
for _n in ("self_update", "sync_bus", "flush_pending_done",
           "run_schedule_check", "reclaim_stale_claims",
           "prune_out", "heartbeat"):
    setattr(worker, _n, lambda *a, **k: None)
worker.claim = loop_claim
worker.execute = loop_execute
worker.time.sleep = _stop_after_one_cycle
try:
    worker.main()
except _CycleDone:
    pass
finally:
    worker.time.sleep = _REAL_SLEEP
    for _n, _f in _SAVED.items():
        setattr(worker, _n, _f)

check("real main(): pending-receipt job neither claimed nor run",
      job_pending["id"] not in LOOP_CALLS["claim"]
      and job_pending["id"] not in LOOP_CALLS["execute"])
check("real main(): the clean job behind it runs",
      LOOP_CALLS["execute"] == [job_clean["id"]],
      f"executed={LOOP_CALLS['execute']}")
(worker.PENDING_DONE / f"{job_pending['id']}.json").unlink()


# --- 15. The drain delivers a staged receipt; the outbox empties ---
# Section 11 proved a failed _mark_done RETAINS its receipt; the
# recovery half - a later per-cycle flush_pending_done delivering
# it - was never asserted (flush_pending_done had 0 hits in the
# suite). Stage a fresh receipt (the crash-recovery shape: a file
# in the outbox, no in-memory state), run ONE real drain, and
# verify the marker lands on origin/queue and the outbox empties.
# The receipt section 11 retained must drain in the same pass.
receipt_drain = worker.PENDING_DONE / "test-149-drain.json"
receipt_drain.write_text(json.dumps(
    {"worker": "borsagator-worker-5", "at": worker.now(),
     "job": "run yahooquery <http://POUL.CA|POUL.CA", "archive": SHA,
     "id": "test-149-drain"}))
worker.flush_pending_done()
data_drain = origin_done("test-149-drain")
check("drain: staged receipt published to origin/queue",
      data_drain is not None and data_drain.get("archive") == SHA,
      f"record={data_drain}")
check("drain: the receipt section 11 retained drains too",
      origin_done("test-149-pushfail") is not None)
check("drain: outbox empty after verified delivery",
      not list(worker.PENDING_DONE.glob("*.json")))
worker.sync_bus()
check("drain: done() True once sync_bus pulls the marker",
      worker.done("test-149-drain"))

# --- 16. A competing bus record is never overwritten by the drain -
# When origin/queue already carries a DIFFERENT done record for the
# job (a manual reconcile or another writer), the drain must keep
# the local receipt pending and leave the remote bytes untouched -
# never force-push over them. Plant the competing record directly
# on origin/queue, stage a conflicting receipt, run ONE drain.
job_conflict = {"id": "test-149-conflict",
                "job": "run yahooquery <http://POUL.CA|POUL.CA"}
competing = {"worker": "borsagator-worker-6", "at": worker.now(),
             "job": job_conflict["job"], "archive": "0" * 40}
subprocess.run(["git", "-C", str(_seed), "fetch", "-q", "origin"],
               check=True)
subprocess.run(["git", "-C", str(_seed), "reset", "-q", "--hard",
                "origin/queue"], check=True)
(_seed / "queue" / "done").mkdir(parents=True, exist_ok=True)
(_seed / "queue" / "done"
 / f"{job_conflict['id']}.json").write_text(json.dumps(competing))
subprocess.run(["git", "-C", str(_seed), "add", "-A"], check=True)
subprocess.run(["git", "-C", str(_seed),
                "-c", "user.email=test@borsagator.local",
                "-c", "user.name=test",
                "commit", "-qm", "competing done"], check=True)
subprocess.run(["git", "-C", str(_seed), "push", "-q", "origin",
                "queue"], check=True)
receipt_conflict = (worker.PENDING_DONE
                    / f"{job_conflict['id']}.json")
receipt_conflict.write_text(json.dumps(
    {"worker": "borsagator-worker-5", "at": worker.now(),
     "job": job_conflict["job"], "archive": SHA,
     "id": job_conflict["id"]}))
worker.flush_pending_done()
check("conflict: competing bus record NOT overwritten",
      origin_done(job_conflict["id"]) == competing,
      f"record={origin_done(job_conflict['id'])}")
check("conflict: differing receipt retained pending",
      receipt_conflict.is_file())
check("conflict: retained receipt still gates re-execution",
      worker._done_or_pending(job_conflict["id"]))
receipt_conflict.unlink()

# --- 17. A corrupt receipt is quarantined, never published, still --
# gating, and surfaced in the heartbeat --------------------------
# A receipt failing validation (here it PARSES, but archive is not
# a string - a parse-only validator would wave it through) is
# quarantined to *.corrupt: never published, never dropped, still
# blocking local re-execution, and visible in corrupt_done.
job_corrupt = {"id": "test-149-corrupt",
               "job": "run yahooquery <http://POUL.CA|POUL.CA"}
receipt_corrupt = worker.PENDING_DONE / f"{job_corrupt['id']}.json"
receipt_corrupt.write_text(json.dumps(
    {"worker": "borsagator-worker-5", "at": worker.now(),
     "job": job_corrupt["job"], "archive": 123}))
worker.flush_pending_done()
check("corrupt receipt quarantined to *.corrupt",
      (worker.PENDING_DONE / f"{job_corrupt['id']}.json.corrupt")
      .is_file() and not receipt_corrupt.exists())
check("corrupt receipt NOT published to origin/queue",
      origin_done(job_corrupt["id"]) is None)
check("corrupt receipt still gates local re-execution",
      worker._done_or_pending(job_corrupt["id"])
      and not main_loop_runnable(job_corrupt))
worker.heartbeat()
payload = json.loads(
    (worker.BUS / "queue" / "heartbeat.json").read_text())
check("quarantine surfaced in heartbeat corrupt_done",
      job_corrupt["id"] in payload.get("corrupt_done", []),
      f"corrupt_done={payload.get('corrupt_done')}")
(worker.PENDING_DONE / f"{job_corrupt['id']}.json.corrupt").unlink()

# --- 18. _mark_done stages BEFORE publication; a failed publication -
# leaves the receipt content-intact ------------------------------
# Section 11 ended at the post-failure STATE (returns False, a
# receipt file exists, the gate is set) with publication impossible
# from the start (a bus URL that does not exist, BUS_PUB deleted -
# _publish_done never ran an attempt against a live remote). Still unasserted:
# ORDERING (the crash-durable receipt must exist BEFORE
# _publish_done runs, or a crash mid-publication loses the
# completion) and CONTENT (failed attempts must not mangle the
# staged record). Intercept _publish_done: observe the receipt at
# attempt time, then fail.
job_order = {"id": "test-149-order",
             "job": "run yahooquery <http://POUL.CA|POUL.CA"}
receipt_order = worker.PENDING_DONE / f"{job_order['id']}.json"
OBSERVED = {}
REAL_PUBLISH_DONE = worker._publish_done


def observing_publish_done(job_id, record, attempts=5):
    OBSERVED["staged"] = receipt_order.is_file()
    OBSERVED["bytes"] = (receipt_order.read_text()
                         if OBSERVED["staged"] else None)
    return False


worker._publish_done = observing_publish_done
try:
    rc = worker._mark_done(job_order, SHA)
finally:
    worker._publish_done = REAL_PUBLISH_DONE
check("ordering: _mark_done False when publication fails",
      rc is False)
check("ordering: receipt staged BEFORE publication runs",
      OBSERVED.get("staged") is True)
order_record = json.loads(receipt_order.read_text())
check("ordering: failed publication retains the receipt intact",
      OBSERVED.get("bytes") == receipt_order.read_text()
      and order_record.get("job") == job_order["job"]
      and order_record.get("archive") == SHA,
      f"record={order_record}")
receipt_order.unlink()

# --- 19. #231: actual fresh-interpreter restart, no network ---------
# The child runs one REAL main cycle with a real local git bus/drain.
# Only update/scheduling/housekeeping and claim transport are stubbed.
# A ledger-body spy appends to a file, so a duplicate survives restart
# and cannot hide behind the new process's empty Python globals.
RESTART_CODE = r'''
import importlib.util, json, os, sys
from pathlib import Path
repo, job_file, effects_file, report_file = map(Path, sys.argv[1:])
spec = importlib.util.spec_from_file_location("restart231", repo / "worker/worker.py")
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)
job = json.loads(job_file.read_text())
claims = []
def effect(job):
    with effects_file.open("a") as f:
        f.write(job["id"] + "\n")
    return True
w.run_ledger_guard = effect
w.run_ledger_watchdog = effect
w.self_update = w.run_schedule_check = w.reclaim_stale_claims = w.prune_out = lambda: None
w.read_queue = lambda: [job]
w.claim = lambda j: claims.append(j["id"]) or True
w.push_bus = lambda *a: True
class StopCycle(Exception): pass
# Do not replace time.sleep on the shared stdlib module: subprocess
# timeout waits can call it too. Replace ONLY worker's clock reference.
real_time = w.time
class CycleClock:
    def __getattr__(self, name):
        return getattr(real_time, name)
    def sleep(self, seconds):
        if seconds == w.POLL_SECONDS:
            raise StopCycle()
        # No real backoff waits in this offline harness.
w.time = CycleClock()
try:
    w.main()
except StopCycle:
    pass
Path(report_file).write_text(json.dumps({
    "claims": claims, "gated": w._done_or_pending(job["id"]),
    "intent": w._intent_path(job["id"]).exists(),
    "receipts": [str(p) for p in w._receipt_paths(job["id"])],
    "undelivered": sorted(w._UNDELIVERED),
    "verified": sorted(w._VERIFIED_DONE),
    "heartbeat": json.loads((w.BUS / "queue/heartbeat.json").read_text())}))
'''


def bus_tip():
    return subprocess.run(
        ["git", "--git-dir", str(BUS_BARE), "rev-parse", "queue"],
        capture_output=True, text=True, check=True).stdout.strip()


def origin_bytes(job_id):
    r = subprocess.run(
        ["git", "--git-dir", str(BUS_BARE), "show",
         f"queue:queue/done/{job_id}.json"], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def restart231(job, effects):
    job_file = TMP / "restart231-job.json"
    report = TMP / "restart231-report.json"
    job_file.write_text(json.dumps(job))
    report.unlink(missing_ok=True)
    r = subprocess.run(
        [sys.executable, "-c", RESTART_CODE, str(REPO), str(job_file),
         str(effects), str(report)], env=os.environ.copy(),
        capture_output=True, text=True, timeout=30)
    if r.returncode != 0 or not report.exists():
        raise RuntimeError(f"restart failed rc={r.returncode}: {r.stderr}")
    result = json.loads(report.read_text())
    result["stderr"] = r.stderr
    (TMP / f"restart231-{job['id']}.json").write_text(json.dumps(result))
    return result


def test_restart231(name, fault, kind="ledger-guard"):
    job = {"id": f"test-231-{name}", "job": kind}
    effects = TMP / f"effects-{name}"
    primary = worker.PENDING_DONE / f"{job['id']}.json"
    fallback = worker.JOB_STATE / primary.name
    real_write, real_pub = worker._write_receipt, worker._publish_done
    real_guard, real_watch = worker.run_ledger_guard, worker.run_ledger_watchdog
    observed = []

    def effect(j):
        observed.append(("effect", worker._intent_path(j["id"]).is_file()))
        with effects.open("a") as f:
            f.write(j["id"] + "\n")
        return True

    def write(path, text):
        if fault in ("primary", "partial", "both") and path == primary:
            if fault == "partial":
                real_write(path, text)  # rename occurred; durability reply lost
            raise OSError("injected primary write failure")
        if fault == "both" and path == fallback:
            raise OSError("injected recovery write failure")
        real_write(path, text)

    def publication(job_id, record, attempts=5):
        observed.append(("delivery", record,
                         primary.read_text() if primary.exists() else None,
                         fallback.read_text() if fallback.exists() else None))
        if fault == "lost-reply":
            assert real_pub(job_id, record, attempts=attempts)
            return False
        if fault == "happy":
            return real_pub(job_id, record, attempts=attempts)
        return False

    worker._write_receipt, worker._publish_done = write, publication
    worker.run_ledger_guard = worker.run_ledger_watchdog = effect
    try:
        worker._execute(job)  # real intent -> real body -> real _mark_done
    finally:
        worker._write_receipt, worker._publish_done = real_write, real_pub
        worker.run_ledger_guard, worker.run_ledger_watchdog = real_guard, real_watch
    check(f"{name}: durable intent exists at effect admission",
          observed[0] == ("effect", True))
    delivery = observed[1]
    record = delivery[1]
    if fault != "both":
        check(f"{name}: exact completion staged BEFORE delivery",
              record in delivery[2:])
    else:
        check(f"{name}: both completion writes failed, intent retained",
              delivery[2:] == (None, None)
              and worker._intent_path(job["id"]).is_file())
    if fault in ("primary", "partial"):
        check(f"{name}: fallback is replayable exact completion bytes",
              fallback.is_file() and fallback.read_text() == record
              and worker._valid_receipt(record, job["id"]))
    if fault == "happy":
        check("happy: normal delivery cleans receipt and intent",
              origin_bytes(job["id"]) == record and not primary.exists()
              and not fallback.exists()
              and not worker._intent_path(job["id"]).exists())
        worker._execute(job)  # BUS has not synced the new done record yet
        check("happy: same-process direct re-entry does not repeat effect",
              effects.read_text().splitlines() == [job["id"]])
    before = bus_tip()
    result = restart231(job, effects)
    after = bus_tip()
    check(f"{name}: fresh interpreter neither claims nor repeats body",
          result["claims"] == []
          and effects.read_text().splitlines() == [job["id"]])
    check(f"{name}: fresh interpreter retains a re-entry gate", result["gated"])
    if fault == "both":
        check("both: restart does NOT invent a done record",
              origin_bytes(job["id"]) is None and before == after)
        check("both: intent alone survives without in-memory gate",
              result["intent"] and not result["receipts"]
              and result["undelivered"] == [])
        check("both: uncertain attempt is surfaced separately from done",
              job["id"] in result["heartbeat"].get("uncertain_jobs", [])
              and job["id"] not in result["heartbeat"].get("pending_done", []))
    else:
        check(f"{name}: restart recovers EXACT done bytes",
              origin_bytes(job["id"]) == record)
        check(f"{name}: verified recovery clears receipts and intent",
              not result["receipts"] and not result["intent"], repr(result))
        if fault in ("happy", "lost-reply"):
            check(f"{name}: already-delivered replay creates NO commit",
                  before == after)
        else:
            count = subprocess.run(
                ["git", "--git-dir", str(BUS_BARE), "rev-list", "--count",
                 f"{before}..{after}"], capture_output=True, text=True,
                check=True).stdout.strip()
            check(f"{name}: recovery adds exactly ONE marker commit", count == "1")
            check(f"{name}: same-cycle post-drain gate covers stale BUS",
                  job["id"] in result["verified"])


for _name, _fault, _kind in (
        ("fallback", "primary", "ledger-guard"),
        ("delivery", "delivery", "ledger-watchdog"),
        ("partial", "partial", "ledger-guard"),
        ("lost-reply", "lost-reply", "ledger-guard"),
        ("both", "both", "ledger-guard"),
        ("happy", "happy", "ledger-guard")):
    test_restart231(_name, _fault, _kind)

# A failed intent fsync AFTER rename must still refuse the body.
# Disk presence alone is not confirmation of crash durability.
_job_refuse = {"id": "test-231-refuse", "job": "ledger-guard"}
_real_sync, _real_body = worker._fsync_dir, worker._execute_body
_refused_calls = []
def refuse_intent_sync(path):
    if path == worker.JOB_STATE:
        raise OSError("injected intent directory fsync failure")
    _real_sync(path)
worker._fsync_dir = refuse_intent_sync
worker._execute_body = lambda j: _refused_calls.append(j["id"])
try:
    worker._execute(_job_refuse)
finally:
    worker._fsync_dir, worker._execute_body = _real_sync, _real_body
check("intent fsync failure: body NOT entered despite renamed intent",
      _refused_calls == [] and worker._intent_path(_job_refuse["id"]).exists()
      and origin_done(_job_refuse["id"]) is None)

# Check actual durability primitive ordering, not just final files.
import stat
_events = []
_real_fsync, _real_replace = worker.os.fsync, worker.os.replace
def trace_fsync(fd):
    _events.append("dir-sync" if stat.S_ISDIR(os.fstat(fd).st_mode)
                   else "file-sync")
    return _real_fsync(fd)
def trace_replace(src, dest):
    _events.append("replace")
    return _real_replace(src, dest)
worker.os.fsync, worker.os.replace = trace_fsync, trace_replace
_probe = worker.JOB_STATE / "ordering-probe"
try:
    worker._write_receipt(_probe, "probe")
finally:
    worker.os.fsync, worker.os.replace = _real_fsync, _real_replace
check("durable write: file fsync, atomic rename, directory fsync",
      _events == ["file-sync", "replace", "dir-sync"], repr(_events))
_probe.unlink()

# Recovery-store corruption/conflicts inherit the existing no-overwrite
# contract, including fail-closed gating and heartbeat visibility.
for _mode in ("corrupt", "conflict"):
    _j = {"id": f"test-231-{_mode}", "job": "ledger-guard"}
    _f = worker.JOB_STATE / f"{_j['id']}.json"
    worker._write_receipt(worker._intent_path(_j["id"]), json.dumps(_j))
    _record = json.dumps({"worker": "test", "at": worker.now(),
                          "job": _j["job"], "archive": "ledger-guard",
                          "id": _j["id"]})
    if _mode == "conflict":
        assert REAL_PUBLISH_DONE(_j["id"], _record)
        _before = origin_bytes(_j["id"])
        _record = _record.replace("ledger-guard", "different-completion")
    else:
        _before = None
        _record = "{}"  # parses, but is not a completion receipt
    worker._write_receipt(_f, _record)
    _result = restart231(_j, TMP / f"effects-{_mode}")
    check(f"recovery {_mode}: never claims, never overwrites origin",
          _result["claims"] == [] and origin_bytes(_j["id"]) == _before)
    check(f"recovery {_mode}: intent and local gate retained",
          _result["intent"] and _result["gated"])
    _field = "corrupt_done" if _mode == "corrupt" else "pending_done"
    check(f"recovery {_mode}: heartbeat keeps evidence visible",
          _j["id"] in _result["heartbeat"].get(_field, []))
    check(f"recovery {_mode}: correct durable evidence retained",
          (_f.with_suffix(".json.corrupt").is_file() and not _f.exists())
          if _mode == "corrupt" else _f.read_text() == _record)

# A reported publish failure can follow partial effects. Keep its
# intent; a human decides whether re-execution is safe.
check("failed publish: existing attempt now requires reconciliation",
      worker._intent_path(job_fail["id"]).is_file()
      and worker._done_or_pending(job_fail["id"]))

# --- 20. #231: failed attempts are UNCERTAIN, never auto-retried ---
for _mode in ("return", "exception", "timeout"):
    _j = {"id": f"test-231-body-{_mode}", "job": "ledger-guard"}
    _saved_guard = worker.run_ledger_guard
    def failed_body(j):
        if _mode == "timeout":
            raise subprocess.TimeoutExpired("ledger-publisher", 1800)
        if _mode == "exception":
            raise RuntimeError("injected after possible partial effects")
        return False
    worker.run_ledger_guard = failed_body
    try:
        try:
            worker._execute(_j)
        except (RuntimeError, subprocess.TimeoutExpired):
            pass
    finally:
        worker.run_ledger_guard = _saved_guard
    _result = restart231(_j, TMP / f"effects-body-{_mode}")
    check(f"body {_mode}: restart blocks ambiguous attempt, not done",
          _result["claims"] == [] and _result["intent"]
          and _result["gated"] and origin_done(_j["id"]) is None
          and _j["id"] in _result["heartbeat"].get("uncertain_jobs", []))

# Abrupt death after an effect, before _mark_done: intent alone must
# block the next process, never masquerade as completed work.
_crash_job = {"id": "test-231-abrupt", "job": "ledger-guard"}
_crash_effects = TMP / "effects-abrupt"
_crash_code = r'''
import importlib.util, json, os, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location("crash231", sys.argv[1])
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)
def effect(job):
    with open(sys.argv[2], "a") as f:
        f.write(job["id"] + "\n")
        f.flush()
        os.fsync(f.fileno())
    os._exit(77)
w.run_ledger_guard = effect
w._execute(json.loads(sys.argv[3]))
'''
_crashed = subprocess.run(
    [sys.executable, "-c", _crash_code, str(REPO / "worker/worker.py"),
     str(_crash_effects), json.dumps(_crash_job)],
    env=os.environ.copy(), capture_output=True, text=True, timeout=30)
check("abrupt death: effect reached, process exits before completion",
      _crashed.returncode == 77 and _crash_effects.is_file()
      and origin_done(_crash_job["id"]) is None)
_crash_result = restart231(_crash_job, _crash_effects)
check("abrupt death: restart neither re-executes nor invents completion",
      _crash_result["claims"] == [] and _crash_result["intent"]
      and _crash_effects.read_text().splitlines() == [_crash_job["id"]]
      and origin_done(_crash_job["id"]) is None)

# Remote confirmation is only sufficient after a successful startup
# sync. A stale local BUS must not authorize work after receipt cleanup.
_real_git, _real_sh, _real_bus = worker.git_bus, worker.sh, worker.BUS
for _stage in ("clone", "fetch", "reset"):
    _commands = []
    def sync_git(command, timeout=120):
        _commands.append(command)
        return subprocess.CompletedProcess([], int(command.startswith(_stage)))
    worker.BUS = TMP / "missing-sync231" if _stage == "clone" else _real_bus
    worker.sh = lambda *a, **k: subprocess.CompletedProcess([], 1)
    worker.git_bus = sync_git
    _refused = False
    try:
        worker.sync_bus()
    except RuntimeError:
        _refused = True
    finally:
        worker.git_bus, worker.sh, worker.BUS = _real_git, _real_sh, _real_bus
    check(f"startup {_stage} failure: sync refuses stale queue",
          _refused and (_stage != "fetch" or _commands == ["fetch origin queue"]))

# The actual loop must stop the cycle at sync, not merely log and run.
_loop_saved = {n: getattr(worker, n) for n in
               ("self_update", "sync_bus", "flush_pending_done", "read_queue")}
_after_sync = []
def broken_sync():
    raise RuntimeError("injected startup sync failure")
worker.self_update = lambda: None
worker.sync_bus = broken_sync
worker.flush_pending_done = lambda: _after_sync.append("drain")
worker.read_queue = lambda: _after_sync.append("queue") or []
worker.time.sleep = _stop_after_one_cycle
try:
    worker.main()
except _CycleDone:
    pass
finally:
    worker.time.sleep = _REAL_SLEEP
    for _n, _f in _loop_saved.items():
        setattr(worker, _n, _f)
check("real main: failed startup sync admits NO work or drain", _after_sync == [])

# Same-host claim entry points must honor intent even with no receipts.
_j = {"id": "test-231-body-return", "job": "ledger-guard"}
check("claim: uncertain intent refuses a new claim",
      worker.claim(_j) is False and not worker.claimed(_j["id"]))

# Interrupted cleanup must leave replayable evidence until intent
# deletion has been durably confirmed. Inject its directory fsync.
_jid = "test-231-cleanup"
_cf = worker.PENDING_DONE / f"{_jid}.json"
_cf.write_text("completion-evidence")
worker._write_receipt(worker._intent_path(_jid), "intent-evidence")
_real_sync = worker._fsync_dir
worker._fsync_dir = lambda path: (_ for _ in ()).throw(OSError("sync failed"))
try:
    worker._forget_completion(_cf, _jid)
finally:
    worker._fsync_dir = _real_sync
check("cleanup: intent-sync failure retains completion evidence",
      _cf.exists() and worker._done_or_pending(_jid))
_cf.unlink(missing_ok=True)

# --- #233: a receipt whose recorded id differs from its filename ---
# is quarantined, never published, still gating ---------------------
# _valid_receipt used to check only shape (JSON object, string
# worker/at/job/archive); a receipt for job A sitting in file B.json
# would publish B's marker carrying A's metadata. The issue's literal
# fix (d["job"] == job_id) is WRONG: "job" holds the job TEXT, not
# the id (_mark_done writes job["job"]), so it would quarantine every
# legitimate receipt - the drain/conflict sections above prove it.
# The fix carries the id in its own field and compares that instead.
_job233 = {"id": "test-233-mismatch",
           "job": "sweep-lite POUL.CA market=EGX"}
_good233 = json.dumps(
    {"worker": "borsagator-worker-5", "at": worker.now(),
     "job": _job233["job"], "archive": "abc123", "id": _job233["id"]})
_bad233 = json.dumps(
    {"worker": "borsagator-worker-5", "at": worker.now(),
     "job": _job233["job"], "archive": "abc123", "id": "some-other-job"})
_old233 = json.dumps(
    {"worker": "borsagator-worker-5", "at": worker.now(),
     "job": _job233["job"], "archive": "abc123"})
check("233: matching receipt still valid (control)",
      worker._valid_receipt(_good233, _job233["id"]))
check("233: mismatched id field rejected",
      not worker._valid_receipt(_bad233, _job233["id"]))
check("233: old-shape receipt without id rejected",
      not worker._valid_receipt(_old233, _job233["id"]))
check("233: missing job field still rejected",
      not worker._valid_receipt(json.dumps(
          {"worker": "borsagator-worker-5", "at": worker.now(),
           "archive": "abc123", "id": _job233["id"]}), _job233["id"]))
_receipt233 = worker.PENDING_DONE / f"{_job233['id']}.json"
_receipt233.write_text(_bad233)
worker.flush_pending_done()
check("233: mismatched receipt quarantined to *.corrupt",
      (worker.PENDING_DONE / f"{_job233['id']}.json.corrupt")
      .is_file() and not _receipt233.exists())
check("233: mismatched receipt NOT published to origin/queue",
      origin_done(_job233["id"]) is None)
check("233: mismatched receipt still gates local re-execution",
      worker._done_or_pending(_job233["id"])
      and not main_loop_runnable(_job233))
worker.heartbeat()
_payload233 = json.loads(
    (worker.BUS / "queue" / "heartbeat.json").read_text())
check("233: quarantine surfaced in heartbeat corrupt_done",
      _job233["id"] in _payload233.get("corrupt_done", []),
      f"corrupt_done={_payload233.get('corrupt_done')}")
(worker.PENDING_DONE / f"{_job233['id']}.json.corrupt").unlink(missing_ok=True)

failed = [c for c in CHECKS if not c[1]]
print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} passed")
sys.exit(1 if failed else 0)
