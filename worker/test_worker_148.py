#!/usr/bin/env python3
"""Regression test for issue #148 (panel round 12, F4): fresh worker
sweeps invoked merge without its required input manifest.

merge.py refuses a run dir with no manifest.json, but _execute called
maybe_merge BEFORE publish() writes manifest.json — and never wrote
the manifest into the workdir at all. Every fresh worker sweep's
merge refused (fleet still published, merge marked failed).

This test exercises the REAL caller — worker._execute — not only
merge.py fixtures: run_tool and publish are stubbed (no runner clones
or bus access offline), while maybe_merge + merge.py + ensemble.py
run for real against this checkout (worker.CODE = the repo root).

Run: python3 worker/test_worker_148.py   (stdlib only, no network)
Fails on unmodified main at check 1 (merge refused: no manifest.json
in run dir); passes on the fix.
"""
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TMP = Path(tempfile.mkdtemp(prefix="test148-"))
os.environ["GATOR_ROOT"] = str(TMP / "gator")

spec = importlib.util.spec_from_file_location(
    "worker148", REPO / "worker" / "worker.py")
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)
worker.CODE = REPO

CSV = ("Date,Open,High,Low,Close,Volume\n"
       "2026-11-09,9.80,9.90,9.70,9.85,1000\n"
       "2026-11-10,9.85,10.00,9.80,9.95,1100\n"
       "2026-11-11,9.95,10.10,9.90,10.05,1200\n"
       "2026-11-12,10.05,10.20,10.00,10.15,1300\n"
       "2026-11-13,10.15,10.30,10.10,10.25,1400\n"
       "2026-11-14,10.25,10.40,10.20,10.35,1500\n")

CAPTURED = {}


def fake_run_tool(tool, ticker, template, ref, repo):
    results = worker.RUNNERS / tool / "results"
    results.mkdir(parents=True, exist_ok=True)
    (results / "POUL.CA.csv").write_text(CSV)
    (results / "run.log").write_text(f"{tool} stub ok\n")
    return "ok", f"{tool} stub log\n"


def fake_publish(job, workdir, manifest):
    CAPTURED["manifest"] = json.loads(json.dumps(manifest))
    CAPTURED["workdir"] = str(workdir)
    return True


worker.run_tool = fake_run_tool
worker.publish = fake_publish

CHECKS = []


def check(name, ok, detail=""):
    CHECKS.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}: {name}"
          + (f" — {detail}" if detail and not ok else ""))
    return ok


# 1. A fresh worker sweep through the real _execute path merges.
job = {"id": "test-148-sweep", "job": "sweep-lite POUL.CA market=EGX"}
worker._execute(job)
workdir = worker.OUT / job["id"]
manifest = CAPTURED["manifest"]
merge = manifest.get("merge") or {}
mm = list((workdir / "_merge_out").rglob("merge-manifest.json")) \
    if (workdir / "_merge_out").is_dir() else []
check("fresh worker sweep merges (status complete)",
      merge.get("status") == "complete" and len(mm) == 1,
      f"merge={merge} merge-manifests={len(mm)}")
check("no merge_error.txt on a successful merge",
      not (workdir / "merge_error.txt").is_file())

# 2. The workdir manifest exists and records the merge outcome.
wd_manifest = workdir / "manifest.json"
check("workdir/manifest.json exists after _execute",
      wd_manifest.is_file())
if wd_manifest.is_file():
    on_disk = json.loads(wd_manifest.read_text())
    check("workdir manifest carries the merge outcome",
          on_disk.get("merge", {}).get("status") == "complete",
          f"merge={on_disk.get('merge')}")
    check("workdir manifest covers every planned tool",
          set(on_disk.get("tools", {})) ==
          {t for t, _ in worker.parse_job(
              job["job"], json.loads(
                  (REPO / "registry" / "tools.json").read_text()))},
          f"tools={sorted(on_disk.get('tools', {}))}")

# 3. The atomic writer leaves no temp file behind.
check("no .manifest.json.tmp left in the workdir",
      not (workdir / ".manifest.json.tmp").exists())
tmpdir = TMP / "atomic"
tmpdir.mkdir(parents=True, exist_ok=True)
worker._write_manifest_atomic(tmpdir, {"job": {"id": "x"}, "tools": {}})
check("_write_manifest_atomic writes parseable JSON",
      json.loads((tmpdir / "manifest.json").read_text()) ==
      {"job": {"id": "x"}, "tools": {}})
check("_write_manifest_atomic leaves no temp file",
      not (tmpdir / ".manifest.json.tmp").exists())

# 4. A non-sweep job still writes the workdir manifest (harmless,
# and publish() copies the workdir into the archive dest).
job2 = {"id": "test-148-run", "job": "run yahooquery POUL.CA"}
CAPTURED.clear()
worker._execute(job2)
workdir2 = worker.OUT / job2["id"]
check("non-sweep job also leaves workdir/manifest.json",
      (workdir2 / "manifest.json").is_file())
check("non-sweep job does not merge (maybe_merge no-op)",
      "merge" not in (CAPTURED.get("manifest") or {}))

failed = [c for c in CHECKS if not c[1]]
print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} passed")
sys.exit(1 if failed else 0)
