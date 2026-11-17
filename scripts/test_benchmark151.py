#!/usr/bin/env python3
"""Proof harness for issue #151 (panel round 12, F7): the Cohere
client in scripts/benchmark_freeze.py sent v2 request/response
shapes to the /v1/chat URL, so the raw-llm-cohere entrant could
never succeed in production.

Unlike the permissive stub in test_benchmark79.py (test_f3), the
stub here implements Cohere's DOCUMENTED contract, from
https://docs.cohere.com/docs/migrating-v1-to-v2 and
https://docs.cohere.com/reference/chat (both read 2026-11-17):

- v2 request: POST /v2/chat, body {model, messages:[{role,
  content}], temperature, response_format:{type: json_object}}.
- v2 response envelope: {id, finish_reason, message:{role,
  content:[{type: "text", text: ...}]}, usage}.
- v1 request: POST /v1/chat, body {message, preamble?, ...};
  v1 response text via `text`. command-r-08-2024 is NOT supported
  on /v1/chat — Cohere returns HTTP 400 with the verbatim message
  "invalid request: this model is not supported with '/v1/chat',
  please use '/v2/chat' instead."

The stub therefore serves ONLY /v2/chat with v2-shaped bodies and
answers any other path (including /v1/chat) with that exact 400.
No valid Cohere key is available to this agent (no custom.cohere
connector; the key is a write-only GitHub org secret), so the
real-contract fixture below is the v2 envelope as documented, and
the stub enforces the documented request contract.

FAILS on unmodified main (default URL still /v1/chat: the strict
stub 400s, call_llm returns llm-call-failed, the entrant is
absent) and PASSES on the fixed tree.

Usage: python3 scripts/test_benchmark151.py
Exit 0 only when every test passes.
"""
import http.server
import json
import os
import socketserver
import sys
import tempfile
import threading
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)

import benchmark_freeze as bf
from test_benchmark79 import (approx, clean_env, load_bench,
                              make_sweep_dir, run_freeze)

RESULTS = []

# The model reply, as JSON text inside a v2 content block.
LLM_JSON = {
    "day": {"direction": "up", "expected_move_pct": 1.5,
            "range_low_pct": -2.0, "range_high_pct": 5.0,
            "confidence": 0.6},
    "week": {"direction": "flat", "expected_move_pct": 0.0,
             "range_low_pct": -4.0, "range_high_pct": 4.0,
             "confidence": 0.5},
    "month": {"direction": "down", "expected_move_pct": -3.0,
              "range_low_pct": -9.0, "range_high_pct": 3.0,
              "confidence": 0.4},
}

# Captured real-contract v2 response envelope (shape per
# docs.cohere.com/reference/chat): id, finish_reason, message with
# a content list of typed blocks, usage.
V2_ENVELOPE = {
    "id": "11111111-2222-3333-4444-555555555555",
    "finish_reason": "COMPLETE",
    "message": {"role": "assistant",
                "content": [{"type": "text",
                             "text": json.dumps(LLM_JSON)}]},
    "usage": {"billed_units": {"input_tokens": 120,
                               "output_tokens": 90},
              "tokens": {"input_tokens": 120, "output_tokens": 90}},
}

# Cohere's verbatim 400 for command-r-08-2024 on /v1/chat.
V1_400_MESSAGE = ("invalid request: this model is not supported "
                  "with '/v1/chat', please use '/v2/chat' instead. "
                  "More details in the migration guide: Migrating "
                  "From API v1 to API v2 | Cohere")


def check(name, fn):
    try:
        fn()
    except Exception as e:
        RESULTS.append((name, False, f"{type(e).__name__}: {e}"))
        print(f"FAIL {name}: {type(e).__name__}: {e}")
        return
    RESULTS.append((name, True, ""))
    print(f"PASS {name}")


