#!/usr/bin/env python3
"""Unit tests for issue #156: guard liveness deadline conflicts
with the whole-sweep concurrency lock.

Before the fix, `check()` in scripts/ledger_guard_watch.py was
purely age-based: a heartbeat older than 90 minutes always paged,
with no notion of a queued guard. But the guard shares the
`borsagator-ledger-publish` concurrency group with the whole
orchestrate job (350-minute timeout), so a guard tick queues
behind a running sweep while the heartbeat ages — a legitimate
long sweep produced a false "Ledger guard dead" signal.

The fix: the watchdog asks the Actions API whether a ledger-guard
run is queued / waiting / in progress. While one is pending, a
stale heartbeat is "suppressed" (no signal filed, no open signal
closed — the guard has not proven itself alive yet), unless the
heartbeat is older than the 420-minute maximum latency, in which
case the signal fires anyway. An undetermined pending state
(API unreadable) fails safe to the old age-only decision.

Stdlib only, no network except a local stub server. Run:
    python3 scripts/test_ledger_guard_watch_156.py
Exit 0 only when every test passes.
"""
import json
import os
import subprocess
import sys
import tempfile
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)

import ledger_guard_watch as watch  # noqa: E402

RESULTS = []
NOW = datetime(2026, 11, 18, 12, 0, tzinfo=timezone.utc)
PENDING = [{"id": 111, "status": "waiting",
            "created_at": "2026-11-18T11:30:00Z",
            "html_url": "https://github.com/moos-labs/borsagator/"
                        "actions/runs/111"}]


def check(name, fn):
    try:
        fn()
    except Exception as e:
        RESULTS.append((name, False, f"{type(e).__name__}: {e}"))
        print(f"FAIL {name}: {type(e).__name__}: {e}")
        return
    RESULTS.append((name, True, ""))
    print(f"PASS {name}")


def _heartbeat(tmp, hour, minute=0, status="ok"):
    p = Path(tmp) / "guard-heartbeat.json"
    p.write_text(json.dumps({
        "last_run_utc": f"2026-11-18T{hour:02d}:{minute:02d}:00Z",
        "run_id": 1, "status": status, "workflow": "ledger-guard"}))
    return str(p)


def _run_cli(args, tmp):
    """Run the script as a subprocess with no GitHub token in env,
    so no real API call can happen (pending state is forced)."""
    env = {k: v for k, v in os.environ.items()
           if k not in ("GH_TOKEN", "GITHUB_TOKEN")}
    r = subprocess.run(
        [sys.executable, os.path.join(SCRIPTS, "ledger_guard_watch.py")]
        + args, capture_output=True, text=True, env=env, cwd=tmp,
        timeout=60)
    return r


def test_stale_with_pending_guard_is_suppressed():
    # Proof bar: a sweep running >90 min does not produce a
    # dead-guard signal while a guard run is queued behind it.
    with tempfile.TemporaryDirectory() as tmp:
        hb = _heartbeat(tmp, 10)  # 120 min old at NOW
        state, why, _, _ = watch.check(hb, NOW, 90,
                                       pending_runs=PENDING)
        assert state == "suppressed", f"expected suppressed, got {state}: {why}"
        assert "111" in why and "waiting" in why, why


def test_stale_with_no_pending_guard_is_dead():
    with tempfile.TemporaryDirectory() as tmp:
        hb = _heartbeat(tmp, 10)
        state, why, _, _ = watch.check(hb, NOW, 90, pending_runs=[])
        assert state == "dead", f"expected dead, got {state}: {why}"
        assert "90-minute" in why, why


def test_stale_with_unknown_pending_fails_safe_to_dead():
    # API unreadable: keep the old age-only decision (page).
    with tempfile.TemporaryDirectory() as tmp:
        hb = _heartbeat(tmp, 10)
        state, _, _, _ = watch.check(hb, NOW, 90, pending_runs=None)
        assert state == "dead", f"expected dead, got {state}"


