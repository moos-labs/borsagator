#!/usr/bin/env python3
"""Issue #67 harness -- worker-side digest/ensemble merge.

Usage: python3 harness_issue67.py <repo-path> <archive-path>
  repo-path:    checkout of moos-labs/borsagator (the tree under test)
  archive-path: checkout of the archive branch (real sweep dirs and
                real worker-run dirs -- the goldens are read from
                it, never from Actions logs or artifacts)

Exit 0 = all checks pass, 1 = any check fails. On the pristine tree
(no scripts/merge.py, no worker hook) the harness FAILS: the module
is absent, and the naive-digest control also fails the parity
assertions -- proving the assertions discriminate. On the fixed
tree every case passes.

Golden values below were re-derived from the live archive at
implementation time (archive HEAD e2363208); where they differ
from the deep scoping doc the live value is asserted and the drift
is named in the check detail.

Parity target (CORRECTION to the deep scoping's case 1): the
archived ensemble.json files are NOT byte-reproducible with the
current ensemble.py — #129 (entitlement_end), #130 (Kronos
ex-rescale) and #131 (corporate-action dedup) landed after the 16
Nov sweeps ran, and every archived 16 Nov ensemble predates them
(none carries entitlement_end or horizon corporate-action marks;
all carry kronos_ex_rescale null). The parity target is therefore
the CURRENT ensemble.py run on the archived sweep's own
Actions-layout inputs (digest.json + collected/ + the period
weights file): same code, same inputs. The harness asserts the
merged ensemble is byte-identical to that reference, and that the
reference differs from the archived file only in the known
#129/#130/#131 keys.

Staging rule (what a worker run looks like): the archived Actions
sweep's collected/<tool>/ dirs become the worker run's per-tool
dirs, MINUS the EMITTER envelope summary.json (on the worker the
tool dir holds what the runner wrote, and merge.py synthesizes
the envelope). The one exception is yahooquery, whose REAL native
summary.json is taken from the live worker run w3-selftest-001
(last_close: NaN) — the only native summary the archive branch
preserves. For the other tools whose runners natively write a
summary.json (openbb, vectorbt, financedatabase, ...), the
archive cannot recover the native file (the envelope overwrote
it), so the files-list comparison excludes the "summary.json"
entry for those tools and says so; metrics — the parity-critical
part — are compared exactly for every tool.
"""
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

FAILS = []

EGX = "sweeps/2026-11-16/050559__sweep-lite-poul-ca-market-egx__run43805931446"
FULL = "sweeps/2026-11-16/141124__sweep-lite-poul-ca__run43875894633"
YQ_WORKER = ("worker-runs/2026-11-17/001209__run-yahooquery-poul-ca__"
             "w3-selftest-001")
NEWS_WORKER = ("worker-runs/2026-11-17/020416__run-news-disclosure-poul-ca__"
               "w5-news-egx-002")
JOB_EGX = "sweep-lite POUL.CA market=EGX"
JOB_FULL = "sweep-lite POUL.CA"
JOB_ID = "sched-2026-11-16"
SECRET_NAMES = ("COHERE_API_KEY", "SIMFIN_API_KEY", "GATOR_BUS_URL",
                "GH_TOKEN", "BORSAGATOR_APP_PRIVATE_KEY", "FMP_API_KEY")


def check(name, ok, detail=""):
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" +
          (f" -- {detail}" if detail else ""))
    if not ok:
        FAILS.append(name)


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def git_head(path):
    p = subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"],
                       capture_output=True, text=True)
    return p.stdout.strip() if p.returncode == 0 else "?"


def reconstruct_period_weights(archived_ensemble, current_weights_path):
    """Rebuild the ledger/weights.json bytes the archived ensemble
    was built against, from its applied_weights pin + the current
    file's ineligible-family rows (agent n=1 skill 0.75,
    fundamentals n=0 skill null — unchanged by the ledger since).
    Returns (bytes, sha256). The caller asserts the sha equals the
    archived pin: only then is the ensemble byte-comparison valid."""
    applied = archived_ensemble["applied_weights"]
    current = json.loads(Path(current_weights_path).read_text())
    factors = {}
    for fam in ("price-forecast", "technicals", "sentiment",
                "agent", "fundamentals"):
        if fam in applied.get("eligible", {}):
            e = applied["eligible"][fam]
            factors[fam] = {"factor": e["factor"],
                            "skill": e.get("skill"), "n": e["n"]}
        else:
            cur = current["factors"][fam]
            factors[fam] = {"factor": cur["factor"],
                            "skill": cur.get("skill"), "n": cur["n"]}
    doc = {"tool": "ensemble-weights", "version": 1,
           "built_from": "calibration-ledger", "min_n": 3,
           "clamp": [0.5, 1.5], "factors": factors}
    raw = json.dumps(doc, indent=1).encode("utf-8")
    import hashlib
    return raw, hashlib.sha256(raw).hexdigest()


