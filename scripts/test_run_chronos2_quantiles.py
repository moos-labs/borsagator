#!/usr/bin/env python3
"""Tests for benchmarks/run_chronos2_quantiles.py (round 93). Stdlib only,
stub forecaster, no torch, no model, no network. Fixed synthetic inputs.
"""
import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "benchmarks"))
sys.path.insert(0, HERE)
CHECKS = {"pass": 0, "fail": 0}


def check(name, ok, detail=""):
    CHECKS["pass" if ok else "fail"] += 1
    if not ok:
        print("FAIL %s %s" % (name, detail))


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, rel))
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


Q = _load("qrun", "benchmarks/run_chronos2_quantiles.py")
T = _load("tsfm_for_runner", "benchmarks/score_tsfm_control.py")


def make_capture(root, cutoff, name, closes):
    """closes: list of (date, close). Returns the capture dir."""
    cap = os.path.join(root, cutoff, name)
    os.makedirs(os.path.join(cap, "digest"))
    for fn in ("manifest.json", "realised.json"):
        open(os.path.join(cap, fn), "w").write("{}")
    open(os.path.join(cap, "digest", "ensemble.json"), "w").write("{}")
    with open(os.path.join(cap, "price.csv"), "w") as f:
        f.write("date,close\n")
        for d, c in closes:
            f.write("%s,%s\n" % (d, c))
    return cap


def days(n, start=(2023, 1, 1), last="2024-05-09"):
    """n ascending synthetic dates ending exactly on `last`."""
    import datetime
    end = datetime.date.fromisoformat(last)
    return [(end - datetime.timedelta(days=n - 1 - i)).isoformat()
            for i in range(n)]


def stub(values):
    """Price quantile at step k: last x (1 + k x 0.01 x {-1, 0, +1})."""
    last = values[-1]
    stub.seen.append(list(values))
    return {k: (last * (1 - 0.01 * k), last, last * (1 + 0.01 * k))
            for k in range(1, 22)}


stub.seen = []


def closes_series(n, last="2024-05-09", base=100.0):
    ds = days(n, last=last)
    return [(d, base + i) for i, d in enumerate(ds)]


def test_constants():
    check("fixed settings", Q.CONTEXT_SESSIONS == 750 and Q.MIN_CONTEXT == 120
          and Q.STEPS == {"day": 1, "week": 5, "month": 21}
          and Q.LEVELS == (0.1, 0.5, 0.9) and Q.RELEASE_DATE == "2025-10-20"
          and Q.VERDICT_MIN_CELL == 48)


def test_horizon_values():
    hz, why = Q.to_horizons(200.0, {k: (200 * (1 - 0.01 * k), 200 * (1 + 0.001 * k), 200 * (1 + 0.01 * k))
                                    for k in range(1, 22)})
    check("no reason", why is None)
    check("day is step 1 cumulative return %", abs(hz["day"]["q10"] + 1.0) < 1e-6
          and abs(hz["day"]["q90"] - 1.0) < 1e-6 and abs(hz["day"]["q50"] - 0.1) < 1e-6, str(hz))
    check("week is step 5", abs(hz["week"]["q10"] + 5.0) < 1e-6 and abs(hz["week"]["q50"] - 0.5) < 1e-6, str(hz))
    check("month is step 21", abs(hz["month"]["q90"] - 21.0) < 1e-6 and abs(hz["month"]["q50"] - 2.1) < 1e-6, str(hz))
    bad, why = Q.to_horizons(100.0, {k: (101.0, 100.0, 99.0) for k in range(1, 22)})
    check("crossing quantiles rejected", bad is None and "not ordered" in why)
    mid, why = Q.to_horizons(100.0, {k: (99.0, 102.0, 101.0) for k in range(1, 22)})
    check("q50 above q90 rejected", mid is None and "not ordered" in why)
    low, why = Q.to_horizons(100.0, {k: (99.0, 98.0, 101.0) for k in range(1, 22)})
    check("q50 below q10 rejected", low is None)
    eq, why = Q.to_horizons(100.0, {k: (100.0, 100.0, 100.0) for k in range(1, 22)})
    check("zero width rejected", eq is None)
    miss, why = Q.to_horizons(100.0, {k: (99.0, 100.0, 101.0) for k in range(1, 21)})
    check("missing step 21 rejected", miss is None and "step 21" in why)


