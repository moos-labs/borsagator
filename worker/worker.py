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
import re
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
# Panel round 2 (Gemini review, 2026-11-14): the bus credential must
# never reach a tool's process environment — tools have dumped env in
# debug logs before, and results are pushed to a public archive.
ENV_DENY_FOR_TOOLS = {"GATOR_BUS_URL"}
TICKER_RE = re.compile(r"^[A-Za-z0-9.\-]{1,12}$")   # same as issue #49
JOB_ID_RE = re.compile(r"^[A-Za-z0-9\-]{1,40}$")
STALE_CLAIM_HOURS = 6
OUT_RETENTION_DAYS = 7


def sh(cmd, cwd=None, env=None, timeout=3600):
    e = dict(os.environ)
    if env:
        e.update(env)
    return subprocess.run(cmd, shell=True, cwd=cwd, env=e,
                          capture_output=True, text=True, timeout=timeout)


def sh_bash(cmd, cwd=None, env=None, timeout=3600):
    """Tool templates are written for GitHub Actions, whose shell
    is bash: they use pipefail, source and friends. The worker's
    /bin/sh is dash and rejects those (news-disclosure died with
    'set: Illegal option -o pipefail', exit 2, on 2026-11-14).
    Run tool commands under bash to match Actions semantics."""
    import shlex
    return sh(f"bash -c {shlex.quote(cmd)}", cwd=cwd, env=env,
              timeout=timeout)


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
        sel = [(parts[1], parts[2])]
    elif kind == "category" and len(parts) >= 3:
        sel = [(t, parts[2]) for t, v in tools.items()
               if v.get("category") == parts[1]]
    elif kind in ("sweep", "sweep-lite") and len(parts) >= 2:
        sel = [(t, parts[1]) for t, v in tools.items()
               if kind == "sweep" or v.get("category") != "agent"]
    else:
        return []
    # Panel round 2: a job string reaches shell command templates via
    # {ticker}; only registry tool ids and allowlisted tickers pass.
    return [(t, tk) for t, tk in sel
            if t in tools and TICKER_RE.match(tk)]


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
    env = {k: v for k, v in os.environ.items()
           if k not in ENV_DENY_FOR_TOOLS}
    env.update({"PATH": f"{venv}/bin:" + os.environ["PATH"],
                "VIRTUAL_ENV": str(venv)})
    if tool == "news-disclosure" and ticker.upper().endswith(".CA"):
        hp = ensure_harvest(ticker.upper().split(".")[0])
        if hp is not None:
            env["EGX_HARVEST_FILE"] = str(hp)
    r = sh_bash(cmd, cwd=repo, env=env, timeout=3600)
    status = "ok" if r.returncode == 0 else f"exit-{r.returncode}"
    return status, (r.stdout + r.stderr)[-4000:]


def publish(job, results_dir, manifest):
    arch = ROOT / "archive-push"
    if not arch.exists():
        url = os.environ["GATOR_BUS_URL"]
        sh(f"git clone --branch archive --single-branch {url} {arch}",
           timeout=900)
        # The bus clone gets its identity in sync_bus; this clone needs
        # its own — without it every commit fails silently (found by
        # the w2 self-test, 2026-11-14: claimed, ran, never published).
        sh(f"git -C {arch} config user.email worker@borsagator.local",
           timeout=30)
        sh(f"git -C {arch} config user.name borsagator-worker", timeout=30)
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


def run_harvest(job, workdir):
    """Issue #47: EGX disclosure harvest — a borsagator-side script
    (kept current by self_update's main checkout) driven in its own
    playwright venv, with a persistent Chromium profile on the box."""
    parts = job["job"].split()
    code = parts[1] if len(parts) > 1 else ""
    if not TICKER_RE.match(code.replace(".CA", "")):
        return {"egx-harvest": "bad-code"}
    venv = VENVS / "egx-harvest"
    py = venv / "bin" / "python"
    if not py.exists():
        sh(f"python3 -m venv {venv}", timeout=300)
        sh(f"{venv}/bin/pip install -q playwright", timeout=1200)
    marker = venv / ".browser-installed"
    if not marker.exists():
        sh(f"{py} -m playwright install chromium", timeout=1800)
        marker.write_text(now())
    script = ROOT / "main" / "worker" / "egx_harvest.py"
    run_dir = workdir / "egx-harvest"
    run_dir.mkdir(parents=True, exist_ok=True)
    env = {k: v for k, v in os.environ.items()
           if k not in ENV_DENY_FOR_TOOLS}
    cmd = f"{py} {script} {code}"
    if Path("/usr/bin/xvfb-run").exists():
        cmd = f"xvfb-run -a -s '-screen 0 1366x768x24' {cmd}"
    r = sh(cmd, cwd=run_dir, env=env, timeout=3600)
    (workdir / "egx-harvest.log").write_text((r.stdout + r.stderr)[-4000:])
    return {"egx-harvest": "ok" if r.returncode == 0
            else f"exit-{r.returncode}"}