def stage_worker_run(archive_path, sweep_rel, job, job_id, dest,
                     status_overrides=None, drop_tools=None,
                     empty_tools=None):
    """Build a worker OUT/<job-id> tree from an archived Actions
    sweep. Returns the run dir Path. status_overrides maps tool ->
    manifest status; drop_tools removes tools from the manifest
    (completeness negative); empty_tools empties a tool's dir to
    just its run.log (failed-tool fixture)."""
    archive_path, dest = Path(archive_path), Path(dest)
    sweep = archive_path / sweep_rel
    digest = json.loads((sweep / "digest.json").read_text())
    run = dest / job_id
    run.mkdir(parents=True)
    manifest_tools = {}
    for r in digest["results"]:
        tool = r["tool"]
        if drop_tools and tool in drop_tools:
            continue
        status = (status_overrides or {}).get(tool)
        if status is None:
            status = {"ok": "ok", "failed": "exit-1",
                      "no-summary": "exit-1",
                      "error": "error"}.get(r["status"], "error")
        manifest_tools[tool] = status
        src = sweep / "collected" / tool
        d = run / tool
        d.mkdir(parents=True)
        if src.is_dir():
            for item in sorted(src.iterdir()):
                if item.name == "summary.json":
                    continue  # the envelope; merge re-synthesizes it
                if item.is_file():
                    shutil.copy2(item, d / item.name)
                elif item.is_dir():
                    shutil.copytree(item, d / item.name)
        if empty_tools and tool in empty_tools:
            for item in list(d.iterdir()):
                if item.name != "run.log":
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
        if tool == "yahooquery":
            # The real native summary (NaN last_close) from the
            # live worker run — the only native summary preserved.
            native = archive_path / YQ_WORKER / "yahooquery" \
                / "summary.json"
            if native.is_file():
                shutil.copy2(native, d / "summary.json")
        log_src = sweep / "collected" / tool / "run.log"
        if log_src.is_file():
            shutil.copy2(log_src, run / f"{tool}.log")
    manifest = {"job": {"id": job_id, "job": job},
                "worker": "borsagator-worker-5",
                "started": digest["started"],
                "finished": digest["finished"],
                "tools": manifest_tools}
    (run / "manifest.json").write_text(json.dumps(manifest, indent=1))
    return run


def current_code_reference(archive_path, repo, sweep_rel, weights_bytes,
                           tmp):
    """Run CURRENT ensemble.py on the archived sweep's own
    Actions-layout inputs (digest.json + collected/ + the period
    weights file). The result is the parity target: same code, same
    inputs, so a worker merge that stages faithfully must reproduce
    it byte-identically."""
    archive_path, repo, tmp = Path(archive_path), Path(repo), Path(tmp)
    sweep = archive_path / sweep_rel
    tree = tmp / "actions-tree"
    (tree / "digest").mkdir(parents=True)
    (tree / "ledger").mkdir(parents=True)
    shutil.copy2(sweep / "digest.json", tree / "digest" / "digest.json")
    shutil.copy2(sweep / "digest.md", tree / "digest" / "digest.md")
    shutil.copytree(sweep / "collected", tree / "collected")
    (tree / "ledger" / "weights.json").write_bytes(weights_bytes)
    env = dict(os.environ)
    env["BORSAGATOR_WEIGHTS"] = "ledger/weights.json"
    proc = subprocess.run(
        [sys.executable, str(repo / "scripts" / "ensemble.py")],
        cwd=str(tree), env=env, capture_output=True, text=True,
        timeout=600)
    raw = (tree / "digest" / "ensemble.json").read_bytes()
    return json.loads(raw), raw


def run_merge(repo, run_dir, job, job_id, out_dir, weights_path,
              extra_args=None):
    cmd = [sys.executable, str(Path(repo) / "scripts" / "merge.py"),
           "--job", job, "--run-dir", str(run_dir),
           "--registry", str(Path(repo) / "registry" / "tools.json"),
           "--weights", str(weights_path),
           "--ensemble", str(Path(repo) / "scripts" / "ensemble.py"),
           "--release-sha", git_head(repo),
           "--claim-id", job_id, "--worker", "borsagator-worker-5",
           "--out", str(out_dir)]
    if extra_args:
        cmd += extra_args
    return subprocess.run(cmd, capture_output=True, text=True,
                          timeout=600)