def test_context_window_and_cutoff():
    with tempfile.TemporaryDirectory() as d:
        cl = closes_series(800)
        # bars after the cutoff directory name must never enter the context
        cl += [("2024-05-10", 999.0), ("2024-05-11", 998.0)]
        cap = make_capture(d, "2024-05-09", "TST", cl)
        stub.seen.clear()
        st, info = Q.run_capture(cap, stub)
        check("written", st == "written", str(info))
        seen = stub.seen[0]
        check("context is the latest 750 closes", len(seen) == 750)
        check("last context value is the cutoff-day close, not a later bar", seen[-1] == 899.0, str(seen[-1]))
        check("no post-cutoff value in context", 999.0 not in seen and 998.0 not in seen)
        data = json.load(open(info))
        check("json header", data["model"] == "chronos-2" and data["base_date"] == "2024-05-09"
              and data["context_sessions"] == 750 and data["last_close_date"] == "2024-05-09")
        check("scorer reads it", T.load_quantiles(cap, "chronos-2") is not None)
        check("day q10 is -1% from last close 899", abs(data["horizons"]["day"]["q10"] + 1.0) < 1e-4, str(data["horizons"]))
    with tempfile.TemporaryDirectory() as d:
        cap = make_capture(d, "2024-05-09", "TST", closes_series(120))
        st, info = Q.run_capture(cap, stub)
        check("exactly 120 closes accepted", st == "written")
        cap2 = make_capture(d, "2024-05-09", "SHORT", closes_series(119))
        st, info = Q.run_capture(cap2, stub)
        check("119 closes excluded", st == "excluded" and "only 119 closes" in info, str(info))
        check("no file for the short one", not os.path.exists(os.path.join(cap2, "collected")))


def test_last_close_date_differs_from_cutoff():
    with tempfile.TemporaryDirectory() as d:
        cap = make_capture(d, "2024-05-12", "TST", closes_series(200, last="2024-05-09"))
        st, p = Q.run_capture(cap, stub)
        data = json.load(open(p))
        check("base_date is the cutoff, last_close_date the last bar",
              data["base_date"] == "2024-05-12" and data["last_close_date"] == "2024-05-09", str(data))


def test_guard():
    with tempfile.TemporaryDirectory() as d:
        cl = closes_series(200, last="2024-05-09")
        c47 = make_capture(d, "2024-05-09", "A-cell47", cl)
        c48 = make_capture(d, "2024-05-09", "B-cell48", cl)
        check("cell 47 pre-release runs", Q.run_capture(c47, stub)[0] == "written")
        st, why = Q.run_capture(c48, stub)
        check("cell 48 refused", st == "excluded" and "verdict cell" in why, str(why))
        check("cell 48 wrote nothing", not os.path.exists(os.path.join(c48, "collected")))
        st, _ = Q.run_capture(c48, stub, allow_verdict=True)
        check("flag allows cell 48", st == "written")
    with tempfile.TemporaryDirectory() as d:
        cl19 = closes_series(200, last="2025-10-19")
        cl20 = closes_series(200, last="2025-10-20")
        a = make_capture(d, "2025-10-19", "A", cl19)
        b = make_capture(d, "2025-10-20", "B", cl20)
        c = make_capture(d, "2025-10-21", "C", closes_series(200, last="2025-10-21"))
        check("2025-10-19 allowed", Q.run_capture(a, stub)[0] == "written")
        st, why = Q.run_capture(b, stub)
        check("2025-10-20 refused (not strictly before)", st == "excluded" and "strictly before" in why, str(why))
        check("2025-10-21 refused", Q.run_capture(c, stub)[0] == "excluded")
        check("flag allows post-release", Q.run_capture(c, stub, allow_verdict=True)[0] == "written")
    check("unnumbered pre-release not refused", Q.guard_reason("/x/2024-05-09/T", "2024-05-09", False) is None)


def test_keep_force_and_out_root():
    with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as out:
        cap = make_capture(d, "2024-05-09", "TST", closes_series(200))
        st, p = Q.run_capture(cap, stub)
        first = open(p).read()
        open(p, "w").write("SENTINEL")
        st, p2 = Q.run_capture(cap, stub)
        check("existing file kept", st == "kept" and open(p).read() == "SENTINEL")
        st, _ = Q.run_capture(cap, stub, force=True)
        check("force rewrites", st == "written" and open(p).read() == first)
        check("no tmp left behind", not os.path.exists(p + ".tmp"))
        st, p3 = Q.run_capture(cap, stub, out_root=out)
        check("out-root mirrors cutoff/ticker",
              st == "written" and p3 == os.path.join(out, "2024-05-09", "TST", "collected", "chronos-2", "quantiles.json"), str(p3))
        check("in-place file untouched by out-root run", open(p).read() == first)


