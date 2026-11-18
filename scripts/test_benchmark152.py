#!/usr/bin/env python3
"""Proof harness for issue #152 (panel round 12, F8): benchmark
response validation in scripts/benchmark_freeze.py accepted
nonfinite moves and inverted intervals, and write_json used the
default allow_nan=True, so a NaN could be written as a bare `NaN`
token into frozen/ledger data.

The defect, verified on unmodified main (base 3780d2d):
- fnum("nan") -> nan, fnum(inf) -> inf, fnum(True) -> 1.0
  (bare float()).
- _parse_llm_response accepted a day horizon with
  expected_move_pct NaN and range_low_pct 5.0 > range_high_pct
  -5.0, returning it parsed with err None.
- json.dumps({"a": float("nan")}) -> '{"a": NaN}' (bare token).

The fix: fnum rejects booleans and nonfinite values (returns
None, which every caller already treats as missing);
_parse_llm_response rejects any horizon whose interval is not
low <= expected <= high; write_json serializes with
allow_nan=False, so a NaN anywhere in a frozen doc raises
ValueError instead of writing a bare token (main() already
catches it and records benchmark/freeze_error.txt, so the freeze
fails loudly instead of freezing corrupt data).

FAILS on unmodified main (T1/T2/T3/T4/T5a) and PASSES on the
fixed tree. T5b proves a valid response still freezes present.

Usage: python3 scripts/test_benchmark152.py
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

# Valid model reply: every interval ordered, every move finite.
VALID_LLM_JSON = {
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


def envelope(llm_text):
    """Cohere v2 envelope carrying the given model-reply text."""
    return {"id": "11111111-2222-3333-4444-555555555555",
            "finish_reason": "COMPLETE",
            "message": {"role": "assistant",
                        "content": [{"type": "text", "text": llm_text}]},
            "usage": {"billed_units": {"input_tokens": 120,
                                       "output_tokens": 90}}}


def check(name, fn):
    try:
        fn()
    except Exception as e:
        RESULTS.append((name, False, f"{type(e).__name__}: {e}"))
        print(f"FAIL {name}: {type(e).__name__}: {e}")
        return
    RESULTS.append((name, True, ""))
    print(f"PASS {name}")


def test_t1_fnum_rejects_nonfinite_and_bool():
    assert bf.fnum("nan") is None, bf.fnum("nan")
    assert bf.fnum(float("nan")) is None
    assert bf.fnum(float("inf")) is None
    assert bf.fnum(float("-inf")) is None
    assert bf.fnum("Infinity") is None
    assert bf.fnum(True) is None
    assert bf.fnum(False) is None
    # Finite values still parse, including numeric strings and 0.
    assert bf.fnum("1.5") == 1.5
    assert bf.fnum(-2) == -2.0
    assert bf.fnum(0) == 0.0
    assert bf.fnum("0") == 0.0
    assert bf.fnum(None) is None
    assert bf.fnum("abc") is None


def test_t2_parse_rejects_nonfinite_move():
    # Bare NaN token in the model reply (Python json accepts it).
    corrupt = json.loads(json.dumps(VALID_LLM_JSON),
                         parse_constant=lambda x: float(x))
    corrupt["day"]["expected_move_pct"] = float("nan")
    parsed, err = bf._parse_llm_response(
        envelope(json.dumps(corrupt)))
    assert parsed is None and err == "llm-response-unparseable", \
        (parsed, err)
    # The string "nan" must not smuggle a NaN in either.
    corrupt2 = dict(VALID_LLM_JSON)
    corrupt2["week"] = dict(VALID_LLM_JSON["week"],
                            expected_move_pct="nan")
    parsed, err = bf._parse_llm_response(
        envelope(json.dumps(corrupt2)))
    assert parsed is None and err == "llm-response-unparseable", \
        (parsed, err)
    # Infinity in a range bound is likewise rejected.
    corrupt3 = dict(VALID_LLM_JSON)
    corrupt3["month"] = dict(VALID_LLM_JSON["month"],
                             range_high_pct=float("inf"))
    parsed, err = bf._parse_llm_response(
        envelope(json.dumps(corrupt3)))
    assert parsed is None and err == "llm-response-unparseable", \
        (parsed, err)


def test_t3_parse_rejects_inverted_interval():
    # low > high outright.
    corrupt = dict(VALID_LLM_JSON)
    corrupt["day"] = dict(VALID_LLM_JSON["day"],
                          range_low_pct=5.0, range_high_pct=-5.0)
    parsed, err = bf._parse_llm_response(
        envelope(json.dumps(corrupt)))
    assert parsed is None and err == "llm-response-unparseable", \
        (parsed, err)
    # Expected move above the high bound.
    corrupt2 = dict(VALID_LLM_JSON)
    corrupt2["week"] = dict(VALID_LLM_JSON["week"],
                            expected_move_pct=6.0, range_high_pct=5.0)
    parsed, err = bf._parse_llm_response(
        envelope(json.dumps(corrupt2)))
    assert parsed is None and err == "llm-response-unparseable", \
        (parsed, err)
    # Expected move below the low bound.
    corrupt3 = dict(VALID_LLM_JSON)
    corrupt3["month"] = dict(VALID_LLM_JSON["month"],
                             expected_move_pct=-10.0,
                             range_low_pct=-9.0)
    parsed, err = bf._parse_llm_response(
        envelope(json.dumps(corrupt3)))
    assert parsed is None and err == "llm-response-unparseable", \
        (parsed, err)


def test_t4_write_json_never_writes_bare_nan():
    tmp = tempfile.mkdtemp(prefix="bench152-t4-")
    old = bf.BENCH_DIR
    bf.BENCH_DIR = tmp
    try:
        try:
            bf.write_json("nan.json", {"a": float("nan")})
        except ValueError:
            pass
        else:
            raise AssertionError("write_json accepted a NaN doc")
        assert not os.path.exists(os.path.join(tmp, "nan.json")), \
            "NaN doc was written"
        # A valid doc still writes, and strict-parse round-trips.
        bf.write_json("ok.json", {"a": 1.5, "b": [1, 2.0]})
        with open(os.path.join(tmp, "ok.json"), "rb") as f:
            raw = f.read()
        assert b"NaN" not in raw and b"Infinity" not in raw, raw
        json.loads(raw.decode("utf-8"),
                   parse_constant=lambda x: (_ for _ in ()).throw(
                       ValueError(f"non-strict token: {x}")))
    finally:
        bf.BENCH_DIR = old


class ReplyHandler(http.server.BaseHTTPRequestHandler):
    """Serves one configured model-reply text as a v2 envelope."""
    reply_text = json.dumps(VALID_LLM_JSON)

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        self.rfile.read(length)
        body = json.dumps(envelope(self.reply_text)).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


def start_stub(reply_text):
    handler = type("H", (ReplyHandler,), {"reply_text": reply_text})
    srv = socketserver.TCPServer(("127.0.0.1", 0), handler)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, port


def test_t5a_freeze_rejects_corrupt_llm_reply():
    # End-to-end: a NaN move + inverted interval from the stub
    # must land the entrant ABSENT, never frozen present.
    corrupt = dict(VALID_LLM_JSON)
    corrupt["day"] = dict(VALID_LLM_JSON["day"],
                          expected_move_pct=float("nan"),
                          range_low_pct=5.0, range_high_pct=-5.0)
    srv, port = start_stub(json.dumps(corrupt))
    try:
        env = clean_env({"COHERE_API_KEY": "dummy-key",
                         "COHERE_API_URL":
                             f"http://127.0.0.1:{port}/v2/chat"})
        tmp = tempfile.mkdtemp(prefix="bench152-t5a-")
        sdir = make_sweep_dir(os.path.join(tmp, "sweep"))
        r = run_freeze(sdir, env)
        assert r.returncode == 0, r.stderr[-500:]
        llm = load_bench(sdir, "raw-llm-cohere")
        assert llm["status"] == "absent", llm
        assert llm["reason"] == "llm-response-unparseable", llm
        assert "horizons" not in llm, llm
    finally:
        srv.shutdown()


def test_t5b_freeze_still_accepts_valid_reply():
    # The same path with a valid reply still freezes present.
    srv, port = start_stub(json.dumps(VALID_LLM_JSON))
    try:
        env = clean_env({"COHERE_API_KEY": "dummy-key",
                         "COHERE_API_URL":
                             f"http://127.0.0.1:{port}/v2/chat"})
        tmp = tempfile.mkdtemp(prefix="bench152-t5b-")
        sdir = make_sweep_dir(os.path.join(tmp, "sweep"))
        r = run_freeze(sdir, env)
        assert r.returncode == 0, r.stderr[-500:]
        llm = load_bench(sdir, "raw-llm-cohere")
        assert llm["status"] == "present", llm
        approx(llm["horizons"]["day"]["expected_move_pct"], 1.5)
        approx(llm["horizons"]["day"]["range_low_pct"], -2.0)
        approx(llm["horizons"]["day"]["range_high_pct"], 5.0)
        # No bare nonfinite token anywhere in the frozen file.
        with open(os.path.join(sdir, "benchmark",
                               "raw-llm-cohere.json"), "rb") as f:
            raw = f.read()
        assert b"NaN" not in raw and b"Infinity" not in raw, raw
    finally:
        srv.shutdown()


def test_t6_kronos_nan_close_row_dropped():
    # fnum strictness also fixes the Kronos path: a NaN close used
    # to be truthy and kept (bool(nan) is True); now the row is
    # dropped like any row with no close.
    import csv
    tmp = tempfile.mkdtemp(prefix="bench152-t6-")
    path = os.path.join(tmp, "forecast.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "open", "high", "low", "close",
                    "volume", "amount"])
        w.writerow(["2026-11-13", "9.9", "10.3", "9.8", "nan",
                    "1000", "10000"])
        w.writerow(["2026-11-14", "9.9", "10.3", "9.8", "10.0",
                    "1000", "10000"])
    old = bf.KRONOS_CSV
    bf.KRONOS_CSV = path
    try:
        rows, _first, _note = bf.read_kronos_csv({})
    finally:
        bf.KRONOS_CSV = old
    assert rows is not None and len(rows) == 1, rows
    assert rows[0][0] == 10.0, rows


def main():
    for name, fn in [
        ("T1 fnum rejects nonfinite and bool",
         test_t1_fnum_rejects_nonfinite_and_bool),
        ("T2 parse rejects nonfinite move",
         test_t2_parse_rejects_nonfinite_move),
        ("T3 parse rejects inverted interval",
         test_t3_parse_rejects_inverted_interval),
        ("T4 write_json never writes bare NaN",
         test_t4_write_json_never_writes_bare_nan),
        ("T5a freeze rejects corrupt LLM reply",
         test_t5a_freeze_rejects_corrupt_llm_reply),
        ("T5b freeze still accepts valid reply",
         test_t5b_freeze_still_accepts_valid_reply),
        ("T6 Kronos NaN-close row dropped",
         test_t6_kronos_nan_close_row_dropped),
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
