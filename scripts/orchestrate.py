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
  5. restores the child's original COMMANDS,
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
import sys
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


def dispatch(repo):
    status, _, data = gh("POST", f"/repos/{ORG}/{repo}/actions/workflows/run.yml/dispatches",
                         {"ref": "main"})
    return status in (201, 204), data


def find_new_run(repo, since_epoch):
    status, _, data = gh("GET", f"/repos/{ORG}/{repo}/actions/workflows/run.yml/runs?event=workflow_dispatch&per_page=5")
    if status != 200:
        return None
    for run in data.get("workflow_runs", []):
        created = run.get("created_at", "")
        try:
            ts = datetime.strptime(created, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
        except Exception:
            continue
        if ts >= since_epoch - 10:
            return run
    return None


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
    if original and "echo $? > results/.exit" in original:
        # A previous run killed mid-flight never reached the finally
        # restore, so the stored value already carries our emitter.
        # Strip it (its signature two-line head) or every kill
        # permanently appends another copy (panel round 4, G4-03).
        original = original.split(
            "\nmkdir -p results\necho $? > results/.exit")[0]
    command = tool["command"].replace("{ticker}", ticker).replace("{date}", date_str)
    composed = command.rstrip() + "\n" + (EMITTER % (tool_id, ticker))
    result = {"tool": tool_id, "repo": repo, "category": tool["category"]}
    if state == "error":
        result.update(status="error", detail="could not read COMMANDS variable — left untouched")
        return result
    changed = False
    try:
        if not set_variable(repo, "COMMANDS", composed):
            result.update(status="error", detail="could not set COMMANDS variable")
            return result
        changed = True
        since = time.time()
        ok, data = dispatch(repo)
        if not ok:
            result.update(status="error", detail=f"dispatch failed: {data}")
            return result
        run = None
        for _ in range(15):
            time.sleep(4)
            run = find_new_run(repo, since)
            if run:
                break
        if not run:
            result.update(status="error", detail="dispatched but no run appeared")
            return result
        result["run_url"] = run.get("html_url")
        finished = wait_run(repo, run["id"])
        if not finished:
            result.update(status="timeout", detail=f"no completion within {TOOL_TIMEOUT//60} min")
            return result
        if finished.get("_api_error"):
            result.update(status="api-error",
                          detail=f"run polling failed (HTTP {finished['_api_error']})")
            return result
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
        return {"tool": tool.get("id", "?"), "status": "error",
                "detail": f"orchestrator exception: {type(e).__name__}: {e}"}


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
    started = datetime.now(timezone.utc)
    results = [run_tool_safe(t, ticker, date_str) for t in selected]
    finished = datetime.now(timezone.utc)

    os.makedirs(DIGEST_DIR, exist_ok=True)
    digest = {
        "job": job, "ticker": ticker, "date": date_str,
        "started": started.isoformat(), "finished": finished.isoformat(),
        "results": results,
    }
    with open(os.path.join(DIGEST_DIR, "digest.json"), "w") as f:
        json.dump(digest, f, indent=2)

    lines = [f"# 🐊 Borsagator digest — {job}", "",
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
        lines.append(f"| {r['tool']} | {r['category']} | {status} | {keys} | {run_link} |")
    lines += ["", "_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._"]
    with open(os.path.join(DIGEST_DIR, "digest.md"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
