#!/usr/bin/env python3
"""Worker-side digest/ensemble merge (#67).

Ports the Actions merge (digest.json/md + ensemble.json) into the
worker pipeline for worker-run sweep jobs. Shared, stdlib-only, and
runnable by the worker and by the harness — never imports
orchestrate.py (which needs the GitHub App token lifecycle and the
child-repo dispatch machinery, none of which exists on the worker).

Three pure steps, mirroring scripts/archive.py's layout:

1. **stage** — assemble an Actions-shaped tree (digest/ + collected/
   + ledger/weights.json + registry/tools.json) in a temp dir from
   the worker run's local OUT/<job-id> tree (per-tool result dirs +
   the run manifest).
2. **synthesize** — build digest.json + digest.md from the staged
   summaries, using the EMITTER's metric-extraction rules verbatim
   (scripts/orchestrate.py), so a worker-synthesized summary matches
   what Actions would have produced from the same files. A runner
   native summary.json, where one exists, is preserved as
   summary-native.json and is NEVER used for metrics: its shape is
   nested per-ticker with no uniform envelope, and re-wrapping it
   would break the parity bar (harness case 1/2). NaN / Infinity
   values are coerced to null — strict JSON only (the live hazard
   is yahooquery's native summary.json with last_close: NaN).
3. **invoke** — run scripts/ensemble.py unmodified with CWD = the
   staged tree, then run scripts/benchmark_freeze.py the same way
   (issue #79) to freeze the benchmark entrants, then **archive**
   the result under sweeps/<date>/<HHMMSS>__<slug>__run<job-id>/
   with worker provenance in the manifest. The sweep-dir timestamp
   is the sweep's finished time (from the run manifest), not the
   merge time (#67 scoping §4f).

Completeness rule (#67 scoping §4g, adopted as written): a sweep is
mergeable when every tool in the parsed plan has a manifest entry.
A planned tool `missing` from the manifest => the merge REFUSES
(exit 2, merge_error.txt, nothing archived — a partial fleet must
never become a partial ensemble). Any other non-ok tool =>
degraded merge: digest.json carries a `degraded` block and
digest.md carries a ⚠️ banner naming the absent families (see
#65 for tool keys). A sweep with no usable base price still writes
its digest (with ensemble.py's ⚠️ no-base-price line) but writes
no ensemble.json and is recorded as `merge: no-ensemble`.

Digest contract for the #68 compiler (scoping §2b): run_url is
null (the worker has no child-run URL) with `worker_run` +
`claim_id` as the auditable pointer instead; conclusion is null
(the worker has no run conclusion — status carries it); synthesized
summaries are written to collected/<tool>/summary.json AND embedded
in digest.json, parsed-identical.

Split merge (#67 §8 item 4, route 1): the worker archives the
merged sweep; a small Actions workflow opens the digest issue from
the archived digest.md (scripts/worker_digest_issue.py). The
worker PAT is NOT widened to issues:write — that is a Muhammad
decision, not decided here.

Usage (worker hook):
    merge.py --job "sweep-lite POUL.CA market=EGX" --run-dir OUT/<id>
             --registry CODE/registry/tools.json
             --weights CODE/ledger/weights.json
             --ensemble CODE/scripts/ensemble.py
             --release-sha <worker-release HEAD>
             --claim-id sched-2026-11-17 --worker borsagator-worker-5
             --plan yahooquery,openbb,...   (optional; derived if absent)
             --job-scheduled "sweep-lite POUL.CA market=EGX" (optional)
             --out <dir to receive sweeps/...>
Exit codes: 0 = merged (or merged with no ensemble — see --merge
in the manifest); 2 = refused (not a sweep, missing tool, already
merged); 1 = crash.
"""
import argparse
import csv
import glob
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

MERGE_VERSION = 2  # #79: benchmark freeze runs after the ensemble
                     # and benchmark/*.json is copied into the sweep
MAX_FILE = 5 * 1024 * 1024  # same cap as scripts/archive.py
MAX_METRIC_KEYS = 30        # EMITTER caps, verbatim
MAX_METRIC_LEN = 120

# Voting families, in ensemble.py's order. A family is absent when
# no tool of that family in the plan finished ok.
VOTING_FAMILIES = ("price-forecast", "technicals", "sentiment",
                   "agent", "fundamentals")