def test_failures_listed():
    def boom(values):
        raise RuntimeError("x")
    with tempfile.TemporaryDirectory() as d:
        cap = make_capture(d, "2024-05-09", "TST", closes_series(200))
        st, why = Q.run_capture(cap, boom)
        check("forecast failure excluded with reason", st == "excluded" and why == "forecast failed: RuntimeError")
        nocsv = os.path.join(d, "2024-05-09", "NOCSV")
        os.makedirs(os.path.join(nocsv, "digest"))
        for fn in ("manifest.json", "realised.json"):
            open(os.path.join(nocsv, fn), "w").write("{}")
        open(os.path.join(nocsv, "digest", "ensemble.json"), "w").write("{}")
        st, why = Q.run_capture(nocsv, stub)
        check("missing price.csv excluded", st == "excluded" and "price.csv" in why)
        cross = lambda v: {k: (v[-1] * 1.1, v[-1], v[-1] * 0.9) for k in range(1, 22)}
        st, why = Q.run_capture(cap, cross)
        check("crossing quantiles excluded", st == "excluded" and "not ordered" in why)
        check("nothing written after failures", not os.path.exists(os.path.join(cap, "collected")))


def test_main_listing_and_guard_before_model():
    with tempfile.TemporaryDirectory() as d:
        make_capture(d, "2024-05-09", "OK", closes_series(200))
        make_capture(d, "2024-05-09", "V-cell60", closes_series(200))
        make_capture(d, "2024-05-10", "SHORT", closes_series(50, last="2024-05-10"))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = Q.main(["--captures", d], forecaster=stub)
        o = buf.getvalue()
        check("main ok", rc == 0, o)
        check("counts line", "captures 3: written 1, kept 0, excluded 2" in o, o)
        check("each excluded capture listed with reason",
              "V-cell60: cell 60 is a verdict cell" in o and "SHORT: only 50 closes" in o, o)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = Q.main(["--captures", d, "--limit", "1"], forecaster=stub)
        check("limit applies", "captures 1:" in buf.getvalue())
        rc = Q.main(["--captures", os.path.join(d, "nothing")], forecaster=stub)
        check("no captures refused", rc == 2)
    # the real model must not load when every capture is refused by the guard
    called = []
    real = Q.load_chronos2
    Q.load_chronos2 = lambda: called.append(1) or stub
    try:
        with tempfile.TemporaryDirectory() as d:
            make_capture(d, "2024-05-09", "V-cell60", closes_series(200))
            with contextlib.redirect_stdout(io.StringIO()):
                Q.main(["--captures", d])
            check("model not loaded when all captures are guarded", called == [])
            make_capture(d, "2024-05-10", "OK2", closes_series(200, last="2024-05-10"))
            with contextlib.redirect_stdout(io.StringIO()):
                try:
                    Q.main(["--captures", d])
                except Exception:
                    pass
            check("model loaded when a capture is runnable", called == [1])
    finally:
        Q.load_chronos2 = real


def _flat(frac):
    return lambda v: {k: (v[-1] * (1 - frac), v[-1], v[-1] * (1 + frac))
                      for k in range(1, 22)}


def test_nonfinite_and_rounding():
    import math
    with tempfile.TemporaryDirectory() as d:
        cap = make_capture(d, "2024-05-09", "TST", closes_series(200))
        for label, bad in (("inf", math.inf), ("nan", math.nan), ("-inf", -math.inf)):
            def f(v, bad=bad):
                o = stub(v)
                o[5] = (o[5][0], o[5][1], bad)
                return o
            st, why = Q.run_capture(cap, f)
            check("%s quantile excluded with reason" % label,
                  st == "excluded" and "non-finite" in why, why)
        check("nothing written for non-finite",
              not os.path.exists(os.path.join(cap, "collected")))
        st, why = Q.run_capture(cap, _flat(1e-9))
        check("interval collapsing at 6 dp excluded", st == "excluded" and "after rounding" in why, why)
        check("collapsed file not written", not os.path.exists(os.path.join(cap, "collected")))
        st, dst = Q.run_capture(cap, _flat(1e-8))
        check("smallest representable interval still written", st == "written", dst)
        data = json.load(open(dst))
        check("rounded q90 > q10", all(h["q90"] > h["q10"] for h in data["horizons"].values()))
    hz, why = Q.to_horizons(100.0, {k: (99.0, 100.0, 101.0) for k in range(1, 22)})
    check("finite ok", hz is not None and why is None)
    for lc in (0.0, -1.0, float("inf"), float("nan")):
        hz, why = Q.to_horizons(lc, {k: (1.0, 2.0, 3.0) for k in range(1, 22)})
        check("bad last close %r rejected with reason" % lc, hz is None and "last close" in why, why)


