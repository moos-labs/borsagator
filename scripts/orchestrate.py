#!/usr/bin/env python3
"""Borsagator orchestrator.

Reads a JOB — "sweep <ticker>" (all tools), "sweep-lite <ticker>" (all but
the expensive agent category), "category <name> <ticker>",
"market <EGX|US> <ticker>", or "run <tool> <ticker>" — then for every
selected tool in registry/tools.json:
  1. reads the child repo's current COMMANDS variable (kept for restore),
  2. sets COMMANDS to the registry template ({ticker}/{date} substituted)
     plus an exit-code capture and a summary.json emitter,
  3. dispatches the child's run.yml workflow,
  4. waits for the run, downloads its "results" artifact,
  5. restores the child's original COMMANDS — only once the child run
     has reached a terminal state (#134), so a still-running child can
     never execute the restored value,
  6. collects results/<tool>/summary.json.
Finally writes digest/digest.json and digest/digest.md.

Auth: a Borsagator GitHub App installation token (Actions + Variables
permissions on the target repos only). Installation tokens live ONE
hour but full sweeps run longer, so when BORSAGATOR_APP_ID and
BORSAGATOR_APP_PRIVATE_KEY are in the environment the orchestrator
mints and refreshes its own tokens (PyJWT); otherwise it uses the
static GH_TOKEN env.
"""
import io
import json
import os
import re
import signal
import sys
import tempfile
import time
import urllib.request
import urllib.error
import zipfile
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ORG = "moos-labs"
HERE = os.path.dirname(os.path.abspath(__file__))
REGISTRY = os.path.join(HERE, "..", "registry", "tools.json")
OUT = os.path.join(os.getcwd(), "collected")
DIGEST_DIR = os.path.join(os.getcwd(), "digest")
POLL_SECONDS = 20
TOOL_TIMEOUT = 60 * 60  # per tool, seconds (tradingagents took ~37 min)
# Issue #134: a dispatched run used to get only 60s (15 x 4s) to appear
# before the tool was recorded "dispatched but no run appeared" — while
# the run later actually started and, worse, the finally block had
# already restored COMMANDS, so it executed the wrong command.
APPEARANCE_POLL_SECONDS = 4
APPEARANCE_ATTEMPTS = 75  # 75 x 4s = 5 min appearance window
APPEARANCE_TOLERANCE_SECONDS = 10  # clock-skew tolerance on created_at
# Issue #134: bound on waiting for a timed-out child to reach a
# terminal state before COMMANDS is restored. A run that is still
# queued/in-progress may not have read the variable yet.
RESTORE_GRACE_SECONDS = 30 * 60

TOKEN = os.environ.get("GH_TOKEN", "")

# --- App-token lifecycle ---------------------------------------------------
# A GitHub App installation token lives ONE hour, but a full sweep runs
# longer — the orchestrator used to go blind mid-sweep: every API call
# returned 401, a still-running child was recorded as "timeout" after
# the full wait, and later tools were never dispatched (first seen in
# the 2026-11-13 full POUL sweep, run 43386334186). With the App
# credentials in the environment the orchestrator mints its own
# installation tokens and refreshes them proactively (~45 min) and on
# any 401. Without them it falls back to the static GH_TOKEN.
APP_ID = os.environ.get("BORSAGATOR_APP_ID", "")
APP_KEY = os.environ.get("BORSAGATOR_APP_PRIVATE_KEY", "")
_token_born = 0.0 if (APP_ID and APP_KEY) else time.time()
_installation_id = None


def _app_jwt():
    import jwt  # PyJWT — installed by the workflow for this purpose
    now = int(time.time())
    return jwt.encode({"iss": APP_ID, "iat": now - 60, "exp": now + 540},
                      APP_KEY, algorithm="RS256")


def _mint_token():
    global TOKEN, _token_born, _installation_id
    jwt_token = _app_jwt()

    def call(method, path):
        req = urllib.request.Request("https://api.github.com" + path,
                                     method=method)
        req.add_header("Authorization", "Bearer " + jwt_token)
        req.add_header("Accept", "application/vnd.github+json")
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read() or b"{}")

    if _installation_id is None:
        data = call("GET", f"/repos/{ORG}/borsagator/installation")
        _installation_id = data["id"]
    data = call("POST",
                f"/app/installations/{_installation_id}/access_tokens")
    TOKEN = data["token"]
    _token_born = time.time()
    print(f"borsagator: minted a fresh App installation token "
          f"(installation {_installation_id})", flush=True)
    return TOKEN


