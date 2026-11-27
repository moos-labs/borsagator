"""Tests for benchmarks/macro_event_study.py: fixed synthetic inputs."""
import importlib.util
import math
import os
import sys
import unittest
import datetime as dt

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "macro_event_study", os.path.join(HERE, "..", "benchmarks", "macro_event_study.py"))
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)
CHECKS = {"pass": 0, "fail": 0}


def check(name, ok, detail=""):
    if ok:
        CHECKS["pass"] += 1
    else:
        CHECKS["fail"] += 1
        print("FAIL", name, detail)


def mk(n=200, start="2020-01-01", jump_at=None, jump=0.0, base=0.001):
    d0 = dt.date.fromisoformat(start)
    rows, c = [], 100.0
    for i in range(n):
        c *= math.exp(base + (jump if i == jump_at else 0.0))
        rows.append(((d0 + dt.timedelta(days=i)).isoformat(), c))
    return rows


def test_session0_and_windows():
    s = mk()
    dates = [d for d, _ in s]
    check("session0 exact", M.session0(dates, dates[10]) == 10)
    check("session0 next", M.session0(dates, "2019-12-01") == 0 and M.session0(dates, "2030-01-01") is None)
    # jump of 5% on series index 100 (return index 99): event date = that date
    s = mk(jump_at=100, jump=0.05)
    ev = [{"type": "t", "date": s[100][0]}]
    r = M.study(s, ev)["t|pre"]
    check("one event", r["n_events"] == 1 and r["n_skipped"] == 0)
    check("AAR at 0 equals jump", abs(r["aar_by_offset"]["0"] - 0.05) < 1e-9, r["aar_by_offset"])
    check("AAR other offsets zero", all(abs(r["aar_by_offset"][str(o)]) < 1e-9 for o in (-2, -1, 1, 2)))
    check("CAR is the jump", abs(r["mean_car"] - 0.05) < 1e-9)
    check("single event LOEO None", r["loeo_mean_car_min"] is None)
    check("no verdict key", not any("verdict" in k or "p_value" in k for k in r))


def test_estimation_excludes_other_events_and_edges():
    s = mk(300, jump_at=100, jump=0.05)
    dates = [d for d, _ in s]
    # a second event inside the first's estimation window at offset -30 with its own jump
    s2 = mk(300, jump_at=100, jump=0.05)
    s2[70:] = [(d, c * math.exp(0.2)) for d, c in s2[70:]]   # +20% jump on return index 69 (series idx 70)
    ev = [{"type": "t", "date": dates[100]}, {"type": "u", "date": dates[70]}]
    r = M.study(s2, ev)
        # event 70 inside estimation (offset -30) of event 100: its own window sessions (68..72) are excluded;
    # outside its window the estimation mean is clean, so AAR(0) of event 100 stays the 5% jump
    check("AAR 0 clean", abs(r["t|pre"]["aar_by_offset"]["0"] - 0.05) < 1e-9, r["t|pre"]["aar_by_offset"]["0"])
    # edge: event too early has no 60 pre sessions
    e = M.study(s, [{"type": "t", "date": dates[30]}])
    check("early event skipped", e["t|pre"]["n_events"] == 0 and e["t|pre"]["n_skipped"] == 1)
    e = M.study(s, [{"type": "t", "date": dates[-1]}])
    check("late event skipped", e["t|pre"]["n_skipped"] == 1)


def test_regime_split_and_loeo():
    s = mk(400, start="2021-01-01")
    dates = [d for d, _ in s]
    ev = [{"type": "t", "date": "2021-09-04"}, {"type": "t", "date": "2021-09-05"}]
    r = M.study(s, ev)
    check("split pre", r["t|pre"]["n_events"] == 1 and r["t|post"]["n_events"] == 1)
    # LOEO on three events with different CARs
    jumps = {150: 0.02, 220: 0.04, 290: 0.06}
    c = 100.0
    rows = []
    d0 = dt.date.fromisoformat("2020-01-01")
    for i in range(400):
        c *= math.exp(0.001 + jumps.get(i, 0.0))
        rows.append(((d0 + dt.timedelta(days=i)).isoformat(), c))
    ev = [{"type": "t", "date": rows[i][0]} for i in jumps]
    r = M.study(rows, ev)["t|pre"]
    check("mean CAR", abs(r["mean_car"] - 0.04) < 1e-6, r["mean_car"])
    check("LOEO min max", abs(r["loeo_mean_car_min"] - 0.03) < 1e-6 and abs(r["loeo_mean_car_max"] - 0.05) < 1e-6, (r["loeo_mean_car_min"], r["loeo_mean_car_max"]))
    check("constants", M.OFFSETS == (-2, -1, 0, 1, 2) and M.EST_LO == -60 and M.EST_HI == -11 and M.SPLIT == "2021-09-05")


def test_edge_boundaries():
    s = mk(300)
    dates = [d for d, _ in s]
    n = len(s)
    ok = M.study(s, [{"type": "t", "date": dates[61]}])["t|pre"]
    bad = M.study(s, [{"type": "t", "date": dates[60]}])["t|pre"]
    check("first allowed event (60 pre returns)", ok["n_events"] == 1, ok)
    check("one short is skipped", bad["n_events"] == 0 and bad["n_skipped"] == 1, bad)
    ok = M.study(s, [{"type": "t", "date": dates[n - 3]}])["t|pre"]
    bad = M.study(s, [{"type": "t", "date": dates[n - 2]}])["t|pre"]
    check("last allowed event (2 post returns)", ok["n_events"] == 1, ok)
    check("one short post is skipped", bad["n_events"] == 0 and bad["n_skipped"] == 1, bad)


def test_min_estimation():
    s = mk(300, jump_at=100, jump=0.05)
    dates = [d for d, _ in s]
    # many events blanket the estimation window: only < MIN_EST usable returns remain
    ev = [{"type": "t", "date": dates[100]}] + [{"type": "u", "date": dates[100 - k]} for k in range(6, 56, 5)]
    r = M.study(s, ev)
    check("insufficient estimation skipped", r["t|pre"]["n_events"] == 0 and r["t|pre"]["n_skipped"] == 1, r.get("t|pre"))


def run_all():
    for fn in (test_session0_and_windows, test_estimation_excludes_other_events_and_edges,
               test_regime_split_and_loeo, test_edge_boundaries, test_min_estimation):
        fn()


class Suite(unittest.TestCase):
    def test_checks(self):
        CHECKS["pass"] = CHECKS["fail"] = 0
        run_all()
        self.assertEqual(CHECKS["fail"], 0)
        self.assertGreater(CHECKS["pass"], 0)


def main():
    run_all()
    print("test_macro_event_study: %d passed, %d failed" % (CHECKS["pass"], CHECKS["fail"]))
    sys.exit(1 if CHECKS["fail"] else 0)


if __name__ == "__main__":
    main()
