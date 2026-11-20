#!/usr/bin/env python3
"""Regression + replay tests for issue #278 (live disclosure-events
feed, option A sweep-live).

The wiring under test (worker/worker.py):
  phase 1 refresh_disclosure_feed — forced pre-sweep EGX harvest for
    POUL/COMI before any tool runs;
  phase 2 extract_disclosure_events — extraction after the tool loop
    and BEFORE maybe_merge (extraction-before-ensemble), with
    ordering/provenance tied to one sweep id;
  freshness/failure policy — refreshed / cached (<=12 h) / failed
    (extraction skipped, never silent), extraction-failed, and the
    stale-input gate between the phases.

Deterministic replay (no network, no real disclosure needed): the
fixture harvests are built from the #109 goldens
(scripts/disclosure_events_fixtures/fixtures.json) — the POUL coupon-42
document re-dated to a 19/11/2026 after-close publication, and the
COMI 297291 earnings document whose item date is the wrong 2026-01-01
(the #274 harvester bug) while its standalone line says 10/11/2026.
The fake harvester writes those harvests; the REAL extractor runs.

Harness-first: FAILS on pristine main (worker has no
refresh_disclosure_feed / extract_disclosure_events — AttributeError —
and _execute_body never writes disclosure events) and PASSES on the
fixed tree. Stdlib only, no network — git/venv are stubbed, the
runner clones are never created, publish/merge/compile/render are
stubbed at the worker-module boundary while _execute_body itself
runs for real.

Run: python3 worker/test_worker_278.py (exit 0 = all pass).
"""
import json
import os
import shutil
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _test_tmp  # noqa: E402  (atexit cleanup of scratch dirs, #388)
_TMP = _test_tmp.mkdtemp(prefix="gator278-test-")
os.environ["GATOR_ROOT"] = str(_TMP)

_HERE = Path(os.path.abspath(__file__)).parent
_REPO = _HERE.parent
sys.path.insert(0, str(_HERE))

import worker  # noqa: E402

PASSED = 0
TIMELINE = []
PUBLISH_SEEN = {}
MARK_DONE_SEEN = {}
FAKE_HARVEST = {"mode": "ok"}  # "ok" | "fail"
FIXTURES = json.loads(
    (_REPO / "scripts" / "disclosure_events_fixtures"
     / "fixtures.json").read_text(encoding="utf-8"))
CASES = {c["name"]: c["doc"] for c in FIXTURES["cases"]}


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


def fake_sh(cmd, cwd=None, env=None, timeout=3600):
    """Fake worker.sh: perform `rm -rf` for real, create venv
    interpreters like the real command, succeed every git call."""
    if cmd.startswith("rm -rf "):
        shutil.rmtree(cmd[len("rm -rf "):].strip(), ignore_errors=True)
        return FakeResult(0)
    if cmd.startswith("python3 -m venv "):
        venv = Path(cmd[len("python3 -m venv "):].strip())
        (venv / "bin").mkdir(parents=True, exist_ok=True)
        (venv / "bin" / "python").write_text("#!/bin/sh\n")
        return FakeResult(0)
    return FakeResult(0)


def utc_now_z():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def poul_doc():
    """Golden POUL coupon-42 doc, re-dated to an after-close
    publication: standalone line 02/11/2026 -> 19/11/2026."""
    doc = json.loads(json.dumps(CASES["golden_poul_dividend"]))
    assert doc["body"].count("02/11/2026") == 1
    doc["body"] = doc["body"].replace("02/11/2026", "19/11/2026")
    doc["date"] = "2026-11-19"
    return doc


def comi_doc():
    """Golden COMI 297291 earnings doc as harvested: item date is the
    wrong 2026-01-01 (the #274 bug); the standalone line 10/11/2026
    is the real publish date."""
    return json.loads(json.dumps(
        CASES["golden_comi_earnings_consolidated"]))


