#!/usr/bin/env python3
"""Borsagator worker agent (issue #33) — local execution mode.

The worker's control bus is the borsagator repo itself:
- Jobs arrive as entries in queue/queue.json on the `queue` branch:
  {"id": "...", "job": "run yahooquery POUL.CA", "added": "<iso>"}
- The worker claims a job by committing queue/claims/<id>.json and
  pushing; a push conflict means another worker won — skip.
- Results are committed to the `archive` branch under
  worker-runs/<ts>__<job-slug>/ (same tree shape as Actions sweeps).
- queue/heartbeat.json on the `queue` branch is rewritten every cycle
  — liveness is observable from anywhere with repo read access.

No inbound access of any kind: the worker only ever makes outbound
HTTPS calls (GitHub + the data sources the tools themselves use).
LLM/API keys for the tools come from /etc/gator.env (written at
provisioning time); tools whose keys are absent fail their run
honestly and the rest of the job continues.
"""
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(os.environ.get("GATOR_ROOT", "/opt/gator"))
BUS = ROOT / "bus"            # borsagator clone (token remote), queue branch
RUNNERS = ROOT / "runners"    # public runner clones (anonymous HTTPS)
VENVS = ROOT / "venvs"
OUT = ROOT / "out"
POLL_SECONDS = int(os.environ.get("GATOR_POLL", "300"))
ORG = "moos-labs"


def sh(cmd, cwd=None, env=None, timeout=3600):
    e = dict(os.environ)
    if env:
        e.update(env)
    return subprocess.run(cmd, shell=True, cwd=cwd, env=e,
                          capture_output=True, text=True, timeout=timeout)


def now():
    return datetime.now(timezone.utc).isoformat()


def git_bus(*args, timeout=120):
    return sh(f"git -C {BUS} " + " ".join(args), timeout=timeout)


def sync_bus():
    if not BUS.exists():
        url = os.environ["GATOR_BUS_URL"]
        sh(f"git clone --branch queue --single-branch {url} {BUS}",
           timeout=300)
    git_bus("fetch origin queue", timeout=120)
    git_bus("reset --hard origin/queue", timeout=60)
    git_bus("config user.email worker@borsagator.local", timeout=30)
    git_bus("config user.name borsagator-worker", timeout=30)


def push_bus(message):
    git_bus("add -A", timeout=60)
    if git_bus("commit -m " + json.dumps(message), timeout=60).returncode != 0:
        return False
    return git_bus("push origin queue", timeout=120).returncode == 0


def heartbeat():
    (BUS / "queue").mkdir(exist_ok=True)
    (BUS / "queue" / "heartbeat.json").write_text(json.dumps(
        {"worker": os.uname().nodename, "at": now(),
         "version": "worker-v1"}))
    push_bus("heartbeat")


def read_queue():
    q = BUS / "queue" / "queue.json"
    if not q.exists():
        return []
    try:
        return json.loads(q.read_text())
    except Exception:
        return []


def claimed(job_id):
    return (BUS / "queue" / "claims" / f"{job_id}.json").exists()


def claim(job):
    c = BUS / "queue" / "claims"
    c.mkdir(parents=True, exist_ok=True)
    (c / f"{job['id']}.json").write_text(json.dumps(
        {"worker": os.uname().nodename, "at": now(), "job": job["job"]}))
    return push_bus(f"claim {job['id']}")


def registry():
    reg_file = BUS / "registry" / "tools.json"
    if not BUS.joinpath("registry").exists():
        # registry lives on main; keep a main checkout alongside
        main = ROOT / "main"
        if not main.exists():
            sh(f"git clone --depth 1 https://github.com/{ORG}/borsagator {main}",
               timeout=300)
        else:
            sh(f"git -C {main} pull --ff-only", timeout=120)
        reg_file = main / "registry" / "tools.json"
    return json.loads(reg_file.read_text())