def test_lazy_model_load():
    called = []
    real = Q.load_chronos2
    Q.load_chronos2 = lambda: called.append(1) or stub
    try:
        with tempfile.TemporaryDirectory() as d:
            make_capture(d, "2024-05-09", "A1", closes_series(200))
            make_capture(d, "2024-05-09", "SHORT", closes_series(50))
            make_capture(d, "2024-05-09", "V-cell60", closes_series(200))
            with contextlib.redirect_stdout(io.StringIO()):
                Q.main(["--captures", os.path.join(d, "2024-05-09", "SHORT")])
            check("excluded-only run does not load", called == [])
            with contextlib.redirect_stdout(io.StringIO()):
                Q.main(["--captures", os.path.join(d, "2024-05-09", "V-cell60")])
            check("guarded-only run does not load", called == [])
            with contextlib.redirect_stdout(io.StringIO()):
                Q.main(["--captures", os.path.join(d, "2024-05-09", "A1")])
            check("first forecast loads once", called == [1])
            with contextlib.redirect_stdout(io.StringIO()):
                Q.main(["--captures", os.path.join(d, "2024-05-09", "A1")])
            check("all kept does not load", called == [1])
            make_capture(d, "2024-05-09", "A2", closes_series(200))
            make_capture(d, "2024-05-09", "A3", closes_series(200))
            with contextlib.redirect_stdout(io.StringIO()):
                Q.main(["--captures", os.path.join(d, "2024-05-09", "A2"),
                        os.path.join(d, "2024-05-09", "A3")])
            check("two forecasts in one run load once", called == [1, 1])
    finally:
        Q.load_chronos2 = real


def test_per_capture_boundary():
    with tempfile.TemporaryDirectory() as d:
        cap = make_capture(d, "2024-05-09", "TST", closes_series(200))
        real = Q.to_horizons

        def zde(lc, steps):
            raise ZeroDivisionError("x")
        Q.to_horizons = zde
        try:
            st, why = Q.run_capture(cap, stub)
        finally:
            Q.to_horizons = real
        check("ZeroDivisionError excluded with reason",
              st == "excluded" and "ZeroDivisionError" in why, why)
        blocker = os.path.join(d, "blocker")
        open(blocker, "w").write("x")
        st, why = Q.run_capture(cap, stub, out_root=blocker)
        check("filesystem error excluded with reason", st == "excluded" and "write failed" in why, why)
        check("no tmp left", not any(f.endswith(".tmp") for _, _, fs in os.walk(d) for f in fs))
    with tempfile.TemporaryDirectory() as d:
        c1 = make_capture(d, "2024-05-09", "AAA", closes_series(200))
        zero = closes_series(200)
        zero[-1] = (zero[-1][0], 0.0)
        c2 = make_capture(d, "2024-05-09", "BBB", zero)
        c3 = make_capture(d, "2024-05-09", "CCC", closes_series(200))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = Q.main(["--captures", c1, c2, c3], forecaster=stub)
        o = buf.getvalue()
        check("batch survives a bad capture", rc == 0 and "written: " in o and
              "captures 3: written 2, kept 0, excluded 1" in o, o)
        check("bad capture listed with reason", "excluded: capture %s: last close" % c2 in o, o)
        check("both neighbours written", all(os.path.exists(os.path.join(c, "collected", "chronos-2", "quantiles.json")) for c in (c1, c3)))
        # an unexpected error escaping run_capture is caught at the loop boundary
        realrc = Q.run_capture

        def flaky(c, *a, **k):
            if c.endswith("BBB"):
                raise OSError("disk")
            if c.endswith("AAA"):
                raise OverflowError("big")
            return realrc(c, *a, **k)
        Q.run_capture = flaky
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                rc = Q.main(["--captures", c2, c1], forecaster=stub)
        finally:
            Q.run_capture = realrc
        o = buf.getvalue()
        check("loop boundary catches OSError and still reports",
              rc == 0 and "excluded: capture %s: failed: OSError" % c2 in o and
              "excluded: capture %s: failed: OverflowError" % c1 in o and
              "captures 2: written 0, kept 0, excluded 2" in o, o)
    with tempfile.TemporaryDirectory() as d:
        tgt = os.path.join(d, "x", "q.json")
        try:
            Q.write_json(tgt, {"a": float("inf")})
            raised = False
        except ValueError:
            raised = True
        check("write_json refuses non-finite (no Infinity in a file)", raised)
        check("no final or tmp file after refusal", not os.path.exists(tgt) and not os.path.exists(tgt + ".tmp"))


def run_all():
    for fn in (test_constants, test_horizon_values, test_context_window_and_cutoff,
               test_last_close_date_differs_from_cutoff, test_guard, test_keep_force_and_out_root, test_failures_listed,
               test_main_listing_and_guard_before_model, test_nonfinite_and_rounding,
               test_lazy_model_load, test_per_capture_boundary):
        fn()
    print("test_run_chronos2_quantiles: %d passed, %d failed" % (CHECKS["pass"], CHECKS["fail"]))
    return CHECKS["fail"]


class Suite(unittest.TestCase):
    def test_all(self):
        CHECKS["pass"] = CHECKS["fail"] = 0
        self.assertEqual(run_all(), 0)


def main():
    sys.exit(1 if run_all() else 0)


if __name__ == "__main__":
    main()
