#!/usr/bin/env python3
"""Borsagator sweep archiver.

Stages a permanent, point-in-time copy of everything a sweep saw and
produced — the harvested per-tool results (collected/), the digest and
the ensemble forecast — so the calibration ledger and the per-stock
reaction profiles can later be built and audited against exactly what
the fleet knew at the time. The workflow commits the staged tree to
the `archive` branch; this script only prepares it (stdlib only,
never raises).

Layout on the archive branch:
  sweeps/<YYYY-MM-DD>/<HHMMSS>__<job-slug>__run<id>/
      manifest.json  digest.json  ensemble.json  digest.md
      registry.json  collected/<tool>/...
Files over 5 MB are skipped and recorded in the manifest.
"""
import hashlib, json, os, re, shutil, sys
from datetime import datetime, timezone

MAX_FILE = 5 * 1024 * 1024
ROOT = os.getcwd()
STAGE = os.path.join(ROOT, "archive_stage")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    digest_path = os.path.join(ROOT, "digest", "digest.json")
    digest = {}
    if os.path.exists(digest_path):
        with open(digest_path, encoding="utf-8") as f:
            digest = json.load(f)
    job = str(digest.get("job") or "unknown-job")
    now = datetime.now(timezone.utc)
    slug = re.sub(r"[^a-z0-9]+", "-", job.lower()).strip("-")[:60] or "job"
    run_id = os.environ.get("GITHUB_RUN_ID", "local")
    target = f"sweeps/{now:%Y-%m-%d}/{now:%H%M%S}__{slug}__run{run_id}"
    dest = os.path.join(STAGE, "data")
    # Fresh stage every run: a file removed or newly skipped since the
    # last run must not linger into this run's payload (Ins, issue #49).
    shutil.rmtree(dest, ignore_errors=True)
    if os.path.isdir(dest):
        # rmtree is best-effort (G4-04): clear leftovers one by one,
        # or stale files ride into this run's archive payload.
        for root, dirs, names in os.walk(dest, topdown=False):
            for n in names:
                try:
                    os.unlink(os.path.join(root, n))
                except Exception:
                    pass
            for d in dirs:
                try:
                    os.rmdir(os.path.join(root, d))
                except Exception:
                    pass
    os.makedirs(dest, exist_ok=True)

    files, skipped = [], []

    def copy(src, rel):
        if not os.path.exists(src):
            return
        size = os.path.getsize(src)
        if size > MAX_FILE:
            skipped.append({"path": rel, "bytes": size, "reason": "over 5 MB cap"})
            return
        out = os.path.join(dest, rel)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        shutil.copy2(src, out)
        files.append({"path": rel, "bytes": size, "sha256": sha256(out)})

    copy(digest_path, "digest.json")
    copy(os.path.join(ROOT, "digest", "ensemble.json"), "ensemble.json")
    copy(os.path.join(ROOT, "digest", "digest.md"), "digest.md")
    copy(os.path.join(ROOT, "registry", "tools.json"), "registry.json")

    collected = os.path.join(ROOT, "collected")
    if os.path.isdir(collected):
        for dirpath, _dirs, names in os.walk(collected):
            for name in sorted(names):
                src = os.path.join(dirpath, name)
                rel = os.path.relpath(src, ROOT).replace(os.sep, "/")
                copy(src, rel)

    manifest = {
        "job": job,
        "ticker": digest.get("ticker"),
        "digest_date": digest.get("date"),
        "archived_at": now.isoformat(),
        "github_run_id": run_id,
        "target": target,
        "tools": {r.get("tool"): r.get("status") for r in digest.get("results", [])},
        "files": files,
        "skipped": skipped,
    }
    with open(os.path.join(dest, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1, ensure_ascii=False)
    with open(os.path.join(STAGE, "TARGET.txt"), "w", encoding="utf-8") as f:
        f.write(target)
    # Leave a trace in the digest the issue is built from.
    try:
        with open(os.path.join(ROOT, "digest", "digest.md"), "a", encoding="utf-8") as f:
            f.write(f"\n_Archived point-in-time at `{target}` on branch `archive` "
                    f"({len(files)} files, {len(skipped)} skipped)._\n")
    except Exception:
        pass
    print(f"archive staged: {target} | {len(files)} files, {len(skipped)} skipped")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("archive failed (non-fatal):", e)
        # Never fail silently (INS-R4-05): the digest issue is what
        # gets read every morning — put the failure in it.
        try:
            p = os.path.join(ROOT, "digest", "digest.md")
            if os.path.exists(p):
                with open(p, "a", encoding="utf-8") as f:
                    f.write(f"\n⚠️ **Archive failed:** {e} — this sweep "
                            f"is NOT in the point-in-time archive.\n")
        except Exception:
            pass
    sys.exit(0)