def harvest_for(code):
    docs = {"POUL": [poul_doc()], "COMI": [comi_doc()]}
    names = {"POUL": ("القاهرة للدواجن", "EGS02051C018"),
             "COMI": ("البنك التجاري الدولي", "EGS60121C018")}
    ar_name, isin = names[code]
    return {"ticker": f"{code}.CA", "company_ar": ar_name, "isin": isin,
            "harvested_at": utc_now_z(), "count": len(docs[code]),
            "items": docs[code]}


def fake_run_harvest(job, workdir):
    """Fake worker.run_harvest: writes the fixture harvest for the
    requested code (mode 'ok') or fails without writing ('fail')."""
    code = job["job"].split()[1].upper().replace(".CA", "")
    if FAKE_HARVEST["mode"] != "ok":
        return {"egx-harvest": "exit-3"}
    run_dir = Path(workdir) / "egx-harvest" / "results"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "disclosures.json").write_text(
        json.dumps(harvest_for(code), ensure_ascii=False, indent=1),
        encoding="utf-8")
    return {"egx-harvest": "ok"}


def seed_cache(code, age_hours):
    """Write a fixture harvest into the on-box cache, aged
    `age_hours` (both harvested_at and mtime)."""
    cache_dir = worker.ROOT / "harvest"
    cache_dir.mkdir(parents=True, exist_ok=True)
    doc = harvest_for(code)
    when = datetime.now(timezone.utc) - timedelta(hours=age_hours)
    doc["harvested_at"] = when.strftime("%Y-%m-%dT%H:%M:%SZ")
    p = cache_dir / f"{code}.json"
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=1),
                 encoding="utf-8")
    ts = when.timestamp()
    os.utime(p, (ts, ts))
    return p


def setup_release():
    """Fake release checkout: the REAL extractor script + a minimal
    registry with only the news-disclosure tool (command 'true')."""
    code = worker.CODE
    (code / "scripts").mkdir(parents=True, exist_ok=True)
    shutil.copy(_REPO / "scripts" / "disclosure_events.py",
                code / "scripts" / "disclosure_events.py")
    (code / "registry").mkdir(parents=True, exist_ok=True)
    (code / "registry" / "tools.json").write_text(json.dumps({
        "tools": [{
            "id": "news-disclosure", "repo": "news-disclosure-runner",
            "ref": "a" * 40, "category": "news", "status": "active",
            "markets": ["EGX", "US"], "command": "true"}]}),
        encoding="utf-8")


# --- stubs for the _execute_body boundary (the pipeline under test
# runs for real; only its neighbours are stubbed) ---
def stub_maybe_merge(job, workdir, manifest, plan):
    ev = Path(workdir) / "disclosure-events" / "POUL-events.json"
    TIMELINE.append(("merge", ev.is_file()))
    return False


def stub_maybe_compile(job, workdir, manifest, plan):
    TIMELINE.append(("compile", None))
    return False


def stub_maybe_render(job, workdir, manifest, plan):
    TIMELINE.append(("render", None))
    return False


def stub_publish(job, results_dir, manifest):
    PUBLISH_SEEN.clear()
    PUBLISH_SEEN["job"] = job
    PUBLISH_SEEN["manifest"] = json.loads(json.dumps(manifest))
    wd = Path(results_dir)
    PUBLISH_SEEN["events_file"] = (
        wd / "disclosure-events" / "POUL-events.json").is_file()
    PUBLISH_SEEN["feed_file"] = (wd / "disclosure_feed.json").is_file()
    PUBLISH_SEEN["error_file"] = (
        wd / "disclosure_feed_error.txt").is_file()
    return "fake-archive-sha-278"


def stub_mark_done(job, archive_sha):
    MARK_DONE_SEEN.clear()
    MARK_DONE_SEEN["job"] = job
    MARK_DONE_SEEN["archive"] = archive_sha
    return True


def run_sweep(job_id, job_text):
    """Drive the REAL _execute_body for one sweep job with the
    boundary stubs in place. Returns (workdir, manifest)."""
    TIMELINE.clear()
    PUBLISH_SEEN.clear()
    MARK_DONE_SEEN.clear()
    job = {"id": job_id, "job": job_text, "added": worker.now()}
    worker._execute_body(job)
    return worker.OUT / job_id, PUBLISH_SEEN["manifest"]