def ensure_token(force=False):
    if not (APP_ID and APP_KEY):
        return TOKEN
    if force or not TOKEN or time.time() - _token_born > 45 * 60:
        try:
            return _mint_token()
        except Exception as e:  # noqa: BLE001 - keep the old token and try on
            print(f"borsagator: token mint failed ({e}); "
                  f"continuing with the current token", flush=True)
    return TOKEN

EMITTER = '''
__borsa_ec=$?
mkdir -p results
echo $__borsa_ec > results/.exit
python3 - <<'BORSA_EOF'
import json, os, glob
res = "results"
summary = {"tool": %r, "ticker": %r, "borsagator": True}
try:
    summary["exit_code"] = int(open(os.path.join(res, ".exit")).read().strip())
except Exception:
    summary["exit_code"] = None
summary["status"] = "ok" if summary["exit_code"] == 0 else "failed"
metrics = {}
for path in sorted(glob.glob(os.path.join(res, "*.json")) + glob.glob(os.path.join(res, "*", "*.json"))):
    if os.path.basename(path) in ("summary.json",):
        continue
    try:
        data = json.load(open(path))
    except Exception:
        continue
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, (int, float, str, bool)) and len(str(v)) <= 120 and len(metrics) < 30:
                metrics[str(k)] = v
import csv as _csv
for path in sorted(glob.glob(os.path.join(res, "*.csv")) + glob.glob(os.path.join(res, "*", "*.csv"))):
    try:
        with open(path, newline="") as f:
            rows = list(_csv.reader(f))
    except Exception:
        continue
    if len(rows) < 2:
        continue
    name = os.path.basename(path)
    metrics["rows_" + name] = len(rows) - 1
    header = [h.strip().lower() for h in rows[0]]
    last = rows[-1]
    for want in ("date", "close"):
        if want in header and len(metrics) < 30:
            idx = header.index(want)
            if idx < len(last):
                metrics[name + "_last_" + want] = last[idx]
summary["metrics"] = metrics
summary["files"] = sorted(os.path.basename(p) for p in glob.glob(os.path.join(res, "*")) if os.path.isfile(p))
with open(os.path.join(res, "summary.json"), "w") as f:
    json.dump(summary, f, indent=2)
print("borsagator: summary.json written")
BORSA_EOF
'''


def gh(method, path, body=None, raw=False, auth=True, _retried=False):
    url = "https://api.github.com" + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if auth:
        tok = ensure_token()
        if tok:
            req.add_header("Authorization", "Bearer " + tok)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if data is not None:
        req.add_header("Content-Type", "application/json")

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a):
            return None

    opener = urllib.request.build_opener(NoRedirect())
    try:
        with opener.open(req, timeout=60) as r:
            payload = r.read()
            if raw:
                return r.status, dict(r.headers), payload
            return r.status, {}, (json.loads(payload) if payload else {})
    except urllib.error.HTTPError as e:
        if e.code == 401 and auth and APP_ID and APP_KEY and not _retried:
            e.read()
            if ensure_token(force=True):
                return gh(method, path, body, raw, auth, _retried=True)
        if e.code in (301, 302, 303, 307, 308):
            return e.code, dict(e.headers), b""
        payload = e.read()
        if raw:
            return e.code, dict(e.headers), payload
        try:
            return e.code, {}, json.loads(payload) if payload else {}
        except Exception:
            return e.code, {}, {"raw": payload[:300]}


def download(url, max_bytes=200_000_000):
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=120) as r:
        blob = r.read(max_bytes + 1)
    if len(blob) > max_bytes:
        raise ValueError(f"download exceeds the {max_bytes}-byte cap")
    return blob


