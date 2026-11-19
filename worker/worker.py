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
import json
import os
import re
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
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
    job_id = str(job.get("id", ""))
    if not JOB_ID_RE.fullmatch(job_id):
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
    return (done(job_id) or job_id in _UNDELIVERED
            or job_id in _VERIFIED_DONE
            or _intent_path(job_id).exists()
            or bool(_receipt_paths(job_id)))


def _mark_done(job, archive_sha):
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
    independent. Never turn an intent alone into a done marker."""
    record = json.dumps(
        {"worker": os.uname().nodename, "at": now(), "job": job["job"],
         "archive": archive_sha, "id": job["id"]})
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


def claim(job):
    if _done_or_pending(job["id"]):
        # Issue #149: a completed job is never claimed again.
        return False
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
# The guard job runs scripts/ledger_publish.py --commit --fail-hard
# (the exact command ledger-guard.yml runs) and then rewrites
# ledger/guard-heartbeat.json on main, exactly as the workflow does.
# The publisher needs a git checkout of MAIN with a push credential:
# the release checkout (CODE) is an anonymous, detached checkout of
# worker-release and can do neither, so the guard keeps a dedicated
# checkout (ROOT/"main-ledger") cloned from GATOR_BUS_URL — the
# worker PAT is borsagator-only Contents RW, which covers pushes to
# main. D2 guard: the worker never EXECUTES main-tip code — before
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
WATCH_SCRIPTS = ("scripts/ledger_guard_watch.py",) + GUARD_SCRIPTS
GUARD_HEARTBEAT_REL = "ledger/guard-heartbeat.json"


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


def _write_guard_heartbeat(checkout, status):
    """Rewrite ledger/guard-heartbeat.json on main and push it —
    the worker twin of ledger-guard.yml's heartbeat step. Resets to
    origin/main first so an unpushed ledger commit from a failed
    publish is never smuggled onto main by the heartbeat push.
    Non-fatal: returns True when the push landed."""
    try:
        sh(f"git -C {checkout} fetch origin main", timeout=120)
        sh(f"git -C {checkout} reset --hard origin/main", timeout=60)
        doc = {"last_run_utc": datetime.now(timezone.utc).strftime(
                   "%Y-%m-%dT%H:%M:%SZ"),
               "run_id": None,
               "status": status,
               "workflow": "ledger-guard",
               "note": "Written by every completed worker ledger-guard "
                       "run (issue #66 extension; formerly "
                       "ledger-guard.yml); the watchdog pages when "
                       "this is older than 90 minutes."}
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
            return True
        msg = f"Ledger guard heartbeat {doc['last_run_utc']} ({status})"
        if sh(f"git -C {checkout} commit -m {json.dumps(msg)}",
              timeout=60).returncode != 0:
            return False
        return sh(f"git -C {checkout} push origin HEAD:main",
                  timeout=120).returncode == 0
    except Exception as e:
        print(f"_write_guard_heartbeat: {type(e).__name__}: {e}",
              file=sys.stderr, flush=True)
        return False


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
    """Execute one `ledger-guard` job. Returns True when the guard
    attempt completed (publisher ran and the heartbeat was written,
    whatever the publisher's own verdict) — the caller then marks
    the slot done. Returns False on a setup refusal (no checkout /
    script mismatch): the slot stays un-done, the claim goes stale
    in 6 h and the job can be retried; the refusal is loud here and
    in the heartbeat file when one could be written."""
    checkout = _ensure_main_checkout()
    if checkout is None:
        print("run_ledger_guard: main checkout unavailable; refusing",
              file=sys.stderr, flush=True)
        return False
    if not scripts_match(checkout, CODE, GUARD_SCRIPTS):
        print("run_ledger_guard: publisher scripts on main differ "
              "from the reviewed release copies; refusing to execute "
              "unreviewed code (D2)", file=sys.stderr, flush=True)
        _write_guard_heartbeat(checkout, "failed")
        return False
    env = _guard_env()
    _assert_no_denied(env)
    r = subprocess.run(
        [sys.executable, str(checkout / "scripts" / "ledger_publish.py"),
         "--commit", "--fail-hard"],
        cwd=checkout, env=env, capture_output=True, text=True,
        timeout=1800)
    if r.stdout.strip():
        print(r.stdout[-2000:], flush=True)
    if r.stderr.strip():
        print(r.stderr[-2000:], file=sys.stderr, flush=True)
    status = "ok" if r.returncode == 0 else "failed"
    if r.returncode != 0:
        # The publisher's durable API signal needs an Issues-capable
        # token the worker PAT is not; mirror the failure to the bus
        # for Moos to file (see the section header above).
        _write_bus_json(
            "ledger-failure.json",
            {"kind": "publish-failed", "job_id": job["id"],
             "at": now(), "worker": os.uname().nodename,
             "detail": (r.stdout + r.stderr)[-500:]},
            f"ledger publish failed {job['id']}")
    _write_guard_heartbeat(checkout, status)
    return True


def guard_pending_from_bus(queue_ids, claim_ids, done_ids):
    """Pure: True when a guard slot is queued or claimed but not
    done — the worker-bus equivalent of the watchdog's #156
    pending-Actions-run check."""
    live = (set(queue_ids) | set(claim_ids)) - set(done_ids)
    return any(str(i).startswith("guard-") for i in live)


def run_ledger_watchdog(job):
    """Execute one `ledger-watchdog` job: run the watchdog script
    against the main checkout's heartbeat file, with the pending
    state taken from the bus, and mirror its signal decision to
    queue/guard-alert.json (the worker PAT cannot file issues —
    see the section header). Returns True when the check ran."""
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
    queue_ids = [str(j.get("id", "")) for j in read_queue()]
    claims_dir = BUS / "queue" / "claims"
    claim_ids = [f.name[:-len(".json")] for f in
                 claims_dir.glob("*.json")] if claims_dir.exists() else []
    done_dir = BUS / "queue" / "done"
    done_ids = [f.name[:-len(".json")] for f in
                done_dir.glob("*.json")] if done_dir.exists() else []
    pending = guard_pending_from_bus(queue_ids, claim_ids, done_ids)
    out = OUT / f"{job['id']}-signal.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    env = _guard_env()
    _assert_no_denied(env)
    r = subprocess.run(
        [sys.executable,
         str(checkout / "scripts" / "ledger_guard_watch.py"),
         "--heartbeat", str(checkout / GUARD_HEARTBEAT_REL),
         "--guard-pending", "yes" if pending else "no",
         "--signal-out", str(out)],
        cwd=checkout, env=env, capture_output=True, text=True,
        timeout=600)
    if r.stdout.strip():
        print(r.stdout[-2000:], flush=True)
    if r.stderr.strip():
        print(r.stderr[-2000:], file=sys.stderr, flush=True)
    try:
        payload = json.loads(out.read_text())
    except Exception:
        payload = None
    if payload and payload.get("action") == "create":
        _write_bus_json(
            "guard-alert.json",
            {"state": "dead", "at": now(),
             "worker": os.uname().nodename, "job_id": job["id"],
             "signal": payload},
            f"guard alert {job['id']}")
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
                _write_bus_json(
                    "guard-alert.json",
                    {"state": "recovered", "at": now(),
                     "worker": os.uname().nodename,
                     "job_id": job["id"],
                     "reason": (payload or {}).get(
                         "reason", "heartbeat fresh")},
                    f"guard recovered {job['id']}")
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
    # for jobs that failed parsing.
    slug = re.sub(r"[^a-z0-9]+", "-", job["job"].lower()).strip("-")[:60]
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
# 45-day window, so skipping loses no disclosure.
DISCLOSURE_TICKERS = ("POUL", "COMI")
DISCLOSURE_FRESH_HOURS = 12  # same bound as HARVEST_TTL_HOURS
DISCLOSURE_EXTRACT_TIMEOUT = 300


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
        kind = (job.get("job") or "").split()
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
        kind = (job.get("job") or "").split()
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
    try:
        kind = (job.get("job") or "").split()
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
            head = subprocess.run(
                ["git", "-C", str(arch), "rev-parse", "HEAD"],
                env=env, capture_output=True, text=True, timeout=30)
            if head.returncode == 0 and head.stdout.strip():
                cmd += ["--archive-sha", head.stdout.strip()]
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
        kind = (job.get("job") or "").split()
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
        _execute_body(job)


def _execute_body(job):
    # Issue #66 extension: first-party schedule jobs — no tools, no
    # archive publish; their outputs are ledger commits on main and
    # bus markers. Done is marked only when the attempt completed
    # (see run_ledger_guard / run_ledger_watchdog).
    if job["job"] == "ledger-guard":
        if run_ledger_guard(job):
            # Issue #216: failure handling is centralized in
            # _mark_done (outbox retention, per-cycle drain,
            # heartbeat surfacing, local re-execution gate); callers
            # deliberately do not branch on its return.
            _mark_done(job, "ledger-guard")
        return
    if job["job"] == "ledger-watchdog":
        if run_ledger_watchdog(job):
            _mark_done(job, "ledger-watchdog")  # centralized #216 handling
        return
    reg = registry()
    workdir = OUT / job["id"]
    workdir.mkdir(parents=True, exist_ok=True)
    manifest = {"job": job, "worker": os.uname().nodename,
                "started": now(), "tools": {}}
    if job["job"].startswith("harvest-egx"):
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
    plan = parse_job(job["job"], reg)
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


def prune_out():
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


def main():
    RUNNERS.mkdir(parents=True, exist_ok=True)
    VENVS.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    while True:
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
            for job in read_queue():
                if not JOB_ID_RE.match(str(job.get("id", ""))):
                    continue  # panel round 2: ids reach file paths
                if _done_or_pending(job["id"]):
                    # Issue #149: a completed job never runs again,
                    # even after its claim was reclaimed. Issue #216:
                    # any local completion evidence (valid or
                    # quarantined-corrupt receipt) also blocks
                    # re-execution on this host.
                    continue
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
