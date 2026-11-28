#!/usr/bin/env python3
"""Borsagator worker agent (issue #33) — local execution mode.

The worker's control bus is the borsagator repo itself:
- Jobs arrive as entries in queue/queue.json on the `queue` branch:
  {"id": "...", "job": "run yahooquery POUL.CA", "added": "<iso>"}
- The worker claims a job by committing queue/claims/<id>.json and
  pushing; a push conflict means another worker won — skip.
- A job that publishes successfully is recorded in
  queue/done/<id>.json (archive commit); done jobs are never
  re-claimed, even after the 6 h claim reclamation (issue #149).
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

Issue #66 extension (Muhammad, 2026-11-18): ALL scheduling moves to
the worker. The schedule mechanism is generic: an entry is either
the legacy daily form (above) or an interval form (`cadence`:
"hourly" / "interval") with a deterministic per-slot job id
(`<prefix><YYYY-MM-DDTHHMMZ>`), a missed marker per missed slot, and
catch-up: the latest missed slot runs ONCE at the next poll (and the
lateness is marked); older missed slots are marked, never run and
never silently dropped. Two interval entries run the ledger guard
(hourly at :47 UTC, job `ledger-guard`) and its watchdog (every
30 min UTC, job `ledger-watchdog`) that used to be the GitHub
schedules in ledger-guard.yml / ledger-guard-watchdog.yml. Each
GitHub schedule line is retired only after its worker equivalent
has fired correctly twice (counts tracked on issue #66).
"""
import hashlib
import uuid
import json
import math
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ROOT = Path(os.environ.get("GATOR_ROOT", "/opt/gator"))
BUS = ROOT / "bus"            # borsagator clone (token remote), queue branch
# Issue #216: the done-receipt outbox lives OUTSIDE the resettable bus
# checkout, so a receipt survives sync_bus (reset --hard) and restarts
# until its delivery to the bus is VERIFIED. BUS_PUB is a DEDICATED
# publication clone used only for done markers: the general bus clone
# has a live claim-refresh thread during job execution, and git's
# index lock serializes individual commands, not a whole
# fetch/reset/write/add/commit/push transaction - so marker
# publication must not share that clone.
PENDING_DONE = ROOT / "pending-done"
# PR #515 review (#499 follow-up): durable local copies of guard
# envelope records, outside the resettable bus clone (the #216
# pattern) — a record whose bus push was rejected survives
# sync_bus and restarts here until its publication on
# origin/queue is verified.
PENDING_ENVELOPES = ROOT / "pending-envelopes"
# #231: pre-effect intents and fallback completion receipts. This is
# outside both resettable clones, NOT an independent failure domain.
JOB_STATE = ROOT / "job-state"
BUS_PUB = ROOT / "bus-pub"      # dedicated done-marker publication clone
PUSH_ATTEMPTS = 5        # reconcile-and-retry budget at mark time
DRAIN_ATTEMPTS = 3       # smaller budget for the per-cycle drain
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


def _sha256_file(path):
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except Exception:
        return ""


# Issue #160: the code the RUNNING process loaded, hashed once at
# import. The heartbeat used to report update_checkout_sha() — the
# /opt/gator/release checkout's HEAD — so after a checkout of the new
# tip a failed me.write_bytes / os.execv (swallowed by
# `except Exception: pass`) left the heartbeat claiming the new SHA
# while old code ran. Hashing the file at heartbeat time would still
# lie in that window (a successful write + failed execv leaves new
# bytes on disk under an old process); the import-time hash is the
# bytes this process actually loaded, and a successful execv re-imports
# (and re-hashes) in the new process.
RUNNING_CODE_SHA = _sha256_file(Path(__file__).resolve())


def running_code_sha():
    """SHA-256 of the running worker.py bytes (issue #160)."""
    return RUNNING_CODE_SHA
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


def sh_group(cmd, cwd=None, env=None, timeout=3600):
    """Like sh(), but the child runs in its own session (process
    group) and a timeout kills the WHOLE group before raising
    (issue #446): with shell=True, subprocess.run's timeout kills
    only the shell, so a long-lived child's own subprocesses (a
    harness's runners) would survive against a run directory the
    caller is about to publish. The kill is verified, not assumed
    (issue #450): after SIGTERM the group must test empty, and
    anything left is SIGKILLed. Same env discipline as sh(): a
    supplied env is the COMPLETE subprocess env (#146)."""
    if env is None:
        e = dict(os.environ)
    else:
        _assert_no_denied(env)
        e = dict(env)
    proc = subprocess.Popen(cmd, shell=True, cwd=cwd, env=e,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True,
                            start_new_session=True)
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        # start_new_session made the child a group leader, so its
        # pid IS the pgid; everything it spawned shares the group.
        out, err = "", ""
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            out, err = proc.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            pass
        # Issue #450: the leader being reaped does NOT prove the
        # group is empty — a descendant that ignores SIGTERM and
        # detached its descriptors lets communicate() return while
        # it lives on. Verify the group is gone; SIGKILL whatever
        # remains and poll until it is actually empty (bounded —
        # a zombie member can hold the entry briefly; it is dead,
        # and the poll gives up rather than hanging).
        try:
            os.killpg(proc.pid, 0)
            group_alive = True
        except ProcessLookupError:
            group_alive = False
        if group_alive:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            for _ in range(50):
                try:
                    os.killpg(proc.pid, 0)
                except ProcessLookupError:
                    break
                time.sleep(0.1)
            try:
                out, err = proc.communicate(timeout=5)
            except Exception:
                pass
        raise subprocess.TimeoutExpired(cmd, timeout, output=out,
                                        stderr=err)
    return subprocess.CompletedProcess(cmd, proc.returncode, out,
                                       err)


def now():
    return datetime.now(timezone.utc).isoformat()


def git_bus(*args, timeout=120):
    return sh(f"git -C {BUS} " + " ".join(args), timeout=timeout)


def sync_bus():
    if not BUS.exists():
        url = os.environ["GATOR_BUS_URL"]
        if sh(f"git clone --branch queue --single-branch {url} {BUS}",
              timeout=300).returncode != 0:
            raise RuntimeError("sync_bus: clone failed; refusing stale queue")
    for command, timeout in (("fetch origin queue", 120),
                             ("reset --hard origin/queue", 60)):
        if git_bus(command, timeout=timeout).returncode != 0:
            raise RuntimeError(f"sync_bus: {command} failed; "
                               "refusing stale queue")
    git_bus("config user.email worker@borsagator.local", timeout=30)
    git_bus("config user.name borsagator-worker", timeout=30)


def push_bus(message):
    git_bus("add -A", timeout=60)
    if git_bus("commit -m " + json.dumps(message), timeout=60).returncode != 0:
        return False
    return git_bus("push origin queue", timeout=120).returncode == 0


# --- Issue #216: durable done-marker publication ----------------------
# All publication goes through the dedicated BUS_PUB clone (never the
# general BUS clone, whose claim-refresh thread is live during job
# execution), and a receipt is deleted ONLY after its content is
# verified on origin/queue. _mark_done, flush_pending_done and the
# claim-refresh thread never touch PENDING_DONE or BUS_PUB from more
# than one thread: both callers run on the main loop thread, and the
# refresh thread touches only BUS - that is what makes the fixed
# .tmp name and the fetch/reset/write/add/commit/push sequence safe.


def _fsync_dir(path):
    dfd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(dfd)
    finally:
        os.close(dfd)


def _pub_git(*args, timeout=120):
    return sh(f"git -C {shlex.quote(str(BUS_PUB))} " + " ".join(args),
              timeout=timeout)


def _pub_ok(*args, timeout=120):
    return _pub_git(*args, timeout=timeout).returncode == 0


def _ensure_pub_clone():
    """True only when the dedicated publication clone exists and is
    configured; every git operation status is checked (the temp-dir
    cleanup is best-effort: a failed cleanup makes the next clone
    attempt fail loudly rather than silently). Uses the SAME
    credential mechanism as the general bus clone: GATOR_BUS_URL in
    the worker's own environment takes precedence. When unset or
    empty, BUS's origin remote is used with a warning on stderr (the
    URL is never logged). If neither source is available, returns
    False with a diagnostic. Source selection happens only when
    creating BUS_PUB; an existing clone is checked and reused. The
    credential URL is stored in this clone's config just like in BUS,
    and the clone must be protected the same way. The clone is
    created atomically - cloned into a sibling temp
    dir, then renamed - so a failed clone never leaves a half-created
    BUS_PUB. An existing BUS_PUB that fails a git check is retained
    and reported, never auto-deleted: a transient read/permission
    error is not proof of disposable corruption. Assumes the existing
    deployment invariant of ONE worker process per GATOR_ROOT (the
    general BUS clone already relies on it)."""
    if BUS_PUB.exists():
        if not _pub_ok("rev-parse --git-dir", timeout=30):
            print(f"_ensure_pub_clone: {BUS_PUB} exists but is not a "
                  f"readable git clone; left in place for a human",
                  file=sys.stderr, flush=True)
            return False
    else:
        tmp = BUS_PUB.parent / (BUS_PUB.name + ".tmp-clone")
        if tmp.exists():
            sh(f"rm -rf {shlex.quote(str(tmp))}", timeout=60)
        url = os.environ.get("GATOR_BUS_URL")
        if not url:
            # Follow-up (found by the repo's own test_worker_149): do not
            # fail closed merely because the env var is unset when the
            # bus clone already exists — BUS was cloned from this same
            # URL, so its origin remote is the bus URL (token included,
            # exactly as the env-var path stores it in BUS_PUB's config).
            r = git_bus("remote get-url origin", timeout=30)
            url = r.stdout.strip() if r.returncode == 0 else ""
            if url:
                print("_ensure_pub_clone: WARNING: GATOR_BUS_URL unset or "
                      "empty; using BUS origin remote for publication clone",
                      file=sys.stderr, flush=True)
        if not url:
            print("_ensure_pub_clone: no bus URL (GATOR_BUS_URL unset "
                  "and BUS has no origin remote)",
                  file=sys.stderr, flush=True)
            return False
        if sh(f"git clone --branch queue --single-branch "
              f"{shlex.quote(url)} {shlex.quote(str(tmp))}",
              timeout=300).returncode != 0:
            if tmp.exists():
                sh(f"rm -rf {shlex.quote(str(tmp))}", timeout=60)
            return False
        os.replace(tmp, BUS_PUB)
    if not _pub_ok("config user.email worker@borsagator.local", timeout=30):
        return False
    return _pub_ok("config user.name borsagator-worker", timeout=30)


def _pub_remote_record(rel):
    """Tri-state read of the marker on origin/queue in the publication
    clone (after a successful fetch): (True, content) when present,
    (True, None) when VERIFIED absent, (False, None) when the read
    itself failed. Absence must be proven, never inferred from an
    error: an unreadable existing marker must not authorize an
    overwrite or a receipt deletion (issue #216)."""
    r = _pub_git("ls-tree origin/queue -- " + shlex.quote(rel), timeout=60)
    if r.returncode != 0:
        return (False, None)
    if not r.stdout.strip():
        return (True, None)
    r = _pub_git("show " + shlex.quote(f"origin/queue:{rel}"), timeout=60)
    if r.returncode != 0:
        return (False, None)
    return (True, r.stdout)