def test_pending_guard_past_max_latency_is_dead():
    # 480 min old, past the 420-min cap: a queued guard that never
    # lands is a real outage, not a long sweep.
    with tempfile.TemporaryDirectory() as tmp:
        hb = _heartbeat(tmp, 4)  # 480 min old at NOW
        state, why, _, _ = watch.check(hb, NOW, 90,
                                       pending_runs=PENDING)
        assert state == "dead", f"expected dead, got {state}: {why}"
        assert "420-minute maximum latency" in why, why
        assert "111" in why, why


def test_pending_guard_at_max_latency_boundary_is_suppressed():
    # Exactly 420 min old: the alarm fires only PAST the cap.
    with tempfile.TemporaryDirectory() as tmp:
        hb = _heartbeat(tmp, 5)  # 420 min old at NOW
        state, _, _, _ = watch.check(hb, NOW, 90,
                                     pending_runs=PENDING)
        assert state == "suppressed", f"expected suppressed, got {state}"


def test_fresh_heartbeat_with_pending_guard_is_fresh():
    with tempfile.TemporaryDirectory() as tmp:
        hb = _heartbeat(tmp, 11, 30)  # 30 min old at NOW
        state, _, _, _ = watch.check(hb, NOW, 90,
                                     pending_runs=PENDING)
        assert state == "fresh", f"expected fresh, got {state}"


def test_missing_heartbeat_with_pending_guard_is_dead():
    # No baseline to measure latency against; in production the
    # file already exists, so its absence is itself worth paging.
    with tempfile.TemporaryDirectory() as tmp:
        missing = os.path.join(tmp, "no-such-heartbeat.json")
        state, _, _, _ = watch.check(missing, NOW, 90,
                                     pending_runs=PENDING)
        assert state == "dead", f"expected dead, got {state}"


def _stub_server(payload, status=200):
    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            body = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def test_pending_guard_runs_lists_non_completed():
    payload = {"total_count": 3, "workflow_runs": [
        {"id": 3, "status": "completed",
         "created_at": "2026-11-18T09:00:00Z", "html_url": "u3"},
        {"id": 2, "status": "in_progress",
         "created_at": "2026-11-18T11:00:00Z", "html_url": "u2"},
        {"id": 1, "status": "waiting",
         "created_at": "2026-11-18T10:00:00Z", "html_url": "u1"}]}
    srv = _stub_server(payload)
    old = os.environ.get("GITHUB_API_URL")
    os.environ["GITHUB_API_URL"] = (
        f"http://127.0.0.1:{srv.server_address[1]}")
    try:
        pending = watch.pending_guard_runs("dummy-token")
    finally:
        if old is None:
            os.environ.pop("GITHUB_API_URL", None)
        else:
            os.environ["GITHUB_API_URL"] = old
        srv.shutdown()
    assert pending is not None, "expected a list, got None"
    assert [r["id"] for r in pending] == [2, 1], pending
    assert all(r["status"] != "completed" for r in pending), pending


def test_pending_guard_runs_api_failure_is_unknown():
    srv = _stub_server({"message": "boom"}, status=500)
    old = os.environ.get("GITHUB_API_URL")
    os.environ["GITHUB_API_URL"] = (
        f"http://127.0.0.1:{srv.server_address[1]}")
    try:
        assert watch.pending_guard_runs("dummy-token") is None
    finally:
        if old is None:
            os.environ.pop("GITHUB_API_URL", None)
        else:
            os.environ["GITHUB_API_URL"] = old
        srv.shutdown()
    assert watch.pending_guard_runs(None) is None


def test_cli_stale_pending_suppresses_signal_dry_run():
    with tempfile.TemporaryDirectory() as tmp:
        hb = _heartbeat(tmp, 10)
        out = os.path.join(tmp, "signal.json")
        r = _run_cli(["--heartbeat", hb, "--now",
                      "2026-11-18T12:00:00Z", "--guard-pending", "yes",
                      "--signal-out", out], tmp)
        assert r.returncode == 0, r.stdout + r.stderr
        assert "SUPPRESSED" in r.stdout, r.stdout
        assert not os.path.exists(out), \
            "suppressed must not write a signal payload"


