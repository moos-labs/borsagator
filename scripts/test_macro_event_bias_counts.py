"""Tests for benchmarks/macro_event_bias_counts.py: fixed synthetic inputs."""
import importlib.util
import math
import os
import sys
import unittest
import datetime as dt

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "macro_event_bias_counts", os.path.join(HERE, "..", "benchmarks", "macro_event_bias_counts.py"))
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)
CHECKS = {"pass": 0, "fail": 0}


def check(name, ok, detail=""):
    if ok:
        CHECKS["pass"] += 1
    else:
        CHECKS["fail"] += 1
        print("FAIL", name, detail)


AAR = {-2: 0.0, -1: 0.0, 0: 0.0, 1: 0.02, 2: 0.0}      # 2.0 pct at offset +1, exact in floats
ROW = {"sessions": 1, "range_low_pct": -8.0, "range_high_pct": 8.0, "horizon": "day", "as_of": "x"}  # W = 8, cap = 2.0


def ev(typ, s0):
    return {"event": {"type": typ, "date": "d"}, "s0": s0, "ab": None}


def bias(row, c_idx, evs, aars):
    return B.capture_bias(row, c_idx, evs, aars)


def test_window_membership_and_point_in_time():
    evs = [ev("cbe_scheduled", 100)]
    check("c=-3 outside", bias(ROW, 97, evs, [AAR]) is None)
    check("c=+3 outside", bias(ROW, 103, evs, [AAR]) is None)
    check("c=-2 inside", bias(ROW, 98, evs, [AAR]) is not None)
    check("c=+2 inside, empty range -> 0", bias(ROW, 102, evs, [AAR])[0] == 0.0)
    b, info = bias(ROW, 100, evs, [AAR])
    check("scheduled c=0 offset +1 bias 2.0", b == 2.0 and not info["capped"], (b, info))
    sp = [ev("cbe_special", 100)]
    check("special c=-1 excluded", bias(ROW, 99, sp, [AAR]) is None)
    check("special c=0 included", bias(ROW, 100, sp, [AAR]) is not None)
    bd = [ev("budget", 100)]
    check("budget treated as special: c=-1 excluded", bias(ROW, 99, bd, [AAR]) is None)
    check("scheduled c=-1 included", bias(ROW, 99, evs, [AAR]) is not None)


def test_sum_range_and_horizon():
    evs = [ev("cbe_scheduled", 100)]
    a = {-2: 0.001, -1: 0.002, 0: 0.004, 1: 0.008, 2: 0.016}
    r3 = dict(ROW, sessions=3, range_low_pct=-100.0, range_high_pct=100.0)
    # c=-2, S=3: offsets -1..1
    b, _ = bias(r3, 98, evs, [a])
    check("range -1..1", abs(b - (0.002 + 0.004 + 0.008) * 100) < 1e-9, b)
    # c=0, S=3: offsets 1..2 (clipped at +2)
    b, _ = bias(r3, 100, evs, [a])
    check("range clipped at +2", abs(b - (0.008 + 0.016) * 100) < 1e-9, b)
    # c=-1, S=1: offset 0 only
    b, _ = bias(dict(r3, sessions=1), 99, evs, [a])
    check("S=1 single offset", abs(b - 0.4) < 1e-9, b)


def test_cap_boundary_and_sign():
    evs = [ev("cbe_scheduled", 100)]
    b, info = bias(ROW, 100, evs, [AAR])                          # |tot| == cap
    check("equal to cap not capped", b == 2.0 and not info["capped"], (b, info))
    tight = dict(ROW, range_low_pct=-7.9, range_high_pct=7.9)
    b, info = bias(tight, 100, evs, [AAR])                        # cap 1.975
    check("above cap is capped", info["capped"] and abs(b - 1.975) < 1e-9, (b, info))
    neg = {**AAR, 1: -0.02}
    b, info = bias(tight, 100, evs, [neg])
    check("negative sign kept", info["capped"] and abs(b + 1.975) < 1e-9, (b, info))
    b, info = bias(ROW, 100, evs, [{**AAR, 1: 0.0}])
    check("zero stays zero", b == 0.0 and not info["capped"])


def test_overlap_max_abs_then_cap():
    evs = [ev("cbe_scheduled", 100), ev("cbe_scheduled", 101)]
    small = {-2: 0.0, -1: 0.0, 0: 0.0, 1: 0.005, 2: 0.0}
    big = {-2: 0.0, -1: 0.0, 0: 0.0, 1: 0.0, 2: -0.03}
    wide = dict(ROW, range_low_pct=-100.0, range_high_pct=100.0)
    # capture at 101, S=1: first event c=1 -> offset 2 = -3.0; second c=0 -> offset 1 = +0.5
    b, _ = bias(wide, 101, evs, [big, small])
    check("overlap picks larger |term| (event 1)", abs(b + 3.0) < 1e-9, b)
    b, _ = bias(wide, 101, evs, [{**big, 2: 0.001}, small])
    check("overlap picks larger |term| (event 2)", abs(b - 0.5) < 1e-9, b)
    # capture at 100, S=2: first c=0 -> offsets 1..2; second c=-1 -> offsets 0..1
    r2 = dict(wide, sessions=2)
    b, _ = bias(r2, 100, evs, [{**big, 1: 0.0}, small])
    check("overlap keeps larger |term| and its sign", abs(b + 3.0) < 1e-9, b)
    b, info = bias(dict(r2, range_low_pct=-8.0, range_high_pct=8.0), 100, evs, [big, small])
    check("overlap then cap", abs(b + 2.0) < 1e-9 and info["capped"], (b, info))
    _, info = bias(ROW, 100, [ev("cbe_scheduled", 100)], [None])
    check("no prior AAR counted, bias 0", info["no_prior"] and bias(ROW, 100, [ev("cbe_scheduled", 100)], [None])[0] == 0.0)