def _write_receipt(path, text):
    """Crash-durable receipt write: temp file in the same directory,
    fsync, atomic os.replace, then fsync the directory so the rename
    itself is durable. A crash leaves either the old receipt or the
    new one, never a partial file. The fixed .tmp name is safe
    because receipts are only ever written from the main loop
    thread (see the section header)."""
    tmp = path.parent / (path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    _fsync_dir(path.parent)


RECEIPT_KEYS = {"worker", "at", "job", "archive", "id"}

# Last-resort diagnostics only. Production execution first persists an
# intent, so a restart still gates an ambiguous effect if all subsequent
# writes and bus delivery fail. This set alone is not durable.
_UNDELIVERED = set()
# A drain runs after sync_bus, so BUS may not yet contain a marker
# verified during this cycle. Keep that delivery gated until restart;
# the durable bus marker is recovered by startup sync then.
_VERIFIED_DONE = set()


def _intent_path(job_id):
    return JOB_STATE / f"{job_id}.intent"


def _completion_dirs():
    return (PENDING_DONE, JOB_STATE)


def _forget_completion(path, job_id):
    """Only after exact remote verification. Keep the completed receipt
    until intent deletion is durable, so interrupted cleanup can retry."""
    _VERIFIED_DONE.add(job_id)
    try:
        intent = _intent_path(job_id)
        if JOB_STATE.exists():
            intent.unlink(missing_ok=True)
            _fsync_dir(JOB_STATE)
        path.unlink()
        _fsync_dir(path.parent)
    except OSError:
        pass  # durable residue remains safe to replay


def _ensure_durable_dir(path):
    """Persist each newly created ancestor, not just the leaf entry."""
    if not path.exists():
        _ensure_durable_dir(path.parent)
        path.mkdir(exist_ok=True)
    _fsync_dir(path.parent)


def _begin_execution(job):
    """Write-ahead uncertainty gate, NEVER a done record. Failure to
    establish durability refuses execution. Existing evidence refuses
    re-entry, including direct _execute callers. One worker process per
    ROOT is required, as for the existing fixed receipt temp names."""
    # Issue #391: the missing-key case used to raise KeyError on
    # job["job"] inside the durability try below and was misreported
    # as an intent failure; a non-dict job raised AttributeError on
    # job.get above. Refuse both explicitly, with no intent written.
    if not isinstance(job, dict):
        print("_begin_execution: malformed entry (not an object); "
              "REFUSING execution", file=sys.stderr, flush=True)
        return False
    job_id = str(job.get("id", ""))
    if not JOB_ID_RE.fullmatch(job_id):
        return False
    if "job" not in job:
        print(f"_begin_execution {job_id}: no 'job' key; REFUSING "
              "execution (malformed queue entry)",
              file=sys.stderr, flush=True)
        return False
    if _done_or_pending(job_id):
        return False
    try:
        _ensure_durable_dir(JOB_STATE)
        _write_receipt(_intent_path(job_id), json.dumps(
            {"job": job["job"], "started": now()}))
        return True
    except Exception as e:  # noqa: BLE001 - fail closed before effects
        print(f"_begin_execution {job_id}: intent not durable; "
              f"REFUSING execution ({type(e).__name__}: {e})",
              file=sys.stderr, flush=True)
        return False


def _valid_receipt(text, job_id):
    """A receipt is publishable only as a JSON object with string
    worker/at/job/archive/id values under a job-id-safe filename
    (the filename becomes a git path) AND with the id recorded
    inside the receipt equal to the job the filename claims (#233:
    the "job" field holds the job TEXT, not the id, so the literal
    d["job"] == job_id check the issue suggested would reject
    every legitimate receipt - the id is carried in its own field
    instead, and a receipt for job A in file B.json is quarantined
    as .corrupt by flush_pending_done)."""
    if not JOB_ID_RE.match(job_id):
        return False
    try:
        d = json.loads(text)
    except Exception:
        return False
    return (isinstance(d, dict) and d.get("id") == job_id
            and all(isinstance(d.get(k), str) for k in RECEIPT_KEYS))


def _publish_done(job_id, record, attempts=PUSH_ATTEMPTS):
    """Issue #216: publish a done marker against a FRESH queue base.
    Every attempt re-fetches and hard-resets the dedicated
    publication clone to origin/queue, and every git exit status is
    checked. A marker already on origin with identical content IS
    successful delivery (a push whose reply was lost, or a manual
    reconcile with the same bytes); a marker with DIFFERENT content
    (manual reconcile, another writer) is never overwritten and the
    receipt never deleted - it stays pending and loud for a human.
    An empty staged diff (diff --cached --quiet exit 0) is
    distinguished from a diff ERROR (exit > 1) and from a real
    staged change (exit 1); only a verified-identical remote record
    closes an empty diff. After a push, delivery is accepted only
    when a fresh fetch shows OUR bytes on origin/queue. Never
    force-pushes. claim() deliberately fails closed on ANY push
    conflict (a competing claim or an unrelated queue write):
    reconcile-retrying there could steal a claim another worker
    legitimately holds, so bounded reconcile-retry belongs only
    here, in done-marker publication."""
    rel = f"queue/done/{job_id}.json"
    for attempt in range(attempts):
        try:
            if attempt:
                time.sleep(min(2 ** attempt, 30))
            if not _ensure_pub_clone():
                continue
            if not _pub_ok("fetch origin queue", timeout=120):
                continue
            if not _pub_ok("reset --hard origin/queue", timeout=60):
                continue
            ok_read, remote = _pub_remote_record(rel)
            if not ok_read:
                continue  # cannot prove absence: never risk overwrite
            if remote == record:
                return True  # verified identical on origin
            if remote is not None:
                print(f"_publish_done {job_id}: CONFLICT - the bus "
                      f"already carries a DIFFERENT done record; the "
                      f"receipt stays pending for manual "
                      f"reconciliation", file=sys.stderr, flush=True)
                return False
            p = BUS_PUB / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(record)
            if not _pub_ok("add " + shlex.quote(rel), timeout=60):
                continue
            d = _pub_git("diff --cached --quiet -- " + shlex.quote(rel),
                         timeout=60)
            if d.returncode == 0:
                # Nothing staged although the file was absent from
                # origin: only explainable as an identical marker
                # having landed in the meantime. Verify, never assume.
                if _pub_ok("fetch origin queue", timeout=120):
                    ok_read, remote = _pub_remote_record(rel)
                    if ok_read and remote == record:
                        return True
                continue
            if d.returncode != 1:
                continue  # diff ERROR: retry fresh
            if not _pub_ok("commit -m " + shlex.quote(f"done {job_id}"),
                           timeout=60):
                continue  # commit ERROR (hook/identity/disk): retry
            if not _pub_ok("push origin queue", timeout=120):
                continue  # non-fast-forward or transport: retry fresh
            # Delivery is claimed only after a fresh fetch shows OUR
            # bytes on origin/queue.
            if not _pub_ok("fetch origin queue", timeout=120):
                continue
            ok_read, remote = _pub_remote_record(rel)
            if not ok_read:
                continue  # cannot verify delivery: keep the receipt
            if remote == record:
                return True
            if remote is not None:
                print(f"_publish_done {job_id}: post-push verification "
                      f"found DIFFERENT remote content; the receipt "
                      f"stays pending for manual reconciliation",
                      file=sys.stderr, flush=True)
                return False
        except Exception as e:  # noqa: BLE001 - retry within budget
            print(f"_publish_done {job_id} attempt {attempt + 1}: "
                  f"{type(e).__name__}: {e}", file=sys.stderr, flush=True)
    return False


def _receipt_paths(job_id):
    """Any local completion evidence for job_id - a valid pending
    receipt OR a quarantined corrupt one. A corrupt receipt is still
    evidence the job RAN TO COMPLETION here: it must keep blocking
    local re-execution until a human resolves it (issue #216)."""
    return [f for directory in _completion_dirs()
            for f in directory.glob(f"{job_id}.json*")
            if f.suffix in (".json", ".corrupt")]


def flush_pending_done(attempts=DRAIN_ATTEMPTS, budget_seconds=300):
    """#216/#231: drain BOTH completion stores after every sync_bus.
    Intents alone are never published. Replay uses the saved completion
    bytes only, never _execute or ledger_publish.py.
    A receipt whose job already has a bus record is deleted only when
    the records are verified identical (a hand-reconcile with the same
    bytes, df1b557f); a differing bus record keeps the receipt pending
    and loud. A receipt that fails validation (unparseable, wrong
    value types, unsafe filename, id mismatching the filename) is
    quarantined to *.corrupt - never
    published, never silently dropped, and it KEEPS blocking local
    re-execution (see _done_or_pending). A remote read that cannot
    prove absence (git error) skips the receipt this cycle rather
    than risk an overwrite. The drain budget is SOFT: it is checked
    between receipts on a monotonic clock, and one in-flight publish
    can overrun it by its own bounded worst case (attempts x git
    timeouts + backoff, potentially several minutes). Under a
    permanent outage or an unresolved conflict, receipts stay pending
    and surfaced indefinitely - they are never silently dropped, but
    delivery is not guaranteed."""
    # Clear in-memory gates whose marker has since reached the bus
    # (e.g. a hand reconcile); the durable done() gate remains.
    for j in [j for j in _UNDELIVERED if done(j)]:
        _UNDELIVERED.discard(j)
    deadline = time.monotonic() + budget_seconds
    receipts = sorted(f for directory in _completion_dirs()
                      for f in directory.glob("*.json"))
    for f in receipts:
        if time.monotonic() > deadline:
            print("flush_pending_done: soft drain budget reached; "
                  "remaining receipts retry next cycle",
                  file=sys.stderr, flush=True)
            break
        job_id = f.stem
        try:
            record = f.read_text()
        except Exception:  # noqa: BLE001 - left in place, still gates
            print(f"flush_pending_done {job_id}: receipt unreadable; "
                  f"left in place (still blocks local re-execution)",
                  file=sys.stderr, flush=True)
            continue
        if not _valid_receipt(record, job_id):
            print(f"flush_pending_done {job_id}: INVALID receipt "
                  f"quarantined as {f.name}.corrupt (still blocks "
                  f"local re-execution)", file=sys.stderr, flush=True)
            try:
                os.replace(f, f.with_suffix(f.suffix + ".corrupt"))
                _fsync_dir(f.parent)
            except OSError:
                pass
            continue
        try:
            if not (_ensure_pub_clone()
                    and _pub_ok("fetch origin queue", timeout=120)):
                continue  # no remote verdict this cycle
            found, bus_record = _pub_remote_record(
                f"queue/done/{job_id}.json")
        except Exception:  # noqa: BLE001 - no verdict this cycle
            continue
        if not found:
            continue  # cannot prove absence: never risk overwrite
        if bus_record is not None:
            if bus_record == record:
                _UNDELIVERED.discard(job_id)
                _forget_completion(f, job_id)
            else:
                print(f"flush_pending_done {job_id}: bus record differs "
                      f"from the pending receipt; keeping the receipt "
                      f"for manual reconciliation",
                      file=sys.stderr, flush=True)
            continue
        if _publish_done(job_id, record, attempts=attempts):
            _UNDELIVERED.discard(job_id)
            _forget_completion(f, job_id)


QUEUE_ERROR = None  # last queue.json parse error (panel round 3, R3-09)


def heartbeat():
    (BUS / "queue").mkdir(exist_ok=True)
    payload = {"worker": os.uname().nodename, "at": now(),
               "version": "worker-v1",
               # Issue #160: code_sha is the hash of the RUNNING code,
               # not the release checkout's HEAD (update_checkout_sha
               # lies after a failed adopt). checkout_sha keeps the
               # checkout HEAD visible for diagnostics.
               "code_sha": running_code_sha(),
               "code_sha_kind": "sha256-running-bytes",
               "checkout_sha": update_checkout_sha(),
               "update_branch": UPDATE_BRANCH}
    if QUEUE_ERROR:
        # A malformed queue.json must not idle the fleet behind a
        # green heartbeat (INS-R3-09).
        payload["queue_error"] = QUEUE_ERROR
    if UPDATE_ERROR:
        # D2: a refused update must be visible on the bus — stale
        # code is safe code, but silent staleness is not.
        payload["update_error"] = UPDATE_ERROR
    pending = sorted({f.stem for directory in _completion_dirs()
                      for f in directory.glob("*.json")})
    corrupt = sorted({f.name[:-len(".json.corrupt")]
                      for directory in _completion_dirs()
                      for f in directory.glob("*.json.corrupt")})
    if pending:
        payload["pending_done"] = pending
    if corrupt:
        payload["corrupt_done"] = corrupt
    # Issue #391: quarantined malformed queue entries are surfaced
    # here so the skip is observable without another bus push.
    malformed_dir = BUS / "queue" / "malformed"
    malformed = sorted(f.stem for f in malformed_dir.glob("*.json")) \
        if malformed_dir.exists() else []
    if malformed:
        payload["malformed_queue"] = malformed
    # An intent is not completion evidence. It means an attempt may
    # have caused effects. Only completed receipts are auto-replayed.
    uncertain = sorted(f.stem for f in JOB_STATE.glob("*.intent")
                       if f.stem not in pending and f.stem not in corrupt)
    if uncertain:
        payload["uncertain_jobs"] = uncertain
    if _UNDELIVERED:
        # Diagnostic set only; durable intents gate production attempts.
        # Heartbeat delivery itself remains best-effort.
        payload["undelivered_done"] = sorted(_UNDELIVERED)
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


def done(job_id):
    """Issue #149: durable completion state. A job is done only when
    its done record exists — written after a successful publish, and
    never reclaimed. Claims are the mutex, not the done-state."""
    return (BUS / "queue" / "done" / f"{job_id}.json").exists()


def _done_or_pending(job_id):
    """#216/#231: local completion evidence OR a pre-effect intent
    blocks re-entry. An intent can be an interrupted/failed attempt,
    NOT proof of completion; it needs reconciliation, never replay
    as done. Such a job must not be re-executed here after
    claim reclamation while that evidence awaits delivery or
    human resolution. Other hosts cannot see this host's outbox:
    while the marker stays undelivered, a peer may still re-run
    after claim reclamation whether or not this host survives - the
    gate protects this host only."""
    _gdelt_retry_cleanup(job_id)
    return (done(job_id) or job_id in _UNDELIVERED
            or job_id in _VERIFIED_DONE
            or _intent_path(job_id).exists()
            or bool(_receipt_paths(job_id)))


def _mark_done(job, archive_sha, extra=None):
    """#149/#216/#231: mark completion only AFTER a successful effect.
    First stage exact completion bytes in the primary outbox. If that
    write fails, try JOB_STATE with the same crash-durable write, then
    attempt bus publication regardless. A confirmed staged receipt is
    replayable on restart; it never re-executes the job or publisher.

    Production _execute first persists a write-ahead intent. If BOTH
    completion writes and delivery fail, restart retains that intent:
    the outcome is uncertain, NOT done, and requires reconciliation.
    This deliberately trades automatic retries of interrupted/failed
    attempts for local at-most-once admission. It is not exactly-once
    delivery: loss of local storage, older workers without intents,
    concurrent workers sharing ROOT, and peer-host claim reclamation
    remain outside this local gate's guarantee. JOB_STATE is on the
    same filesystem by default, so fallback writes are NOT assumed
    independent. Never turn an intent alone into a done marker.

    Issue #610 item 4c: `extra` carries optional additional record
    fields (e.g. the superseded markers from _mark_superseded). The
    five RECEIPT_KEYS stay strings; _valid_receipt allows extra
    keys, so a superseded record still validates as a receipt."""
    record_dict = {"worker": os.uname().nodename, "at": now(),
                   "job": job["job"], "archive": archive_sha,
                   "id": job["id"]}
    if extra:
        record_dict.update(extra)
    record = json.dumps(record_dict)
    receipt = None
    for directory in _completion_dirs():
        try:
            _ensure_durable_dir(directory)
            candidate = directory / f"{job['id']}.json"
            _write_receipt(candidate, record)
            receipt = candidate
            break
        except Exception as e:  # noqa: BLE001 - try fallback, then bus
            print(f"_mark_done: RECEIPT WRITE FAILED in {directory} "
                  f"for {job['id']} ({type(e).__name__}: {e})",
                  file=sys.stderr, flush=True)
    if _publish_done(job["id"], record):
        _VERIFIED_DONE.add(job["id"])
        _UNDELIVERED.discard(job["id"])
        if receipt is not None:
            _forget_completion(receipt, job["id"])
        else:
            # No replayable receipt exists, but delivery was verified.
            try:
                _intent_path(job["id"]).unlink(missing_ok=True)
                if JOB_STATE.exists():
                    _fsync_dir(JOB_STATE)
            except OSError:
                pass
        return True
    if receipt is None:
        _UNDELIVERED.add(job["id"])
    print(f"_mark_done: delivery not confirmed for {job['id']}; "
          + (f"receipt retained at {receipt}; replayed each cycle"
             if receipt is not None else
             "NO durable completion receipt; any pre-effect intent "
             "is retained, outcome UNCERTAIN; manual reconciliation"),
          file=sys.stderr, flush=True)
    return False


def _mark_superseded(job, archive_label, superseded_by, reason):
    """Issue #610 item 4c: mark a slot-bound guard/watch job done
    WITHOUT executing it, because a newer slot of the same kind
    supersedes it (T4 spec). Reuses _mark_done — same publication
    path, same receipt staging — with the superseded markers added
    as extra record fields. The done record makes _done_or_pending
    true afterwards, so the skipped job is never re-executed. The
    archive label is the job kind's archive ("ledger-guard" /
    "ledger-watchdog"), matching an executed slot's record shape."""
    print(f"_mark_superseded {job['id']}: skipping, superseded by "
          f"{superseded_by} ({reason})", flush=True)
    return _mark_done(job, archive_label, extra={
        "superseded": True, "superseded_by": superseded_by,
        "reason": reason})


def _malformed_name(job):
    """File stem for a malformed queue entry's quarantine record.
    A usable id names its own record; an entry without one is named
    by a hash of its canonical JSON, so the same entry always maps
    to the same record (and a later valid entry with that id is
    never blocked by it — the record is evidence only, never a
    gate)."""
    job_id = job.get("id") if isinstance(job, dict) else None
    if isinstance(job_id, str) and JOB_ID_RE.fullmatch(job_id):
        return job_id
    try:
        canonical = json.dumps(job, sort_keys=True, default=str)
    except Exception:
        canonical = repr(job)
    digest = hashlib.sha256(canonical.encode()).hexdigest()[:16]
    return f"no-id-{digest}"


def _quarantine_malformed_job(job, reason):
    """Record a malformed queue entry as a named failure and return
    False — never raise. Issue #391: a queue entry without a usable
    id/job must be quarantined / skipped with evidence, never raised
    out of claim() into the cycle. The record lives under
    queue/malformed/ (scanned by nothing — not claims/, so
    reclaim_stale_claims never touches it — and surfaced in the
    heartbeat payload). An already-recorded entry is not re-pushed
    every cycle; a record whose push failed is wiped by the next
    sync_bus reset and re-recorded, so the push is retried."""
    name = _malformed_name(job)
    try:
        record = {"worker": os.uname().nodename, "at": now(),
                  "reason": reason, "entry": job}
        d = BUS / "queue" / "malformed"
        d.mkdir(parents=True, exist_ok=True)
        path = d / f"{name}.json"
        if path.exists():
            return False
        path.write_text(json.dumps(record))
        push_bus(f"malformed queue entry skipped {name} ({reason})")
    except Exception as e:  # noqa: BLE001 - a skip record must never raise
        print(f"_quarantine_malformed_job {name}: record failed "
              f"({type(e).__name__}: {e})", file=sys.stderr, flush=True)
    return False


def claim(job):
    # Issue #391: a malformed queue entry must be quarantined with
    # evidence, never raised out of claim() into the cycle. Before
    # this guard, job["id"]/job["job"] raised KeyError here — before
    # _execute ever ran, so the #381 job_text() normalization never
    # got a chance — and the cycle-level catch aborted the queue
    # loop, stalling head-of-line on one bad entry. A `job` key
    # that is present but None/non-string is NOT rejected here: #381
    # deliberately routes those through _execute_body, which fails
    # closed with a named unknown-job / invalid-job-type failure.
    if not isinstance(job, dict):
        return _quarantine_malformed_job(job, "not-an-object")
    job_id = job.get("id")
    if not isinstance(job_id, str) or not JOB_ID_RE.fullmatch(job_id):
        return _quarantine_malformed_job(job, "missing-or-invalid-id")
    if "job" not in job:
        return _quarantine_malformed_job(job, "missing-job")
    if _done_or_pending(job_id):
        # Issue #149: a completed job is never claimed again.
        return False
    c = BUS / "queue" / "claims"
    c.mkdir(parents=True, exist_ok=True)
    (c / f"{job_id}.json").write_text(json.dumps(
        {"worker": os.uname().nodename, "at": now(), "job": job["job"],
         "attempt": uuid.uuid4().hex}))
    return push_bus(f"claim {job_id}")


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


# --- Issue #66 extension: generic interval entries --------------------
# A daily entry (no `cadence`, or cadence "daily") keeps the exact
# legacy behaviour above. An interval entry fires on a fixed grid in
# its tz: slots start at `minute` (default 0) plus every
# `every_minutes` minutes ("hourly" is shorthand for every 60).
# Slot ids are deterministic per slot: <prefix><YYYY-MM-DDTHHMMZ>
# in UTC, e.g. guard-2026-11-18T1047Z — they satisfy JOB_ID_RE.
# Catch-up rule (per entry, `grace_minutes` / `catchup_minutes`):
#   age <= grace            -> "fire"    (normal, on-time firing)
#   grace < age <= catchup  -> "catchup" (enqueue ONCE + missed
#                                         marker recording lateness)
#   age > catchup           -> "mark"    (missed marker only)
# Only the LATEST slot of an entry can ever enqueue; older slots in
# the mark window (MARK_WINDOW_SLOTS) are marked, never run — a long
# outage produces markers, not a firing storm. A slot id that is
# already handled (queued / claimed / done) or already marked is
# skipped entirely, so no slot ever runs twice.
MARK_WINDOW_SLOTS = 4


def entry_prefix(entry):
    """Job-id prefix for an entry: explicit `prefix`, else the
    legacy sweep prefix."""
    return entry.get("prefix") or SCHEDULED_JOB_PREFIX


def entry_every_minutes(entry):
    """Slot spacing for an interval entry, or None for a daily
    entry. `cadence: "hourly"` means 60; `cadence: "interval"`
    takes `every_minutes`."""
    cadence = entry.get("cadence")
    if cadence == "hourly":
        return 60
    if cadence == "interval":
        try:
            every = int(entry.get("every_minutes") or 0)
        except (TypeError, ValueError):
            return None
        return every if every > 0 else None
    return None


def slot_start_for(entry, now_local):
    """The most recent slot start <= now_local for an interval
    entry (an aware datetime in the entry's tz), or None."""
    every = entry_every_minutes(entry)
    if not every:
        return None
    try:
        anchor = int(entry.get("minute") or 0)
    except (TypeError, ValueError):
        return None
    from datetime import timedelta
    midnight = now_local.replace(hour=0, minute=0, second=0,
                                 microsecond=0)
    rel = (now_local.hour * 60 + now_local.minute) - anchor
    # Floor division: for a `now` before today's first slot, rel is
    # negative and k = -1 lands on yesterday's last slot — correct.
    return midnight + timedelta(minutes=anchor + (rel // every) * every)


def slot_job_id(entry, slot_local):
    """Deterministic per-slot job id (UTC stamp)."""
    slot_utc = slot_local.astimezone(timezone.utc)
    return f"{entry_prefix(entry)}{slot_utc.strftime('%Y-%m-%dT%H%MZ')}"


def slot_decision(entry, slot_local, now_local):
    """Pure decision for one interval slot: "fire" / "catchup" /
    "mark" per the catch-up rule above; None when the slot is in
    the future or the entry does not run today."""
    days = entry.get("days")
    if days and slot_local.strftime("%a") not in days:
        return None
    if now_local < slot_local:
        return None
    age_min = (now_local - slot_local).total_seconds() / 60
    try:
        grace = float(entry.get("grace_minutes", 10))
        catchup = float(entry.get("catchup_minutes",
                                  (entry_every_minutes(entry) or 60) * 2))
    except (TypeError, ValueError):
        return None
    if age_min <= grace:
        return "fire"
    if age_min <= catchup:
        return "catchup"
    return "mark"


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
        if entry_every_minutes(entry) is None:
            # Legacy daily entry — unchanged behaviour.
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
            continue
        # Interval entry (#66 extension): walk the mark window from
        # the latest slot backwards. Only the latest slot may
        # enqueue; a handled or already-marked slot is skipped
        # entirely, so a slot never runs twice.
        from datetime import timedelta
        every = entry_every_minutes(entry)
        latest = slot_start_for(entry, now_local)
        if latest is None:
            continue
        for i in range(MARK_WINDOW_SLOTS):
            slot = latest - timedelta(minutes=i * every)
            job_id = slot_job_id(entry, slot)
            if job_id in handled_ids or job_id in missed_job_ids:
                continue
            if i > 0:
                # Superseded slot: record the miss, never run it.
                to_mark.append((entry, job_id))
                continue
            decision = slot_decision(entry, slot, now_local)
            if decision == "fire":
                to_enqueue.append((entry, job_id))
            elif decision == "catchup":
                to_enqueue.append((entry, job_id))
                to_mark.append((entry, job_id))
            elif decision == "mark":
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


def _quarantine_non_object_entries(queue):
    """Issue #402: return the dict entries of a raw queue, quarantining
    every non-object entry with evidence first — never silently
    dropped, never fatal to the cycle. A null/string/list entry has
    no .get, so the unguarded `j.get("id", "")` comprehensions in
    run_schedule_check() and run_ledger_watchdog() raised
    AttributeError out of those functions before the #391
    queue-loop quarantine ever ran — and run_schedule_check runs
    at the top of every poll cycle, so the cycle then failed at the
    same point forever with no valid job ever processing. The
    quarantine record (queue/malformed/, raw entry kept) is the
    evidence; the returned list is for id computation only — the
    caller's raw queue is left untouched, so a quarantined entry
    stays in queue.json exactly as the #391 main-loop path leaves
    it (re-quarantine is a no-op once the record exists). A
    queue.json that is not a list at all is quarantined as one
    malformed payload ("queue-not-a-list") and yields no entries.
    Issue #420: main() routes its queue through this helper too,
    so a non-list queue.json is quarantined as one record even
    when no schedule exists (run_schedule_check returns before
    quarantine then) — before #420 the main loop iterated the raw
    payload, raising TypeError on a scalar and quarantining one
    record per char/key on a string/object."""
    if not isinstance(queue, list):
        _quarantine_malformed_job(queue, "queue-not-a-list")
        return []
    entries = []
    for entry in queue:
        if isinstance(entry, dict):
            entries.append(entry)
        else:
            _quarantine_malformed_job(entry, "not-an-object")
    return entries


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
    entries = _quarantine_non_object_entries(queue)
    if not isinstance(queue, list):
        # Issue #402: a non-list queue.json cannot be appended to;
        # the whole payload is already quarantined above, so skip
        # the check rather than crash the cycle.
        print("run_schedule_check: queue.json is not a list; "
              "skipping", file=sys.stderr, flush=True)
        return
    handled = {str(j.get("id", "")) for j in entries}
    claims_dir = BUS / "queue" / "claims"
    if claims_dir.exists():
        handled |= {f.name[:-len(".json")]
                    for f in claims_dir.glob("*.json")}
    done_dir = BUS / "queue" / "done"
    if done_dir.exists():
        # Issue #149 done records also suppress re-enqueue (matters
        # for interval slots, whose ids stay meaningful all day).
        handled |= {f.name[:-len(".json")]
                    for f in done_dir.glob("*.json")}
    # Missed markers are missed-<slot-suffix>.json; the job id is
    # <entry prefix><suffix>. Reconstruct for every prefix in play
    # (over-generation across entries is harmless: suffix shapes
    # differ and check_schedule only matches real slot ids).
    prefixes = {entry_prefix(e) for e in schedule} | {SCHEDULED_JOB_PREFIX}
    missed = {p + f.name[len('missed-'):-len('.json')]
              for f in (BUS / "queue").glob("missed-*.json")
              for p in prefixes}
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
    enqueued_ids = {job_id for _, job_id in to_enqueue}
    for entry, job_id in to_mark:
        suffix = job_id[len(entry_prefix(entry)):]
        marker = BUS / "queue" / f"missed-{suffix}.json"
        if entry_every_minutes(entry) is None:
            reason = ("scheduled fire missed: worker had not enqueued "
                      "by the 09:30 Cairo catch-up cutoff — no "
                      "post-open sweep; see the Actions fallback run "
                      "or dispatch manually")
        elif job_id in enqueued_ids:
            reason = ("scheduled fire was late: caught up ONCE at the "
                      "next poll and enqueued — this marker records "
                      "the lateness, the job still runs (issue #66 "
                      "extension)")
        else:
            reason = ("scheduled fire missed: slot superseded without "
                      "running (worker down or busy past the catch-up "
                      "window); only the latest slot catches up — "
                      "never silently dropped (issue #66 extension)")
        marker.write_text(json.dumps(
            {"job_id": job_id, "job": entry["job"], "at": now(),
             "worker": os.uname().nodename,
             "reason": reason}, indent=1))
        push_bus(f"missed scheduled job {job_id}")
        print(f"run_schedule_check: marked missed {job_id}", flush=True)


# --- Issue #66 extension: ledger guard + watchdog execution -----------
# The guard job runs scripts/ledger_publish.py in staging mode
# (issue #443): the publisher validates the ledger in a dedicated
# checkout of MAIN and pushes ONE envelope commit — the validated
# ledger outputs (when changed) plus this run's heartbeat, or the
# heartbeat alone when the outputs are unchanged — to a per-run
# branch publish/ledger-<job-id>. The ledger-publish relay
# (.github/workflows/ledger-publish-relay.yml, kicked by the push)
# turns the branch into a PR, executes the required close-gate on
# the candidate commit and merges it; the worker marks the slot
# done only after the envelope's heartbeat is confirmed ON MAIN.
# Before #443 the guard pushed the ledger and the heartbeat
# directly to main; branch protection requires the close-gate
# check, which a worker-pushed commit never carries, so every
# push was declined ("protected branch hook declined") and the
# ledger went stale from 2026-11-20.
# The publisher needs a git checkout of MAIN with a push credential:
# the release checkout (CODE) is an anonymous, detached checkout of
# worker-release and can do neither, so the guard keeps a dedicated
# checkout (ROOT/"main-ledger") cloned from GATOR_BUS_URL — the
# worker PAT is borsagator-only Contents RW, which covers branch
# pushes. D2 guard: the worker never EXECUTES main-tip code — before
# running, the publisher scripts in the main checkout must be
# byte-identical to the reviewed release checkout's copies, or the
# run refuses loudly (and the heartbeat records the refusal).
# The watchdog job runs scripts/ledger_guard_watch.py against that
# heartbeat. The worker PAT has NO Issues permission (Contents RW
# only), so the watchdog cannot file the `ledger-failure` issue
# itself: it runs the script with --signal-out and mirrors the
# would-be signal onto the bus as queue/guard-alert.json; Moos's
# heartbeat/cycle reads the queue branch and files/closes the issue
# from Moos's side. Same reason the guard, on a failed publish,
# writes queue/ledger-failure.json (the publisher's own API signal
# no-ops without an Issues-capable token).
GUARD_CHECKOUT = ROOT / "main-ledger"
GUARD_SCRIPTS = ("scripts/ledger_publish.py", "scripts/ledger.py")
# INS-DEV-004: the watch imports band_calibration for the calibration
# coverage alert, so it joins the D2 byte-identity set.
WATCH_SCRIPTS = (("scripts/ledger_guard_watch.py",
                  "scripts/band_calibration.py") + GUARD_SCRIPTS)
GUARD_LEDGER_REL = "ledger/ledger.json"
GUARD_HEARTBEAT_REL = "ledger/guard-heartbeat.json"
# Issue #443: the publisher subprocess gets the same 1800s bound
# it effectively had, but now under sh_group (the whole process
# group is killed and verified empty on timeout — see
# run_ledger_guard's hang-proofing note) instead of a bare
# subprocess.run whose timeout kills only the publisher process.
GUARD_PUBLISH_TIMEOUT_S = 1800
# Issue #443: after staging, the worker polls main for the run's
# envelope heartbeat (the relay's merge is what lands it). The
# relay normally completes in a few minutes; the bound is generous
# so a slow relay queue never fails a healthy slot, and finite so
# a dead relay cannot hang the guard: on expiry the slot stays
# un-done and the failure is recorded (ledger-failure.json +
# missed-<slot> marker), exactly the #434 refusal shape.
GUARD_CONFIRM_TIMEOUT_S = 1500
GUARD_CONFIRM_POLL_S = 30
# Issue #434: a guard slot counts as "pending execution" only while
# its slot time is within the claim-staleness horizon. queue.json is
# append-only, so a slot that never completed (e.g. the 2026-11-19
# 0647Z slot, still un-done a day later) stays in the queue forever;
# treating it as pending suppressed the watchdog permanently.
GUARD_SLOT_RE = re.compile(
    r"^guard-(\d{4})-(\d{2})-(\d{2})T(\d{2})(\d{2})Z$")


def bus_url_token(url):
    """The credential embedded in a git HTTPS URL, or None. Pure:
    `https://x-access-token:<PAT>@host/...` yields the PAT,
    `https://<PAT>@host/...` yields the PAT, a credential-free URL
    yields None. The value is never logged anywhere."""
    import urllib.parse
    try:
        parts = urllib.parse.urlparse(url or "")
    except Exception:
        return None
    if parts.password:
        return parts.password
    if parts.username and parts.username not in ("git", "x-access-token"):
        return parts.username
    return None


def _guard_env():
    """Environment for first-party guard/watchdog scripts: the bus
    URL is stripped (as for tools) and its credential is re-exposed
    as GH_TOKEN — the name ledger_publish.py / ledger.py read.
    In-process only; never logged, never given to tool runs."""
    env = {k: v for k, v in os.environ.items()
           if k not in ENV_DENY_FOR_TOOLS}
    token = bus_url_token(os.environ.get("GATOR_BUS_URL", ""))
    if token:
        env["GH_TOKEN"] = token
    return env


def _ensure_main_checkout():
    """Clone or refresh the dedicated main checkout for the guard.
    Returns the Path, or None when it cannot be established."""
    if not GUARD_CHECKOUT.exists():
        url = os.environ.get("GATOR_BUS_URL", "")
        if not url:
            return None
        if sh(f"git clone --branch main --single-branch {url} "
              f"{GUARD_CHECKOUT}", timeout=300).returncode != 0:
            return None
        sh(f"git -C {GUARD_CHECKOUT} config user.email "
           f"worker@borsagator.local", timeout=30)
        sh(f"git -C {GUARD_CHECKOUT} config user.name "
           f"borsagator-worker", timeout=30)
    if sh(f"git -C {GUARD_CHECKOUT} fetch origin main",
          timeout=120).returncode != 0:
        return None
    if sh(f"git -C {GUARD_CHECKOUT} reset --hard origin/main",
          timeout=60).returncode != 0:
        return None
    return GUARD_CHECKOUT


def scripts_match(dir_a, dir_b, names):
    """True when every named file is byte-identical in both trees
    (the D2 guard for running main-checkout scripts)."""
    for name in names:
        ha = _sha256_file(Path(dir_a) / name)
        if not ha or ha != _sha256_file(Path(dir_b) / name):
            return False
    return True


def _guard_branch(job_id):
    """The per-run staging branch for a guard job (issue #443).
    Sanitized to a safe ref fragment: job ids are worker/scheduler
    generated, but the queue is data — never let a crafted id
    escape the publish/ledger- namespace or grow ref-illegal
    characters."""
    slug = re.sub(r"[^A-Za-z0-9._-]", "-", str(job_id)).strip(".")
    return "publish/ledger-" + (slug or "run")


def _guard_heartbeat_doc(status, job_id):
    """The heartbeat document for one guard run (the file is issue
    #128's; the watchdog reads only last_run_utc + status)."""
    return {"last_run_utc": datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"),
            "run_id": job_id,
            "status": status,
            "workflow": "ledger-guard",
            "note": "Written by every completed worker ledger-guard "
                    "run (issue #66 extension; formerly "
                    "ledger-guard.yml); the watchdog pages when "
                    "this is older than 90 minutes."}


BRANCH_PRESENT = "present"
BRANCH_ABSENT = "absent"
BRANCH_UNKNOWN = "unknown"
# Issue #501: the last branch lookup's error, recorded whenever
# the state comes back UNKNOWN (None after a definitive answer).
BRANCH_LOOKUP_ERROR = None


def _branch_state_on_origin(checkout, branch):
    """Tri-state branch lookup (issue #501): (BRANCH_PRESENT,
    None) when refs/heads/<branch> exists on origin;
    (BRANCH_ABSENT, None) when ls-remote succeeds and lists no
    such ref — git's definitive absence answer; (BRANCH_UNKNOWN,
    error) when the lookup itself failed (auth, network, command
    error). A failed lookup is UNKNOWN, never absence: callers
    must fail closed on it, because reading an error as 'branch
    absent' is how a staging push could overwrite an envelope
    it failed to see. The error is also recorded in
    BRANCH_LOOKUP_ERROR."""
    global BRANCH_LOOKUP_ERROR
    try:
        r = sh(f"git -C {checkout} ls-remote origin "
               f"refs/heads/{branch}", timeout=60)
    except Exception as e:
        BRANCH_LOOKUP_ERROR = f"{type(e).__name__}: {e}"
        print(f"_branch_state_on_origin: {BRANCH_LOOKUP_ERROR}",
              file=sys.stderr, flush=True)
        return BRANCH_UNKNOWN, BRANCH_LOOKUP_ERROR
    if r.returncode != 0:
        err = (r.stderr or "").strip() or (r.stdout or "").strip()
        BRANCH_LOOKUP_ERROR = " ".join(err.split())[-200:] \
            or f"ls-remote exited {r.returncode}"
        print(f"_branch_state_on_origin: lookup failed: "
              f"{BRANCH_LOOKUP_ERROR}",
              file=sys.stderr, flush=True)
        return BRANCH_UNKNOWN, BRANCH_LOOKUP_ERROR
    BRANCH_LOOKUP_ERROR = None
    if r.stdout.strip():
        return BRANCH_PRESENT, None
    return BRANCH_ABSENT, None


def _branch_exists_on_origin(checkout, branch):
    """True only when refs/heads/<branch> is POSITIVELY present
    on origin (issue #501 tri-state: see _branch_state_on_origin
    — an errored lookup is not absence and does not read as
    existence either)."""
    state, _ = _branch_state_on_origin(checkout, branch)
    return state == BRANCH_PRESENT


def _stage_guard_heartbeat(checkout, branch, status, job_id,
                           attempt_id=None):
    """Stage a heartbeat-only envelope on the run's staging branch
    (issue #443): the fallback for a publisher that failed or
    refused, so the run still leaves its liveness evidence for
    the relay to land — with a FAILED status, and never with the
    (possibly invalid) ledger outputs the publisher rejected.

    Returns True when the branch carries this run's heartbeat
    afterwards. An already-existing branch is left untouched and
    still counts: if the publisher staged its success envelope
    and then died before reporting, that envelope is the truthful
    record of the run, and overwriting it with a failed heartbeat
    would falsify it (the caller's confirmation reads the status
    off main and reconciles). A failed fetch/reset stops the
    staging — CodeRabbit #440's stacked-commit lesson applies to
    branches too: never commit on top of a state we failed to
    reset. An empty staged diff means the heartbeat is already
    byte-identical to main's (a same-second duplicate run): also
    fine — the caller's confirmation verifies it on main."""
    try:
        state, lookup_err = _branch_state_on_origin(checkout,
                                                    branch)
        if state == BRANCH_UNKNOWN:
            # Issue #501: fail closed — a lookup error is not
            # absence, so no staging push may be attempted on its
            # strength (it could overwrite an envelope this call
            # failed to see). The error is recorded above and in
            # BRANCH_LOOKUP_ERROR.
            print(f"_stage_guard_heartbeat: branch lookup for "
                  f"{branch} failed ({lookup_err}) — failing "
                  "closed, no staging push attempted",
                  file=sys.stderr, flush=True)
            return False
        if state == BRANCH_PRESENT:
            print(f"_stage_guard_heartbeat: {branch} already "
                  "staged — leaving the existing envelope in place",
                  flush=True)
            # Issue #499: persist the expected envelope before
            # confirmation relies on the (deletable) branch.
            # INS-REVIEW-093: a required durable record that
            # cannot be established blocks the handoff — this
            # path must not report success without it.
            # INS-REVIEW-105: adoption is bound to the producing
            # attempt — an existing branch staged by a DIFFERENT
            # attempt (or by an unknown producer) is never
            # adopted or rebound to this attempt, and an
            # unreadable envelope on an existing branch fails
            # closed instead of reporting staged.
            env = _staged_guard_envelope(checkout, branch)
            if env is None:
                print("_stage_guard_heartbeat: the envelope on "
                      "the existing branch could not be read — "
                      "failing closed, not handing off",
                      file=sys.stderr, flush=True)
                return False
            if not _branch_envelope_producer_ok(
                    job_id, env, attempt_id):
                print("_stage_guard_heartbeat: the existing "
                      "branch was not produced by this attempt "
                      "— refusing adoption",
                      file=sys.stderr, flush=True)
                return False
            if _persist_guard_envelope(
                    job_id, branch, env,
                    attempt_id=attempt_id) is None:
                print("_stage_guard_heartbeat: the durable "
                      "envelope record could not be established "
                      "— failing closed, not handing off",
                      file=sys.stderr, flush=True)
                return False
            return True
        if sh(f"git -C {checkout} fetch origin main",
              timeout=120).returncode != 0:
            print("_stage_guard_heartbeat: fetch failed",
                  file=sys.stderr, flush=True)
            return False
        if sh(f"git -C {checkout} reset --hard origin/main",
              timeout=60).returncode != 0:
            print("_stage_guard_heartbeat: reset failed",
                  file=sys.stderr, flush=True)
            return False
        doc = _guard_heartbeat_doc(status, job_id)
        p = Path(checkout) / GUARD_HEARTBEAT_REL
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(doc, indent=2) + "\n")
        sh(f"git -C {checkout} config user.name borsagator-ledger",
           timeout=30)
        sh(f"git -C {checkout} config user.email moos@sherbeeny.com",
           timeout=30)
        sh(f"git -C {checkout} add {GUARD_HEARTBEAT_REL}", timeout=60)
        if sh(f"git -C {checkout} diff --cached --quiet",
              timeout=60).returncode == 0:
            # The envelope is already byte-identical on main;
            # persist it so confirmation has its record (issue
            # #499) even though no branch was created.
            # INS-REVIEW-093: the durable record is a handoff
            # precondition here too — without it (or without a
            # readable ledger tree to record) this path must not
            # report success.
            blobs = _ledger_tree_map(checkout, "HEAD")
            c = sh(f"git -C {checkout} rev-parse HEAD", timeout=60)
            if blobs is None or _persist_guard_envelope(
                    job_id, branch,
                    {"heartbeat": doc, "blobs": blobs,
                     "commit": c.stdout.strip()
                     if c.returncode == 0 else None},
                    attempt_id=attempt_id) is None:
                print("_stage_guard_heartbeat: the durable "
                      "envelope record could not be established "
                      "— failing closed, not handing off",
                      file=sys.stderr, flush=True)
                return False
            return True
        msg = (f"Ledger guard heartbeat {doc['last_run_utc']} "
               f"({status})")
        if sh(f"git -C {checkout} commit -m {json.dumps(msg)}",
              timeout=60).returncode != 0:
            print("_stage_guard_heartbeat: commit failed",
                  file=sys.stderr, flush=True)
            return False
        # Issue #499 + INS-REVIEW-093: persist the expected
        # envelope (heartbeat content, blob hashes, envelope
        # commit) BEFORE the staging push — never after it. The
        # relay may delete this branch at any point after its
        # merge, and the persisted record plus the PR/merge
        # evidence is what confirmation stands on; a required
        # durable record that cannot be established blocks the
        # handoff, so no push is attempted without it.
        blobs = _ledger_tree_map(checkout, "HEAD")
        c = sh(f"git -C {checkout} rev-parse HEAD", timeout=60)
        if blobs is None or _persist_guard_envelope(
                job_id, branch,
                {"heartbeat": doc, "blobs": blobs,
                 "commit": c.stdout.strip()
                 if c.returncode == 0 else None},
                attempt_id=attempt_id) is None:
            print("_stage_guard_heartbeat: the durable envelope "
                  "record could not be established — failing "
                  "closed, no staging push attempted",
                  file=sys.stderr, flush=True)
            return False
        if sh(f"git -C {checkout} push origin "
              f"HEAD:refs/heads/{branch}",
              timeout=120).returncode != 0:
            print("_stage_guard_heartbeat: staging push failed",
                  file=sys.stderr, flush=True)
            return False
        return True
    except Exception as e:
        print(f"_stage_guard_heartbeat: {type(e).__name__}: {e}",
              file=sys.stderr, flush=True)
        return False


def _ledger_tree_map(checkout, ref):
    """Map of ledger/** path -> blob sha at `ref`, or None when the
    ref or its ledger tree cannot be read. The envelope's identity
    is its full content (issue #498): the heartbeat alone does not
    prove the validated ledger outputs landed with it."""
    try:
        r = sh(f"git -C {checkout} ls-tree -r {ref} -- ledger/",
               timeout=60)
        if r.returncode != 0:
            return None
        out = {}
        for line in r.stdout.splitlines():
            meta, _, path = line.partition("\t")
            parts = meta.split()
            if len(parts) == 3 and parts[1] == "blob" and path:
                out[path] = parts[2]
        return out
    except Exception as e:
        print(f"_ledger_tree_map: {type(e).__name__}: {e}",
              file=sys.stderr, flush=True)
        return None


def _staged_guard_envelope(checkout, branch):
    """The full envelope this attempt staged on the branch: the
    heartbeat doc plus the blob sha of every ledger/** file in the
    staged commit (issue #498), or None when the branch or the
    envelope cannot be read. Confirmation compares main against
    THIS envelope: a same-run-id heartbeat left on main by an
    earlier attempt (its relay merged after that attempt's
    confirmation window expired) must never confirm a later
    attempt whose own envelope did not land — the #434 false-done
    class (PR review finding on #491) — and a heartbeat that
    landed without this attempt's ledger outputs must not confirm
    either."""
    try:
        if sh(f"git -C {checkout} fetch origin {branch}",
              timeout=120).returncode != 0:
            return None
        r = sh(f"git -C {checkout} show "
               f"FETCH_HEAD:{GUARD_HEARTBEAT_REL}", timeout=60)
        if r.returncode != 0:
            return None
        doc = json.loads(r.stdout)
        if not isinstance(doc, dict):
            return None
        blobs = _ledger_tree_map(checkout, "FETCH_HEAD")
        if blobs is None:
            return None
        c = sh(f"git -C {checkout} rev-parse FETCH_HEAD",
               timeout=60)
        commit = c.stdout.strip() if c.returncode == 0 else None
        return {"heartbeat": doc, "blobs": blobs, "commit": commit}
    except Exception as e:
        print(f"_staged_guard_envelope: {type(e).__name__}: {e}",
              file=sys.stderr, flush=True)
        return None


def _staged_guard_heartbeat(checkout, branch):
    """The heartbeat doc this attempt staged on the branch (written
    by the publisher, or by the worker's fallback stager), or None
    when the branch or the file cannot be read."""
    env = _staged_guard_envelope(checkout, branch)
    return env["heartbeat"] if env is not None else None


def _guard_envelope_record_path(job_id):
    return BUS / "queue" / "envelopes" / f"{job_id}.json"


def _pending_envelope_path(job_id):
    return PENDING_ENVELOPES / f"{job_id}.json"


def _guard_attempt_id(job_id):
    """The immutable identifier of THIS execution attempt of a
    guard job: the claim record (worker + claim time) written
    when the job was claimed. A reclaim writes a new claim, so a
    re-executed job is a different attempt; the same attempt
    resuming (restart under the same claim) keeps the same id.
    PR #515 review: persisted envelope records are bound to this
    id — exact-content equality proves which content is on main,
    not which attempt produced it, so a later attempt must never
    confirm on an earlier attempt's record. None when no claim
    record can be read (direct/test execution)."""
    try:
        p = BUS / "queue" / "claims" / f"{job_id}.json"
        claim = json.loads(p.read_text())
        worker_name = claim.get("worker")
        at = claim.get("at")
        if worker_name and at:
            return f"{worker_name}@{at}"
    except Exception:
        pass
    return None


def _remote_envelope_record(job_id):
    """The envelope record stored on origin/queue for job_id,
    fetched fresh and read from FETCH_HEAD (never from the
    resettable working tree), or None when it cannot be read
    or parsed."""
    try:
        if git_bus("fetch origin queue",
                   timeout=120).returncode != 0:
            return None
        r = git_bus(f"show "
                    f"FETCH_HEAD:queue/envelopes/{job_id}.json",
                    timeout=60)
        if r.returncode != 0:
            return None
        rec = json.loads(r.stdout)
        return rec if isinstance(rec, dict) else None
    except Exception:
        return None


def _envelope_records_match(a, b):
    """Identity equality of two envelope records (INS-REVIEW-105):
    same job, branch, producing attempt, envelope commit,
    heartbeat content and blob map. persisted_at is metadata,
    not identity."""
    if not isinstance(a, dict) or not isinstance(b, dict):
        return False
    return all(a.get(k) == b.get(k) for k in
               ("job_id", "branch", "attempt_id",
                "envelope_commit", "heartbeat", "blobs"))


def _envelope_record_on_remote(job_id, record=None):
    """True when origin/queue verifiably carries the envelope
    record for job_id. With `record` (INS-REVIEW-105) the remote
    copy must EQUAL that exact record — existence of SOME record
    at the path proves nothing: a rejected push can leave an
    earlier attempt's record on the remote under the same job
    id, and existence-only read-back then deleted the newer
    attempt's durable local copy. Without `record`, legacy
    existence semantics (test/direct callers only)."""
    remote = _remote_envelope_record(job_id)
    if remote is None:
        return False
    if record is None:
        return True
    return _envelope_records_match(remote, record)


def _publish_envelope_record(job_id, record=None):
    """Publish the bus copy of an envelope record and VERIFY it
    on origin/queue (PR #515 review). push_bus commits locally
    before pushing, so a rejected push can leave the record
    committed-but-unpushed: the retry therefore also tries a
    bare push, and only a verified read-back counts as
    published. With `record`, the read-back must equal that
    exact record (INS-REVIEW-105) — a different record at the
    same path is not publication of this one. Bounded; returns
    False when publication could not be verified (the durable
    local copy remains)."""
    for _ in range(3):
        try:
            push_bus(f"guard envelope record {job_id}")
        except Exception:
            pass
        if _envelope_record_on_remote(job_id, record):
            return True
        try:
            git_bus("push origin queue", timeout=120)
        except Exception:
            pass
        if _envelope_record_on_remote(job_id, record):
            return True
    return False


def _persist_guard_envelope(job_id, branch, envelope,
                            attempt_id=None):
    """Persist the expected envelope — heartbeat content, blob
    hashes and the envelope commit — on the bus BEFORE
    confirmation relies on it (issue #499). The relay deletes the
    staging branch after a verified merge, so the branch is not
    evidence: the retained record plus the PR/merge evidence is.
    The envelope commit names an immutable git object that stays
    reachable through the merge commit even after the branch is
    gone.

    PR #515 review, two bindings added: the record is bound to
    the attempt that produced it (attempt_id — a later attempt
    of the same job must not confirm on it), and publication is
    durable: a local copy is kept OUTSIDE the resettable bus
    clone (PENDING_ENVELOPES, the #216 pattern) until the exact
    record is verified on origin/queue — a rejected bus push no
    longer silently strands the only copy inside a clone that
    sync_bus resets.

    INS-REVIEW-093 hardens the return contract: the record is
    returned ONLY when the durable local copy was actually
    established. Bus publication stays secondary (best-effort,
    verified opportunistically, retried at load) — but a failed
    DURABLE write returns None, and callers that stage or hand
    off an envelope must not report success without the record:
    the earlier 'persistence must never fail staging' rule let
    a dead durable write plus a failed bus publication still
    report a successful handoff, stranding the envelope with no
    record anywhere."""
    if not isinstance(envelope, dict) \
            or "heartbeat" not in envelope \
            or "blobs" not in envelope:
        return None
    record = {"job_id": str(job_id), "branch": branch,
              "envelope_commit": envelope.get("commit"),
              "heartbeat": envelope["heartbeat"],
              "blobs": envelope["blobs"],
              "attempt_id": attempt_id,
              "persisted_at": now()}
    durable = False
    try:
        lp = _pending_envelope_path(job_id)
        lp.parent.mkdir(parents=True, exist_ok=True)
        lp.write_text(json.dumps(record, indent=1))
        durable = True
    except Exception as e:
        print(f"_persist_guard_envelope (local copy): "
              f"{type(e).__name__}: {e}",
              file=sys.stderr, flush=True)
    try:
        p = _guard_envelope_record_path(job_id)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(record, indent=1))
        if _publish_envelope_record(job_id, record):
            # Verified on origin/queue as THIS exact record
            # (INS-REVIEW-105) — the durable local copy's job
            # is done. An existence-only read-back is not
            # enough: the remote may carry an earlier attempt's
            # record at this path while this push was rejected.
            try:
                _pending_envelope_path(job_id).unlink(
                    missing_ok=True)
            except Exception:
                pass
    except Exception as e:
        print(f"_persist_guard_envelope: {type(e).__name__}: {e}",
              file=sys.stderr, flush=True)
    return record if durable else None


def _load_persisted_guard_envelope(job_id, attempt_id=None):
    """The persisted expected envelope for a job (issue #499), or
    None when no record exists or it is malformed. This is the
    confirmation source once the staging branch has been deleted
    (by the relay, or by cleanup) — confirmation must not depend
    on a deletable branch.

    PR #515 review: the record must belong to THIS attempt —
    when attempt_id is given, a record bound to a different
    attempt (an earlier attempt whose envelope landed late) is
    NOT this attempt's evidence and returns None. When the bus
    copy is missing but the durable local copy survives (its
    bus push was rejected earlier), the local copy is used and
    its publication is retried — without rerunning the job."""
    # INS-REVIEW-105: every candidate is validated on its own
    # before it may suppress the other. The bus working copy can
    # be STALE (sync_bus resets the clone to an older committed
    # record) while the durable local copy is this attempt's —
    # reading the bus copy first and applying the attempt check
    # only to the winner hid the valid local record behind the
    # stale one. Candidates: durable local copy first (it lives
    # outside the resettable clone), then the bus copy; the
    # first candidate that is well-formed AND bound to this
    # attempt wins.
    selected = None
    selected_local = False
    for source in ("local", "bus"):
        try:
            p = _pending_envelope_path(job_id) \
                if source == "local" \
                else _guard_envelope_record_path(job_id)
            if not p.exists():
                continue
            cand = json.loads(p.read_text())
        except Exception as e:
            print(f"_load_persisted_guard_envelope ({source}): "
                  f"{type(e).__name__}: {e}",
                  file=sys.stderr, flush=True)
            continue
        if not isinstance(cand, dict) \
                or not isinstance(cand.get("heartbeat"), dict) \
                or not isinstance(cand.get("blobs"), dict):
            continue
        if attempt_id is not None \
                and cand.get("attempt_id") != attempt_id:
            print(f"_load_persisted_guard_envelope: {source} "
                  f"record for {job_id} belongs to attempt "
                  f"{cand.get('attempt_id')}, not this attempt "
                  f"({attempt_id}) — not this attempt's evidence",
                  file=sys.stderr, flush=True)
            continue
        selected = cand
        selected_local = source == "local"
        break
    if selected is None:
        return None
    if selected_local:
        # Retry publication of the surviving copy; the local
        # copy is unlinked only when the remote verifiably
        # carries THIS record (INS-REVIEW-105).
        try:
            p = _guard_envelope_record_path(job_id)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(selected, indent=1))
            if _publish_envelope_record(job_id, selected):
                try:
                    _pending_envelope_path(job_id).unlink(
                        missing_ok=True)
                except Exception:
                    pass
        except Exception as e:
            print(f"_load_persisted_guard_envelope (publish): "
                  f"{type(e).__name__}: {e}",
                  file=sys.stderr, flush=True)
    return selected


def _existing_envelope_record(job_id):
    """The persisted envelope record for a job, whichever copy
    survives (durable local first, then the bus working copy),
    WITHOUT attempt filtering — the producing-attempt evidence
    _branch_envelope_producer_ok validates against. None when
    no well-formed record exists."""
    for path in (_pending_envelope_path(job_id),
                 _guard_envelope_record_path(job_id)):
        try:
            if path.exists():
                rec = json.loads(path.read_text())
                if isinstance(rec, dict) \
                        and isinstance(rec.get("heartbeat"), dict) \
                        and isinstance(rec.get("blobs"), dict):
                    return rec
        except Exception:
            continue
    return None


def _branch_envelope_producer_ok(job_id, env, attempt_id):
    """INS-REVIEW-105: an envelope read from an existing staging
    branch may be adopted by this attempt only when the
    persisted record — written by the producing attempt BEFORE
    its push — proves the branch is this attempt's own work:
    same attempt id AND same envelope commit. A different or
    unknown producer is rejected: exact-content equality proves
    which content is staged, not whose attempt staged it, and
    rebinding an earlier attempt's branch to a later attempt
    rewrites the recovery record under the wrong identity.
    Direct/test execution (attempt_id None) has no claim to
    bind against and keeps the legacy adoption."""
    if attempt_id is None:
        return True
    rec = _existing_envelope_record(job_id)
    if rec is None:
        return False
    return rec.get("attempt_id") == attempt_id \
        and rec.get("envelope_commit") == env.get("commit")


def _guard_envelope_on_main(checkout, job_id, expected=None):
    """The heartbeat doc on origin/main when it is this attempt's
    envelope, else None. Fetch + show, never a push returncode:
    the watchdog reads this file, so this file is what
    confirmation means (issue #434). With `expected` — the full
    envelope this attempt staged, as returned by
    _staged_guard_envelope (a bare heartbeat doc is also accepted
    for callers that only have the doc) — confirmation requires
    FULL expected-content equality (issue #498): the on-main
    heartbeat doc must equal the staged doc in every field, and
    every ledger/** blob of the staged envelope must be present
    on main with the identical blob sha. A bare run_id match, or
    a heartbeat that landed without this attempt's ledger
    outputs, is never sufficient. Run ids are compared as
    strings — the publisher writes LEDGER_RUN_ID verbatim, the
    Actions path historically wrote an int."""
    try:
        if sh(f"git -C {checkout} fetch origin main",
              timeout=120).returncode != 0:
            return None
        r = sh(f"git -C {checkout} show "
               f"origin/main:{GUARD_HEARTBEAT_REL}", timeout=60)
        if r.returncode != 0:
            return None
        live = json.loads(r.stdout)
        if not isinstance(live, dict) \
                or str(live.get("run_id")) != str(job_id):
            return None
        if expected is None:
            return None
        exp_doc = expected.get("heartbeat") \
            if isinstance(expected, dict) else None
        if exp_doc is None and isinstance(expected, dict) \
                and "run_id" in expected:
            exp_doc = expected
        if exp_doc is None or live != exp_doc:
            return None
        blobs = expected.get("blobs") \
            if isinstance(expected, dict) else None
        if blobs is not None:
            live_blobs = _ledger_tree_map(checkout, "origin/main")
            if live_blobs is None:
                return None
            for path, blob_sha in blobs.items():
                if live_blobs.get(path) != blob_sha:
                    return None
            # INS-REVIEW-105: presence of the staged blobs is
            # not the whole envelope — a path the envelope
            # DELETED (present in its base, absent in its tree)
            # must be absent here too. A landing that retains a
            # deleted file kept every staged blob and still is
            # not this envelope; the relay refuses it, and the
            # worker's tip check passed it.
            if _expected_stage_commit(expected):
                manifest = _envelope_manifest(checkout, expected)
                if manifest is None:
                    return None
                _, deleted = manifest
                for path in deleted:
                    if path in live_blobs:
                        return None
        return live
    except Exception as e:
        print(f"_guard_envelope_on_main: {type(e).__name__}: {e}",
              file=sys.stderr, flush=True)
        return None


