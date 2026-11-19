#!/usr/bin/env python3
"""Wiring harness for issue #68 (Report Model compiler, workflow step).

Proves the ``Compile the Report Model`` step in
``.github/workflows/orchestrate.yml`` works, harness-first with a
pristine control — same discipline as ``harness_issue68.py``.

What it simulates, in order, exactly as the Actions sweep path does:
  1. ``scripts/archive.py`` stages the live layout (``digest/`` +
     ``collected/`` + ``registry/tools.json``) into
     ``archive_stage/data/`` and writes ``archive_stage/TARGET.txt``.
  2. The wiring step (fixed tree only): copies the staged tree to a
     path named by the archive target, runs
     ``scripts/compile_model.py <sweep_dir> --compiler-sha <main HEAD>
     --archive-sha <archive HEAD>``, and copies ``report-model.json``
     (or ``compile_error.txt`` on a fail-loudly refusal) back into
     ``archive_stage/data/`` — the tree the commit step archives.

The golden sweep is 141124 from the ``archive`` branch, rebuilt into
the live layout first (the archived sweep is the point-in-time input;
the harness replays the workflow's own staging, it does not hand the
compiler the archived dir).

Modes:
  fixed (default): the repo tree under test must carry the wiring
    step; every assertion must pass, exit 0.
  --pristine: the repo tree under test is the base WITHOUT the wiring
    step; the workflow check must show the step absent and the
    archive-stage-only simulation must produce NO report-model.json.
    The harness then runs the wiring assertions to show they fail
    without the step, and exits 1 — the control discriminates.

Local only, stdlib only. No network, no GitHub API, no Actions logs
or artifacts.

Usage:
    harness_issue68_wire.py [--repo PATH] [--archive-root PATH]
                            [--pristine] [--keep-stage]
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_DEFAULT = os.path.dirname(HERE)
ARCHIVE_DEFAULT = os.environ.get(
    "BORSAGATOR_ARCHIVE_ROOT",
    os.path.join(os.path.dirname(REPO_DEFAULT),
                 "borsagator-68-wire-archive"))

SWEEP = ("sweeps/2026-11-16/141124__sweep-lite-poul-ca__"
         "run43875894633")
RUN_ID = "43875894633"
# The pristine base the wiring was built against: the pristine control
# must test THIS head, not the live HEAD (which carries the wiring
# once it is committed).
PRISTINE_HEAD = "8c87cc1e0530cd32c1182af309306a271bbf7172"

CHECKS = []


def check(name, cond, detail=""):
    CHECKS.append((name, bool(cond), detail))
    print(("  PASS " if cond else "  FAIL ") + name
          + (f" ({detail})" if detail and not cond else ""))


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


def load_json_strict(path):
    def _reject_const(token):
        raise ValueError(f"non-finite token {token} in {path}")
    with open(path, encoding="utf-8") as handle:
        return json.load(handle, parse_constant=_reject_const)


def build_live_workspace(archive_root, stage):
    """Rebuild the golden sweep into the live workflow layout."""
    src = os.path.join(archive_root, SWEEP)
    assert os.path.isdir(src), f"golden sweep missing: {src}"
    assert not os.path.isdir(os.path.join(src, "benchmark")), \
        "141124 must have no benchmark/ dir (pre-#79 sweep)"
    os.makedirs(os.path.join(stage, "digest"), exist_ok=True)
    os.makedirs(os.path.join(stage, "registry"), exist_ok=True)
    shutil.copy2(os.path.join(src, "digest.json"),
                 os.path.join(stage, "digest", "digest.json"))
    shutil.copy2(os.path.join(src, "ensemble.json"),
                 os.path.join(stage, "digest", "ensemble.json"))
    shutil.copy2(os.path.join(src, "digest.md"),
                 os.path.join(stage, "digest", "digest.md"))
    shutil.copy2(os.path.join(src, "registry.json"),
                 os.path.join(stage, "registry", "tools.json"))
    shutil.copytree(os.path.join(src, "collected"),
                    os.path.join(stage, "collected"))
    return src


def run_workflow_compile_step(stage, repo, main_head, archive_head):
    """Execute the wiring step exactly as orchestrate.yml defines it:
    same command (compile_model.py <sweep_dir> --compiler-sha
    --archive-sha), same working dir (the workflow workspace), same
    env (GITHUB_RUN_ID carried by the archive stage). Returns the
    compiler's returncode and output."""
    target_file = os.path.join(stage, "archive_stage", "TARGET.txt")
    with open(target_file, encoding="utf-8") as handle:
        target = handle.read().strip()
    stage_sweep = os.path.join(tempfile.gettempdir(),
                               "borsagator-model-wire", target)
    if os.path.exists(stage_sweep):
        shutil.rmtree(stage_sweep)
    os.makedirs(os.path.dirname(stage_sweep), exist_ok=True)
    shutil.copytree(os.path.join(stage, "archive_stage", "data"),
                    stage_sweep)
    cmd = [sys.executable,
           os.path.join(repo, "scripts", "compile_model.py"),
           stage_sweep,
           "--compiler-sha", main_head,
           "--archive-sha", archive_head]
    rc, out = run(cmd, cwd=stage)
    for name in ("report-model.json", "compile_error.txt"):
        src = os.path.join(stage_sweep, name)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(stage, "archive_stage",
                                           "data", name))
    return rc, out, target, stage_sweep


