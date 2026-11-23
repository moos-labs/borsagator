#!/usr/bin/env python3
"""Tests for the `diagnose <job_id>` worker job (guard-slot
2026-11-22T0847Z follow-up).

The wiring under test (worker/worker.py):
  parse_diagnose_job — exactly `diagnose <job_id>` with a
    JOB_ID_RE target parses; anything else fails closed (None).
    parse_job (the registry grammar) returns [] for the string,
    which is why _execute_body dispatches this kind before
    parse_job, like diag-egx-ab.
  run_diagnose — builds the evidence bundle from local state
    (intent, receipts, bus copies, OUT listing, journal excerpt)
    and mirrors it to queue/diagnostics/<target>.json. Absent
    pieces are recorded as absent, never invented.
  _execute_body diagnose branch — publishes via the stubbed
    publish and marks done only on a successful publish.

Harness-first: FAILS on pristine main (no parse_diagnose_job /
run_diagnose — AttributeError) and PASSES on the patched tree.
Stdlib only. Run: python3 worker/test_worker_diagnose.py
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _test_tmp  # noqa: E402  (atexit cleanup of scratch dirs, #388)
_TMP = _test_tmp.mkdtemp(prefix="gator-diagnose-test-")
os.environ["GATOR_ROOT"] = str(_TMP)

_HERE = Path(os.path.abspath(__file__)).parent
sys.path.insert(0, str(_HERE))

import worker  # noqa: E402

PASSED = 0
FAILED = 0


def check(name, cond):
    global PASSED, FAILED
    if cond:
        PASSED += 1
        print(f"ok - {name}")
    else:
        FAILED += 1
        print(f"FAIL - {name}")


TARGET = "guard-2026-11-22T0847Z"

# --- parse_diagnose_job -------------------------------------------------
check("parse: exact form",
      worker.parse_diagnose_job(f"diagnose {TARGET}")
      == {"target": TARGET})
check("parse: bare keyword fails", worker.parse_diagnose_job(
    "diagnose") is None)
check("parse: extra token fails", worker.parse_diagnose_job(
    f"diagnose {TARGET} extra") is None)
check("parse: bad target fails", worker.parse_diagnose_job(
    "diagnose ../etc") is None)
check("parse: non-string fails", worker.parse_diagnose_job(
    None) is None)
check("parse: typo fails", worker.parse_diagnose_job(
    f"diagnos {TARGET}") is None)
check("registry grammar has no diagnose",
      worker.parse_job(f"diagnose {TARGET}",
                       {"tools": []}) == [])

# --- run_diagnose bundle ------------------------------------------------
worker.JOB_STATE.mkdir(parents=True, exist_ok=True)
worker.PENDING_DONE.mkdir(parents=True, exist_ok=True)
worker._intent_path(TARGET).write_text(json.dumps(
    {"job": "ledger-guard", "started": "2026-11-22T08:50:57Z"}))
(worker.PENDING_DONE / f"{TARGET}.done").write_text(
    '{"status": "local-only"}')
out_dir = worker.OUT / TARGET
out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / "manifest.json").write_text('{"job": "partial"}')
bus_claims = worker.BUS / "queue" / "claims"
bus_claims.mkdir(parents=True, exist_ok=True)
(bus_claims / f"{TARGET}.json").write_text('{"worker": "w5"}')

check("journal: no window for plain id",
      worker._diagnose_journal("plain-id", None)[0] == "no-window")

worker.sync_bus = lambda: None
pushed = []
worker.push_bus = lambda msg: pushed.append(msg) or True
worker._diagnose_journal = lambda t, i: (
    "ok", f"guard run {t} push rejected")

workdir = _TMP / "run-diag"
status = worker.run_diagnose(
    {"id": "diag-1", "job": f"diagnose {TARGET}"}, workdir)
check("run: status ok", status == {"diagnose": "ok"})
bundle = json.loads(
    (workdir / "diagnose" / "diagnostics.json").read_text())
check("run: intent captured",
      json.loads(bundle["intent"])["job"] == "ledger-guard")
check("run: intent hashed", len(bundle["intent_sha256"]) == 64)
check("run: receipt captured",
      bundle["receipts"][f"{TARGET}.done"]
      == '{"status": "local-only"}')
check("run: bus claim captured",
      bundle["bus"]["queue/claims/" + TARGET + ".json"]
      == '{"worker": "w5"}')
check("run: bus done recorded absent",
      bundle["bus"]["queue/done/" + TARGET + ".json"] is None)
check("run: out manifest captured",
      bundle["out_manifest"] == '{"job": "partial"}')
check("run: journal excerpt captured",
      bundle["journal_status"] == "ok"
      and TARGET in bundle["journal_excerpt"])
check("run: queue mirror written",
      (worker.BUS / "queue" / "diagnostics"
       / f"{TARGET}.json").is_file())
check("run: queue mirror pushed", pushed == [f"diagnostics {TARGET}"])
check("run: queue status recorded", bundle["queue_publish"] == "ok")

# Absent target: everything recorded absent, still ok.
status2 = worker.run_diagnose(
    {"id": "diag-2", "job": "diagnose guard-2026-01-01T0000Z"},
    _TMP / "run-diag2")
bundle2 = json.loads(
    (_TMP / "run-diag2" / "diagnose" / "diagnostics.json").read_text())
check("absent: status ok", status2 == {"diagnose": "ok"})
check("absent: intent None", bundle2["intent"] is None)
check("absent: no receipts", bundle2["receipts"] == {})

# Bad job: named failure, no bundle.
status3 = worker.run_diagnose(
    {"id": "diag-3", "job": "diagnose"}, _TMP / "run-diag3")
check("bad job: named failure", status3 == {"diagnose": "bad-job"})

# --- _execute_body dispatch ----------------------------------------------
worker.registry = lambda: {"tools": []}
marked = []
worker._mark_done = lambda job, sha: marked.append((job["id"], sha))
worker.publish = lambda job, wd, mf: "archivesha"
worker.run_diagnose = lambda job, wd: {"diagnose": "ok"}
job = {"id": "diag-4", "job": f"diagnose {TARGET}"}
worker._execute_body(job)
check("dispatch: marked done on publish", marked == [("diag-4",
                                                      "archivesha")])
marked.clear()
worker.publish = lambda job, wd, mf: None
fails = []
worker._record_publish_failure = lambda job: fails.append(job["id"])
worker._execute_body(job)
check("dispatch: failed publish not marked",
      marked == [] and fails == ["diag-4"])

print(f"\n{PASSED} passed, {FAILED} failed")
sys.exit(1 if FAILED else 0)
