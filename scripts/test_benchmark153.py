#!/usr/bin/env python3
"""Proof harness for issue #153 (panel round 12, F9): benchmark
call_llm in scripts/benchmark_freeze.py made ONE Cohere call, no
retry, and discarded the exception — any failure returned
(None, "llm-call-failed").

The defect, verified on unmodified main (base 7b13077):
- A stub returning HTTP 500 on request 1 and a valid envelope on
  request 2 still yields (None, "llm-call-failed") — the transient
  failure permanently drops the entrant.
- A stub returning HTTP 401 always yields the same bare
  "llm-call-failed" — an expired/invalid key is indistinguishable
  from a transient failure.

The fix: bounded retry (3 attempts, 1s then 2s backoff) on
transient failures (timeout / 429 / 5xx); the failure reason
carries str(e) after the "llm-call-failed" prefix, so a persistent
auth failure is visible; permanent failures (any other HTTP
status, e.g. 401/403/400) fail fast with exactly one attempt.
The (result, reason) return contract is unchanged.

FAILS on unmodified main (T1/T2/T3/T4/T5/T6/T7/T8 — every test
that needs a retry or a named reason) and PASSES on the fixed
tree. T7/T8 are the issue's proof bar, end to end through the
freeze: a stub that fails twice then succeeds yields a present
entrant; a persistent auth failure yields an absent entrant with
a reason naming the 401.

Usage: python3 scripts/test_benchmark153.py
Exit 0 only when every test passes.
"""
import http.server
import json
import os
import socketserver
import sys
import tempfile
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)

import benchmark_freeze as bf
from test_benchmark152 import VALID_LLM_JSON, envelope
from test_benchmark79 import (approx, clean_env, load_bench,
                              make_sweep_dir, run_freeze)

RESULTS = []
NO_SLEEP = lambda s: None  # noqa: E731
OK_BODY = json.dumps(envelope(json.dumps(VALID_LLM_JSON))).encode()


def check(name, fn):
    try:
        fn()
    except Exception as e:
        RESULTS.append((name, False, f"{type(e).__name__}: {e}"))
        print(f"FAIL {name}: {type(e).__name__}: {e}")
        return
    RESULTS.append((name, True, ""))
    print(f"PASS {name}")