def parse_job(job, reg):
    """Reuse the orchestrator's grammar, minimally: run/category/
    sweep-lite/sweep, sequential only (the worker is one machine —
    the COMMANDS race cannot happen here)."""
    tools = {t["id"]: t for t in reg["tools"] if t.get("status") == "active"}
    parts = job.split()
    if not parts:
        return []
    kind = parts[0]
    if kind == "run" and len(parts) >= 3:
        return [(parts[1], parts[2])]
    if kind == "category" and len(parts) >= 3:
        return [(t, parts[2]) for t, v in tools.items()
                if v.get("category") == parts[1]]
    if kind in ("sweep", "sweep-lite") and len(parts) >= 2:
        sel = [(t, parts[1]) for t, v in tools.items()
               if kind == "sweep" or v.get("category") != "agent"]
        return sel
    return []


def run_tool(tool, ticker, template):
    repo = RUNNERS / tool
    if not repo.exists():
        r = sh(f"git clone --depth 1 https://github.com/{ORG}/{tool}-runner {repo}",
               timeout=600)
        if r.returncode != 0:
            r2 = sh(f"git clone --depth 1 https://github.com/{ORG}/{tool} {repo}",
                    timeout=600)
            if r2.returncode != 0:
                return "clone-failed", ""
    else:
        sh(f"git -C {repo} pull --ff-only", timeout=180)
    venv = VENVS / tool
    py = venv / "bin" / "python"
    if not py.exists():
        sh(f"python3 -m venv {venv}", timeout=300)
        req = repo / "requirements.txt"
        if req.exists():
            sh(f"{venv}/bin/pip install -q -r {req}", timeout=1800)
    results = repo / "results"
    sh(f"rm -rf {results}", timeout=60)
    cmd = template.replace("{ticker}", ticker).replace(
        "{date}", datetime.now(timezone.utc).date().isoformat())
    env = {"PATH": f"{venv}/bin:" + os.environ["PATH"],
           "VIRTUAL_ENV": str(venv)}
    r = sh(cmd, cwd=repo, env=env, timeout=3600)
    status = "ok" if r.returncode == 0 else f"exit-{r.returncode}"
    return status, (r.stdout + r.stderr)[-4000:]


def publish(job, results_dir, manifest):
    arch = ROOT / "archive-push"
    if not arch.exists():
        url = os.environ["GATOR_BUS_URL"]
        sh(f"git clone --branch archive --single-branch {url} {arch}",
           timeout=600)
    else:
        sh(f"git -C {arch} pull --ff-only", timeout=180)
    slug = job["job"].lower().replace(" ", "-").replace(".", "-")
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d/%H%M%S")
    dest = arch / "worker-runs" / f"{ts}__{slug}__{job['id']}"
    sh(f"mkdir -p {dest} && cp -r {results_dir}/. {dest}/", timeout=300)
    (dest / "manifest.json").write_text(json.dumps(manifest, indent=1))
    sh(f"git -C {arch} add -A && git -C {arch} commit -m "
       + json.dumps(f"worker run {job['id']}: {job['job']}"), timeout=120)
    return sh(f"git -C {arch} push origin archive",
              timeout=300).returncode == 0


def execute(job):
    reg = registry()
    plan = parse_job(job["job"], reg)
    templates = {t["id"]: t["command"] for t in reg["tools"]}
    workdir = OUT / job["id"]
    workdir.mkdir(parents=True, exist_ok=True)
    manifest = {"job": job, "worker": os.uname().nodename,
                "started": now(), "tools": {}}
    for tool, ticker in plan:
        status, log = run_tool(tool, ticker, templates.get(tool, ""))
        dest = workdir / tool
        src = RUNNERS / tool / "results"
        if src.exists():
            sh(f"mkdir -p {dest} && cp -r {src}/. {dest}/", timeout=120)
        (workdir / f"{tool}.log").write_text(log)
        manifest["tools"][tool] = status
    manifest["finished"] = now()
    publish(job, workdir, manifest)


def main():
    RUNNERS.mkdir(parents=True, exist_ok=True)
    VENVS.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    while True:
        try:
            sync_bus()
            heartbeat()
            for job in read_queue():
                if not claimed(job["id"]):
                    if claim(job):
                        execute(job)
                        break  # one job per cycle, then re-sync
        except Exception as e:  # the loop must survive anything
            print(f"worker cycle error: {type(e).__name__}: {e}",
                  file=sys.stderr, flush=True)
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    sys.exit(main())