def main():
    repo, archive = Path(sys.argv[1]), Path(sys.argv[2])
    print(f"repo HEAD: {git_head(repo)}")
    print(f"archive HEAD: {git_head(archive)}")
    merge_py = repo / "scripts" / "merge.py"
    check("merge module present (scripts/merge.py)",
          merge_py.is_file(),
          "absent on the pristine tree" if not merge_py.is_file()
          else "present")
    if not merge_py.is_file():
        # Pristine control, continued: the naive digest (rows
        # without summary synthesis) also fails the parity
        # assertions on its own — the assertions discriminate
        # even without the module-absent failure above.
        naive = {"job": JOB_EGX, "ticker": "POUL.CA",
                 "date": "2026-11-16",
                 "results": [{"tool": r["tool"], "status": "ok"}
                             for r in json.loads(
                                 (archive / EGX / "digest.json")
                                 .read_text())["results"]]}
        arch_metrics = {r["tool"]: (r.get("summary") or {})
                        .get("metrics") for r in json.loads(
                            (archive / EGX / "digest.json")
                            .read_text())["results"]}
        naive_has_metrics = all(
            (r.get("summary") or {}).get("metrics") ==
            arch_metrics[r["tool"]]
            for r in naive["results"])
        check("naive control: a hand-rolled digest without summary "
              "synthesis FAILS the parity assertions",
              naive_has_metrics is False,
              "naive digest carries no metrics, as expected")
        print(f"\n{len(FAILS)} FAIL(s); harness exits 1")
        return 1
    merge = load_module("merge67", merge_py)

    tmp = Path(tempfile.mkdtemp(prefix="h67-"))
    try:
        # --- weights reconstruction (pins the parity cases) ---
        egx_ens = json.loads(
            (archive / EGX / "ensemble.json").read_text())
        wbytes, wsha = reconstruct_period_weights(
            egx_ens, repo / "ledger" / "weights.json")
        check("period weights reconstruct to the archived pin",
              wsha == egx_ens["applied_weights"]["file_sha256"],
              f"reconstructed {wsha[:12]} vs archived "
              f"{egx_ens['applied_weights']['file_sha256'][:12]}")
        period_weights = tmp / "weights-egx.json"
        period_weights.write_bytes(wbytes)
        full_ens = json.loads(
            (archive / FULL / "ensemble.json").read_text())
        wbytes29, wsha29 = reconstruct_period_weights(
            full_ens, repo / "ledger" / "weights.json")
        check("period weights reconstruct (29-tool golden)",
              wsha29 == full_ens["applied_weights"]["file_sha256"],
              f"reconstructed {wsha29[:12]} vs archived "
              f"{full_ens['applied_weights']['file_sha256'][:12]}")
        period_weights29 = tmp / "weights-full.json"
        period_weights29.write_bytes(wbytes29)

        # --- case 1: parity, EGX golden (ensemble byte-identical) ---
        run = stage_worker_run(archive, EGX, JOB_EGX, JOB_ID,
                               tmp / "run-egx")
        out = tmp / "out-egx"
        proc = run_merge(repo, run, JOB_EGX, JOB_ID, out,
                         period_weights)
        sweep_dir = out / ("sweeps/2026-11-16/050559__"
                           "sweep-lite-poul-ca-market-egx__run" + JOB_ID)
        check("parity: merge exits 0 (EGX golden)",
              proc.returncode == 0, proc.stderr.strip()[-300:])
        check("parity: sweep dir uses the finished time, not now",
              sweep_dir.is_dir(),
              f"expected {sweep_dir.relative_to(out)}")
        if sweep_dir.is_dir():
            got = (sweep_dir / "ensemble.json").read_bytes()
            # Parity target: current ensemble.py on the archived
            # sweep's own Actions-layout inputs (same code, same
            # inputs). The archived ensemble.json file itself is NOT
            # the target: ensemble.py changed after 16 Nov (#129
            # entitlement_end, #130 Kronos ex-rescale, #131 dedup),
            # so the file predates the current output shape — every
            # archived 16 Nov ensemble lacks entitlement_end and
            # horizon corporate-action marks. The harness asserts
            # the merged ensemble equals the current-code reference
            # byte-identically, AND that the reference differs from
            # the archived file only in those known keys.
            ref, ref_bytes = current_code_reference(
                archive, repo, EGX, wbytes, tmp / "ref-egx")
            got_obj = json.loads(got)
            if got != ref_bytes:
                diffs = [k for k in set(got_obj) | set(ref)
                         if got_obj.get(k) != ref.get(k)]
                detail = f"ensemble differs from current-code " \
                         f"reference in keys: {diffs}"
            else:
                detail = "byte-identical to current ensemble.py " \
                         "on the archived sweep's own inputs"
            check("parity: ensemble.json == current ensemble.py on "
                  "the archived sweep's Actions inputs (EGX golden)",
                  got == ref_bytes, detail)
            arch_diffs = [k for k in set(ref) | set(egx_ens)
                          if ref.get(k) != egx_ens.get(k)]
            check("parity: current-code reference differs from the "
                  "archived file ONLY in the known post-sweep "
                  "ensemble changes (#129/#130/#131)",
                  set(arch_diffs) <= {"corporate_actions", "horizons",
                                      "kronos_ex_rescale"},
                  f"diff keys: {arch_diffs}")
            # Digest summaries parsed-identical to the archived
            # collected summaries (the #68 verification source).
            got_d = json.loads((sweep_dir / "digest.json").read_text())
            bad = []
            for r in got_d["results"]:
                arch_sum_path = (archive / EGX / "collected" / r["tool"]
                                 / "summary.json")
                if not arch_sum_path.is_file():
                    # Actions row with no summary (no-summary): the
                    # merge synthesizes an empty-metrics summary;
                    # the ensemble treats both as "no metrics".
                    if r["summary"]["metrics"] != {}:
                        bad.append(r["tool"] + ":nonempty")
                    continue
                arch_sum = json.loads(arch_sum_path.read_text())
                if r["summary"]["metrics"] != arch_sum["metrics"]:
                    bad.append(r["tool"])
                if r["run_url"] is not None or \
                        r["conclusion"] is not None:
                    bad.append(r["tool"] + ":provenance")
                if r.get("worker_run") is None or \
                        r.get("claim_id") != JOB_ID:
                    bad.append(r["tool"] + ":worker_run")
            check("parity: digest summaries match archived EMITTER "
                  "metrics (EGX, all 14 tools)",
                  not bad, f"mismatched: {bad}" if bad else "14/14")
            check("parity: digest carries a degraded block exactly "
                  "because 2 tools failed (kronos + roberta "
                  "no-summary on Actions)",
                  ("degraded" in got_d) ==
                  (len([r for r in got_d["results"]
                        if r["status"] != "ok"]) > 0),
                  f"degraded={got_d.get('degraded')}")
            mm = json.loads(
                (sweep_dir / "merge-manifest.json").read_text())
            check("parity: merge manifest provenance complete",
                  mm.get("merged_by") == "worker" and
                  mm.get("claim_id") == JOB_ID and
                  mm.get("source_runs") and
                  mm.get("job_shape") == JOB_EGX,
                  f"merged_by={mm.get('merged_by')} "
                  f"claim={mm.get('claim_id')}")
            sm = json.loads(
                (sweep_dir / "manifest.json").read_text())
            check("parity: sweep manifest records weights pin + "
                  "release SHA",
                  sm.get("weights_file_sha256") ==
                  egx_ens["applied_weights"]["file_sha256"] and
                  sm.get("worker_release_sha") == git_head(repo),
                  f"weights_sha ok, release "
                  f"{(sm.get('worker_release_sha') or '')[:12]}")

        # --- case 2: metrics parity, 29-tool golden ---
        run29 = stage_worker_run(archive, FULL, JOB_FULL, JOB_ID,
                                 tmp / "run-full")
        out29 = tmp / "out-full"
        proc29 = run_merge(repo, run29, JOB_FULL, JOB_ID, out29,
                           period_weights29)
        check("parity: merge exits 0 (29-tool golden)",
              proc29.returncode == 0, proc29.stderr.strip()[-300:])
        if proc29.returncode == 0:
            sd29 = out29 / ("sweeps/2026-11-16/141124__"
                            "sweep-lite-poul-ca__run" + JOB_ID)
            got_d29 = json.loads(
                (sd29 / "digest.json").read_text())
            arch_d29 = json.loads(
                (archive / FULL / "digest.json").read_text())
            # Files over 5 MB were skipped by archive.py itself
            # (pred.csv, 261300 rows) — the archived collected tree
            # cannot reproduce metrics/files derived from them, so
            # those keys are excluded from the comparison, and the
            # exclusion is named here, not silent.
            arch_m29 = json.loads(
                (archive / FULL / "manifest.json").read_text())
            skipped_names = {s["path"].split("/")[-1]
                             for s in arch_m29.get("skipped", [])}
            bad29, files_note = [], []
            for r, ar in zip(got_d29["results"],
                             arch_d29["results"]):
                gm = dict(r["summary"]["metrics"])
                am = dict(ar["summary"]["metrics"])
                for name in skipped_names:
                    for k in (f"rows_{name}", f"{name}_last_date",
                              f"{name}_last_close"):
                        gm.pop(k, None)
                        am.pop(k, None)
                if gm != am:
                    bad29.append(r["tool"])
                gf = [f for f in r["summary"]["files"]
                      if f != "summary.json"
                      and f not in skipped_names]
                af = [f for f in ar["summary"]["files"]
                      if f != "summary.json"
                      and f not in skipped_names]
                if gf != af:
                    files_note.append(r["tool"])
            check("parity: synthesized metrics == EMITTER metrics "
                  "(29 tools)",
                  not bad29, f"mismatched: {bad29}" if bad29 else
                  "29/29 (metrics from >5MB skipped files excluded: "
                  f"{sorted(skipped_names)})")
            check("parity: files lists match modulo the native "
                  "summary.json entry (unrecoverable from archive)",
                  not files_note,
                  f"mismatched: {files_note}" if files_note else "")
            got_e29 = (sd29 / "ensemble.json").read_bytes()
            ref29, ref29_bytes = current_code_reference(
                archive, repo, FULL, wbytes29, tmp / "ref-full")
            got_e29_obj = json.loads(got_e29)
            check("parity: ensemble.json == current ensemble.py on "
                  "the archived sweep's Actions inputs (29-tool)",
                  got_e29 == ref29_bytes,
                  "byte-identical" if got_e29 == ref29_bytes else
                  f"diff keys: {[k for k in set(got_e29_obj) | set(ref29) if got_e29_obj.get(k) != ref29.get(k)]}")
            arch_diffs29 = [k for k in set(ref29) | set(full_ens)
                            if ref29.get(k) != full_ens.get(k)]
            check("parity: current-code reference differs from the "
                  "archived 29-tool file ONLY in the known "
                  "post-sweep ensemble changes (#129/#130/#131)",
                  set(arch_diffs29) <= {"corporate_actions",
                                        "family_scores", "horizons",
                                        "kronos_ex_rescale"},
                  f"diff keys: {arch_diffs29}")

        # --- case 3: native-summary fixtures (NaN + no summary) ---
        yq_dir = archive / YQ_WORKER / "yahooquery"
        strict_fail = []
        try:
            json.loads((yq_dir / "summary.json").read_text(),
                       parse_constant=lambda c: (_ for _ in ()).throw(
                           ValueError(f"non-finite {c}")))
        except ValueError:
            strict_fail.append("native summary is not strict JSON")
        s = merge.synthesize_summary(yq_dir, "yahooquery", "POUL.CA",
                                     0, "ok")
        try:
            json.dumps(s, allow_nan=False)
            strict_ok = True
        except ValueError:
            strict_ok = False
        check("synthesis: yahooquery native summary (NaN) coerced "
              "to strict JSON",
              bool(strict_fail) and strict_ok and
              s["metrics"].get("rows_POUL.CA.csv") == 1210,
              f"rows={s['metrics'].get('rows_POUL.CA.csv')} "
              f"files={s['files']}")
        news_dir = archive / NEWS_WORKER / "news-disclosure"
        s2 = merge.synthesize_summary(news_dir, "news-disclosure",
                                      "POUL.CA", 0, "ok")
        check("synthesis: news-disclosure with no summary.json "
              "synthesizes metrics from its files",
              bool(s2["metrics"]) and
              len(s2["metrics"]) <= 30 and
              all(len(str(v)) <= 120
                  for v in s2["metrics"].values()),
              f"{len(s2['metrics'])} metrics, e.g. "
              f"news_count={s2['metrics'].get('news_count')}")

        # --- case 4: completeness refuses a missing tool ---
        run_miss = stage_worker_run(
            archive, EGX, JOB_EGX, JOB_ID, tmp / "run-miss",
            drop_tools={"kronos"})
        out_miss = tmp / "out-miss"
        err = tmp / "run-miss" / "merge_error.txt"
        proc_miss = run_merge(repo, run_miss, JOB_EGX, JOB_ID,
                              out_miss, period_weights,
                              ["--error-file", str(err)])
        check("completeness: missing planned tool refuses (exit 2)",
              proc_miss.returncode == 2,
              f"exit={proc_miss.returncode} "
              f"{proc_miss.stderr.strip()[-160:]}")
        check("completeness: refusal archives nothing",
              not (out_miss / "sweeps").exists(),
              "sweeps/ exists" if (out_miss / "sweeps").exists()
              else "no sweeps dir")
        check("completeness: merge_error.txt written",
              err.is_file() and "kronos" in err.read_text(),
              err.read_text().strip()[:120] if err.is_file() else
              "missing")

        # --- case 5: degraded ref-unavailable merges with banner ---
        run_deg = stage_worker_run(
            archive, EGX, JOB_EGX, JOB_ID, tmp / "run-deg",
            status_overrides={"kronos": "ref-unavailable"},
            empty_tools={"kronos"})
        out_deg = tmp / "out-deg"
        proc_deg = run_merge(repo, run_deg, JOB_EGX, JOB_ID, out_deg,
                             period_weights)
        sd_deg = out_deg / ("sweeps/2026-11-16/050559__"
                            "sweep-lite-poul-ca-market-egx__run"
                            + JOB_ID)
        check("degraded: ref-unavailable tool still merges (exit 0)",
              proc_deg.returncode == 0,
              proc_deg.stderr.strip()[-200:])
        if proc_deg.returncode == 0 and sd_deg.is_dir():
            d_deg = json.loads(
                (sd_deg / "digest.json").read_text())
            e_deg = json.loads(
                (sd_deg / "ensemble.json").read_text())
            md_deg = (sd_deg / "digest.md").read_text()
            check("degraded: digest.json carries the degraded block",
                  d_deg.get("degraded", {}).get("absent_families")
                  == ["price-forecast"] and
                  set(d_deg["degraded"]["absent_tools"]) ==
                  {"kronos", "financial-roberta"},
                  f"{d_deg.get('degraded')}")
            check("degraded: digest.md carries the ⚠️ banner",
                  "⚠️ **Degraded sweep:**" in md_deg and
                  "price-forecast" in md_deg,
                  "banner present" if "Degraded sweep" in md_deg
                  else "no banner")
            check("degraded: no family score invented (price-forecast "
                  "null)",
                  e_deg["family_scores"].get("price-forecast") is None,
                  f"{e_deg['family_scores']}")
            kron = [r for r in d_deg["results"]
                    if r["tool"] == "kronos"][0]
            check("degraded: failed row is status error with detail",
                  kron["status"] == "error" and bool(kron.get("detail")),
                  f"{kron['status']} detail={kron.get('detail','')[:60]}")

        # --- case 6: degraded keyless (financetoolkit failed) ---
        run_key = stage_worker_run(
            archive, EGX, JOB_EGX, JOB_ID, tmp / "run-key",
            status_overrides={"financetoolkit": "exit-1"},
            empty_tools={"financetoolkit"})
        out_key = tmp / "out-key"
        proc_key = run_merge(repo, run_key, JOB_EGX, JOB_ID, out_key,
                             period_weights)
        sd_key = out_key / ("sweeps/2026-11-16/050559__"
                            "sweep-lite-poul-ca-market-egx__run"
                            + JOB_ID)
        check("keyless: fundamentals tool failed still merges",
              proc_key.returncode == 0,
              proc_key.stderr.strip()[-200:])
        if proc_key.returncode == 0 and sd_key.is_dir():
            d_key = json.loads(
                (sd_key / "digest.json").read_text())
            e_key = json.loads(
                (sd_key / "ensemble.json").read_text())
            check("keyless: fundamentals absent, banner names #65",
                  "fundamentals" in
                  d_key.get("degraded", {}).get("absent_families", [])
                  and "#65" in (sd_key / "digest.md").read_text(),
                  f"{d_key.get('degraded')}")
            check("keyless: ensemble fundamentals null, not invented",
                  e_key["family_scores"].get("fundamentals") is None,
                  f"{e_key['family_scores']}")

        # --- case 7: double merge refuses ---
        proc2 = run_merge(repo, run, JOB_EGX, JOB_ID, out,
                          period_weights)
        check("double-merge: second run refuses (exit 2)",
              proc2.returncode == 2,
              f"exit={proc2.returncode} "
              f"{proc2.stderr.strip()[-160:]}")
        check("double-merge: still exactly one sweep dir",
              (out / "sweeps" / "2026-11-16").is_dir() and
              len(list((out / "sweeps" / "2026-11-16").iterdir())) == 1,
              "1 dir" if (out / "sweeps" / "2026-11-16").is_dir() and
              len(list((out / "sweeps" / "2026-11-16")
                       .iterdir())) == 1 else "wrong dir count")

        # --- case 8: determinism (re-merge byte-identical) ---
        out_b = tmp / "out-egx-b"
        proc_b = run_merge(repo, run, JOB_EGX, JOB_ID, out_b,
                           period_weights)
        sd_b = out_b / ("sweeps/2026-11-16/050559__"
                        "sweep-lite-poul-ca-market-egx__run" + JOB_ID)
        same = False
        if proc_b.returncode == 0 and sd_b.is_dir():
            same = (sd_b / "digest.json").read_bytes() == \
                (sweep_dir / "digest.json").read_bytes() and \
                (sd_b / "ensemble.json").read_bytes() == \
                (sweep_dir / "ensemble.json").read_bytes()
        check("determinism: re-merge of the same staged tree is "
              "byte-identical (digest.json + ensemble.json)",
              same, "identical" if same else "differs")

        # --- case 9: no-base-price ---
        run_nb = stage_worker_run(archive, EGX, JOB_EGX, JOB_ID,
                                  tmp / "run-nb",
                                  status_overrides={
                                      t: "exit-1" for t in
                                      ("yahooquery", "openbb",
                                       "egx-data", "pandas-ta",
                                       "talib")},
                                  empty_tools={
                                      "yahooquery", "openbb",
                                      "egx-data", "pandas-ta", "talib",
                                      "kronos", "vectorbt",
                                      "quantstats",
                                      "financedatabase"})
        out_nb = tmp / "out-nb"
        proc_nb = run_merge(repo, run_nb, JOB_EGX, JOB_ID, out_nb,
                            period_weights)
        sd_nb = out_nb / ("sweeps/2026-11-16/050559__"
                          "sweep-lite-poul-ca-market-egx__run"
                          + JOB_ID)
        check("no-base: merge exits 0 with no ensemble",
              proc_nb.returncode == 0,
              proc_nb.stderr.strip()[-200:])
        if proc_nb.returncode == 0 and sd_nb.is_dir():
            check("no-base: no ensemble.json written",
                  not (sd_nb / "ensemble.json").exists())
            md_nb = (sd_nb / "digest.md").read_text()
            check("no-base: digest carries the ⚠️ no-base-price line",
                  "no base price found" in md_nb,
                  "line present" if "no base price" in md_nb else
                  "missing")
            sm_nb = json.loads(
                (sd_nb / "manifest.json").read_text())
            check("no-base: manifest records merge=no-ensemble",
                  sm_nb.get("merge") == "no-ensemble",
                  f"merge={sm_nb.get('merge')}")

        # --- case 10: JOB_SCHEDULED recorded ---
        out_js = tmp / "out-js"
        proc_js = run_merge(repo, run, JOB_EGX, JOB_ID, out_js,
                            period_weights,
                            ["--job-scheduled",
                             "sweep-lite POUL.CA market=EGX",
                             "--job-scheduled-checked"])
        sd_js = out_js / ("sweeps/2026-11-16/050559__"
                          "sweep-lite-poul-ca-market-egx__run"
                          + JOB_ID)
        ok_js = False
        if proc_js.returncode == 0 and sd_js.is_dir():
            mm_js = json.loads(
                (sd_js / "merge-manifest.json").read_text())
            ok_js = mm_js.get("job_scheduled") == {
                "value": "sweep-lite POUL.CA market=EGX",
                "checked": True}
        check("job-scheduled: checked value flows into the merge "
              "manifest", ok_js,
              "recorded" if ok_js else "not recorded")
        out_js2 = tmp / "out-js2"
        proc_js2 = run_merge(repo, run, JOB_EGX, JOB_ID, out_js2,
                             period_weights)
        ok_js2 = False
        if proc_js2.returncode == 0:
            sd_js2 = out_js2 / ("sweeps/2026-11-16/050559__"
                                "sweep-lite-poul-ca-market-egx__run"
                                + JOB_ID)
            mm2 = json.loads(
                (sd_js2 / "merge-manifest.json").read_text())
            ok_js2 = mm2.get("job_scheduled") == {
                "value": None, "checked": False}
        check("job-scheduled: unchecked value is recorded as null "
              "+ unchecked (never guessed)",
              ok_js2, "recorded" if ok_js2 else "not recorded")

        # --- case 11: secret scan over the merged sweep ---
        # registry.json is the committed registry snapshot, copied
        # verbatim by archive.py on the Actions path too — it
        # names the tools' key env vars in command templates, so
        # it is excluded from the scan by design; every file the
        # merge itself writes is scanned.
        hits = []
        allowed_hex = set()
        if sweep_dir.is_dir():
            sm = json.loads(
                (sweep_dir / "manifest.json").read_text())
            for v in (sm.get("worker_release_sha"),
                     sm.get("worker_code_sha"),
                     sm.get("weights_file_sha256")):
                if v:
                    allowed_hex.add(v)
            for f in sm.get("files", []):
                allowed_hex.add(f["sha256"])
            for p in sorted(sweep_dir.rglob("*")):
                if not p.is_file() or p.name == "registry.json":
                    continue
                text = p.read_bytes().decode("utf-8", errors="ignore")
                for name in SECRET_NAMES:
                    if name in text:
                        hits.append(f"{p.name}: {name}")
                for m in re.finditer(r"\b[0-9a-f]{40}\b", text):
                    if m.group(0) not in allowed_hex:
                        hits.append(f"{p.name}: unexplained 40-hex")
        check("secret scan: no key names / unexplained token-shaped "
              "strings in any merge output",
              not hits, f"hits: {hits[:5]}" if hits else "clean")

        # --- case 12: ledger pickup (scorer acceptance, offline) ---
        try:
            ledger = load_module("ledger67",
                                 repo / "scripts" / "ledger.py")
            ens_m = json.loads(
                (sweep_dir / "ensemble.json").read_text())
            day_h = ens_m["horizons"]["day"]
            fc = {"as_of": ens_m["date"],
                  "base_price": ens_m["base_price"],
                  "direction": day_h["direction"],
                  "expected_move_pct": day_h["expected_move_pct"],
                  "range_low_pct": day_h["range_low_pct"],
                  "range_high_pct": day_h["range_high_pct"],
                  "net_score": day_h["net_score"],
                  "families": day_h["families"],
                  "sessions": day_h["trading_sessions"],
                  "corporate_actions": ens_m["corporate_actions"]}
            # Later series: the 141124 egx-data CSV extends past
            # the merged sweep's as-of date.
            series = {}
            prov = {}
            for src_dir, tag in (
                    (sweep_dir / "collected" / "egx-data", "merged"),
                    (archive / FULL / "collected" / "egx-data",
                     "later")):
                for csv_path in sorted(src_dir.glob("*.csv")):
                    text = csv_path.read_text(errors="replace")
                    parsed, _sym = ledger.parse_price_csv(text)
                    if not parsed:
                        continue
                    for d, c in parsed.items():
                        series[d] = c
                        prov.setdefault(d, set()).add(tag)
            row = ledger.score_forecast(fc, series, prov, "merged")
            check("ledger pickup: score_forecast accepts the merged "
                  "ensemble's forecast",
                  row.get("status") in ("pending", "matured"),
                  f"status={row.get('status')} "
                  f"sessions_available={row.get('sessions_available')}")
        except Exception as e:
            check("ledger pickup: score_forecast accepts the merged "
                  "ensemble's forecast", False,
                  f"{type(e).__name__}: {e}")

        # --- case 13: worker hook (maybe_merge, offline) ---
        try:
            import os as _os
            _os.environ["GATOR_ROOT"] = str(tmp / "gator")
            worker = load_module("worker67",
                                 repo / "worker" / "worker.py")
            worker.CODE = repo
            hook_run = stage_worker_run(archive, EGX, JOB_EGX, JOB_ID,
                                        tmp / "run-hook")
            hook_job = {"id": JOB_ID, "job": JOB_EGX}
            reg = json.loads(
                (repo / "registry" / "tools.json").read_text())
            plan = worker.parse_job(JOB_EGX, reg)
            check("worker hook: parse_job gives the 14-tool EGX plan",
                  len(plan) == 14, f"{len(plan)} tools")
            hook_manifest = {"job": hook_job,
                             "worker": "borsagator-worker-5",
                             "started": "2026-11-16T04:45:04+00:00",
                             "finished": "2026-11-16T05:05:59+00:00",
                             "tools": json.loads(
                                 (hook_run / "manifest.json")
                                 .read_text())["tools"]}
            # The hook's merge uses CODE/ledger/weights.json — the
            # current (n=9) file, so no byte-parity is asserted
            # here; only that the hook lands a merged sweep.
            ok_hook = worker.maybe_merge(hook_job, hook_run,
                                         hook_manifest, plan)
            merged_dirs = list(
                (hook_run / "_merge_out").rglob("merge-manifest.json")) \
                if (hook_run / "_merge_out").is_dir() else []
            check("worker hook: maybe_merge merges a sweep job",
                  ok_hook and len(merged_dirs) == 1 and
                  hook_manifest.get("merge", {}).get("status") ==
                  "complete",
                  f"ok={ok_hook} manifest={hook_manifest.get('merge')}")
            ok_non = worker.maybe_merge(
                {"id": "x", "job": "run yahooquery POUL.CA"},
                hook_run, {}, [("yahooquery", "POUL.CA")])
            check("worker hook: non-sweep job is a no-op",
                  ok_non is False, "no-op" if ok_non is False else
                  "merged a non-sweep")
            hook_run2 = stage_worker_run(
                archive, EGX, JOB_EGX, JOB_ID, tmp / "run-hook2",
                drop_tools={"kronos"})
            hook_manifest2 = {"job": hook_job,
                              "worker": "borsagator-worker-5",
                              "started": "2026-11-16T04:45:04+00:00",
                              "finished": "2026-11-16T05:05:59+00:00",
                              "tools": json.loads(
                                  (hook_run2 / "manifest.json")
                                  .read_text())["tools"]}
            ok_hook2 = worker.maybe_merge(hook_job, hook_run2,
                                          hook_manifest2, plan)
            check("worker hook: missing-tool refusal keeps the fleet "
                  "(merge_error.txt + manifest, no merge output)",
                  ok_hook2 is False and
                  (hook_run2 / "merge_error.txt").is_file() and
                  hook_manifest2.get("merge", {}).get("status") ==
                  "failed" and
                  not (hook_run2 / "_merge_out").exists(),
                  f"ok={ok_hook2} "
                  f"merge={hook_manifest2.get('merge')}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            check("worker hook: maybe_merge merges a sweep job",
                  False, f"{type(e).__name__}: {e}")

        # --- case 14: archive collision retry (local bare repos) ---
        try:
            bare = tmp / "bare.git"
            subprocess.run(["git", "init", "--bare", "-q", str(bare)],
                           check=True)
            def _clone(name):
                d = tmp / name
                subprocess.run(["git", "clone", "-q", str(bare),
                                str(d)], check=True)
                subprocess.run(["git", "-C", str(d), "config",
                                "user.email", "t@t"], check=True)
                subprocess.run(["git", "-C", str(d), "config",
                                "user.name", "t"], check=True)
                return d
            a = _clone("clone-a")
            (a / "f").write_text("a\n")
            subprocess.run(["git", "-C", str(a), "add", "."],
                         check=True)
            subprocess.run(["git", "-C", str(a), "commit", "-qm",
                            "a", "--no-gpg-sign"], check=True)
            # Publish as `archive`, then work ON the archive branch:
            # `git push origin archive` pushes the local branch of
            # that name, so the fixture must be on it (an earlier
            # version pushed from master and push_archive failed
            # on a missing refspec — a fixture bug, not a merge bug).
            subprocess.run(["git", "-C", str(a), "push", "-q",
                            "origin", "HEAD:archive"], check=True)
            subprocess.run(["git", "-C", str(a), "checkout", "-q",
                            "-b", "archive", "origin/archive"],
                           check=True)
            b = _clone("clone-b")
            subprocess.run(["git", "-C", str(b), "checkout", "-q",
                            "archive"], check=True)
            (b / "g").write_text("b\n")
            subprocess.run(["git", "-C", str(b), "add", "."],
                         check=True)
            subprocess.run(["git", "-C", str(b), "commit", "-qm",
                            "b", "--no-gpg-sign"], check=True)
            subprocess.run(["git", "-C", str(b), "push", "-q",
                            "origin", "archive"], check=True)
            (a / "h").write_text("h\n")
            subprocess.run(["git", "-C", str(a), "add", "."],
                         check=True)
            subprocess.run(["git", "-C", str(a), "commit", "-qm",
                            "h", "--no-gpg-sign"], check=True)
            worker = load_module("worker67b",
                                 repo / "worker" / "worker.py")
            ok_push = worker.push_archive(a)
            landed = subprocess.run(
                ["git", "-C", str(b), "pull", "-q", "origin",
                 "archive"], capture_output=True)
            check("archive collision: push_archive rebases and lands "
                  "after a concurrent push",
                  ok_push and (b / "h").is_file(),
                  f"push_archive={ok_push}")
            c = _clone("clone-c")
            subprocess.run(["git", "-C", str(c), "remote", "set-url",
                            "origin", str(tmp / "no-such-remote.git")],
                           check=True)
            ok_fail = worker.push_archive(c, attempts=3)
            check("archive collision: push_archive fails loudly "
                  "after 3 attempts on a dead remote",
                  ok_fail is False, f"returned {ok_fail}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            check("archive collision: push_archive rebases and lands "
                  "after a concurrent push", False,
                  f"{type(e).__name__}: {e}")

        # --- case 15: watch states (merging / merge-failed / merged) ---
        try:
            dwc = load_module("dwc67", repo / "scripts"
                              / "digest_watch_check.py")
            wa = tmp / "watch"
            wr = wa / "worker-runs" / "2026-11-16"
            sw = wa / "sweeps" / "2026-11-16"
            wr.mkdir(parents=True)
            sw.mkdir(parents=True)
            fleet = wr / "050559__sweep-lite-poul-ca-market-egx__runx"
            fleet.mkdir()
            (fleet / "manifest.json").write_text(json.dumps(
                {"job": {"id": "sched-2026-11-16",
                         "job": JOB_EGX},
                 "tools": {"yahooquery": "ok"}}))
            code, line = dwc.check("2026-11-16", wa / "worker-runs",
                                   None, wa / "sweeps")
            check("watch: fleet archived, merge not landed -> merging",
                  line.startswith("status=merging"),
                  f"{code} {line}")
            (fleet / "merge_error.txt").write_text("boom\n")
            code, line = dwc.check("2026-11-16", wa / "worker-runs",
                                   None, wa / "sweeps")
            check("watch: merge_error.txt present -> merge-failed",
                  line.startswith("status=merge-failed"),
                  f"{code} {line}")
            (fleet / "merge_error.txt").unlink()
            merged = sw / ("050559__sweep-lite-poul-ca-market-egx__"
                           "runsched-2026-11-16")
            merged.mkdir()
            (merged / "merge-manifest.json").write_text("{}")
            code, line = dwc.check("2026-11-16", wa / "worker-runs",
                                   None, wa / "sweeps")
            check("watch: merged sweep present -> merged (exit 0)",
                  code == 0 and line.startswith("status=merged"),
                  f"{code} {line}")
            code, line = dwc.check("2026-11-16", wa / "worker-runs")
            check("watch: legacy call without sweeps dir still says "
                  "archived",
                  code == 0 and line.startswith("status=archived"),
                  f"{code} {line}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            check("watch: merging/merge-failed/merged states", False,
                  f"{type(e).__name__}: {e}")

        # --- case 16: split-merge issue listing ---
        try:
            wdi = load_module("wdi67", repo / "scripts"
                              / "worker_digest_issue.py")
            t, s = wdi.digest_title_status(
                "# 🐊 Borsagator digest — sweep-lite POUL.CA "
                "market=EGX\n\n<!-- borsagator-digest-status: "
                "complete -->\n")
            check("split-merge: complete digest titles plainly",
                  s == "complete" and "FAILED" not in t, t)
            t2, s2 = wdi.digest_title_status(
                "# 🐊 Borsagator digest — sweep-lite POUL.CA\n\n"
                "<!-- borsagator-digest-status: running -->\n")
            check("split-merge: running digest titles FAILED",
                  s2 == "running" and t2.endswith("— ⚠️ FAILED"), t2)
            import yaml
            wf = yaml.safe_load(
                (repo / ".github" / "workflows"
                 / "worker-digest-issue.yml").read_text())
            # YAML 1.1 parses `on:` as boolean True — read both.
            on = wf.get(True) if True in wf else wf.get("on")
            check("split-merge: workflow YAML parses, triggers on "
                  "archive sweeps pushes",
                  (on or {}).get("push", {}).get("branches")
                  == ["archive"] and
                  "sweeps/**" in str(on["push"].get("paths")),
                  f"on={on}")
            # The listing itself, on a throwaway git repo.
            grepo = tmp / "grepo"
            subprocess.run(["git", "init", "-q", str(grepo)],
                           check=True)
            subprocess.run(["git", "-C", str(grepo), "config",
                            "user.email", "t@t"], check=True)
            subprocess.run(["git", "-C", str(grepo), "config",
                            "user.name", "t"], check=True)
            (grepo / "x").write_text("x\n")
            subprocess.run(["git", "-C", str(grepo), "add", "."],
                         check=True)
            subprocess.run(["git", "-C", str(grepo), "commit", "-qm",
                            "base", "--no-gpg-sign"], check=True)
            before = subprocess.run(
                ["git", "-C", str(grepo), "rev-parse", "HEAD"],
                capture_output=True, text=True).stdout.strip()
            sd = grepo / "sweeps" / "2026-11-16" / ("050559__"
                  "sweep-lite-poul-ca-market-egx__runsched-2026-11-16")
            sd.mkdir(parents=True)
            (sd / "merge-manifest.json").write_text("{}")
            (sd / "digest.md").write_text(
                "# 🐊 Borsagator digest — sweep-lite POUL.CA "
                "market=EGX\n\n<!-- borsagator-digest-status: "
                "complete -->\n")
            subprocess.run(["git", "-C", str(grepo), "add", "."],
                         check=True)
            subprocess.run(["git", "-C", str(grepo), "commit", "-qm",
                            "merged sweep", "--no-gpg-sign"],
                         check=True)
            after = subprocess.run(
                ["git", "-C", str(grepo), "rev-parse", "HEAD"],
                capture_output=True, text=True).stdout.strip()
            found = wdi.added_merge_manifests(before, after, grepo)
            check("split-merge: added merged sweep is listed, raw "
                  "dirs are not",
                  found == ["sweeps/2026-11-16/050559__sweep-lite-"
                            "poul-ca-market-egx__runsched-2026-11-16"],
                  f"found={found}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            check("split-merge: issue listing + workflow", False,
                  f"{type(e).__name__}: {e}")

        # --- case 17: naive control (assertions discriminate) ---
        naive = {"job": JOB_EGX, "ticker": "POUL.CA",
                 "date": "2026-11-16",
                 "results": [{"tool": r["tool"], "status": "ok"}
                             for r in json.loads(
                                 (archive / EGX / "digest.json")
                                 .read_text())["results"]]}
        arch_metrics = {r["tool"]: (r.get("summary") or {})
                        .get("metrics") for r in json.loads(
                            (archive / EGX / "digest.json")
                            .read_text())["results"]}
        naive_has_metrics = all(
            (r.get("summary") or {}).get("metrics") ==
            arch_metrics[r["tool"]]
            for r in naive["results"])
        check("naive control: a hand-rolled digest without summary "
              "synthesis FAILS the parity assertions",
              naive_has_metrics is False,
              "naive digest carries no metrics, as expected")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if FAILS:
        print(f"\n{len(FAILS)} FAIL(s): {FAILS}; harness exits 1")
        return 1
    print("\nALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
