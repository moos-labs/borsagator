"""Tests for benchmarks/score_macro_centre_tilt.py: fixed synthetic inputs."""
import contextlib
import datetime
import importlib.util
import io
import os
import sys
import unittest

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "score_macro_centre_tilt", os.path.join(HERE, "..", "benchmarks", "score_macro_centre_tilt.py"))
T = importlib.util.module_from_spec(spec)
spec.loader.exec_module(T)
CHECKS = {"pass": 0, "fail": 0}


def check(name, ok, detail=""):
    if ok:
        CHECKS["pass"] += 1
    else:
        CHECKS["fail"] += 1
        print("FAIL", name, detail)


def D(s):
    return datetime.date.fromisoformat(s)


def rowset(last, ref, pub_last="2026-01-01", pub_ref="2025-10-01"):
    # last observed 2026-01-01, ref observed 63 days earlier (2025-10-30)
    return [(D("2025-10-30"), D(pub_ref), ref), (D("2026-01-01"), D(pub_last), last)]


def test_constants():
    check("S", T.S == 0.10)
    check("window", T.WINDOW_DAYS == 63)
    check("thetas", (T.SERIES["oil"][1], T.SERIES["fx"][1], T.SERIES["tbill"][1]) == (0.05, 0.02, 1.0))
    check("signs", (T.SERIES["oil"][3], T.SERIES["fx"][3], T.SERIES["tbill"][3]) == (-1, 1, -1))


def test_signal_boundaries():
    s = T.signal
    check("rel just above theta is +1", s(rowset(105.01, 100.0), "2026-01-01", 0.05, "rel")[0] == 1)
    check("rel exactly theta is 0", s(rowset(105.0, 100.0), "2026-01-01", 0.05, "rel")[0] == 0)
    check("rel just below -theta is -1", s(rowset(94.99, 100.0), "2026-01-01", 0.05, "rel")[0] == -1)
    check("rel exactly -theta is 0", s(rowset(95.0, 100.0), "2026-01-01", 0.05, "rel")[0] == 0)
    check("abs just above 1.0 is +1", s(rowset(21.01, 20.0), "2026-01-01", 1.0, "abs")[0] == 1)
    check("abs exactly 1.0 is 0", s(rowset(21.0, 20.0), "2026-01-01", 1.0, "abs")[0] == 0)
    check("abs below -1.0 is -1", s(rowset(18.99, 20.0), "2026-01-01", 1.0, "abs")[0] == -1)


def test_point_in_time_and_missing():
    s = T.signal
    # latest row published after the cutoff is not usable: only the older row is usable, no 63-day reference
    x, why = s(rowset(120.0, 100.0, pub_last="2026-01-02"), "2026-01-01", 0.05, "rel")
    check("unpublished latest row not used, missing listed", x == 0 and why is not None, why)
    x, why = s(rowset(120.0, 100.0, pub_last="2026-01-01"), "2026-01-01", 0.05, "rel")
    check("published on cutoff day is usable", x == 1 and why is None)
    x, why = s([], "2026-01-01", 0.05, "rel")
    check("no rows is missing", x == 0 and why == "no usable value")
    # reference exactly 63 days before is usable, 62 days is not
    rows62 = [(D("2025-10-31"), D("2025-10-31"), 100.0), (D("2026-01-01"), D("2026-01-01"), 120.0)]
    x, why = s(rows62, "2026-01-01", 0.05, "rel")
    check("62 days is not enough history", x == 0 and why is not None)
    rows63 = [(D("2025-10-30"), D("2025-10-30"), 100.0), (D("2026-01-01"), D("2026-01-01"), 120.0)]
    check("63 days is enough", s(rows63, "2026-01-01", 0.05, "rel")[0] == 1)


def test_composite_and_centre():
    dirs = [v[3] for v in T.SERIES.values()]
    check("all up: -1 +1 -1 = -1/3", abs(T.composite([1, 1, 1], dirs) - (-1 / 3.0)) < 1e-12)
    check("oil down, fx up, tbill down = 1", abs(T.composite([-1, 1, -1], dirs) - 1.0) < 1e-12)
    check("all zero is 0", T.composite([0, 0, 0], dirs) == 0)
    # tilt_rows: centre = S x m x v2 half, width equals v2
    series = {"oil": rowset(94.0, 100.0), "fx": rowset(120.0, 100.0), "tbill": rowset(18.0, 20.0)}
    row = {"ticker": "A", "as_of": "2026-01-01", "horizon": "week", "real": 0.0,
           "naive_half": 5.0, "mult": 1.0, "v2_sigma": 0.02}
    pairs, listed = T.tilt_rows([row], series)
    p = pairs[0]
    v2h = T.R.half_pct(0.02, "week", T.ens_mod.V2_BAND_K["week"], 1.0)
    check("m is 1", abs(p["m"] - 1.0) < 1e-12 and not listed)
    check("centre is 0.10 x v2 half", abs(p["centre"] - 0.10 * v2h) < 1e-12, str(p["centre"]))
    edge = dict(row, real=0.10 * v2h + v2h)
    check("edge of tilted band inclusive", T.tilt_rows([edge], series)[0][0]["in_ch"])
    out = dict(row, real=0.10 * v2h + v2h + 1e-6)
    check("just outside tilted band misses", not T.tilt_rows([out], series)[0][0]["in_ch"])
    want = T.bs.winkler_is(edge["real"], p["centre"] - v2h, p["centre"] + v2h)
    check("interval score uses the tilted band", T.tilt_rows([edge], series)[0][0]["is_ch"] == want
          and want != T.R.row_is(edge, v2h))
    check("v2 band stays centred on 0", T.tilt_rows([edge], series)[0][0]["in_v2"] is False)
    miss = {"oil": [], "fx": series["fx"], "tbill": series["tbill"]}
    pairs, listed = T.tilt_rows([row], miss)
    check("missing signal set to 0 and listed", len(listed) == 1 and "oil" in listed[0]
          and abs(pairs[0]["m"] - 2 / 3.0) < 1e-12, str(listed))
    check("zero v2 sigma row dropped", T.tilt_rows([dict(row, v2_sigma=0)], series)[0] == [])


def test_refusal():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc1 = T.main(["describe", "--captures", "x", "--min-cell", "47"])
        rc2 = T.main(["describe", "--captures", "x", "--max-cell", "91"])
    check("refuses cells outside 48-90", rc1 == 2 and rc2 == 2 and buf.getvalue().count("refusing") == 2)


def test_counts():
    pairs = [{"ticker": "A", "as_of": "d1", "horizon": "day"}, {"ticker": "B", "as_of": "d1", "horizon": "day"},
             {"ticker": "A", "as_of": "d2", "horizon": "day"}]
    L = T.count_lines(pairs)
    check("day counts", L[0] == "day: rows=3 cutoff clusters=2 tickers=2", L[0])
    check("week empty", L[1] == "week: rows=0 cutoff clusters=0 tickers=0")


def run_all():
    for fn in (test_constants, test_signal_boundaries, test_point_in_time_and_missing,
               test_composite_and_centre, test_refusal, test_counts):
        fn()


class Suite(unittest.TestCase):
    def test_checks(self):
        CHECKS["pass"] = CHECKS["fail"] = 0
        run_all()
        self.assertEqual(CHECKS["fail"], 0)
        self.assertGreater(CHECKS["pass"], 0)


def main():
    run_all()
    print("test_macro_centre_tilt: %d passed, %d failed" % (CHECKS["pass"], CHECKS["fail"]))
    sys.exit(1 if CHECKS["fail"] else 0)


if __name__ == "__main__":
    main()