class StrictCohereHandler(http.server.BaseHTTPRequestHandler):
    """Serves only the documented v2 contract. Any other path
    (notably /v1/chat) gets Cohere's verbatim 400."""

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length)
        if self.path != "/v2/chat":
            body = {"id": "00000000-0000-0000-0000-000000000000",
                    "message": V1_400_MESSAGE}
            self._send(400, body)
            return
        try:
            req = json.loads(raw.decode("utf-8"))
        except Exception:
            self._send(400, {"message": "invalid request: bad JSON"})
            return
        # Enforce the documented v2 request contract.
        assert req.get("model") == "command-r-08-2024", req
        assert req.get("temperature") == 0, req
        assert req.get("response_format") == {"type": "json_object"}, req
        msgs = req.get("messages")
        assert isinstance(msgs, list) and len(msgs) == 1, req
        assert msgs[0].get("role") == "user", req
        assert isinstance(msgs[0].get("content"), str), req
        assert "message" not in req and "preamble" not in req, req
        self._send(200, V2_ENVELOPE)

    def _send(self, status, body):
        raw = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *a):
        pass


def start_stub():
    srv = socketserver.TCPServer(("127.0.0.1", 0), StrictCohereHandler)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, port


def test_t1_default_url_is_v2():
    assert bf.LLM_URL_DEFAULT == "https://api.cohere.com/v2/chat", \
        bf.LLM_URL_DEFAULT
    assert urllib.parse.urlparse(bf.LLM_URL_DEFAULT).path == "/v2/chat"


def test_t2_parse_real_v2_envelope():
    parsed, err = bf._parse_llm_response(V2_ENVELOPE)
    assert err is None, err
    assert parsed is not None
    approx(parsed["day"]["expected_move_pct"], 1.5)
    assert parsed["day"]["direction"] == "up"
    assert parsed["week"]["direction"] == "flat"
    assert parsed["month"]["direction"] == "down"
    approx(parsed["month"]["range_low_pct"], -9.0)
    assert parsed["day"]["confidence"] == 0.6


def test_t3_v1_shaped_response_is_unparseable():
    # The parser is v2-only by design: a v1 response carries its
    # text in `text`, not in message.content — it must not parse.
    parsed, err = bf._parse_llm_response(
        {"id": "x", "text": json.dumps(LLM_JSON),
         "generation_id": "y", "finish_reason": "COMPLETE"})
    assert parsed is None and err == "llm-response-unparseable"


def test_t4_call_llm_uses_default_url_path():
    # Drive call_llm through the path taken from LLM_URL_DEFAULT
    # (no env override, no url arg) against the strict stub: on
    # unmodified main the path is /v1/chat and the stub 400s with
    # Cohere's verbatim message, so call_llm must fail.
    srv, port = start_stub()
    try:
        path = urllib.parse.urlparse(bf.LLM_URL_DEFAULT).path
        url = f"http://127.0.0.1:{port}{path}"
        parsed, err = bf.call_llm("Generate a JSON forecast.",
                                  "dummy-key", url=url)
        assert err is None, f"call failed against {path}: {err}"
        assert parsed is not None
        approx(parsed["day"]["expected_move_pct"], 1.5)
    finally:
        srv.shutdown()


def test_t5_freeze_present_via_v2_stub():
    # End-to-end: the freeze's raw-llm-cohere entrant lands present
    # when the v2 contract is served (COHERE_API_URL override is the
    # harness-only mechanism; the production default is covered by
    # T1/T4).
    srv, port = start_stub()
    try:
        env = clean_env({"COHERE_API_KEY": "dummy-key",
                         "COHERE_API_URL": f"http://127.0.0.1:{port}/v2/chat"})
        tmp = tempfile.mkdtemp(prefix="bench151-t5-")
        sdir = make_sweep_dir(os.path.join(tmp, "sweep"))
        r = run_freeze(sdir, env)
        assert r.returncode == 0, r.stderr[-500:]
        llm = load_bench(sdir, "raw-llm-cohere")
        assert llm["status"] == "present", llm
        approx(llm["horizons"]["day"]["expected_move_pct"], 1.5)
        assert llm["llm_model"] == "command-r-08-2024"
        assert llm["prompt_version"] == "v1"
    finally:
        srv.shutdown()


def main():
    for name, fn in [
        ("T1 default URL is /v2/chat", test_t1_default_url_is_v2),
        ("T2 parse real v2 envelope", test_t2_parse_real_v2_envelope),
        ("T3 v1-shaped response unparseable",
         test_t3_v1_shaped_response_is_unparseable),
        ("T4 call_llm via default-URL path",
         test_t4_call_llm_uses_default_url_path),
        ("T5 freeze entrant present via v2 stub",
         test_t5_freeze_present_via_v2_stub),
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