def _expected_stage_commit(expected):
    """The staged envelope's commit, from a branch-read envelope
    ("commit") or a persisted record ("envelope_commit")."""
    if not isinstance(expected, dict):
        return None
    return expected.get("commit") or expected.get("envelope_commit")


def _envelope_manifest(checkout, expected):
    """The staged envelope's change manifest against its
    declared base (its single parent): (changed, deleted)
    ledger/** path sets — changed = added or modified by the
    envelope, deleted = present in the base and absent from the
    envelope's tree. None when the envelope names no commit,
    the commit does not have exactly one parent, or either
    tree cannot be read."""
    try:
        stage = _expected_stage_commit(expected)
        blobs = expected.get("blobs") \
            if isinstance(expected, dict) else None
        if not stage or not isinstance(blobs, dict):
            return None
        r = sh(f"git -C {checkout} rev-list --parents -n 1 "
               f"{stage}", timeout=60)
        if r.returncode != 0:
            return None
        parts = r.stdout.split()
        if len(parts) != 2:
            return None
        base_map = _ledger_tree_map(checkout, parts[1])
        if base_map is None:
            return None
        changed = {p for p, s in blobs.items()
                   if base_map.get(p) != s}
        deleted = {p for p in base_map if p not in blobs}
        return changed, deleted
    except Exception as e:
        print(f"_envelope_manifest: {type(e).__name__}: {e}",
              file=sys.stderr, flush=True)
        return None


def _envelope_matches_at(checkout, ref, job_id, expected,
                         deleted):
    """Full envelope equality at one commit: the heartbeat doc
    equals the staged doc (and names this job), every staged
    blob is present with the identical sha, and every manifest
    deletion is absent. Returns the doc, or None."""
    try:
        exp_doc = expected.get("heartbeat")
        blobs = expected.get("blobs")
        d = sh(f"git -C {checkout} show "
               f"{ref}:{GUARD_HEARTBEAT_REL}", timeout=60)
        if d.returncode != 0:
            return None
        doc = json.loads(d.stdout)
        if not isinstance(doc, dict) or doc != exp_doc \
                or str(doc.get("run_id")) != str(job_id):
            return None
        tree = _ledger_tree_map(checkout, ref)
        if tree is None:
            return None
        if any(tree.get(p) != s for p, s in blobs.items()):
            return None
        if any(p in tree for p in deleted):
            return None
        return doc
    except Exception:
        return None


def _guard_envelope_in_main_history(checkout, job_id, expected):
    """Confirm-at-M (PR #515 review, INS-REVIEW-092; landing
    binding hardened by INS-REVIEW-105): full-content equality
    as in _guard_envelope_on_main, evaluated at the commit
    where this envelope WAS main's state — its landing —
    instead of only at the moving tip, so a later envelope
    superseding it does not rewrite this attempt's verdict.

    The landing must be a REAL first-parent landing: either the
    recorded stage commit itself sits on main's first-parent
    chain (main passed through the exact staged tree), or a
    first-parent merge commit M with exactly two parents whose
    second parent IS the recorded stage commit, with M's tree
    carrying the full envelope (doc equality, every blob,
    manifest deletions absent) and no ledger path introduced
    by M outside the envelope's manifest. A stage commit merely
    REACHABLE from main — via a merge whose resulting tree
    dropped, altered or retained-around the payload — is not a
    landing: the previous implementation searched plain
    `git log` (which traverses side parents) and confirmed at
    the side-parent stage commit itself, accepting landings
    the relay had refused. Returns the heartbeat doc, or
    None."""
    try:
        if not isinstance(expected, dict):
            return None
        exp_doc = expected.get("heartbeat")
        blobs = expected.get("blobs")
        stage = _expected_stage_commit(expected)
        if not isinstance(exp_doc, dict) \
                or not isinstance(blobs, dict) or not stage:
            return None
        manifest = _envelope_manifest(checkout, expected)
        if manifest is None:
            return None
        changed, deleted = manifest
        manifest_paths = changed | deleted
        r = sh(f"git -C {checkout} rev-list --first-parent "
               f"--parents -n 400 origin/main", timeout=120)
        if r.returncode != 0:
            return None
        for line in r.stdout.splitlines():
            parts = line.split()
            if not parts:
                continue
            commit, parents = parts[0], parts[1:]
            if commit == stage:
                doc = _envelope_matches_at(
                    checkout, commit, job_id, expected, deleted)
                if doc is not None:
                    return doc
                continue
            if len(parents) != 2 or parents[1] != stage:
                continue
            doc = _envelope_matches_at(
                checkout, commit, job_id, expected, deleted)
            if doc is None:
                continue
            fp_map = _ledger_tree_map(checkout, parents[0])
            m_map = _ledger_tree_map(checkout, commit)
            if fp_map is None or m_map is None:
                continue
            introduced = {p for p in set(fp_map) | set(m_map)
                          if fp_map.get(p) != m_map.get(p)}
            if introduced <= manifest_paths:
                return doc
        return None
    except Exception as e:
        print(f"_guard_envelope_in_main_history: "
              f"{type(e).__name__}: {e}",
              file=sys.stderr, flush=True)
        return None


def _confirm_guard_envelope(checkout, job_id, branch,
                            timeout_s=None, poll_s=None,
                            attempt_id=None):
    """Poll main for this attempt's envelope heartbeat until the
    relay's merge lands it or the bound expires; returns the
    on-main doc, or None. The expected doc is read back from the
    staging branch (retried while unreadable) and the on-main
    heartbeat must BE that envelope — see
    _guard_envelope_on_main. Bounded by construction — the
    2026-11-22 guard stall (a claimed slot with no outcome for
    over an hour) must never recur on this path. The bounds are
    resolved from the module constants at call time (not bound
    as argument defaults) so tests can shrink them."""
    if timeout_s is None:
        timeout_s = GUARD_CONFIRM_TIMEOUT_S
    if poll_s is None:
        poll_s = GUARD_CONFIRM_POLL_S
    if attempt_id is None:
        attempt_id = _guard_attempt_id(job_id)
    deadline = time.monotonic() + timeout_s
    expected = None
    while True:
        if expected is None:
            staged = _staged_guard_envelope(checkout, branch)
            if staged is not None:
                if not _branch_envelope_producer_ok(
                        job_id, staged, attempt_id):
                    # INS-REVIEW-105: the branch carries another
                    # (or an unknown) attempt's envelope — never
                    # adopt it, and never rebind its record to
                    # this attempt; stand on this attempt's own
                    # persisted record only (loaded below).
                    print(f"_confirm_guard_envelope: the staged "
                          f"branch for {job_id} was not produced "
                          f"by this attempt — refusing adoption",
                          file=sys.stderr, flush=True)
                    staged = None
                elif _persist_guard_envelope(
                        job_id, branch, staged,
                        attempt_id=attempt_id) is None:
                    # Issue #499: persist before confirmation
                    # relies on it — the relay deletes the branch
                    # after its merge, possibly before a later
                    # poll or a worker restart needs the expected
                    # content again. INS-REVIEW-105: a required
                    # persistence failure here fails closed —
                    # the earlier code ignored the None and went
                    # on to confirm an envelope with no durable
                    # record anywhere.
                    print(f"_confirm_guard_envelope: the durable "
                          f"envelope record for {job_id} could "
                          f"not be established — failing closed",
                          file=sys.stderr, flush=True)
                    return None
                else:
                    expected = staged
            if expected is None:
                # Branch already gone (relay merged + deleted, or
                # a restart): stand on the persisted record plus
                # the PR/merge evidence, not the branch. The
                # record must belong to THIS attempt (PR #515
                # review) — an earlier attempt's landed envelope
                # is not this attempt's confirmation.
                expected = _load_persisted_guard_envelope(
                    job_id, attempt_id=attempt_id)
        if expected is not None:
            doc = _guard_envelope_on_main(checkout, job_id,
                                          expected)
            if doc is None:
                # Confirm at M, not only at the tip (PR #515
                # review): a later envelope may already have
                # superseded this one on main — the verdict is
                # read where this envelope landed.
                doc = _guard_envelope_in_main_history(
                    checkout, job_id, expected)
            if doc is not None:
                # PR #515 review: the bound is honoured BEFORE
                # accepting a document — the persist + fetch
                # above can themselves consume the remaining
                # budget, and a pass that started inside the
                # bound must not return success after it.
                if time.monotonic() > deadline:
                    return None
                return doc
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return None
        time.sleep(min(poll_s, remaining))

def _write_bus_json(rel_name, payload, message):
    """Write one JSON file onto the queue branch (best-effort)."""
    try:
        p = BUS / "queue" / rel_name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(payload, indent=1))
        return push_bus(message)
    except Exception as e:
        print(f"_write_bus_json {rel_name}: {type(e).__name__}: {e}",
              file=sys.stderr, flush=True)
        return False


def run_ledger_guard(job):
    """Execute one `ledger-guard` job (issue #443 envelope design).

    Returns True ONLY when the run's envelope heartbeat is
    confirmed on main — the caller then marks the slot done
    (issue #434's done-gate, unchanged). The envelope is staged on
    publish/ledger-<job-id>: by the publisher (validated ledger +
    ok heartbeat, or the heartbeat alone when the ledger is
    unchanged), or — when the publisher fails or refuses — by the
    worker as a failed-status heartbeat-only envelope. The relay
    lands it on main; a slot whose envelope never lands stays
    un-done and is recorded (ledger-failure.json + missed-<slot>
    marker).

    Hang-proofing (2026-11-22 evidence: guard-2026-11-22T0847Z was
    claimed at 08:50:57Z and produced NO outcome for over an hour
    while the same worker completed other jobs — the old bare
    subprocess.run(timeout=...) kills only the publisher process
    on expiry, and a surviving grandchild holding the output
    pipes can block the output collect indefinitely): the
    publisher now runs under sh_group (the whole process group is
    killed and verified empty on timeout), the confirmation wait
    is bounded, every git call carries its own timeout, and ANY
    exit from this function — success, failure, timeout,
    unexpected exception — has either confirmed the heartbeat on
    main or left a durable bus record. Silence is the one outcome
    this function no longer produces."""
    try:
        return _run_ledger_guard(job)
    except Exception as e:
        print(f"run_ledger_guard: unexpected {type(e).__name__}: "
              f"{e}", file=sys.stderr, flush=True)
        try:
            _write_bus_json(
                "ledger-failure.json",
                {"kind": "guard-error", "job_id": job.get("id"),
                 "at": now(), "worker": os.uname().nodename,
                 "detail": f"unexpected {type(e).__name__}: {e}"},
                f"ledger guard error {job.get('id')}")
        except Exception:
            pass
        return False


def _run_ledger_guard(job):
    job_id = job["id"]
    branch = _guard_branch(job_id)
    # PR #515 review: this execution's attempt identity (from
    # the claim record) — envelope records persisted below are
    # bound to it, and confirmation accepts only this attempt's
    # record as fallback evidence.
    attempt_id = _guard_attempt_id(job_id)
    checkout = _ensure_main_checkout()
    if checkout is None:
        print("run_ledger_guard: main checkout unavailable; refusing",
              file=sys.stderr, flush=True)
        _write_bus_json(
            "ledger-failure.json",
            {"kind": "setup-failed", "job_id": job_id,
             "at": now(), "worker": os.uname().nodename,
             "detail": "main checkout unavailable; guard refused"},
            f"ledger guard setup failed {job_id}")
        return False
    if not scripts_match(checkout, CODE, GUARD_SCRIPTS):
        print("run_ledger_guard: publisher scripts on main differ "
              "from the reviewed release copies; refusing to execute "
              "unreviewed code (D2)", file=sys.stderr, flush=True)
        _write_bus_json(
            "ledger-failure.json",
            {"kind": "setup-failed", "job_id": job_id,
             "at": now(), "worker": os.uname().nodename,
             "detail": "publisher scripts on main differ from the "
                       "reviewed release copies (D2); guard "
                       "refused"},
            f"ledger guard setup failed {job_id}")
        # The refusal still leaves its liveness evidence for the
        # relay to land (staged failed heartbeat, confirmed when
        # it lands) — but the slot is NOT done either way: a D2
        # refusal retries after adoption, as before.
        if _stage_guard_heartbeat(checkout, branch, "failed",
                                  job_id, attempt_id=attempt_id):
            _confirm_guard_envelope(checkout, job_id, branch,
                                    attempt_id=attempt_id)
        return False
    env = _guard_env()
    env["LEDGER_RUN_ID"] = str(job_id)
    # INS-REVIEW-093: the publisher establishes the durable
    # envelope record BEFORE its own staging push, in the same
    # pending-envelopes dir and bound to this attempt — so the
    # record exists even when the publisher dies before the
    # capture below, and even when this process dies before
    # writing its own copy.
    env["GATOR_PENDING_ENVELOPES"] = str(PENDING_ENVELOPES)
    if attempt_id is not None:
        env["LEDGER_ATTEMPT_ID"] = attempt_id
    _assert_no_denied(env)
    cmd = shlex.join(
        [sys.executable,
         str(checkout / "scripts" / "ledger_publish.py"),
         "--commit", "--fail-hard",
         "--publish-branch", branch, "--guard-heartbeat"])
    timed_out = False
    detail = ""
    try:
        r = sh_group(cmd, cwd=str(checkout), env=env,
                     timeout=GUARD_PUBLISH_TIMEOUT_S)
        rc = r.returncode
        out, err = r.stdout or "", r.stderr or ""
    except subprocess.TimeoutExpired as e:
        timed_out = True
        rc = -1
        out, err = e.output or "", e.stderr or ""
        if isinstance(out, bytes):
            out = out.decode("utf-8", "replace")
        if isinstance(err, bytes):
            err = err.decode("utf-8", "replace")
    if out.strip():
        print(out[-2000:], flush=True)
    if err.strip():
        print(err[-2000:], file=sys.stderr, flush=True)
    if timed_out:
        detail = (f"publisher exceeded the "
                  f"{GUARD_PUBLISH_TIMEOUT_S}s guard bound; its "
                  "process group was killed and verified empty "
                  "(issue #443 hang-proofing)")
        _write_bus_json(
            "ledger-failure.json",
            {"kind": "publish-timeout", "job_id": job_id,
             "at": now(), "worker": os.uname().nodename,
             "detail": detail + "; publisher tail: "
                       + (out + err)[-400:]},
            f"ledger publish timed out {job_id}")
    elif rc != 0:
        # The publisher's durable API signal needs an Issues-capable
        # token the worker PAT is not; mirror the failure to the bus
        # for Moos to file (see the section header above).
        detail = (out + err)[-500:]
        _write_bus_json(
            "ledger-failure.json",
            {"kind": "publish-failed", "job_id": job_id,
             "at": now(), "worker": os.uname().nodename,
             "detail": detail},
            f"ledger publish failed {job_id}")
    # PR #515 review (persist-before-handoff): capture the
    # envelope the publisher staged — read back from the REMOTE
    # branch, i.e. the commit the publisher actually pushed and
    # accepted, never the local HEAD — and persist it NOW,
    # before any fallback staging or confirmation. The relay
    # may merge and delete the branch before the worker's first
    # confirmation fetch; without this capture a successful
    # publisher leaves no envelope record, and the worker would
    # skip verification and mark the slot missed even when main
    # contains the exact envelope.
    pub_env = _staged_guard_envelope(checkout, branch)
    if pub_env is not None and _persist_guard_envelope(
            job_id, branch, pub_env,
            attempt_id=attempt_id) is None:
        # INS-REVIEW-093: a required durable record that cannot
        # be established blocks the handoff — no fallback staging
        # and no confirmation may proceed on an envelope whose
        # record does not exist.
        print(f"run_ledger_guard: the durable envelope record "
              f"for {job_id} could not be established — failing "
              "closed, handoff blocked", file=sys.stderr,
              flush=True)
        _write_bus_json(
            "ledger-failure.json",
            {"kind": "envelope-record-failed", "job_id": job_id,
             "at": now(), "worker": os.uname().nodename,
             "detail": "the durable envelope record could not "
                       "be established after the publisher "
                       "staged; handoff blocked (INS-REVIEW-093)"},
            f"ledger envelope record failed {job_id}")
        return False
    if rc != 0:
        # Failed-status heartbeat only — never stage the (possibly
        # invalid) ledger outputs the publisher refused. When the
        # publisher had in fact already staged its envelope before
        # dying, _stage_guard_heartbeat leaves it untouched and the
        # confirmation below reconciles on the on-main status.
        _stage_guard_heartbeat(checkout, branch, "failed", job_id,
                               attempt_id=attempt_id)
    doc = _confirm_guard_envelope(checkout, job_id, branch,
                                  attempt_id=attempt_id)
    if doc is None:
        # Issue #434: the heartbeat is the guard run's archive — a
        # slot whose heartbeat never landed must not read done.
        # Record it on the bus (signal + missed marker) and refuse
        # done; the next hourly slot retries.
        print(f"run_ledger_guard: envelope for {job_id} not "
              f"confirmed on main within "
              f"{GUARD_CONFIRM_TIMEOUT_S}s; refusing done",
              file=sys.stderr, flush=True)
        detail2 = (f"staged envelope on {branch} not confirmed on "
                   f"main after {GUARD_CONFIRM_TIMEOUT_S}s; slot "
                   "not marked done")
        if detail:
            detail2 += f"; publisher outcome: {detail}"
        _write_bus_json(
            "ledger-failure.json",
            {"kind": "envelope-unconfirmed", "job_id": job_id,
             "at": now(), "worker": os.uname().nodename,
             "detail": detail2},
            f"ledger envelope unconfirmed {job_id}")
        suffix = job_id[len("guard-"):] \
            if str(job_id).startswith("guard-") else job_id
        _write_bus_json(
            f"missed-{suffix}.json",
            {"job_id": job_id, "job": "ledger-guard",
             "at": now(), "worker": os.uname().nodename,
             "reason": "guard ran but its envelope heartbeat did "
                       "not land on main via the publish relay — "
                       "slot not marked done; the next hourly "
                       "guard retries (issues #434, #443)"},
            f"missed guard envelope {job_id}")
        return False
    if rc != 0 and str(doc.get("status")) == "ok":
        # The publisher reported failure yet a success envelope
        # landed (it staged, then died before reporting): main is
        # the truth — the publish DID land.
        print(f"run_ledger_guard: publisher rc={rc} but the ok "
              f"envelope for {job_id} is confirmed on main — "
              "counting the publish as landed", flush=True)
    return True


def _guard_slot_time(job_id):
    """Slot UTC of a `guard-YYYY-MM-DDTHHMMZ` id, or None when the
    id does not parse as a guard slot."""
    m = GUARD_SLOT_RE.match(str(job_id))
    if not m:
        return None
    try:
        return datetime(int(m.group(1)), int(m.group(2)),
                        int(m.group(3)), int(m.group(4)),
                        int(m.group(5)), tzinfo=timezone.utc)
    except ValueError:
        return None


def guard_pending_from_bus(queue_ids, claim_ids, done_ids, now=None):
    """Pure: True when a guard slot is queued or claimed but not
    done — the worker-bus equivalent of the watchdog's #156
    pending-Actions-run check. Issue #434: only a slot whose slot
    time is within the claim-staleness horizon (STALE_CLAIM_HOURS)
    counts. queue.json is append-only, so a slot that never
    completed stays listed forever — the old set-only rule read the
    2026-11-19 0647Z slot as "pending" a full day later and
    suppressed every watchdog page while the heartbeat went stale
    (1547Z/1647Z/1747Z, 2026-11-20). A slot older than the horizon
    is stale evidence, not a pending execution, and must not
    suppress the page. A future-dated slot is not pending either
    (CodeRabbit #440: a negative age passed the horizon check, so
    an injected future id would suppress the page — the scheduler
    never produces one). An id that does not parse as a guard slot
    is not pending either (fail-safe towards paging, matching the
    watch script's unknown-pending rule)."""
    if now is None:
        now = datetime.now(timezone.utc)
    live = (set(queue_ids) | set(claim_ids)) - set(done_ids)
    for job_id in live:
        if not str(job_id).startswith("guard-"):
            continue
        slot = _guard_slot_time(job_id)
        if slot is None:
            continue
        age = (now - slot).total_seconds()
        if 0 <= age < STALE_CLAIM_HOURS * 3600:
            return True
    return False


def _mirror_calibration_alert(job, cal_out):
    """INS-DEV-004: mirror the watch's calibration decision onto the
    bus as queue/calibration-alert.json (same reason as the guard
    alert: the worker PAT cannot file issues, Moos's side does).
    A missing signal file means the check was "unknown" (ledger
    unreadable): nothing is written and an existing alert stays.
    An unreadable file or a failed push returns False so the watch
    job is not marked done and the next watch retries. Runs before
    the guard decision so a suppressed guard page never hides a
    calibration alert."""
    try:
        payload = json.loads(Path(cal_out).read_text())
    except FileNotFoundError:
        return True
    except Exception as e:
        print(f"run_ledger_watchdog: calibration signal unreadable "
              f"for {job['id']}: {e}; refusing done",
              file=sys.stderr, flush=True)
        return False
    if payload and payload.get("action") == "create":
        if not _write_bus_json(
                "calibration-alert.json",
                {"state": "alert", "at": now(),
                 "worker": os.uname().nodename, "job_id": job["id"],
                 "signal": payload},
                f"calibration alert {job['id']}"):
            print(f"run_ledger_watchdog: calibration-alert push "
                  f"failed for {job['id']}; refusing done",
                  file=sys.stderr, flush=True)
            return False
        return True
    alert = BUS / "queue" / "calibration-alert.json"
    if alert.exists():
        try:
            cur = json.loads(alert.read_text())
        except Exception:
            cur = {}
        if cur.get("state") == "alert":
            if not _write_bus_json(
                    "calibration-alert.json",
                    {"state": "recovered", "at": now(),
                     "worker": os.uname().nodename,
                     "job_id": job["id"],
                     "reason": (payload or {}).get(
                         "reason", "no cell outside tolerance")},
                    f"calibration recovered {job['id']}"):
                print(f"run_ledger_watchdog: calibration-recovered "
                      f"push failed for {job['id']}; refusing done",
                      file=sys.stderr, flush=True)
                return False
    return True


def run_ledger_watchdog(job):
    """Execute one `ledger-watchdog` job: run the watchdog script
    against the main checkout's heartbeat file, with the pending
    state taken from the bus, and mirror its signal decision to
    queue/guard-alert.json (the worker PAT cannot file issues —
    see the section header). Returns True only when the check ran
    AND any signal decision reached the bus. Issue #434: the old
    code returned True whenever the script had run, ignoring
    whether the alert push landed — a watch job could read done
    while its page never reached the bus, exactly like the guard
    slots it watches. A failed alert/recovery write now returns
    False, so the watch job stays un-done and the next half-hour
    watch retries the page."""
    checkout = _ensure_main_checkout()
    if checkout is None:
        print("run_ledger_watchdog: main checkout unavailable",
              file=sys.stderr, flush=True)
        return False
    if not scripts_match(checkout, CODE, WATCH_SCRIPTS):
        print("run_ledger_watchdog: watchdog scripts on main differ "
              "from the reviewed release copies; refusing (D2)",
              file=sys.stderr, flush=True)
        return False
    # Issue #402: read_queue() returns the raw parsed list, so a
    # non-object entry raised AttributeError here before the
    # watchdog ran; quarantine with evidence, never crash.
    queue_ids = [str(j.get("id", "")) for j in
                 _quarantine_non_object_entries(read_queue())]
    claims_dir = BUS / "queue" / "claims"
    claim_ids = [f.name[:-len(".json")] for f in
                 claims_dir.glob("*.json")] if claims_dir.exists() else []
    done_dir = BUS / "queue" / "done"
    done_ids = [f.name[:-len(".json")] for f in
                done_dir.glob("*.json")] if done_dir.exists() else []
    pending = guard_pending_from_bus(queue_ids, claim_ids, done_ids)
    out = OUT / f"{job['id']}-signal.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    # Issue #434: a stale signal-out from an earlier run must not
    # masquerade as this run's decision — remove it first, so a
    # payload present afterwards was written by this run.
    out.unlink(missing_ok=True)
    cal_out = OUT / f"{job['id']}-calibration-signal.json"
    cal_out.unlink(missing_ok=True)
    env = _guard_env()
    _assert_no_denied(env)
    r = subprocess.run(
        [sys.executable,
         str(checkout / "scripts" / "ledger_guard_watch.py"),
         "--heartbeat", str(checkout / GUARD_HEARTBEAT_REL),
         "--guard-pending", "yes" if pending else "no",
         "--ledger", str(checkout / GUARD_LEDGER_REL),
         "--calibration-signal-out", str(cal_out),
         "--signal-out", str(out)],
        cwd=checkout, env=env, capture_output=True, text=True,
        timeout=600)
    if r.stdout.strip():
        print(r.stdout[-2000:], flush=True)
    if r.stderr.strip():
        print(r.stderr[-2000:], file=sys.stderr, flush=True)
    if r.returncode != 0:
        print(f"run_ledger_watchdog: watch script exited "
              f"{r.returncode} for {job['id']}; refusing done",
              file=sys.stderr, flush=True)
        return False
    if not _mirror_calibration_alert(job, cal_out):
        return False
    try:
        payload = json.loads(out.read_text())
    except FileNotFoundError:
        payload = None
    except Exception as e:
        # CodeRabbit #440: only a missing file is the designed
        # no-signal suppression. An existing but unreadable or
        # malformed signal file must NOT read as suppression — the
        # page it carried would be dropped silently. Refuse done;
        # the next half-hour watch retries.
        print(f"run_ledger_watchdog: signal file unreadable for "
              f"{job['id']}: {e}; refusing done",
              file=sys.stderr, flush=True)
        return False
    if payload is None:
        # The script exited 0 without writing a payload: the only
        # designed path is the #156 suppression (stale heartbeat
        # with a guard run pending — deliberately no signal file,
        # see test_cli_stale_pending_suppresses_signal_dry_run).
        # That is a legitimate no-signal outcome, not a failure:
        # the check ran, nothing was due to be paged.
        print(f"run_ledger_watchdog: guard run pending for "
              f"{job['id']} — page suppressed, check done",
              flush=True)
        return True
    if payload and payload.get("action") == "create":
        if not _write_bus_json(
                "guard-alert.json",
                {"state": "dead", "at": now(),
                 "worker": os.uname().nodename, "job_id": job["id"],
                 "signal": payload},
                f"guard alert {job['id']}"):
            print(f"run_ledger_watchdog: guard-alert push failed "
                  f"for {job['id']}; refusing done",
                  file=sys.stderr, flush=True)
            return False
    else:
        # Fresh or suppressed: if an alert is on the bus, flip it to
        # recovered so Moos's side closes the signal issue.
        alert = BUS / "queue" / "guard-alert.json"
        if alert.exists():
            try:
                cur = json.loads(alert.read_text())
            except Exception:
                cur = {}
            if cur.get("state") == "dead":
                if not _write_bus_json(
                        "guard-alert.json",
                        {"state": "recovered", "at": now(),
                         "worker": os.uname().nodename,
                         "job_id": job["id"],
                         "reason": (payload or {}).get(
                             "reason", "heartbeat fresh")},
                        f"guard recovered {job['id']}"):
                    print(f"run_ledger_watchdog: guard-recovered "
                          f"push failed for {job['id']}; refusing done",
                          file=sys.stderr, flush=True)
                    return False
    return True


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
    """Issue #390: the checkout HEAD is diagnostics only (#382) —
    a failed lookup must never become a job failure. sh() raises
    subprocess.TimeoutExpired on a timeout and OSError when git is
    missing, so an unguarded call here raises out of every call
    site — including the manifest-creation site in _execute_body,
    which runs after intent persistence and would block publish +
    done, leaving the job uncertain. Return "" on any lookup
    failure so publication proceeds with code_sha intact; the
    lookup stays bounded by its 30s timeout. (self_update is the
    one exception: it fails closed on "" — see its own guard —
    because adopting a tip with no known running revision would
    skip the D2 ancestry check.)"""
    try:
        r = sh(f"git -C {CODE} rev-parse HEAD", timeout=30)
    except (subprocess.TimeoutExpired, OSError):
        return ""
    return r.stdout.strip() if r.returncode == 0 else ""


def registry():
    # D2: templates come from the release-branch checkout that
    # self_update maintains — never main tip, never the low-trust
    # queue branch (INS-R3-02). No pull here: self_update runs
    # first each cycle and is the only place the checkout moves.
    _ensure_update_checkout()
    return json.loads((CODE / "registry" / "tools.json").read_text())


def job_text(job):
    """Issue #381: the queue's `job` field is untrusted input —
    normalize it to a string before any .split()/.lower() call.
    A missing, None, or non-string value becomes "" (an empty job
    string): the #371 fail-closed branch then records a named
    failure instead of raising AttributeError after intent
    persistence. Non-string values are rejected explicitly with
    their own named failure in _execute_body; this helper only
    ever feeds parsing and dispatch, never the manifest —
    manifest["job"] keeps the raw queued value as evidence."""
    if not isinstance(job, dict):
        return ""
    value = job.get("job")
    return value if isinstance(value, str) else ""


def parse_job(job, reg):
    """Reuse the orchestrator's grammar, minimally: run/category/
    sweep-lite/sweep, sequential only (the worker is one machine —
    the COMMANDS race cannot happen here)."""
    tools = {t["id"]: t for t in reg["tools"] if t.get("status") == "active"}
    # Issue #381: the job string is untrusted queue input — a None
    # (or non-string) job used to crash here (None.split()) after
    # intent persistence. Treat it as an empty job string: the
    # caller fails closed on the empty plan.
    parts = (job if isinstance(job, str) else "").split()
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


def classify_empty_plan(job):
    """Issue #381: WHY parse_job returned [] for this job string.
    The #371 `unknown-job` status is one umbrella over distinct
    causes — the manifest keeps that single status (test_worker_371
    pins it) and records this cause beside it, so a deliberately
    rejected selection is distinguished in the record from unknown
    syntax instead of conflated under it:
      "empty-job" — no job text at all ("" / whitespace / None).
      "unknown-syntax" — the kind token is not a known job kind,
        or a known kind is missing its arguments.
      "invalid-selection" — known kind, well-formed arguments, but
        the selection/filter emptied the plan (unknown tool id or
        category, a filter token parse_job rejects, a market= with
        no matching tool, a ticker the registry grammar refuses).
    The cause is derived from the grammar alone, never from the
    registry, so it stays truthful even when the registry is stale."""
    parts = (job if isinstance(job, str) else "").split()
    if not parts:
        return "empty-job"
    kind = parts[0]
    if kind not in ("run", "category", "sweep", "sweep-lite"):
        return "unknown-syntax"
    if kind in ("run", "category") and len(parts) < 3:
        return "unknown-syntax"
    if kind in ("sweep", "sweep-lite") and len(parts) < 2:
        return "unknown-syntax"
    return "invalid-selection"


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
    # Issue #158: the venv must match the PINNED ref's requirements,
    # not whatever it contained when it was first created. Deps used
    # to install only inside `if not py.exists()`, so a promoted ref
    # that changed requirements.txt reused stale deps, and the
    # venv/pip return codes were unchecked — a failed install still
    # ran the tool against wrong/missing deps. The venv now records
    # the sha256 of the requirements it was built from; any change
    # recreates the venv and reinstalls (a full recreate, so a dep
    # REMOVED from requirements.txt disappears too), and a venv/pip
    # failure fails the tool loudly (venv-failed / deps-failed) with
    # the tool never run. A failed install leaves no marker, so the
    # next run retries. A venv built by the old code has no marker,
    # so it is rebuilt on its next run.
    venv = VENVS / tool
    py = venv / "bin" / "python"
    req = repo / "requirements.txt"
    req_sha = _sha256_file(req) if req.exists() else ""
    marker = venv / ".gator-requirements-sha"
    installed_sha = marker.read_text().strip() if marker.is_file() else ""
    if not py.exists() or installed_sha != req_sha:
        if venv.exists():
            sh(f"rm -rf {venv}", timeout=60)
        if sh(f"python3 -m venv {venv}",
              timeout=300).returncode != 0:
            return "venv-failed", "python3 -m venv failed"
        if not py.exists():
            # A zero rc that produced no interpreter is a failed
            # venv all the same — never run the tool against the
            # system python with the venv's PATH prefix missing.
            return "venv-failed", ("python3 -m venv returned 0 but "
                                   "no interpreter at " + str(py))
        if req.exists():
            r = sh(f"{venv}/bin/pip install -q -r {req}", timeout=1800)
            if r.returncode != 0:
                return "deps-failed", (r.stdout + r.stderr)[-4000:]
        marker.write_text(req_sha)
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


def _archive_tree_has(arch, sha, expected):
    """Verify the tree at ``sha`` in the archive checkout holds every
    (relpath, local_path) pair at the exact content: the blob SHA
    recorded in the tree must equal ``git hash-object`` of the local
    file. A changed HEAD alone proves nothing (issue #257) — this
    proves the run's bytes are in the commit. Returns True only
    when every expected file matches."""
    for rel, local in expected:
        tree = sh(f"git -C {arch} ls-tree {sha} -- {rel}",
                  timeout=60)
        if tree.returncode != 0:
            print(f"publish: verify: ls-tree failed for {rel}",
                  flush=True)
            return False
        parts = tree.stdout.split()
        if len(parts) < 3:
            print(f"publish: verify: {rel} absent from tree "
                  f"{sha[:12]}", flush=True)
            return False
        blob = parts[2]
        hashed = sh(f"git -C {arch} hash-object {local}",
                    timeout=60)
        if hashed.returncode != 0:
            print(f"publish: verify: hash-object failed for "
                  f"{local}", flush=True)
            return False
        if hashed.stdout.strip() != blob:
            print(f"publish: verify: {rel} blob mismatch "
                  f"(tree {blob[:12]} != local "
                  f"{hashed.stdout.strip()[:12]})", flush=True)
            return False
    return True


def _publish_harvest_attachments(results_dir, arch):
    """Issue #279: copy harvested attachment PDFs next to the stable
    harvest pointer (harvest/<CODE>.json) so an item's pointer
    "attachments/<NewsID>.pdf" resolves inside the archive. The same
    files also ride the wholesale results copy into worker-runs/; this
    copy is what makes the pointer usable from harvest/<CODE>.json.
    Only safe .pdf filenames are copied; anything else is skipped,
    never renamed. Returns the number of files copied (0 when the
    harvester stored none — older harvests have no attachments dir).
    """
    src = Path(results_dir) / "egx-harvest" / "results" / "attachments"
    if not src.is_dir():
        return 0
    dest = Path(arch) / "harvest" / "attachments"
    dest.mkdir(parents=True, exist_ok=True)
    n = 0
    for f in sorted(src.iterdir()):
        if not f.is_file() or f.suffix.lower() != ".pdf":
            continue
        if not re.fullmatch(r"[A-Za-z0-9_.\-]+", f.name):
            continue
        (dest / f.name).write_bytes(f.read_bytes())
        n += 1
    return n