HARVEST_TTL_HOURS = 12


def ensure_harvest(code):
    """Issue #53: keep a fresh EGX harvest on the box and return its
    disclosures.json path (or None). A harvest failure never blocks
    the news run — the feed just stays title-only, as before."""
    cache_dir = ROOT / "harvest"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache = cache_dir / f"{code}.json"
    if cache.exists():
        age = time.time() - cache.stat().st_mtime
        if age < HARVEST_TTL_HOURS * 3600:
            return cache
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    fake_job = {"id": f"auto-harvest-{code}-{stamp}",
                "job": f"harvest-egx {code}", "added": now()}
    wd = OUT / fake_job["id"]
    wd.mkdir(parents=True, exist_ok=True)
    try:
        res = run_harvest(fake_job, wd)
        src = wd / "egx-harvest" / "results" / "disclosures.json"
        if res.get("egx-harvest") == "ok" and src.exists():
            cache.write_bytes(src.read_bytes())
            return cache
    except Exception:
        pass
    return cache if cache.exists() else None


def execute(job):
    reg = registry()
    workdir = OUT / job["id"]
    workdir.mkdir(parents=True, exist_ok=True)
    manifest = {"job": job, "worker": os.uname().nodename,
                "started": now(), "tools": {}}
    if job["job"].startswith("harvest-egx"):
        manifest["tools"] = run_harvest(job, workdir)
        manifest["finished"] = now()
        if not publish(job, workdir, manifest):
            try:
                err = BUS / "queue" / "claims" / f"{job['id']}.error.json"
                err.write_text(json.dumps(
                    {"worker": os.uname().nodename, "at": now(),
                     "error": "publish failed"}))
                push_bus(f"publish failed {job['id']}")
            except Exception:
                pass
        return
    plan = parse_job(job["job"], reg)
    templates = {t["id"]: t["command"] for t in reg["tools"]}
    for tool, ticker in plan:
        status, log = run_tool(tool, ticker, templates.get(tool, ""))
        dest = workdir / tool
        src = RUNNERS / tool / "results"
        if src.exists():
            sh(f"mkdir -p {dest} && cp -r {src}/. {dest}/", timeout=120)
        (workdir / f"{tool}.log").write_text(log)
        manifest["tools"][tool] = status
    manifest["finished"] = now()
    if not publish(job, workdir, manifest):
        # Failures must be observable on the bus, not just local.
        try:
            err = BUS / "queue" / "claims" / f"{job['id']}.error.json"
            err.write_text(json.dumps(
                {"worker": os.uname().nodename, "at": now(),
                 "error": "publish failed"}))
            push_bus(f"publish failed {job['id']}")
        except Exception:
            pass


def prune_out():
    cutoff = time.time() - OUT_RETENTION_DAYS * 86400
    for d in OUT.iterdir() if OUT.exists() else []:
        if d.is_dir() and d.stat().st_mtime < cutoff:
            sh(f"rm -rf {d}", timeout=120)


def reclaim_stale_claims():
    """A claim whose push succeeded but whose result never published
    (worker died mid-job) must not block the job forever."""
    claims = BUS / "queue" / "claims"
    if not claims.exists():
        return
    cutoff = datetime.now(timezone.utc).timestamp() - STALE_CLAIM_HOURS * 3600
    changed = False
    for f in claims.glob("*.json"):
        try:
            at = json.loads(f.read_text()).get("at", "")
            claimed_ts = datetime.fromisoformat(at).timestamp()
        except Exception:
            continue  # unparseable claim: leave it, a human looks
        if claimed_ts < cutoff:
            f.unlink()
            changed = True
    if changed:
        push_bus("reclaim stale claims")


def self_update():
    """Pull the main checkout; if worker/worker.py changed, adopt it
    and restart — fixes reach the worker over the bus, no relaunch.
    (Added after the w2 self-test forced a full replacement cycle.)"""
    main = ROOT / "main"
    if not main.exists():
        sh(f"git clone --depth 1 https://github.com/{ORG}/borsagator {main}",
           timeout=300)
        return
    sh(f"git -C {main} pull --ff-only", timeout=120)
    src = main / "worker" / "worker.py"
    me = Path(__file__).resolve()
    try:
        if src.exists() and src.read_bytes() != me.read_bytes():
            me.write_bytes(src.read_bytes())
            os.execv(sys.executable, [sys.executable, str(me)])
    except Exception:
        pass


def main():
    RUNNERS.mkdir(parents=True, exist_ok=True)
    VENVS.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    while True:
        try:
            self_update()
            sync_bus()
            reclaim_stale_claims()
            prune_out()
            heartbeat()
            for job in read_queue():
                if not JOB_ID_RE.match(str(job.get("id", ""))):
                    continue  # panel round 2: ids reach file paths
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
