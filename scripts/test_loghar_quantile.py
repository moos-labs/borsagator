"""Tests for benchmarks/replay_loghar_quantile.py: fixed synthetic inputs."""
import contextlib
import importlib.util
import io
import math
import os
import sys
import unittest

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.join(HERE, "..", "benchmarks")
sys.path.insert(0, BENCH)
sys.path.insert(0, HERE)


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(BENCH, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


Q = _load("replay_loghar_quantile")
CHECKS = {"pass": 0, "fail": 0}


def check(name, ok, detail=""):
    CHECKS["pass" if ok else "fail"] += 1
    if not ok:
        print("FAIL: %s %s" % (name, detail))


def test_constants():
    check("tau", Q.TAU == 0.80)
    check("floor", Q.MOVE_FLOOR == 0.01)
    check("min rows", Q.MIN_TRAIN_ROWS == 8)
    check("train max", Q.TRAIN_MAX_CELL == 47)
    check("clean min", Q.CLEAN_MIN_CELL == 91)


def test_pinball():
    pts = [(0.0, 1.0), (1.0, 3.0)]
    check("pinball under-prediction weighted tau", abs(Q.pinball(pts, 0.0, 0.0) - 0.8 * 4.0) < 1e-12)
    check("pinball over-prediction weighted 1-tau", abs(Q.pinball(pts, 5.0, 0.0) - (0.2 * 4.0 + 0.2 * 2.0)) < 1e-12)


def test_fit_exact_line():
    pts = [(float(i), 2.0 + 0.5 * i) for i in range(10)]
    f = Q.fit_quantile(pts)
    check("recovers exact line", abs(f["a"] - 2.0) < 1e-9 and abs(f["b"] - 0.5) < 1e-9 and f["loss"] < 1e-9)
    check("too few rows", Q.fit_quantile(pts[:7]) is None)
    check("exactly min rows fits", Q.fit_quantile(pts[:8]) is not None)


def test_fit_quantile_level():
    # one clean line plus one outlier above: tau 0.8 line keeps 80% at or below
    pts = [(float(i), float(i)) for i in range(9)] + [(4.5, 40.0)]
    f = Q.fit_quantile(pts)
    below = sum(1 for x, y in pts if y <= f["a"] + f["b"] * x + 1e-9)
    check("at least tau share on or below", below / len(pts) >= 0.8, str(below))
    check("optimum no worse than neighbours",
          all(Q.pinball(pts, f["a"] + da, f["b"] + db) >= Q.pinball(pts, f["a"], f["b"]) - 1e-9
              for da in (-0.1, 0.0, 0.1) for db in (-0.05, 0.0, 0.05)))


def test_tie_break():
    pts = [(float(i), 1.0) for i in range(5)] + [(float(i) + 10.0, 1.0) for i in range(5)]
    f = Q.fit_quantile(pts)
    check("flat data gives b=0", abs(f["b"]) < 1e-9 and abs(f["a"] - 1.0) < 1e-9)


def test_tie_break_smaller_a():
    pts = [(2.0, 3.0), (3.0, 3.0), (2.0, 4.0), (1.0, 1.0)]
    old = Q.MIN_TRAIN_ROWS
    Q.MIN_TRAIN_ROWS = 2
    try:
        f = Q.fit_quantile(pts)
    finally:
        Q.MIN_TRAIN_ROWS = old
    check("equal loss and |b-1| tie goes to smaller a", abs(f["a"] + 2.0) < 1e-9 and abs(f["b"] - 3.0) < 1e-9, str(f))
    check("min rows restored", Q.MIN_TRAIN_ROWS == old)


def _row(h, sig, real, mult=1.0, cell=1):
    return {"horizon": h, Q.KEY: sig, "real": real, "mult": mult, "cell": cell,
            "v2_sigma": sig, "ticker": "T", "as_of": "d", "naive_half": 5.0}


def test_points_and_half():
    r = _row("day", 0.02, -3.0)
    u = Q.unit_pct(r)
    check("unit is half_pct at k=1", abs(u - 0.02 * 1.0 * 100) < 1e-9)
    pts = Q.train_points([r, _row("week", 0.02, 1.0), _row("day", None, 1.0)], "day")
    check("points filter by horizon and forecast", len(pts) == 1)
    check("point uses abs move in log", abs(pts[0][1] - math.log(3.0)) < 1e-12)
    pts = Q.train_points([_row("day", 0.02, 0.0)], "day")
    check("zero move floored", abs(pts[0][1] - math.log(0.01)) < 1e-12)
    check("quantile half formula", abs(Q.quantile_half(r, {"a": 0.0, "b": 1.0}) - u) < 1e-9)
    check("quantile half with a", abs(Q.quantile_half(r, {"a": math.log(2.0), "b": 1.0}) - 2 * u) < 1e-9)


def test_constant_unit_and_overflow():
    pts = [(1.5, 1.0 + 0.1 * i) for i in range(10)]
    f = Q.fit_quantile(pts)
    check("constant unit still fits", f is not None and f["b"] == 1.0 and f["n"] == 10)
    # tau 0.8 optimum of y - x over ten evenly spaced values is the 8th value
    check("constant unit intercept is the 0.8 quantile of y-x", abs(f["a"] - (1.0 + 0.7 - 1.5)) < 1e-9, str(f))
    check("constant unit below min rows", Q.fit_quantile(pts[:7]) is None)
    flat = [(1.5, 0.5)] * 8
    f = Q.fit_quantile(flat)
    check("identical points fit", f is not None and abs(f["a"] + 1.0) < 1e-9)
    frozen = {"quantile": {"day": Q.fit_quantile(pts), "week": None, "month": None}}
    out = Q.score_rows([_row("day", 0.02, 1.0)], frozen)
    check("constant-unit horizon is scored", len(out) == 1)
    r2 = _row("day", 0.02, 1.0)
    u2 = Q.unit_pct(r2)
    h2 = Q.quantile_half(r2, {"a": 800.0, "b": -(800.0 / math.log(u2))})
    check("combined log-width is exponentiated once", abs(h2 - 1.0) < 1e-6, str(h2))


def test_usage_shows_frozen_for_describe():
    check("describe usage lists --frozen",
          "describe --frozen FILE" in (Q.__doc__ or ""))


def test_score_skips_unfit_horizon():
    frozen = {"quantile": {"day": {"a": 0.0, "b": 1.0}, "week": None, "month": None}}
    out = Q.score_rows([_row("day", 0.02, 1.0), _row("week", 0.02, 1.0)], frozen)
    check("unfit horizon not scored", [o["horizon"] for o in out] == ["day"])
    check("inside band flagged", out[0]["in_ch"] is True)
    out = Q.score_rows([_row("day", 0.02, 5.0)], frozen)
    check("outside band flagged", out[0]["in_ch"] is False)


def test_score_refuses_training_cells():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = Q.main(["score", "--frozen", "x", "--captures", "/nonexistent", "--min-cell", "90"])
    check("refuses min-cell below 91", rc == 2 and "refusing" in buf.getvalue())


def run_all():
    for fn in (test_constants, test_pinball, test_fit_exact_line, test_fit_quantile_level,
               test_tie_break, test_tie_break_smaller_a, test_constant_unit_and_overflow,
               test_usage_shows_frozen_for_describe, test_points_and_half, test_score_skips_unfit_horizon,
               test_score_refuses_training_cells):
        fn()


class Suite(unittest.TestCase):
    def test_checks(self):
        CHECKS["pass"] = CHECKS["fail"] = 0
        run_all()
        self.assertEqual(CHECKS["fail"], 0)
        self.assertGreater(CHECKS["pass"], 0)


def main():
    CHECKS["pass"] = CHECKS["fail"] = 0
    run_all()
    print("test_loghar_quantile: %d passed, %d failed" % (CHECKS["pass"], CHECKS["fail"]))
    return 1 if CHECKS["fail"] else 0


if __name__ == "__main__":
    sys.exit(main())
