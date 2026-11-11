#!/usr/bin/env python3
"""Borsagator orchestrator.

Reads a JOB ("sweep <ticker>" or "run <tool> <ticker>"), then for every
selected tool in registry/tools.json:
  1. reads the child repo's current COMMANDS variable (kept for restore),
  2. sets COMMANDS to the registry template ({ticker}/{date} substituted)
     plus an exit-code capture and a summary.json emitter,
  3. dispatches the child's run.yml workflow,
  4. waits for the run, downloads its "results" artifact,
  5. restores the child's original COMMANDS,
  6. collects results/<tool>/summary.json.
Finally writes digest/digest.json and digest/digest.md.

Auth: GH_TOKEN env must be a Borsagator GitHub App installation token
(Actions + Variables permissions on the target repos only).
Stdlib only.
"""
import io
import json
import os
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

EMITTER = '''
echo $? > results/.exit
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
for path in sorted(glob.glob(os.path.join(res, "*.json"))):
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
summary["metrics"] = metrics
summary["files"] = sorted(os.path.basename(p) for p in glob.glob(os.path.join(res, "*")) if os.path.isfile(p))
with open(os.path.join(res, "summary.json"), "w") as f:
    json.dump(summary, f, indent=2)
print("borsagator: summary.json written")
BORSA_EOF
'''


def gh(method, path, body=None, raw=False, auth=True):
    url = "https://api.github.com" + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if auth and TOKEN:
        req.add_header("Authorization", "Bearer " + TOKEN)
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
        if e.code in (301, 302, 303, 307, 308):
            return e.code, dict(e.headers), b""
        payload = e.read()
        if raw:
            return e.code, dict(e.headers), payload
        try:
            return e.code, {}, json.loads(payload) if payload else {}
        except Exception:
            return e.code, {}, {"raw": payload[:300]}


def download(url):
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def get_variable(repo, name):
    status, _, data = gh("GET", f"/repos/{ORG}/{repo}/actions/variables/{name}")
    if status == 200:
        return data.get("value")
    return None


def set_variable(repo, name, value):
    status, _, _ = gh("PATCH", f"/repos/{ORG}/{repo}/actions/variables/{name}",
                      {"name": name, "value": value})
    if status == 404:
        status, _, _ = gh("POST", f"/repos/{ORG}/{repo}/actions/variables",
                          {"name": name, "value": value})
    return status < 300


def delete_variable(repo, name):
    gh("DELETE", f"/repos/{ORG}/{repo}/actions/variables/{name}")


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
    while time.time() < deadline:
        status, _, data = gh("GET", f"/repos/{ORG}/{repo}/actions/runs/{run_id}")
        if status == 200 and data.get("status") == "completed":
            return data
        time.sleep(POLL_SECONDS)
    return None


def fetch_summary(repo, run_id, tool_id):
    status, _, data = gh("GET", f"/repos/{ORG}/{repo}/actions/runs/{run_id}/artifacts")
    if status != 200:
        return None
    artifact = next((a for a in data.get("artifacts", []) if a.get("name") == "results"), None)
    if not artifact:
        return None
    status, headers, _ = gh("GET", f"/repos/{ORG}/{repo}/actions/artifacts/{artifact['id']}/zip", raw=True)
    location = headers.get("Location") or headers.get("location")
    if not location:
        return None
    blob = download(location)
    dest = os.path.join(OUT, tool_id)
    os.makedirs(dest, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        z.extractall(dest)
    summary_path = os.path.join(dest, "summary.json")
    if os.path.exists(summary_path):
        try:
            with open(summary_path) as f:
                return json.load(f)
        except Exception:
            return None
    return None


def run_tool(tool, ticker, date_str):
    repo = tool["repo"]
    tool_id = tool["id"]
    print(f"== {tool_id} ({repo})", flush=True)
    original = get_variable(repo, "COMMANDS")
    command = tool["command"].replace("{ticker}", ticker).replace("{date}", date_str)
    composed = command.rstrip() + "\n" + (EMITTER % (tool_id, ticker))
    result = {"tool": tool_id, "repo": repo, "category": tool["category"]}
    try:
        if not set_variable(repo, "COMMANDS", composed):
            result.update(status="error", detail="could not set COMMANDS variable")
            return result
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
        result["conclusion"] = finished.get("conclusion")
        summary = fetch_summary(repo, run["id"], tool_id)
        if summary:
            result["summary"] = summary
            result["status"] = summary.get("status", "unknown")
        else:
            result["status"] = "no-summary"
        return result
    finally:
        if original is None:
            delete_variable(repo, "COMMANDS")
        else:
            set_variable(repo, "COMMANDS", original)


def main():
    job = (os.environ.get("JOB") or (sys.argv[1] if len(sys.argv) > 1 else "")).strip()
    if not job:
        print("No JOB given (env JOB or argv[1]).", file=sys.stderr)
        return 2
    parts = job.split()
    mode = parts[0].lower()
    with open(REGISTRY) as f:
        registry = json.load(f)
    tools = [t for t in registry["tools"] if t.get("status") == "active"]
    date_str = datetime.now(ZoneInfo("Africa/Cairo")).strftime("%Y-%m-%d")
    if mode == "sweep" and len(parts) >= 2:
        ticker = parts[1]
        selected = tools
    elif mode == "run" and len(parts) >= 3:
        wanted, ticker = parts[1], parts[2]
        selected = [t for t in tools if t["id"] == wanted]
        if not selected:
            print(f"Unknown tool: {wanted}", file=sys.stderr)
            return 2
    else:
        print(f"Unparseable JOB: {job!r} (want 'sweep <ticker>' or 'run <tool> <ticker>')", file=sys.stderr)
        return 2

    print(f"Borsagator job: {job} | tools: {[t['id'] for t in selected]} | date {date_str}", flush=True)
    started = datetime.now(timezone.utc)
    results = [run_tool(t, ticker, date_str) for t in selected]
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
        keys = "; ".join(f"{k}={v}" for k, v in list(metrics.items())[:5]) or r.get("detail", "") or "—"
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
