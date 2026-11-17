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

This test exercises the REAL reclaim_stale_claims / claim / done /
_execute / publish path — push_bus is stubbed (no network), and
run_tool / run_harvest are stubbed only where a runner clone would
be needed. The publish() SHA contract is tested against a real
local git repo (file URL, no network).

Run: python3 worker/test_worker_149.py   (stdlib only, no network)
Fails on unmodified main: done/_mark_done do not exist, and the
completed-job checks fail (a done job is re-runnable after reclaim).
"""
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
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
    done jobs are skipped; an unclaimed, unfinished job is claimed
    and executed."""
    if worker.done(job["id"]):
        return False
    if not worker.claimed(job["id"]):
        return True
    return False


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
rec = done_dir() / f"{job_sweep['id']}.json"
check("sweep-lite publish success: done record written",
      rec.is_file())
if rec.is_file():
    data = json.loads(rec.read_text())
    check("sweep-lite done record carries the archive commit + job",
          data.get("archive") == SHA and data.get("job") == job_sweep["job"]
          and data.get("at"),
          f"record={data}")
check("sweep-lite publish success: 'done <id>' pushed to the bus",
      f"done {job_sweep['id']}" in PUSHED)


def fake_run_harvest(job, workdir):
    return {"egx-harvest": "ok"}


worker.run_harvest = fake_run_harvest
job_harvest = {"id": "test-149-harvest", "job": "harvest-egx POUL"}
worker._execute(job_harvest)
rec_h = done_dir() / f"{job_harvest['id']}.json"
check("harvest publish success: done record written with archive sha",
      rec_h.is_file() and json.loads(rec_h.read_text()).get("archive") == SHA)

job_fail = {"id": "test-149-fail", "job": "run yahooquery POUL.CA"}
worker.publish = fake_publish_fail
PUSHED.clear()
worker._execute(job_fail)
check("failed publish: NO done record written",
      not (done_dir() / f"{job_fail['id']}.json").exists()
      and f"done {job_fail['id']}" not in PUSHED)
check("failed publish: error file written, job stays reclaimable",
      (claims_dir() / f"{job_fail['id']}.error.json").is_file()
      and not worker.done(job_fail["id"]))

# --- 11. A failed done-push is loud and returns False ---------------
FAIL_NEXT_PUSH.append(True)
check("_mark_done returns False when the bus push fails",
      worker._mark_done({"id": "test-149-pushfail",
                         "job": "run yahooquery POUL.CA"}, SHA) is False)

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

failed = [c for c in CHECKS if not c[1]]
print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} passed")
sys.exit(1 if failed else 0)