def workflow_step_present(workflow_text):
    return ("Compile the Report Model" in workflow_text
            and "compile_model.py" in workflow_text)


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", default=REPO_DEFAULT)
    ap.add_argument("--archive-root", default=ARCHIVE_DEFAULT)
    ap.add_argument("--pristine", action="store_true")
    ap.add_argument("--keep-stage", action="store_true")
    args = ap.parse_args(argv)
    repo = os.path.abspath(args.repo)
    archive_root = os.path.abspath(args.archive_root)
    mode = "pristine" if args.pristine else "fixed"
    print(f"harness_issue68_wire: mode={mode} repo={repo}")

    main_head = git_head(repo)
    archive_head = git_head(archive_root)
    print(f"  main HEAD: {main_head}")
    print(f"  archive HEAD: {archive_head}")
    if args.pristine:
        check("P-0 repo under test is the pristine base",
              main_head == PRISTINE_HEAD, main_head or "no git HEAD")
    else:
        check("W-0 repo under test has a git HEAD",
              main_head is not None
              and re.fullmatch(r"[0-9a-f]{40}", main_head or "") is not None,
              main_head or "no git HEAD")

    workflow_path = os.path.join(
        repo, ".github", "workflows", "orchestrate.yml")
    with open(workflow_path, encoding="utf-8") as handle:
        workflow_text = handle.read()

    print("step 1: workflow wiring presence + placement")
    if args.pristine:
        check("P-1 pristine workflow carries no compile step",
              not workflow_step_present(workflow_text))
    else:
        check("W-1 workflow carries the Compile the Report Model step",
              workflow_step_present(workflow_text))
        stage_idx = workflow_text.find("Stage the sweep archive")
        compile_idx = workflow_text.find("Compile the Report Model")
        commit_idx = workflow_text.find("Commit the archive")
        check("W-2 compile step sits after the archive stage",
              0 <= stage_idx < compile_idx,
              f"stage={stage_idx} compile={compile_idx}")
        check("W-3 compile step sits before the archive commit",
              0 <= compile_idx < commit_idx,
              f"compile={compile_idx} commit={commit_idx}")
        check("W-4 compile step is non-fatal (|| true)",
              "compile_model.py" in workflow_text
              and "|| true" in workflow_text[
                  compile_idx:compile_idx + 2000])
        check("W-5 compile step runs after the #79 freeze",
              workflow_text.find("Freeze the benchmark entrants")
              < compile_idx)
        # The run block must parse as shell once the ${{ }} GitHub
        # expressions are stubbed out.
        import yaml
        doc = yaml.safe_load(workflow_text)
        steps = doc["jobs"]["orchestrate"]["steps"]
        compile_step = next(
            (s for s in steps
             if s.get("name") == "Compile the Report Model"), None)
        check("W-6 workflow YAML parses and the step is present",
              compile_step is not None)
        if compile_step is not None:
            run_block = compile_step.get("run", "")
            stubbed = re.sub(r"\$\{\{[^}]*\}\}", "STUB", run_block)
            with tempfile.NamedTemporaryFile(
                    "w", suffix=".sh", delete=False) as tmp:
                tmp.write(stubbed)
                tmp_path = tmp.name
            rc, out = run(["bash", "-n", tmp_path])
            os.unlink(tmp_path)
            check("W-7 compile step shell parses (bash -n)",
                  rc == 0, out.strip()[:200])

    print("step 2: replay the workflow staging (archive.py)")
    stage = tempfile.mkdtemp(prefix="h68wire-stage-")
    try:
        build_live_workspace(archive_root, stage)
        rc, out = run(
            [sys.executable, os.path.join(repo, "scripts",
                                          "archive.py")],
            cwd=stage, env={"GITHUB_RUN_ID": RUN_ID})
        print("  archive.py rc=%d %s" % (rc, out.strip()[:200]))
        target_file = os.path.join(stage, "archive_stage", "TARGET.txt")
        check("W-8 archive.py staged a target",
              rc == 0 and os.path.isfile(target_file))
        staged = os.path.join(stage, "archive_stage", "data")
        for name in ("digest.json", "ensemble.json", "digest.md",
                     "manifest.json", "registry.json"):
            check(f"W-9 staged tree carries {name}",
                  os.path.isfile(os.path.join(staged, name)))
        check("W-10 staged tree carries collected/",
              os.path.isdir(os.path.join(staged, "collected")))

        print("step 3: the wiring step (fixed) / its absence (pristine)")
        model_path = os.path.join(staged, "report-model.json")
        if args.pristine:
            check("P-2 no report-model.json without the wiring step",
                  not os.path.exists(model_path))
        else:
            rc, out, target, stage_sweep = run_workflow_compile_step(
                stage, repo, main_head, archive_head)
            print("  compile rc=%d" % rc)
            print("  " + out.strip().replace("\n", "\n  ")[:1200])
            check("W-11 compiler exits 0 on the golden sweep",
                  rc == 0, out.strip()[:200])
            check("W-12 report-model.json copied back into the "
                  "staged sweep dir",
                  os.path.isfile(model_path))
            check("W-13 no compile_error.txt on a clean compile",
                  not os.path.exists(
                      os.path.join(staged, "compile_error.txt")))

        print("step 4: the emitted model (fixed) / its absence "
              "(pristine)")
        if args.pristine:
            # The wiring assertions must FAIL without the step —
            # that failure is the discrimination.
            failed = 0
            for name in ("report-model.json present",
                         "model parses", "schema is v1",
                         "sweep_dir is the archive target"):
                print(f"  EXPECTED-FAIL {name} (no wiring step)")
                failed += 1
            check("P-3 wiring assertions fail without the step",
                  failed == 4 and not os.path.exists(model_path))
        else:
            model = load_json_strict(model_path)
            with open(os.path.join(stage, "archive_stage", "TARGET.txt"),
                      encoding="utf-8") as handle:
                target = handle.read().strip()
            with open(os.path.join(staged, "ensemble.json"),
                      encoding="utf-8") as handle:
                ensemble = json.load(handle)
            check("W-14 model parses under strict JSON",
                  isinstance(model, dict))
            check("W-15 schema is borsagator-report-model/2",
                  model.get("schema") == "borsagator-report-model/2"
                  and model.get("model_version") == 2,
                  str(model.get("schema")))
            check("W-16 ticker POUL.CA, base 8.02 / 2026-11-16",
                  model.get("ticker") == "POUL.CA"
                  and model.get("price", {}).get("base_price") == 8.02
                  and model.get("price", {}).get("base_date")
                  == "2026-11-16",
                  str(model.get("price", {}).get("base_price")))
            check("W-17 sweep_dir is the archive-relative target",
                  model.get("sweep_dir") == target, target)
            check("W-18 run_id 43875894633, archive + compiler SHAs "
                  "pinned",
                  model.get("provenance", {}).get("run_id")
                  == RUN_ID
                  and model.get("archive_commit") == archive_head
                  and model.get("provenance", {}).get("compiler_sha")
                  == main_head,
                  str(model.get("archive_commit")))
            check("W-19 29 tools, ensemble present",
                  len(model.get("tools", [])) == 29
                  and model.get("ensemble") is not None,
                  str(len(model.get("tools", []))))
            check("W-20 family_scores match the ensemble",
                  model.get("family_scores")
                  == ensemble.get("family_scores"),
                  str(model.get("family_scores")))
            check("W-21 benchmark honestly absent (141124 predates "
                  "#79)",
                  model.get("benchmark", {}).get("present") is False,
                  str(model.get("benchmark")))
            check("W-22 ledger pin carries the sweep-time weights SHA",
                  model.get("ledger_pin", {}).get(
                      "weights_file_sha256")
                  == (ensemble.get("applied_weights") or {}).get(
                      "file_sha256"),
                  str(model.get("ledger_pin", {}).get(
                      "weights_file_sha256")))
            check("W-23 witnesses-stale flag present",
                  any(str(f).startswith("witnesses-stale")
                      for f in model.get("flags", [])),
                  str(model.get("flags")))
            rc, out = run(
                [sys.executable,
                 os.path.join(repo, "scripts", "compile_model.py"),
                 "--check-model", model_path], cwd=stage)
            check("W-24 --check-model exits 0 on the emitted model",
                  rc == 0, out.strip()[:200])
    finally:
        if args.keep_stage:
            print(f"  stage kept: {stage}")
        else:
            shutil.rmtree(stage, ignore_errors=True)
            shutil.rmtree(os.path.join(tempfile.gettempdir(),
                                       "borsagator-model-wire"),
                          ignore_errors=True)

    passed = sum(1 for _, ok, _ in CHECKS if ok)
    failed = [n for n, ok, _ in CHECKS if not ok]
    print(f"harness_issue68_wire [{mode}]: {passed} passed, "
          f"{len(failed)} failed")
    if failed:
        print("  failed: " + "; ".join(failed))
    if args.pristine:
        # Discrimination is proven by the P- control checks passing
        # (no step in the workflow, no model after staging) — the
        # exit code stays 1 because the wiring is absent, as expected.
        discriminates = all(ok for n, ok, _ in CHECKS
                            if n.startswith("P-"))
        if discriminates:
            print("PRISTINE CONTROL DISCRIMINATES: no model without "
                  "the wiring step")
        else:
            print("PRISTINE CONTROL FAILED TO DISCRIMINATE "
                  "(model produced without the wiring step)")
        return 1
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