def make_handler(plan):
    """plan: list of (status, body, delay_s) per request, in order;
    later requests repeat the last entry. state["count"] records
    how many requests the stub actually received."""
    state = {"count": 0}

    class H(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length") or 0)
            self.rfile.read(length)
            i = min(state["count"], len(plan) - 1)
            state["count"] += 1
            status, body, delay = plan[i]
            if delay:
                time.sleep(delay)
            try:
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass  # client already timed out; the retry is a new conn

        def log_message(self, *a):
            pass

    return H, state


def start_stub(plan):
    handler, state = make_handler(plan)

    class Server(socketserver.ThreadingTCPServer):
        daemon_threads = True
        allow_reuse_address = True

    srv = Server(("127.0.0.1", 0), handler)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, port, state


def call(url, **kw):
    return bf.call_llm("prompt", "dummy-key", url=url,
                        sleep=NO_SLEEP, **kw)


def test_t1_retry_500_then_success():
    srv, port, state = start_stub([(500, b'{"error": "boom"}', 0),
                                   (500, b'{"error": "boom"}', 0),
                                   (200, OK_BODY, 0)])
    try:
        parsed, err = call(f"http://127.0.0.1:{port}/v2/chat")
        assert parsed is not None and err is None, (parsed, err)
        approx(parsed["day"]["expected_move_pct"], 1.5)
        assert state["count"] == 3, state
    finally:
        srv.shutdown()


def test_t2_retry_429_then_success():
    srv, port, state = start_stub([(429, b'{"error": "slow down"}', 0),
                                   (200, OK_BODY, 0)])
    try:
        parsed, err = call(f"http://127.0.0.1:{port}/v2/chat")
        assert parsed is not None and err is None, (parsed, err)
        assert state["count"] == 2, state
    finally:
        srv.shutdown()


def test_t3_retry_timeout_then_success():
    # First response is slower than the call timeout; the retry
    # must still land the result.
    srv, port, state = start_stub([(200, OK_BODY, 0.6),
                                   (200, OK_BODY, 0)])
    try:
        parsed, err = call(f"http://127.0.0.1:{port}/v2/chat",
                           timeout=0.2)
        assert parsed is not None and err is None, (parsed, err)
        assert state["count"] == 2, state
    finally:
        srv.shutdown()


def test_t4_persistent_401_fails_fast_with_reason():
    srv, port, state = start_stub(
        [(401, b'{"error": "invalid api key"}', 0)])
    try:
        parsed, err = call(f"http://127.0.0.1:{port}/v2/chat")
        assert parsed is None, parsed
        assert err is not None and err.startswith("llm-call-failed"), err
        assert "401" in err, err
        assert state["count"] == 1, state  # no retry on auth failure
    finally:
        srv.shutdown()


def test_t5_persistent_500_bounded_with_backoff():
    sleeps = []
    srv, port, state = start_stub([(500, b'{"error": "boom"}', 0)])
    try:
        parsed, err = bf.call_llm(
            "prompt", "dummy-key",
            url=f"http://127.0.0.1:{port}/v2/chat",
            sleep=sleeps.append)
        assert parsed is None, parsed
        assert err is not None and "500" in err, err
        assert state["count"] == 3, state  # bounded: exactly 3 attempts
        assert sleeps == [1.0, 2.0], sleeps
    finally:
        srv.shutdown()


def test_t6_other_4xx_fails_fast():
    srv, port, state = start_stub(
        [(400, b'{"error": "bad request"}', 0)])
    try:
        parsed, err = call(f"http://127.0.0.1:{port}/v2/chat")
        assert parsed is None, parsed
        assert err is not None and "400" in err, err
        assert state["count"] == 1, state
    finally:
        srv.shutdown()


def test_t7_freeze_present_after_two_transient_failures():
    # Proof bar, end to end: stub fails twice then succeeds.
    srv, port, state = start_stub([(500, b'{"error": "boom"}', 0),
                                   (500, b'{"error": "boom"}', 0),
                                   (200, OK_BODY, 0)])
    try:
        env = clean_env({"COHERE_API_KEY": "dummy-key",
                         "COHERE_API_URL":
                             f"http://127.0.0.1:{port}/v2/chat"})
        tmp = tempfile.mkdtemp(prefix="bench153-t7-")
        sdir = make_sweep_dir(os.path.join(tmp, "sweep"))
        r = run_freeze(sdir, env)
        assert r.returncode == 0, r.stderr[-500:]
        llm = load_bench(sdir, "raw-llm-cohere")
        assert llm["status"] == "present", llm
        approx(llm["horizons"]["day"]["expected_move_pct"], 1.5)
        assert state["count"] == 3, state
    finally:
        srv.shutdown()


def test_t8_freeze_absent_on_persistent_auth_failure():
    # Proof bar, end to end: persistent 401 -> absent, reason
    # names the 401 instead of the bare "llm-call-failed".
    srv, port, state = start_stub(
        [(401, b'{"error": "invalid api key"}', 0)])
    try:
        env = clean_env({"COHERE_API_KEY": "dummy-key",
                         "COHERE_API_URL":
                             f"http://127.0.0.1:{port}/v2/chat"})
        tmp = tempfile.mkdtemp(prefix="bench153-t8-")
        sdir = make_sweep_dir(os.path.join(tmp, "sweep"))
        r = run_freeze(sdir, env)
        assert r.returncode == 0, r.stderr[-500:]
        llm = load_bench(sdir, "raw-llm-cohere")
        assert llm["status"] == "absent", llm
        assert "401" in llm["reason"], llm
        assert state["count"] == 1, state
    finally:
        srv.shutdown()


def main():
    for name, fn in [
        ("T1 retry 500,500 then success", test_t1_retry_500_then_success),
        ("T2 retry 429 then success", test_t2_retry_429_then_success),
        ("T3 retry timeout then success",
         test_t3_retry_timeout_then_success),
        ("T4 persistent 401 fails fast with reason",
         test_t4_persistent_401_fails_fast_with_reason),
        ("T5 persistent 500 bounded with backoff",
         test_t5_persistent_500_bounded_with_backoff),
        ("T6 other 4xx fails fast", test_t6_other_4xx_fails_fast),
        ("T7 freeze present after two transient failures",
         test_t7_freeze_present_after_two_transient_failures),
        ("T8 freeze absent on persistent auth failure",
         test_t8_freeze_absent_on_persistent_auth_failure),
    ]:
        check(name, fn)
    failed = [r for r in RESULTS if not r[1]]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} passed")
    if failed:
        for name, _ok, detail in failed:
            print(f"  FAILED: {name}: {detail}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