def publish(job, results_dir, manifest):
    arch = ROOT / "archive-push"
    if not arch.exists():
        url = os.environ["GATOR_BUS_URL"]
        # Issue #257: sh() never raises — an unchecked clone failure
        # used to fall through and commit against whatever was on
        # disk. Every copy/add/commit step below is enforced the
        # same way; any failure is a publish failure, loud on the bus.
        if sh(f"git clone --branch archive --single-branch {url} {arch}",
              timeout=900).returncode != 0:
            print("publish: archive clone failed", flush=True)
            return False
        # The bus clone gets its identity in sync_bus; this clone needs
        # its own — without it every commit fails silently (found by
        # the w2 self-test, 2026-11-14: claimed, ran, never published).
        sh(f"git -C {arch} config user.email worker@borsagator.local",
           timeout=30)
        sh(f"git -C {arch} config user.name borsagator-worker", timeout=30)
    else:
        sh(f"git -C {arch} pull --ff-only", timeout=180)
    # Identity is needed for the commit below however this checkout
    # was created. publish() set it only on its own clone, so a
    # checkout made by anything else (a harness clone, a fresh worker
    # image, a manual clone) committed nothing — and because sh()
    # never raises, publish still returned the old HEAD as if it had
    # published. Ensure it here, every run; git config is idempotent.
    sh(f"git -C {arch} config user.email worker@borsagator.local",
       timeout=30)
    sh(f"git -C {arch} config user.name borsagator-worker", timeout=30)
    # INS-R3-01: the slug reaches shell strings below — reduce it to
    # a safe alphabet so a crafted job string cannot inject commands
    # ($(…), backticks, ;) into the publish step, which runs even
    # for jobs that failed parsing. Issue #381: job_text() — a None
    # (or non-string) job used to crash here (.lower()) after the
    # #371 branch had already decided to publish the failure.
    slug = re.sub(r"[^a-z0-9]+", "-", job_text(job).lower()).strip("-")[:60]
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d/%H%M%S")
    dest = arch / "worker-runs" / f"{ts}__{slug}__{job['id']}"
    # Issue #257: copy failures used to ride on silently (sh() never
    # raises) and the commit then archived a partial run.
    if sh(f"mkdir -p {dest} && cp -r {results_dir}/. {dest}/",
          timeout=300).returncode != 0:
        print(f"publish: fleet copy to {dest} failed", flush=True)
        return False
    # Issue #67: the merge stages under results_dir/_merge_out — it
    # is not a fleet result and must not ride into worker-runs/.
    if sh(f"rm -rf {dest}/_merge_out", timeout=60).returncode != 0:
        print("publish: _merge_out strip failed", flush=True)
        return False
    # 959m F5: an abandoned gdelt restore stage (rollback evidence, kept
    # locally under the workdir) is not a fleet result; strip it from the
    # published copy only, never from results_dir.
    if _strip_restore_stages(dest) != 0:
        print("publish: gdelt restore-stage strip failed", flush=True)
        return False
    (dest / "manifest.json").write_text(json.dumps(manifest, indent=1))
    # Issue #67: a merged sweep rides the SAME commit as its fleet
    # (one commit, one push): copy the merge's sweeps/ tree to the
    # archive root alongside worker-runs/.
    merge_out = Path(results_dir) / "_merge_out"
    if merge_out.is_dir():
        if sh(f"cp -r {merge_out}/. {arch}/",
              timeout=300).returncode != 0:
            print("publish: merge_out copy failed", flush=True)
            return False
    # maybe_compile fail-closed handoff: an unvalidated model that
    # could neither be quarantined nor removed locally (read-only
    # tree) must NOT publish; the hook recorded the path to drop
    # plus cleanup_failed evidence in the run manifest. The
    # compiler's own #161 ".quarantined" artifact is a local
    # inspection file — the Actions wiring archives only
    # report-model.json / compile_error.txt — so it is excluded here
    # too: unvalidated model bytes never ride the archive under a
    # renamed file. Independently of the handoff, EVERY non-compiled
    # outcome (refused/error) with a valid sweep_dir drops that
    # sweep's exact report-model.json — the wholesale copy never
    # deletes, so a previous commit's model at the same path would
    # otherwise survive a refusal (false green) — and a compiled
    # outcome drops a previous commit's stale compile_error.txt.
    # Removal is direct pathlib, never a shell string;
    # the only removable paths are the recorded sweep's
    # report-model.json (when the hook recorded suppress_model) and
    # its .quarantined sibling; and a removal that cannot be verified
    # REFUSES the publish (truthful False, fleet held for the cycle
    # report) rather than letting an unchecked model ride a green
    # commit.
    compile_block = manifest.get("compile") \
        if isinstance(manifest, dict) else None
    if not isinstance(compile_block, dict):
        compile_block = {}
    sweep_rel = compile_block.get("sweep_dir")
    suppress = compile_block.get("suppress_model")
    status = compile_block.get("status")
    valid_sweep = isinstance(sweep_rel, str) and sweep_rel \
        and not sweep_rel.startswith("/") \
        and all(part not in ("", ".", "..")
                for part in sweep_rel.split("/"))
    if suppress is not None and not valid_sweep:
        print(f"publish: refusing: suppress_model {suppress!r} "
              f"recorded without a valid sweep_dir", flush=True)
        return False
    if suppress is not None and status == "compiled":
        # contradictory evidence: a compiled outcome never records
        # suppress_model — refusing beats guessing which to trust.
        print(f"publish: refusing: status 'compiled' with "
              f"suppress_model {suppress!r} recorded", flush=True)
        return False
    drop = []
    if valid_sweep:
        drop.append(f"{sweep_rel}/report-model.json.quarantined")
        if status == "compiled":
            # the compiler clears the LOCAL stale marker on success
            # (#161 _clear_error_marker); the archive side is ours:
            # a previous commit's refusal marker at this path must
            # not sit next to the new model.
            drop.append(f"{sweep_rel}/compile_error.txt")
        elif status in ("refused", "error"):
            # cp never deletes: without this drop, a PREVIOUS
            # commit's report-model.json at the same sweep path
            # survives the wholesale _merge_out copy and the tree
            # keeps a model the compiler refused or never produced
            # — a false green. Every non-compiled outcome drops the
            # exact model path, not only cleanup-failure handoffs.
            drop.append(f"{sweep_rel}/report-model.json")
    if suppress is not None:
        if suppress != f"{sweep_rel}/report-model.json":
            print(f"publish: refusing: suppress_model {suppress!r} "
                  f"is not the recorded sweep's report-model.json",
                  flush=True)
            return False
        if suppress not in drop:
            drop.append(suppress)
    # Issue #69: maybe_render fail-closed handoff, mirroring the
    # compile one above. The wholesale _merge_out copy never
    # deletes, so a previous commit's report twins at the same
    # sweep path would otherwise survive a render refusal (a false
    # green: a report beside a refused model). Every non-rendered
    # outcome drops the exact twins; a rendered outcome drops a
    # previous commit's stale render_error.txt. A suppress_render
    # list (twins the hook could not remove locally) must name
    # exactly this sweep's twins, and a rendered outcome never
    # records one — contradictory evidence refuses the publish.
    render_block = manifest.get("render") \
        if isinstance(manifest, dict) else None
    if not isinstance(render_block, dict):
        render_block = {}
    render_rel = render_block.get("sweep_dir")
    render_status = render_block.get("status")
    suppress_render = render_block.get("suppress_render")
    render_valid = isinstance(render_rel, str) and render_rel \
        and not render_rel.startswith("/") \
        and all(part not in ("", ".", "..")
                for part in render_rel.split("/"))
    if suppress_render is not None and not render_valid:
        print(f"publish: refusing: suppress_render {suppress_render!r} "
              f"recorded without a valid sweep_dir", flush=True)
        return False
    if suppress_render is not None and render_status == "rendered":
        print(f"publish: refusing: status 'rendered' with "
              f"suppress_render {suppress_render!r} recorded",
              flush=True)
        return False
    if render_valid:
        if render_status == "rendered":
            drop.append(f"{render_rel}/render_error.txt")
        elif render_status in ("refused", "error", "skipped"):
            drop.append(f"{render_rel}/report.html")
            drop.append(f"{render_rel}/report.md")
    if suppress_render is not None:
        if not isinstance(suppress_render, list) or sorted(
                suppress_render) != sorted(
                [f"{render_rel}/report.html",
                 f"{render_rel}/report.md"]):
            print(f"publish: refusing: suppress_render "
                  f"{suppress_render!r} is not the recorded sweep's "
                  f"report twins", flush=True)
            return False
        for rel in suppress_render:
            if rel not in drop:
                drop.append(rel)
    arch_resolved = arch.resolve()
    for rel in drop:
        target = arch / rel
        try:
            if arch_resolved not in target.resolve().parents:
                print(f"publish: refusing: {rel} escapes the "
                      f"archive checkout", flush=True)
                return False
            if target.is_symlink() or target.is_file():
                target.unlink()
            if target.exists():
                print(f"publish: refusing: could not remove {rel} "
                      f"from the archive checkout", flush=True)
                return False
        except OSError as exc:
            print(f"publish: refusing: cannot exclude {rel}: "
                  f"{exc}", flush=True)
            return False
    # Issue #91: keep a stable pointer to the newest harvest per EGX
    # code at harvest/<CODE>.json on this branch. GitHub Actions
    # runs have no local harvest, so fetch_feed.py fetches the
    # pointer from the public repo; worker-runs/ keeps the full
    # timestamped history. Sources: a successful harvest-egx job's
    # own output, or the harvest-pointer/ stash _execute leaves
    # when a news run used the local harvest cache.
    ptr_src = []
    # Issue #348: tokenize on whitespace exactly like the #346 F9
    # fix did for top30-enumerate (and like run_harvest's own
    # .split()), so a leading-space harvest job refreshes the
    # pointer instead of silently skipping it. Issue #381: job_text()
    # — the unguarded .split() here used to crash on a non-string
    # job (the `(job["job"] or "")` guard only covers None/empty).
    if job_text(job).split()[:1] == ["harvest-egx"]:
        parts = job_text(job).split()
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
        # Issue #279: attachments captured by this harvest ride next
        # to the pointer so item["attachments"] paths resolve. A
        # harvest with no attachments dir copies nothing (0).
        n_att = _publish_harvest_attachments(results_dir, arch)
        print(f"publish: harvest attachments copied: {n_att}",
              flush=True)
    # Commit message via a file: job text never enters a shell string.
    msg_file = arch / ".commit-msg"
    msg_file.write_text(f"worker run {job['id']}: {job['job']}\n")
    # Issue #257: add and commit are enforced separately (sh() never
    # raises). A commit failure is a publish failure — except the
    # legitimate already-published retry: "nothing to commit" with a
    # clean tree means this exact run is already committed, and the
    # verification below must prove its bytes in the remote tree
    # rather than accepting an arbitrary unchanged HEAD.
    already_published = False
    if sh(f"git -C {arch} add -A", timeout=120).returncode != 0:
        print("publish: git add failed", flush=True)
        msg_file.unlink(missing_ok=True)
        return False
    if sh(f"git -C {arch} commit -F {msg_file}",
          timeout=120).returncode != 0:
        st = sh(f"git -C {arch} status --porcelain", timeout=60)
        if st.returncode != 0 or st.stdout.strip():
            print("publish: git commit failed (tree not clean)",
                  flush=True)
            msg_file.unlink(missing_ok=True)
            return False
        print("publish: nothing to commit — verifying the run is "
              "already published", flush=True)
        already_published = True
    msg_file.unlink(missing_ok=True)
    # Issue #149: success returns the archive commit SHA (the done
    # record's target); failure returns False. Callers use truthiness.
    if not push_archive(arch):
        return False
    # Issue #257: resolve the candidate SHA AFTER the push (a rebase
    # retry replays the commit under a new SHA), confirm it reached
    # the remote archive branch, and verify the expected run/sweep
    # files AND hashes in that commit's tree. An unresolved SHA, a
    # remote HEAD that is not the candidate, or any tree mismatch is
    # a publish failure — a commit failure + up-to-date push can
    # never again file a done record naming a commit without the run.
    rev = sh(f"git -C {arch} rev-parse HEAD",
             timeout=30).stdout.strip()
    if not rev:
        print("publish: could not resolve candidate SHA", flush=True)
        return False
    remote = sh(f"git -C {arch} ls-remote origin archive",
                timeout=60)
    if remote.returncode != 0:
        print("publish: ls-remote failed", flush=True)
        return False
    remote_sha = remote.stdout.split()[0] if remote.stdout.split() \
        else ""
    if remote_sha != rev:
        print(f"publish: remote archive HEAD {remote_sha[:12]} != "
              f"candidate {rev[:12]}", flush=True)
        return False
    expected = [(f"{dest.relative_to(arch)}/manifest.json",
                 dest / "manifest.json")]
    if isinstance(manifest, dict):
        render_block = manifest.get("render") or {}
        render_rel = render_block.get("sweep_dir") \
            if isinstance(render_block, dict) else None
        if isinstance(render_block, dict) \
                and render_block.get("status") == "rendered" \
                and isinstance(render_rel, str) and render_rel:
            for f in render_block.get("files") or []:
                if not isinstance(f, dict) or "path" not in f:
                    continue
                expected.append((
                    f"{render_rel}/{f['path']}",
                    Path(results_dir) / "_merge_out" / render_rel
                    / f["path"]))
            expected.append((
                f"{render_rel}/manifest.json",
                Path(results_dir) / "_merge_out" / render_rel
                / "manifest.json"))
    if not _archive_tree_has(arch, rev, expected):
        print("publish: remote tree verification failed", flush=True)
        return False
    if already_published:
        print(f"publish: already-published retry verified at "
              f"{rev[:12]}", flush=True)
    return rev


def run_harvest(job, workdir):
    """Issue #47: EGX disclosure harvest — a borsagator-side script
    (kept current by self_update's main checkout) driven in its own
    playwright venv, with a persistent Chromium profile on the box."""
    # Issue #381: job_text() — only reached after the harvest-egx
    # dispatch matched a string, but never trust a bare .split()
    # on untrusted queue input twice.
    parts = job_text(job).split()
    code = parts[1] if len(parts) > 1 else ""
    if not TICKER_RE.match(code.replace(".CA", "")):
        return {"egx-harvest": "bad-code"}
    py, _venv_ready = _ensure_egx_playwright_venv()
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


# --- Issue #328: worker entry point for the live top-30 enumeration ---
# The #283 stage-2 tooling (scripts/top30_enumerate.py) is merged and
# probe/fixture-validated only. The live run — filter-semantics
# validation + fixed-window enumeration + corpus capture — needs the
# worker and its TSPD-trusted browser profile (this VM cannot reach
# EGX). Before this issue there was no worker route to run it:
# parse_job returns [] for any other job string, so a queued
# `top30-enumerate ...` job ran an empty plan and published an empty
# run as done. The entry point below dispatches in _execute_body
# before parse_job (the harvest-egx pattern) and runs the enumerator
# CLI in the same playwright venv the harvest uses.
#
# Scope: the entry point only. Issue #346 F2 wired the
# enumerator's live fetcher through the TSPD-trusted browser
# session (--transport profile; scripts/top30_enumerate.py
# ProfileFetcher). What is still unverified live: the profile
# session has never completed a real enumeration against EGX —
# no profile-backed live run has been observed, and the §2
# filter-semantics validation protocol (docs/top30-enumeration.md
# §2) has not run. A live run whose requests meet challenge shells therefore
# records source_challenge named failures per listing and an honest
# enumeration_closed=False — the entry point never converts that
# into a success. The browser-fetcher upgrade + §2 validation are
# follow-up work, not claimed here. Corpus capture
# (capture_document) is likewise a later stage: the enumerator's
# live mode enumerates; the ledger it writes carries per-document
# corpus states (not_captured until capture runs) and this entry
# point archives exactly that ledger — it never presents
# collection-only output as a ready corpus or a complete/pass
# verdict.
TOP30_WINDOW_START = "2026-08-19"
TOP30_WINDOW_END = "2026-11-19"
TOP30_MODES = ("live", "probe", "fixtures")
TOP30_ENUMERATOR_TIMEOUT = 7200  # 31 listings x pagination; the
# claim-refresh thread in execute() keeps the claim alive past 6 h.
TOP30_TERMINAL_STATES = ("empty", "exhausted", "count_reconciled",
                         "duplicate_page")
TOP30_CORPUS_STATES = ("not_captured", "archived", "partial",
                       "failed")


def _ensure_egx_playwright_venv():
    """Shared playwright venv for the EGX harvest and the top-30
    enumeration: the venv python + installed Chromium. Returns
    (py, ready); ready is False when no interpreter exists after
    the ensure attempt. run_harvest keeps its historical unchecked
    behaviour (it ignores ready); run_top30_enumerate fails closed
    on not ready."""
    venv = VENVS / "egx-harvest"
    py = venv / "bin" / "python"
    if not py.exists():
        sh(f"python3 -m venv {venv}", timeout=300)
        sh(f"{venv}/bin/pip install -q playwright", timeout=1200)
    marker = venv / ".browser-installed"
    if not marker.exists():
        sh(f"{py} -m playwright install chromium", timeout=1800)
        marker.write_text(now())
    return py, py.exists()


def _egx_profile_dir():
    """The persistent Chromium profile the harvester uses
    (worker/egx_harvest.py PROFILE): the TSPD trust anchor. A live
    enumeration without it would only collect challenge shells."""
    return ROOT / "egx-profile"


def parse_top30_job(job):
    """Parse a `top30-enumerate` job string into a plan dict, or
    None when the string is not a top30 job / malformed. Grammar:
    `top30-enumerate [--mode live|probe|fixtures]
    [--fixtures DIR]`. Unknown tokens fail closed (None) — a job
    the worker does not understand must never run. `--mode
    fixtures` needs its fixture dir named, and `--fixtures` is
    only meaningful with it: a fixtures run archives SIMULATED
    pages, labelled mode=fixtures in the ledger, so it can never
    pass as a live run — it exists so the entry point itself can be
    verified end to end on the worker without EGX contact.
    NOTE: parse_job (the registry grammar) still returns [] for
    this string — the registry has no enumeration tool. Dispatch
    happens in _execute_body before parse_job, like harvest-egx."""
    # Issue #381: isinstance, not `or ""` — the old guard only
    # covered None/empty; a non-string truthy value crashed .split().
    parts = (job if isinstance(job, str) else "").split()
    if not parts or parts[0] != "top30-enumerate":
        return None
    plan = {"kind": "top30-enumerate", "mode": "live",
            "fixtures": None}
    i = 1
    while i < len(parts):
        tok = parts[i]
        if tok == "--mode" and i + 1 < len(parts) \
                and parts[i + 1] in TOP30_MODES:
            plan["mode"] = parts[i + 1]
            i += 2
        elif tok == "--fixtures" and i + 1 < len(parts):
            plan["fixtures"] = parts[i + 1]
            i += 2
        else:
            return None
    if plan["mode"] == "fixtures" and not plan["fixtures"]:
        return None  # fixtures mode needs its fixture dir named
    if plan["mode"] != "fixtures" and plan["fixtures"]:
        return None  # --fixtures only with --mode fixtures
    return plan


def parse_gdelt_fetch_job(job):
    """Parse a `gdelt-fetch` job string into a plan dict, or None
    when the string is not a gdelt-fetch job / malformed. Grammar:
    `gdelt-fetch --start YYYYMMDDHHMMSS --end YYYYMMDDHHMMSS
    [--budget-seconds N] [--workers N] [--mode live|fixtures]
    [--resume-from JOBID]`.
    --start and --end are REQUIRED, 14-digit GDELT datetimes, and
    start must be <= end, else the parser returns None (fail closed).
    --budget-seconds default 0 (unlimited, matching the filter script
    default), --workers default 6. --mode fixtures labels the run
    mode=fixtures in the manifest so it can never pass as a live run;
    live mode is the default. --resume-from names the predecessor job
    id whose latest published run supplies the restored filter state
    (without it a run resumes from its own job id); the id must match
    [A-Za-z0-9][A-Za-z0-9._-]{0,127}, else None (fail closed).
    Unknown tokens fail closed (None).
    NOTE: parse_job (the registry grammar) still returns [] for this
    string — the registry has no gdelt-fetch tool. Dispatch happens in
    _execute_body before parse_job, like harvest-egx / top30-enumerate.
    """
    # Issue #381: isinstance, not `or ""` — the old guard only
    # covered None/empty; a non-string truthy value crashed .split().
    parts = (job if isinstance(job, str) else "").split()
    if not parts or parts[0] != "gdelt-fetch":
        return None
    plan = {"kind": "gdelt-fetch", "start": None, "end": None,
            "budget_seconds": 0, "workers": 6, "mode": "live",
            "resume_from": None}
    i = 1
    while i < len(parts):
        tok = parts[i]
        if tok == "--start" and i + 1 < len(parts):
            val = parts[i + 1]
            if not re.fullmatch(r"[0-9]{14}", val):
                return None
            plan["start"] = val
            i += 2
        elif tok == "--end" and i + 1 < len(parts):
            val = parts[i + 1]
            if not re.fullmatch(r"[0-9]{14}", val):
                return None
            plan["end"] = val
            i += 2
        elif tok == "--budget-seconds" and i + 1 < len(parts):
            try:
                plan["budget_seconds"] = int(parts[i + 1])
            except ValueError:
                return None
            if plan["budget_seconds"] < 0:
                return None   # 959n F7: negative is refused (0 stays unlimited)
            i += 2
        elif tok == "--workers" and i + 1 < len(parts):
            try:
                plan["workers"] = int(parts[i + 1])
            except ValueError:
                return None
            i += 2
        elif tok == "--mode" and i + 1 < len(parts) \
                and parts[i + 1] in ("live", "fixtures"):
            plan["mode"] = parts[i + 1]
            i += 2
        elif tok == "--resume-from" and i + 1 < len(parts):
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}",
                                parts[i + 1]):
                return None
            plan["resume_from"] = parts[i + 1]
            i += 2
        else:
            return None
    if plan["start"] is None or plan["end"] is None:
        return None
    if plan["start"] > plan["end"]:
        return None
    if plan["workers"] < 1:
        return None
    return plan


def build_top30_required_cells(manifest):
    """Required universe (issue #283 gates re-check schema addition): one cell per manifest issuer x event type — FAIT/
    FAITA is ONE issuer, so its two listings form one cell per
    type, not two. The count is derived from the live manifest
    (35 issuers x 3 types = 105 cells after the 2026-11-26 T1/T2
    round). Returns (cells_doc, cells); cells_doc carries the
    versioned sha256 the later runner consumes as
    `required_cells`."""
    issuers = [i["issuer"] for i in manifest.get("issuers", [])]
    types = list(manifest.get("event_types", []))
    cells = [{"issuer": iss, "event_type": t,
              "cell_id": "%s:%s" % (iss, t)}
             for iss in issuers for t in types]
    canon = json.dumps(cells, sort_keys=True, ensure_ascii=False)
    doc = {"schema_version": 1, "issue": 283,
           "manifest_base_commit": manifest.get("base_commit"),
           "manifest_frozen_at": manifest.get("frozen_at"),
           "window": {"start": TOP30_WINDOW_START,
                      "end": TOP30_WINDOW_END, "inclusive": True},
           "event_types": types, "issuer_count": len(issuers),
           "count": len(cells), "cells": cells,
           "sha256": hashlib.sha256(canon.encode("utf-8")).hexdigest()}
    return doc, cells


def _is_sha256_hex(value):
    """True when value is a 64-char lowercase hex digest — the only
    shape hashlib.sha256(...).hexdigest() ever produces."""
    return isinstance(value, str) \
        and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _validate_top30_ledger(ledger, manifest, mode):
    """Fail-closed validation of an enumerator ledger against the
    frozen manifest and the #283 gates re-check flags (issue #328).
    Returns (ok, reasons). An honest failure ledger PASSES — named
    failures + enumeration_closed False is the correct outcome of
    a blocked run. A DISHONEST ledger fails: a closure claim over
    failed routes, a missing route, FAITA defaulted or omitted, a
    clipped body presented as a full hash, or any complete/pass
    verdict claimed from collection-only output. Issue #346 adds:
    the collection summary must reconcile against the records
    (F4), route provenance must match the frozen manifest (F5),
    the route set is frozen and duplicate route records are
    rejected (F6), and an archived body needs a real 64-hex hash
    (F8). Issue #352 adds: attribution is required on every
    validated document record (F5 — a record without listing /
    ISIN is unresolved provenance, never vouched for), and
    source_document_id must be unique within each issuer (F4 —
    a repeated id under one issuer inflates the reconciled
    totals). Issue #357 F2: a non-empty string
    source_document_id is required on every validated document
    record — a missing, empty, or non-string id is a named
    validation failure, never an exception and never silently
    skipped. Never raises on malformed input: every defect is a
    reason, not a crash."""
    reasons = []
    if not isinstance(ledger, dict):
        return False, ["ledger is not a JSON object"]
    if not isinstance(manifest, dict):
        return False, ["manifest is not a JSON object"]
    if ledger.get("schema_version") != 1:
        reasons.append("ledger schema_version is not 1: %r"
                       % (ledger.get("schema_version"),))
    window = ledger.get("window")
    if not isinstance(window, dict) \
            or window.get("start") != TOP30_WINDOW_START \
            or window.get("end") != TOP30_WINDOW_END:
        reasons.append("window is not the frozen %s -> %s"
                       % (TOP30_WINDOW_START, TOP30_WINDOW_END))
    if ledger.get("mode") != mode:
        reasons.append("ledger mode %r != requested mode %r"
                       % (ledger.get("mode"), mode))
    mref = ledger.get("manifest")
    # Issue #346 F7: mref may be a string/list (malformed input) —
    # never call .get on it unless it is a dict; the validator's
    # never-raises contract covers the reason line too.
    mref_commit = mref.get("base_commit") \
        if isinstance(mref, dict) else None
    if not isinstance(mref, dict) \
            or mref_commit != manifest.get("base_commit"):
        reasons.append("ledger manifest base_commit %r != frozen "
                       "manifest %r"
                       % (mref_commit, manifest.get("base_commit")))
    coll = ledger.get("collection")
    if not isinstance(coll, dict):
        reasons.append("collection missing")
        coll = {}
    else:
        for key in ("enumerated", "archived", "missing",
                    "enumeration_closed", "pagination_complete"):
            if coll.get(key) is None:
                reasons.append("collection %s not supplied" % key)
        for key in ("enumerated", "archived"):
            v = coll.get(key)
            if v is not None and (not isinstance(v, int)
                                  or isinstance(v, bool) or v < 0):
                reasons.append("collection %s must be a non-negative "
                               "int: %r" % (key, v))
        if not isinstance(coll.get("missing"), list) \
                or not all(isinstance(m, str)
                           for m in (coll.get("missing") or [])):
            reasons.append("collection missing must be a list of "
                           "strings")
        for key in ("enumeration_closed", "pagination_complete"):
            if coll.get(key) is not None \
                    and not isinstance(coll.get(key), bool):
                reasons.append("collection %s must be a boolean: %r"
                               % (key, coll.get(key)))
    # Per-listing coverage: every manifest route must be present.
    # Issue #346 F5/F6: the frozen route set is enforced both ways
    # — a listing record's ISIN must equal the manifest ISIN for
    # its code (never defaulted to another listing's ISIN), an unknown code
    # is rejected, a code recorded under the wrong issuer is
    # rejected, and a duplicate route record is rejected instead
    # of silently collapsing into `seen`.
    expected = {}       # code -> manifest ISIN
    route_issuer = {}   # code -> manifest issuer
    manifest_issuers = set()
    for iss in manifest.get("issuers", []) or []:
        if not isinstance(iss, dict):
            continue
        if iss.get("issuer"):
            manifest_issuers.add(iss["issuer"])
        for lst in iss.get("listings", []) or []:
            if isinstance(lst, dict) and lst.get("code"):
                expected[lst["code"]] = lst.get("isin")
                route_issuer[lst["code"]] = iss.get("issuer")
    seen = {}
    issuers = ledger.get("issuers")
    if not isinstance(issuers, list):
        reasons.append("issuers is not a list")
        issuers = []
    for irec in issuers:
        if not isinstance(irec, dict):
            continue
        if irec.get("issuer") not in manifest_issuers:
            reasons.append("issuer %r is not in the frozen manifest"
                           % (irec.get("issuer"),))
        for lrec in irec.get("listings", []) or []:
            if not isinstance(lrec, dict) or not lrec.get("code"):
                continue
            code = lrec["code"]
            if code in seen:
                reasons.append("duplicate listing route %s: recorded "
                               "more than once" % code)
                continue
            seen[code] = lrec
            if code not in expected:
                reasons.append("listing route %s is not in the "
                               "frozen manifest" % code)
                continue
            if lrec.get("isin") != expected[code]:
                reasons.append("listing route %s carries ISIN %r but "
                               "the frozen manifest records %r"
                               % (code, lrec.get("isin"),
                                  expected[code]))
            if route_issuer.get(code) != irec.get("issuer"):
                reasons.append("listing route %s is recorded under "
                               "issuer %r but belongs to %r in the "
                               "frozen manifest"
                               % (code, irec.get("issuer"),
                                  route_issuer.get(code)))
    for code in expected:
        if code not in seen:
            reasons.append("listing route %s missing from ledger"
                           % code)
    # Issue #346 F4: reconcile the summary against the records it
    # summarizes. `enumerated` is the count of issuer-level
    # documents (the enumerator dedupes FAIT/FAITA shared ids at
    # the issuer level, so listing-level documents are NOT summed
    # — they would double-count). `archived` is the count of
    # documents whose corpus status is archived.
    # Issue #352 (settled interface): `collection.missing` is a
    # list of frozen ROUTE codes for routes that could not be
    # enumerated — never document IDs, and never manufactured:
    # the producer emits missing=[] and evidences blocked/failed
    # routes in the listing/failure records (e.g. FAITA's B-02
    # named failure), so no later consumer may read missing as
    # an exhaustive ledger of unarchived documents. Every entry
    # must still be a frozen route code; an invented id is
    # neither an expected document nor a route.
    doc_total = 0
    archived_total = 0
    for irec in issuers:
        if not isinstance(irec, dict):
            continue
        docs = irec.get("documents")
        if not isinstance(docs, list):
            continue
        # Issue #352 F4: source_document_id must be unique WITHIN
        # each issuer. The producer dedupes within an issuer, so
        # a repeated id under one issuer inflates the reconciled
        # totals. Uniqueness is per issuer only — one announcement
        # may legitimately appear through different issuers'
        # searches, so cross-issuer sharing is NOT rejected.
        # Issue #357 F2: identity is REQUIRED on every validated
        # document record before it can be counted as a unique
        # document — a missing, empty, or non-string id is a
        # named validation failure, never an exception (the
        # never-raises contract) and never silently skipped:
        # #352 only tracked string ids, so unidentified records
        # bypassed the uniqueness check entirely while still
        # satisfying the reconciled counts. The producer always
        # emits ids (top30_enumerate.py emits them at discovery),
        # so honest ledgers are unaffected. An unidentified record
        # still counts toward the totals (same precedent as #352
        # F5 attribution: the failure is the named reason, not a
        # cascade of count mismatches) — it just never enters the
        # per-issuer identity set.
        seen_ids = set()
        for d in docs:
            if not isinstance(d, dict):
                continue
            doc_total += 1
            sid = d.get("source_document_id")
            if not isinstance(sid, str) or not sid:
                reasons.append("document under issuer %s has "
                               "source_document_id %r, not a "
                               "non-empty string (identity required "
                               "on every validated document record)"
                               % (irec.get("issuer"), sid))
            else:
                if sid in seen_ids:
                    reasons.append("duplicate source_document_id "
                                   "%r within issuer %s"
                                   % (sid, irec.get("issuer")))
                seen_ids.add(sid)
            corp = d.get("corpus")
            if isinstance(corp, dict) \
                    and corp.get("status") == "archived":
                archived_total += 1
    if isinstance(coll.get("enumerated"), int) \
            and not isinstance(coll.get("enumerated"), bool):
        if coll["enumerated"] != doc_total:
            reasons.append("collection enumerated=%d but the ledger "
                           "carries %d issuer-level document(s)"
                           % (coll["enumerated"], doc_total))
    if isinstance(coll.get("archived"), int) \
            and not isinstance(coll.get("archived"), bool):
        if coll["archived"] != archived_total:
            reasons.append("collection archived=%d but %d document(s) "
                           "have corpus status archived"
                           % (coll["archived"], archived_total))
    if isinstance(coll.get("enumerated"), int) \
            and not isinstance(coll.get("enumerated"), bool) \
            and isinstance(coll.get("archived"), int) \
            and not isinstance(coll.get("archived"), bool):
        if coll["archived"] > coll["enumerated"]:
            reasons.append("collection archived=%d exceeds "
                           "enumerated=%d"
                           % (coll["archived"], coll["enumerated"]))
    if isinstance(coll.get("missing"), list):
        for m in coll["missing"]:
            if isinstance(m, str) and m not in expected:
                reasons.append("collection missing entry %r is not a "
                               "frozen route (expected documents / "
                               "routes only)" % m)
    # FAITA: a named blocked route (B-02), never enumerated under
    # another listing's ISIN and never silently omitted. This rule
    # applies ONLY while the frozen manifest carries no FAITA ISIN
    # (B-02 open); once the ISIN is verified (T1, 2026-11-26:
    # EGS60322C012), FAITA enumerates like any other listing and
    # no B-02 named failure is required or expected.
    faita = seen.get("FAITA")
    if expected.get("FAITA") is None:
        if faita is None:
            reasons.append("FAITA route missing (B-02 named failure "
                           "required)")
        elif faita.get("enumeration_status") == "enumerated":
            reasons.append("FAITA enumerated despite missing ISIN "
                           "(B-02: never default to the FAIT ISIN)")
        elif not any(isinstance(f, dict)
                     and f.get("kind") == "B-02-missing-isin"
                     for f in faita.get("failures", []) or []):
            reasons.append("FAITA carries no B-02-missing-isin named "
                           "failure")
    # enumeration_closed honesty: closed only with zero failures,
    # every route at an evidenced terminal state, pagination done.
    failures = ledger.get("failures")
    if not isinstance(failures, list):
        reasons.append("failures is not a list")
        failures = []
    if coll.get("enumeration_closed"):
        if failures:
            reasons.append("enumeration_closed=True with %d named "
                           "failure(s)" % len(failures))
        for code, lrec in seen.items():
            if lrec.get("terminal_state") not in TOP30_TERMINAL_STATES:
                reasons.append("enumeration_closed=True but %s "
                               "terminal_state=%r is not evidenced"
                               % (code, lrec.get("terminal_state")))
            # Issue #340: the closure check above only looked at
            # the TOP-LEVEL failures list. A hand-built ledger can
            # clear that list and set every terminal_state while
            # a route still carries a named listing-level failure
            # (variant A: FAITA's B-02). Closure requires zero
            # failures at BOTH levels, and no blocked route.
            lfails = lrec.get("failures")
            if lfails:
                if isinstance(lfails, list):
                    reasons.append("enumeration_closed=True but %s "
                                   "carries %d named listing-level "
                                   "failure(s)"
                                   % (code, len(lfails)))
                else:
                    reasons.append("enumeration_closed=True but %s "
                                   "listing failures is not a list: "
                                   "%r" % (code, lfails))
            if lrec.get("enumeration_status") == "blocked":
                reasons.append("enumeration_closed=True but %s "
                               "enumeration_status is blocked"
                               % code)
        if not coll.get("pagination_complete"):
            reasons.append("enumeration_closed=True but "
                           "pagination_complete is not True")
    # Corpus honesty per document: a clipped body is never a full
    # hash; archived requires a full hash; partial requires the
    # clipped label. Collection-only output claims no verdict.
    for irec in issuers:
        if not isinstance(irec, dict):
            continue
        for doc in irec.get("documents", []) or []:
            if not isinstance(doc, dict):
                continue
            # Issue #352 F5: attribution is REQUIRED on every
            # validated document record. The #346 fix checked a
            # document's listing/ISIN only when the record carried
            # them, so stripping listing and/or isin bypassed every
            # provenance check while the document still counted
            # toward the validated totals. The producer always
            # attributes documents (top30_enumerate.py emits
            # listing + isin at discovery, including not_captured
            # records), so a record without attribution is not an
            # honest incomplete ledger — it is unresolved
            # provenance, and it fails here rather than being
            # vouched for. A document's listing must be a route of
            # its own issuer and never a blocked route; its ISIN
            # must be present and match the manifest ISIN for that
            # listing.
            dlisting = doc.get("listing")
            if dlisting is None:
                reasons.append("document %s has no listing "
                               "attribution (validated records must "
                               "name a frozen route)"
                               % (doc.get("source_document_id"),))
            elif dlisting not in expected:
                reasons.append("document %s claims listing %r, "
                               "not a frozen route"
                               % (doc.get("source_document_id"),
                                  dlisting))
            elif route_issuer.get(dlisting) \
                    != irec.get("issuer"):
                reasons.append("document %s claims listing %s, "
                               "not a route of issuer %s"
                               % (doc.get("source_document_id"),
                                  dlisting, irec.get("issuer")))
            elif expected[dlisting] is None:
                reasons.append("document %s claims blocked route "
                               "%s (no verified ISIN)"
                               % (doc.get("source_document_id"),
                                  dlisting))
            elif doc.get("isin") is None:
                reasons.append("document %s claims listing %s but "
                               "carries no ISIN (provenance "
                               "required)"
                               % (doc.get("source_document_id"),
                                  dlisting))
            elif doc.get("isin") != expected[dlisting]:
                reasons.append("document %s carries ISIN %r for "
                               "listing %s but the frozen "
                               "manifest records %r"
                               % (doc.get("source_document_id"),
                                  doc.get("isin"), dlisting,
                                  expected[dlisting]))
            corp = doc.get("corpus")
            if not isinstance(corp, dict):
                reasons.append("document %s has no corpus record"
                               % (doc.get("source_document_id"),))
                continue
            st, kind = corp.get("status"), corp.get("body_hash_kind")
            if st not in TOP30_CORPUS_STATES:
                reasons.append("document %s corpus status %r is not "
                               "a known state"
                               % (doc.get("source_document_id"), st))
            if st == "archived" and kind != "full":
                reasons.append("document %s archived with "
                               "body_hash_kind=%r (a clipped body "
                               "is never a full-document hash)"
                               % (doc.get("source_document_id"), kind))
            if st == "archived" and not corp.get("body_sha256"):
                reasons.append("document %s archived with no "
                               "body_sha256"
                               % (doc.get("source_document_id"),))
            if st == "partial" and kind != "clipped-body-sha256":
                reasons.append("document %s partial with "
                               "body_hash_kind=%r (must be "
                               "clipped-body-sha256)"
                               % (doc.get("source_document_id"), kind))
            # Issue #346 F8: an archived body needs a real 64-hex
            # sha256 — a 2-char or non-hex string is not a hash.
            # Any body_sha256 present on any corpus record must be
            # 64-hex too. Attachment accounting is a named later
            # step, not validated here: link_found entries carry
            # no hash until the corpus runner fetches the PDF
            # (docs/top30-enumeration.md §9), so only the record
            # shape is checked.
            sha = corp.get("body_sha256")
            if sha and not _is_sha256_hex(sha):
                reasons.append("document %s has body_sha256=%r (must "
                               "be 64 hex chars when present)"
                               % (doc.get("source_document_id"), sha))
            atts = corp.get("attachments")
            if atts is not None and (not isinstance(atts, list)
                    or not all(isinstance(a, dict) for a in atts)):
                reasons.append("document %s attachments is not a list "
                               "of records"
                               % (doc.get("source_document_id"),))
    for key in ("complete", "verdict", "passed",
                "evaluation_complete"):
        if key in ledger:
            reasons.append("ledger claims %r from collection-only "
                           "output (gold/scorer verdicts are later "
                           "stages)" % key)
    return (not reasons), reasons


