#!/usr/bin/env python3
"""Tests for INS-DEV-004: band_calibration.alert_cells() wired into
the ledger guard watch (issue #593 follow-up).

Before: cells at effective n >= 30 whose as-published coverage sat
outside 0.75-0.85 were only listed in ledger/benchmark.md. Now
scripts/ledger_guard_watch.py fits the calibration from the committed
ledger and files / updates / closes a dedicated "Calibration coverage
alert" `ledger-failure` issue, independent of guard liveness.

Pins: the alert / clear / unknown decision (unknown never clears),
the dry-run payloads and the --signal-out back-compat skip, the live
API path against a local stub (create, no-spam on an unchanged cell
set, comment on a changed set, close on recovery, no close on
unknown), and the worker bus mirror (alert, recovered, missing file
leaves state alone, failed push refuses done).

Stdlib only, no network except a local stub server. Run:
    python3 scripts/test_ledger_guard_calibration_alert_dev004.py
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
NOW = datetime(2026, 11, 25, 12, 0, tzinfo=timezone.utc)


def check(name, fn):
    try:
        fn()
    except Exception as e:
        RESULTS.append((name, False))
        print(f"FAIL {name}: {type(e).__name__}: {e}")
        return
    RESULTS.append((name, True))
    print(f"PASS {name}")


def _row(ticker, i, resid, half=10.0):
    return {"ticker": ticker, "horizon": "day", "status": "matured",
            "dividend_gap": None, "formula": None,
            "as_of": "2026-10-%02d" % (i % 28 + 1),
            "sweep": "sweeps/%s-%03d" % (ticker, i),
            "expected_move_pct": 0.0, "realized_move_pct": resid,
            "range_low_pct": -half, "range_high_pct": half}


def _rows(ticker, n_in, n_out):
    """n_in rows inside the +-10 band, n_out outside it: as-published
    coverage = n_in / (n_in + n_out)."""
    out = [_row(ticker, i, -5.0) for i in range(n_in)]
    out += [_row(ticker, n_in + i, -15.0) for i in range(n_out)]
    return out


def _ledger(tmp, rows, name="ledger.json"):
    p = Path(tmp) / name
    p.write_text(json.dumps({"forecasts_detail": rows}))
    return str(p)


# AAA: 30/30 inside -> coverage 1.0, outside tolerance, n=30 -> alert.
# BBB: 24/30 inside -> coverage 0.80, in tolerance.
ALERT_ROWS = _rows("AAA", 30, 0)
CLEAR_ROWS = _rows("BBB", 24, 6)


def test_alert_state_lists_the_cell():
    with tempfile.TemporaryDirectory() as tmp:
        st, alerts, err = watch.calibration_alerts(
            _ledger(tmp, ALERT_ROWS))
    assert st == "alert" and err is None, (st, err)
    assert [a["ticker"] for a in alerts] == ["AAA"], alerts
    assert alerts[0]["coverage_before"] == 1.0, alerts


def test_in_tolerance_is_clear():
    with tempfile.TemporaryDirectory() as tmp:
        st, alerts, _ = watch.calibration_alerts(
            _ledger(tmp, CLEAR_ROWS))
    assert st == "clear" and alerts == [], (st, alerts)


def test_below_public_n_is_clear():
    with tempfile.TemporaryDirectory() as tmp:
        st, alerts, _ = watch.calibration_alerts(
            _ledger(tmp, _rows("CCC", 10, 0)))
    assert st == "clear", (st, alerts)


def test_missing_or_bad_ledger_is_unknown_not_clear():
    with tempfile.TemporaryDirectory() as tmp:
        st, _, err = watch.calibration_alerts(
            os.path.join(tmp, "nope.json"))
        assert st == "unknown" and "missing" in err, (st, err)
        bad = Path(tmp) / "bad.json"
        bad.write_text("not json{{{")
        st, _, _ = watch.calibration_alerts(str(bad))
        assert st == "unknown", st
        nolist = Path(tmp) / "nolist.json"
        nolist.write_text(json.dumps({"forecasts_detail": None}))
        st, _, _ = watch.calibration_alerts(str(nolist))
        assert st == "unknown", st


def test_title_body_names_cells_and_tolerance():
    alerts = [{"ticker": "AAA", "horizon": "day", "n": 30,
               "n_eff": 30, "coverage_before": 1.0}]
    title, body = watch.calibration_title_body(alerts, NOW)
    assert title.startswith(watch.CAL_TITLE_PREFIX), title
    assert "AAA day" in body and "1.000" in body, body
    assert "Cells: AAA/day" in body, body
    assert "0.75-0.85" in body, body
    # #713: the alert text must name the per-horizon gate and the
    # exact-binomial page predicate, not the old scalar n >= 30.
    assert "n_eff >= 30 day / 6 week / 2 month" in body, body
    assert "exact-binomial" in body, body


def _run_cli(args, tmp):
    env = {k: v for k, v in os.environ.items()
           if k not in ("GH_TOKEN", "GITHUB_TOKEN")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, os.path.join(SCRIPTS, "ledger_guard_watch.py")]
        + args, capture_output=True, text=True, env=env, cwd=tmp,
        timeout=60)


def _hb(tmp):
    p = Path(tmp) / "hb.json"
    p.write_text(json.dumps({
        "last_run_utc": "2026-11-25T11:30:00Z", "run_id": 1,
        "status": "ok", "workflow": "ledger-guard"}))
    return str(p)


def test_cli_dry_run_writes_alert_payload():
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "cal.json"
        r = _run_cli(["--heartbeat", _hb(tmp), "--now",
                      "2026-11-25T12:00:00Z", "--guard-pending", "no",
                      "--ledger", _ledger(tmp, ALERT_ROWS),
                      "--signal-out", str(Path(tmp) / "g.json"),
                      "--calibration-signal-out", str(out)], tmp)
        assert r.returncode == 0, r.stdout + r.stderr
        p = json.loads(out.read_text())
        assert p["action"] == "create", p
        assert p["cells"] == ["AAA/day"], p
        assert p["labels"] == ["ledger-failure"], p
        assert p["title"].startswith("⚠️ Calibration coverage alert"), p


def test_cli_dry_run_writes_none_when_clear():
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "cal.json"
        r = _run_cli(["--heartbeat", _hb(tmp), "--now",
                      "2026-11-25T12:00:00Z", "--guard-pending", "no",
                      "--ledger", _ledger(tmp, CLEAR_ROWS),
                      "--signal-out", str(Path(tmp) / "g.json"),
                      "--calibration-signal-out", str(out)], tmp)
        assert r.returncode == 0, r.stdout + r.stderr
        assert json.loads(out.read_text())["action"] == "none"


def test_cli_unknown_ledger_writes_no_payload():
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "cal.json"
        r = _run_cli(["--heartbeat", _hb(tmp), "--now",
                      "2026-11-25T12:00:00Z", "--guard-pending", "no",
                      "--ledger", str(Path(tmp) / "absent.json"),
                      "--signal-out", str(Path(tmp) / "g.json"),
                      "--calibration-signal-out", str(out)], tmp)
        assert r.returncode == 0, r.stdout + r.stderr
        assert not out.exists(), "unknown must not write a payload"
        assert "UNKNOWN" in r.stdout, r.stdout


def test_cli_signal_out_without_cal_out_skips_calibration():
    # Old callers (pre-DEV-004 worker) pass --signal-out only: the
    # calibration check must not run and must never hit the live API.
    with tempfile.TemporaryDirectory() as tmp:
        r = _run_cli(["--heartbeat", _hb(tmp), "--now",
                      "2026-11-25T12:00:00Z", "--guard-pending", "no",
                      "--ledger", _ledger(tmp, ALERT_ROWS),
                      "--signal-out", str(Path(tmp) / "g.json")], tmp)
        assert r.returncode == 0, r.stdout + r.stderr
        assert "calibration check skipped" in r.stdout, r.stdout


def test_guard_dead_and_calibration_alert_are_independent():
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "cal.json"
        g = Path(tmp) / "g.json"
        r = _run_cli(["--heartbeat", _hb(tmp), "--now",
                      "2026-11-25T18:00:00Z", "--guard-pending", "no",
                      "--ledger", _ledger(tmp, ALERT_ROWS),
                      "--signal-out", str(g),
                      "--calibration-signal-out", str(out)], tmp)
        assert r.returncode == 0, r.stdout + r.stderr
        assert json.loads(g.read_text())["action"] == "create"
        assert json.loads(out.read_text())["action"] == "create"
        # guard suppressed (pending) must not hide the calibration page
        g.unlink()
        out.unlink()
        r = _run_cli(["--heartbeat", _hb(tmp), "--now",
                      "2026-11-25T18:00:00Z", "--guard-pending", "yes",
                      "--ledger", _ledger(tmp, ALERT_ROWS),
                      "--signal-out", str(g),
                      "--calibration-signal-out", str(out)], tmp)
        assert r.returncode == 0, r.stdout + r.stderr
        assert not g.exists()
        assert json.loads(out.read_text())["action"] == "create"


class Stub:
    """Records every request; serves a configurable open-issue list."""

    def __init__(self, open_issues):
        self.calls = []
        outer = self

        class H(BaseHTTPRequestHandler):
            def _go(self, method):
                n = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(n)) if n else None
                outer.calls.append((method, self.path, body))
                status, data = 200, {}
                if self.path.startswith("/search/issues"):
                    data = {"items": outer.open_issues}
                elif method == "POST" and self.path.endswith("/issues"):
                    status, data = 201, {"number": 900}
                elif method == "POST":
                    status, data = 201, {"id": 1}
                raw = json.dumps(data).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_GET(self):
                self._go("GET")

            def do_POST(self):
                self._go("POST")

            def do_PATCH(self):
                self._go("PATCH")

            def log_message(self, *a):
                pass

        self.open_issues = open_issues
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=self.srv.serve_forever,
                         daemon=True).start()

    def __enter__(self):
        self._old = os.environ.get("GITHUB_API_URL")
        os.environ["GITHUB_API_URL"] = (
            f"http://127.0.0.1:{self.srv.server_address[1]}")
        return self

    def __exit__(self, *a):
        if self._old is None:
            os.environ.pop("GITHUB_API_URL", None)
        else:
            os.environ["GITHUB_API_URL"] = self._old
        self.srv.shutdown()

    def writes(self):
        return [(m, p) for m, p, _ in self.calls if m != "GET"]


def _alerts(n=1):
    return [{"ticker": t, "horizon": "day", "n": 30, "n_eff": 30,
             "coverage_before": 1.0} for t in ("AAA", "BBB")[:n]]


def test_live_alert_creates_issue_with_ledger_failure_label():
    with Stub([]) as s:
        assert watch.signal_calibration("tok", _alerts(), NOW) is True
        creates = [c for c in s.calls
                   if c[0] == "POST" and c[1].endswith("/issues")]
    assert len(creates) == 1, s.calls
    body = creates[0][2]
    assert body["labels"] == ["ledger-failure"], body
    assert body["title"].startswith(watch.CAL_TITLE_PREFIX), body


def test_live_same_cells_does_not_comment_again():
    _, body = watch.calibration_title_body(_alerts(), NOW)
    issue = {"number": 7, "title": watch.CAL_TITLE_PREFIX,
             "body": body}
    with Stub([issue]) as s:
        assert watch.signal_calibration("tok", _alerts(), NOW) is True
        assert s.writes() == [], s.writes()


def test_live_changed_cells_comments_on_open_issue():
    _, body = watch.calibration_title_body(_alerts(1), NOW)
    issue = {"number": 7, "title": watch.CAL_TITLE_PREFIX,
             "body": body}
    with Stub([issue]) as s:
        assert watch.signal_calibration("tok", _alerts(2), NOW) is True
        w = s.writes()
    assert w == [("POST", w[0][1])] and w[0][1].endswith(
        "/issues/7/comments"), w


def test_live_clear_closes_open_alert_issue():
    issue = {"number": 7, "title": watch.CAL_TITLE_PREFIX, "body": ""}
    with Stub([issue]) as s:
        assert watch.clear_calibration("tok", NOW) is True
        w = s.writes()
    assert ("PATCH", w[-1][1]) == w[-1] and w[-1][1].endswith(
        "/issues/7"), w


def test_live_clear_ignores_other_signal_issues():
    other = {"number": 8, "title": "⚠️ Ledger guard dead", "body": ""}
    with Stub([other]) as s:
        assert watch.clear_calibration("tok", NOW) is True
        assert s.writes() == [], s.writes()


def test_unknown_never_closes_or_files():
    with tempfile.TemporaryDirectory() as tmp:
        issue = {"number": 7, "title": watch.CAL_TITLE_PREFIX,
                 "body": ""}
        with Stub([issue]) as s:
            ok = watch.run_calibration_check(
                os.path.join(tmp, "absent.json"), NOW, "tok")
            assert ok is True
            assert s.calls == [], s.calls


def test_no_token_alert_fails_loud():
    assert watch.signal_calibration(None, _alerts(), NOW) is False


# --- worker bus mirror ------------------------------------------------

def _load_worker():
    sys.path.insert(0, os.path.join(ROOT, "worker"))
    import worker  # noqa: E402
    return worker


def _mirror_env(worker, tmp, push_ok=True):
    worker.BUS = Path(tmp) / "bus"
    (worker.BUS / "queue").mkdir(parents=True)
    pushed = []
    worker.push_bus = lambda msg: (pushed.append(msg) or push_ok)
    return pushed


def test_worker_mirrors_alert_then_recovery():
    w = _load_worker()
    with tempfile.TemporaryDirectory() as tmp:
        pushed = _mirror_env(w, tmp)
        out = Path(tmp) / "cal.json"
        out.write_text(json.dumps({"action": "create", "cells":
                                   ["AAA/day"], "reason": "x"}))
        assert w._mirror_calibration_alert({"id": "j1"}, out) is True
        cur = json.loads(
            (w.BUS / "queue" / "calibration-alert.json").read_text())
        assert cur["state"] == "alert" and cur["job_id"] == "j1", cur
        out.write_text(json.dumps({"action": "none", "reason": "ok"}))
        assert w._mirror_calibration_alert({"id": "j2"}, out) is True
        cur = json.loads(
            (w.BUS / "queue" / "calibration-alert.json").read_text())
        assert cur["state"] == "recovered", cur
        assert len(pushed) == 2, pushed


def test_worker_missing_signal_file_leaves_alert_alone():
    w = _load_worker()
    with tempfile.TemporaryDirectory() as tmp:
        pushed = _mirror_env(w, tmp)
        (w.BUS / "queue" / "calibration-alert.json").write_text(
            json.dumps({"state": "alert"}))
        assert w._mirror_calibration_alert(
            {"id": "j3"}, Path(tmp) / "absent.json") is True
        cur = json.loads(
            (w.BUS / "queue" / "calibration-alert.json").read_text())
        assert cur["state"] == "alert" and pushed == [], (cur, pushed)


def test_worker_failed_push_refuses_done():
    w = _load_worker()
    with tempfile.TemporaryDirectory() as tmp:
        _mirror_env(w, tmp, push_ok=False)
        out = Path(tmp) / "cal.json"
        out.write_text(json.dumps({"action": "create", "cells": []}))
        assert w._mirror_calibration_alert({"id": "j4"}, out) is False


def test_worker_unreadable_signal_refuses_done():
    w = _load_worker()
    with tempfile.TemporaryDirectory() as tmp:
        _mirror_env(w, tmp)
        out = Path(tmp) / "cal.json"
        out.write_text("not json{{{")
        assert w._mirror_calibration_alert({"id": "j5"}, out) is False


def test_worker_watch_set_includes_band_calibration():
    w = _load_worker()
    assert "scripts/band_calibration.py" in w.WATCH_SCRIPTS
    assert "scripts/ledger_guard_watch.py" in w.WATCH_SCRIPTS


TESTS = [(n[5:], f) for n, f in sorted(globals().items())
         if n.startswith("test_") and callable(f)]


def main():
    for name, fn in TESTS:
        check(name, fn)
    failed = [n for n, ok in RESULTS if not ok]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
