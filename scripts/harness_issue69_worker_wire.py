#!/usr/bin/env python3
"""Worker-wiring harness for issue #69 (deterministic report renderer,
worker-path ``maybe_render`` hook in ``worker/worker.py``).

Proves the worker hook works, harness-first with a pristine control —
same discipline as ``harness_issue68_worker_wire.py`` (which covered
the ``maybe_compile`` hook).

What it exercises, with the REAL ``maybe_render`` imported from the
worker tree under test, the REAL ``scripts/compile_model.py`` and the
REAL ``scripts/render.py``:
  1. A worker-style run dir under a temporary GATOR_ROOT:
     ``out/<job-id>/_merge_out/<sweep_dir>`` carries the golden sweep
     141124 from the ``archive`` branch in the shape ``merge.py``
     produces, and ``manifest["merge"]`` names it with status
     complete. The hook runs ``maybe_compile`` first (real compiler),
     then ``maybe_render`` — the production order.
  2. ``release/`` is a copy of the repo tree under test (the worker's
     CODE checkout) and ``archive-push/`` a real clone of the
     ``archive`` branch, so ``--compiler-sha`` and ``--archive-sha``
     resolve exactly as in production.
  3. I-5 fallback verdict: the live model carries no IR-3 chart
     fields, so the chart comes from ``--sweep-dir`` CSVs. Rendering
     the golden model with ``--sweep-dir`` must produce an inline SVG
     chart; without it the section must degrade to the
     price-series table — never a faked chart.
  4. Refusal / crash branches: a schema-v99 model (real renderer
     refusal, exit 2), a profile-mismatch model, and corrupted-
     release shims for ``render.py`` (exit 1, exit 0 silent, exit 0
     twins without the data island, hang). Every non-rendered
     outcome must leave no twins in place, write render_error.txt,
     record ``manifest["render"]``, and still publish the fleet.
  5. The publish proof is EXECUTED, not inferred: ``publish()``
     runs against a local bare repo standing in for the bus remote,
     once after a real compile+render (twins in the same commit as
     the model and the fleet), once after a real render refusal
     (render_error.txt and no twins in the commit), once after a
     render success at the same path (twins land, stale marker
     dropped), and once after a compile refusal (model AND twins
     dropped, fleet intact).
  6. Fixed mode exits 0 only when every check passes. --pristine:
     the worker tree is the base WITHOUT the hook (main
     ``e41c22b``, the renderer merge); the control must show
     ``maybe_render`` absent and the render sequence failing,
     then exits 1 — the control discriminates.

Local only, stdlib only. No network beyond the one-time ``archive``
branch clone, no GitHub API, no live worker, no real bus.

Usage:
    harness_issue69_worker_wire.py [--repo PATH] [--archive-root PATH]
                                   [--pristine] [--keep-stage]
"""
import argparse
from pathlib import Path
import hashlib
import importlib.util
import json
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
                 "borsagator-69-worker-wire-archive"))

SWEEP = ("sweeps/2026-11-16/141124__sweep-lite-poul-ca__"
         "run43875894633")