def run_top30_enumerate(job, workdir):
    """Issue #328: run scripts/top30_enumerate.py for one
    `top30-enumerate` job, in the egx-harvest playwright venv, and
    validate the ledger fail-closed before it can be archived.
    The ledger + frozen required-cells file + validation record
    land under workdir/top30/ and ride the archive publish.
    Returns {"top30-enumerate": status}:
      ok — the enumerator ran and the ledger passed validation.
        enumeration_closed may still be False: an honest failure
        ledger (challenge shells, blocked FAITA, unreachable EGX)
        is a successful entry-point run, not a job failure.
      bad-job — the job string is not a top30-enumerate job.
      manifest-missing / venv-failed / profile-missing /
      ledger-missing / ledger-unparseable / exit-N /
      validation-failed — named failures; the evidence written so
        far still archives, so the failure is inspectable.
    Live mode requires the persistent Chromium profile: the run's
    premise is the TSPD-trusted profile, and without it the run
    would only collect challenge shells. The live fetch itself
    runs through that profile session (--transport profile); the
    profile is the transport, not just a prerequisite check
    (issue #346 F2). Probe/fixtures modes never touch EGX and
    need no profile."""
    # Issue #381: job_text() — only reached after the dispatch
    # matched a string, but parse_top30_job must never see a raw
    # untrusted value.
    plan = parse_top30_job(job_text(job))
    run_dir = Path(workdir) / "top30"
    run_dir.mkdir(parents=True, exist_ok=True)
    if plan is None:
        return {"top30-enumerate": "bad-job"}
    manifest_path = CODE / "evaluation" / "top30_manifest.json"
    try:
        manifest = json.loads(
            manifest_path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001 — named failure, not a crash
        (run_dir / "top30-enumerate.log").write_text(
            "manifest load failed: %s: %s\n"
            % (type(e).__name__, e))
        return {"top30-enumerate": "manifest-missing"}
    cells_doc, _cells = build_top30_required_cells(manifest)
    (run_dir / "top30_required_cells.json").write_text(
        json.dumps(cells_doc, indent=1, ensure_ascii=False),
        encoding="utf-8")
    py, venv_ready = _ensure_egx_playwright_venv()
    if not venv_ready:
        (run_dir / "top30-enumerate.log").write_text(
            "playwright venv not ready: no interpreter at %s\n" % py)
        return {"top30-enumerate": "venv-failed"}
    if plan["mode"] == "live" and not _egx_profile_dir().is_dir():
        (run_dir / "top30-enumerate.log").write_text(
            "live mode requires the persistent Chromium profile at "
            "%s (created by a harvest run); refusing to enumerate "
            "without it\n" % _egx_profile_dir())
        return {"top30-enumerate": "profile-missing"}
    script = CODE / "scripts" / "top30_enumerate.py"
    out_path = run_dir / "top30_expected_docs.json"
    cmd = [str(py), str(script), "--mode", plan["mode"],
           "--manifest", str(manifest_path),
           "--out", str(out_path)]
    if plan["fixtures"]:
        cmd += ["--fixtures", plan["fixtures"]]
    if plan["mode"] == "live":
        # Issue #346 F2: live enumeration fetches through the
        # persistent Chromium profile session, not plain HTTP.
        # Probe/fixtures modes keep their existing transports.
        cmd += ["--transport", "profile", "--profile",
                str(_egx_profile_dir())]
    env = {k: v for k, v in os.environ.items()
           if k not in ENV_DENY_FOR_TOOLS}
    # shlex.quote each part: the fixtures dir comes from the job
    # string and must never reach a shell unquoted (INS-R3-01).
    r = sh(" ".join(shlex.quote(c) for c in cmd), cwd=run_dir,
           env=env, timeout=TOP30_ENUMERATOR_TIMEOUT)
    (run_dir / "top30-enumerate.log").write_text(
        (r.stdout + r.stderr)[-4000:])
    if r.returncode != 0:
        return {"top30-enumerate": "exit-%d" % r.returncode}
    if not out_path.exists():
        return {"top30-enumerate": "ledger-missing"}
    try:
        ledger = json.loads(out_path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001 — named failure, not a crash
        (run_dir / "top30-enumerate.log").write_text(
            "ledger unparseable: %s: %s\n" % (type(e).__name__, e))
        return {"top30-enumerate": "ledger-unparseable"}
    ok, reasons = _validate_top30_ledger(ledger, manifest,
                                         plan["mode"])
    coll = ledger.get("collection") \
        if isinstance(ledger.get("collection"), dict) else {}
    validation = {
        "job": job["job"], "mode": plan["mode"],
        "transport": {"live": "profile", "probe": "http",
                      "fixtures": "fixtures"}[plan["mode"]],
        "enumerator": "scripts/top30_enumerate.py",
        "ledger": "top30/top30_expected_docs.json",
        "required_cells": "top30/top30_required_cells.json",
        "required_cells_sha256": cells_doc["sha256"],
        "required_cells_count": cells_doc["count"],
        "enumeration_closed": coll.get("enumeration_closed"),
        "pagination_complete": coll.get("pagination_complete"),
        "enumerated": coll.get("enumerated"),
        "failures": len(ledger.get("failures") or [])
        if isinstance(ledger.get("failures"), list) else None,
        "valid": ok, "reasons": reasons,
        "validated_at": now(),
    }
    (run_dir / "top30-validation.json").write_text(
        json.dumps(validation, indent=1, ensure_ascii=False),
        encoding="utf-8")
    if not ok:
        return {"top30-enumerate": "validation-failed"}
    return {"top30-enumerate": "ok"}


GDELT_RESTORE_REF = "origin/archive"


def _git_out(arch, *args):
    r = subprocess.run(["git", "-C", str(arch), *args],
                       capture_output=True, timeout=300)
    if r.returncode != 0:
        raise RuntimeError("git %s failed" % args[0])
    return r.stdout


def _git_out_to_file(arch, dest, *args):
    """959n F9: run git and stream its stdout to a file (no in-memory copy
    of a checkpoint-sized tar)."""
    with open(dest, "wb") as out:
        r = subprocess.run(["git", "-C", str(arch), *args], stdout=out,
                           stderr=subprocess.PIPE, timeout=300)
    if r.returncode != 0:
        raise RuntimeError("git %s failed" % args[0])


class GdeltRestoreRollbackFailed(Exception):
    """A restore failed AND the previous snapshot could not be put back;
    the staging directory (with the backups) is preserved."""


def _truncate_tail_bytes(path):
    """Drop a trailing partial line (no final LF) from a staged copy, the
    same byte-based recovery the filter applies (0x0A never occurs inside a
    UTF-8 multi-byte sequence). The dropped record belongs to a file not yet
    marked done (matches are written before the done marker), so it is
    replayed. Returns the bytes removed."""
    size = os.path.getsize(path)
    if size == 0:
        return 0
    with open(path, "r+b") as f:
        f.seek(size - 1)
        if f.read(1) == b"\n":
            return 0
        pos, cut = size, 0
        while pos > 0:
            step = min(65536, pos)
            pos -= step
            f.seek(pos)
            i = f.read(step).rfind(b"\n")
            if i >= 0:
                cut = pos + i + 1
                break
        f.truncate(cut)
        f.flush()
        os.fsync(f.fileno())
    return size - cut


def _makedirs_durable(path):
    """makedirs that fsyncs every directory it CREATED and each one's
    parent (the parent holds the new entry). Errors propagate."""
    path = Path(os.path.abspath(str(path)))
    created = []
    p = path
    while not p.is_dir():
        created.append(p)
        if p.parent == p:
            break
        p = p.parent
    path.mkdir(parents=True, exist_ok=True)
    for d in created:
        _fsync_dir(d)
        _fsync_dir(d.parent)


class GdeltRestoreMismatch(Exception):
    """The predecessor run recorded a different mode than this job."""


GDELT_BINDING = "restored-from.json"


def _gdelt_pick_published(arch, src_id, mode, strict=False, window=None):
    """The latest PUBLISHED run for src_id on the fetched origin/archive tree
    (worker-runs/DATE/RUN__<job-id>, with a gdelt-state dir), as
    (run_path, names), or None when there is none. The run's recorded mode
    (gdelt/gdelt_fetch.json) must equal `mode`: a different recorded mode
    raises GdeltRestoreMismatch, so a live job never restores fixture
    state (or the reverse). A run with no recorded mode is accepted for
    the job's own id (same plan) and rejected when strict (a
    --resume-from predecessor)."""
    def ls(path):
        raw = _git_out(arch, "ls-tree", "--name-only", GDELT_RESTORE_REF,
                       path.rstrip("/") + "/")
        return [x for x in raw.decode("utf-8", "replace").splitlines() if x]

    runs = []
    for date_path in ls("worker-runs"):
        for run_path in ls(date_path):
            name = run_path.rsplit("/", 1)[-1]
            if name.rsplit("__", 1)[-1] == src_id:
                runs.append(run_path)
    runs.sort(key=lambda p: (p.split("/")[-2], p.split("/")[-1]))
    for run_path in reversed(runs):
        files = _git_out(arch, "ls-tree", "-r", "--name-only",
                         GDELT_RESTORE_REF, run_path + "/gdelt-state",
                         *[run_path + "/gdelt/" + n for n in
                           ("matches.jsonl", "macro_matches.jsonl")])
        names = [x for x in files.decode("utf-8", "replace").splitlines() if x]
        if not any(n.startswith(run_path + "/gdelt-state/") for n in names):
            continue
        recorded = None
        rec_window = None
        try:
            raw = _git_out(arch, "show", "%s:%s/gdelt/gdelt_fetch.json"
                           % (GDELT_RESTORE_REF, run_path))
            rec = json.loads(raw.decode("utf-8", "replace"))
            if isinstance(rec, dict) and isinstance(rec.get("mode"), str):
                recorded = rec["mode"]
            if isinstance(rec, dict) and "start" in rec and "end" in rec:
                rec_window = (str(rec["start"]), str(rec["end"]))
        except Exception:
            recorded = None
        # 959m F9: a predecessor that recorded a different window must not
        # be restored (its matches would be published under the current
        # plan's bounds if the filter never starts to refuse it).
        if window is not None and rec_window is not None \
                and rec_window != (str(window[0]), str(window[1])):
            raise GdeltRestoreMismatch(
                "predecessor %s recorded window %s..%s, job window %s..%s"
                % (run_path, rec_window[0], rec_window[1], window[0], window[1]))
        if (recorded is not None and recorded != mode) or \
                (recorded is None and strict):
            raise GdeltRestoreMismatch(
                "predecessor %s recorded mode %r, job mode %r"
                % (run_path, recorded, mode))
        return run_path, names
    return None


def _gdelt_binding(state_dir):
    """The published run the local checkpoint was restored from, or None."""
    try:
        d = json.loads((Path(state_dir) / GDELT_BINDING).read_text())
        return d.get("run") if isinstance(d, dict) else None
    except Exception:
        return None


def _fsync_tree(root):
    """fsync every regular file under root, then every directory under it
    (children first) and root itself."""
    root = str(root)
    for dp, dns, fns in os.walk(root, topdown=False):
        for fn in fns:
            fp = os.path.join(dp, fn)
            if os.path.islink(fp):
                continue
            fd = os.open(fp, os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        _fsync_dir(dp)


def _gdelt_restore_remote(arch, src_id, state_dir, out_dir, mode=None,
                          strict=False, picked=None, window=None):
    """Restore the latest published run for src_id (its gdelt-state/ plus
    gdelt/matches.jsonl and gdelt/macro_matches.jsonl) into state_dir /
    out_dir as ONE snapshot. State records files as done, so the matches
    for those files must come back with it or the published output would
    omit them. The restore is STAGED: everything is extracted into a
    scratch directory, validated (every listed file extracted, every
    state config and every matches line parses), and only then swapped
    in by directory rename. Any failure discards the scratch directory
    and leaves the previous state_dir / out_dir untouched. The restored
    config.json / macro_config.json bind the state to the predecessor's
    absolute --out path; only that "out" field is re-pointed at this
    run's out_dir (aliases/themes hash and the start/end window stay as
    restored, a different window still refuses). A restored-from.json
    in the state records which published run this checkpoint represents.
    Returns the run path, or None when nothing was published."""
    import tarfile
    import tempfile
    if picked is None:
        picked = _gdelt_pick_published(arch, src_id, mode, strict)
    if picked is None:
        return None
    run_path, names = picked
    state_dir, out_dir = Path(state_dir), Path(out_dir)
    out_abs = os.path.abspath(str(out_dir))
    stage = Path(tempfile.mkdtemp(prefix=".gdelt-restore-",
                                  dir=str(state_dir.parent)))
    keep_stage = False
    try:
        st_stage, out_stage = stage / "state", stage / "out"
        st_stage.mkdir()
        out_stage.mkdir()
        tar_path = stage / "archive.tar"
        _git_out_to_file(arch, tar_path, "archive", "--format=tar",
                         GDELT_RESTORE_REF, *names)
        want, got = set(), set()
        with tarfile.open(tar_path) as tf:
            for m in tf.getmembers():
                if not m.isfile() or m.name not in names:
                    continue
                rel = m.name[len(run_path) + 1:]
                if ".." in Path(rel).parts:
                    continue
                if rel.startswith("gdelt-state/"):
                    dst = st_stage / rel[len("gdelt-state/"):]
                else:
                    dst = out_stage / rel[len("gdelt/"):]
                dst.parent.mkdir(parents=True, exist_ok=True)
                # 959n F9: stream the member to disk (no second in-memory copy).
                with tf.extractfile(m) as src_f, open(dst, "wb") as dst_f:
                    shutil.copyfileobj(src_f, dst_f, 1 << 20)
                got.add(m.name)
        tar_path.unlink()   # scratch, never part of the installed snapshot
        want = {n for n in names if ".." not in Path(n).parts}
        if got != want:
            raise RuntimeError("restore incomplete: %d of %d files"
                               % (len(got), len(want)))
        cfg_bounds = []
        for cfg_name in ("config.json", "macro_config.json"):
            cp = st_stage / cfg_name
            if cp.exists():
                c = json.loads(cp.read_text())
                if not isinstance(c, dict):
                    raise RuntimeError("restored %s is not an object" % cfg_name)
                if window is not None and "start" in c and "end" in c:
                    # 959n F8: a checkpoint for another window must never be
                    # installed (the handler could publish it under THIS
                    # plan's bounds when the filter never runs to refuse it).
                    cfg_bounds.append((str(c["start"]), str(c["end"])))
                if "out" in c:
                    c["out"] = out_abs
                    cp.write_text(json.dumps(c, indent=1))
        if window is not None:
            want_w = (str(window[0]), str(window[1]))
            if any(b != want_w for b in cfg_bounds):
                raise GdeltRestoreMismatch(
                    "restored config window %s differs from job window %s..%s"
                    % (sorted(set(cfg_bounds)), want_w[0], want_w[1]))
            if not cfg_bounds:
                # Bound-less legacy checkpoint: only acceptable when the
                # published sidecar establishes the window.
                try:
                    sc = json.loads(_git_out(
                        arch, "show", "%s:%s/gdelt/gdelt_fetch.json"
                        % (GDELT_RESTORE_REF, run_path)).decode("utf-8", "replace"))
                    sw = (str(sc["start"]), str(sc["end"]))
                except Exception:
                    sw = None
                if sw != want_w:
                    raise GdeltRestoreMismatch(
                        "restored checkpoint %s does not establish window %s..%s"
                        % (run_path, want_w[0], want_w[1]))
        for fn in ("matches.jsonl", "macro_matches.jsonl"):
            mp = out_stage / fn
            if mp.exists():
                # An interrupted tail is repaired on the staged copy first;
                # a complete malformed record still rejects the snapshot.
                # Records are LF-delimited bytes (str.splitlines() would
                # also split on U+2028 inside a valid record).
                _truncate_tail_bytes(mp)
                # 959n F9: validate record by record (binary file iteration
                # splits on LF only, like the old split(b"\n")), never the
                # whole file as a list.
                with open(mp, "rb") as mf:
                    for rec in mf:
                        if rec.strip():
                            json.loads(rec.decode("utf-8"))
        (st_stage / GDELT_BINDING).write_text(
            json.dumps({"run": run_path, "mode": mode}))
        # Durability BEFORE the swap: fsync every restored match file, the
        # config/binding files, and each staged directory. Otherwise a host
        # crash can persist the binding and done.txt while the match bytes
        # are lost; the next run would skip the restore and the filter would
        # skip every file in done, silently omitting those matches.
        _fsync_tree(stage)
        # Commit: swap both directories; undo the first if the second fails.
        # The old state moves aside FIRST (a missing state forces a fresh
        # restore), the new OUTPUT is installed BEFORE the new state, so the
        # binding/done markers never exist without their matches.
        prev_st = stage / "prev-state"
        prev_out = stage / "prev-out"
        moved_st = moved_out = installed_out = installed_st = False
        try:
            if state_dir.exists():
                os.rename(state_dir, prev_st)
                moved_st = True
            if out_dir.exists():
                os.rename(out_dir, prev_out)
                moved_out = True
            os.rename(out_stage, out_dir)
            installed_out = True
            # 959m F6: persist the output install BEFORE the state install, so
            # a power loss cannot keep done.txt + binding without the matches.
            _fsync_dir(str(out_dir.parent))
            os.rename(st_stage, state_dir)
            installed_st = True
            # Every parent directory that gained or lost an entry.
            for d in {str(state_dir.parent), str(out_dir.parent), str(stage)}:
                _fsync_dir(d)
        except Exception:
            try:
                # Undo in reverse install order. The NEW state moves aside
                # first: a non-empty state_dir would make the rename of the
                # previous state over it fail. Output is installed before
                # state, so it is moved aside after the state.
                if installed_st and state_dir.exists():
                    os.rename(state_dir, st_stage)
                if installed_out and out_dir.exists():
                    os.rename(out_dir, out_stage)
                if moved_out:
                    os.rename(prev_out, out_dir)
                if moved_st:
                    os.rename(prev_st, state_dir)
                for d in {str(state_dir.parent), str(out_dir.parent), str(stage)}:
                    _fsync_dir(d)   # the rollback itself must be durable
            except Exception as e2:
                keep_stage = True   # the backups stay on disk
                # Rollback unconfirmed: whatever sits in state_dir may be the
                # new snapshot paired with the wrong output. Invalidate local
                # reuse (binding and done markers) so the next attempt
                # restores from the archive instead of skipping the restore.
                for fn in (GDELT_BINDING, "done.txt", "macro_done.txt"):
                    try:
                        (state_dir / fn).unlink(missing_ok=True)
                    except OSError:
                        pass
                raise GdeltRestoreRollbackFailed(str(stage)) from e2
            raise
        return str(run_path)
    finally:
        if not keep_stage:
            shutil.rmtree(stage, ignore_errors=True)


def _gkg_unfinished(out_text):
    """Count from the filter's last `gkg-filter-status unfinished=N
    absent=M` line; 0 when the line is absent (older filter)."""
    hits = re.findall(r"^gkg-filter-status unfinished=(\d+) absent=\d+\s*$",
                      out_text or "", re.M)
    return int(hits[-1]) if hits else 0


def run_gdelt_fetch(job, workdir):
    """Run a `gdelt-fetch` job: download the two real GDELT master
    lists and invoke scripts/gdelt_gkg_filter.py with the configured
    date range. Returns {"gdelt-fetch": status}. The master lists
    (about 270 MB, over GitHub's 100 MiB file limit) live in a
    temporary directory OUTSIDE workdir, so publish()'s copy of
    workdir can never carry them; the directory is removed on every
    return path.
    """
    import tempfile
    try:
        master_dir = Path(tempfile.mkdtemp(prefix="gdelt-master-"))
    except OSError:
        # 959n F10: nothing was touched yet; a retryable no-publish outcome
        # through execute()'s retry path instead of an escaping OSError.
        return {"gdelt-fetch": "setup-io-failed"}
    try:
        return _run_gdelt_fetch(job, workdir, master_dir)
    finally:
        shutil.rmtree(master_dir, ignore_errors=True)


# Incomplete = archived for resume but NOT queue-done. master-download-failed
# is transient (network) and is incomplete on purpose: marking it done would
# lose the job. "unfinished" = the filter left files neither done nor absent.
# Unknown resume state: nothing is published and the claim is released.
GDELT_NO_PUBLISH = ("archive-check-failed", "restore-rollback-failed",
                    "checkpoint-io-failed", "setup-io-failed")
GDELT_INCOMPLETE = ("budget-exhausted", "timeout", "unfinished",
                    "master-download-failed", "checkpoint-io-incomplete")
GDELT_CHECKPOINT_IO_RC = 75   # scripts/gdelt_gkg_filter.CHECKPOINT_IO_EXIT


GDELT_ALLOWED_HOST = "data.gdeltproject.org"   # scripts/gdelt_gkg_filter.ALLOWED_HOST


def _validate_master_file(path, label=""):
    """Validate a downloaded master list line by line (no full read into
    memory): non-empty, UTF-8, every non-blank line `size md5 url`."""
    n = gkg = 0
    with open(path, "rb") as f:
        for raw in f:
            line = raw.decode("utf-8")
            if not line.strip():
                continue
            fld = line.split()
            if len(fld) != 3 or not fld[0].isdigit() or "/" not in fld[2]:
                raise ValueError("invalid master listing line in %s" % label)
            n += 1
            # A recognisable GKG archive entry (any date, so a valid master
            # whose entries all fall outside the window still passes):
            # <14-digit timestamp>.<...>.gkg.csv.zip, as list_files selects.
            base = fld[2].rsplit("/", 1)[-1]
            ts = base.split(".")[0]
            if base.endswith(".gkg.csv.zip") and ts.isdigit() and len(ts) == 14:
                # 959m F7: only an entry fetch() will accept counts (scheme
                # http/https and the GDELT host); a bare path does not.
                u = urlsplit(fld[2])
                if u.scheme in ("http", "https") and u.netloc == GDELT_ALLOWED_HOST:
                    gkg += 1
    if n == 0:
        raise ValueError("empty master listing: %s" % label)
    if gkg == 0:
        raise ValueError("master listing has no GKG archive entries: %s" % label)
    return n


def _run_gdelt_fetch(job, workdir, master_dir):
    # Issue #381: job_text() — never feed raw untrusted job text.
    plan = parse_gdelt_fetch_job(job_text(job))
    run_dir = Path(workdir) / "gdelt"
    try:
        run_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return {"gdelt-fetch": "setup-io-failed"}
    if plan is None:
        return {"gdelt-fetch": "bad-job"}

    start = plan["start"]
    end = plan["end"]
    mode = plan["mode"]
    workers = plan["workers"]
    budget = plan["budget_seconds"]

    # State/out dirs are fixed so re-queued jobs resume.
    state_dir = Path(workdir) / "gdelt-state"
    out_dir = Path(workdir) / "gdelt-out"
    try:
        _makedirs_durable(state_dir)
        _makedirs_durable(out_dir)
        # 959m F8: the workdir entry itself lives in its parent (OUT).
        _fsync_dir(str(Path(workdir).parent))
    except OSError:
        # Setup failed before any checkpoint was touched: a no-publish,
        # retryable outcome through execute()'s retry path.
        return {"gdelt-fetch": "setup-io-failed"}

    # (c) Restore the previous run's state AND match output from the
    # REMOTE archive branch only. The local archive-push checkout can
    # carry residue from a failed publish() (commit or push failed, run
    # dir left behind), so it is never enumerated: candidates come from
    # the fetched origin/archive tree, and a successor on another
    # checkout sees exactly what a published run left.
    # A local done.txt no longer skips the remote check: another worker may
    # have advanced the same job. The local checkpoint is bound
    # (restored-from.json) to the published run it represents; the fast
    # path is kept only when that is still the latest compatible run.
    mismatch = None
    missing_pred = False
    rollback_failed = False
    lookup_failed = False
    arch = ROOT / "archive-push"
    url = os.environ.get("GATOR_BUS_URL")
    archive_configured = arch.exists() or bool(url)
    fetched = False
    for _attempt in range(2):   # one retry of the archive lookup
        try:
            if not arch.exists() and url:
                sh(f"git clone --branch archive --single-branch {url} {arch}",
                   timeout=900)
            if arch.exists():
                fr = sh(f"git -C {shlex.quote(str(arch))} fetch origin "
                        "+refs/heads/archive:refs/remotes/origin/archive",
                        timeout=180)
                fetched = (fr.returncode == 0)
        except Exception:
            fetched = False
        if fetched:
            break
    if archive_configured and not fetched:
        # Unknown resume state: never continue (and publish a possibly
        # stale checkpoint over a newer one). Fresh starts stay valid only
        # when a SUCCESSFUL lookup finds no checkpoint, or no archive is
        # configured at all.
        lookup_failed = True
    if fetched:
        try:
            # The job's OWN published run wins (a same-id retry resumes
            # itself); the --resume-from predecessor is only the fallback
            # when the job has no published run yet, and its recorded
            # mode must be present and equal to this job's.
            try:
                src, picked = job["id"], _gdelt_pick_published(
                    arch, job["id"], mode, window=(start, end))
                if picked is None and plan["resume_from"]:
                    src = plan["resume_from"]
                    picked = _gdelt_pick_published(arch, src, mode,
                                                   strict=True,
                                                   window=(start, end))
                    if picked is None:
                        missing_pred = True
            except GdeltRestoreMismatch as e:
                mismatch = str(e)
                picked = None
            if picked is not None:
                local = (state_dir / "done.txt").exists()
                if not (local and _gdelt_binding(state_dir) == picked[0]):
                    _gdelt_restore_remote(arch, src, state_dir, out_dir,
                                          mode=mode, picked=picked,
                                          window=(start, end))
        except GdeltRestoreRollbackFailed:
            rollback_failed = True
        except GdeltRestoreMismatch as e:
            # 959n F8: refused BEFORE install; nothing published.
            mismatch = str(e)
        except Exception:
            # ANY other failure in this block (the pick, an explicit
            # --resume-from lookup after the own-ID lookup bound picked, or
            # the staged restore) is an unknown resume state: continuing
            # with unchanged local state could publish it as the newest
            # checkpoint.
            lookup_failed = True
    if rollback_failed or lookup_failed:
        status = ("restore-rollback-failed" if rollback_failed
                  else "archive-check-failed")
        (run_dir / "gdelt-fetch.log").write_text(
            "%s: not continuing, nothing published\n" % status)
        return {"gdelt-fetch": status}
    if mismatch or missing_pred:
        status = ("resume-mode-mismatch" if mismatch
                  else "resume-predecessor-missing")
        (run_dir / "gdelt-fetch.log").write_text(
            "%s: %s\n" % (status, mismatch or plan["resume_from"]))
        return {"gdelt-fetch": status}

    # (a) Download master lists (live mode only)
    master_path = None
    trans_path = None
    if mode == "live":
        master_path = master_dir / "masterfilelist.txt"
        trans_path = master_dir / "masterfilelist-translation.txt"
        try:
            for url, dest in [
                ("https://data.gdeltproject.org/gdeltv2/masterfilelist.txt",
                 master_path),
                ("https://data.gdeltproject.org/gdeltv2/masterfilelist-translation.txt",
                 trans_path),
            ]:
                req = Request(url, headers={"User-Agent": "gdelt-fetch/1.0"})
                try:
                    with urlopen(req, timeout=300) as r, open(dest, "wb") as out:
                        shutil.copyfileobj(r, out, 1 << 20)
                    _validate_master_file(dest, url)
                except BaseException:
                    dest.unlink(missing_ok=True)   # never leave a bad listing
                    raise
        except Exception:
            # named failure status. Restored matches belong to the
            # restored done state, so they are copied into the run dir
            # on this path too, or the published run would count files
            # done without their matches.
            # 959n F11: the copy, counter reads and sidecar writes are
            # checkpoint I/O; an OSError here is a no-publish retryable
            # outcome, not an escape from the handler.
            try:
                for fn in ("matches.jsonl", "macro_matches.jsonl"):
                    if (out_dir / fn).exists():
                        shutil.copy2(out_dir / fn, run_dir / fn)
                    else:
                        (run_dir / fn).unlink(missing_ok=True)   # no stale copy
                (run_dir / "gdelt-fetch.log").write_text(
                    "master-download-failed\n")
                # Report the RESTORED progress, not 0: the progress record
                # (_gdelt_note_incomplete) must not see this failure as a
                # drop to zero files done.
                def _nonblank(p):
                    p = Path(p)
                    if not p.exists():
                        return 0
                    return len([l for l in p.read_text(errors="replace").splitlines()
                                if l.strip()])

                def _distinct(p):
                    p = Path(p)
                    if not p.exists():
                        return 0
                    return len({l.strip() for l in p.read_text(errors="replace").splitlines() if l.strip()})

                def _rawlines(p):
                    p = Path(p)
                    if not p.exists():
                        return 0
                    with open(p, "rb") as f:
                        return sum(1 for _ in f)
                (run_dir / "gdelt_fetch.json").write_text(json.dumps({
                    "start": start, "end": end, "mode": mode,
                    "files_done": _nonblank(state_dir / "done.txt"),
                    "macro_files_done": _nonblank(state_dir / "macro_done.txt"),
                    "absent_files": _nonblank(state_dir / "absent.txt"),
                    "transient_files": _distinct(state_dir / "transient.txt"),
                    "matches": _rawlines(out_dir / "matches.jsonl"),
                    "macro_matches": _rawlines(out_dir / "macro_matches.jsonl"),
                    "error": "master-download-failed",
                }, indent=1))
                return {"gdelt-fetch": "master-download-failed"}
            except OSError:
                return {"gdelt-fetch": "checkpoint-io-failed"}

    # (b) Run filter script — build argv ONCE: script path appears exactly
    # once; master flags are added only in the matching mode, then shared
    # flags follow (--budget-seconds only when > 0).
    script = CODE / "scripts" / "gdelt_gkg_filter.py"
    aliases = CODE / "evaluation" / "gdelt_alias_table.csv"
    themes = CODE / "evaluation" / "gdelt_macro_themes.csv"
    cmd = [sys.executable, str(script)]
    if mode == "live":
        cmd += ["--master", str(master_path),
                "--master-translation", str(trans_path)]
    elif mode == "fixtures":
        fx = os.environ.get("GDELT_FIXTURE_MASTER_DIR")
        if fx:
            fxp = Path(fx)
            m = fxp / "masterfilelist.txt"
            mt = fxp / "masterfilelist-translation.txt"
            if m.exists():
                cmd += ["--master", str(m)]
            if mt.exists():
                cmd += ["--master-translation", str(mt)]
    cmd += ["--aliases", str(aliases),
            "--themes", str(themes),
            "--start", start, "--end", end,
            "--state", str(state_dir),
            "--out", str(out_dir),
            "--workers", str(workers)]
    if budget and budget > 0:
        cmd += ["--budget-seconds", str(budget)]

    timed_out = False
    try:
        # The queue write credential must never reach a tool process:
        # same denylist-filtered env as the neighbouring tool launches.
        filter_env = {k: v for k, v in os.environ.items()
                      if k not in ENV_DENY_FOR_TOOLS}
        r = sh_group(" ".join(shlex.quote(c) for c in cmd), cwd=str(CODE),
                     env=filter_env, timeout=7200)
        rc = r.returncode
        out_text = (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired as e:
        # sh_group killed the whole process group; keep going so the
        # partial output is copied, summarised and archived.
        timed_out = True
        rc = None
        def _txt(v):
            return v.decode("utf-8", "replace") if isinstance(v, bytes) \
                else (v or "")
        out_text = _txt(e.output) + _txt(e.stderr)

    # 959m F10: classify an UNSAFE checkpoint exit (rc 75 without
    # safe=1) BEFORE copying or re-reading any checkpoint file, so an
    # unreadable absent.txt cannot raise ahead of the quarantine/retry path.
    unsafe_exit = (not timed_out and rc == GDELT_CHECKPOINT_IO_RC
                   and "gkg-filter-checkpoint-error safe=1" not in out_text)
    read_failed = False
    files_done = macro_files_done = absent_files = transient_files = 0
    matches = macro_matches = 0
    if not unsafe_exit:
        try:
            # (d) Copy filter outputs into workdir so publish() archives them.
            # Do NOT copy raw GKG zips (script doesn't keep them).
            for fn in ("matches.jsonl", "macro_matches.jsonl"):
                src = out_dir / fn
                if src.exists():
                    shutil.copy2(src, run_dir / fn)
                else:
                    (run_dir / fn).unlink(missing_ok=True)   # no stale copy

            # state summary
            done_txt = state_dir / "done.txt"
            macro_done_txt = state_dir / "macro_done.txt"
            if done_txt.exists():
                files_done = len([l for l in done_txt.read_text().splitlines() if l.strip()])
            if macro_done_txt.exists():
                macro_files_done = len([l for l in macro_done_txt.read_text().splitlines() if l.strip()])
            absent_txt = state_dir / "absent.txt"
            if absent_txt.exists():
                absent_files = len([l for l in absent_txt.read_text().splitlines() if l.strip()])
            transient_txt = state_dir / "transient.txt"
            if transient_txt.exists():
                # DISTINCT files that have failed transiently at least once: a new
                # file's first failure is progress (the filter moved on to files not
                # yet attempted), a repeat failure of the same file is not.
                transient_files = len({l.strip() for l in transient_txt.read_text(errors="replace").splitlines() if l.strip()})

            def _lines(p):
                p = Path(p)
                if not p.exists():
                    return 0
                # Binary: a timed-out filter can leave a truncated multibyte
                # UTF-8 record, which must not raise before the status is set.
                with open(p, "rb") as f:
                    return sum(1 for _ in f)

            matches = _lines(out_dir / "matches.jsonl")
            macro_matches = _lines(out_dir / "macro_matches.jsonl")

            # state config
            state_summary = {}
            cfg = state_dir / "config.json"
            if cfg.exists():
                try:
                    state_summary = json.loads(cfg.read_text())
                except Exception:
                    state_summary = {}

            # Copy state summary into workdir
            (run_dir / "gdelt-state-summary.json").write_text(
                json.dumps({"files_done": files_done,
                            "macro_files_done": macro_files_done,
                            "absent_files": absent_files,
                            "matches": matches,
                            "macro_matches": macro_matches,
                            "config": state_summary}, indent=1))

        except (OSError, ValueError):
            # Checkpoint or report not readable/copied: never publish it as
            # progress; the retryable no-publish outcome applies.
            read_failed = True
            files_done = macro_files_done = absent_files = 0
            transient_files = matches = macro_matches = 0

    # (f) Progress log
    log_line = f"start={start} end={end} files_done={files_done} matches={matches} macro_matches={macro_matches}\n"
    # Determine status. A budget-limited run (the filter prints
    # "budget exhausted; rerun to resume") and a timeout are INCOMPLETE:
    # the caller archives them but must not mark the queue job done.
    if read_failed:
        # 959m F10 / 959n F12: the checkpoint or report could not be
        # read/copied, so it is never published as progress (retryable, no
        # publish). Checked BEFORE timed_out: a timeout plus a read failure
        # must not publish (timeout is in GDELT_INCOMPLETE, hence archived).
        status = "checkpoint-io-failed"
    elif timed_out:
        status = "timeout"
    elif rc == GDELT_CHECKPOINT_IO_RC:
        # Retryable checkpoint I/O failure (distinct from deterministic
        # refusals, which stay "exit-1"). Incomplete only when the filter
        # reports the checkpoint safe to reuse; otherwise nothing is
        # published and the job is retried.
        status = ("checkpoint-io-incomplete"
                  if "gkg-filter-checkpoint-error safe=1" in out_text
                  else "checkpoint-io-failed")
    elif rc != 0:
        status = "exit-%d" % rc
    elif "budget exhausted" in out_text:
        status = "budget-exhausted"
    elif _gkg_unfinished(out_text) > 0:
        status = "unfinished"
    else:
        status = "ok"
    if status != "ok":
        log_line += "status=%s\n" % status
        # bounded tail of the filter's stdout+stderr for diagnosis
        log_line += "--- filter output tail (max 4000 chars) ---\n" \
            + out_text[-4000:] + "\n"
    (run_dir / "gdelt-fetch.log").write_text(log_line)

    # Sidecar: runner writes workdir/gdelt/gdelt_fetch.json; the dispatch
    # branch reads it into manifest['gdelt_fetch'].
    (run_dir / "gdelt_fetch.json").write_text(json.dumps({
        "start": start, "end": end, "mode": mode,
        "files_done": files_done, "macro_files_done": macro_files_done,
        "absent_files": absent_files,
        "transient_files": transient_files,
        "matches": matches, "macro_matches": macro_matches,
        "status": status,
    }, indent=1))

    return {"gdelt-fetch": status}


# --- Issue #283: paired A/B single-URL EGX diagnostic probe -------
# /ar/ warmup 403). The two tools launch Chromium differently and
# time and configuration are confounded across all runs so far, so
# this probe runs BOTH launch configs against ONE fixed URL
# (scripts/diag_egx_ab.py, legs A-B-A, clean context close between
# legs). The URL is fixed in the script: the job takes no arguments.
# A probe that records both legs resetting is an honest "ok" with
# verdict shared-access-problem, not a job failure — the record,
# not the EGX response, is the deliverable (same honest-failure
# rule as run_top30_enumerate). Dispatches in _execute_body before
# parse_job, like harvest-egx / top30-enumerate: the registry has
# no diag tool. Runs on the worker only, after verify -> merge ->
# promote -> adopt.
DIAG_EGX_AB_TIMEOUT = 1800  # 3 legs x 90 s nav + settle + launch


def parse_diag_egx_ab_job(job):
    """Parse a `diag-egx-ab` job string into a plan dict, or None
    when the string is not exactly that job. Grammar: `diag-egx-ab`
    and nothing else — the URL is fixed in scripts/diag_egx_ab.py,
    so any argument fails closed (None). NOTE: parse_job (the
    registry grammar) still returns [] for this string — the
    registry has no diag tool. Dispatch happens in _execute_body
    before parse_job, like harvest-egx."""
    # Issue #381: isinstance, not `or ""` — see parse_top30_job.
    parts = (job if isinstance(job, str) else "").split()
    if parts != ["diag-egx-ab"]:
        return None
    return {"kind": "diag-egx-ab"}


def run_diag_egx_ab(job, workdir):
    """Issue #283: run scripts/diag_egx_ab.py for one `diag-egx-ab`
    job, in the egx-harvest playwright venv, under xvfb-run (leg A
    is headful iff DISPLAY is set, exactly like run_harvest, so the
    harvester launch is reproduced faithfully). The record +
    human log land under workdir/diag-egx-ab/ and ride the archive
    publish. Returns {"diag-egx-ab": status}:
      ok — the probe ran and the record is well-formed. Any
        verdict (config-dependent / shared-access-problem /
        not-reproduced / inconclusive) is an "ok": the record is
        the deliverable.
      bad-job — the job string is not a diag-egx-ab job.
      profile-missing / venv-failed / exit-N / record-missing /
      record-unparseable / record-invalid — named failures; the
        evidence written so far still archives, so the failure is
        inspectable.
    Live mode requires the persistent Chromium profile: the probe's
    premise is the SAME profile both tools use, and without it the
    legs would not reproduce either launch."""
    # Issue #381: job_text() — see run_top30_enumerate.
    plan = parse_diag_egx_ab_job(job_text(job))
    run_dir = Path(workdir) / "diag-egx-ab"
    run_dir.mkdir(parents=True, exist_ok=True)
    if plan is None:
        (run_dir / "diag-egx-ab-worker.log").write_text(
            "bad job: %r\n" % job["job"])
        return {"diag-egx-ab": "bad-job"}
    if not _egx_profile_dir().is_dir():
        (run_dir / "diag-egx-ab-worker.log").write_text(
            "diag needs the persistent Chromium profile at %s "
            "(created by a harvest run); refusing to probe without "
            "it\n" % _egx_profile_dir())
        return {"diag-egx-ab": "profile-missing"}
    py, venv_ready = _ensure_egx_playwright_venv()
    if not venv_ready:
        (run_dir / "diag-egx-ab-worker.log").write_text(
            "playwright venv not ready: no interpreter at %s\n" % py)
        return {"diag-egx-ab": "venv-failed"}
    script = CODE / "scripts" / "diag_egx_ab.py"
    cmd = [str(py), str(script),
           "--profile", str(_egx_profile_dir()),
           "--out-dir", str(run_dir)]
    if Path("/usr/bin/xvfb-run").exists():
        # run_harvest's wrapper, verbatim: leg A needs DISPLAY.
        cmd = ["xvfb-run", "-a", "-s", "-screen 0 1366x768x24"] + cmd
    env = {k: v for k, v in os.environ.items()
           if k not in ENV_DENY_FOR_TOOLS}
    # shlex.quote each part: the profile/out paths come from the
    # worker root, but the quoting rule is the same as
    # run_top30_enumerate (INS-R3-01).
    r = sh(" ".join(shlex.quote(c) for c in cmd), cwd=run_dir,
           env=env, timeout=DIAG_EGX_AB_TIMEOUT)
    (run_dir / "diag-egx-ab-worker.log").write_text(
        (r.stdout + r.stderr)[-4000:])
    if r.returncode != 0:
        return {"diag-egx-ab": "exit-%d" % r.returncode}
    record_path = run_dir / "diag-egx-ab.json"
    if not record_path.exists():
        return {"diag-egx-ab": "record-missing"}
    try:
        record = json.loads(record_path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001 — named failure, not a crash
        (run_dir / "diag-egx-ab-worker.log").write_text(
            "record unparseable: %s: %s\n" % (type(e).__name__, e))
        return {"diag-egx-ab": "record-unparseable"}
    legs = record.get("legs_records") \
        if isinstance(record, dict) else None
    if not isinstance(legs, list) or not legs or not all(
            isinstance(leg, dict) and leg.get("classification")
            for leg in legs):
        return {"diag-egx-ab": "record-invalid"}
    return {"diag-egx-ab": "ok"}


# --- Issue #446: walk-forward backtest cells (design #436 §6.4) --
# PR #441 shipped the harness (scripts/backtest.py) but no worker
# dispatch: parse_job's grammar has no backtest tool, so the
# design's job string `run backtest <cutoff> <ticker>` produced an
# empty plan and failed closed as unknown-job (#371) without any
# cell ever executing. The entry point below dispatches in
# _execute_body before parse_job, like top30-enumerate /
# diag-egx-ab, and runs the harness from the release checkout with
# its only output root pointed at the run dir, so the cell's
# captures + scores ride the archive publish and the forward
# ledger is never touched.
BACKTEST_TIMEOUT = 7200  # capture + 3 runners (Kronos x2) + scoring


def parse_backtest_job(job):
    """Parse a `run backtest` job string into a plan dict, or None
    when the string is not exactly that job. Grammar:
    `run backtest <cutoff> <ticker>` — the cutoff a canonical
    YYYY-MM-DD date, the ticker one token (uppercased here).
    Unknown or extra tokens fail closed (None): a job the worker
    does not understand must never run. NOTE: parse_job (the
    registry grammar) still returns [] for this string — the
    registry has no backtest tool. Dispatch happens in
    _execute_body before parse_job, like top30-enumerate."""
    # Issue #381: isinstance, not `or ""` — see parse_top30_job.
    parts = (job if isinstance(job, str) else "").split()
    if len(parts) != 4 or parts[:2] != ["run", "backtest"]:
        return None
    cutoff = parts[2]
    try:
        parsed = datetime.strptime(cutoff, "%Y-%m-%d")
    except ValueError:
        return None
    if parsed.strftime("%Y-%m-%d") != cutoff:
        return None  # canonical form only (2023-2-9 is not a cutoff)
    ticker = parts[3].upper()
    if not re.fullmatch(r"[A-Z0-9][A-Z0-9.\-]*", ticker):
        return None
    return {"kind": "backtest", "cutoff": cutoff, "ticker": ticker}


def run_backtest(job, workdir):
    """Issue #446: run one walk-forward backtest cell (design #436
    §6.4) via scripts/backtest.py from the release checkout.

    Pins first (the D2/#65 discipline run_tool enforces): every
    runner checkout is prepared and verified against the release
    registry pin — clone if missing, fetch + checkout on a
    mismatch, HEAD re-verified — because a release can promote a
    pin before the next live tool run, and the harness must never
    execute a checkout the current registry has not pinned. Each
    runner then runs under its own venv interpreter
    (VENVS/<id>/bin/python), whose requirements marker
    (.gator-requirements-sha, maintained by run_tool) must match
    the prepared checkout's requirements.txt. The harness itself
    is stdlib + repo scripts and runs under the worker's own
    interpreter, launched via sh_group so a timeout kills the
    whole process tree before the result archives.

    Returns {"backtest": status}:
      ok — the cell ran and its manifest is in the run dir.
      skipped — the harness completed with a skipped cell (a gate
        or data refusal); it writes no manifest, and the reason is
        the result JSON at the tail of the log.
      bad-job — the job string is not a `run backtest` job.
      ref-unpinned / ref-unavailable / ref-mismatch — a runner
        checkout could not be confirmed at its registry pin
        (ref-mismatch includes a tracked working-tree change at
        the pin: HEAD equality proves the commit, not the tree).
      setup-timeout / setup-failed — the preparation phase timed
        out or errored; the log names the runner + operation.
      venv-missing — a runner venv interpreter is absent (the
        tool has not run on this box yet).
      venv-stale — a venv's requirements marker does not match
        its checkout's requirements.txt (a sweep rebuilds it).
      timeout — the harness exceeded BACKTEST_TIMEOUT; the
        failure archives like every other named failure instead
        of escaping _execute_body unpublished.
      exit-N / manifest-unparseable / manifest-invalid — named
        failures; the evidence written so far still archives, so
        the failure is inspectable."""
    # Issue #381: job_text() — see run_top30_enumerate.
    plan = parse_backtest_job(job_text(job))
    run_dir = Path(workdir) / "backtest"
    run_dir.mkdir(parents=True, exist_ok=True)
    log_path = run_dir / "backtest-worker.log"
    if plan is None:
        log_path.write_text("bad job: %r\n" % job["job"])
        return {"backtest": "bad-job"}
    runners = ("kronos", "pandas-ta", "talib")
    # The whole preparation phase converts timeouts and execution
    # errors into named setup failures (round-4 review): an
    # uncaught TimeoutExpired from a prep fetch would escape
    # _execute_body unpublished, exactly like the harness timeout
    # did before round 2. prep_step names the runner + operation
    # in the log.
    prep_step = "registry"
    try:
        reg = {t["id"]: t for t in registry()["tools"]}
        for tool in runners:
            prep_step = "%s checkout" % tool
            entry = reg.get(tool) or {}
            pin = entry.get("ref")
            if not pin or not re.fullmatch(r"[0-9a-f]{40}", pin):
                log_path.write_text(
                    "runner %s: registry ref unpinned (%r)\n"
                    % (tool, pin))
                return {"backtest": "ref-unpinned"}
            repo = RUNNERS / tool
            if not repo.exists():
                url = "https://github.com/%s/%s" % (
                    ORG, entry.get("repo") or tool + "-runner")
                if sh(f"git clone --depth 1 {url} {repo}",
                      timeout=600).returncode != 0:
                    log_path.write_text(
                        "runner %s: clone failed\n" % tool)
                    return {"backtest": "ref-unavailable"}
            head = sh(f"git -C {repo} rev-parse HEAD", timeout=60)
            head_sha = head.stdout.strip() \
                if head.returncode == 0 else ""
            if head_sha != pin:
                # run_tool's fetch discipline: shallow first, full
                # fetch as fallback, then checkout the pin.
                if sh(f"git -C {repo} fetch --depth 1 origin {pin}",
                      timeout=180).returncode != 0:
                    if sh(f"git -C {repo} fetch origin {pin}",
                          timeout=180).returncode != 0:
                        log_path.write_text(
                            "runner %s: pin %s unreachable "
                            "(checkout at %s)\n"
                            % (tool, pin, head_sha or "?"))
                        return {"backtest": "ref-unavailable"}
                if sh(f"git -C {repo} checkout {pin}",
                      timeout=120).returncode != 0:
                    log_path.write_text(
                        "runner %s: checkout of pin %s failed\n"
                        % (tool, pin))
                    return {"backtest": "ref-unavailable"}
                head = sh(f"git -C {repo} rev-parse HEAD",
                          timeout=60)
                head_sha = head.stdout.strip() \
                    if head.returncode == 0 else ""
                if head_sha != pin:
                    log_path.write_text(
                        "runner %s: checkout at %s after "
                        "preparation, pin is %s\n"
                        % (tool, head_sha or "?", pin))
                    return {"backtest": "ref-mismatch"}
            # HEAD == pin proves the commit, not the working tree:
            # a tracked local modification would execute modified
            # code while the manifest records the pinned HEAD.
            status = sh(f"git -C {repo} status --porcelain "
                        f"--untracked-files=no", timeout=60)
            if status.returncode != 0 or status.stdout.strip():
                log_path.write_text(
                    "runner %s: tracked working-tree changes at "
                    "pin %s (or status failed): %s\n"
                    % (tool, pin,
                       (status.stdout.strip().splitlines()
                        or ["(status command failed)"])[0]))
                return {"backtest": "ref-mismatch"}
        venv_pythons = {t: VENVS / t / "bin" / "python"
                        for t in runners}
        missing = [t for t in runners
                   if not venv_pythons[t].exists()]
        if missing:
            log_path.write_text(
                "runner venv interpreter(s) missing: %s \u2014 the "
                "tool has not run on this box yet, so its venv "
                "(built by run_tool from the pinned ref's "
                "requirements) does not exist\n" % ", ".join(
                    "%s (%s)" % (t, venv_pythons[t])
                    for t in missing))
            return {"backtest": "venv-missing"}
        for tool in runners:
            prep_step = "%s venv" % tool
            req = RUNNERS / tool / "requirements.txt"
            req_sha = _sha256_file(req) if req.exists() else ""
            marker = VENVS / tool / ".gator-requirements-sha"
            installed = marker.read_text().strip() \
                if marker.is_file() else ""
            if installed != req_sha:
                log_path.write_text(
                    "runner %s: venv requirements marker %s does "
                    "not match the prepared checkout's "
                    "requirements %s \u2014 a sweep run rebuilds "
                    "the venv\n"
                    % (tool, installed or "(none)",
                       req_sha or "(none)"))
                return {"backtest": "venv-stale"}
    except subprocess.TimeoutExpired:
        log_path.write_text(
            "setup timed out during %s\n" % prep_step)
        return {"backtest": "setup-timeout"}
    except OSError as exc:
        log_path.write_text(
            "setup failed during %s: %s\n" % (prep_step, exc))
        return {"backtest": "setup-failed"}
    script = CODE / "scripts" / "backtest.py"
    cmd = [sys.executable, str(script),
           "--cutoff", plan["cutoff"],
           "--ticker", plan["ticker"],
           "--out-root", str(run_dir),
           "--kronos-runner", str(RUNNERS / "kronos"),
           "--pandas-ta-runner", str(RUNNERS / "pandas-ta"),
           "--talib-runner", str(RUNNERS / "talib"),
           "--kronos-python", str(venv_pythons["kronos"]),
           "--pandas-ta-python", str(venv_pythons["pandas-ta"]),
           "--talib-python", str(venv_pythons["talib"]),
           "--borsagator-root", str(CODE),
           "--repeat-kronos"]
    env = {k: v for k, v in os.environ.items()
           if k not in ENV_DENY_FOR_TOOLS}
    # shlex.quote each part: the run-dir path comes from the worker
    # root, but the quoting rule is the same as run_diag_egx_ab.
    try:
        r = sh_group(" ".join(shlex.quote(c) for c in cmd),
                     cwd=CODE, env=env, timeout=BACKTEST_TIMEOUT)
    except subprocess.TimeoutExpired:
        log_path.write_text(
            "harness timed out after %ds; process group "
            "terminated\n" % BACKTEST_TIMEOUT)
        return {"backtest": "timeout"}
    log_path.write_text((r.stdout + r.stderr)[-4000:])
    if r.returncode != 0:
        return {"backtest": "exit-%d" % r.returncode}
    manifest_path = run_dir / plan["cutoff"] / plan["ticker"] \
        / "manifest.json"
    if not manifest_path.exists():
        # A skipped cell writes no manifest; its reason is the
        # result JSON at the tail of the log above.
        return {"backtest": "skipped"}
    try:
        manifest = json.loads(
            manifest_path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001 — named failure, not a crash
        (run_dir / "backtest-worker.log").write_text(
            "manifest unparseable: %s: %s\n" % (type(e).__name__, e))
        return {"backtest": "manifest-unparseable"}
    if not isinstance(manifest, dict) \
            or manifest.get("status") != "ok":
        return {"backtest": "manifest-invalid"}
    return {"backtest": "ok"}


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


# --- Issue #278: live disclosure-events feed (option A, sweep-live) ---
# The #109 pilot proved extraction on archived harvests; this wires
# the feed live, worker-side, in two phases around the sweep's tool
# loop in _execute_body:
#   phase 1 (pre-sweep refresh): force a fresh official EGX harvest
#     for every in-scope ticker in the plan (POUL/COMI, v1) BEFORE
#     any tool runs, so the news-disclosure tool's ensure_harvest
#     serves the just-refreshed cache;
#   phase 2 (extraction): after the tool loop, BEFORE maybe_merge
#     (extraction-before-ensemble), run scripts/disclosure_events.py
#     over each refreshed harvest and write per-ticker events files
#     into the run dir, all under this sweep's job id.
#   phase 3 (#308, inside phase 2 per ticker): run
#     scripts/pdf_verify.py over the just-extracted events against
#     the PDFs phase 1 captured (archive-root + hash-checked reads,
#     per captured-attachment pointers). Recorded only, in
#     extraction[code]["pdf_verification"] and
#     disclosure-events/<CODE>-verification.json: it never changes
#     an event or its verification_status, never changes the
#     extraction outcome, and never fails a sweep — a ticker with
#     no captured attachments verifies as no-coverage, a cached
#     refresh (no PDFs on disk this sweep) as
#     skipped-no-attachments, and a verifier failure as
#     verification-failed. Verifier output must not feed #283
#     acceptance until the #308 live run is checked.
# "Live" means sweep-live only: a disclosure published after market
# close is picked up by the NEXT sweep's refresh — no intraday
# alerting is promised or built in v1.
# Freshness / failure policy (defined here, enforced by the code):
#   refreshed — the refresh ran inside this sweep (harvested_at >=
#     sweep start); extraction runs.
#   cached    — the refresh failed but the on-box cache is still
#     within DISCLOSURE_FRESH_HOURS; extraction runs, flagged
#     cached with its age recorded.
#   failed    — the refresh failed and there is no usable cache
#     (absent, or older than DISCLOSURE_FRESH_HOURS); extraction is
#     SKIPPED for that ticker — the sweep never extracts from stale
#     input. The failure is recorded in manifest["disclosure_feed"]
#     AND in disclosure_feed_error.txt in the run dir (both ride
#     the archive); the sweep itself still runs (fleet + ensemble
#     are unaffected in v1 — nothing consumes events yet; #280/#281
#     own consumption) so a dead feed never loses a sweep.
#   extraction-failed / stale-input — the extractor errored, its
#     output failed validation, or the harvest changed / aged past
#     the bound between the phases; no events file is kept for that
#     ticker, the failure is recorded the same way, the sweep
#     still runs.
# The extraction gate re-verifies the harvest file phase 1 recorded
# (same harvested_at, still within the freshness bound): a harvest
# that changed under us, or aged past the bound between the phases,
# is refused as stale-input rather than extracted. A later refresh
# by the news tool's own ensure_harvest does NOT rescue a failed
# phase 1 — the feed consumes only what the pre-sweep refresh
# produced or validated; the next sweep re-extracts the full
# 90-day window, so skipping loses no disclosure.
DISCLOSURE_TICKERS = ("POUL", "COMI")
DISCLOSURE_FRESH_HOURS = 12  # same bound as HARVEST_TTL_HOURS
DISCLOSURE_EXTRACT_TIMEOUT = 300
PDF_VERIFY_TIMEOUT = 300  # #308: per-ticker pdf_verify subprocess bound


def _harvest_meta(path):
    """(harvested_at, n_items, age_hours) for a disclosures.json
    file, or None when it is missing or unparseable. Age is from the
    file mtime (robust when harvested_at is absent); harvested_at is
    the provenance the refresh recorded."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return None
    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return None
    try:
        age_h = (time.time() - Path(path).stat().st_mtime) / 3600
    except OSError:
        return None
    return (data.get("harvested_at") or "", len(items), age_h)


def _egx_tickers_in_plan(plan):
    """In-scope EGX codes for the disclosure feed, in plan order:
    news-disclosure entries with a .CA ticker in DISCLOSURE_TICKERS.
    Out-of-scope .CA tickers are reported separately (skipped with
    a reason), never silently dropped."""
    in_scope, out = [], []
    for tool, ticker in plan or []:
        if tool != "news-disclosure":
            continue
        tk = (ticker or "").upper()
        if not tk.endswith(".CA"):
            continue
        code = tk.split(".")[0]
        if code in DISCLOSURE_TICKERS:
            if code not in in_scope:
                in_scope.append(code)
        elif code not in out:
            out.append(code)
    return in_scope, out


def refresh_harvest(code, workdir):
    """Force a fresh EGX harvest for `code` (#278 phase 1). Always
    runs run_harvest (no 12 h TTL shortcut — the point is a harvest
    inside this sweep's window); on success the on-box cache is
    updated and ("refreshed", cache_path, detail) is returned. On a
    failed refresh the cache still serves when it is within
    DISCLOSURE_FRESH_HOURS ("cached", ...); otherwise ("failed",
    None, detail). Never raises: a harvester crash is a failed
    refresh, not a dead sweep."""
    cache_dir = ROOT / "harvest"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache = cache_dir / f"{code}.json"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    fake_job = {"id": f"disclosure-refresh-{code}-{stamp}",
                "job": f"harvest-egx {code}", "added": now()}
    wd = Path(workdir) / "disclosure-refresh" / code
    wd.mkdir(parents=True, exist_ok=True)
    try:
        res = run_harvest(fake_job, wd)
        src = wd / "egx-harvest" / "results" / "disclosures.json"
        if res.get("egx-harvest") == "ok" and src.exists():
            meta = _harvest_meta(src)
            if meta is not None and meta[1] > 0:
                cache.write_bytes(src.read_bytes())
                return ("refreshed", cache,
                        f"harvested_at={meta[0]} items={meta[1]}")
            return ("failed", None,
                    "harvest succeeded but produced no usable items")
        detail = f"run_harvest returned {res.get('egx-harvest')}"
    except Exception as e:  # noqa: BLE001 - failed refresh, not a crash
        detail = f"run_harvest raised {type(e).__name__}: {e}"
    meta = _harvest_meta(cache)
    if meta is not None and meta[2] <= DISCLOSURE_FRESH_HOURS:
        return ("cached", cache,
                f"{detail}; serving cache harvested_at={meta[0]} "
                f"age={meta[2]:.1f}h items={meta[1]}")
    if meta is not None:
        return ("failed", None,
                f"{detail}; cache too old ({meta[2]:.1f}h > "
                f"{DISCLOSURE_FRESH_HOURS}h)")
    return ("failed", None, f"{detail}; no cache on the box")


def _record_disclosure_feed(manifest, entry):
    """Best-effort manifest record: the feed outcome must be
    recorded whenever the manifest is the dict _execute_body built,
    and a malformed manifest must still never raise into the sweep
    path."""
    try:
        manifest["disclosure_feed"] = entry
    except Exception:  # noqa: BLE001 - recording must never raise
        print(f"disclosure feed: manifest not writable, outcome: "
              f"{entry}", flush=True)


def _write_disclosure_feed_files(workdir, record):
    """Mirror the feed record into the run dir so it rides the
    archive as its own file (disclosure_feed.json), plus a
    human-readable error file whenever the feed is not ok. Never
    raises: a failed write is recorded in the record, and the
    manifest copy (written by _write_manifest_atomic) survives."""
    try:
        tmp = Path(workdir) / ".disclosure_feed.json.tmp"
        tmp.write_text(json.dumps(record, indent=1, ensure_ascii=False),
                       encoding="utf-8")
        os.replace(tmp, Path(workdir) / "disclosure_feed.json")
    except Exception as e:  # noqa: BLE001 - file mirror is evidence
        record["feed_file_write_failed"] = (
            f"{type(e).__name__}: {e}")[:200]
    if record.get("status") != "ok":
        try:
            lines = [f"disclosure feed: status={record.get('status')}",
                     f"sweep_id={record.get('sweep_id')} "
                     f"origin={record.get('origin')} "
                     f"mode={record.get('mode')}"]
            for code, tick in (record.get("tickers") or {}).items():
                lines.append(f"{code}: refresh={tick.get('refresh')} "
                             f"{tick.get('detail', '')}")
            for code, ext in (record.get("extraction") or {}).items():
                if ext.get("status") != "extracted":
                    lines.append(f"{code}: extraction="
                                 f"{ext.get('status')} "
                                 f"{ext.get('detail', '')}")
            (Path(workdir) / "disclosure_feed_error.txt").write_text(
                "\n".join(lines) + "\n", encoding="utf-8")
        except Exception:  # noqa: BLE001 - error file is evidence
            pass


def refresh_disclosure_feed(job, workdir, manifest, plan):
    """#278 phase 1 — pre-sweep refresh of the official EGX
    disclosure feed. Runs only for sweep / sweep-lite jobs with a
    plan, before any tool runs. Returns the feed record dict (also
    stored in manifest["disclosure_feed"]), or None for a job the
    feed does not cover. Never raises: a harvester failure is a
    recorded feed failure, not a dead sweep."""
    try:
        kind = job_text(job).split()  # Issue #381: isinstance normalization, not `or ""`
        if not kind or kind[0] not in ("sweep", "sweep-lite") or not plan:
            return None
        job_id = str(job.get("id", ""))
        record = {
            "sweep_id": job_id,
            "origin": ("scheduled"
                       if job_id.startswith(SCHEDULED_JOB_PREFIX)
                       else "on-demand"),
            "mode": "sweep-live",
            "intraday_alerting": False,
            "started": manifest.get("started") or now(),
            "tickers": {},
            "status": "skipped",
        }
        in_scope, out_of_scope = _egx_tickers_in_plan(plan)
        if out_of_scope:
            record["out_of_scope"] = out_of_scope
        if not in_scope:
            record["detail"] = (
                "no in-scope EGX tickers in plan (POUL/COMI); "
                f"out of scope: {out_of_scope}")
            _record_disclosure_feed(manifest, record)
            return record
        for code in in_scope:
            status, path, detail = refresh_harvest(code, workdir)
            meta = _harvest_meta(path) if path is not None else None
            record["tickers"][code] = {
                "refresh": status,
                "detail": detail,
                **({"harvested_at": meta[0], "items": meta[1],
                    "cache_age_hours": round(meta[2], 2)}
                   if meta is not None else {}),
            }
        usable = [c for c, t in record["tickers"].items()
                  if t["refresh"] in ("refreshed", "cached")]
        record["refresh_status"] = (
            "ok" if len(usable) == len(in_scope)
            else "partial" if usable else "failed")
        record["status"] = record["refresh_status"]
        _record_disclosure_feed(manifest, record)
        return record
    except Exception as e:  # noqa: BLE001 - feed must never kill a sweep
        print(f"refresh_disclosure_feed failed: "
              f"{type(e).__name__}: {e}", file=sys.stderr, flush=True)
        return None


def _quarter_window(started_iso):
    """Extractor quarter window for a sweep: 90 days ending on the
    sweep's date, so a disclosure announced after the previous
    market close is inside the window (and not flagged stale)."""
    from datetime import timedelta
    try:
        day = datetime.fromisoformat(started_iso).date()
    except Exception:
        day = datetime.now(timezone.utc).date()
    return day - timedelta(days=90), day


def _refresh_results_dir(workdir, code):
    """#308 — archive root for this sweep's phase-1 refresh of `code`:
    the refresh workdir's results dir, under which the harvester's
    attachment pointers ("attachments/<NewsID>.pdf", #279) resolve.
    refresh_harvest() writes into exactly this path; a cached
    refresh has no results dir this sweep, so verification skips."""
    return Path(workdir) / "disclosure-refresh" / code \
        / "egx-harvest" / "results"


def verify_disclosure_events(code, events_path, cache, workdir):
    """#308 — run scripts/pdf_verify.py over one ticker's extracted
    events against the PDFs this sweep's phase-1 refresh captured
    (per captured-attachment pointers, archive-root + hash-checked
    reads exactly as the verifier does standalone). Returns the
    pdf_verification record for extraction[code]; the caller stores
    it and writes the verification JSON into the run dir
    (disclosure-events/<CODE>-verification.json) so it rides the
    archive. Never raises and never changes the extraction outcome:
    a verifier failure is recorded, not fatal — the sweep runs
    either way, and tickers without captured attachments verify as
    no-coverage. Statuses: verified (exit 0), with-failures
    (exit 1: partial / mismatch / missing / inconclusive recorded),
    no-coverage (exit 2: zero events checked), verification-failed
    (script missing / crash / timeout / bad output),
    skipped-no-attachments (no refresh results dir on disk — a
    cached refresh has no PDFs this sweep). Verifier output is
    NEVER used to change an event or its verification_status here
    (#283 acceptance must not consume it until the #308 live run
    is checked)."""
    base = {"status": "verification-failed", "summary": {},
            "verification_file": None, "detail": ""}
    try:
        archive_root = _refresh_results_dir(workdir, code)
        if not (archive_root / "attachments").is_dir():
            base["status"] = "skipped-no-attachments"
            base["detail"] = ("no attachments dir on disk for this "
                              "sweep (refresh was cached, or the "
                              "harvest captured none)")
            return base
        script = CODE / "scripts" / "pdf_verify.py"
        if not script.is_file():
            base["detail"] = "verifier script missing: %s" % script
            return base
        out_path = Path(workdir) / "disclosure-events" / (
            "%s-verification.json" % code)
        # The verifier writes --out itself and never creates the
        # parent: extraction normally created disclosure-events/
        # already, but guarantee it here so a missing dir can never
        # turn a verification run into a crash (a verifier traceback
        # also exits 1, which would otherwise masquerade as a
        # checked-events failure).
        out_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            proc = subprocess.run(
                [sys.executable, str(script), "verify", str(events_path),
                 "--disclosures", str(cache),
                 "--archive-root", str(archive_root),
                 "--out", str(out_path)],
                capture_output=True, text=True,
                timeout=PDF_VERIFY_TIMEOUT)
        except Exception as e:  # noqa: BLE001 - verifier failure
            base["detail"] = ("verifier raised %s: %s"
                              % (type(e).__name__, e))
            return base
        if proc.returncode not in (0, 1, 2):
            base["detail"] = ("verifier exited %s: %s"
                              % (proc.returncode,
                                 (proc.stdout + proc.stderr).strip()[-300:]))
            return base
        try:
            out = json.loads(out_path.read_text(encoding="utf-8"))
            summary = out.get("summary") or {}
        except Exception as e:  # noqa: BLE001 - bad verifier output
            base["detail"] = "verifier output invalid: %s" % e
            return base
        base["summary"] = summary
        base["verification_file"] = (
            "disclosure-events/%s-verification.json" % code)
        if proc.returncode == 0:
            base["status"] = "verified"
            base["detail"] = ("all checked events role-verified in "
                              "the stored PDFs")
        elif proc.returncode == 1:
            base["status"] = "with-failures"
            base["detail"] = ("checked events with failures: %s"
                              % ", ".join(
                                  "%s=%s" % (k, summary.get(k))
                                  for k in ("verified", "partial",
                                            "mismatch", "missing",
                                            "inconclusive")
                                  if summary.get(k)))
        else:
            base["status"] = "no-coverage"
            base["detail"] = ("zero events checked (no captured "
                              "attachment for any event)")
        return base
    except Exception as e:  # noqa: BLE001 - verification must not kill
        base["detail"] = ("verification failed: %s: %s"
                          % (type(e).__name__, e))
        return base


def extract_disclosure_events(job, workdir, manifest, plan):
    """#278 phase 2 — extraction before the ensemble. Runs only for
    sweep / sweep-lite jobs, after the tool loop and before
    maybe_merge. Extracts events from each harvest phase 1 produced
    or validated, writes per-ticker events files into the run dir
    (disclosure-events/<CODE>-events.json), and records the outcome
    — including ordering/provenance (sweep id, origin, harvest
    timestamp, quarter window) — in manifest["disclosure_feed"] and
    disclosure_feed.json. A failed or stale feed is recorded, never
    silent, and the sweep still runs. Never raises."""
    try:
        kind = job_text(job).split()  # Issue #381: isinstance normalization, not `or ""`
        if not kind or kind[0] not in ("sweep", "sweep-lite") or not plan:
            return None
        record = manifest.get("disclosure_feed")
        if not isinstance(record, dict):
            return None
        job_id = str(job.get("id", ""))
        if record.get("sweep_id") != job_id:
            # A feed record from another sweep must never be consumed.
            record["status"] = "failed"
            record["extraction_detail"] = (
                "sweep_id mismatch: refusing to extract")
            _record_disclosure_feed(manifest, record)
            _write_disclosure_feed_files(workdir, record)
            return record
        script = CODE / "scripts" / "disclosure_events.py"
        qs, qe = _quarter_window(record.get("started") or "")
        out_dir = Path(workdir) / "disclosure-events"
        out_dir.mkdir(parents=True, exist_ok=True)
        extraction = {}
        tickers = record.get("tickers") or {}
        for code, tick in tickers.items():
            if tick.get("refresh") not in ("refreshed", "cached"):
                extraction[code] = {
                    "status": "skipped",
                    "detail": ("no usable harvest (refresh: "
                               f"{tick.get('refresh')}); extraction "
                               "refused rather than run on stale input")}
                continue
            cache = ROOT / "harvest" / f"{code}.json"
            meta = _harvest_meta(cache)
            if meta is None:
                extraction[code] = {
                    "status": "failed",
                    "detail": ("harvest cache unreadable at "
                               "extraction time")}
                continue
            if meta[0] != tick.get("harvested_at"):
                extraction[code] = {
                    "status": "stale-input",
                    "detail": (f"harvest changed between refresh and "
                               f"extraction (refresh harvested_at="
                               f"{tick.get('harvested_at')!r}, now "
                               f"{meta[0]!r}); refusing to extract")}
                continue
            if meta[2] > DISCLOSURE_FRESH_HOURS:
                extraction[code] = {
                    "status": "stale-input",
                    "detail": (f"harvest aged past the freshness bound "
                               f"between refresh and extraction "
                               f"({meta[2]:.1f}h > "
                               f"{DISCLOSURE_FRESH_HOURS}h); refusing")}
                continue
            events_path = out_dir / f"{code}-events.json"
            if not script.is_file():
                extraction[code] = {
                    "status": "extraction-failed",
                    "detail": f"extractor script missing: {script}"}
                continue
            try:
                proc = subprocess.run(
                    [sys.executable, str(script), "extract", str(cache),
                     "--out", str(events_path),
                     "--quarter-start", qs.isoformat(),
                     "--quarter-end", qe.isoformat()],
                    capture_output=True, text=True,
                    timeout=DISCLOSURE_EXTRACT_TIMEOUT)
            except Exception as e:  # noqa: BLE001 - extraction failure
                extraction[code] = {
                    "status": "extraction-failed",
                    "detail": (f"extractor raised "
                               f"{type(e).__name__}: {e}")}
                continue
            if proc.returncode != 0:
                extraction[code] = {
                    "status": "extraction-failed",
                    "detail": ("extractor exited "
                               f"{proc.returncode}: "
                               f"{(proc.stdout + proc.stderr).strip()[-300:]}")}
                if events_path.is_file():
                    events_path.unlink(missing_ok=True)
                continue
            try:
                out = json.loads(
                    events_path.read_text(encoding="utf-8"))
                rep = out.get("report") or {}
                if out.get("schema_version") != 1 \
                        or not isinstance(out.get("events"), list) \
                        or rep.get("documents") != meta[1]:
                    raise ValueError(
                        "output failed validation (schema_version / "
                        "events / document count)")
            except Exception as e:  # noqa: BLE001 - invalid output
                extraction[code] = {
                    "status": "extraction-failed",
                    "detail": f"extractor output invalid: {e}"}
                if events_path.is_file():
                    events_path.unlink(missing_ok=True)
                continue
            evs = out["events"]
            extraction[code] = {
                "status": "extracted",
                "events_file": f"disclosure-events/{code}-events.json",
                "events": len(evs),
                "verified": sum(
                    1 for e in evs
                    if e.get("verification_status") == "verified"),
                "candidates": sum(
                    1 for e in evs
                    if e.get("extraction_status") == "candidate"),
                "by_type": rep.get("by_type") or {},
                "harvested_at": meta[0],
                "quarter": {"start": qs.isoformat(),
                            "end": qe.isoformat()},
                "sweep_id": job_id,
            }
            # #308 — verify the just-extracted events against the
            # PDFs this sweep's phase-1 refresh captured. Recorded
            # only: it never changes the extraction outcome, and a
            # verifier failure never fails the sweep.
            extraction[code]["pdf_verification"] = \
                verify_disclosure_events(code, events_path, cache,
                                         workdir)
        record["extraction"] = extraction
        done = [c for c, e in extraction.items()
                if e["status"] == "extracted"]
        if not tickers:
            record["status"] = "skipped"
        else:
            record["status"] = (
                "ok" if done and len(done) == len(tickers)
                else "partial" if done else "failed")
        _record_disclosure_feed(manifest, record)
        _write_disclosure_feed_files(workdir, record)
        return record
    except Exception as e:  # noqa: BLE001 - feed must never kill a sweep
        print(f"extract_disclosure_events failed: "
              f"{type(e).__name__}: {e}", file=sys.stderr, flush=True)
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
                try:
                    att = json.loads(c.read_text()).get("attempt")
                except (OSError, ValueError, AttributeError):
                    att = None
                rec = {"worker": os.uname().nodename, "at": now(),
                       "job": job["job"]}
                if att:
                    rec["attempt"] = att   # 959m F11: identity survives refresh
                c.write_text(json.dumps(rec))
                push_bus(f"claim refresh {job['id']}")
            except Exception:
                pass

    t = threading.Thread(target=refresh, daemon=True)
    t.start()
    outcome = None
    try:
        outcome = _execute(job)
    finally:
        stop.set()
        if outcome == "incomplete":
            # An incomplete (resumable) run is archived but not done.
            # Stop the refresh thread FIRST (it rewrites the claim every
            # CLAIM_REFRESH_SECONDS and shares the BUS checkout), then
            # remove the queue claim so a same-id retry is not blocked
            # for the 6 h stale-claim age. Finished runs keep the
            # existing completion path and never reach this.
            t.join(timeout=300)
            if t.is_alive():
                print("execute: claim refresh thread still running; claim "
                      "of %s NOT released" % job["id"], file=sys.stderr,
                      flush=True)
            else:
                # 959n F13: persist an attempt-bound pending release BEFORE
                # deleting the claim, so an unconfirmed push is retried by
                # _gdelt_retry_cleanup (via _done_or_pending) on the next run
                # instead of waiting out the 6 h stale reclaim.
                mp = _gdelt_cleanup_marker(job["id"])
                marked = False
                try:
                    mp.parent.mkdir(parents=True, exist_ok=True)
                    mp.write_text(json.dumps({
                        "claim_pending": True,
                        "claim_attempt": _local_claim_attempt(job["id"])}))
                    marked = True
                except OSError:
                    pass
                if _release_claim(job["id"]) and marked:
                    try:
                        mp.unlink(missing_ok=True)
                    except OSError:
                        pass


def _local_claim_attempt(job_id):
    """The attempt identity of the claim this host currently holds locally
    (959m F11), or None (legacy claim without one, or no claim file)."""
    try:
        a = json.loads((BUS / "queue" / "claims" / f"{job_id}.json").read_text()).get("attempt")
        return a if isinstance(a, str) and a else None
    except (OSError, ValueError, AttributeError):
        return None


def _release_claim(job_id, only_own=False, expect_attempt=False):
    """Remove queue/claims/<id>.json from the bus and CONFIRM it is gone
    from origin/queue. Returns True only on confirmation; on failure the
    claim stays (the 6 h stale reclaim is the fallback) and it says so."""
    claim = BUS / "queue" / "claims" / f"{job_id}.json"
    rel = f"queue/claims/{job_id}.json"
    try:
        if only_own:
            # A deferred cleanup may only remove the claim THIS host placed.
            f0 = git_bus("fetch origin queue", timeout=120)
            if f0.returncode != 0:
                raise RuntimeError("fetch failed")
            r0 = git_bus("ls-tree --name-only origin/queue " + shlex.quote(rel),
                         timeout=60)
            if r0.returncode != 0:
                raise RuntimeError("ls-tree failed")
            if not (r0.stdout or "").strip():
                return True                       # already gone
            r1 = git_bus("show origin/queue:" + shlex.quote(rel), timeout=60)
            if r1.returncode != 0:
                raise RuntimeError("show failed")
            rc1 = json.loads(r1.stdout or "{}")
            owner = rc1.get("worker")
            if owner != os.uname().nodename:
                return True                       # another worker's claim: leave it
            if expect_attempt is not False and rc1.get("attempt") != expect_attempt:
                # 959m F11: same host, but a LATER attempt's claim (or one
                # we cannot attribute): the replayed cleanup must not remove it.
                return True
        claim.unlink(missing_ok=True)
        push_bus(f"release claim {job_id} (incomplete run)")
        # A fresh remote observation is required: a failed fetch would leave
        # a stale ref (and an empty ls-tree could fake a confirmation).
        f1 = git_bus("fetch origin queue", timeout=120)
        if f1.returncode != 0:
            raise RuntimeError("fetch failed")
        r = git_bus("ls-tree --name-only origin/queue " + shlex.quote(rel),
                    timeout=60)
        gone = (r.returncode == 0 and not (r.stdout or "").strip())
    except Exception:
        gone = False
    if not gone:
        print("execute: bus claim of %s NOT confirmed removed" % job_id,
              file=sys.stderr, flush=True)
    return gone


def _write_manifest_atomic(workdir, manifest):
    """Write manifest.json into the workdir atomically (temp file in
    the same dir + os.replace) so a reader never sees a partial
    manifest. Issue #148: merge.py refuses a run dir without
    manifest.json, and publish() writes it only into the archive
    dest — so a fresh worker sweep's merge always refused."""
    tmp = Path(workdir) / ".manifest.json.tmp"
    tmp.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    os.replace(tmp, Path(workdir) / "manifest.json")


def maybe_merge(job, workdir, manifest, plan):
    """Issue #67: post-sweep merge hook. Runs scripts/merge.py
    (shared module, stdlib-only) on the just-finished sweep's local
    OUT/<job-id> tree, before publish() archives fleet + merge in
    one commit. Fires only for sweep / sweep-lite plans — category
    and single-tool runs have no ensemble to build. A merge failure
    or refusal must NEVER lose the fleet: it writes merge_error.txt
    in the run dir, records manifest["merge"], and returns False so
    _execute still publishes the fleet. Never raises."""
    kind = job_text(job).split()  # Issue #381: isinstance normalization, not `or ""`
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


COMPILE_TIMEOUT = 1800


def _record_compile(manifest, entry):
    """Best-effort manifest record: the compile outcome must be
    recorded whenever the manifest is the dict _execute_body built,
    and a malformed manifest must still never raise into the publish
    path."""
    try:
        manifest["compile"] = entry
    except Exception:  # noqa: BLE001 - recording must never raise
        print(f"maybe_compile: manifest not writable, outcome: "
              f"{entry}", flush=True)


def maybe_compile(job, workdir, manifest, plan):
    """Issue #68: post-merge Report Model compile hook. Runs
    scripts/compile_model.py on the just-merged sweep dir
    (workdir/_merge_out/<sweep_dir>) after maybe_merge succeeds and
    before the second _write_manifest_atomic / publish, so
    report-model.json — or compile_error.txt on a fail-loudly
    refusal — rides the SAME archive commit as fleet + merge,
    atomic with its sweep (#68 D-2). Mirrors maybe_merge: fires
    only for sweep / sweep-lite plans; a compile refusal or crash
    never loses the fleet — it records manifest["compile"] and
    returns False so _execute still publishes. The whole body is
    guarded: a malformed manifest or a dead compiler ends in a
    recorded "error", never an exception into _execute_body. Every
    non-compiled outcome is fail-closed: with a writable sweep dir,
    a surviving report-model.json is moved aside (.quarantined, the
    #161 convention) and compile_error.txt names the CURRENT cause
    — the compiler handles its own expected refusals, the hook
    covers everything else (timeout, crash, missing/invalid model).
    If the model file can neither be quarantined nor removed
    (read-only tree), the hook records cleanup_failed + a
    suppress_model path and publish() excludes that exact file
    (validated pathlib removal, publish refused on failure) — an
    unvalidated model never publishes, not even renamed
    (.quarantined artifacts are excluded too, matching the Actions
    wiring's selective copy).
    Concurrency invariant: the local run dir is single-writer (this
    worker process) between compile and publish; the recorded
    sha256 covers the exact bytes validated, and the hook re-reads
    once after validation to prove the file did not change.
    Validation scope: --check-model is the compiler's own consumer
    validator (v1 schema); semantic correctness (ticker/digest
    linkage, source SHAs) is the compiler's compile-time contract
    (F-1/F-5/F-9, D-7), trusted here because the pinned compiler
    itself produced the model — the harness verifies ticker,
    archive_commit and compiler_sha behaviorally on the golden
    sweep rather than the hook re-deriving them."""
    sweep_dir = None
    sweep_rel = None
    status, detail = "error", "compile hook aborted before running"
    # Issue #406: outcome of the --archive-sha lookup, recorded in
    # the manifest compile entry so a failed lookup is distinct
    # from having no archive clone at all. None until the lookup
    # block runs (early exits record no field, not a guess).
    archive_lookup = None
    try:
        kind = job_text(job).split()  # Issue #381: isinstance normalization, not `or ""`
        if not kind or kind[0] not in ("sweep", "sweep-lite") or not plan:
            return False
        merge_info = manifest.get("merge")
        if not isinstance(merge_info, dict):
            merge_info = {}
        merge_status = merge_info.get("status")
        sweep_rel = merge_info.get("sweep_dir")
        # merge.py records merge status "complete" / "no-ensemble" on
        # success; maybe_merge records "failed" otherwise. Gate on
        # BOTH a successful status and a usable sweep_dir, so a
        # stale sweep_dir beside a failed merge can never compile.
        if (merge_status not in ("complete", "no-ensemble")
                or not isinstance(sweep_rel, str)
                or not sweep_rel.strip()):
            _record_compile(manifest, {
                "status": "skipped",
                "detail": ("no successful merged sweep (merge "
                           f"status: {merge_status})")})
            return False
        if os.path.isabs(sweep_rel):
            _record_compile(manifest, {
                "status": "error",
                "detail": (f"absolute sweep_dir from merge: "
                           f"{sweep_rel!r}")[:500]})
            return False
        # sweep_rel is the local merge's own merge-manifest value;
        # resolve containment (incl. symlinks) under _merge_out all
        # the same — the resolved dir must be STRICTLY below it:
        # ".", the base itself, absolute paths and symlink escapes
        # are errors, never followed.
        base = (Path(workdir) / "_merge_out").resolve()
        sweep_dir = (base / sweep_rel).resolve()
        if base not in sweep_dir.parents:
            _record_compile(manifest, {
                "status": "error",
                "detail": (f"sweep_dir escapes _merge_out: "
                           f"{sweep_rel!r}")[:500]})
            return False
        if not sweep_dir.is_dir():
            _record_compile(manifest, {
                "status": "error",
                "detail": (f"merged sweep dir missing on disk: "
                           f"{sweep_rel}")[:500]})
            return False
        compile_script = CODE / "scripts" / "compile_model.py"
        env = {k: v for k, v in os.environ.items()
               if k not in ENV_DENY_FOR_TOOLS}
        # Issue #146: one filtered env for every subprocess this
        # hook spawns, asserted at the boundary before the first.
        _assert_no_denied(env)
        cmd = [sys.executable, str(compile_script), str(sweep_dir),
               "--repo-root", str(CODE),
               "--compiler-sha", update_checkout_sha()]
        # Pin the archive HEAD the worker can see (the publish
        # clone's tip) at compile time: the sweep's own archive
        # commit does not exist yet — the same ambiguity the
        # Actions wiring records in archive_commit. With no local
        # clone yet, omit the flag and let the compiler record
        # archive-sha-unavailable rather than guess. Direct argv,
        # no shell interpolation of paths.
        arch = ROOT / "archive-push"
        if arch.is_dir():
            # Issue #398: the archive HEAD is diagnostics only —
            # a failed lookup must never abort the compile. The
            # rev-parse raises TimeoutExpired on a timeout and
            # OSError when git is missing; omit the flag on any
            # lookup failure and let the compiler record
            # archive-sha-unavailable rather than guess.
            # Issue #406: record the outcome distinctly — a clone
            # whose rev-parse fails (timeout / missing git /
            # non-zero exit / empty output) is "lookup-failed",
            # not the "no-clone" of a missing archive-push dir.
            # Both used to land on the same archive-sha-unavailable
            # fallback with nothing to tell them apart.
            # Issue #421: text=True decoding can also fail — a
            # UnicodeDecodeError from undecodable git output is a
            # lookup failure too, not a compile failure; catch
            # UnicodeError (its parent) so the diagnostic lands
            # as "lookup-failed" and the compile continues.
            try:
                head = subprocess.run(
                    ["git", "-C", str(arch), "rev-parse", "HEAD"],
                    env=env, capture_output=True, text=True, timeout=30)
            except (subprocess.TimeoutExpired, OSError, UnicodeError):
                head = None
            if head is not None and head.returncode == 0 \
                    and head.stdout.strip():
                cmd += ["--archive-sha", head.stdout.strip()]
                archive_lookup = "ok"
            else:
                archive_lookup = "lookup-failed"
        else:
            archive_lookup = "no-clone"
        proc = subprocess.run(cmd, env=env, capture_output=True,
                              text=True, timeout=COMPILE_TIMEOUT)
        if proc.stdout.strip():
            print(proc.stdout, end="", flush=True)
        if proc.stderr.strip():
            print(proc.stderr, end="", file=sys.stderr, flush=True)
        model_path = sweep_dir / "report-model.json"
        err_path = sweep_dir / "compile_error.txt"
        if proc.returncode == 0 and model_path.is_file():
            # One read: the same bytes feed the hash and the parse,
            # so the recorded sha256 covers exactly what was
            # validated and archived; a second read after the
            # consumer check proves the file did not change
            # underneath us (single-writer invariant).
            blob = model_path.read_bytes()
            try:
                model = json.loads(blob.decode("utf-8"))
            except Exception as e:
                detail = f"compile wrote an unreadable model: {e}"
            else:
                # D-7 / F-8: the compiler's own consumer-side schema
                # check must pass before the run manifest calls this
                # sweep compiled.
                chk = subprocess.run(
                    [sys.executable, str(compile_script),
                     "--check-model", str(model_path)],
                    env=env, capture_output=True, text=True,
                    timeout=COMPILE_TIMEOUT)
                if chk.returncode != 0:
                    detail = ("model failed consumer schema check: "
                              + (chk.stdout + chk.stderr).strip())
                elif model_path.read_bytes() != blob:
                    detail = ("report-model.json changed during "
                              "validation")
                else:
                    _record_compile(manifest, {
                        "status": "compiled",
                        "sweep_dir": sweep_rel,
                        "model": f"{sweep_rel}/report-model.json",
                        "model_sha256": hashlib.sha256(
                            blob).hexdigest(),
                        "degraded": model.get("degraded"),
                        "flags": model.get("flags") or [],
                        "tools": len(model.get("tools") or []),
                        "archive_commit": model.get("archive_commit"),
                        "archive_lookup": archive_lookup,
                    })
                    return True
        elif proc.returncode == 0:
            detail = "compile exited 0 but no report-model.json found"
        elif proc.returncode == 2:
            # Fail-loudly refusal (F-1 / F-5 / F-9 / F-6 / F-10):
            # no model; compile_error.txt is the compiler's own.
            detail = (err_path.read_text(
                encoding="utf-8", errors="replace").strip()
                if err_path.is_file() else
                "compile_model.py refused (exit 2): "
                + proc.stderr.strip())
            status = "refused"
        else:
            detail = (f"compile_model.py exited {proc.returncode}: "
                      f"{proc.stderr.strip()}")
    except subprocess.TimeoutExpired:
        status = "error"
        detail = f"compile timed out after {COMPILE_TIMEOUT}s"
    except Exception as e:  # noqa: BLE001 - the fleet must publish
        status = "error"
        detail = f"compile hook failed: {type(e).__name__}: {e}"
    # Fail-closed tail for every non-compiled outcome: never leave a
    # report-model.json in place that this run did not validate, and
    # make compile_error.txt name the CURRENT cause (a marker the
    # compiler wrote this run — the refusal case — is already
    # current and is kept; anything older is replaced).
    entry = {"status": status, "detail": detail[:500]}
    # Issue #406: carry the lookup outcome on the fail-closed
    # record too, when the lookup ran — a compile that fails
    # after a failed lookup must not lose the distinction.
    if archive_lookup is not None:
        entry["archive_lookup"] = archive_lookup
    if isinstance(sweep_rel, str) and sweep_rel:
        entry["sweep_dir"] = sweep_rel
        entry["error_file"] = f"{sweep_rel}/compile_error.txt"
    if sweep_dir is not None:
        stale = sweep_dir / "report-model.json"
        if stale.is_file():
            try:
                os.replace(stale, str(stale) + ".quarantined")
            except OSError:
                try:
                    os.remove(stale)
                except OSError as exc:
                    # Absolute removal is impossible here (read-only
                    # tree): do NOT pretend fail-closed held — record
                    # the evidence and suppress the file at publish.
                    entry["cleanup_failed"] = (
                        f"{type(exc).__name__}: {exc}")[:300]
                    entry["suppress_model"] = (
                        f"{sweep_rel}/report-model.json")
        marker = sweep_dir / "compile_error.txt"
        if status != "refused" or not marker.is_file():
            try:
                marker.write_text(f"compile {status}: {detail}\n")
            except OSError as exc:
                entry["marker_write_failed"] = (
                    f"{type(exc).__name__}: {exc}")[:300]
    _record_compile(manifest, entry)
    return False


RENDER_TIMEOUT = 600


def _record_render(manifest, entry):
    """Best-effort manifest record: the render outcome must be
    recorded whenever the manifest is the dict _execute_body built,
    and a malformed manifest must still never raise into the publish
    path."""
    try:
        manifest["render"] = entry
    except Exception:  # noqa: BLE001 - recording must never raise
        print(f"maybe_render: manifest not writable, outcome: "
              f"{entry}", flush=True)


def _append_sweep_files(sweep_dir, entries):
    """Append (path, bytes, sha256) entries to the sweep dir's
    manifest.json files[], replacing any same-path entry, so the
    listing stays truthful (same shape archive.py writes). Returns
    True on success, False otherwise; never raises. Issue #256:
    the update is a same-directory temp write + atomic os.replace
    (mirroring _write_manifest_atomic), then the file on disk is
    re-read and the appended entries re-validated (path, bytes,
    sha256) before True is returned — a failed or partial write
    leaves the previous valid index in place, never a truncated
    one; a validation failure restores the previous bytes the
    same way. The temp file is removed on every handled failure
    path so it never rides publish()'s wholesale _merge_out copy.
    The twins ride publish() through the wholesale _merge_out
    copy either way — this only keeps the manifest's index honest."""
    mpath = sweep_dir / "manifest.json"
    tmp = sweep_dir / ".manifest.json.tmp"
    try:
        original = mpath.read_bytes()
        m = json.loads(original.decode("utf-8"))
        files = m.get("files")
        if not isinstance(files, list):
            return False
        for e in entries:
            files[:] = [f for f in files
                        if not (isinstance(f, dict)
                                and f.get("path") == e["path"])]
            files.append(e)
        new_bytes = (json.dumps(m, indent=2) + "\n").encode("utf-8")
        with open(tmp, "wb") as handle:
            handle.write(new_bytes)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, mpath)
        _fsync_dir(sweep_dir)
    except Exception:  # noqa: BLE001 - index append is best-effort
        try:
            if tmp.is_file():
                os.remove(tmp)
        except OSError:
            pass
        return False
    # Validate what actually landed on disk BEFORE reporting
    # success: the index must parse and every appended entry must
    # be present with matching bytes and sha256. On failure the
    # previous valid index is restored atomically (best effort).
    try:
        landed = json.loads(mpath.read_text(encoding="utf-8"))
        landed_files = landed.get("files")
        if not isinstance(landed_files, list):
            raise ValueError("landed manifest has no files[] list")
        by_path = {f.get("path"): f for f in landed_files
                   if isinstance(f, dict)}
        for e in entries:
            got = by_path.get(e["path"])
            if not isinstance(got, dict) \
                    or got.get("bytes") != e["bytes"] \
                    or got.get("sha256") != e["sha256"]:
                raise ValueError(
                    "landed index missing/corrupt entry "
                    f"{e['path']!r}")
    except Exception:  # noqa: BLE001 - restore the valid index
        try:
            with open(tmp, "wb") as handle:
                handle.write(original)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, mpath)
            _fsync_dir(sweep_dir)
        except OSError:
            pass
        return False
    return True


def maybe_render(job, workdir, manifest, plan):
    """Issue #69: post-compile report render hook. Runs
    scripts/render.py on the just-compiled model
    (workdir/_merge_out/<sweep_dir>/report-model.json) after
    maybe_compile succeeds and before the second
    _write_manifest_atomic / publish, so report.html + report.md
    ride the SAME archive commit as fleet + merge + model, atomic
    with their sweep (#69 D-6). Mirrors maybe_compile: fires only
    for sweep / sweep-lite plans; a render refusal or crash never
    loses the fleet — it writes render_error.txt, records
    manifest["render"], and returns False so _execute still
    publishes. The whole body is guarded: a malformed manifest or
    a dead renderer ends in a recorded "error", never an exception
    into _execute_body. Every non-rendered outcome is fail-closed:
    with a writable sweep dir, surviving report.html / report.md
    are removed and render_error.txt names the CURRENT cause. If
    the twins can neither be removed (read-only tree), the hook
    records cleanup_failed + a suppress_render list and publish()
    excludes those exact files (validated pathlib removal,
    publish refused on failure) — an unvalidated report never
    publishes. I-5 fallback: the renderer gets --sweep-dir (the
    merged sweep dir itself), so it reads per-tool report.md
    contents and the price/Kronos chart CSVs from the sweep dir —
    the live model carries no IR-1/IR-3 chart fields, so without
    the fallback the chart degrades to a table and the per-tool
    sections lose their reports. The fallback never fakes a chart:
    with no chart CSVs the renderer renders the price-series
    table instead. When reaction_profile.present is true the
    profile file CODE/profiles/<TICKER>.json is passed --profile
    (the renderer asserts built_at matches the model); a missing
    or mismatched profile fails the render, never a silent skip.
    Validation scope: exit 0 plus both twins present, non-empty,
    the HTML carrying the model data island, and byte equality
    against the first read (single-writer invariant). Semantic
    correctness is the renderer's own contract (prose-audit,
    schema refusal, i18n parity), trusted here because the pinned
    renderer itself produced the twins — the harness verifies
    bands, chart mode and twin SHAs behaviorally on the golden
    sweep rather than the hook re-deriving them. Issue #256: the
    sweep-index append is atomic + re-validated, and an append
    failure is an "error" (twins removed, marker written) — never
    a "rendered" beside an index that does not list the twins."""
    sweep_dir = None
    sweep_rel = None
    status, detail = "error", "render hook aborted before running"
    try:
        kind = job_text(job).split()  # Issue #381: isinstance normalization, not `or ""`
        if not kind or kind[0] not in ("sweep", "sweep-lite") or not plan:
            return False
        compile_info = manifest.get("compile")
        if not isinstance(compile_info, dict):
            compile_info = {}
        compile_status = compile_info.get("status")
        sweep_rel = compile_info.get("sweep_dir")
        # Gate on a COMPILED model: the renderer consumes the model
        # and nothing else for numbers, so without one there is
        # nothing to render. A refused/error compile records a
        # skipped render (with the sweep_dir, so publish() can still
        # drop stale twins at that path) — never a crash, never a
        # render from raw sweep files.
        if compile_status != "compiled":
            _record_render(manifest, {
                "status": "skipped",
                "detail": ("no compiled model to render (compile "
                           f"status: {compile_status})"),
                **({"sweep_dir": sweep_rel}
                   if isinstance(sweep_rel, str) and sweep_rel else {}),
            })
            return False
        if not isinstance(sweep_rel, str) or not sweep_rel.strip():
            _record_render(manifest, {
                "status": "error",
                "detail": "compiled model without a sweep_dir"})
            return False
        if os.path.isabs(sweep_rel):
            _record_render(manifest, {
                "status": "error",
                "detail": (f"absolute sweep_dir from compile: "
                           f"{sweep_rel!r}")[:500]})
            return False
        base = (Path(workdir) / "_merge_out").resolve()
        sweep_dir = (base / sweep_rel).resolve()
        if base not in sweep_dir.parents:
            _record_render(manifest, {
                "status": "error",
                "detail": (f"sweep_dir escapes _merge_out: "
                           f"{sweep_rel!r}")[:500]})
            return False
        if not sweep_dir.is_dir():
            _record_render(manifest, {
                "status": "error",
                "detail": (f"merged sweep dir missing on disk: "
                           f"{sweep_rel}")[:500]})
            return False
        model_path = sweep_dir / "report-model.json"
        if not model_path.is_file():
            detail = ("compiled model missing on disk: "
                      f"{sweep_rel}/report-model.json")
            status = "error"
        else:
            blob = model_path.read_bytes()
            try:
                model = json.loads(blob.decode("utf-8"))
            except Exception as e:
                model = None
                detail = f"compiled model unreadable: {e}"
                status = "error"
            if model is not None:
                ticker = model.get("ticker") or ""
                if not re.fullmatch(r"[A-Za-z0-9.\-]{1,32}", ticker or ""):
                    detail = f"model ticker not a safe profile name: {ticker!r}"
                    status = "error"
                else:
                    render_script = CODE / "scripts" / "render.py"
                    env = {k: v for k, v in os.environ.items()
                           if k not in ENV_DENY_FOR_TOOLS}
                    _assert_no_denied(env)
                    cmd = [sys.executable, str(render_script),
                           str(model_path),
                           "--sweep-dir", str(sweep_dir),
                           "--out-dir", str(sweep_dir)]
                    rp = model.get("reaction_profile") or {}
                    if rp.get("present"):
                        cmd += ["--profile", str(
                            CODE / "profiles" / f"{ticker}.json")]
                    proc = subprocess.run(
                        cmd, env=env, capture_output=True, text=True,
                        timeout=RENDER_TIMEOUT)
                    if proc.stdout.strip():
                        print(proc.stdout, end="", flush=True)
                    if proc.stderr.strip():
                        print(proc.stderr, end="", file=sys.stderr,
                              flush=True)
                    html_path = sweep_dir / "report.html"
                    md_path = sweep_dir / "report.md"
                    if proc.returncode == 0 and html_path.is_file() \
                            and md_path.is_file():
                        html_blob = html_path.read_bytes()
                        md_blob = md_path.read_bytes()
                        if not html_blob or not md_blob:
                            detail = ("render wrote an empty twin: "
                                      f"html {len(html_blob)} bytes, "
                                      f"md {len(md_blob)} bytes")
                        elif b'id="report-model"' not in html_blob:
                            detail = ("report.html carries no model "
                                      "data island")
                        elif (html_path.read_bytes() != html_blob
                              or md_path.read_bytes() != md_blob):
                            detail = ("report twins changed during "
                                      "validation")
                        else:
                            # Issue #258: the chart flag separates
                            # history from forecast — a forecast-only
                            # SVG records "svg-forecast-only", never
                            # "svg", so a monitoring check on
                            # chart=svg cannot mistake it for a real
                            # price chart.
                            chart = ("svg-forecast-only"
                                     if b'aria-label="Price chart '
                                        b'(forecast only)"' in html_blob
                                     else "svg"
                                     if b'aria-label="Price chart"'
                                     in html_blob else "table")
                            files = [
                                {"path": "report.html",
                                 "bytes": len(html_blob),
                                 "sha256": hashlib.sha256(
                                     html_blob).hexdigest()},
                                {"path": "report.md",
                                 "bytes": len(md_blob),
                                 "sha256": hashlib.sha256(
                                     md_blob).hexdigest()},
                            ]
                            appended = _append_sweep_files(
                                sweep_dir, files)
                            if not appended:
                                # Issue #256: the sweep index could
                                # not be updated and validated — never
                                # record "rendered" with an index that
                                # does not list the twins. Fall through
                                # to the fail-closed tail: twins
                                # removed, marker written, status
                                # "error" recorded.
                                detail = ("sweep index append failed "
                                          "(manifest.json not updated "
                                          "or not validated)")
                                status = "error"
                            else:
                                _record_render(manifest, {
                                    "status": "rendered",
                                    "sweep_dir": sweep_rel,
                                    "files": files,
                                    "files_appended": appended,
                                    "chart": chart,
                                    "sweep_dir_fallback": True,
                                    "ticker": ticker,
                                })
                                return True
                    elif proc.returncode == 0:
                        detail = ("render exited 0 but report.html / "
                                  "report.md missing")
                    elif proc.returncode == 2:
                        status = "refused"
                        detail = ("render.py refused (exit 2): "
                                  + (proc.stderr.strip()
                                     or proc.stdout.strip()))
                    else:
                        detail = (f"render.py exited {proc.returncode}: "
                                  f"{proc.stderr.strip()}")
    except subprocess.TimeoutExpired:
        status = "error"
        detail = f"render timed out after {RENDER_TIMEOUT}s"
    except Exception as e:  # noqa: BLE001 - the fleet must publish
        status = "error"
        detail = f"render hook failed: {type(e).__name__}: {e}"
    # Fail-closed tail for every non-rendered outcome: never leave
    # report twins in place that this run did not validate, and
    # make render_error.txt name the CURRENT cause.
    entry = {"status": status, "detail": detail[:500]}
    if isinstance(sweep_rel, str) and sweep_rel:
        entry["sweep_dir"] = sweep_rel
        entry["error_file"] = f"{sweep_rel}/render_error.txt"
    if sweep_dir is not None:
        stale = []
        for twin in ("report.html", "report.md"):
            p = sweep_dir / twin
            if p.is_file():
                try:
                    os.remove(p)
                except OSError as exc:
                    stale.append(twin)
                    entry["cleanup_failed"] = (
                        f"{type(exc).__name__}: {exc}")[:300]
        if stale:
            entry["suppress_render"] = [
                f"{sweep_rel}/{t}" for t in ("report.html", "report.md")]
        marker = sweep_dir / "render_error.txt"
        try:
            # Issue #258: explicit UTF-8 — the old locale-default
            # write raised UnicodeEncodeError on a non-UTF-8 host
            # locale + non-ASCII detail, and that exception escaped
            # maybe_render (the tail sits outside the generic
            # except above) so publish() never ran. Any marker-write
            # failure is recorded as evidence and the fleet still
            # publishes; it can never skip publish().
            marker.write_text(f"render {status}: {detail}\n",
                              encoding="utf-8")
        except Exception as exc:  # noqa: BLE001 - marker is evidence
            entry["marker_write_failed"] = (
                f"{type(exc).__name__}: {exc}")[:300]
    _record_render(manifest, entry)
    return False


def _execute(job):
    # #231: an intent precedes ALL effects, including ledger publish.
    # Never clear it just because the body returned/raised: failures
    # can follow partial effects. Only verified completion clears it.
    if _begin_execution(job):
        return _execute_body(job)


def _record_publish_failure(job):
    """Publish failures must be observable on the bus, not just
    local (shared by the harvest and top30 branches)."""
    try:
        err = BUS / "queue" / "claims" / f"{job['id']}.error.json"
        err.write_text(json.dumps(
            {"worker": os.uname().nodename, "at": now(),
             "error": "publish failed"}))
        push_bus(f"publish failed {job['id']}")
    except Exception:
        pass


# --- incomplete gdelt-fetch jobs: yield the lane when stuck -----------
# An incomplete job keeps its queue position, so main() would re-select
# it first every cycle and break after one job. Mechanism: DEFERRAL keyed
# on PROGRESS. After each incomplete run the worker records the cumulative
# done-file count (files_done + macro_files_done from the run's sidecar). A
# run whose count did not exceed the previous recorded count is a stall;
# GDELT_STALL_LIMIT consecutive stalls defer the job for GDELT_DEFER_SECONDS,
# during which main() skips it (no claim) so later jobs run. A run that
# advances the count resets the stalls, so a budget-limited chunk that
# keeps processing files is never demoted. After the deferral expires the
# job gets one retry; a further stall defers it again. Local state (per
# worker host), under JOB_STATE/gdelt-progress; failures to read or write
# it fail OPEN (no deferral).
GDELT_STALL_LIMIT = 3
GDELT_DEFER_SECONDS = 6 * 3600


def _gdelt_progress_path(job_id):
    return JOB_STATE / "gdelt-progress" / f"{job_id}.json"


def _gdelt_progress_read(job_id):
    try:
        d = json.loads(_gdelt_progress_path(job_id).read_text())
        return d if isinstance(d, dict) else None
    except Exception:
        return None


def _gdelt_note_incomplete(job_id, total, now_ts=None):
    """Record one incomplete run; returns the stored record or None."""
    now_ts = time.time() if now_ts is None else now_ts
    try:
        prev = _gdelt_progress_read(job_id) or {}
        prev_total = prev.get("total")
        progressed = (total > 0) if prev_total is None else (total > prev_total)
        stalls = 0 if progressed else int(prev.get("stalls", 0)) + 1
        # The stored total never goes DOWN: a run that reports fewer
        # files (for example a failure path) must not lower the bar and
        # make the next unchanged run look like progress.
        rec = {"total": max(int(prev_total or 0), int(total)),
               "stalls": stalls, "deferred_until": 0}
        if stalls >= GDELT_STALL_LIMIT:
            rec["deferred_until"] = now_ts + GDELT_DEFER_SECONDS
        path = _gdelt_progress_path(job_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(rec))
        os.replace(tmp, path)
        return rec
    except Exception:
        return None


def _gdelt_deferred(job_id, now_ts=None):
    now_ts = time.time() if now_ts is None else now_ts
    rec = _gdelt_progress_read(job_id)
    if not rec:
        return False
    try:
        until = float(rec.get("deferred_until", 0) or 0)
    except (TypeError, ValueError, OverflowError):
        return False  # unreadable deadline: fail open, like missing or invalid JSON
    if not math.isfinite(until):
        return False  # an infinite deadline would defer the job forever
    return until > now_ts


def _gdelt_quarantine_checkpoint(job_id, workdir):
    """After checkpoint-io-failed the local state/out pair is NOT safe to
    reuse (complete match rows can sit beside a done.txt that lacks their
    file, so a retry would archive duplicates). Move the pair aside, outside
    workdir (publish() never carries it), and CONFIRM both fixed directories
    are gone: the next admitted attempt then restores the newest PUBLISHED
    snapshot from the archive, or starts from a clean empty pair when none is
    published. Returns True only when the confirmation holds."""
    wd = Path(workdir)
    try:
        qdir = JOB_STATE / "gdelt-quarantine" / ("%s-%d" % (job_id, int(time.time() * 1000)))
        qdir.mkdir(parents=True, exist_ok=True)
        for name in ("gdelt-state", "gdelt-out"):
            if (wd / name).exists():
                os.rename(wd / name, qdir / name)
        _fsync_dir(wd)
        _fsync_dir(qdir)
        return not (wd / "gdelt-state").exists() and not (wd / "gdelt-out").exists()
    except OSError:
        return False


def _gdelt_cleanup_marker(job_id):
    return JOB_STATE / "gdelt-intent-cleanup" / f"{job_id}.json"


def _gdelt_intent_identity(job_id):
    """Identity of the write-ahead intent currently on disk (sha256 of its
    bytes: it carries the job text and the attempt's start time), or None
    when there is no intent."""
    try:
        return hashlib.sha256(_intent_path(job_id).read_bytes()).hexdigest()
    except OSError:
        return None


def _gdelt_release_intent(job_id, archive_sha=None, expect=None):
    """Remove the write-ahead intent of an incomplete (already published)
    gdelt-fetch run and CONFIRM it is gone. On failure after retries a
    cleanup marker records the verified publication so the cleanup can be
    retried without rerunning the fetch; returns False then."""
    ident = _gdelt_intent_identity(job_id)
    if expect is not None and ident != expect and (
            ident is not None or _intent_path(job_id).exists()):
        # ident None while the intent file still exists means it is
        # unreadable: treat it like a mismatch, never unlink it.
        # A later attempt's intent: the marker is stale. Leave the intent
        # alone and drop only the marker.
        try:
            _gdelt_cleanup_marker(job_id).unlink(missing_ok=True)
        except OSError:
            pass
        return True
    for attempt in range(3):
        try:
            _intent_path(job_id).unlink(missing_ok=True)
            if JOB_STATE.exists():
                _fsync_dir(JOB_STATE)
        except OSError:
            time.sleep(0.05)
            continue
        if not _intent_path(job_id).exists():
            try:
                _gdelt_cleanup_marker(job_id).unlink(missing_ok=True)
            except OSError:
                pass
            return True
    try:
        mp = _gdelt_cleanup_marker(job_id)
        mp.parent.mkdir(parents=True, exist_ok=True)
        mp.write_text(json.dumps({"archive_sha": archive_sha,
                                 "intent": ident,
                                 "claim_attempt": _local_claim_attempt(job_id)}))
    except OSError:
        pass
    return False


def _strip_restore_stages(dest):
    """959n F6: remove abandoned .gdelt-restore-* stages under dest. The one
    exclusion publish() uses (the test drives this same helper). Returns the
    shell return code."""
    return sh(f"find {dest} -name '.gdelt-restore-*' -prune -exec rm -rf {{}} +",
              timeout=60).returncode


def _gdelt_total_done(gf):
    """files_done + macro + absent + transient from a gdelt_fetch summary
    (0 when missing or malformed)."""
    gf = gf or {}
    try:
        return (int(gf.get("files_done", 0))
                + int(gf.get("macro_files_done", 0))
                + int(gf.get("absent_files", 0))
                + int(gf.get("transient_files", 0)))
    except (TypeError, ValueError, AttributeError):
        return 0


def _gdelt_retry_cleanup(job_id):
    """Retry a recorded intent cleanup (see _gdelt_release_intent). Once the
    replayed intent is gone, release the bus claim THIS host placed; the
    marker stays (as claim_pending) until that release is confirmed."""
    try:
        mp = _gdelt_cleanup_marker(job_id)
        if mp.exists():
            try:
                data = json.loads(mp.read_text())
                expect = data.get("intent")
            except (ValueError, AttributeError):
                data, expect = {}, None
            if data.get("claim_pending") is True:
                if not isinstance(data.get("claim_attempt"), str) \
                        or not data.get("claim_attempt"):
                    # 959n F14: missing/null/non-string/empty attempt = no
                    # identity: it cannot be bound to a claim, so never
                    # release one. Drop the marker.
                    mp.unlink(missing_ok=True)
                    return
                if _release_claim(job_id, only_own=True,
                                  expect_attempt=data.get("claim_attempt")):
                    mp.unlink(missing_ok=True)
                return
            if not isinstance(expect, str):
                # No recorded identity: it cannot be bound to an intent, so
                # never unlink one. Drop the unusable marker.
                mp.unlink(missing_ok=True)
                return
            if _gdelt_release_intent(job_id, expect=expect) \
                    and not _intent_path(job_id).exists():
                # Our intent is gone (not a mismatch that left a later
                # attempt's intent in place): release the claim.
                att = data.get("claim_attempt")
                if not _release_claim(job_id, only_own=True, expect_attempt=att):
                    mp.parent.mkdir(parents=True, exist_ok=True)
                    mp.write_text(json.dumps({"claim_pending": True,
                                              "claim_attempt": att}))
    except OSError:
        pass


def _gdelt_progress_clear(job_id):
    try:
        _gdelt_progress_path(job_id).unlink(missing_ok=True)
    except OSError:
        pass


def _execute_body(job):
    # Issue #381: normalize the untrusted `job` field ONCE, here,
    # before any dispatch, parse, or publish call below. `text` is
    # the string every .split()/== below uses; the raw queued value
    # stays in manifest["job"] as evidence. None becomes "" (an
    # empty job string, failed closed by the #371 branch below);
    # any other non-string type is rejected explicitly with its own
    # named failure — never an exception after intent persistence.
    raw_job = job.get("job") if isinstance(job, dict) else None
    text = raw_job if isinstance(raw_job, str) else ""
    invalid_job_type = raw_job is not None \
        and not isinstance(raw_job, str)
    # Issue #66 extension: first-party schedule jobs — no tools, no
    # archive publish; their outputs are ledger commits on main and
    # bus markers. Done is marked only when the effect is confirmed
    # (issue #434): run_ledger_guard returns True only when its
    # heartbeat commit is verified on main, run_ledger_watchdog
    # only when its signal decision reached the bus — a failed
    # delivery leaves the slot un-done instead of silently done.
    if text == "ledger-guard":
        if run_ledger_guard(job):
            # Issue #216: failure handling is centralized in
            # _mark_done (outbox retention, per-cycle drain,
            # heartbeat surfacing, local re-execution gate); callers
            # deliberately do not branch on its return.
            _mark_done(job, "ledger-guard")
        return
    if text == "ledger-watchdog":
        if run_ledger_watchdog(job):
            _mark_done(job, "ledger-watchdog")  # centralized #216 handling
        return
    reg = registry()
    workdir = OUT / job["id"]
    workdir.mkdir(parents=True, exist_ok=True)
    manifest = {"job": job, "worker": os.uname().nodename,
                "started": now(), "tools": {},
                # Issue #371: pin the running code SHA on EVERY run
                # manifest (same name/kind as the heartbeat) so the
                # exact code behind a run — including a no-op — is
                # proven from the archive alone.
                "code_sha": running_code_sha(),
                "code_sha_kind": "sha256-running-bytes",
                # Issue #382 (INS-373-374 F4): record the checkout
                # HEAD + update branch alongside the running-code
                # pin, mirroring the heartbeat fields. These are
                # DIAGNOSTICS only — checkout_sha is the release
                # checkout's HEAD, not proof of the running code
                # (it lies after a failed adopt, issue #160);
                # code_sha remains the running-code pin.
                "checkout_sha": update_checkout_sha(),
                "update_branch": UPDATE_BRANCH}
    if invalid_job_type:
        # Issue #381: a non-string `job` field (int, list, dict,
        # bool — anything but a string or None) is rejected
        # explicitly with its own named failure. None normalizes
        # to "" above and lands in the #371 unknown-job branch;
        # other types never reach a parser: the raw value stays
        # recorded in manifest["job"] as evidence, the run is
        # published + marked done-with-failure (same "done means
        # executed + archived" precedent as the unknown-job
        # branch), and no AttributeError escapes after intent
        # persistence. Only a failed publish leaves the job
        # unmarked.
        manifest["tools"] = {"invalid-job-type": "invalid-job-type"}
        manifest["finished"] = now()
        archive_sha = publish(job, workdir, manifest)
        if not archive_sha:
            _record_publish_failure(job)
        else:
            # Issue #149: only a successful publish marks the job
            # done. Issue #216: failure handling is centralized in
            # _mark_done.
            _mark_done(job, archive_sha)
        return
    # Issue #348: tokenize on whitespace exactly like the #346 F9
    # fix did for top30-enumerate (and like run_harvest's own
    # .split()), so a leading-space harvest job dispatches here
    # instead of falling through to parse_job (which returns []
    # and — since #371 — fails closed with a named unknown-job
    # failure instead of publishing an empty run as done).
    if text.split()[:1] == ["harvest-egx"]:
        manifest["tools"] = run_harvest(job, workdir)
        manifest["finished"] = now()
        archive_sha = publish(job, workdir, manifest)
        if not archive_sha:
            try:
                err = BUS / "queue" / "claims" / f"{job['id']}.error.json"
                err.write_text(json.dumps(
                    {"worker": os.uname().nodename, "at": now(),
                     "error": "publish failed"}))
                push_bus(f"publish failed {job['id']}")
            except Exception:
                pass
        else:
            # Issue #149: only a successful publish marks the job done.
            # Issue #216: failure handling is centralized in _mark_done.
            _mark_done(job, archive_sha)
        return
    # Issue #346 F9: tokenize on whitespace exactly like
    # parse_top30_job does (.split()), so a leading-space job
    # dispatches here instead of falling through to parse_job
    # (which returns [] and — since #371 — fails closed with a
    # named unknown-job failure instead of publishing an empty
    # run as done).
    if text.split()[:1] == ["top30-enumerate"]:
        # Issue #328: the registry grammar has no enumeration tool
        # (parse_job returns []), so this kind dispatches here like
        # harvest-egx — never through the tool loop. A bad job
        # string still publishes its named failure and marks done
        # (done means executed + archived, as for harvest-egx);
        # only a failed publish leaves the job unmarked.
        manifest["tools"] = run_top30_enumerate(job, workdir)
        manifest["finished"] = now()
        archive_sha = publish(job, workdir, manifest)
        if not archive_sha:
            _record_publish_failure(job)
        else:
            # Issue #149: only a successful publish marks the job done.
            _mark_done(job, archive_sha)
        return
    # Issue #446: walk-forward backtest cells (design #436 §6.4) —
    # same dispatch shape as diag-egx-ab above (before parse_job;
    # the registry has no backtest tool). The two-token prefix
    # keeps the registry grammar's `run <tool> <ticker>` jobs
    # untouched. A bad job string still publishes its named failure
    # and marks done (done means executed + archived, as for
    # diag-egx-ab); only a failed publish leaves the job unmarked.
    if text.split()[:2] == ["run", "backtest"]:
        manifest["tools"] = run_backtest(job, workdir)
        manifest["finished"] = now()
        archive_sha = publish(job, workdir, manifest)
        if not archive_sha:
            _record_publish_failure(job)
        else:
            # Issue #149: only a successful publish marks the job done.
            _mark_done(job, archive_sha)
        return
    # gdelt-fetch: GDELT GKG master download + filter
    if text.split()[:1] == ["gdelt-fetch"]:
        manifest["tools"] = run_gdelt_fetch(job, workdir)
        if manifest["tools"].get("gdelt-fetch") in GDELT_NO_PUBLISH:
            # Unknown resume state (archive lookup failed, or a restore
            # could not be rolled back): publish NOTHING (a stale or
            # inconsistent checkpoint must not become the newest run),
            # release the intent, and let execute() release the claim.
            # Record a stall (total 0: the stored progress never goes down,
            # the first retry stays eligible) so a PERSISTENT failure is
            # deferred instead of re-selected at the head of the bulk lane.
            _gdelt_note_incomplete(job["id"], 0)
            if manifest["tools"].get("gdelt-fetch") == "checkpoint-io-failed" \
                    and not _gdelt_quarantine_checkpoint(job["id"], workdir):
                # The unsafe local pair could not be set aside and confirmed
                # gone: do NOT admit a retry that would reuse it. The intent
                # stays, so the job is held on this host for resolution.
                return None
            if _gdelt_release_intent(job["id"]):
                return "incomplete"
            return None
        # Load gdelt_fetch summary from sidecar written by runner
        gf_path = Path(workdir) / "gdelt" / "gdelt_fetch.json"
        if gf_path.exists():
            try:
                manifest["gdelt_fetch"] = json.loads(gf_path.read_text())
            except Exception:
                manifest["gdelt_fetch"] = {}
        manifest["finished"] = now()
        archive_sha = publish(job, workdir, manifest)
        if not archive_sha:
            _record_publish_failure(job)
            if manifest["tools"].get("gdelt-fetch") in GDELT_INCOMPLETE:
                # 959n F15: record the stall here too (like the no-publish
                # and published-incomplete paths) so GDELT_STALL_LIMIT
                # deferral can engage.
                _gdelt_note_incomplete(
                    job["id"], _gdelt_total_done(manifest.get("gdelt_fetch")))
                # 959m F12: an incomplete gdelt-fetch chunk is resumable by
                # design. An unconfirmed push is not proof nothing landed, so
                # make the chunk resumable instead of leaving the job gated:
                # release the intent (and, via "incomplete", the claim) so a
                # same-id retry restores from the last VERIFIED published
                # checkpoint (or finds the snapshot if it did land).
                if _gdelt_release_intent(job["id"]):
                    return "incomplete"
                return None
        elif manifest["tools"].get("gdelt-fetch") in GDELT_INCOMPLETE:
            # Fetch progress is not queue completion: a budget-limited
            # or timed-out run is archived (its gdelt-state is the
            # resume point) but is NOT marked done, and its write-ahead
            # intent is released so a same-id re-queue is admitted and
            # resumes from this published run.
            released = _gdelt_release_intent(job["id"], archive_sha)
            total = _gdelt_total_done(manifest.get("gdelt_fetch"))
            _gdelt_note_incomplete(job["id"], total)
            if not released:
                # The intent could not be removed: the claim is NOT released
                # (the job would stay blocked on this host). A cleanup marker
                # is retried by _done_or_pending without rerunning the fetch.
                return None
            # Tell execute() to release the bus claim once its refresh
            # thread is stopped (see execute()).
            return "incomplete"
        else:
            # Issue #149: only a successful publish marks the job done.
            _mark_done(job, archive_sha)
            _gdelt_progress_clear(job["id"])
        return
    # Issue #283: paired A/B EGX probe — same dispatch shape as
    # top30-enumerate above (before parse_job; the registry has no
    # diag tool). A bad job string still publishes its named failure
    # and marks done (done means executed + archived, as for
    # harvest-egx); only a failed publish leaves the job unmarked.
    if text.split()[:1] == ["diag-egx-ab"]:
        manifest["tools"] = run_diag_egx_ab(job, workdir)
        manifest["finished"] = now()
        archive_sha = publish(job, workdir, manifest)
        if not archive_sha:
            _record_publish_failure(job)
        else:
            # Issue #149: only a successful publish marks the job done.
            _mark_done(job, archive_sha)
        return
    plan = parse_job(text, reg)
    if not plan:
        # Issue #371 (INS-HARV-003 finding 3): an empty plan fails
        # closed — never an empty run published as done. A job
        # string parse_job cannot place (e.g. `harvest-egx-poul`,
        # a typo'd `top30-enumerate-typo`, an unknown sweep filter,
        # an empty string) used to fall through the tool loop with
        # no tools and publish `tools: {}` as a success. Record a
        # named `unknown-job` failure instead: the bad job string
        # stays recorded in manifest["job"], and the run is
        # published + marked done-with-failure — "done means
        # executed + archived", the exact precedent of the
        # harvest-egx bad-code, top30-enumerate bad-job and
        # diag-egx-ab bad-job branches (issue #216 central handling
        # in _mark_done; no new marking channel, no error file —
        # the failure lives in the published manifest, as for those
        # siblings). Only a failed publish leaves the job unmarked.
        # Issue #381: `unknown-job` is ONE umbrella status over
        # distinct causes — unknown syntax (a string parse_job
        # cannot place, e.g. `harvest-egx-poul`) and invalid/empty
        # selection (a well-formed `sweep-lite POUL.CA market=XX`
        # whose filters deliberately reject it). The manifest keeps
        # the single status (test_worker_371 pins it) and records
        # the cause beside it, so the two are distinguished in the
        # record instead of conflated: see classify_empty_plan.
        manifest["tools"] = {"unknown-job": "unknown-job"}
        manifest["unknown_job_cause"] = classify_empty_plan(text)
        manifest["finished"] = now()
        archive_sha = publish(job, workdir, manifest)
        if not archive_sha:
            _record_publish_failure(job)
        else:
            # Issue #149: only a successful publish marks the job
            # done. Issue #216: failure handling is centralized in
            # _mark_done.
            _mark_done(job, archive_sha)
        return
    templates = {t["id"]: t["command"] for t in reg["tools"]}
    # D2: each tool runs only at its registry-pinned SHA.
    refs = {t["id"]: t.get("ref") for t in reg["tools"]}
    repos = {t["id"]: t.get("repo", f"{t['id']}-runner")
             for t in reg["tools"]}
    # Issue #278 phase 1: pre-sweep refresh of the official EGX
    # disclosure feed (POUL/COMI) — before any tool runs, so the
    # news-disclosure tool serves the just-refreshed harvest.
    refresh_disclosure_feed(job, workdir, manifest, plan)
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
    # Issue #278 phase 2: extraction BEFORE the ensemble
    # (maybe_merge) — events from this sweep's refresh, under this
    # sweep's id; a failed/stale feed is recorded, never silent.
    extract_disclosure_events(job, workdir, manifest, plan)
    # Issue #148: merge.py requires manifest.json in the run dir,
    # and publish() writes it only into the archive dest — so a
    # fresh worker sweep's merge always refused ("no manifest.json
    # in run dir"). Write the current run manifest into the workdir
    # before the merge hook reads it.
    _write_manifest_atomic(workdir, manifest)
    # Issue #67: post-sweep merge hook — fleet + merge publish in
    # one commit. A merge failure never loses the fleet (see
    # maybe_merge): publish() below still runs.
    maybe_merge(job, workdir, manifest, plan)
    # Issue #68: post-merge Report Model compile hook — the compiled
    # model (or its fail-loudly refusal marker) rides the SAME
    # archive commit as fleet + merge. A compile refusal or crash
    # never loses the fleet (see maybe_compile): publish() below
    # still runs.
    maybe_compile(job, workdir, manifest, plan)
    # Issue #69: post-compile report render hook — the rendered
    # report.html + report.md (or the render refusal marker) ride
    # the SAME archive commit as fleet + merge + model. A render
    # refusal or crash never loses the fleet (see maybe_render):
    # publish() below still runs.
    maybe_render(job, workdir, manifest, plan)
    # The merge and compile hooks record their outcomes in the
    # in-memory manifest; refresh the workdir copy so it stays
    # truthful (publish() writes the same final manifest into the
    # archive dest).
    _write_manifest_atomic(workdir, manifest)
    archive_sha = publish(job, workdir, manifest)
    if not archive_sha:
        # Failures must be observable on the bus, not just local.
        try:
            err = BUS / "queue" / "claims" / f"{job['id']}.error.json"
            err.write_text(json.dumps(
                {"worker": os.uname().nodename, "at": now(),
                 "error": "publish failed"}))
            push_bus(f"publish failed {job['id']}")
        except Exception:
            pass
    else:
        # Issue #149: only a successful publish marks the job done.
        # Issue #216: failure handling is centralized in _mark_done.
        _mark_done(job, archive_sha)


GDELT_QUARANTINE_KEEP_DAYS = 7     # retention: age limit ...
GDELT_QUARANTINE_KEEP_MAX = 10     # ... and count limit (newest kept)


def prune_gdelt_quarantine():
    """Bound JOB_STATE/gdelt-quarantine: drop entries older than the age
    limit, then everything beyond the newest KEEP_MAX."""
    qroot = JOB_STATE / "gdelt-quarantine"
    try:
        items = sorted((d for d in qroot.iterdir() if d.is_dir()),
                       key=lambda d: d.stat().st_mtime, reverse=True)
    except OSError:
        return
    cutoff = time.time() - GDELT_QUARANTINE_KEEP_DAYS * 86400
    for k, d in enumerate(items):
        try:
            if k >= GDELT_QUARANTINE_KEEP_MAX or d.stat().st_mtime < cutoff:
                shutil.rmtree(d, ignore_errors=True)
        except OSError:
            pass


def prune_out():
    prune_gdelt_quarantine()
    cutoff = time.time() - OUT_RETENTION_DAYS * 86400
    for d in OUT.iterdir() if OUT.exists() else []:
        if d.is_dir() and d.stat().st_mtime < cutoff:
            sh(f"rm -rf {d}", timeout=120)


def reclaim_stale_claims():
    """A claim whose push succeeded but whose result never published
    (worker died mid-job) must not block the job forever.
    Issue #149: only UNFINISHED attempts are reclaimed for re-run.
    A stale claim on a job with a done record is just a redundant
    file — it is removed, but the job stays done (the main loop and
    claim() both skip done jobs), so it can never execute again."""
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
            # A done job's claim is redundant once stale; an
            # unfinished attempt is reclaimed for re-run. Either way
            # the file goes — done() is what keeps a completed job
            # from executing again, not the claim.
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
    if not cur and not UPDATE_PIN:
        # CodeRabbit Major on PR #396 (issue #390 follow-up): the
        # #390 guard makes update_checkout_sha() return "" on a
        # failed lookup, so an empty cur must NOT silently skip the
        # ancestry check below — with no known running revision
        # there is nothing to prove the tip descends from, so
        # refuse adoption (fail closed) and keep running code.
        # Diagnostic call sites still degrade to "" (see
        # test_worker_390); only adoption refuses.
        # Issue #404: this refusal is gated on the UNPINNED path
        # only. A pinned adoption is trusted by configuration, not
        # by ancestry (docstring: the worker adopts a tip that is
        # a fast-forward descendant of the running checkout OR
        # exactly GATOR_PIN_SHA when set) — the pin check already
        # ran before cur was read, so a matching pin adopts even
        # when the checkout lookup fails.
        UPDATE_ERROR = ("current checkout revision unreadable; "
                        "keeping running code")
        return
    if not UPDATE_PIN and tip != cur:
        # Fast-forward only: a rewritten history is refused even if
        # the branch moved. (Needs the full clone from
        # _ensure_update_checkout — shallow history has no ancestry.)
        # Skipped on the pinned path (CodeRabbit Minor on PR #409):
        # a matching pin is trusted by configuration, not by
        # ancestry — with cur unreadable, tip != cur is still true
        # and the ancestry check would refuse the pinned update.
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
    except Exception as e:
        # Issue #160: a failed write/execv must NOT be silent. The old
        # `except Exception: pass` left UPDATE_ERROR None, so the next
        # heartbeat claimed the new SHA while this (old) process kept
        # running. Record the failure; the heartbeat carries it.
        # (os.execv never returns on success, so reaching here after a
        # successful write means the exec failed and old code runs
        # under new bytes on disk — the import-time RUNNING_CODE_SHA
        # still reports the old code, correctly.)
        UPDATE_ERROR = (f"self-update failed to adopt {tip[:12]}: "
                        f"{type(e).__name__}: {e}; running old code")


# Issue #610 item 4c: slot-bound guard/watch ids carry their slot
# time (guard-YYYY-MM-DDTHHMMZ / watch-YYYY-MM-DDTHHMMZ). A slot
# is superseded when a NEWER slot of the same kind is already
# queued or has already landed (done) — the older slot's verdict
# is stale, so executing it (~10.5 min) only delays the lane-1
# work behind it. Slot times are compared as parsed datetimes,
# never as strings alone.
_SLOT_RE = re.compile(
    r"^(guard|watch)-(\d{4})-(\d{2})-(\d{2})T(\d{2})(\d{2})Z$")
_SLOT_KIND = {"ledger-guard": "guard", "ledger-watchdog": "watch"}


def _slot_time(job_id):
    """Parse a guard-/watch- slot id to an aware UTC datetime, or
    None when the id is not a slot id or does not parse. Fail
    closed: an unparseable id is never treated as a slot."""
    m = _SLOT_RE.match(job_id) if isinstance(job_id, str) else None
    if not m:
        return None
    try:
        return datetime(int(m.group(2)), int(m.group(3)),
                        int(m.group(4)), int(m.group(5)),
                        int(m.group(6)), tzinfo=timezone.utc)
    except ValueError:
        return None


def _superseded_slot(job_id, job_text, queue_jobs, done_ids):
    """Issue #610 item 4c (T4 spec): True only for a `ledger-guard`
    job with id `guard-<slot>` or a `ledger-watchdog` job with id
    `watch-<slot>` when EITHER (a) another job of the same kind
    with a strictly LATER slot time exists in the queue list and
    is not done, OR (b) a done record exists for the same kind
    with a strictly later slot time. Returns
    (superseded, superseded_by, reason); superseded_by is the
    NEWEST later slot id found (queued or done), or None.

    NEVER superseded: the newest slot of its kind, any
    `manual-guard-*` job, any `sched-*` job, any non-slot job, or
    a job whose id does not parse as a slot time (fail closed).
    Cross-kind never supersedes: a newer guard does not supersede
    a watch, and vice versa. Pure: no I/O, no globals."""
    kind = _SLOT_KIND.get(job_text) if isinstance(job_text, str) \
        else None
    if kind is None:
        return (False, None, "")
    slot = _slot_time(job_id)
    if slot is None:
        return (False, None, "")
    done_set = set(done_ids) if done_ids else set()
    best_id = None
    best_slot = None
    for other in queue_jobs or []:
        if not isinstance(other, dict):
            continue
        other_id = other.get("id")
        if not isinstance(other_id, str) or other_id == job_id:
            continue
        if other.get("job") != job_text:
            continue  # same kind only
        if other_id in done_set:
            continue  # covered by the done-record branch below
        other_slot = _slot_time(other_id)
        if other_slot is not None and other_slot > slot and \
                (best_slot is None or other_slot > best_slot):
            best_slot, best_id = other_slot, other_id
    for done_id in done_set:
        if done_id == job_id:
            continue
        m = _SLOT_RE.match(done_id) if isinstance(done_id, str) \
            else None
        if not m or m.group(1) != kind:
            continue  # same kind only (done ids carry no job text)
        done_slot = _slot_time(done_id)
        if done_slot is not None and done_slot > slot and \
                (best_slot is None or done_slot > best_slot):
            best_slot, best_id = done_slot, done_id
    if best_id is None:
        return (False, None, "")
    return (True, best_id, f"superseded by {best_id}")


def _lane_sorted(jobs):
    """Issue #610: priority lane — slot-bound ledger guard and
    watchdog jobs claim before bulk FIFO work (sweeps, backtests),
    which otherwise delays a :47 guard slot behind hours of queue.
    Stable sort: FIFO order is preserved inside each lane."""
    def lane(job):
        if isinstance(job, dict):
            cmd = str(job.get("job") or "").split()
            if cmd and cmd[0] in ("ledger-guard", "ledger-watchdog"):
                return 0
        return 1
    return sorted(jobs, key=lane)


def main():
    RUNNERS.mkdir(parents=True, exist_ok=True)
    VENVS.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    while True:
        worked = False
        try:
            self_update()
            sync_bus()
            # Issue #216: re-publish any done receipts that a push
            # race, crash or restart left pending, before new work.
            flush_pending_done()
            # Issue #66: the worker owns the clock — check the
            # schedule every cycle, before claiming, so a due
            # firing is enqueued even on a cycle that then claims
            # an older job first.
            run_schedule_check()
            reclaim_stale_claims()
            prune_out()
            heartbeat()
            # Issue #420: validate the top-level queue before
            # iterating — a queue.json holding a scalar (42, null)
            # raised TypeError at iteration, and a string/object
            # iterated as chars/keys, quarantining one record per
            # char/key. With no schedule.json, run_schedule_check
            # returns before quarantine, so no diagnostic was
            # recorded at all. The #402 helper quarantines a
            # non-list payload as one "queue-not-a-list" record
            # and filters non-dict entries as "not-an-object" —
            # that replaces the loop's old "missing-or-invalid-id"
            # reason for non-dict entries; the #391 dict-entry
            # reasons (missing-or-invalid-id / missing-job) are
            # unchanged.
            # Issue #610 item 4c: done ids for the superseded-slot
            # check — filenames under queue/done/ after this cycle's
            # sync_bus, plus ids verified done by this process.
            # Read once per cycle; the queue list below is the same
            # snapshot the loop iterates.
            _done_dir = BUS / "queue" / "done"
            done_ids = {f.stem for f in _done_dir.glob("*.json")} \
                if _done_dir.exists() else set()
            done_ids |= _VERIFIED_DONE
            queue_jobs = _lane_sorted(
                _quarantine_non_object_entries(read_queue()))
            for job in queue_jobs:
                job_id = job.get("id") if isinstance(job, dict) else None
                if not isinstance(job_id, str) or not JOB_ID_RE.match(job_id):
                    # Issue #391: quarantine with evidence instead
                    # of the old silent skip — and a non-dict entry
                    # no longer raises AttributeError on job.get
                    # here, which aborted the whole queue loop.
                    _quarantine_malformed_job(job, "missing-or-invalid-id")
                    continue  # panel round 2: ids reach file paths
                if _done_or_pending(job_id):
                    # Issue #149: a completed job never runs again,
                    # even after its claim was reclaimed. Issue #216:
                    # any local completion evidence (valid or
                    # quarantined-corrupt receipt) also blocks
                    # re-execution on this host.
                    continue
                # Issue #610 item 4c: skip a late slot when a newer
                # slot of the same kind is queued or has landed —
                # write the done record WITHOUT claiming or
                # executing, and continue WITHOUT break, so one
                # cycle can skip many stale slots. The done record
                # makes _done_or_pending true afterwards, so the
                # skipped job is never re-executed. worked=True
                # keeps the cycle looping at once (1s sleep) so
                # the stale backlog drains fast.
                superseded, superseded_by, reason = _superseded_slot(
                    job_id, job.get("job"), queue_jobs, done_ids)
                if superseded:
                    _mark_superseded(
                        job,
                        "ledger-guard"
                        if job.get("job") == "ledger-guard"
                        else "ledger-watchdog",
                        superseded_by, reason)
                    worked = True
                    continue
                # A stuck incomplete gdelt-fetch job is deferred (see
                # _gdelt_deferred) so it cannot block later jobs. This
                # sits AFTER the supersede handling above, which is
                # unchanged, and before claiming.
                if _gdelt_deferred(job_id):
                    continue
                if not claimed(job_id):
                    if claim(job):
                        worked = True
                        execute(job)
                        break  # one job per cycle, then re-sync
        except Exception as e:  # the loop must survive anything
            print(f"worker cycle error: {type(e).__name__}: {e}",
                  file=sys.stderr, flush=True)
        # Issue #610: the poll sleep is for idle cycles only — after
        # a job, loop at once (re-sync, then claim the next job);
        # sleeping 300s after every job starved slot-bound work.
        time.sleep(POLL_SECONDS if not worked else 1)


if __name__ == "__main__":
    sys.exit(main())