def get_variable(repo, name):
    """Returns (state, value): state is 'ok' (value known), 'missing' (404),
    or 'error' (anything else — caller must not touch the variable)."""
    status, _, data = gh("GET", f"/repos/{ORG}/{repo}/actions/variables/{name}")
    if status == 200:
        return "ok", data.get("value")
    if status == 404:
        return "missing", None
    return "error", None


def set_variable(repo, name, value):
    status, _, _ = gh("PATCH", f"/repos/{ORG}/{repo}/actions/variables/{name}",
                      {"name": name, "value": value})
    if status == 404:
        status, _, _ = gh("POST", f"/repos/{ORG}/{repo}/actions/variables",
                          {"name": name, "value": value})
    return status < 300


def delete_variable(repo, name):
    status, _, _ = gh("DELETE", f"/repos/{ORG}/{repo}/actions/variables/{name}")
    return status in (204, 404)


def dispatch(repo, inputs=None):
    body = {"ref": "main"}
    if inputs:
        body["inputs"] = inputs
    status, _, data = gh("POST", f"/repos/{ORG}/{repo}/actions/workflows/run.yml/dispatches",
                         body)
    return status in (201, 204), data


def get_branch_sha(repo, branch="main"):
    """Best-effort HEAD SHA of the child's branch, used only as a
    preference when matching the dispatched run (#134). Returns None
    on any failure — matching then falls back to branch + time."""
    status, _, data = gh("GET", f"/repos/{ORG}/{repo}/branches/{branch}")
    if status != 200:
        return None
    commit = data.get("commit") or {}
    return commit.get("sha")


def snapshot_runs(repo):
    """Ids of the workflow_dispatch runs visible just before a dispatch,
    so find_new_run can require a strictly newer run (#134). Returns an
    empty set on any API failure — matching then falls back to branch +
    time, never to refusing the dispatch."""
    status, _, data = gh("GET", f"/repos/{ORG}/{repo}/actions/workflows/run.yml/runs?event=workflow_dispatch&per_page=10")
    if status != 200:
        return set()
    return {run["id"] for run in data.get("workflow_runs", [])
            if isinstance(run.get("id"), int)}


