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
    r = sh(cmd, cwd=repo, env=env, timeout=3600)
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
    libdir = ensure_chromium_deps()
    script = ROOT / "main" / "worker" / "egx_harvest.py"
    run_dir = workdir / "egx-harvest"
    run_dir.mkdir(parents=True, exist_ok=True)
    env = {k: v for k, v in os.environ.items()
           if k not in ENV_DENY_FOR_TOOLS}
    if libdir:
        env["LD_LIBRARY_PATH"] = (libdir + ":"
                                  + env.get("LD_LIBRARY_PATH", ""))
    r = sh(f"{py} {script} {code}", cwd=run_dir, env=env, timeout=3600)
    (workdir / "egx-harvest.log").write_text((r.stdout + r.stderr)[-4000:])
    return {"egx-harvest": "ok" if r.returncode == 0
            else f"exit-{r.returncode}"}


# Issue #47: worker-3's image predates the cloud-init Chromium
# libraries (added 2026-11-14 06:03 UTC, future launches only), and
# the gator user has no sudo — so headless Chromium fails to load
# (first seen: libatk-1.0.so.0). Fetch the missing .debs from the
# official Ubuntu archive into user space and point the browser at
# them via LD_LIBRARY_PATH. No root, no apt, no privilege change.
PLAYWRIGHT_SONAME_PKGS = {
    "libatk-1.0.so.0": "libatk1.0-0t64",
    "libatk-bridge-2.0.so.0": "libatk-bridge2.0-0t64",
    "libatspi.so.2": "at-spi2-core",
    "libcups.so.2": "libcups2t64",
    "libdrm.so.2": "libdrm2",
    "libxkbcommon.so.0": "libxkbcommon0",
    "libxcomposite.so.1": "libxcomposite1",
    "libxdamage.so.1": "libxdamage1",
    "libxfixes.so.3": "libxfixes3",
    "libxrandr.so.2": "libxrandr2",
    "libgbm.so.1": "libgbm1",
    "libasound.so.2": "libasound2t64",
    "libpango-1.0.so.0": "libpango-1.0-0",
    "libpangoft2-1.0.so.0": "libpangoft2-1.0-0",
    "libpangocairo-1.0.so.0": "libpangocairo-1.0-0",
    "libcairo.so.2": "libcairo2",
    "libnss3.so": "libnss3",
    "libnspr4.so": "libnspr4",
    "libsmime3.so": "libnss3",
    "libnssutil.so": "libnss3",
    "libplc4.so": "libnspr4",
    "libplds4.so": "libnspr4",
    "libgio-2.0.so.0": "libglib2.0-0",
    "libgobject-2.0.so.0": "libglib2.0-0",
    "libglib-2.0.so.0": "libglib2.0-0",
    "libdbus-1.so.3": "libdbus-1-3",
    "libexpat.so.1": "libexpat1",
    "libx11.so.6": "libx11-6",
    "libxcb.so.1": "libxcb1",
    "libxext.so.6": "libxext6",
    "libxi.so.6": "libxi6",
    "libxtst.so.6": "libxtst6",
    "libxss.so.1": "libxss1",
    "libxcursor.so.1": "libxcursor1",
    "libxinerama.so.1": "libxinerama1",
}


def _os_codename():
    try:
        for line in Path("/etc/os-release").read_text().splitlines():
            if line.startswith("VERSION_CODENAME="):
                return line.split("=", 1)[1].strip().strip('"')
    except Exception:
        pass
    return "noble"


def _packages_index(codename):
    """Map package name -> archive path for one Ubuntu release/arch."""
    import gzip
    import urllib.request
    url = (f"http://archive.ubuntu.com/ubuntu/dists/{codename}/main/"
           "binary-arm64/Packages.gz")
    try:
        with urllib.request.urlopen(url, timeout=120) as resp:
            raw = gzip.decompress(resp.read()).decode("utf-8", "replace")
    except Exception as e:
        print(f"[deps] packages index fetch failed: {e}", flush=True)
        return {}
    pkgs, cur = {}, {}
    for line in raw.splitlines():
        if not line.strip():
            if cur.get("Package") and cur.get("Filename"):
                pkgs[cur["Package"]] = cur["Filename"]
            cur = {}
        elif ": " in line:
            k, v = line.split(": ", 1)
            cur[k] = v
    if cur.get("Package") and cur.get("Filename"):
        pkgs[cur["Package"]] = cur["Filename"]
    return pkgs


def _missing_libs(binary, libdir=""):
    env = dict(os.environ)
    if libdir:
        env["LD_LIBRARY_PATH"] = libdir + ":" + env.get("LD_LIBRARY_PATH",
                                                        "")
    r = sh(f"ldd {binary}", env=env, timeout=120)
    out = set()
    for line in (r.stdout + r.stderr).splitlines():
        if "not found" in line:
            out.add(line.split()[0])
    return sorted(out)


def ensure_chromium_deps():
    """Make Playwright's headless Chromium loadable without root.

    Returns the extracted lib dir (for LD_LIBRARY_PATH), or '' when
    nothing was needed / nothing could be done."""
    import urllib.request
    cache = ROOT / "chromium-deps"
    libdir = cache / "usr" / "lib" / "aarch64-linux-gnu"
    cache.mkdir(parents=True, exist_ok=True)
    shells = sorted(Path.home().glob(
        ".cache/ms-playwright/chromium_headless_shell-*/"
        "chrome-headless-shell-linux-arm64/chrome-headless-shell"))
    if not shells:
        print("[deps] no chromium headless shell found yet", flush=True)
        return ""
    binary = str(shells[-1])
    pkgs = None
    for _round in range(4):
        missing = _missing_libs(binary, str(libdir))
        if not missing:
            print("[deps] chromium libs complete", flush=True)
            return str(libdir) if (libdir.exists()
                                   and any(libdir.iterdir())) else ""
        print(f"[deps] missing: {missing}", flush=True)
        if pkgs is None:
            pkgs = _packages_index(_os_codename())
            if not pkgs:
                return ""
        progressed = False
        for soname in missing:
            pkg = PLAYWRIGHT_SONAME_PKGS.get(soname)
            if not pkg:
                print(f"[deps] no package known for {soname}", flush=True)
                continue
            filename = None
            for cand in (pkg, re.sub(r"t64$", "", pkg)):
                if cand in pkgs:
                    filename = pkgs[cand]
                    break
            if not filename:
                print(f"[deps] {pkg} not in index", flush=True)
                continue
            deb = cache / Path(filename).name
            if not deb.exists():
                url = f"http://archive.ubuntu.com/ubuntu/{filename}"
                print(f"[deps] fetching {url}", flush=True)
                try:
                    with urllib.request.urlopen(url, timeout=300) as resp:
                        deb.write_bytes(resp.read())
                except Exception as e:
                    print(f"[deps] fetch failed {url}: {e}", flush=True)
                    continue
            r = sh(f"dpkg-deb -x {deb} {cache}", timeout=120)
            if r.returncode == 0:
                progressed = True
            else:
                print(f"[deps] dpkg-deb failed for {deb}: "
                      f"{r.stderr[-300:]}", flush=True)
        if not progressed:
            print("[deps] no progress this round — stopping", flush=True)
            return str(libdir) if libdir.exists() else ""
    print("[deps] still missing after 4 rounds", flush=True)
    return str(libdir) if libdir.exists() else ""


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

