#!/usr/bin/env python3
"""Worker-wiring harness for issue #68 (Report Model compiler,
worker-path ``maybe_compile`` hook in ``worker/worker.py``).

Proves the worker hook works, harness-first with a pristine control —
same discipline as ``harness_issue68_wire.py`` (which covered the
Actions step in ``.github/workflows/orchestrate.yml``).

What it exercises, with the REAL ``maybe_compile`` imported from the
worker tree under test and the REAL ``scripts/compile_model.py``:
  1. A worker-style run dir under a temporary GATOR_ROOT:
     ``out/<job-id>/_merge_out/<sweep_dir>`` carries the golden sweep
     141124 from the ``archive`` branch in the shape ``merge.py``
     produces (digest.json + digest.md + ensemble.json + collected/
     + manifest.json + registry.json; any archived report-model.json
     / compile_error.txt is stripped — merge output never carries
     them), and ``manifest["merge"]`` names it with status complete.
  2. ``release/`` is a copy of the repo tree under test (the worker's
     CODE checkout) and ``archive-push/`` a real clone of the
     ``archive`` branch (the worker's publish clone), so
     ``--compiler-sha`` and ``--archive-sha`` resolve exactly as in
     production.
  3. The publish proof is EXECUTED, not inferred: ``publish()`` runs
     against a local bare repo standing in for the bus remote, once
     after a real compile (model in the same commit as the fleet) and
     once after a real F-1 refusal (compile_error.txt and no model in
     the commit, fleet intact).
  4. Refusal branches use real bad input (F-1 ticker mismatch, F-5
     collected/embedded mismatch, F-9 unknown status). Crash-class
     branches (exit 1, exit 0 without a model, malformed model,
     schema-invalid model, hang) use a corrupted-release seam: the
     worker's dependency IS the on-disk script at CODE/scripts/, so
     pointing a fresh GATOR_ROOT's release/ at a broken copy injects
     the fault at the real subprocess boundary — the hook under test
     is unmodified.
  5. Fixed mode exits 0 only when every check passes. --pristine:
     the worker tree is the base WITHOUT the hook; the control must
     show ``maybe_compile`` absent and the compile sequence failing,
     then exits 1 — the control discriminates.

Local only, stdlib only. No network beyond the one-time ``archive``
branch clone, no GitHub API, no live worker, no real bus.

Usage:
    harness_issue68_worker_wire.py [--repo PATH] [--archive-root PATH]
                                   [--pristine] [--keep-stage]
"""
import argparse
from pathlib import Path
import hashlib
import importlib.util
import json
import glob
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_DEFAULT = os.path.dirname(HERE)
ARCHIVE_DEFAULT = os.environ.get(
    "BORSAGATOR_ARCHIVE_ROOT",
    os.path.join(os.path.dirname(REPO_DEFAULT),
                 "borsagator-68-worker-wire-archive"))

SWEEP = ("sweeps/2026-11-16/141124__sweep-lite-poul-ca__"
         "run43875894633")
JOB = {"id": "h68-worker-wire", "job": "sweep-lite POUL.CA market=EGX"}
SENTINEL = "SENTINEL-BUS-URL-VALUE"
# The pristine base the hook was built against: the pristine control
# must test THIS head, not the live HEAD (which carries the hook once
# it is committed).
PRISTINE_HEAD = "10f1bfd1b3890996999b851247a27cdca53b71c7"

CHECKS = []
SECTION = "?"


def check(name, cond, detail=""):
    CHECKS.append((SECTION, name, bool(cond), detail))
    print((f"  PASS [{SECTION}] " if cond else f"  FAIL [{SECTION}] ")
          + name + (f" ({detail})" if detail and not cond else ""))


def section(title):
    global SECTION
    SECTION = title
    print(f"== {title} ==")


def run(cmd, cwd=None, env=None):
    merged = dict(os.environ)
    if env:
        merged.update(env)
    proc = subprocess.run(cmd, cwd=cwd, env=merged,
                          capture_output=True, text=True, timeout=600)
    return proc.returncode, proc.stdout + proc.stderr


def git_head(path):
    rc, out = run(["git", "-C", path, "rev-parse", "HEAD"])
    return out.strip() if rc == 0 else None