def find_new_run(repo, since_epoch, seen_ids=None, expected_branch="main",
                 expected_sha=None):
    """The run created by our just-issued dispatch — not merely the
    newest workflow_dispatch run (#134).

    Two overlapping sweeps dispatching the same child repo within
    seconds used to cross-wire: the old code returned the first run
    with created_at >= since - 10s from a newest-first list of 5, with
    no check on branch, head SHA, or whether the run predated our
    dispatch. Now a candidate must be a run we had not seen before the
    dispatch, created within tolerance of it, on the dispatched branch;
    among those, the run whose head SHA matches the branch HEAD we read
    just before dispatching — and whose created_at is earliest at/after
    our dispatch — wins. (A dispatch input carrying a correlation id
    cannot be matched back: the runs API never returns dispatch inputs,
    so identity has to come from id + time + branch + SHA.)"""
    status, _, data = gh("GET", f"/repos/{ORG}/{repo}/actions/workflows/run.yml/runs?event=workflow_dispatch&per_page=10")
    if status != 200:
        return None
    seen_ids = seen_ids or set()
    candidates = []
    for run in data.get("workflow_runs", []):
        if run.get("id") in seen_ids:
            continue
        created = run.get("created_at", "")
        try:
            ts = datetime.strptime(created, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
        except Exception:
            continue
        if ts < since_epoch - APPEARANCE_TOLERANCE_SECONDS:
            continue
        # Our dispatch always uses ref main; a run on another branch
        # is somebody else's, however new it is.
        head_branch = run.get("head_branch")
        if head_branch is not None and head_branch != expected_branch:
            continue
        score = 0
        if head_branch == expected_branch:
            score += 2
        if expected_sha and run.get("head_sha") == expected_sha:
            score += 2
        if ts >= since_epoch:
            score += 1
        candidates.append((score, ts, run.get("id", 0), run))
    if not candidates:
        return None
    # Highest score wins; ties break to the earliest created run, which
    # is the one our dispatch created — a later run from an overlapping
    # sweep sorts after it.
    candidates.sort(key=lambda c: (-c[0], c[1], c[2]))
    return candidates[0][3]


def get_run_status(repo, run_id):
    """The run's status string ('queued'/'in_progress'/'completed'/...),
    or None if the API call failed."""
    status, _, data = gh("GET", f"/repos/{ORG}/{repo}/actions/runs/{run_id}")
    if status != 200:
        return None
    return data.get("status")


def wait_for_terminal(repo, run_id, grace_seconds=RESTORE_GRACE_SECONDS):
    """Poll until the child run reaches a terminal state ('completed').

    Issue #134: the COMMANDS restore must not run while the child may
    still read the variable — the child evaluates vars.COMMANDS when
    its job executes, so a queued/in-progress run that has not read it
    yet would execute the restored (wrong) command. Returns True if a
    terminal state was observed, False if the grace expired or the API
    stayed unreachable (the caller then restores anyway, loudly, so the
    variable is never left composed forever — the restore is gated, not
    deleted)."""
    deadline = time.time() + grace_seconds
    bad_polls = 0
    while time.time() < deadline:
        state = get_run_status(repo, run_id)
        if state == "completed":
            return True
        if state is None:
            bad_polls += 1
            if bad_polls >= 6:
                return False
        else:
            bad_polls = 0
        time.sleep(POLL_SECONDS)
    return False


def wait_run(repo, run_id):
    deadline = time.time() + TOOL_TIMEOUT
    bad_polls = 0
    while time.time() < deadline:
        status, _, data = gh("GET", f"/repos/{ORG}/{repo}/actions/runs/{run_id}")
        if status == 200:
            bad_polls = 0
            if data.get("status") == "completed":
                return data
        else:
            # A dead API (5xx, unrecoverable 401) must not burn the whole
            # tool timeout masquerading as a slow run.
            bad_polls += 1
            if bad_polls >= 6:
                return {"status": "api-error", "conclusion": None,
                        "_api_error": status}
        time.sleep(POLL_SECONDS)
    return None


def fetch_summary(repo, run_id, tool_id):
    """Returns (summary_or_None, detail). The detail explains a failure
    so a 'no-summary' row in the digest is diagnosable instead of mute.
    Artifact members are validated before extraction: a member whose
    resolved path escapes the destination is refused (zip-slip)."""
    status, _, data = gh("GET", f"/repos/{ORG}/{repo}/actions/runs/{run_id}/artifacts")
    if status != 200:
        return None, f"artifacts list HTTP {status}"
    artifact = next((a for a in data.get("artifacts", []) if a.get("name") == "results"), None)
    if not artifact:
        return None, "no 'results' artifact on the run"
    status, headers, _ = gh("GET", f"/repos/{ORG}/{repo}/actions/artifacts/{artifact['id']}/zip", raw=True)
    location = headers.get("Location") or headers.get("location")
    if not location:
        return None, f"artifact zip HTTP {status} with no Location"
    try:
        blob = download(location)
    except Exception as e:
        return None, f"artifact download failed: {e}"
    dest = os.path.join(OUT, tool_id)
    os.makedirs(dest, exist_ok=True)
    dest_abs = os.path.abspath(dest)
    try:
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            infos = z.infolist()
            if len(infos) > 5000:
                return None, f"refused artifact: {len(infos)} members"
            if sum(i.file_size for i in infos) > 500_000_000:
                return None, "refused artifact: expanded size over the cap"
            for member in z.namelist():
                target = os.path.abspath(os.path.join(dest_abs, member))
                if target != dest_abs and not target.startswith(dest_abs + os.sep):
                    return None, f"refused unsafe artifact member: {member}"
            z.extractall(dest)
    except Exception as e:
        return None, f"artifact extract failed: {e}"
    summary_path = os.path.join(dest, "summary.json")
    if os.path.exists(summary_path):
        try:
            with open(summary_path) as f:
                return json.load(f), ""
        except Exception as e:
            return None, f"summary.json unreadable: {e}"
    return None, "artifact carried no summary.json"


def run_tool(tool, ticker, date_str):
    repo = tool["repo"]
    tool_id = tool["id"]
    print(f"== {tool_id} ({repo})", flush=True)
    state, original = get_variable(repo, "COMMANDS")
    if original and "results/.exit" in original:
        # A previous run killed mid-flight never reached the finally
        # restore, so the stored value already carries our emitter.
        # Strip it at its earliest signature line or every kill
        # permanently appends another copy (panel round 4, G4-03).
        cuts = [original.find(m) for m in
                ("\n__borsa_ec=$?", "\nmkdir -p results\necho $?")]
        cuts = [c for c in cuts if c >= 0]
        if cuts:
            original = original[:min(cuts)]
    command = tool["command"].replace("{ticker}", ticker).replace("{date}", date_str)
    composed = command.rstrip() + "\n" + (EMITTER % (tool_id, ticker))
    result = {"tool": tool_id, "repo": repo, "category": tool["category"]}
    use_inputs = bool(tool.get("inputs"))
    if state == "error" and not use_inputs:
        result.update(status="error", detail="could not read COMMANDS variable — left untouched")
        return result
    changed = False
    run_id = None
    run_terminal = False
    try:
        since = time.time()
        # #134: snapshot the runs visible before our dispatch, and the
        # branch HEAD, so find_new_run can tell our run apart from an
        # overlapping sweep's run to the same child repo. Both are
        # best-effort: a failed read degrades matching, never the run.
        expected_sha = get_branch_sha(repo)
        seen_ids = snapshot_runs(repo)
        if use_inputs:
            # INS-R4-02: parameters travel as dispatch inputs; the
            # shared COMMANDS variable is never read as a channel
            # nor patched, so overlapping sweeps cannot cross-wire.
            ok, data = dispatch(repo, {"commands": composed})
        else:
            if not set_variable(repo, "COMMANDS", composed):
                result.update(status="error", detail="could not set COMMANDS variable")
                return result
            changed = True
            ok, data = dispatch(repo)
        if not ok:
            result.update(status="error", detail=f"dispatch failed: {data}")
            return result
        run = None
        for _ in range(APPEARANCE_ATTEMPTS):
            time.sleep(APPEARANCE_POLL_SECONDS)
            run = find_new_run(repo, since, seen_ids=seen_ids,
                               expected_sha=expected_sha)
            if run:
                break
        if not run:
            result.update(status="error", detail="dispatched but no run appeared")
            return result
        run_id = run["id"]
        result["run_url"] = run.get("html_url")
        finished = wait_run(repo, run_id)
        if not finished:
            result.update(status="timeout", detail=f"no completion within {TOOL_TIMEOUT//60} min")
            return result
        if finished.get("_api_error"):
            result.update(status="api-error",
                          detail=f"run polling failed (HTTP {finished['_api_error']})")
            return result
        run_terminal = True
        result["conclusion"] = finished.get("conclusion")
        summary, fs_detail = fetch_summary(repo, run["id"], tool_id)
        if summary:
            result["summary"] = summary
            result["status"] = summary.get("status", "unknown")
        else:
            result["status"] = "no-summary"
            if fs_detail:
                result["detail"] = fs_detail
        return result
    finally:
        if changed:
            if run_id is not None and not run_terminal:
                # #134: the child run exists but never reached a terminal
                # state in our sight (wait timeout, API error, or an
                # orchestrator exception mid-flight). It may not have
                # read COMMANDS yet — restoring now would make it
                # execute the restored (wrong) command. Wait for a
                # terminal state first; the restore still happens, it
                # is gated, not deleted.
                if wait_for_terminal(repo, run_id):
                    print(f"borsagator: child run {run_id} reached a "
                          f"terminal state before COMMANDS restore",
                          flush=True)
                else:
                    print(f"WARNING: COMMANDS restore for {repo} "
                          f"proceeding although run {run_id} never "
                          f"reached a terminal state", flush=True)
                    result["detail"] = ((result.get("detail") or "")
                                        + " [COMMANDS restored while child "
                                        "run not terminal]")
            ok = (delete_variable(repo, "COMMANDS") if state == "missing"
                  else set_variable(repo, "COMMANDS", original))
            if not ok:
                # A silent restore failure leaves the child repo
                # patched with our composed command (INS-R4-03).
                print(f"WARNING: COMMANDS restore FAILED for {repo}",
                      flush=True)
                result["detail"] = ((result.get("detail") or "")
                                     + " [COMMANDS restore failed]")


def run_tool_safe(tool, ticker, date_str):
    """One tool's failure — including an orchestrator-side exception —
    becomes its own error row; it must never abort the whole sweep
    before the digest is written (Ins review, issue #49)."""
    try:
        return run_tool(tool, ticker, date_str)
    except Exception as e:
        # Issue #113: the error row must carry the same shape as a
        # success row — the digest table reads r['category'], so an
        # error row without it killed the whole gator (run
        # 43815097317: stocksharp RemoteDisconnected) AFTER
        # digest.json was written and BEFORE digest.md was.
        return {"tool": tool.get("id", "?"),
                "category": tool.get("category", "error"),
                "status": "error",
                "detail": f"orchestrator exception: {type(e).__name__}: {e}"}


# Issue #120: digest status markers — a digest file must never look
# finished when it isn't. The placeholder carries "running"; the full
# digest "complete"; a failure notice "failed". The workflow's issue
# step reads the marker and refuses to file a "running" digest as a
# finished run (a SIGKILL / runner crash leaves the placeholder in
# place — no Python code runs then, so only the issue step can catch
# that death).
DIGEST_STATUS_RUNNING = "running"
DIGEST_STATUS_COMPLETE = "complete"
DIGEST_STATUS_FAILED = "failed"


def _digest_status_line(status):
    return f"<!-- borsagator-digest-status: {status} -->"


def _write_text_atomic(path, text):
    """Write text via a temp file + os.replace in the same directory,
    so a crash mid-write can never leave a torn digest behind."""
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".digest-",
                               suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _write_failure_digest(header, job, started, total, results, exc):
    """Issue #120: replace the "Running" placeholder with a failure
    notice — what died, when, and how far the sweep got. digest.json
    is deliberately NOT written here, and any partial/stale copy is
    removed: with no digest.json the ensemble step records that no
    forecast was produced instead of forecasting on partial or stale
    results. Best-effort: must never raise itself (it runs on the way
    out of a failure)."""
    try:
        detail = str(exc).strip() or "interrupted (no further detail)"
        died = datetime.now(timezone.utc)
        lines = [header, "", _digest_status_line(DIGEST_STATUS_FAILED), "",
                 f"⚠️ **SWEEP FAILED — {type(exc).__name__}: {detail}.**",
                 "",
                 f"The sweep died at {died.strftime('%Y-%m-%d %H:%M UTC')} "
                 f"(started {started.strftime('%Y-%m-%d %H:%M UTC')}) after "
                 f"{len(results)} of {total} tools finished. This is NOT a "
                 f"completed sweep — do not treat the absence of results "
                 f"as an all-clear. No digest.json was written, so the "
                 f"ensemble step records that no forecast was produced.",
                 ""]
        if results:
            lines.append("Tools completed before the failure:")
            lines.append("")
            for r in results:
                r_detail = (r.get("detail") or "").replace("\n", " ")
                lines.append(f"- {r.get('tool', '?')}: {r.get('status', '?')}"
                             + (f" — {r_detail}" if r_detail else ""))
            lines.append("")
        lines.append("_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._")
        try:
            os.remove(os.path.join(DIGEST_DIR, "digest.json"))
        except OSError:
            pass
        _write_text_atomic(os.path.join(DIGEST_DIR, "digest.md"),
                           "\n".join(lines) + "\n")
    except Exception as e:  # noqa: BLE001 - the failure notice must not mask the original failure
        print(f"borsagator: could not write the failure digest ({e})",
              file=sys.stderr, flush=True)


def _sigterm_handler(signum, frame):
    """Issue #120: a runner timeout / cancellation kills with SIGTERM.
    Turn it into an exception so the failure path above can replace
    the placeholder with a failure notice instead of leaving it."""
    raise KeyboardInterrupt("SIGTERM received — runner timeout or cancellation")


def main():
    job = (os.environ.get("JOB") or (sys.argv[1] if len(sys.argv) > 1 else "")).strip()
    if not job:
        print("No JOB given (env JOB or argv[1]).", file=sys.stderr)
        return 2
    parts = job.split()
    mode = parts[0].lower()
    with open(REGISTRY) as f:
        registry = json.load(f)
    all_tools = registry["tools"]
    tools = [t for t in all_tools if t.get("status") == "active"]
    date_str = datetime.now(ZoneInfo("Africa/Cairo")).strftime("%Y-%m-%d")
    if mode in ("sweep", "sweep-lite") and len(parts) >= 2:
        ticker = parts[1]
        selected = list(tools)
        if mode == "sweep-lite":
            selected = [t for t in selected if t["category"] != "agent"]
        # Optional trailing filters: market=EGX / market=US / no-agent
        for tok in parts[2:]:
            if tok.startswith("market="):
                mkt = tok.split("=", 1)[1].upper()
                selected = [t for t in selected if mkt in [m.upper() for m in t.get("markets", [])]]
            elif tok == "no-agent":
                selected = [t for t in selected if t["category"] != "agent"]
            else:
                print(f"Unknown sweep filter: {tok}", file=sys.stderr)
                return 2
        if not selected:
            print("Filters left no tools to run.", file=sys.stderr)
            return 2
    elif mode == "category" and len(parts) >= 3:
        cat, ticker = parts[1].lower(), parts[2]
        selected = [t for t in tools if t["category"] == cat]
        if not selected:
            print(f"No active tools in category: {cat}", file=sys.stderr)
            return 2
    elif mode == "market" and len(parts) >= 3:
        mkt, ticker = parts[1].upper(), parts[2]
        selected = [t for t in tools if mkt in [m.upper() for m in t.get("markets", [])]]
        if not selected:
            print(f"No active tools for market: {mkt}", file=sys.stderr)
            return 2
    elif mode == "run" and len(parts) >= 3:
        wanted, ticker = parts[1], parts[2]
        selected = [t for t in all_tools
                    if t["id"] == wanted and t.get("status") in ("active", "manual")]
        if not selected:
            print(f"Unknown tool: {wanted}", file=sys.stderr)
            return 2
    else:
        print(f"Unparseable JOB: {job!r} (want 'sweep|sweep-lite <ticker>', "
              f"'category <name> <ticker>', 'market <EGX|US> <ticker>' or 'run <tool> <ticker>')",
              file=sys.stderr)
        return 2

    # The ticker is substituted into child shell command templates —
    # it must be a plain symbol, never shell text (panel ⭐, issue #49).
    if not re.fullmatch(r"[A-Za-z0-9.\-]{1,12}", ticker or ""):
        print(f"Refusing unsafe ticker: {ticker!r}", file=sys.stderr)
        return 2

    print(f"Borsagator job: {job} | tools: {[t['id'] for t in selected]} | date {date_str}", flush=True)
    # Issue #120: a runner timeout / cancellation arrives as SIGTERM —
    # turn it into an exception so the failure path below can replace
    # the placeholder with a failure notice. (SIGKILL cannot be
    # caught; that death is flagged by the workflow's issue step,
    # which reads the digest status marker.)
    try:
        signal.signal(signal.SIGTERM, _sigterm_handler)
    except (AttributeError, ValueError, OSError):
        pass
    started = datetime.now(timezone.utc)
    # Issue #113: head the digest file BEFORE any tool runs, so a
    # mid-run death still leaves a headed digest.md for the ensemble
    # append and the issue step (which titles from its first line).
    # The full digest below overwrites this placeholder on success.
    # Issue #120: the placeholder is explicitly marked "running" and
    # says the sweep is INCOMPLETE — if the run dies before the
    # orchestrator can replace it (SIGKILL, runner crash), the issue
    # step reads the marker and files it as a failure, never as a
    # finished run.
    os.makedirs(DIGEST_DIR, exist_ok=True)
    header = f"# 🐊 Borsagator digest — {job}"
    _write_text_atomic(
        os.path.join(DIGEST_DIR, "digest.md"),
        header + "\n\n" + _digest_status_line(DIGEST_STATUS_RUNNING) + "\n\n"
        "⚠️ **SWEEP INCOMPLETE — this digest was never finished.**\n\n"
        f"The sweep started {started.strftime('%Y-%m-%d %H:%M UTC')} and was "
        "still running when this file was last written. If this issue was "
        "filed with this text, the sweep died mid-run (runner crash, "
        "timeout, or SIGKILL) before any results were recorded — do NOT "
        "treat it as a completed sweep.\n")
    results = []
    try:
        for t in selected:
            results.append(run_tool_safe(t, ticker, date_str))
        finished = datetime.now(timezone.utc)

        digest = {
            "job": job, "ticker": ticker, "date": date_str,
            "started": started.isoformat(), "finished": finished.isoformat(),
            "results": results,
        }
        # Atomic like digest.md: a failed write must leave NO digest.json
        # behind, so the failure path's "no digest.json was written"
        # stays true and the ensemble cannot read a torn file.
        _write_text_atomic(os.path.join(DIGEST_DIR, "digest.json"),
                           json.dumps(digest, indent=2))

        # Issue #113: the digest write itself must never be the hole that
        # loses the record — the Ins #49 principle covered tool failures
        # but NOT the digest-writing section, and a table-building
        # exception (KeyError: 'category', run 43815097317) killed the
        # gator after digest.json and before digest.md. Any failure here
        # still writes a minimal headed digest; the run then exits 0 with
        # the failure recorded in the digest, not lost with it.
        try:
            lines = [header, _digest_status_line(DIGEST_STATUS_COMPLETE), "",
                     f"Started {started.strftime('%Y-%m-%d %H:%M UTC')} · finished {finished.strftime('%H:%M UTC')} · "
                     f"{len(results)} tools", "",
                     "| Tool | Category | Status | Key results | Run |",
                     "|---|---|---|---|---|"]
            for r in results:
                summary = r.get("summary") or {}
                metrics = summary.get("metrics") or {}
                verdict_keys = [k for k in metrics if any(w in k.lower() for w in
                                ("rating", "decision", "verdict", "signal", "recommendation"))]
                ordered = [(k, metrics[k]) for k in verdict_keys] + \
                          [(k, v) for k, v in metrics.items() if k not in verdict_keys]
                keys = "; ".join(f"{k}={v}" for k, v in ordered[:5]) or r.get("detail", "") or "—"
                # Tool-controlled values must not break the table (INS-R4-06).
                keys = keys.replace("|", "\\|").replace("\n", " ").replace("\r", " ")
                status = r.get("status", "?")
                if r.get("conclusion") and r["conclusion"] != "success":
                    status += f" ({r['conclusion']})"
                run_link = f"[run]({r['run_url']})" if r.get("run_url") else "—"
                lines.append(f"| {r.get('tool', '?')} | {r.get('category', '—')} | {status} | {keys} | {run_link} |")
            lines += ["", "_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._"]
        except Exception as e:  # noqa: BLE001 - the fallback digest must not throw
            print(f"borsagator: digest table build failed ({type(e).__name__}: {e}); "
                  f"writing minimal digest", file=sys.stderr, flush=True)
            lines = [header, _digest_status_line(DIGEST_STATUS_COMPLETE), "",
                     f"Started {started.strftime('%Y-%m-%d %H:%M UTC')} · finished {finished.strftime('%H:%M UTC')} · "
                     f"{len(results)} tools", "",
                     f"⚠️ The detailed results table could not be built "
                     f"({type(e).__name__}: {e}). Tool outcomes are preserved "
                     f"in digest.json.", ""]
            for r in results:
                detail = (r.get("detail") or "").replace("\n", " ").replace("|", "\\|")
                lines.append(f"- {r.get('tool', '?')}: {r.get('status', '?')}"
                             + (f" — {detail}" if detail else ""))
            lines += ["", "_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._"]
        _write_text_atomic(os.path.join(DIGEST_DIR, "digest.md"),
                           "\n".join(lines) + "\n")
    except BaseException as e:
        # Issue #120: replace the placeholder with a failure notice
        # (what died, when) instead of leaving a "Running" digest
        # that the issue step would file as a finished run. The
        # exception propagates so the workflow step fails loudly.
        _write_failure_digest(header, job, started, len(selected),
                              results, e)
        raise
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