def mkev(typ, s0, jump_ab):
    return {"event": {"type": typ, "date": "d"}, "s0": s0, "ab": jump_ab}


def test_prior_aar_no_lookahead():
    one = {o: 0.01 for o in (-2, -1, 0, 1, 2)}
    two = {o: 0.03 for o in (-2, -1, 0, 1, 2)}
    tgt = mkev("cbe_scheduled", 200, None)
    # prior ends at s0+2 and target window starts at 198: need s0+2 < 198 -> s0 <= 195
    evs = [mkev("cbe_scheduled", 195, one), mkev("cbe_scheduled", 196, two), tgt]
    a = B.prior_aar(evs, 2)
    check("s0 diff 5 included, diff 4 excluded", a is not None and abs(a[0] - 0.01) < 1e-12, a)
    evs = [mkev("cbe_special", 100, two), tgt]
    check("other type ignored", B.prior_aar(evs, 1) is None)
    evs = [mkev("cbe_scheduled", 100, None), tgt]
    check("skipped (ab None) event ignored", B.prior_aar(evs, 1) is None)
    # regression: an event with s0 None (outside the series) must not raise
    none_tgt = mkev("cbe_scheduled", None, None)
    check("target s0 None -> None", B.prior_aar([mkev("cbe_scheduled", 100, one), none_tgt], 1) is None)
    check("pool event s0 None ignored", B.prior_aar([mkev("cbe_scheduled", None, one), tgt], 1) is None)
    evs = [tgt, mkev("cbe_scheduled", 300, one)]
    check("future event ignored", B.prior_aar(evs, 0) is None)
    evs = [mkev("cbe_scheduled", 100, one), mkev("cbe_scheduled", 150, two), tgt]
    check("mean of priors", abs(B.prior_aar(evs, 2)[1] - 0.02) < 1e-12)


def test_cutoff_index_and_run():
    dates = ["2026-01-01", "2026-01-02", "2026-01-04"]
    check("cutoff exact", B.cutoff_index(dates, "2026-01-02") == 1)
    check("cutoff between -> previous", B.cutoff_index(dates, "2026-01-03") == 1)
    check("cutoff before series", B.cutoff_index(dates, "2025-12-31") is None)
    check("cutoff after series", B.cutoff_index(dates, "2027-01-01") == 2)
    # end to end on a synthetic series: prior event jumps +2% on the session after its date
    d0 = dt.date(2020, 1, 1)
    rows_s, c = [], 100.0
    for i in range(400):
        c *= math.exp(0.001 + (0.02 if i == 121 else 0.0))
        rows_s.append(((d0 + dt.timedelta(days=i)).isoformat(), c))
    ds = [r[0] for r in rows_s]
    events = [{"type": "cbe_scheduled", "date": ds[120]}, {"type": "cbe_scheduled", "date": ds[300]}]
    led = [dict(ROW, as_of=ds[300], horizon="day", sessions=1, range_low_pct=-100.0, range_high_pct=100.0),
           dict(ROW, as_of=ds[200], horizon="day", sessions=1),
           dict(ROW, as_of=ds[299], horizon="week", sessions=3, range_low_pct=-0.2, range_high_pct=0.2)]
    out = B.run(rows_s, events, led)
    check("n_captures", out["n_captures"] == 3)
    check("two in window", out["n_in_window"] == 2, out)
    check("one capped", out["n_capped"] == 1, out)
    check("no prior none", out["n_no_prior_aar"] == 0, out)
    cell = out["by_type_horizon"]["cbe_scheduled|day"]
    check("day cell counts", cell["n"] == 1 and cell["n_bias_pos"] == 1 and cell["n_capped"] == 0, cell)
    wk = out["by_type_horizon"]["cbe_scheduled|week"]
    check("week cell positive capped", wk["n"] == 1 and wk["n_capped"] == 1 and wk["n_bias_pos"] == 1, wk)
    flat = repr(out)
    check("no verdict keys", not any(w in flat for w in ("verdict", "keep", "p_value")))


def run_all():
    for fn in (test_window_membership_and_point_in_time, test_sum_range_and_horizon, test_cap_boundary_and_sign,
               test_overlap_max_abs_then_cap, test_prior_aar_no_lookahead, test_cutoff_index_and_run):
        fn()


class Suite(unittest.TestCase):
    def test_checks(self):
        CHECKS["pass"] = CHECKS["fail"] = 0
        run_all()
        self.assertEqual(CHECKS["fail"], 0)
        self.assertGreater(CHECKS["pass"], 0)


def main():
    run_all()
    print("test_macro_event_bias_counts: %d passed, %d failed" % (CHECKS["pass"], CHECKS["fail"]))
    sys.exit(1 if CHECKS["fail"] else 0)


if __name__ == "__main__":
    main()
