#!/usr/bin/env python3
"""Regression tests for issue #147: ref failures retain old runner
outputs, archived as the current run's.

The bug (proven live by probe 003): worker.run_tool early-returned
(ref-unpinned / clone-failed / ref-unavailable) BEFORE `rm -rf
{results}`, and _execute copied RUNNERS/<tool>/results into the run
dir whenever it existed, regardless of status — so a failed tool
shipped the previous run's CSV/log/summary as fresh data, and the
ensemble read those CSVs with no status gate.

The fix:
  1. run_tool clears results/ before any early return.
  2. _execute copies results into the run dir only when
     status == "ok"; a failed tool archives an EMPTY results dir,
     with the failure recorded in the manifest + <tool>.log.
  3. scripts/ensemble.py price_series / realized_sigma take an
     optional ok() predicate (digest status == "ok") and main()
     passes it; the Kronos forecast.csv is read only when Kronos
     is ok — a failed tool's files never vote or set the base.

Harness-first: FAILS on the pristine HEAD (stale files survive the
ref failures, _execute copies them, price_series returns the failed
tool's series) and PASSES on the fixed tree. Stdlib only, no
network — git is stubbed, the runner clones are plain directories
under a temp GATOR_ROOT.

Run: python3 worker/test_worker_147.py (exit 0 = all pass).
"""
import csv
import json
import os
import shutil
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="gator147-test-"))
os.environ["GATOR_ROOT"] = str(_TMP)

_HERE = Path(os.path.abspath(__file__)).parent
_REPO = _HERE.parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_REPO / "scripts"))

import worker  # noqa: E402
import ensemble  # noqa: E402

HEX40 = "a" * 40
PASSED = 0
STALE = {
    "POUL.CA.csv": "Date,Close\n2026-11-15,10.00\n",
    "run.log": "stale log from probe 002\n",
    "summary.json": '{"stale": true}\n',
}


def check(name, cond):
    global PASSED
    assert cond, name
    PASSED += 1
    print(f"pass: {name}")


class FakeResult:
    def __init__(self, rc=0, out="", err=""):
        self.returncode = rc
        self.stdout = out
        self.stderr = err


def fake_sh_factory(fetch_rc=0, clone_rc=0):
    """Fake worker.sh: perform `rm -rf` for real (so we can observe
    whether the clear ran), fail/succeed git fetch + clone on
    demand, succeed everything else (venv, tool command)."""
    def fake_sh(cmd, cwd=None, env=None, timeout=3600):
        if cmd.startswith("rm -rf "):
            shutil.rmtree(cmd[len("rm -rf "):].strip(),
                          ignore_errors=True)
            return FakeResult(0)
        if "git -C" in cmd and "fetch" in cmd:
            return FakeResult(fetch_rc, "",
                              "fatal: couldn't find remote ref")
        if cmd.startswith("git clone"):
            return FakeResult(clone_rc, "", "fatal: unable to connect")
        return FakeResult(0)
    return fake_sh


def seed_results(tool="yahooquery", files=None):
    res = worker.RUNNERS / tool / "results"
    res.mkdir(parents=True, exist_ok=True)
    for name, content in (files or STALE).items():
        (res / name).write_text(content)
    return res


def write_csv(path, closes, start=date(2026, 10, 1)):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Date", "Close"])
        for i, c in enumerate(closes):
            w.writerow([(start + timedelta(days=i)).isoformat(), c])