def load_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def sha256_file(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def ensure_archive(archive_root):
    if not os.path.isdir(os.path.join(archive_root, SWEEP)):
        rc, out = run(["git", "clone", "--quiet", "--branch",
                       "archive", "--single-branch",
                       "https://github.com/moos-labs/borsagator.git",
                       archive_root])
        assert rc == 0, f"archive clone failed: {out}"


def import_worker(worker_py, gator_root):
    os.environ["GATOR_ROOT"] = gator_root
    spec = importlib.util.spec_from_file_location(
        "worker_under_test", worker_py)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def copy_golden_sweep(archive_root, dest):
    """Copy the golden sweep in merge-output shape (no compiled
    model, no error marker: merge.py output never carries them)."""
    shutil.copytree(os.path.join(archive_root, SWEEP), dest)
    for name in ("report-model.json", "report-model.json.quarantined",
                 "compile_error.txt"):
        stale = os.path.join(dest, name)
        if os.path.isfile(stale):
            os.remove(stale)


def build_root(repo, archive_root, prefix):
    """One GATOR_ROOT: release/ = tree under test, archive-push/ =
    real archive clone, out/<job>/_merge_out/<sweep> = golden."""
    root = tempfile.mkdtemp(prefix=prefix)
    shutil.copytree(repo, os.path.join(root, "release"))
    rc, out = run(["git", "clone", "--quiet", archive_root,
                   os.path.join(root, "archive-push")])
    assert rc == 0, f"archive-push clone failed: {out}"
    workdir = os.path.join(root, "out", JOB["id"])
    sweep_dir = os.path.join(workdir, "_merge_out", SWEEP)
    copy_golden_sweep(archive_root, sweep_dir)
    return root, workdir, sweep_dir


def make_manifest(sweep_rel, merge_status="complete"):
    m = {"job": JOB, "worker": "harness",
         "started": "2026-11-16T14:10:00+00:00",
         "finished": "2026-11-16T14:11:24+00:00",
         "tools": {"yahooquery": "ok"}}
    if merge_status is not None:
        m["merge"] = {"status": merge_status, "sweep_dir": sweep_rel}
    return m


SHIMS = {
    "exit1": ("import sys\n"
              "sys.stderr.write('shim crash\\n')\n"
              "sys.exit(1)\n"),
    "exit0_silent": "import sys\nsys.exit(0)\n",
    "exit0_garbage": ("import sys\n"
                      "open(sys.argv[1]+'/report-model.json','w')"
                      ".write('not json{{{')\n"
                      "sys.exit(0)\n"),
    "exit0_badschema": ("import sys\n"
                        "if '--check-model' in sys.argv:\n"
                        "    sys.exit(2)\n"
                        "open(sys.argv[1]+'/report-model.json','w')"
                        ".write('{}')\n"
                        "sys.exit(0)\n"),
    "sleep": "import time\ntime.sleep(120)\n",
}


def shim_root(repo, archive_root, shim):
    """A GATOR_ROOT whose release/scripts/compile_model.py is a
    corrupted dependency (the seam for crash-class branches)."""
    root, workdir, sweep_dir = build_root(repo, archive_root,
                                          "h68-shim-")
    script = os.path.join(root, "release", "scripts",
                          "compile_model.py")
    with open(script, "w", encoding="utf-8") as handle:
        handle.write(SHIMS[shim])
    return root, workdir, sweep_dir


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Worker-wiring harness for issue #68.")
    ap.add_argument("--repo", default=REPO_DEFAULT)
    ap.add_argument("--archive-root", default=ARCHIVE_DEFAULT)
    ap.add_argument("--pristine", action="store_true")
    ap.add_argument("--keep-stage", action="store_true")
    args = ap.parse_args(argv)
    repo = os.path.abspath(args.repo)

    if args.pristine:
        stage = tempfile.mkdtemp(prefix="h68-worker-wire-pristine-")
        rc, out = run(["git", "clone", "--quiet", repo,
                       os.path.join(stage, "pristine")])
        assert rc == 0, out
        rc, out = run(["git", "checkout", "--quiet", PRISTINE_HEAD],
                      cwd=os.path.join(stage, "pristine"))
        assert rc == 0, out
        worker = import_worker(os.path.join(
            stage, "pristine", "worker", "worker.py"), stage)
        section("pristine control")
        check("maybe_compile absent from pristine worker.py",
              not hasattr(worker, "maybe_compile"))
        try:
            worker.maybe_compile(JOB, stage, make_manifest(SWEEP),
                                 [("yahooquery", "POUL.CA")])
            check("compile sequence fails without the hook", False)
        except AttributeError:
            check("compile sequence fails without the hook", True)
        failed = [c for c in CHECKS if not c[2]]
        print(f"pristine control: {len(CHECKS) - len(failed)}"
              f"/{len(CHECKS)} passed")
        if failed:
            print("pristine control did NOT discriminate")
            return 1
        print("pristine control discriminates: no worker-side "
              "compile without the hook (exit 1 as designed)")
        return 1

    ensure_archive(args.archive_root)
    main_head = git_head(repo)
    assert main_head, "repo under test is not a git checkout"
    os.environ["GATOR_BUS_URL"] = SENTINEL
    plan = [("yahooquery", "POUL.CA")]

    section("fixture")
    root, workdir, sweep_dir = build_root(repo, args.archive_root,
                                          "h68-worker-wire-")
    archive_head = git_head(os.path.join(root, "archive-push"))
    worker = import_worker(os.path.join(repo, "worker", "worker.py"),
                           root)
    for name in ("digest.json", "digest.md", "ensemble.json",
                 "manifest.json", "registry.json", "collected"):
        check(f"golden sweep carries {name}",
              os.path.exists(os.path.join(sweep_dir, name)))
    check("golden sweep carries no pre-existing report-model.json",
          not os.path.isfile(os.path.join(sweep_dir,
                                          "report-model.json")))

    section("golden compile (real compiler, real sweep)")
    check("hook present: worker.maybe_compile exists",
          hasattr(worker, "maybe_compile"))
    manifest = make_manifest(SWEEP)
    ok = worker.maybe_compile(JOB, workdir, manifest, plan)
    model_path = os.path.join(sweep_dir, "report-model.json")
    check("returns True on the golden sweep", ok)
    check("report-model.json written inside the sweep dir",
          os.path.isfile(model_path))
    check("no compile_error.txt after a successful compile",
          not os.path.isfile(os.path.join(sweep_dir,
                                          "compile_error.txt")))
    model = load_json(model_path) if os.path.isfile(model_path) \
        else None
    if model is not None:
        rc, out = run([sys.executable,
                       os.path.join(repo, "scripts",
                                    "compile_model.py"),
                       "--check-model", model_path])
        check("consumer schema check (--check-model) exits 0",
              rc == 0, out[-200:])
        check("model ticker is POUL.CA",
              model.get("ticker") == "POUL.CA")
        check("model archive_commit pins the worker's archive HEAD",
              model.get("archive_commit") == archive_head)
        check("model provenance pins the release checkout HEAD",
              (model.get("provenance") or {}).get("compiler_sha")
              == main_head)
        flags = model.get("flags") or []
        check("golden sweep compiles degraded-with-flags (D-4)",
              len(flags) > 0)
        check("tree-sha-unavailable flag present (sweep dir is not "
              "a git checkout on the worker)",
              any(f.startswith("tree-sha-unavailable") for f in flags))
    comp = manifest.get("compile") or {}
    check("manifest[compile].status is 'compiled'",
          comp.get("status") == "compiled")
    check("manifest[compile] names the sweep dir",
          comp.get("sweep_dir") == SWEEP)
    check("manifest[compile] names the archived model path",
          comp.get("model") == f"{SWEEP}/report-model.json")
    if os.path.isfile(model_path):
        check("manifest[compile].model_sha256 covers the model bytes",
              comp.get("model_sha256") == sha256_file(model_path))
    check("manifest[compile] records the model's flags verbatim",
          comp.get("flags") == (model or {}).get("flags"))
    if os.path.isfile(model_path):
        check("denied GATOR_BUS_URL sentinel absent from the model",
              SENTINEL.encode()
              not in open(model_path, "rb").read())
    try:
        worker._assert_no_denied({"GATOR_BUS_URL": SENTINEL})
        check("_assert_no_denied refuses a denied env", False)
    except AssertionError:
        check("_assert_no_denied refuses a denied env", True)

    section("fail-loudly refusals (real bad input)")
    refusals = {}
    # F-1: ensemble.ticker disagrees with digest.ticker.
    d = os.path.join(root, "out", JOB["id"] + "-f1")
    s = os.path.join(d, "_merge_out", SWEEP)
    shutil.copytree(sweep_dir, s)
    if os.path.isfile(os.path.join(s, "report-model.json")):
        os.remove(os.path.join(s, "report-model.json"))
    digest_bytes = open(os.path.join(s, "digest.json"), "rb").read()
    ens = load_json(os.path.join(s, "ensemble.json"))
    ens["ticker"] = "WRONG.CA"
    with open(os.path.join(s, "ensemble.json"), "w",
              encoding="utf-8") as h:
        json.dump(ens, h)
    refusals["F-1"] = (d, digest_bytes, "ticker mismatch")
    # F-5: collected summary diverges from the digest-embedded one.
    d5 = os.path.join(root, "out", JOB["id"] + "-f5")
    s5 = os.path.join(d5, "_merge_out", SWEEP)
    shutil.copytree(sweep_dir, s5)
    if os.path.isfile(os.path.join(s5, "report-model.json")):
        os.remove(os.path.join(s5, "report-model.json"))
    collected = None
    for dirpath, _dirs, names in os.walk(os.path.join(s5,
                                                      "collected")):
        if "summary.json" in names:
            collected = os.path.join(dirpath, "summary.json")
            break
    assert collected, "no collected summary.json in golden sweep"
    summ = load_json(collected)
    summ["close"] = -12345.0
    with open(collected, "w", encoding="utf-8") as h:
        json.dump(summ, h)
    refusals["F-5"] = (d5, None, "collected summary.json")
    # F-9: a tool status outside the closed vocabulary.
    d9 = os.path.join(root, "out", JOB["id"] + "-f9")
    s9 = os.path.join(d9, "_merge_out", SWEEP)
    shutil.copytree(sweep_dir, s9)
    if os.path.isfile(os.path.join(s9, "report-model.json")):
        os.remove(os.path.join(s9, "report-model.json"))
    dig = load_json(os.path.join(s9, "digest.json"))
    dig["results"][0]["status"] = "bogus-status"
    with open(os.path.join(s9, "digest.json"), "w",
              encoding="utf-8") as h:
        json.dump(dig, h)
    refusals["F-9"] = (d9, None, "unknown digest-row status")
    for name, (rdir, keep_bytes, needle) in refusals.items():
        m = make_manifest(SWEEP)
        ok = worker.maybe_compile(JOB, rdir, m, plan)
        rec = m.get("compile") or {}
        sw = os.path.join(rdir, "_merge_out", SWEEP)
        err = os.path.join(sw, "compile_error.txt")
        check(f"{name}: returns False, status 'refused'",
              not ok and rec.get("status") == "refused")
        check(f"{name}: compile_error.txt names the cause",
              os.path.isfile(err) and needle
              in open(err, encoding="utf-8").read())
        check(f"{name}: no report-model.json left in place (#161)",
              not os.path.isfile(os.path.join(sw,
                                              "report-model.json")))
        if keep_bytes is not None:
            check(f"{name}: digest.json byte-identical (fleet "
                  "intact)", open(os.path.join(sw, "digest.json"),
                                  "rb").read() == keep_bytes)

    section("stale model fail-closed (timeout, crash, bad output)")
    # The timeout branch is covered by the corrupted-release
    # 'sleep' shim below (deterministic seam): a FIFO digest
    # cannot stand in for a slow sweep because the compiler's
    # isfile gate refuses it before any read.
    # Corrupted-release seams: the hook's dependency is the on-disk
    # script; a broken release checkout injects each crash class at
    # the real subprocess boundary with the hook unmodified.
    for shim, expect in (
            ("exit1", "exited 1"),
            ("exit0_silent", "exited 0 but no report-model.json"),
            ("exit0_garbage", "unreadable model"),
            ("exit0_badschema", "failed consumer schema check"),
            ("sleep", "timed out")):
        sroot, swdir, ssweep = shim_root(repo, args.archive_root,
                                         shim)
        stale_model = os.path.join(ssweep, "report-model.json")
        pre_placed = shim != "exit0_silent"
        if pre_placed:
            with open(stale_model, "w", encoding="utf-8") as h:
                h.write('{"stale": true}')
        w = import_worker(os.path.join(repo, "worker", "worker.py"),
                          sroot)
        w.COMPILE_TIMEOUT = 3
        m = make_manifest(SWEEP)
        ok = w.maybe_compile(JOB, swdir, m, plan)
        rec = m.get("compile") or {}
        check(f"shim {shim}: status 'error', detail names the "
              "failure",
              not ok and rec.get("status") == "error"
              and expect in rec.get("detail", ""),
              rec.get("detail", "")[:120])
        if pre_placed:
            check(f"shim {shim}: stale model quarantined, none left",
                  os.path.isfile(stale_model + ".quarantined")
                  and not os.path.isfile(stale_model))
        else:
            check(f"shim {shim}: no model appeared",
                  not os.path.isfile(stale_model))
        check(f"shim {shim}: compile_error.txt marker written",
              os.path.isfile(os.path.join(ssweep,
                                          "compile_error.txt")))
        shutil.rmtree(sroot, ignore_errors=True)

    section("gates (skip / error, never crash)")
    # A stale sweep_dir beside a FAILED merge: dir exists, must not
    # compile.
    m = make_manifest(SWEEP, merge_status="failed")
    ok = worker.maybe_compile(JOB, workdir, m, plan)
    check("failed merge with stale sweep_dir: skipped, no compile",
          not ok and (m.get("compile") or {}).get("status")
          == "skipped")
    m = make_manifest(SWEEP, merge_status="some-future-status")
    ok = worker.maybe_compile(JOB, workdir, m, plan)
    check("unknown merge status: skipped (allowlist, not absence)",
          not ok and (m.get("compile") or {}).get("status")
          == "skipped")
    m = make_manifest("sweeps/2000-01-01/no-such-sweep")
    ok = worker.maybe_compile(JOB, workdir, m, plan)
    check("sweep dir missing on disk: status 'error'",
          not ok and (m.get("compile") or {}).get("status")
          == "error")
    m = make_manifest("../escape")
    ok = worker.maybe_compile(JOB, workdir, m, plan)
    check("sweep_dir with '..': refused as 'error'",
          not ok and (m.get("compile") or {}).get("status")
          == "error")
    outside = tempfile.mkdtemp(prefix="h68-outside-")
    os.symlink(outside, os.path.join(workdir, "_merge_out",
                                     "link_sweep"))
    m = make_manifest("link_sweep")
    ok = worker.maybe_compile(JOB, workdir, m, plan)
    check("sweep_dir through a symlink escaping _merge_out: "
          "refused as 'error'",
          not ok and (m.get("compile") or {}).get("status")
          == "error")
    os.unlink(os.path.join(workdir, "_merge_out", "link_sweep"))
    shutil.rmtree(outside, ignore_errors=True)
    m = make_manifest(123)
    ok = worker.maybe_compile(JOB, workdir, m, plan)
    check("non-string sweep_dir: skipped, no exception", not ok)
    m = {"job": JOB}
    m["merge"] = ["not-a-dict"]
    ok = worker.maybe_compile(JOB, workdir, m, plan)
    check("malformed manifest['merge']: no exception, returns False",
          not ok)
    m_run = {"job": {"id": "x", "job": "run yahooquery POUL.CA"}}
    ok = worker.maybe_compile(m_run["job"], workdir, m_run, plan)
    check("non-sweep job: returns False, no manifest['compile']",
          not ok and "compile" not in m_run)
    ok = worker.maybe_compile(JOB, workdir, make_manifest(SWEEP), None)
    check("no plan: returns False without compiling", not ok)

    section("executed publish proof (local bare remote)")
    bare = os.path.join(root, "bus.git")
    rc, out = run(["git", "clone", "--quiet", "--bare",
                   args.archive_root, bare])
    assert rc == 0, out
    os.environ["GATOR_BUS_URL"] = bare

    def run_publish_case(tag, tamper, plant_quarantine=False,
                         doctor=None):
        proot = tempfile.mkdtemp(prefix=f"h68-pub-{tag}-")
        shutil.copytree(repo, os.path.join(proot, "release"))
        rc, out = run(["git", "clone", "--quiet", bare,
                       os.path.join(proot, "archive-push")])
        assert rc == 0, out
        pw = import_worker(os.path.join(repo, "worker", "worker.py"),
                           proot)
        workdir = os.path.join(proot, "out", JOB["id"])
        sw = os.path.join(workdir, "_merge_out", SWEEP)
        copy_golden_sweep(args.archive_root, sw)
        # a fleet artifact beside the merge tree
        os.makedirs(os.path.join(workdir, "yahooquery"),
                    exist_ok=True)
        with open(os.path.join(workdir, "yahooquery",
                               "summary.json"), "w") as h:
            h.write("{}")
        with open(os.path.join(workdir, "yahooquery.log"),
                  "w") as h:
            h.write("log")
        if tamper:
            ens = load_json(os.path.join(sw, "ensemble.json"))
            ens["ticker"] = "WRONG.CA"
            with open(os.path.join(sw, "ensemble.json"), "w") as h:
                json.dump(ens, h)
        if plant_quarantine:
            # a stale #161 artifact beside the merge output
            with open(os.path.join(
                    sw, "report-model.json.quarantined"), "w") as h:
                h.write("{}")
        manifest = make_manifest(SWEEP)
        workdir = Path(workdir)
        pw._write_manifest_atomic(workdir, manifest)
        compiled = pw.maybe_compile(JOB, workdir, manifest, plan)
        pw._write_manifest_atomic(workdir, manifest)
        if doctor is not None:
            doctor(manifest)
            pw._write_manifest_atomic(workdir, manifest)
        sha = pw.publish(JOB, workdir, manifest)
        return proot, sw, manifest, compiled, sha

    proot, sw, pmanifest, compiled, sha = run_publish_case(
        "ok", False, plant_quarantine=True)
    check("compiled case: maybe_compile True, publish returns a "
          "SHA", compiled and bool(sha))
    if sha:
        rc, out = run(["git", "--git-dir", bare, "show",
                       "--name-only", "--format=", sha])
        names = out.split()
        check("one commit carries BOTH the model and the fleet "
              "(same-commit proof)",
              f"{SWEEP}/report-model.json" in names
              and any(n.startswith("worker-runs/")
                      and n.endswith("manifest.json") for n in names))
        rc, out = run(["git", "--git-dir", bare, "show",
                       f"{sha}:{SWEEP}/report-model.json"])
        check("archived model bytes hash to the manifest's "
              "model_sha256",
              hashlib.sha256(out.encode()).hexdigest()
              == (pmanifest.get("compile") or {})
              .get("model_sha256"))
        rc_q, _ = run(["git", "--git-dir", bare, "cat-file", "-e",
                       f"{sha}:{SWEEP}/report-model.json.quarantined"])
        check(".quarantined artifact excluded from the archive "
              "(matches the Actions wiring's selective copy)",
              rc_q != 0)
        run_manifest = None
        for n in names:
            if n.startswith("worker-runs/") \
                    and n.endswith("manifest.json"):
                rc, out = run(["git", "--git-dir", bare, "show",
                               f"{sha}:{n}"])
                run_manifest = json.loads(out)
        check("archived run manifest carries the compile block",
              (run_manifest or {}).get("compile", {}).get("status")
              == "compiled")
        rc, out = run(["git", "--git-dir", bare, "show",
                       f"{sha}:{SWEEP}/manifest.json"])
        files = (json.loads(out).get("files")
                 if rc == 0 else None)
        check("merge sweep manifest files[] predates the model "
              "(documented ambiguity, run manifest carries the "
              "hash)", files is None or not any(
                  f.get("path") == "report-model.json"
                  for f in files))
    proot2, sw2, pmanifest2, compiled2, sha2 = \
        run_publish_case("refused", True)
    check("refusal case: maybe_compile False, publish STILL "
          "returns a SHA", not compiled2 and bool(sha2))
    if sha2:
        rc, out = run(["git", "--git-dir", bare, "show",
                       "--name-status", "--format=", sha2])
        check("refusal commit DELETES the prior commit's model "
              "(cp never deletes; the default drop must)",
              f"D\t{SWEEP}/report-model.json" in out)
        rc_m, _ = run(["git", "--git-dir", bare, "cat-file", "-e",
                       f"{sha2}:{SWEEP}/report-model.json"])
        rc_e, _ = run(["git", "--git-dir", bare, "cat-file", "-e",
                       f"{sha2}:{SWEEP}/compile_error.txt"])
        rc_f, _ = run(["git", "--git-dir", bare, "cat-file", "-e",
                       f"{sha2}:{SWEEP}/digest.json"])
        check("refusal tree: model ABSENT (tree-level, after a "
              "success at the same path), marker + fleet present",
              rc_m != 0 and rc_e == 0 and rc_f == 0,
              detail=f"model-rc={rc_m} marker-rc={rc_e} "
                     f"digest-rc={rc_f}")
        check("refusal run manifest records status 'refused'",
              (pmanifest2.get("compile") or {}).get("status")
              == "refused")
    # success after a refusal at the same path: the new model must
    # land AND the prior commit's stale marker must be dropped
    # (the compiler clears the local marker; the archive side is
    # publish's).
    proot3, sw3, pmanifest3, compiled3, sha3 =         run_publish_case("ok-after-refusal", False)
    check("ok-after-refusal: compile True, publish returns a SHA",
          compiled3 and bool(sha3))
    if sha3:
        rc_m, _ = run(["git", "--git-dir", bare, "cat-file", "-e",
                       f"{sha3}:{SWEEP}/report-model.json"])
        rc_e, _ = run(["git", "--git-dir", bare, "cat-file", "-e",
                       f"{sha3}:{SWEEP}/compile_error.txt"])
        check("ok-after-refusal tree: model present, stale "
              "compile_error.txt dropped",
              rc_m == 0 and rc_e != 0,
              detail=f"model-rc={rc_m} marker-rc={rc_e}")
    shutil.rmtree(proot, ignore_errors=True)
    shutil.rmtree(proot2, ignore_errors=True)
    shutil.rmtree(proot3, ignore_errors=True)

    # Suppression safety: an invalid suppress_model path or a
    # failed destination unlink must REFUSE the publish (truthful
    # False, no commit) — never let an unchecked model ride a green
    # commit, never remove anything but the recorded sweep's model.
    rc, out = run(["git", "--git-dir", bare, "rev-parse", "HEAD"])
    head_before_supp = out.strip()

    def doctor_suppress(value):
        def _d(m):
            # a non-compiled outcome carrying the suppression handoff
            m["compile"]["status"] = "error"
            m["compile"]["suppress_model"] = value
        return _d

    def doctor_no_sweep(m):
        m["compile"] = {"status": "error",
                        "suppress_model":
                        f"{SWEEP}/report-model.json"}

    def doctor_compiled_with_suppress(m):
        m["compile"]["status"] = "compiled"
        m["compile"]["suppress_model"] = (
            f"{SWEEP}/report-model.json")

    invalid = [
        ("dotdot", doctor_suppress("../digest.json")),
        ("absolute", doctor_suppress("/etc/passwd")),
        ("other-file", doctor_suppress(f"{SWEEP}/digest.json")),
        ("no-sweep-dir", doctor_no_sweep),
        ("compiled-with-suppress", doctor_compiled_with_suppress),
    ]
    for tag, doctor in invalid:
        px, swx, mx, cx, shax = run_publish_case(f"supp-{tag}",
                                                 False,
                                                 doctor=doctor)
        rc, out = run(["git", "--git-dir", bare, "rev-parse",
                       "HEAD"])
        check(f"invalid suppress ({tag}): publish refuses "
              f"(False), no commit",
              not shax and out.strip() == head_before_supp)
        if tag == "other-file":
            check("invalid suppress: the mis-named fleet file "
                  "survives in the checkout",
                  os.path.isfile(os.path.join(
                      px, "archive-push", SWEEP, "digest.json")))
        shutil.rmtree(px, ignore_errors=True)

    # Destination unlink failure (failure-injection seam:
    # Path.unlink patched to raise for the model path only, restored
    # immediately — the only mock here; os.unlink is bypassed by
    # pathlib on this Python, so the patch targets Path.unlink).
    import pathlib as _pathlib
    real_unlink = _pathlib.Path.unlink

    def _failing_unlink(self, *a, **k):
        if str(self).endswith("report-model.json"):
            raise PermissionError(
                "injected destination unlink failure")
        return real_unlink(self, *a, **k)

    _pathlib.Path.unlink = _failing_unlink
    try:
        px, swx, mx, cx, shax = run_publish_case(
            "supp-unlink-fails", False,
            doctor=doctor_suppress(f"{SWEEP}/report-model.json"))
    finally:
        _pathlib.Path.unlink = real_unlink
    rc, out = run(["git", "--git-dir", bare, "rev-parse", "HEAD"])
    check("destination unlink failure: publish refuses (False), "
          "no commit",
          not shax and out.strip() == head_before_supp)
    check("destination unlink failure: model still in the "
          "checkout (removal honestly not claimed)",
          os.path.isfile(os.path.join(
              px, "archive-push", SWEEP, "report-model.json")))
    shutil.rmtree(px, ignore_errors=True)
    os.environ["GATOR_BUS_URL"] = SENTINEL

    section("gates: base itself and absolute paths")
    m = make_manifest(".")
    ok = worker.maybe_compile(JOB, workdir, m, plan)
    check("sweep_dir '.' (the base itself): refused as 'error'",
          not ok and (m.get("compile") or {}).get("status")
          == "error")
    abs_inside = os.path.join(workdir, "_merge_out", SWEEP)
    m = make_manifest(abs_inside)
    ok = worker.maybe_compile(JOB, workdir, m, plan)
    check("absolute sweep_dir even inside base: refused as 'error'",
          not ok and (m.get("compile") or {}).get("status")
          == "error")

    section("cleanup failure: suppression at publish (forced)")
    sroot, swdir, ssweep = shim_root(repo, args.archive_root,
                                     "exit1")
    stale_model = os.path.join(ssweep, "report-model.json")
    with open(stale_model, "w", encoding="utf-8") as h:
        h.write('{"stale": true}')
    w = import_worker(os.path.join(repo, "worker", "worker.py"),
                      sroot)
    # force quarantine AND removal to fail: read-only sweep dir
    os.chmod(ssweep, 0o555)
    m = make_manifest(SWEEP)
    ok = w.maybe_compile(JOB, swdir, m, plan)
    rec = m.get("compile") or {}
    check("cleanup failed: status 'error', cleanup_failed evidence "
          "recorded",
          not ok and rec.get("status") == "error"
          and bool(rec.get("cleanup_failed")))
    check("cleanup failed: suppress_model path recorded",
          rec.get("suppress_model") == f"{SWEEP}/report-model.json")
    check("cleanup failed: marker_write_failed evidence recorded",
          bool(rec.get("marker_write_failed")))
    check("cleanup failed: unquarantinable model still on disk "
          "(honest, not claimed removed)",
          os.path.isfile(stale_model))
    os.chmod(ssweep, 0o755)
    # publish with that manifest must drop the unvalidated model
    # while preserving the fleet; remove the pre-existing
    # archive-push clone (used for the pin above) so publish clones
    # fresh from the bare bus.
    shutil.rmtree(os.path.join(sroot, "archive-push"),
                  ignore_errors=True)
    bare2 = os.path.join(sroot, "bus.git")
    rc, out = run(["git", "clone", "--quiet", "--bare",
                   args.archive_root, bare2])
    assert rc == 0, out
    os.environ["GATOR_BUS_URL"] = bare2
    with open(os.path.join(swdir, "yahooquery.log"), "w") as h:
        h.write("log")
    w._write_manifest_atomic(swdir, m)
    sha = w.publish(JOB, Path(swdir), m)
    check("cleanup failed: publish still lands (fleet preserved)",
          bool(sha))
    if sha:
        # The golden sweep path is already tracked in the archive
        # history, so suppression shows up as a DELETION in the
        # commit's name list. The real assertion is tree state:
        # the model must be ABSENT from the committed tree while a
        # fleet file is present.
        rc_m, _ = run(["git", "--git-dir", bare2, "cat-file", "-e",
                       f"{sha}:{SWEEP}/report-model.json"])
        rc_f, _ = run(["git", "--git-dir", bare2, "cat-file", "-e",
                       f"{sha}:{SWEEP}/digest.json"])
        check("suppressed model absent from the committed tree, "
              "fleet (digest) present",
              rc_m != 0 and rc_f == 0,
              detail=f"model-rc={rc_m} digest-rc={rc_f}")
    shutil.rmtree(sroot, ignore_errors=True)
    os.environ["GATOR_BUS_URL"] = SENTINEL

    section("end-to-end _execute_body (real orchestration)")
    # Seams, clearly identified: run_tool (external tool execution:
    # network, runner repos, venvs) serves the golden sweep's
    # collected outputs; _mark_done (bus write) records the call.
    # Everything else is real: registry, parse_job, manifest writes,
    # maybe_merge (real merge.py + real ensemble.py), maybe_compile
    # (real compile_model.py), publish (real, against a local bare
    # remote standing in for the bus).
    def run_execute_body(tag, mutate_hook, tamper_tool):
        eroot = tempfile.mkdtemp(prefix=f"h68-e2e-{tag}-")
        shutil.copytree(repo, os.path.join(eroot, "release"))
        src_file = os.path.join(eroot, "release", "worker",
                                "worker.py")
        if mutate_hook:
            src_text = open(src_file, encoding="utf-8").read()
            call = "    maybe_compile(job, workdir, manifest, plan)\n"
            # Under the M1 mutant tree the call is already absent;
            # the bypass case then exercises the same tree.
            if call in src_text:
                src_text = src_text.replace(call, "", 1)
            with open(src_file, "w", encoding="utf-8") as h:
                h.write(src_text)
        bare = os.path.join(eroot, "bus.git")
        rc, out = run(["git", "clone", "--quiet", "--bare",
                       args.archive_root, bare])
        assert rc == 0, out
        os.environ["GATOR_BUS_URL"] = bare
        w = import_worker(src_file, eroot)
        calls = {"done": []}

        def run_tool_seam(tool, ticker, *a):
            src_dir = os.path.join(args.archive_root, SWEEP,
                                   "collected", tool)
            results = os.path.join(eroot, "runners", tool,
                                   "results")
            if os.path.isdir(src_dir):
                os.makedirs(results, exist_ok=True)
                for f in os.listdir(src_dir):
                    shutil.copy2(os.path.join(src_dir, f),
                                 os.path.join(results, f))
                if tamper_tool == tool:
                    # Real bad-input refusal: corrupt this tool's
                    # price series (every close x1.5) so the F-1
                    # tripwire (check 3, price_series_last) refuses
                    # the compile. Exactly one corrupt source
                    # breaks the 25% agreement band whichever tool
                    # the ensemble base comes from.
                    import csv as _csv
                    for cpath in glob.glob(os.path.join(
                            results, "*.csv")):
                        with open(cpath, newline="") as h:
                            rows = list(_csv.reader(h))
                        if len(rows) < 6:
                            continue
                        hdr = [c.strip().lower() for c in rows[0]]
                        ci = next((i for i, c in enumerate(hdr)
                                   if c in ("close", "adj close",
                                            "adjclose")), None)
                        if ci is None:
                            continue
                        for r in rows[1:]:
                            if ci < len(r):
                                try:
                                    r[ci] = str(float(r[ci]) * 1.5)
                                except (ValueError, TypeError):
                                    pass
                        with open(cpath, "w", newline="") as h:
                            _csv.writer(h).writerows(rows)
                return "ok", "seam log"
            return "failed", "seam: no fixture for tool"

        def mark_done_seam(job, archive_sha):
            calls["done"].append((job["id"], archive_sha))

        w.run_tool = run_tool_seam
        w._mark_done = mark_done_seam
        job = {"id": f"h68-e2e-{tag}", "added": "2026-11-19",
               "job": "sweep-lite POUL.CA market=EGX"}
        w._execute_body(job)
        return eroot, bare, w, calls, job

    eroot, bare, w, calls, job = run_execute_body("ok", False, None)
    outdir = os.path.join(eroot, "out", job["id"])
    e_manifest = load_json(os.path.join(outdir, "manifest.json"))
    e_sweep = (e_manifest.get("merge") or {}).get("sweep_dir")
    check("e2e: merge succeeded and named a sweep dir",
          bool(e_sweep))
    check("e2e: compile block status 'compiled'",
          (e_manifest.get("compile") or {}).get("status")
          == "compiled")
    done_sha = calls["done"][-1][1] if calls["done"] else None
    check("e2e: job marked done with an archive SHA (publish "
          "landed)", bool(done_sha))
    if done_sha and e_sweep:
        rc, out = run(["git", "--git-dir", bare, "show",
                       "--name-only", "--format=", done_sha])
        names = out.split()
        check("e2e: ONE commit carries model + fleet + merge",
              f"{e_sweep}/report-model.json" in names
              and f"{e_sweep}/digest.json" in names
              and any(n.startswith("worker-runs/") for n in names))
        rc, out = run(["git", "--git-dir", bare, "show",
                       f"{done_sha}:{e_sweep}/report-model.json"])
        check("e2e: archived model passes --check-model", True
              if rc == 0 else False)
        if rc == 0:
            mpath = os.path.join(eroot, "archived-model.json")
            with open(mpath, "w") as h:
                h.write(out)
            rc2, out2 = run([sys.executable,
                             os.path.join(
                                 repo, "scripts", "compile_model.py"),
                             "--check-model", mpath])
            check("e2e: archived model validates as v1 schema",
                  rc2 == 0, out2[-160:])
            check("e2e: archived model bytes hash to manifest "
                  "model_sha256",
                  hashlib.sha256(out.encode()).hexdigest()
                  == (e_manifest.get("compile") or {})
                  .get("model_sha256"))
    shutil.rmtree(eroot, ignore_errors=True)

    eroot, bare, w, calls, job = run_execute_body("bypass", True,
                                                  None)
    outdir = os.path.join(eroot, "out", job["id"])
    e_manifest = load_json(os.path.join(outdir, "manifest.json"))
    e_sweep = (e_manifest.get("merge") or {}).get("sweep_dir")
    done_sha = calls["done"][-1][1] if calls["done"] else None
    check("e2e hook-bypassed: fleet + merge still publish, job "
          "done", bool(done_sha) and bool(e_sweep))
    check("e2e hook-bypassed: no compile block recorded",
          "compile" not in e_manifest)
    if done_sha and e_sweep:
        rc, out = run(["git", "--git-dir", bare, "show",
                       "--name-only", "--format=", done_sha])
        names = out.split()
        check("e2e hook-bypassed: NO report-model.json in the "
              "commit (the mutation is caught)",
              f"{e_sweep}/report-model.json" not in names
              and f"{e_sweep}/digest.json" in names)
    shutil.rmtree(eroot, ignore_errors=True)

    eroot, bare, w, calls, job = run_execute_body("refused", False,
                                                  "openbb")
    outdir = os.path.join(eroot, "out", job["id"])
    e_manifest = load_json(os.path.join(outdir, "manifest.json"))
    e_sweep = (e_manifest.get("merge") or {}).get("sweep_dir")
    done_sha = calls["done"][-1][1] if calls["done"] else None
    check("e2e forced-refusal (F-1 price-series corruption): "
          "compile block status 'refused'",
          (e_manifest.get("compile") or {}).get("status")
          == "refused",
          detail=str(e_manifest.get("compile")))
    check("e2e forced-refusal: fleet still publishes, job done",
          bool(done_sha) and bool(e_sweep))
    if done_sha and e_sweep:
        rc_m, _ = run(["git", "--git-dir", bare, "cat-file", "-e",
                       f"{done_sha}:{e_sweep}/report-model.json"])
        rc_e, _ = run(["git", "--git-dir", bare, "cat-file", "-e",
                       f"{done_sha}:{e_sweep}/compile_error.txt"])
        rc_f, _ = run(["git", "--git-dir", bare, "cat-file", "-e",
                       f"{done_sha}:{e_sweep}/digest.json"])
        check("e2e forced-refusal: tree carries compile_error.txt"
              " + fleet, model ABSENT (tree-level)",
              rc_m != 0 and rc_e == 0 and rc_f == 0,
              detail=f"model-rc={rc_m} marker-rc={rc_e} "
                     f"digest-rc={rc_f}")
    shutil.rmtree(eroot, ignore_errors=True)
    os.environ["GATOR_BUS_URL"] = SENTINEL

    section("wiring source assertions (no mocks)")
    src = open(os.path.join(repo, "worker", "worker.py"),
               encoding="utf-8").read()
    i_merge = src.find("\n    maybe_merge(job, workdir, manifest, plan)")
    i_compile = src.find(
        "\n    maybe_compile(job, workdir, manifest, plan)")
    i_manifest2 = src.find("_write_manifest_atomic(workdir, manifest)",
                           i_merge)
    i_publish = src.find("archive_sha = publish(job, workdir, manifest)",
                         i_manifest2)
    check("call order: maybe_merge < maybe_compile < second "
          "_write_manifest_atomic < publish in _execute_body",
          -1 < i_merge < i_compile < i_manifest2 < i_publish)
    check("hook filters ENV_DENY_FOR_TOOLS and asserts the boundary",
          "if k not in ENV_DENY_FOR_TOOLS" in src
          and "_assert_no_denied(env)" in src)
    check("archive pin is direct argv git, no shell interpolation",
          '["git", "-C", str(arch), "rev-parse", "HEAD"]' in src)
    check("hook runs the compiler with a named bounded timeout",
          "COMPILE_TIMEOUT = 1800" in src
          and "timeout=COMPILE_TIMEOUT" in src)
    check("publish suppression is validated pathlib removal, "
          "refuses on failure, no shell",
          'target.unlink()' in src
          and 'suppress != f"{sweep_rel}/report-model.json"' in src
          and 'rm -f {arch}/' not in src)
    check("fail-closed tail quarantines a surviving model and "
          "writes the marker",
          'os.replace(stale, str(stale) + ".quarantined")' in src
          and 'marker.write_text(' in src)

    failed = [c for c in CHECKS if not c[2]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    if not args.keep_stage:
        shutil.rmtree(root, ignore_errors=True)
    else:
        print(f"stage kept: {root}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