JOB = {"id": "h69-worker-wire", "job": "sweep-lite POUL.CA market=EGX"}
SENTINEL = "SENTINEL-BUS-URL-VALUE"
# The pristine base the hook was built against: main at the renderer
# merge (PR #252, 8eec120) plus the guard heartbeat (e41c22b) — the
# hook does not exist there yet.
PRISTINE_HEAD = "e41c22b658cd4893bdc759fbd8eabf1e519e1165"

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
    model, no error marker, no report twins: merge.py output never
    carries them)."""
    shutil.copytree(os.path.join(archive_root, SWEEP), dest)
    for name in ("report-model.json", "report-model.json.quarantined",
                 "compile_error.txt", "report.html", "report.md",
                 "render_error.txt"):
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
    "exit0_no_island": ("import sys, os\n"
                        "d = sys.argv[sys.argv.index('--out-dir') + 1] "
                        "if '--out-dir' in sys.argv else sys.argv[1]\n"
                        "open(os.path.join(d, 'report.html'), 'w').write("
                        "'<html><body>no island</body></html>')\n"
                        "open(os.path.join(d, 'report.md'), 'w').write("
                        "'# report\\n')\n"
                        "sys.exit(0)\n"),
    "sleep": "import time\ntime.sleep(120)\n",
}


def shim_root(repo, archive_root, shim):
    """A GATOR_ROOT whose release/scripts/render.py is a corrupted
    dependency (the seam for crash-class branches). The sweep dir
    already carries a compiled model: the hook under test is
    unmodified, the fault is injected at the real subprocess
    boundary."""
    root, workdir, sweep_dir = build_root(repo, archive_root,
                                          "h69-shim-")
    script = os.path.join(root, "release", "scripts", "render.py")
    with open(script, "w", encoding="utf-8") as handle:
        handle.write(SHIMS[shim])
    return root, workdir, sweep_dir


def compile_and_render(worker, workdir, manifest, plan):
    """Production order: compile, then render. Returns
    (compiled, rendered)."""
    compiled = worker.maybe_compile(JOB, workdir, manifest, plan)
    rendered = worker.maybe_render(JOB, workdir, manifest, plan)
    return compiled, rendered


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Worker-wiring harness for issue #69.")
    ap.add_argument("--repo", default=REPO_DEFAULT)
    ap.add_argument("--archive-root", default=ARCHIVE_DEFAULT)
    ap.add_argument("--pristine", action="store_true")
    ap.add_argument("--keep-stage", action="store_true")
    args = ap.parse_args(argv)
    repo = os.path.abspath(args.repo)

    # Never stage in /tmp (512M tmpfs fills on the archive clone):
    # stage under the archive root's parent unless TMPDIR names a
    # roomier dir.
    tmp_base = os.environ.get("TMPDIR")
    if not tmp_base or os.path.abspath(tmp_base) == "/tmp":
        tmp_base = os.path.join(
            os.path.dirname(os.path.abspath(args.archive_root)),
            "h69-worker-wire-tmp")
    os.makedirs(tmp_base, exist_ok=True)
    tempfile.tempdir = tmp_base

    if args.pristine:
        stage = tempfile.mkdtemp(prefix="h69-worker-wire-pristine-")
        rc, out = run(["git", "clone", "--quiet", repo,
                       os.path.join(stage, "pristine")])
        assert rc == 0, out
        rc, out = run(["git", "checkout", "--quiet", PRISTINE_HEAD],
                      cwd=os.path.join(stage, "pristine"))
        assert rc == 0, out
        worker = import_worker(os.path.join(
            stage, "pristine", "worker", "worker.py"), stage)
        section("pristine control")
        check("maybe_render absent from pristine worker.py",
              not hasattr(worker, "maybe_render"))
        try:
            worker.maybe_render(JOB, stage, make_manifest(SWEEP),
                                [("yahooquery", "POUL.CA")])
            check("render sequence fails without the hook", False)
        except AttributeError:
            check("render sequence fails without the hook", True)
        failed = [c for c in CHECKS if not c[2]]
        print(f"pristine control: {len(CHECKS) - len(failed)}"
              f"/{len(CHECKS)} passed")
        if failed:
            print("pristine control did NOT discriminate")
            return 1
        print("pristine control discriminates: no worker-side "
              "render without the hook (exit 1 as designed)")
        return 1

    ensure_archive(args.archive_root)
    main_head = git_head(repo)
    assert main_head, "repo under test is not a git checkout"
    os.environ["GATOR_BUS_URL"] = SENTINEL
    plan = [("yahooquery", "POUL.CA")]

    section("fixture")
    root, workdir, sweep_dir = build_root(repo, args.archive_root,
                                          "h69-worker-wire-")
    worker = import_worker(os.path.join(repo, "worker", "worker.py"),
                           root)
    for name in ("digest.json", "digest.md", "ensemble.json",
                 "manifest.json", "registry.json", "collected"):
        check(f"golden sweep carries {name}",
              os.path.exists(os.path.join(sweep_dir, name)))
    check("golden sweep carries no pre-existing report-model.json",
          not os.path.isfile(os.path.join(sweep_dir,
                                          "report-model.json")))
    check("golden sweep carries no pre-existing report twins",
          not os.path.isfile(os.path.join(sweep_dir, "report.html"))
          and not os.path.isfile(os.path.join(sweep_dir,
                                              "report.md")))

    section("golden render (real compile, real render, real sweep)")
    check("hook present: worker.maybe_render exists",
          hasattr(worker, "maybe_render"))
    manifest = make_manifest(SWEEP)
    compiled, rendered = compile_and_render(worker, workdir,
                                            manifest, plan)
    html_path = os.path.join(sweep_dir, "report.html")
    md_path = os.path.join(sweep_dir, "report.md")
    check("maybe_compile True on the golden sweep", compiled)
    check("maybe_render True on the golden sweep", rendered)
    check("report.html written inside the sweep dir",
          os.path.isfile(html_path))
    check("report.md written inside the sweep dir",
          os.path.isfile(md_path))
    check("no render_error.txt after a successful render",
          not os.path.isfile(os.path.join(sweep_dir,
                                          "render_error.txt")))
    html_blob = open(html_path, "rb").read() \
        if os.path.isfile(html_path) else b""
    md_blob = open(md_path, "rb").read() \
        if os.path.isfile(md_path) else b""
    check("HTML carries the model data island",
          b'id="report-model"' in html_blob)
    check("HTML chart is inline SVG (I-5 fallback fired)",
          b'aria-label="Price chart"' in html_blob
          and b"<svg" in html_blob)
    check("MD twin carries the D2 bands (support 7.13 / "
          "resistance 11.59)",
          b"7.13" in md_blob and b"11.59" in md_blob)
    check("MD twin carries the disagreement headline",
          b"Families disagree" in md_blob)
    check("no imperative recommendation line in the MD twin",
          b"buy at/below" not in md_blob
          and b"sell/trim at/above" not in md_blob)
    rec = manifest.get("render") or {}
    check("manifest[render].status is 'rendered'",
          rec.get("status") == "rendered")
    check("manifest[render] names the sweep dir",
          rec.get("sweep_dir") == SWEEP)
    check("manifest[render] records chart 'svg'",
          rec.get("chart") == "svg")
    check("manifest[render] records the I-5 sweep-dir fallback",
          rec.get("sweep_dir_fallback") is True)
    files = rec.get("files") or []
    check("manifest[render] lists both twins",
          sorted(f.get("path") for f in files)
          == ["report.html", "report.md"])
    if os.path.isfile(html_path) and os.path.isfile(md_path):
        by_path = {f["path"]: f for f in files}
        check("manifest[render] SHAs cover the twin bytes",
              by_path.get("report.html", {}).get("sha256")
              == sha256_file(html_path)
              and by_path.get("report.md", {}).get("sha256")
              == sha256_file(md_path))
    sweep_manifest = load_json(os.path.join(sweep_dir,
                                            "manifest.json"))
    mfiles = sweep_manifest.get("files") or []
    mby = {f.get("path"): f for f in mfiles
           if isinstance(f, dict)}
    check("sweep manifest.json files[] lists report.html",
          "report.html" in mby
          and mby["report.html"].get("sha256")
          == sha256_file(html_path) if os.path.isfile(html_path)
          else False)
    check("sweep manifest.json files[] lists report.md",
          "report.md" in mby
          and mby["report.md"].get("sha256")
          == sha256_file(md_path) if os.path.isfile(md_path)
          else False)
    check("sweep manifest files[] append recorded",
          rec.get("files_appended") is True)
    check("denied GATOR_BUS_URL sentinel absent from report.html",
          SENTINEL.encode() not in html_blob)

    section("I-5 fallback verdict (direct renderer calls)")
    model_path = os.path.join(sweep_dir, "report-model.json")
    model = load_json(model_path)
    check("live model carries NO IR-3 chart fields (fallback "
          "required, not optional)",
          "price_series_tail" not in model
          and "kronos_forecast" not in model)
    out_nodir = os.path.join(root, "out", "render-nodir")
    rc, out = run([sys.executable,
                   os.path.join(repo, "scripts", "render.py"),
                   model_path,
                   "--profile",
                   os.path.join(repo, "profiles", "POUL.CA.json"),
                   "--out-dir", out_nodir])
    check("render without --sweep-dir exits 0 (degraded chart)",
          rc == 0, out[-200:])
    nodir_html = open(os.path.join(out_nodir, "report.html"),
                      encoding="utf-8").read() \
        if rc == 0 else ""
    check("without --sweep-dir the chart degrades to the "
          "price-series table, never a faked chart",
          "<svg" not in nodir_html
          and "Chart data unavailable" in nodir_html)
    out_dir = os.path.join(root, "out", "render-withdir")
    rc, out = run([sys.executable,
                   os.path.join(repo, "scripts", "render.py"),
                   model_path,
                   "--profile",
                   os.path.join(repo, "profiles", "POUL.CA.json"),
                   "--sweep-dir", sweep_dir,
                   "--out-dir", out_dir])
    check("render with --sweep-dir exits 0", rc == 0, out[-200:])
    withdir_html = open(os.path.join(out_dir, "report.html"),
                        encoding="utf-8").read() if rc == 0 else ""
    check("with --sweep-dir the chart is inline SVG from the "
          "sweep CSVs",
          "<svg" in withdir_html
          and 'aria-label="Price chart"' in withdir_html)
    check("fallback render is byte-identical to the hook's twins",
          open(os.path.join(out_dir, "report.html"), "rb").read()
          == html_blob
          and open(os.path.join(out_dir, "report.md"), "rb").read()
          == md_blob)

    section("render refusal (real bad model, fleet intact)")
    # Schema-v99 model: the renderer refuses (exit 2); the hook
    # must record 'refused', leave no twins, write the marker.
    d = os.path.join(root, "out", JOB["id"] + "-refused")
    s = os.path.join(d, "_merge_out", SWEEP)
    shutil.copytree(sweep_dir, s)
    for name in ("report.html", "report.md", "render_error.txt"):
        p = os.path.join(s, name)
        if os.path.isfile(p):
            os.remove(p)
    bad = load_json(os.path.join(s, "report-model.json"))
    bad["schema"] = "borsagator-report-model/99"
    with open(os.path.join(s, "report-model.json"), "w",
              encoding="utf-8") as h:
        json.dump(bad, h)
    m = make_manifest(SWEEP)
    m["compile"] = {"status": "compiled", "sweep_dir": SWEEP}
    ok = worker.maybe_render(JOB, d, m, plan)
    rec = m.get("render") or {}
    check("schema-v99: returns False, status 'refused'",
          not ok and rec.get("status") == "refused")
    check("schema-v99: no report.html left in place",
          not os.path.isfile(os.path.join(s, "report.html")))
    check("schema-v99: no report.md left in place",
          not os.path.isfile(os.path.join(s, "report.md")))
    err = os.path.join(s, "render_error.txt")
    check("schema-v99: render_error.txt names the cause",
          os.path.isfile(err)
          and "model_schema_unsupported" in open(
              err, encoding="utf-8").read())
    # Profile mismatch: model built_at disagrees with the profile
    # file the hook passes.
    d2 = os.path.join(root, "out", JOB["id"] + "-profile")
    s2 = os.path.join(d2, "_merge_out", SWEEP)
    shutil.copytree(sweep_dir, s2)
    for name in ("report.html", "report.md", "render_error.txt"):
        p = os.path.join(s2, name)
        if os.path.isfile(p):
            os.remove(p)
    bad2 = load_json(os.path.join(s2, "report-model.json"))
    bad2["reaction_profile"]["built_at"] = "2000-01-01T00:00:00Z"
    with open(os.path.join(s2, "report-model.json"), "w",
              encoding="utf-8") as h:
        json.dump(bad2, h)
    m2 = make_manifest(SWEEP)
    m2["compile"] = {"status": "compiled", "sweep_dir": SWEEP}
    ok2 = worker.maybe_render(JOB, d2, m2, plan)
    rec2 = m2.get("render") or {}
    check("profile mismatch: returns False, status 'refused'",
          not ok2 and rec2.get("status") == "refused")
    check("profile mismatch: no twins left in place",
          not os.path.isfile(os.path.join(s2, "report.html"))
          and not os.path.isfile(os.path.join(s2, "report.md")))

    section("stale twins fail-closed (crash shims)")
    for shim, expect in (
            ("exit1", "exited 1"),
            # exit0_silent writes nothing, so the pre-placed stale
            # twins are what the hook validates — and rejects for
            # carrying no data island. That IS the fail-closed path.
            ("exit0_silent", "no model data island"),
            ("exit0_no_island", "no model data island"),
            ("sleep", "timed out")):
        sroot, swdir, ssweep = shim_root(repo, args.archive_root,
                                         shim)
        # The shim tree has no compiled model yet: compile it with
        # the REAL compiler (release copy), then render with the
        # corrupted render.py seam.
        w = import_worker(os.path.join(repo, "worker", "worker.py"),
                          sroot)
        w.RENDER_TIMEOUT = 3
        m = make_manifest(SWEEP)
        compiled_shim = w.maybe_compile(JOB, swdir, m, plan)
        check(f"shim {shim}: fixture compiled first",
              compiled_shim)
        # Pre-place stale twins: a failed render must remove them.
        for twin in ("report.html", "report.md"):
            with open(os.path.join(ssweep, twin), "w",
                      encoding="utf-8") as h:
                h.write("stale")
        ok = w.maybe_render(JOB, swdir, m, plan)
        rec = m.get("render") or {}
        check(f"shim {shim}: status 'error', detail names the "
              "failure",
              not ok and rec.get("status") == "error"
              and expect in rec.get("detail", ""),
              rec.get("detail", "")[:120])
        check(f"shim {shim}: stale twins removed, none left",
              not os.path.isfile(os.path.join(ssweep,
                                              "report.html"))
              and not os.path.isfile(os.path.join(ssweep,
                                                  "report.md")))
        check(f"shim {shim}: render_error.txt marker written",
              os.path.isfile(os.path.join(ssweep,
                                          "render_error.txt")))
        shutil.rmtree(sroot, ignore_errors=True)

    section("gates (skip / error, never crash)")
    m = make_manifest(SWEEP, merge_status="complete")
    m["compile"] = {"status": "refused", "sweep_dir": SWEEP,
                    "detail": "compiler refused"}
    ok = worker.maybe_render(JOB, workdir, m, plan)
    check("refused compile: render skipped, no twins attempted",
          not ok and (m.get("render") or {}).get("status")
          == "skipped")
    m = make_manifest(SWEEP, merge_status="failed")
    ok = worker.maybe_render(JOB, workdir, m, plan)
    check("failed merge: render skipped (compile skipped too)",
          not ok and (m.get("render") or {}).get("status")
          == "skipped")
    m = make_manifest("sweeps/2000-01-01/no-such-sweep")
    m["compile"] = {"status": "compiled",
                    "sweep_dir": "sweeps/2000-01-01/no-such-sweep"}
    ok = worker.maybe_render(JOB, workdir, m, plan)
    check("sweep dir missing on disk: status 'error'",
          not ok and (m.get("render") or {}).get("status")
          == "error")
    m = make_manifest("../escape")
    m["compile"] = {"status": "compiled", "sweep_dir": "../escape"}
    ok = worker.maybe_render(JOB, workdir, m, plan)
    check("sweep_dir with '..': refused as 'error'",
          not ok and (m.get("render") or {}).get("status")
          == "error")
    m = {"job": JOB}
    m["compile"] = ["not-a-dict"]
    ok = worker.maybe_render(JOB, workdir, m, plan)
    check("malformed manifest['compile']: no exception, "
          "returns False", not ok)
    m_run = {"job": {"id": "x", "job": "run yahooquery POUL.CA"}}
    ok = worker.maybe_render(m_run["job"], workdir, m_run, plan)
    check("non-sweep job: returns False, no manifest['render']",
          not ok and "render" not in m_run)
    ok = worker.maybe_render(JOB, workdir, make_manifest(SWEEP), None)
    check("no plan: returns False without rendering", not ok)

    section("executed publish proof (local bare remote)")
    bare = os.path.join(root, "bus.git")
    rc, out = run(["git", "clone", "--quiet", "--bare",
                   args.archive_root, bare])
    assert rc == 0, out
    os.environ["GATOR_BUS_URL"] = bare

    def run_publish_case(tag, tamper_compile=False,
                         tamper_render=False):
        proot = tempfile.mkdtemp(prefix=f"h69-pub-{tag}-")
        shutil.copytree(repo, os.path.join(proot, "release"))
        rc, out = run(["git", "clone", "--quiet", bare,
                       os.path.join(proot, "archive-push")])
        assert rc == 0, out
        pw = import_worker(os.path.join(repo, "worker", "worker.py"),
                           proot)
        workdir = os.path.join(proot, "out", JOB["id"])
        sw = os.path.join(workdir, "_merge_out", SWEEP)
        copy_golden_sweep(args.archive_root, sw)
        os.makedirs(os.path.join(workdir, "yahooquery"),
                    exist_ok=True)
        with open(os.path.join(workdir, "yahooquery",
                               "summary.json"), "w") as h:
            h.write("{}")
        with open(os.path.join(workdir, "yahooquery.log"),
                  "w") as h:
            h.write("log")
        if tamper_compile:
            ens = load_json(os.path.join(sw, "ensemble.json"))
            ens["ticker"] = "WRONG.CA"
            with open(os.path.join(sw, "ensemble.json"), "w") as h:
                json.dump(ens, h)
        manifest = make_manifest(SWEEP)
        workdir = Path(workdir)
        pw._write_manifest_atomic(workdir, manifest)
        compiled = pw.maybe_compile(JOB, workdir, manifest, plan)
        if tamper_render and compiled:
            bad = load_json(os.path.join(sw, "report-model.json"))
            bad["schema"] = "borsagator-report-model/99"
            with open(os.path.join(sw, "report-model.json"), "w",
                      encoding="utf-8") as h:
                json.dump(bad, h)
        rendered = pw.maybe_render(JOB, workdir, manifest, plan)
        pw._write_manifest_atomic(workdir, manifest)
        sha = pw.publish(JOB, workdir, manifest)
        return proot, sw, manifest, compiled, rendered, sha

    proot, sw, pmanifest, compiled, rendered, sha = \
        run_publish_case("ok")
    check("rendered case: compile True, render True, publish "
          "returns a SHA", compiled and rendered and bool(sha))
    if sha:
        rc, out = run(["git", "--git-dir", bare, "show",
                       "--name-only", "--format=", sha])
        names = out.split()
        check("one commit carries model + twins + fleet "
              "(same-commit proof)",
              f"{SWEEP}/report-model.json" in names
              and f"{SWEEP}/report.html" in names
              and f"{SWEEP}/report.md" in names
              and any(n.startswith("worker-runs/")
                      and n.endswith("manifest.json") for n in names))
        rc, out = run(["git", "--git-dir", bare, "show",
                       f"{sha}:{SWEEP}/report.html"])
        check("archived report.html hashes to the manifest's SHA",
              hashlib.sha256(out.encode()).hexdigest()
              == ((pmanifest.get("render") or {}).get("files") or
                  [{}])[0].get("sha256"))
        rc, out = run(["git", "--git-dir", bare, "show",
                       f"{sha}:{SWEEP}/manifest.json"])
        files = (json.loads(out).get("files")
                 if rc == 0 else None)
        check("archived sweep manifest files[] lists both twins",
              files is not None
              and any(f.get("path") == "report.html" for f in files)
              and any(f.get("path") == "report.md" for f in files))
        run_manifest = None
        for n in names:
            if n.startswith("worker-runs/") \
                    and n.endswith("manifest.json"):
                rc, out = run(["git", "--git-dir", bare, "show",
                               f"{sha}:{n}"])
                run_manifest = json.loads(out)
        check("archived run manifest carries the render block",
              (run_manifest or {}).get("render", {}).get("status")
              == "rendered")
    proot2, sw2, pmanifest2, compiled2, rendered2, sha2 = \
        run_publish_case("render-refused", tamper_render=True)
    check("render-refused case: compile True, render False, "
          "publish STILL returns a SHA",
          compiled2 and not rendered2 and bool(sha2))
    if sha2:
        rc, out = run(["git", "--git-dir", bare, "show",
                       "--name-status", "--format=", sha2])
        check("render-refusal commit DELETES the prior commit's "
              "twins (cp never deletes; the drop must)",
              f"D\t{SWEEP}/report.html" in out
              and f"D\t{SWEEP}/report.md" in out)
        rc_h, _ = run(["git", "--git-dir", bare, "cat-file", "-e",
                       f"{sha2}:{SWEEP}/report.html"])
        rc_m, _ = run(["git", "--git-dir", bare, "cat-file", "-e",
                       f"{sha2}:{SWEEP}/report.md"])
        rc_e, _ = run(["git", "--git-dir", bare, "cat-file", "-e",
                       f"{sha2}:{SWEEP}/render_error.txt"])
        rc_f, _ = run(["git", "--git-dir", bare, "cat-file", "-e",
                       f"{sha2}:{SWEEP}/digest.json"])
        check("render-refusal tree: twins ABSENT, marker + fleet "
              "present",
              rc_h != 0 and rc_m != 0 and rc_e == 0 and rc_f == 0,
              detail=f"html-rc={rc_h} md-rc={rc_m} "
                     f"marker-rc={rc_e} digest-rc={rc_f}")
        check("render-refusal run manifest records status "
              "'refused'",
              (pmanifest2.get("render") or {}).get("status")
              == "refused")
    proot3, sw3, pmanifest3, compiled3, rendered3, sha3 = \
        run_publish_case("ok-after-refusal")
    check("ok-after-refusal: compile True, render True, publish "
          "returns a SHA", compiled3 and rendered3 and bool(sha3))
    if sha3:
        rc_h, _ = run(["git", "--git-dir", bare, "cat-file", "-e",
                       f"{sha3}:{SWEEP}/report.html"])
        rc_m, _ = run(["git", "--git-dir", bare, "cat-file", "-e",
                       f"{sha3}:{SWEEP}/report.md"])
        rc_e, _ = run(["git", "--git-dir", bare, "cat-file", "-e",
                       f"{sha3}:{SWEEP}/render_error.txt"])
        check("ok-after-refusal tree: twins present, stale "
              "render_error.txt dropped",
              rc_h == 0 and rc_m == 0 and rc_e != 0,
              detail=f"html-rc={rc_h} md-rc={rc_m} "
                     f"marker-rc={rc_e}")
    proot4, sw4, pmanifest4, compiled4, rendered4, sha4 = \
        run_publish_case("compile-refused", tamper_compile=True)
    check("compile-refused case: compile False, render skipped, "
          "publish STILL returns a SHA",
          not compiled4 and not rendered4 and bool(sha4))
    if sha4:
        rc_m, _ = run(["git", "--git-dir", bare, "cat-file", "-e",
                       f"{sha4}:{SWEEP}/report-model.json"])
        rc_h, _ = run(["git", "--git-dir", bare, "cat-file", "-e",
                       f"{sha4}:{SWEEP}/report.html"])
        rc_e, _ = run(["git", "--git-dir", bare, "cat-file", "-e",
                       f"{sha4}:{SWEEP}/compile_error.txt"])
        check("compile-refusal tree: model AND twins ABSENT, "
              "marker present",
              rc_m != 0 and rc_h != 0 and rc_e == 0,
              detail=f"model-rc={rc_m} html-rc={rc_h} "
                     f"marker-rc={rc_e}")
        check("compile-refusal run manifest records render "
              "'skipped'",
              (pmanifest4.get("render") or {}).get("status")
              == "skipped")
    shutil.rmtree(proot, ignore_errors=True)
    shutil.rmtree(proot2, ignore_errors=True)
    shutil.rmtree(proot3, ignore_errors=True)
    shutil.rmtree(proot4, ignore_errors=True)

    section("end-to-end _execute_body (real orchestration)")
    # Seams, clearly identified: run_tool (external tool execution:
    # network, runner repos, venvs) serves the golden sweep's
    # collected outputs; _mark_done (bus write) records the call.
    # Everything else is real: registry, parse_job, manifest writes,
    # maybe_merge (real merge.py + real ensemble.py), maybe_compile
    # (real compile_model.py), maybe_render (real render.py),
    # publish (real, against a local bare remote).
    def run_execute_body(tag, mutate_hook):
        eroot = tempfile.mkdtemp(prefix=f"h69-e2e-{tag}-")
        shutil.copytree(repo, os.path.join(eroot, "release"))
        src_file = os.path.join(eroot, "release", "worker",
                                "worker.py")
        if mutate_hook:
            src_text = open(src_file, encoding="utf-8").read()
            call = "    maybe_render(job, workdir, manifest, plan)\n"
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
                return "ok", "seam log"
            return "failed", "seam: no fixture for tool"

        def mark_done_seam(job, archive_sha):
            calls["done"].append((job["id"], archive_sha))

        w.run_tool = run_tool_seam
        w._mark_done = mark_done_seam
        job = {"id": f"h69-e2e-{tag}", "added": "2026-11-19",
               "job": "sweep-lite POUL.CA market=EGX"}
        w._execute_body(job)
        return eroot, bare, w, calls, job

    eroot, bare, w, calls, job = run_execute_body("ok", False)
    outdir = os.path.join(eroot, "out", job["id"])
    e_manifest = load_json(os.path.join(outdir, "manifest.json"))
    e_sweep = (e_manifest.get("merge") or {}).get("sweep_dir")
    check("e2e: merge succeeded and named a sweep dir",
          bool(e_sweep))
    check("e2e: compile block status 'compiled'",
          (e_manifest.get("compile") or {}).get("status")
          == "compiled")
    check("e2e: render block status 'rendered'",
          (e_manifest.get("render") or {}).get("status")
          == "rendered",
          detail=str(e_manifest.get("render")))
    done_sha = calls["done"][-1][1] if calls["done"] else None
    check("e2e: job marked done with an archive SHA (publish "
          "landed)", bool(done_sha))
    if done_sha and e_sweep:
        rc, out = run(["git", "--git-dir", bare, "show",
                       "--name-only", "--format=", done_sha])
        names = out.split()
        check("e2e: ONE commit carries twins + model + fleet",
              f"{e_sweep}/report.html" in names
              and f"{e_sweep}/report.md" in names
              and f"{e_sweep}/report-model.json" in names
              and f"{e_sweep}/digest.json" in names
              and any(n.startswith("worker-runs/") for n in names))
        rc, out = run(["git", "--git-dir", bare, "show",
                       f"{done_sha}:{e_sweep}/report.html"])
        check("e2e: archived report.html hashes to the "
              "manifest's SHA",
              rc == 0 and hashlib.sha256(out.encode()).hexdigest()
              == ((e_manifest.get("render") or {}).get("files")
                  or [{}])[0].get("sha256"))
    shutil.rmtree(eroot, ignore_errors=True)

    eroot, bare, w, calls, job = run_execute_body("bypass", True)
    outdir = os.path.join(eroot, "out", job["id"])
    e_manifest = load_json(os.path.join(outdir, "manifest.json"))
    e_sweep = (e_manifest.get("merge") or {}).get("sweep_dir")
    done_sha = calls["done"][-1][1] if calls["done"] else None
    check("e2e hook-bypassed: fleet + merge + model still "
          "publish, job done",
          bool(done_sha) and bool(e_sweep)
          and (e_manifest.get("compile") or {}).get("status")
          == "compiled")
    check("e2e hook-bypassed: no render block recorded",
          "render" not in e_manifest)
    if done_sha and e_sweep:
        rc, out = run(["git", "--git-dir", bare, "show",
                       "--name-only", "--format=", done_sha])
        names = out.split()
        check("e2e hook-bypassed: NO report twins in the commit "
              "(the mutation is caught)",
              f"{e_sweep}/report.html" not in names
              and f"{e_sweep}/report.md" not in names
              and f"{e_sweep}/report-model.json" in names
              and f"{e_sweep}/digest.json" in names)
    shutil.rmtree(eroot, ignore_errors=True)
    os.environ["GATOR_BUS_URL"] = SENTINEL

    section("wiring source assertions (no mocks)")
    src = open(os.path.join(repo, "worker", "worker.py"),
               encoding="utf-8").read()
    i_merge = src.find("\n    maybe_merge(job, workdir, manifest, plan)")
    i_compile = src.find(
        "\n    maybe_compile(job, workdir, manifest, plan)")
    i_render = src.find(
        "\n    maybe_render(job, workdir, manifest, plan)")
    i_manifest2 = src.find("_write_manifest_atomic(workdir, manifest)",
                           i_merge)
    i_publish = src.find("archive_sha = publish(job, workdir, manifest)",
                         i_manifest2)
    check("call order: maybe_merge < maybe_compile < maybe_render "
          "< second _write_manifest_atomic < publish",
          -1 < i_merge < i_compile < i_render < i_manifest2 < i_publish)
    check("hook filters ENV_DENY_FOR_TOOLS and asserts the boundary",
          "if k not in ENV_DENY_FOR_TOOLS" in src
          and "_assert_no_denied(env)" in src)
    check("hook runs the renderer with a named bounded timeout",
          "RENDER_TIMEOUT = 600" in src
          and "timeout=RENDER_TIMEOUT" in src)
    check("hook passes the I-5 --sweep-dir fallback to the renderer",
          '"--sweep-dir", str(sweep_dir)' in src)
    check("publish suppression drops the twins on a non-rendered "
          "outcome and refuses on a bad handoff",
          'drop.append(f"{render_rel}/report.html")' in src
          and "suppress_render" in src)
    check("fail-closed tail removes surviving twins and writes "
          "the marker",
          'os.remove(p)' in src
          and 'marker.write_text(f"render {status}: {detail}\\n")'
          in src)

    failed = [c for c in CHECKS if not c[2]]
    print(f"harness_issue69_worker_wire: {len(CHECKS) - len(failed)}"
          f"/{len(CHECKS)} passed")
    if failed:
        print("FAILURES:")
        for sec, name, _ok, detail in failed:
            print(f"  [{sec}] {name} {detail}")
        return 1
    print("harness_issue69_worker_wire: ALL GREEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