def main():
    real_sh = worker.sh

    # --- run_tool: the clear must precede every early return ---
    worker.sh = fake_sh_factory()
    res = seed_results()
    status, _ = worker.run_tool("yahooquery", "POUL.CA", "true",
                                "bogus-ref", "yahooquery-runner")
    check("run_tool ref-unpinned returns ref-unpinned",
          status == "ref-unpinned")
    check("run_tool ref-unpinned clears stale results",
          not res.exists() or not any(res.iterdir()))

    worker.sh = fake_sh_factory(fetch_rc=128)
    res = seed_results()
    status, _ = worker.run_tool("yahooquery", "POUL.CA", "true",
                                HEX40, "yahooquery-runner")
    check("run_tool ref-unavailable returns ref-unavailable",
          status == "ref-unavailable")
    check("run_tool ref-unavailable clears stale results",
          not res.exists() or not any(res.iterdir()))

    worker.sh = fake_sh_factory(clone_rc=128)
    shutil.rmtree(worker.RUNNERS / "yahooquery", ignore_errors=True)
    status, _ = worker.run_tool("yahooquery", "POUL.CA", "true",
                                HEX40, "yahooquery-runner")
    check("run_tool clone-failed returns clone-failed",
          status == "clone-failed")

    # Happy path preserved: a valid ref + a zero exit still runs ok
    # (the clear moved, not removed — results/ is empty before the
    # fake tool runs, which writes nothing).
    worker.sh = fake_sh_factory()
    status, _ = worker.run_tool("yahooquery", "POUL.CA", "true",
                                HEX40, "yahooquery-runner")
    check("run_tool ok path still returns ok", status == "ok")

    # --- _execute: the copy is gated on status == "ok" ---
    worker.sh = real_sh  # _execute's copy uses the real shell
    reg = {"tools": [{"id": "yahooquery", "command": "true",
                      "ref": HEX40, "repo": "yahooquery-runner",
                      "category": "price", "status": "active",
                      "markets": ["EGX"]}]}
    published = {}

    def fake_publish(job, results_dir, manifest):
        published["dir"] = Path(results_dir)
        published["manifest"] = manifest
        return True

    orig = (worker.registry, worker.run_tool,
            worker.maybe_merge, worker.publish)
    try:
        worker.registry = lambda: reg
        worker.maybe_merge = lambda *a: False
        worker.publish = fake_publish

        # E1: ref-unavailable + stale results on disk -> the run dir
        # gets an EMPTY tool dir, never the stale files.
        seed_results()
        worker.run_tool = lambda *a: ("ref-unavailable", "")
        worker._execute({"id": "test-147-e1",
                         "job": "run yahooquery POUL.CA"})
        dest = published["dir"] / "yahooquery"
        check("failed tool archives an empty results dir",
              dest.is_dir() and not any(dest.iterdir()))
        check("failed tool status stays in the manifest",
              published["manifest"]["tools"]["yahooquery"]
              == "ref-unavailable")
        check("failed tool log is still archived",
              (published["dir"] / "yahooquery.log").is_file())

        # E2: a tool that dies mid-run after writing partial files
        # must not have those partials archived either.
        def _partial(*a):
            seed_results(files={"POUL.CA.csv":
                                "Date,Close\n2026-11-16,9.50\n",
                                "run.log": "partial output\n"})
            return "exit-1", "boom"
        worker.run_tool = _partial
        worker._execute({"id": "test-147-e2",
                         "job": "run yahooquery POUL.CA"})
        dest = published["dir"] / "yahooquery"
        check("exit-1 partial outputs are not archived",
              dest.is_dir() and not any(dest.iterdir()))
        check("exit-1 status stays in the manifest",
              published["manifest"]["tools"]["yahooquery"] == "exit-1")

        # E3: happy path — an ok tool's fresh results ARE copied.
        def _ok(*a):
            seed_results(files={"POUL.CA.csv":
                                "Date,Close\n2026-11-16,10.00\n"})
            return "ok", ""
        worker.run_tool = _ok
        worker._execute({"id": "test-147-e3",
                         "job": "run yahooquery POUL.CA"})
        dest = published["dir"] / "yahooquery"
        check("ok tool results are still copied",
              (dest / "POUL.CA.csv").is_file())
    finally:
        (worker.registry, worker.run_tool,
         worker.maybe_merge, worker.publish) = orig

    # --- ensemble: failed-tool files excluded from base/voting ---
    sweep = Path(tempfile.mkdtemp(prefix="gator147-sweep-"))
    collected = sweep / "collected"
    registry_path = sweep / "tools.json"
    registry_path.write_text(json.dumps({"tools": [
        {"id": "yahooquery", "category": "price"},
        {"id": "egx-data", "category": "price"},
        {"id": "kronos", "category": "forecast"}]}))
    ensemble.COLLECTED = str(collected)
    ensemble.REGISTRY = str(registry_path)
    # The trap: the FAILED tool's series is the freshest-dated AND
    # the longest/anchored one — without the gate it wins both the
    # base and the sigma pool (probe-003 shape).
    write_csv(collected / "yahooquery" / "POUL.CA.csv",
              [3.13] * 60, start=date(2026, 9, 18))
    write_csv(collected / "egx-data" / "POUL.CA.csv",
              [10.00] * 40, start=date(2026, 10, 7))
    ok = lambda t: t != "yahooquery"
    series = ensemble.price_series("POUL.CA", ok)
    check("price_series excludes the failed tool",
          "yahooquery/poul.ca.csv" not in series
          and "egx-data/poul.ca.csv" in series)
    series_all = ensemble.price_series("POUL.CA")
    check("price_series without ok keeps old behaviour",
          "yahooquery/poul.ca.csv" in series_all)
    # Volatile stale series (alternating 9/10) vs flat ok series:
    # ungated, the longest anchored (stale) series sets sigma.
    write_csv(collected / "yahooquery" / "POUL.CA.csv",
              [9.0 if i % 2 else 10.0 for i in range(60)],
              start=date(2026, 9, 18))
    sigma_all, src_all, _ = ensemble.realized_sigma("POUL.CA", 10.0)
    check("ungated sigma is set by the stale anchored series",
          sigma_all > 0.05 and "yahooquery" in src_all)
    sigma, src, _ = ensemble.realized_sigma("POUL.CA", 10.0, ok)
    check("gated sigma comes from the ok tool only",
          sigma == 0.0 and "egx-data" in src)

    # End to end through main(): base from the ok tool, no Kronos
    # price-forecast from the failed tool's stale forecast.csv.
    write_csv(collected / "yahooquery" / "POUL.CA.csv",
              [3.13] * 40, start=date(2026, 10, 8))
    write_csv(collected / "egx-data" / "POUL.CA.csv",
              [10.00] * 40, start=date(2026, 10, 7))
    (collected / "kronos" / "forecast.csv").parent.mkdir(
        parents=True, exist_ok=True)
    (collected / "kronos" / "forecast.csv").write_text(
        "close,high,low\n" + "\n".join("3.13,3.20,3.05" for _ in range(10))
        + "\n")
    digest = sweep / "digest"
    digest.mkdir(exist_ok=True)
    (digest / "digest.json").write_text(json.dumps({
        "ticker": "POUL.CA", "date": "2026-11-16",
        "job": "test-147",
        "results": [
            {"tool": "yahooquery", "status": "error",
             "summary": {"metrics": {}}},
            {"tool": "egx-data", "status": "ok",
             "summary": {"metrics": {}}},
            {"tool": "kronos", "status": "error",
             "summary": {"metrics": {}}}]}))
    (digest / "digest.md").write_text("# 🐊 Borsagator digest — test-147\n")
    ensemble.DIGEST = str(digest / "digest.json")
    ensemble.OUT_JSON = str(digest / "ensemble.json")
    ensemble.OUT_MD = str(digest / "digest.md")
    ensemble.main()
    out = json.loads((digest / "ensemble.json").read_text())
    check("ensemble base stands on the ok tool (10.00, egx-data)",
          out["base_price"] == 10.0
          and out["base_source"].startswith("egx-data/"))
    check("ensemble has no price-forecast from failed Kronos",
          out["family_scores"].get("price-forecast") is None)

    shutil.rmtree(_TMP, ignore_errors=True)
    shutil.rmtree(sweep, ignore_errors=True)
    print(f"\n{PASSED}/18 passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
