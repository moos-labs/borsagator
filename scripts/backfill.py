#!/usr/bin/env python3
"""One-off backfill of the sweep archive from past digest issues.

For each listed issue: parse the per-tool run links from the digest
table, download each child run's `results` artifact, stage it as
collected/<tool>/, try to recover the original digest.json /
ensemble.json from the Borsagator run that produced the issue, and
write a manifest marked as a backfill (with any gaps recorded —
artifacts that already expired are listed, never hidden).

Runs inside backfill.yml with GH_TOKEN set to the Borsagator App
token. Stdlib only. Produces archive_stage/ exactly like archive.py.
"""
import hashlib, io, json, os, re, sys, urllib.request, urllib.error
import zipfile
from datetime import datetime, timezone

API = "https://api.github.com"
TOKEN = os.environ.get("GH_TOKEN", "")
ISSUES = [7, 13, 14, 15, 17, 18]
MAX_FILE = 5 * 1024 * 1024
ROOT = os.getcwd()
STAGE = os.path.join(ROOT, "archive_stage")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a):
        return None


def api(path, raw=False):
    req = urllib.request.Request(API + path, method="GET")
    req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Accept", "application/vnd.github+json")
    with urllib.request.build_opener().open(req, timeout=90) as r:
        data = r.read()
    return data if raw else json.loads(data)


def download_zip(owner_repo, artifact_id):
    req = urllib.request.Request(
        f"{API}/repos/{owner_repo}/actions/artifacts/{artifact_id}/zip",
        method="GET")
    req.add_header("Authorization", f"Bearer {TOKEN}")
    try:
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=90) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        loc = e.headers.get("Location")
        if not loc:
            raise
        with urllib.request.build_opener().open(loc, timeout=120) as r:
            return r.read()


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def main():
    registry = json.load(open(os.path.join(ROOT, "registry", "tools.json"),
                              encoding="utf-8"))
    repo_of = {t["id"]: t["repo"] for t in registry["tools"]}
    os.makedirs(os.path.join(STAGE, "data"), exist_ok=True)
    targets = []

    bors_runs = api("/repos/moos-labs/borsagator/actions/runs?per_page=40")["workflow_runs"]

    for num in ISSUES:
        issue = api(f"/repos/moos-labs/borsagator/issues/{num}")
        body = issue.get("body") or ""
        title = issue.get("title") or f"issue-{num}"
        job = title.replace("🐊 Borsagator digest — ", "").strip()
        created = issue.get("created_at", "")  # 2026-11-12T05:39:00Z
        day = created[:10] or "unknown"
        hms = (created[11:19] or "000000").replace(":", "")
        slug = re.sub(r"[^a-z0-9]+", "-", job.lower()).strip("-")[:50] or "job"
        target = f"sweeps/{day}/{hms}__backfill-issue-{num}__{slug}"
        dest = os.path.join(STAGE, "data", target)
        os.makedirs(dest, exist_ok=True)
        files, skipped, gaps = [], [], []

        def stage(rel, data):
            if len(data) > MAX_FILE:
                skipped.append({"path": rel, "bytes": len(data),
                                "reason": "over 5 MB cap"})
                return
            out = os.path.join(dest, rel)
            os.makedirs(os.path.dirname(out), exist_ok=True)
            with open(out, "wb") as f:
                f.write(data)
            files.append({"path": rel, "bytes": len(data),
                          "sha256": sha256(data)})

        stage("digest.md", body.encode("utf-8"))

        # Recover digest.json / ensemble.json from the producing run:
        # the latest Borsagator run completed before the issue appeared.
        cands = [r for r in bors_runs
                 if r["created_at"] <= created and r.get("conclusion") == "success"]
        if cands:
            run_id = cands[0]["id"]
            try:
                arts = api(f"/repos/moos-labs/borsagator/actions/runs/{run_id}/artifacts")["artifacts"]
                if arts:
                    z = zipfile.ZipFile(io.BytesIO(
                        download_zip("moos-labs/borsagator", arts[0]["id"])))
                    for name in z.namelist():
                        if name in ("digest.json", "ensemble.json"):
                            stage(name, z.read(name))
                else:
                    gaps.append("borsagator digest artifact not found")
            except Exception as e:
                gaps.append(f"digest artifact recovery failed: {e}")
        else:
            gaps.append("no candidate borsagator run found")

        # Child artifacts -> collected/<tool>/
        seen_tools = set()
        for line in body.splitlines():
            m = re.match(r"\| ([a-z0-9-]+) \| [^|]+ \| ([^|]+) \|", line)
            r = re.search(r"/(moos-labs/[a-z0-9-]+)/actions/runs/(\d+)", line)
            if not m or not r:
                continue
            tool, repo, run_id = m.group(1), r.group(1), int(r.group(2))
            if tool in seen_tools:
                continue
            seen_tools.add(tool)
            try:
                arts = api(f"/repos/{repo}/actions/runs/{run_id}/artifacts")["artifacts"]
                if not arts:
                    gaps.append(f"{tool}: artifact gone (expired?)")
                    continue
                z = zipfile.ZipFile(io.BytesIO(download_zip(repo, arts[0]["id"])))
                for name in z.namelist():
                    if name.endswith("/"):
                        continue
                    stage(f"collected/{tool}/{name}", z.read(name))
            except Exception as e:
                gaps.append(f"{tool}: download failed: {e}")

        manifest = {
            "job": job, "backfill": True, "source_issue": num,
            "issue_url": issue.get("html_url"),
            "archived_at": datetime.now(timezone.utc).isoformat(),
            "target": target, "gaps": gaps,
            "registry_snapshot": "current registry (backfill; not the run-time one)",
            "files": files, "skipped": skipped,
        }
        with open(os.path.join(dest, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=1, ensure_ascii=False)
        targets.append(target)
        print(f"issue #{num}: {len(files)} files, gaps={gaps}")

    with open(os.path.join(STAGE, "TARGETS.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(targets))
    print("backfill staged:", len(targets), "sweeps")


if __name__ == "__main__":
    main()