# Families whose tools need keys #65 has not landed yet: an absence
# here is labelled keyless, not a fleet bug.
KEY_GATED_FAMILIES = ("agent", "fundamentals")

# Manifest status -> digest-row status (#67 scoping §4c item 1).
# The mapping is a table, not inline conditionals — the harness
# tests every row of it.
STATUS_MAP = {
    "ok": "ok",
    "ref-unavailable": "error",
    "clone-failed": "error",
    "bad-code": "error",
    "ref-unpinned": "error",
}

SECRET_NAMES = ("COHERE_API_KEY", "SIMFIN_API_KEY", "GATOR_BUS_URL",
                "GH_TOKEN", "BORSAGATOR_APP_PRIVATE_KEY", "FMP_API_KEY")


class MergeError(Exception):
    """A merge failure that must be recorded, not raised raw."""


class MergeRefused(MergeError):
    """The sweep must not be merged (completeness rule, double
    merge, or not a sweep job). Exit 2."""


def _fnum(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def _parse_ts(value):
    """ISO timestamp -> aware datetime, or None."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def _load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _load_json_lenient(path):
    """Strict JSON only: NaN / Infinity / -Infinity become null
    instead of Python floats (json.load accepts them by default,
    and a bare NaN downstream breaks every strict consumer — the
    live yahooquery native-summary hazard, #67 R8)."""
    with open(path, encoding="utf-8") as f:
        return json.load(f, parse_constant=lambda _c: None)


def _write_text_atomic(path, text):
    """Temp file + os.replace, as in orchestrate.py #113/#120."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".merge-",
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


def _write_json_atomic(path, obj):
    _write_text_atomic(path, json.dumps(obj, indent=2,
                                       ensure_ascii=False) + "\n")


def planned_tools(job, registry):
    """The worker's parse_job selection, re-derived from the job
    string + registry (same grammar, same trailing filters). Only
    sweep / sweep-lite jobs are mergeable; anything else returns []
    and the caller refuses. Mirrors worker.parse_job exactly —
    the harness asserts the two agree on every job shape."""
    tools = {t["id"]: t for t in registry.get("tools", [])
             if t.get("status") == "active"}
    parts = job.split()
    if not parts or parts[0] not in ("sweep", "sweep-lite"):
        return []
    if len(parts) < 2:
        return []
    ticker = parts[1]
    sel = [(t, ticker) for t, v in tools.items()
           if parts[0] == "sweep" or v.get("category") != "agent"]
    for tok in parts[2:]:
        if tok.startswith("market="):
            mkt = tok.split("=", 1)[1].upper()
            sel = [(t, tk) for t, tk in sel
                   if mkt in [m.upper()
                              for m in tools[t].get("markets", [])]]
        elif tok == "no-agent":
            sel = [(t, tk) for t, tk in sel
                   if tools[t].get("category") != "agent"]
        else:
            return []
    return [(t, tk) for t, tk in sel if t in tools]


def map_status(manifest_status):
    """Manifest status -> digest-row status (STATUS_MAP table)."""
    if manifest_status == "ok":
        return "ok"
    if isinstance(manifest_status, str) and \
            manifest_status.startswith("exit-"):
        return "failed"
    return STATUS_MAP.get(manifest_status, "error")


def synthesize_summary(tool_dir, tool, ticker, exit_code, status):
    """The EMITTER's metric extraction (orchestrate.py EMITTER),
    copied verbatim in rule, not in shell: scan results/*.json
    (dict top level only, scalar values, <=120 chars, <=30 keys)
    then CSV row counts + last date/close. A native summary.json is
    skipped in the JSON scan exactly as the EMITTER skips it (it
    writes over it), and is preserved separately by the caller.
    Returns the uniform envelope dict."""
    tool_dir = Path(tool_dir)
    metrics = {}

    def _scan_json(path):
        try:
            data = _load_json_lenient(path)
        except Exception:
            return
        if not isinstance(data, dict):
            return
        for k, v in data.items():
            if isinstance(v, (int, float, str, bool)) \
                    and v is not None \
                    and len(str(v)) <= MAX_METRIC_LEN \
                    and len(metrics) < MAX_METRIC_KEYS:
                # json.load with parse_constant already turned
                # NaN/Infinity into None; a float NaN reaching here
                # (e.g. via a nested parse) is dropped, never kept.
                if isinstance(v, float) and not math.isfinite(v):
                    continue
                metrics[str(k)] = v

    for path in sorted(glob.glob(str(tool_dir / "*.json")) +
                       glob.glob(str(tool_dir / "*" / "*.json"))):
        if os.path.basename(path) == "summary.json":
            continue
        _scan_json(path)
    for path in sorted(glob.glob(str(tool_dir / "*.csv")) +
                       glob.glob(str(tool_dir / "*" / "*.csv"))):
        try:
            with open(path, newline="", encoding="utf-8") as f:
                rows = list(csv.reader(f))
        except Exception:
            continue
        if len(rows) < 2:
            continue
        name = os.path.basename(path)
        metrics["rows_" + name] = len(rows) - 1
        header = [h.strip().lower() for h in rows[0]]
        last = rows[-1]
        for want in ("date", "close"):
            if want in header and len(metrics) < MAX_METRIC_KEYS:
                idx = header.index(want)
                if idx < len(last):
                    metrics[name + "_last_" + want] = last[idx]
    files = sorted(p.name for p in tool_dir.iterdir()
                   if p.is_file()) if tool_dir.is_dir() else []
    return {"tool": tool, "ticker": ticker, "borsagator": True,
            "exit_code": exit_code, "status": status,
            "metrics": metrics, "files": files}


def _tool_detail(tool_dir, log_tail):
    """One-line detail for a failed tool, from its log tail."""
    text = (log_tail or "").strip()
    if not text:
        return ""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return ""
    return lines[-1][:200].replace("|", "\\|").replace("\n", " ")


def build_digest(job, ticker, date_str, started, finished, plan,
                 registry, manifest_tools, run_dir, worker_run,
                 claim_id):
    """Build the digest rows + degraded block. Raises MergeRefused
    when a planned tool is missing from the manifest (completeness
    rule). Returns (digest, degraded, log_tails_used)."""
    tools_by_id = {t["id"]: t for t in registry.get("tools", [])}
    results = []
    absent_tools = []
    for tool, _tk in plan:
        if tool not in manifest_tools:
            # Completeness rule: a planned tool with no manifest
            # entry means the worker died mid-plan — refuse.
            raise MergeRefused(
                f"planned tool {tool} missing from the run manifest")
        mstatus = manifest_tools[tool]
        status = map_status(mstatus)
        if mstatus == "ok":
            exit_code = 0
        elif isinstance(mstatus, str) and mstatus.startswith("exit-"):
            try:
                exit_code = int(mstatus[len("exit-"):])
            except ValueError:
                exit_code = None
        else:
            exit_code = None
        tool_dir = Path(run_dir) / tool
        summary = synthesize_summary(
            tool_dir, tool, ticker, exit_code, status)
        log_path = Path(run_dir) / f"{tool}.log"
        log_tail = log_path.read_text(encoding="utf-8",
                                      errors="replace")[-4000:] \
            if log_path.is_file() else ""
        row = {"tool": tool,
               "repo": tools_by_id.get(tool, {}).get("repo",
                                                     f"{tool}-runner"),
               "category": tools_by_id.get(tool, {}).get("category",
                                                         "—"),
               "status": status,
               "run_url": None,
               "conclusion": None,
               "summary": summary,
               "worker_run": worker_run,
               "claim_id": claim_id}
        if status != "ok":
            row["detail"] = _tool_detail(tool_dir, log_tail) or \
                f"worker status {mstatus}"
            absent_tools.append(tool)
        results.append(row)
    # Degraded: a voting family is absent when no tool of that
    # family in the plan finished ok. Families absent by SHAPE
    # (e.g. agent in sweep-lite — no agent tool in the plan at
    # all) are not degraded: Actions sweep-lite digests carry no
    # degraded block for exactly that shape.
    fam_tools = {}
    for tool, _tk in plan:
        fam = tools_by_id.get(tool, {}).get("family")
        if fam:
            fam_tools.setdefault(fam, []).append(tool)
    absent_families = []
    for fam in VOTING_FAMILIES:
        tools = fam_tools.get(fam)
        if not tools:
            continue  # absent by shape, not by failure
        if not any(manifest_tools.get(t) == "ok" for t in tools):
            absent_families.append(fam)
    degraded = None
    if absent_tools or absent_families:
        reason = "keyless" if absent_families and \
            all(f in KEY_GATED_FAMILIES for f in absent_families) \
            and not absent_tools else "partial-fleet"
        degraded = {"reason": reason,
                    "absent_families": absent_families,
                    "absent_tools": absent_tools}
    digest = {"job": job, "ticker": ticker, "date": date_str,
              "started": started, "finished": finished,
              "results": results}
    if degraded is not None:
        digest["degraded"] = degraded
    return digest, degraded


def build_digest_md(job, started, finished, digest, degraded):
    """The orchestrator's digest table, same columns and guards
    (#113 header, #120 status marker, | sanitisation). The Run
    column is "—": worker rows carry no run_url; provenance is
    worker_run + claim_id in digest.json."""
    header = f"# 🐊 Borsagator digest — {job}"
    lines = [header,
             "<!-- borsagator-digest-status: complete -->", "",
             f"Started {started.strftime('%Y-%m-%d %H:%M UTC')} · "
             f"finished {finished.strftime('%H:%M UTC')} · "
             f"{len(digest['results'])} tools", ""]
    if degraded is not None:
        fams = ", ".join(degraded["absent_families"]) or "—"
        tools = ", ".join(degraded["absent_tools"]) or "—"
        lines += [
            f"⚠️ **Degraded sweep:** {tools} did not finish cleanly — "
            f"families absent: {fams}. This digest is published with "
            f"the banner so a 3-family ensemble is never read as a "
            f"5-family one (see #65 for tool keys).", ""]
    lines += ["| Tool | Category | Status | Key results | Run |",
              "|---|---|---|---|---|"]
    for r in digest["results"]:
        summary = r.get("summary") or {}
        metrics = summary.get("metrics") or {}
        verdict_keys = [k for k in metrics if any(
            w in k.lower() for w in
            ("rating", "decision", "verdict", "signal",
             "recommendation"))]
        ordered = [(k, metrics[k]) for k in verdict_keys] + \
            [(k, v) for k, v in metrics.items()
             if k not in verdict_keys]
        keys = "; ".join(f"{k}={v}" for k, v in ordered[:5]) or \
            r.get("detail", "") or "—"
        keys = keys.replace("|", "\\|").replace("\n", " ") \
            .replace("\r", " ")
        lines.append(f"| {r.get('tool', '?')} | "
                     f"{r.get('category', '—')} | "
                     f"{r.get('status', '?')} | {keys} | — |")
    lines += ["",
              "_Verdicts are each tool's own, preserved as reported — "
              "Borsagator never averages them into one score._"]
    return "\n".join(lines) + "\n"


def sweep_dir_name(finished, job, job_id):
    """sweeps/<date>/<HHMMSS>__<slug>__run<job-id>/ — the timestamp
    is the sweep's finished time, not the merge time (#67 §8.8)."""
    slug = re.sub(r"[^a-z0-9]+", "-", job.lower()).strip("-")[:60] \
        or "job"
    return (f"sweeps/{finished:%Y-%m-%d}/"
            f"{finished:%H%M%S}__{slug}__run{job_id}")


def merge(job, run_dir, registry_path, weights_path, ensemble_path,
          release_sha, claim_id, worker, out_dir, plan=None,
          job_scheduled=None, job_scheduled_checked=False):
    """Run the full merge. Returns the sweep manifest dict.
    Raises MergeRefused (exit 2) or MergeError (exit 1)."""
    run_dir = Path(run_dir)
    out_dir = Path(out_dir)
    registry = _load_json(registry_path)
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.is_file():
        raise MergeRefused(f"no manifest.json in run dir {run_dir}")
    run_manifest = _load_json(manifest_path)
    manifest_tools = run_manifest.get("tools") or {}
    if not isinstance(manifest_tools, dict):
        raise MergeRefused("run manifest tools is not an object")
    parts = job.split()
    if not parts or parts[0] not in ("sweep", "sweep-lite"):
        raise MergeRefused(f"not a sweep job: {job!r}")
    if len(parts) < 2:
        raise MergeRefused(f"sweep job without a ticker: {job!r}")
    ticker = parts[1].upper()
    if not re.fullmatch(r"[A-Za-z0-9.\-]{1,12}", ticker):
        raise MergeRefused(f"refusing unsafe ticker: {ticker!r}")
    if plan is None:
        plan = planned_tools(job, registry)
    if not plan:
        raise MergeRefused(f"no tools selected for job {job!r} "
                           f"(unknown filter or empty plan)")
    started = _parse_ts(run_manifest.get("started")) \
        or datetime.now(timezone.utc)
    finished = _parse_ts(run_manifest.get("finished")) \
        or datetime.now(timezone.utc)
    date_str = finished.astimezone(timezone.utc).strftime("%Y-%m-%d")
    job_id = claim_id or (run_manifest.get("job") or {}).get("id") \
        or run_dir.name
    worker_run = f"worker-runs/{finished:%Y-%m-%d}/{run_dir.name}"
    target_rel = sweep_dir_name(finished, job, job_id)
    target = out_dir / target_rel
    if (target / "merge-manifest.json").exists():
        raise MergeRefused(f"already merged: {target_rel} carries a "
                           f"merge manifest — refusing a second merge")
    if target.exists():
        raise MergeRefused(f"already merged: {target_rel} exists")

    digest, degraded = build_digest(
        job, ticker, date_str, started.isoformat(),
        finished.isoformat(), plan, registry,
        manifest_tools, run_dir, worker_run, claim_id)

    # Stage the Actions-shaped tree in a temp dir.
    stage = Path(tempfile.mkdtemp(prefix="borsagator-merge-"))
    try:
        weights_bytes = Path(weights_path).read_bytes()
        weights_sha = _sha256_bytes(weights_bytes)
        (stage / "ledger").mkdir(parents=True)
        (stage / "ledger" / "weights.json").write_bytes(weights_bytes)
        (stage / "registry").mkdir(parents=True)
        shutil.copy2(registry_path, stage / "registry" / "tools.json")
        collected = stage / "collected"
        for tool, _tk in plan:
            src = run_dir / tool
            dest = collected / tool
            dest.mkdir(parents=True, exist_ok=True)
            if src.is_dir():
                for item in sorted(src.iterdir()):
                    if item.name == "summary.json":
                        # Preserve the runner-native summary for
                        # the record; the uniform envelope (written
                        # below) is what digest.json embeds.
                        shutil.copy2(item, dest / "summary-native.json")
                        continue
                    if item.is_file():
                        shutil.copy2(item, dest / item.name)
                    elif item.is_dir():
                        shutil.copytree(item, dest / item.name)
            # The uniform summary: written to collected/ AND
            # embedded in digest.json, parsed-identical (#68 §2c).
            row = next(r for r in digest["results"]
                       if r["tool"] == tool)
            summary_text = json.dumps(row["summary"], indent=2,
                                      ensure_ascii=False) + "\n"
            (dest / "summary.json").write_text(
                summary_text, encoding="utf-8")
        digest_dir = stage / "digest"
        digest_dir.mkdir(parents=True, exist_ok=True)
        _write_json_atomic(digest_dir / "digest.json", digest)
        md = build_digest_md(job, started, finished, digest, degraded)
        _write_text_atomic(digest_dir / "digest.md", md)

        # Invoke ensemble.py unmodified, CWD = the staged tree.
        # The weights path is RELATIVE ("ledger/weights.json", the
        # staged copy): ensemble records the path verbatim in
        # applied_weights.file, and an absolute temp path would
        # break parity with an Actions-built ensemble.
        env = dict(os.environ)
        env["BORSAGATOR_WEIGHTS"] = "ledger/weights.json"
        proc = subprocess.run(
            [sys.executable, str(ensemble_path)],
            cwd=str(stage), env=env, capture_output=True, text=True,
            timeout=3600)
        if proc.stdout.strip():
            print(proc.stdout, end="")
        if proc.stderr.strip():
            print(proc.stderr, end="", file=sys.stderr)
        ensemble_path_out = digest_dir / "ensemble.json"
        has_ensemble = ensemble_path_out.is_file()
        merge_status = "complete" if has_ensemble else "no-ensemble"
        if not has_ensemble:
            # ensemble.py already appended its ⚠️ no-base-price (or
            # failure) line to digest.md; the digest still ships.
            print("merge: no ensemble produced (no base price or "
                  "ensemble failure) — digest ships without one",
                  file=sys.stderr)

        # Issue #79: freeze the benchmark entrants from this sweep's
        # ensemble + Kronos path, CWD = the staged tree (same
        # invocation shape as ensemble.py above). The freeze never
        # fails the merge: a missing script (a pre-#79 worker
        # release) or a failed run leaves the sweep without
        # benchmark/ — legal, like a pre-#79 sweep. BENCHMARK_RUN_ID
        # is the claim id, so the frozen `sweep` field names this
        # merge's sweep dir.
        freeze_path = Path(ensemble_path).with_name("benchmark_freeze.py")
        if freeze_path.is_file():
            fenv = dict(env)
            fenv["BENCHMARK_RUN_ID"] = claim_id or ""
            fproc = subprocess.run(
                [sys.executable, str(freeze_path)],
                cwd=str(stage), env=fenv, capture_output=True, text=True,
                timeout=600)
            if fproc.stdout.strip():
                print(fproc.stdout, end="")
            if fproc.stderr.strip():
                print(fproc.stderr, end="", file=sys.stderr)
        else:
            print("merge: no benchmark_freeze.py next to ensemble.py "
                  "— sweep ships without benchmark/",
                  file=sys.stderr)

        # Archive into sweeps/ with the archive.py shape + worker
        # provenance. Files over 5 MB are skipped and recorded.
        files, skipped = [], []

        def _copy(src, rel):
            size = os.path.getsize(src)
            if size > MAX_FILE:
                skipped.append({"path": rel, "bytes": size,
                                "reason": "over 5 MB cap"})
                return
            out = target / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, out)
            files.append({"path": rel, "bytes": size,
                          "sha256": _sha256_file(out)})

        target.mkdir(parents=True)
        # Leave a trace in the digest, as archive.py does — before
        # copying, so the manifest's sha256 covers the archived bytes.
        try:
            with open(digest_dir / "digest.md", "a",
                      encoding="utf-8") as f:
                f.write(f"\n_Merged on the worker ({worker}) at "
                        f"`{target_rel}`; point-in-time inputs in "
                        f"`{worker_run}`._\n")
        except OSError:
            pass
        _copy(digest_dir / "digest.json", "digest.json")
        if has_ensemble:
            _copy(ensemble_path_out, "ensemble.json")
        _copy(digest_dir / "digest.md", "digest.md")
        if (digest_dir / "ensemble_error.txt").is_file():
            _copy(digest_dir / "ensemble_error.txt",
                  "ensemble_error.txt")
        _copy(stage / "registry" / "tools.json", "registry.json")
        # Issue #79: explicit copy loop for the frozen benchmark
        # entrants (like ensemble.json above — the collected/** walk
        # below would NOT pick them up, and a benchmark/ dir at the
        # staged root would otherwise be silently dropped).
        bench_dir = stage / "benchmark"
        if bench_dir.is_dir():
            for name in sorted(os.listdir(bench_dir)):
                src = bench_dir / name
                if src.is_file():
                    _copy(src, f"benchmark/{name}")
        # Issue #280: stage the #278 disclosure-events feed file
        # for this ticker into the sweep dir, so the Report Model
        # compiler (v2) can surface it. Absent on Actions sweeps
        # and pre-#278 runs: the compiler records "missing", never
        # a failure. The file is staged as-is and validated by the
        # compiler — a malformed feed surfaces as "unavailable"
        # with the reason named, never as a merge refusal.
        events_src = run_dir / "disclosure-events" / (
            f"{ticker.split('.')[0]}-events.json")
        if events_src.is_file():
            _copy(events_src,
                  f"disclosure-events/{ticker.split('.')[0]}"
                  f"-events.json")
        for dirpath, _dirs, names in os.walk(collected):
            _dirs.sort()  # deterministic manifest file order
            for name in sorted(names):
                src = os.path.join(dirpath, name)
                rel = os.path.relpath(src, stage).replace(os.sep, "/")
                _copy(src, rel)
        tools_map = {r.get("tool"): r.get("status")
                     for r in digest.get("results", [])}
        now = datetime.now(timezone.utc)
        sweep_manifest = {
            "job": job,
            "job_shape": job,
            "ticker": ticker,
            "digest_date": date_str,
            "archived_at": now.isoformat(),
            "github_run_id": None,
            "run_id": job_id,
            "target": target_rel,
            "tools": tools_map,
            "files": files,
            "skipped": skipped,
            "merged_by": "worker",
            "worker": worker,
            "worker_code_sha": release_sha,
            "worker_release_sha": release_sha,
            "claim_id": claim_id,
            "source_runs": [worker_run],
            "weights_file": "ledger/weights.json",
            "weights_file_sha256": weights_sha,
            "degraded": degraded,
            "merge": merge_status,
        }
        _write_json_atomic(target / "manifest.json", sweep_manifest)
        # Merge marker for the split-merge issue workflow (#67 §4d):
        # only a sweep dir carrying this file may open a digest
        # issue; a raw worker-run archive push must never do so.
        # JOB_SCHEDULED is recorded here as checked-and-known or
        # explicitly unchecked: the live repo variable is set by
        # the cycle (to `sweep-lite POUL.CA market=EGX` if unset) —
        # the merge records what it was told, never a guess.
        merge_manifest = {
            "merged_by": "worker",
            "merge_version": MERGE_VERSION,
            "job": job,
            "job_shape": job,
            "claim_id": claim_id,
            "source_runs": [worker_run],
            "sweep_dir": target_rel,
            "finished": finished.isoformat(),
            "merge": merge_status,
            "degraded": degraded,
            "job_scheduled": {
                "value": job_scheduled,
                "checked": bool(job_scheduled_checked),
            },
        }
        _write_json_atomic(target / "merge-manifest.json",
                           merge_manifest)
        print(f"merge: {target_rel} | {len(files)} files, "
              f"{len(skipped)} skipped, merge={merge_status}")
        return sweep_manifest
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Worker-side digest/ensemble merge (#67).")
    ap.add_argument("--job", required=True)
    ap.add_argument("--run-dir", required=True,
                    help="worker OUT/<job-id> tree (per-tool dirs + "
                         "manifest.json)")
    ap.add_argument("--registry", required=True)
    ap.add_argument("--weights", required=True,
                    help="ledger/weights.json from the release checkout")
    ap.add_argument("--ensemble", required=True,
                    help="scripts/ensemble.py to run unmodified")
    ap.add_argument("--release-sha", default="",
                    help="worker-release HEAD the merge ran from")
    ap.add_argument("--claim-id", default="")
    ap.add_argument("--worker", default="")
    ap.add_argument("--plan", default="",
                    help="comma-separated planned tools (default: "
                         "derive from --job + registry)")
    ap.add_argument("--job-scheduled", default=None,
                    help="value of the repo JOB_SCHEDULED variable, "
                         "when the caller checked it")
    ap.add_argument("--job-scheduled-checked", action="store_true",
                    help="the caller actually checked JOB_SCHEDULED")
    ap.add_argument("--out", required=True,
                    help="dir to receive sweeps/<date>/...")
    ap.add_argument("--error-file", default="",
                    help="also write merge_error.txt here on refusal "
                         "or failure")
    args = ap.parse_args(argv)
    plan = None
    if args.plan:
        ticker = args.job.split()[1] if len(args.job.split()) > 1 \
            else ""
        plan = [(t.strip(), ticker) for t in args.plan.split(",")
                if t.strip()]
    try:
        merge(args.job, args.run_dir, args.registry, args.weights,
              args.ensemble, args.release_sha, args.claim_id,
              args.worker, args.out, plan=plan,
              job_scheduled=args.job_scheduled,
              job_scheduled_checked=args.job_scheduled_checked)
    except MergeRefused as e:
        print(f"merge refused: {e}", file=sys.stderr)
        if args.error_file:
            try:
                Path(args.error_file).write_text(
                    f"merge refused: {e}\n", encoding="utf-8")
            except OSError:
                pass
        return 2
    except MergeError as e:
        print(f"merge failed: {e}", file=sys.stderr)
        if args.error_file:
            try:
                Path(args.error_file).write_text(
                    f"merge failed: {e}\n", encoding="utf-8")
            except OSError:
                pass
        return 1
    except Exception as e:  # noqa: BLE001 - record, never lose the fleet
        print(f"merge crashed: {type(e).__name__}: {e}",
              file=sys.stderr)
        if args.error_file:
            try:
                Path(args.error_file).write_text(
                    f"merge crashed: {type(e).__name__}: {e}\n",
                    encoding="utf-8")
            except OSError:
                pass
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