def test_cli_stale_no_pending_files_signal_dry_run():
    with tempfile.TemporaryDirectory() as tmp:
        hb = _heartbeat(tmp, 10)
        out = os.path.join(tmp, "signal.json")
        r = _run_cli(["--heartbeat", hb, "--now",
                      "2026-11-18T12:00:00Z", "--guard-pending", "no",
                      "--signal-out", out], tmp)
        assert r.returncode == 0, r.stdout + r.stderr
        payload = json.loads(Path(out).read_text())
        assert payload["action"] == "create", payload
        assert payload["title"].startswith("⚠️ Ledger guard dead"), payload


def test_cli_pending_past_max_latency_files_signal_dry_run():
    with tempfile.TemporaryDirectory() as tmp:
        hb = _heartbeat(tmp, 4)  # 480 min old
        out = os.path.join(tmp, "signal.json")
        r = _run_cli(["--heartbeat", hb, "--now",
                      "2026-11-18T12:00:00Z", "--guard-pending", "yes",
                      "--signal-out", out], tmp)
        assert r.returncode == 0, r.stdout + r.stderr
        payload = json.loads(Path(out).read_text())
        assert payload["action"] == "create", payload
        assert "maximum latency" in payload["reason"], payload


def test_workflows_keep_serialization_and_watchdog_can_read_runs():
    # The fix does not remove the concurrency group anywhere; the
    # watchdog gains the Actions read it needs for the lookup.
    wd = Path(ROOT, ".github/workflows/ledger-guard-watchdog.yml") \
        .read_text()
    assert "actions: read" in wd, "watchdog needs actions: read"
    assert "concurrency:" not in wd, \
        "watchdog must not join the publish group"
    for name in ("ledger-guard.yml", "orchestrate.yml"):
        text = Path(ROOT, ".github/workflows", name).read_text()
        assert "group: borsagator-ledger-publish" in text, name


TESTS = [
    ("stale_with_pending_guard_is_suppressed",
     test_stale_with_pending_guard_is_suppressed),
    ("stale_with_no_pending_guard_is_dead",
     test_stale_with_no_pending_guard_is_dead),
    ("stale_with_unknown_pending_fails_safe_to_dead",
     test_stale_with_unknown_pending_fails_safe_to_dead),
    ("pending_guard_past_max_latency_is_dead",
     test_pending_guard_past_max_latency_is_dead),
    ("pending_guard_at_max_latency_boundary_is_suppressed",
     test_pending_guard_at_max_latency_boundary_is_suppressed),
    ("fresh_heartbeat_with_pending_guard_is_fresh",
     test_fresh_heartbeat_with_pending_guard_is_fresh),
    ("missing_heartbeat_with_pending_guard_is_dead",
     test_missing_heartbeat_with_pending_guard_is_dead),
    ("pending_guard_runs_lists_non_completed",
     test_pending_guard_runs_lists_non_completed),
    ("pending_guard_runs_api_failure_is_unknown",
     test_pending_guard_runs_api_failure_is_unknown),
    ("cli_stale_pending_suppresses_signal_dry_run",
     test_cli_stale_pending_suppresses_signal_dry_run),
    ("cli_stale_no_pending_files_signal_dry_run",
     test_cli_stale_no_pending_files_signal_dry_run),
    ("cli_pending_past_max_latency_files_signal_dry_run",
     test_cli_pending_past_max_latency_files_signal_dry_run),
    ("workflows_keep_serialization_and_watchdog_can_read_runs",
     test_workflows_keep_serialization_and_watchdog_can_read_runs),
]


def main():
    for name, fn in TESTS:
        check(name, fn)
    failed = [n for n, ok, _ in RESULTS if not ok]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
