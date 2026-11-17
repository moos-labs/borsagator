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

Issue #66: the worker also owns the clock. The schedule lives as data
in queue/schedule.json on the `queue` branch (Sun–Thu 08:15 Cairo);
every poll cycle the worker checks it and enqueues a deterministic
`sched-<date>` bus job when one is due. The GitHub Actions cron is
only a fallback (staggered to 06:45 UTC, with a skip-check on today's
claim) until the worker schedule has fired correctly twice.
"""
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(os.environ.get("GATOR_ROOT", "/opt/gator"))
BUS = ROOT / "bus"            # borsagator clone (token remote), queue branch
RUNNERS = ROOT / "runners"    # public runner clones (anonymous HTTPS)
VENVS = ROOT / "venvs"
OUT = ROOT / "out"
POLL_SECONDS = int(os.environ.get("GATOR_POLL", "300"))
ORG = "moos-labs"
# D2 (issue #65): the worker's code channel. The worker NEVER executes
# main-tip code: it follows the `worker-release` branch, which only
# moves by a reviewed promotion, and only adopts a tip that is a
# fast-forward descendant of the code it already runs. GATOR_PIN_SHA
# is an optional emergency freeze (normally unset): when set, only
# that exact SHA is adopted.
UPDATE_BRANCH = os.environ.get("GATOR_UPDATE_BRANCH", "worker-release")
UPDATE_PIN = os.environ.get("GATOR_PIN_SHA", "")
CODE = ROOT / "release"      # release-branch checkout (was ROOT/"main")
UPDATE_ERROR = None          # last self-update refusal, in heartbeat
# Panel round 2 (Gemini review, 2026-11-14): the bus credential must
# never reach a tool's process environment — tools have dumped env in
# debug logs before, and results are pushed to a public archive.
ENV_DENY_FOR_TOOLS = {"GATOR_BUS_URL"}
TICKER_RE = re.compile(r"^[A-Za-z0-9.\-]{1,12}$")   # same as issue #49
JOB_ID_RE = re.compile(r"^[A-Za-z0-9\-]{1,40}$")
STALE_CLAIM_HOURS = 6
OUT_RETENTION_DAYS = 7


def _assert_no_denied(env):
    """Final subprocess-boundary guard (issue #146): a supplied env
    must never carry a denied credential. Fail closed — a caller
    that built the env wrong is a bug, and the leak it would cause
    lands in a publicly archived tool log."""
    leaked = sorted(set(env) & ENV_DENY_FOR_TOOLS)
    if leaked:
        raise AssertionError(
            "refusing to spawn a subprocess with denied env keys: "
            + ", ".join(leaked))


def sh(cmd, cwd=None, env=None, timeout=3600):
    if env is None:
        # Worker-internal calls (git/bus plumbing): the worker's own
        # process env, bus credential included — this is the worker,
        # not a tool.
        e = dict(os.environ)
    else:
        # Issue #146: a supplied env is the COMPLETE subprocess env.
        # The old `e = dict(os.environ); e.update(env)` merged the
        # caller's filtered env back into the full parent env, so the
        # ENV_DENY_FOR_TOOLS filtering in run_tool (which strips
        # GATOR_BUS_URL) was undone at this final boundary and the bus
        # write-credential reached every tool process. Callers that
        # supply env (run_tool, the EGX harvest) already pass a full
        # filtered copy of os.environ, so nothing is lost here.
        _assert_no_denied(env)
        e = dict(env)
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


QUEUE_ERROR = None  # last queue.json parse error (panel round 3, R3-09)


def heartbeat():
    (BUS / "queue").mkdir(exist_ok=True)
    payload = {"worker": os.uname().nodename, "at": now(),
               "version": "worker-v1",
               "code_sha": update_checkout_sha(),
               "update_branch": UPDATE_BRANCH}
    if QUEUE_ERROR:
        # A malformed queue.json must not idle the fleet behind a
        # green heartbeat (INS-R3-09).
        payload["queue_error"] = QUEUE_ERROR
    if UPDATE_ERROR:
        # D2: a refused update must be visible on the bus — stale
        # code is safe code, but silent staleness is not.
        payload["update_error"] = UPDATE_ERROR
    (BUS / "queue" / "heartbeat.json").write_text(json.dumps(payload))
    push_bus("heartbeat")


def read_queue():
    global QUEUE_ERROR
    q = BUS / "queue" / "queue.json"
    if not q.exists():
        QUEUE_ERROR = None
        return []
    try:
        data = json.loads(q.read_text())
        QUEUE_ERROR = None
        return data
    except Exception as e:
        QUEUE_ERROR = f"{type(e).__name__}: {e}"[:200]
        print(f"read_queue: {QUEUE_ERROR}", file=sys.stderr, flush=True)
        return []


def claimed(job_id):
    return (BUS / "queue" / "claims" / f"{job_id}.json").exists()


def claim(job):
    c = BUS / "queue" / "claims"
    c.mkdir(parents=True, exist_ok=True)
    (c / f"{job['id']}.json").write_text(json.dumps(
        {"worker": os.uname().nodename, "at": now(), "job": job["job"]}))
    return push_bus(f"claim {job['id']}")


# --- Issue #66: worker-owned schedule ---------------------------------
# The schedule lives as data on the `queue` branch
# (queue/schedule.json), e.g.:
#   [{"id": "sched-sweep-lite-poul", "job": "sweep-lite POUL.CA market=EGX",
#     "days": ["Sun", "Mon", "Tue", "Wed", "Thu"], "time": "08:15",
#     "tz": "Africa/Cairo"}]
# Every poll cycle run_schedule_check() reads it (the bus was just
# re-synced) and enqueues a deterministic `sched-<YYYY-MM-DD>` job
# when one is due. Cairo observes DST (Egypt reintroduced it in 2023:
# 08:15 Cairo is 06:15 UTC in winter, 05:15 UTC in summer), so the
# fire time is computed with zoneinfo, never a fixed UTC offset —
# and 08:15 is never ambiguous or nonexistent on either 2026
# transition day (both happen at 00:00 local).
SCHEDULE_FILE = "queue/schedule.json"
SCHEDULED_JOB_PREFIX = "sched-"
# A missed fire is caught up only while still pre-open; after this
# Cairo time the worker marks it missed explicitly instead of running
# a post-open sweep on stale prices (the Actions fallback at 06:45
# UTC covers the common worker-down case while it still exists).
SCHEDULE_CATCHUP_HOUR = 9
SCHEDULE_CATCHUP_MINUTE = 30
# Poll is 5 min, so a job enqueued "at 08:15" lands 08:15–08:25
# Cairo; nothing downstream may assume 08:15 sharp.


def _schedule_fire_time(entry, day):
    """The entry's fire time on `day` (a date) in the entry's tz,
    or None if the entry is malformed."""
    try:
        hh, mm = entry["time"].split(":")
        tz = ZoneInfo(entry.get("tz") or "Africa/Cairo")
        return datetime(day.year, day.month, day.day,
                        int(hh), int(mm), tzinfo=tz)
    except Exception:
        return None


def schedule_decision(entry, now_local):
    """Pure decision for one schedule entry at `now_local` (an aware
    datetime already in the entry's tz). Returns "fire" when the
    scheduled time today has passed and the 09:30 Cairo catch-up
    cutoff has not, "missed" when past the cutoff, None when the
    entry does not fire today or has not come due yet."""
    if not entry.get("job") or not entry.get("time"):
        return None
    if now_local.strftime("%a") not in (entry.get("days") or []):
        return None
    fire = _schedule_fire_time(entry, now_local.date())
    if fire is None or now_local < fire:
        return None
    cutoff = now_local.replace(hour=SCHEDULE_CATCHUP_HOUR,
                               minute=SCHEDULE_CATCHUP_MINUTE,
                               second=0, microsecond=0)
    return "fire" if now_local < cutoff else "missed"


def scheduled_job_id(day):
    """Deterministic id for a scheduled firing (the same id the
    Actions fallback's skip-check looks for). One scheduled sweep
    per day by design — the id carries no entry id."""
    return f"{SCHEDULED_JOB_PREFIX}{day.isoformat()}"


def check_schedule(schedule, handled_ids, missed_job_ids, now_utc):
    """Pure core of the scheduler check. `handled_ids` are job ids
    already in queue.json or claimed; `missed_job_ids` are jobs
    already marked missed. Returns (to_enqueue, to_mark_missed):
    lists of (entry, job_id). A restart mid-cycle, a second worker,
    or a re-run of the check can never double-fire: an id that is
    already handled or already marked is skipped."""
    to_enqueue, to_mark = [], []
    for entry in schedule:
        if not isinstance(entry, dict):
            continue
        try:
            tz = ZoneInfo(entry.get("tz") or "Africa/Cairo")
        except Exception:
            print(f"check_schedule: bad tz {entry.get('tz')!r}; skipping "
                  f"entry {entry.get('id')}", file=sys.stderr, flush=True)
            continue
        now_local = now_utc.astimezone(tz)
        decision = schedule_decision(entry, now_local)
        if decision is None:
            continue
        job_id = scheduled_job_id(now_local.date())
        if job_id in handled_ids:
            continue
        if decision == "fire":
            to_enqueue.append((entry, job_id))
        elif job_id not in missed_job_ids:
            to_mark.append((entry, job_id))
    return to_enqueue, to_mark


def load_schedule():
    p = BUS / SCHEDULE_FILE
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text())
    except Exception as e:
        print(f"load_schedule: {type(e).__name__}: {e}",
              file=sys.stderr, flush=True)
        return []
    if not isinstance(data, list):
        print("load_schedule: schedule is not a list; ignoring",
              file=sys.stderr, flush=True)
        return []
    return [e for e in data if isinstance(e, dict)]


def run_schedule_check(now_override=None):
    """Enqueue due scheduled jobs; mark missed ones explicitly.
    Runs at the top of every poll cycle, right after sync_bus, so
    the queue read is fresh. Note the R6 edge case: while a job is
    executing, no cycle runs — a >24 h job would delay the next
    day's check. The catch-up rule covers the realistic case (a job
    finishing after 08:15 but before 09:30 still fires today; after
    09:30 the miss is marked, never silently skipped), and a sweep
    running past 24 h is itself a failure the heartbeat exposes."""
    schedule = load_schedule()
    if not schedule:
        return
    now_utc = now_override or datetime.now(timezone.utc)
    queue = read_queue()
    if QUEUE_ERROR:
        # A malformed queue.json must never be overwritten with a
        # truncated list — skip the check; the heartbeat already
        # carries the parse error (INS-R3-09).
        print("run_schedule_check: queue.json unreadable; skipping",
              file=sys.stderr, flush=True)
        return
    handled = {str(j.get("id", "")) for j in queue}
    claims_dir = BUS / "queue" / "claims"
    if claims_dir.exists():
        handled |= {f.name[:-len(".json")]
                    for f in claims_dir.glob("*.json")}
    missed = {f"sched-{f.name[len('missed-'):-len('.json')]}"
              for f in (BUS / "queue").glob("missed-*.json")}
    to_enqueue, to_mark = check_schedule(schedule, handled, missed,
                                          now_utc)
    for entry, job_id in to_enqueue:
        queue.append({"id": job_id, "job": entry["job"],
                      "added": now()})
        (BUS / "queue" / "queue.json").write_text(
            json.dumps(queue, indent=1))  # no trailing newline:
        # matches the existing queue.json byte style exactly
        push_bus(f"schedule {job_id}")
        print(f"run_schedule_check: enqueued {job_id}: {entry['job']}",
              flush=True)
    for entry, job_id in to_mark:
        date = job_id[len(SCHEDULED_JOB_PREFIX):]
        marker = BUS / "queue" / f"missed-{date}.json"
        marker.write_text(json.dumps(
            {"job_id": job_id, "job": entry["job"], "at": now(),
             "worker": os.uname().nodename,
             "reason": "scheduled fire missed: worker had not enqueued "
                       "by the 09:30 Cairo catch-up cutoff — no "
                       "post-open sweep; see the Actions fallback run "
                       "or dispatch manually"}, indent=1))
        push_bus(f"missed scheduled sweep {job_id}")
        print(f"run_schedule_check: marked missed {job_id}", flush=True)


def _ensure_update_checkout():
    """D2: the code checkout is the release branch, never main tip.
    Full clone, not --depth 1 — the fast-forward guard in
    self_update needs history (a shallow clone has no ancestry
    to check). Incremental fetches after the first are cheap."""
    if not CODE.exists():
        sh(f"git clone --branch {UPDATE_BRANCH} --single-branch "
           f"https://github.com/{ORG}/borsagator {CODE}", timeout=300)
    return CODE


def update_checkout_sha():
    r = sh(f"git -C {CODE} rev-parse HEAD", timeout=30)
    return r.stdout.strip() if r.returncode == 0 else ""


def registry():
    # D2: templates come from the release-branch checkout that
    # self_update maintains — never main tip, never the low-trust
    # queue branch (INS-R3-02). No pull here: self_update runs
    # first each cycle and is the only place the checkout moves.
    _ensure_update_checkout()
    return json.loads((CODE / "registry" / "tools.json").read_text())


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
        # Issue #66 (R4): honour the orchestrator's trailing filters,
        # exactly as scripts/orchestrate.py applies them — market=EGX /
        # market=US / no-agent. Without this a worker sweep-lite runs
        # 29 tools; with market=EGX it must run the same 14 the
        # Actions sweep runs. An unknown filter fails closed (empty
        # plan, like the orchestrator's exit 2) — a wrong sweep must
        # never run silently.
        for tok in parts[2:]:
            if tok.startswith("market="):
                mkt = tok.split("=", 1)[1].upper()
                sel = [(t, tk) for t, tk in sel
                       if mkt in [m.upper()
                                  for m in tools[t].get("markets", [])]]
            elif tok == "no-agent":
                sel = [(t, tk) for t, tk in sel
                       if tools[t].get("category") != "agent"]
            else:
                return []
    else:
        return []
    # Panel round 2: a job string reaches shell command templates via
    # {ticker}; only registry tool ids and allowlisted tickers pass.
    return [(t, tk) for t, tk in sel
            if t in tools and TICKER_RE.match(tk)]


def run_tool(tool, ticker, template, ref=None, repo_name=None):
    # D2 (issue #65): a tool runs ONLY at its registry-pinned SHA.
    # No pull of the runner's branch tip, no fallback to tip: an
    # unreachable ref fails the tool loudly ("ref-unavailable") and
    # the job continues without it — unreviewed code never runs
    # with the keys in its environment. The repo comes from the
    # registry, not the tool id (financial-roberta's repo is
    # roberta-sentiment-runner; the old id-derived URL could never
    # clone it).
    repo = RUNNERS / tool
    # Issue #147: clear the previous run's results BEFORE any early
    # return. A ref failure (ref-unpinned / clone-failed /
    # ref-unavailable) used to return while the old results/ was
    # still in place, and _execute then archived those stale files
    # as the current run's (probe 003: byte-identical CSV/log/
    # summary under a ref-unavailable manifest). The clear is a
    # no-op when the repo/results do not exist yet.
    results = repo / "results"
    sh(f"rm -rf {results}", timeout=60)
    if not ref or not re.fullmatch(r"[0-9a-f]{40}", ref):
        return "ref-unpinned", ""
    url = f"https://github.com/{ORG}/{repo_name or tool + '-runner'}"
    if not repo.exists():
        if sh(f"git clone --depth 1 {url} {repo}",
               timeout=600).returncode != 0:
            return "clone-failed", ""
    # Fetch exactly the pinned commit (GitHub serves arbitrary SHAs
    # for public repos): shallow first, full fetch as fallback.
    if sh(f"git -C {repo} fetch --depth 1 origin {ref}",
          timeout=180).returncode != 0:
        if sh(f"git -C {repo} fetch origin {ref}",
              timeout=180).returncode != 0:
            return "ref-unavailable", ""
    if sh(f"git -C {repo} checkout {ref}",
          timeout=120).returncode != 0:
        return "ref-unavailable", ""
    venv = VENVS / tool
    py = venv / "bin" / "python"
    if not py.exists():
        sh(f"python3 -m venv {venv}", timeout=300)
        req = repo / "requirements.txt"
        if req.exists():
            sh(f"{venv}/bin/pip install -q -r {req}", timeout=1800)
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


def push_archive(arch, attempts=3):
    """Push the archive clone with bounded fetch+rebase retry
    (issue #67, R5: a dropped merge push is a sweep with no digest
    and no ensemble, invisible until the watch). The local commit
    is a single fleet+merge commit, so a rebase replay is safe; a
    conflicting rebase aborts and the push fails loudly. Returns
    True on success."""
    for attempt in range(1, attempts + 1):
        if sh(f"git -C {arch} push origin archive",
              timeout=300).returncode == 0:
            return True
        if attempt == attempts:
            break
        print(f"push_archive: push failed (attempt {attempt}); "
              f"fetching and rebasing", flush=True)
        if sh(f"git -C {arch} fetch origin archive",
              timeout=180).returncode != 0:
            return False
        if sh(f"git -C {arch} rebase origin/archive",
              timeout=180).returncode != 0:
            sh(f"git -C {arch} rebase --abort", timeout=60)
            return False
    return False


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
    # INS-R3-01: the slug reaches shell strings below — reduce it to
    # a safe alphabet so a crafted job string cannot inject commands
    # ($(…), backticks, ;) into the publish step, which runs even
    # for jobs that failed parsing.
    slug = re.sub(r"[^a-z0-9]+", "-", job["job"].lower()).strip("-")[:60]
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d/%H%M%S")
    dest = arch / "worker-runs" / f"{ts}__{slug}__{job['id']}"
    sh(f"mkdir -p {dest} && cp -r {results_dir}/. {dest}/", timeout=300)
    # Issue #67: the merge stages under results_dir/_merge_out — it
    # is not a fleet result and must not ride into worker-runs/.
    sh(f"rm -rf {dest}/_merge_out", timeout=60)
    (dest / "manifest.json").write_text(json.dumps(manifest, indent=1))
    # Issue #67: a merged sweep rides the SAME commit as its fleet
    # (one commit, one push): copy the merge's sweeps/ tree to the
    # archive root alongside worker-runs/.
    merge_out = Path(results_dir) / "_merge_out"
    if merge_out.is_dir():
        sh(f"cp -r {merge_out}/. {arch}/", timeout=300)
    # Issue #91: keep a stable pointer to the newest harvest per EGX
    # code at harvest/<CODE>.json on this branch. GitHub Actions
    # runs have no local harvest, so fetch_feed.py fetches the
    # pointer from the public repo; worker-runs/ keeps the full
    # timestamped history. Sources: a successful harvest-egx job's
    # own output, or the harvest-pointer/ stash _execute leaves
    # when a news run used the local harvest cache.
    ptr_src = []
    if job["job"].startswith("harvest-egx"):
        parts = job["job"].split()
        code = parts[1].upper().replace(".CA", "") if len(parts) > 1 else ""
        cand = results_dir / "egx-harvest" / "results" / "disclosures.json"
        if manifest.get("tools", {}).get("egx-harvest") == "ok" \
                and TICKER_RE.match(code) and cand.exists():
            ptr_src.append((code, cand))
    stash = results_dir / "harvest-pointer"
    if stash.is_dir():
        for f in sorted(stash.glob("*.json")):
            ptr_src.append((f.stem.upper(), f))
        copied = dest / "harvest-pointer"
        if copied.exists():
            sh(f"rm -rf {copied}", timeout=60)  # plumbing, not a result
    if ptr_src:
        hdir = arch / "harvest"
        hdir.mkdir(parents=True, exist_ok=True)
        for code, src in ptr_src:
            (hdir / f"{code}.json").write_bytes(src.read_bytes())
    # Commit message via a file: job text never enters a shell string.
    msg_file = arch / ".commit-msg"
    msg_file.write_text(f"worker run {job['id']}: {job['job']}\n")
    sh(f"git -C {arch} add -A && git -C {arch} commit -F {msg_file}",
       timeout=120)
    msg_file.unlink(missing_ok=True)
    return push_archive(arch)


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
    script = CODE / "worker" / "egx_harvest.py"
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
    # INS-R3-07 (partial): a stale cache may still serve after a
    # failed refresh — matching is content-based, so old disclosures
    # mostly match old items — but never past 72 h, and never
    # silently.
    if cache.exists():
        age_h = (time.time() - cache.stat().st_mtime) / 3600
        if age_h < 72:
            print(f"ensure_harvest: refresh failed; serving stale "
                  f"cache for {code} ({age_h:.1f} h old)", flush=True)
            return cache
        print(f"ensure_harvest: cache for {code} is {age_h:.1f} h "
              f"old — refusing to serve it", flush=True)
    return None


CLAIM_REFRESH_SECONDS = 1200  # 20 min (INS-R3-03)


def execute(job):
    """Run a claimed job while a background thread keeps the claim's
    timestamp fresh (INS-R3-03): reclaim_stale_claims is age-only
    (6 h), but a full sweep can legitimately run far longer — without
    refresh, a second worker could reclaim and duplicate it."""
    import threading
    stop = threading.Event()

    def refresh():
        c = BUS / "queue" / "claims" / f"{job['id']}.json"
        while not stop.wait(CLAIM_REFRESH_SECONDS):
            try:
                c.write_text(json.dumps(
                    {"worker": os.uname().nodename, "at": now(),
                     "job": job["job"]}))
                push_bus(f"claim refresh {job['id']}")
            except Exception:
                pass

    t = threading.Thread(target=refresh, daemon=True)
    t.start()
    try:
        _execute(job)
    finally:
        stop.set()


def maybe_merge(job, workdir, manifest, plan):
    """Issue #67: post-sweep merge hook. Runs scripts/merge.py
    (shared module, stdlib-only) on the just-finished sweep's local
    OUT/<job-id> tree, before publish() archives fleet + merge in
    one commit. Fires only for sweep / sweep-lite plans — category
    and single-tool runs have no ensemble to build. A merge failure
    or refusal must NEVER lose the fleet: it writes merge_error.txt
    in the run dir, records manifest["merge"], and returns False so
    _execute still publishes the fleet. Never raises."""
    kind = (job.get("job") or "").split()
    if not kind or kind[0] not in ("sweep", "sweep-lite") or not plan:
        return False
    merge_script = CODE / "scripts" / "merge.py"
    err_file = Path(workdir) / "merge_error.txt"
    try:
        env = {k: v for k, v in os.environ.items()
               if k not in ENV_DENY_FOR_TOOLS}
        cmd = [sys.executable, str(merge_script),
               "--job", job["job"], "--run-dir", str(workdir),
               "--registry", str(CODE / "registry" / "tools.json"),
               "--weights", str(CODE / "ledger" / "weights.json"),
               "--ensemble", str(CODE / "scripts" / "ensemble.py"),
               "--release-sha", update_checkout_sha(),
               "--claim-id", str(job.get("id", "")),
               "--worker", os.uname().nodename,
               "--plan", ",".join(t for t, _ in plan),
               "--out", str(Path(workdir) / "_merge_out"),
               "--error-file", str(err_file)]
        # JOB_SCHEDULED (#67 §8 item 9): the cycle sets the repo
        # variable to `sweep-lite POUL.CA market=EGX` if unset. The
        # worker records what it was told via the environment, never
        # a guess — an unset value is recorded as unchecked.
        scheduled = os.environ.get("JOB_SCHEDULED")
        if scheduled:
            cmd += ["--job-scheduled", scheduled,
                    "--job-scheduled-checked"]
        # Issue #146: maybe_merge calls subprocess.run directly, not
        # sh() — apply the same final-boundary guard here.
        _assert_no_denied(env)
        proc = subprocess.run(cmd, env=env, capture_output=True,
                              text=True, timeout=3600)
        if proc.stdout.strip():
            print(proc.stdout, end="", flush=True)
        if proc.stderr.strip():
            print(proc.stderr, end="", file=sys.stderr, flush=True)
        if proc.returncode != 0:
            detail = err_file.read_text(
                encoding="utf-8", errors="replace").strip() \
                if err_file.is_file() else \
                f"merge.py exited {proc.returncode}"
            manifest["merge"] = {"status": "failed",
                                 "detail": detail[:500]}
            return False
        # The merge writes exactly one merge-manifest.json; find it
        # under any date dir.
        found = list((Path(workdir) / "_merge_out").rglob(
            "merge-manifest.json")) if \
            (Path(workdir) / "_merge_out").is_dir() else []
        if found:
            mm = json.loads(found[0].read_text())
            manifest["merge"] = {"status": mm.get("merge"),
                                 "sweep_dir": mm.get("sweep_dir")}
            return True
        manifest["merge"] = {"status": "failed",
                             "detail": "merge exited 0 but no "
                                       "merge-manifest.json found"}
        return False
    except Exception as e:  # noqa: BLE001 - the fleet must publish
        try:
            err_file.write_text(f"merge hook failed: "
                                f"{type(e).__name__}: {e}\n")
        except OSError:
            pass
        manifest["merge"] = {"status": "failed",
                             "detail": f"merge hook failed: "
                                       f"{type(e).__name__}: {e}"[:500]}
        return False


def _execute(job):
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
    # D2: each tool runs only at its registry-pinned SHA.
    refs = {t["id"]: t.get("ref") for t in reg["tools"]}
    repos = {t["id"]: t.get("repo", f"{t['id']}-runner")
             for t in reg["tools"]}
    for tool, ticker in plan:
        status, log = run_tool(tool, ticker, templates.get(tool, ""),
                               refs.get(tool), repos.get(tool))
        dest = workdir / tool
        src = RUNNERS / tool / "results"
        if status == "ok":
            if src.exists():
                sh(f"mkdir -p {dest} && cp -r {src}/. {dest}/",
                   timeout=120)
        else:
            # Issue #147: a failed tool archives an EMPTY results
            # dir — never another run's outputs as this run's.
            # run_tool already cleared results/ before the run, so
            # anything left in src is at most this run's partial
            # output; it stays on the worker (the next run clears
            # it) and is never copied into the run dir, where the
            # merge would scan it into digest metrics and the
            # ensemble would read it as data. The failure itself is
            # recorded in the manifest and in <tool>.log.
            dest.mkdir(parents=True, exist_ok=True)
        (workdir / f"{tool}.log").write_text(log)
        manifest["tools"][tool] = status
        if tool == "news-disclosure" and ticker.upper().endswith(".CA"):
            # Issue #91: stash the harvest this run used (run_tool
            # may have refreshed it via ensure_harvest) so publish()
            # can refresh the archive-branch pointer for Actions.
            code = ticker.upper().split(".")[0]
            cache = ROOT / "harvest" / f"{code}.json"
            if cache.exists():
                stash = workdir / "harvest-pointer"
                stash.mkdir(parents=True, exist_ok=True)
                (stash / f"{code}.json").write_bytes(cache.read_bytes())
    manifest["finished"] = now()
    # Issue #67: post-sweep merge hook — fleet + merge publish in
    # one commit. A merge failure never loses the fleet (see
    # maybe_merge): publish() below still runs.
    maybe_merge(job, workdir, manifest, plan)
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
    """Adopt the release branch, never main tip (D2, issue #65).

    Promotion is a deliberate act: a reviewed main commit is
    fast-forwarded onto `worker-release`, and the worker only ever
    adopts a tip that is a fast-forward descendant of the checkout
    it already runs (or exactly GATOR_PIN_SHA when set). A
    force-pushed / rewritten tip is refused and reported — the
    worker keeps running the old, reviewed code. Fixes still reach
    the worker over the bus with no relaunch; what changes is that
    only reviewed, promoted code can arrive.
    (Replaces the old pull-from-main-tip hook.)
    Promotion PRs must come from a frozen `promote/<sha>` branch
    pinned to the exact reviewed SHA — never from live `main` —
    and are gated by scripts/promote.py + docs/promotion.md
    (issue #145). This guard alone cannot tell a reviewed
    descendant from an unreviewed one; the frozen candidate is
    what makes the descendant reviewed."""
    global UPDATE_ERROR
    _ensure_update_checkout()
    if not CODE.exists():
        UPDATE_ERROR = "update checkout missing after clone"
        return
    if sh(f"git -C {CODE} fetch origin {UPDATE_BRANCH}",
          timeout=120).returncode != 0:
        UPDATE_ERROR = "fetch of release branch failed; keeping running code"
        return
    tip = sh(f"git -C {CODE} rev-parse FETCH_HEAD",
             timeout=30).stdout.strip()
    if not tip:
        UPDATE_ERROR = "release branch tip unreadable; keeping running code"
        return
    if UPDATE_PIN and tip != UPDATE_PIN:
        UPDATE_ERROR = (f"release tip {tip[:12]} != pinned "
                        f"{UPDATE_PIN[:12]}; keeping running code")
        return
    cur = update_checkout_sha()
    if cur and tip != cur:
        # Fast-forward only: a rewritten history is refused even if
        # the branch moved. (Needs the full clone from
        # _ensure_update_checkout — shallow history has no ancestry.)
        if sh(f"git -C {CODE} merge-base --is-ancestor HEAD {tip}",
              timeout=60).returncode != 0:
            UPDATE_ERROR = (f"release tip {tip[:12]} is not a "
                            f"descendant of running {cur[:12]}; refusing")
            return
    if sh(f"git -C {CODE} checkout {tip}", timeout=60).returncode != 0:
        UPDATE_ERROR = f"checkout of release tip {tip[:12]} failed"
        return
    UPDATE_ERROR = None
    src = CODE / "worker" / "worker.py"
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
            # Issue #66: the worker owns the clock — check the
            # schedule every cycle, before claiming, so a due
            # firing is enqueued even on a cycle that then claims
            # an older job first.
            run_schedule_check()
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