def main():
    real_sh = worker.sh
    real_harvest = worker.run_harvest
    real_merge = worker.maybe_merge
    real_compile = worker.maybe_compile
    real_render = worker.maybe_render
    real_publish = worker.publish
    real_mark_done = worker._mark_done
    real_refresh = worker.refresh_disclosure_feed
    real_extract = worker.extract_disclosure_events
    worker.sh = fake_sh
    worker.run_harvest = fake_run_harvest
    worker.maybe_merge = stub_maybe_merge
    worker.maybe_compile = stub_maybe_compile
    worker.maybe_render = stub_maybe_render
    worker.publish = stub_publish
    worker._mark_done = stub_mark_done
    setup_release()

    def wrap_refresh(job, workdir, manifest, plan):
        rec = real_refresh(job, workdir, manifest, plan)
        TIMELINE.append(("refresh", rec["status"] if rec else None))
        return rec

    def wrap_extract(job, workdir, manifest, plan):
        rec = real_extract(job, workdir, manifest, plan)
        TIMELINE.append(("extract", rec["status"] if rec else None))
        return rec

    worker.refresh_disclosure_feed = wrap_refresh
    worker.extract_disclosure_events = wrap_extract

    # --- pure helpers ---
    qs, qe = worker._quarter_window("2026-11-20T06:15:00+00:00")
    check("quarter window is 90 days ending on the sweep date",
          (qs, qe) == (date(2026, 8, 22), date(2026, 11, 20)))
    in_scope, out = worker._egx_tickers_in_plan([
        ("news-disclosure", "POUL.CA"),
        ("news-disclosure", "COMI.CA"),
        ("news-disclosure", "ETEL.CA"),
        ("yahooquery", "POUL.CA")])
    check("tickers in plan: POUL/COMI in scope, ETEL out of scope",
          in_scope == ["POUL", "COMI"] and out == ["ETEL"])

    # --- integration: scheduled sweep (the acceptance path) ---
    FAKE_HARVEST["mode"] = "ok"
    wd, manifest = run_sweep("sched-2026-11-20",
                             "sweep-lite POUL.CA market=EGX")
    feed = manifest.get("disclosure_feed") or {}
    check("scheduled sweep: refresh -> extract -> merge -> "
          "compile -> render order in the real pipeline",
          [t[0] for t in TIMELINE] ==
          ["refresh", "extract", "merge", "compile", "render"])
    check("scheduled sweep: merge ran only after extraction "
          "wrote the events file",
          dict(TIMELINE).get("merge") is True)
    check("scheduled sweep: origin is scheduled, sweep id recorded",
          feed.get("origin") == "scheduled"
          and feed.get("sweep_id") == "sched-2026-11-20")
    check("scheduled sweep: no intraday alerting promised",
          feed.get("mode") == "sweep-live"
          and feed.get("intraday_alerting") is False)
    check("scheduled sweep: feed ok, harvest refreshed in-window",
          feed.get("status") == "ok"
          and feed["tickers"]["POUL"]["refresh"] == "refreshed"
          and feed["tickers"]["POUL"]["harvested_at"]
          >= feed["started"])
    check("scheduled sweep: events file rides the publish",
          PUBLISH_SEEN["events_file"] and PUBLISH_SEEN["feed_file"]
          and not PUBLISH_SEEN["error_file"])
    events = json.loads(
        (wd / "disclosure-events" / "POUL-events.json")
        .read_text(encoding="utf-8"))
    ev = events["events"][0]
    check("replay: after-close disclosure (19/11) appears in the "
          "next sweep's events with the correct announced date",
          ev["event_type"] == "dividend"
          and ev["announced"]["value"] == "2026-11-19"
          and ev["announced"]["basis"] == "standalone-date-line"
          and ev["payload"]["coupon_number"] == "42"
          and ev["payload"]["ex_date"]["value"] == "2026-11-16"
          and ev["stale"] is False)
    check("scheduled sweep: extraction record carries the sweep id",
          feed["extraction"]["POUL"]["sweep_id"] == "sched-2026-11-20"
          and feed["extraction"]["POUL"]["events"] == 1
          and feed["extraction"]["POUL"]["verified"] == 1)
    check("scheduled sweep: sweep still completes (done marked)",
          MARK_DONE_SEEN.get("archive") == "fake-archive-sha-278")

    # --- integration: on-demand sweep proves the same ordering ---
    FAKE_HARVEST["mode"] = "ok"
    wd2, manifest2 = run_sweep("ondemand-20261119-01",
                               "sweep-lite POUL.CA market=EGX")
    feed2 = manifest2.get("disclosure_feed") or {}
    check("on-demand sweep: same refresh -> extract -> merge order",
          [t[0] for t in TIMELINE] ==
          ["refresh", "extract", "merge", "compile", "render"])
    check("on-demand sweep: origin is on-demand, same sweep id",
          feed2.get("origin") == "on-demand"
          and feed2.get("sweep_id") == "ondemand-20261119-01"
          and feed2.get("status") == "ok")
    check("on-demand sweep: events file present at publish",
          PUBLISH_SEEN["events_file"])

    # --- multi-ticker unit path: POUL + COMI in one plan ---
    FAKE_HARVEST["mode"] = "ok"
    workdir = worker.OUT / "unit-multi"
    workdir.mkdir(parents=True, exist_ok=True)
    m3 = {"job": {"id": "unit-multi", "job": "sweep POUL.CA"},
          "started": worker.now(), "tools": {}}
    plan = [("news-disclosure", "POUL.CA"),
            ("news-disclosure", "COMI.CA")]
    rec = real_refresh(m3["job"], workdir, m3, plan)
    rec = real_extract(m3["job"], workdir, m3, plan)
    check("multi-ticker: both POUL and COMI extracted",
          rec["status"] == "ok"
          and rec["extraction"]["POUL"]["status"] == "extracted"
          and rec["extraction"]["COMI"]["status"] == "extracted")
    comi_events = json.loads(
        (workdir / "disclosure-events" / "COMI-events.json")
        .read_text(encoding="utf-8"))
    cev = comi_events["events"][0]
    check("COMI 297291: announced date is the standalone line "
          "10/11/2026, not the buggy item date 2026-01-01",
          cev["event_type"] == "earnings"
          and cev["announced"]["value"] == "2026-11-10"
          and cev["announced"]["basis"] == "standalone-date-line")

    # --- refresh fails, fresh cache: cached + extracted, flagged ---
    FAKE_HARVEST["mode"] = "fail"
    seed_cache("POUL", 1)
    wd4, manifest4 = run_sweep("sched-2026-11-21",
                               "sweep-lite POUL.CA market=EGX")
    feed4 = manifest4.get("disclosure_feed") or {}
    check("refresh fails + 1h cache: served cached, flagged, "
          "extraction still runs",
          feed4.get("status") == "ok"
          and feed4["tickers"]["POUL"]["refresh"] == "cached"
          and feed4["extraction"]["POUL"]["status"] == "extracted"
          and feed4["tickers"]["POUL"]["cache_age_hours"] <= 12)

    # --- refresh fails, stale cache: failed, skipped, loud, sweep runs
    seed_cache("POUL", 30)
    wd5, manifest5 = run_sweep("sched-2026-11-22",
                               "sweep-lite POUL.CA market=EGX")
    feed5 = manifest5.get("disclosure_feed") or {}
    check("refresh fails + 30h cache: feed failed, extraction "
          "skipped (never on stale input)",
          feed5.get("status") == "failed"
          and feed5["tickers"]["POUL"]["refresh"] == "failed"
          and feed5["extraction"]["POUL"]["status"] == "skipped")
    check("stale cache: error file rides the archive, no events file",
          PUBLISH_SEEN["error_file"]
          and not PUBLISH_SEEN["events_file"])
    check("stale cache: the sweep still runs (merge called, done "
          "marked)",
          "merge" in [t[0] for t in TIMELINE]
          and MARK_DONE_SEEN.get("archive") == "fake-archive-sha-278")

    # --- refresh fails, no cache at all ---
    cache = worker.ROOT / "harvest" / "POUL.json"
    cache.unlink(missing_ok=True)
    wd6, manifest6 = run_sweep("sched-2026-11-23",
                               "sweep-lite POUL.CA market=EGX")
    feed6 = manifest6.get("disclosure_feed") or {}
    check("refresh fails + no cache: feed failed, extraction skipped",
          feed6.get("status") == "failed"
          and feed6["extraction"]["POUL"]["status"] == "skipped"
          and PUBLISH_SEEN["error_file"])

    # --- extraction fails (extractor exits 2): recorded, sweep runs
    FAKE_HARVEST["mode"] = "ok"
    script = worker.CODE / "scripts" / "disclosure_events.py"
    real_script = script.read_bytes()
    script.write_text("import sys\nsys.exit(2)\n", encoding="utf-8")
    try:
        wd7, manifest7 = run_sweep("sched-2026-11-24",
                                   "sweep-lite POUL.CA market=EGX")
    finally:
        script.write_bytes(real_script)
    feed7 = manifest7.get("disclosure_feed") or {}
    check("extractor exits 2: extraction-failed, no events file, "
          "sweep still runs",
          feed7.get("status") == "failed"
          and feed7["extraction"]["POUL"]["status"]
          == "extraction-failed"
          and not PUBLISH_SEEN["events_file"]
          and PUBLISH_SEEN["error_file"]
          and "merge" in [t[0] for t in TIMELINE])

    # --- stale-input gate: harvest changed between the phases ---
    FAKE_HARVEST["mode"] = "ok"
    workdir8 = worker.OUT / "unit-stale-gate"
    workdir8.mkdir(parents=True, exist_ok=True)
    m8 = {"job": {"id": "unit-stale-gate", "job": "sweep POUL.CA"},
          "started": worker.now(), "tools": {}}
    plan8 = [("news-disclosure", "POUL.CA")]
    real_refresh(m8["job"], workdir8, m8, plan8)
    check("stale gate setup: refresh ok",
          m8["disclosure_feed"]["status"] == "ok")
    mutated = harvest_for("POUL")
    mutated["harvested_at"] = "2000-01-01T00:00:00Z"
    (worker.ROOT / "harvest" / "POUL.json").write_text(
        json.dumps(mutated, ensure_ascii=False, indent=1),
        encoding="utf-8")
    rec8 = real_extract(m8["job"], workdir8, m8, plan8)
    check("stale-input gate: changed harvest refused, no events file",
          rec8["status"] == "failed"
          and rec8["extraction"]["POUL"]["status"] == "stale-input"
          and not (workdir8 / "disclosure-events"
                   / "POUL-events.json").exists())

    # --- jobs the feed does not cover ---
    m9 = {"started": worker.now(), "tools": {}}
    job9 = {"id": "run-1", "job": "run news-disclosure POUL.CA"}
    check("non-sweep job: hooks do not fire",
          real_refresh(job9, worker.OUT / "unit-nosweep", m9,
                       [("news-disclosure", "POUL.CA")]) is None
          and "disclosure_feed" not in m9)
    m10 = {"started": worker.now(), "tools": {}}
    job10 = {"id": "sched-2026-11-25",
             "job": "sweep-lite AAPL market=US"}
    rec10 = real_refresh(job10, worker.OUT / "unit-noegx", m10,
                         [("news-disclosure", "AAPL")])
    check("sweep with no EGX tickers: feed skipped, explicitly",
          rec10 is not None and rec10["status"] == "skipped"
          and "no in-scope EGX tickers" in rec10["detail"])

    worker.sh = real_sh
    worker.run_harvest = real_harvest
    worker.maybe_merge = real_merge
    worker.maybe_compile = real_compile
    worker.maybe_render = real_render
    worker.publish = real_publish
    worker._mark_done = real_mark_done
    worker.refresh_disclosure_feed = real_refresh
    worker.extract_disclosure_events = real_extract
    print(f"\n{PASSED} checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
