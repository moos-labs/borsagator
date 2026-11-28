"""Tests for scripts/score_fx_conversion.py: fixed synthetic inputs only."""
import datetime
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import score_fx_conversion as C  # noqa: E402

CHECKS = {"pass": 0, "fail": 0}


def check(name, cond, detail=""):
    if cond:
        CHECKS["pass"] += 1
    else:
        CHECKS["fail"] += 1
        print("FAIL", name, detail)


def hold_rows(gain, months=12, per=4):
    """Hold-out rows: `per` rows in each of `months` calendar months of 2026, constant realised return."""
    rows = []
    for m in range(1, months + 1):
        for k in range(per):
            rows.append(("2026-%02d-%02d" % (m, 1 + k), 0, m, gain))
    return rows


def train_rows(mean, n=40):
    return [("2025-01-%02d" % (1 + (i % 28)), 0, 1, mean) for i in range(n)]


def test_slots():
    # 2026-01-05 is a Monday. 12 weekday sessions, close doubling-free fixed values.
    start = datetime.date(2026, 1, 5)
    s = []
    d = start
    while len(s) < 30:
        if d.weekday() < 5:
            s.append((d.isoformat(), 100.0 + len(s)))
        d += datetime.timedelta(days=1)
    day = C.slot_rows(s, "day")
    check("day slot: one row per session, last has no realised close", len(day) == 30 and day[-1][3] is None and day[0][3] is not None)
    check("day slot: weekday carried (first session is Monday)", day[0][1] == 0 and day[4][1] == 4)
    check("day slot: return is the log move to the next session in %",
          abs(day[0][3] - math.log(101.0 / 100.0) * 100) < 1e-12)
    wk = C.slot_rows(s, "week")
    check("week slot: Monday starts only, 5-session hold", [r[0] for r in wk] == [s[i][0] for i in (0, 5, 10, 15, 20, 25)]
          and abs(wk[0][3] - math.log(105.0 / 100.0) * 100) < 1e-12 and wk[-1][3] is None)
    mo = C.slot_rows(s, "month")
    check("month slot: first session of each calendar month, 21-session hold",
          len(mo) == 2 and mo[0][0] == "2026-01-05"
          and mo[1][0][:7] == "2026-02" and abs(mo[0][3] - math.log(121.0 / 100.0) * 100) < 1e-12)
    b = C.buckets(day, "day")
    check("day buckets are the five weekdays", sorted(b) == ["dow0", "dow1", "dow2", "dow3", "dow4"])
    check("month slot adds month-of-year buckets", "all" in C.buckets(mo, "month") and "moy01" in C.buckets(mo, "month"))


def test_score_bucket():
    hold = hold_rows(0.5)
    r = C.score_bucket(train_rows(0.2), hold, 0.07, reps=200)
    check("positive training mean: long direction, n and clusters counted", r["direction"] == 1 and r["n"] == 48 and r["clusters"] == 12, str(r))
    check("constant gain 0.5: mean and conservative edge are 0.5", abs(r["mean_gain_pct"] - 0.5) < 1e-12 and abs(r["conservative_edge_pct"] - 0.5) < 1e-12, str(r))
    check("edge 0.5 > cost 0.07 passes the rule", r["lower_gt_cost"] is True)
    r = C.score_bucket(train_rows(0.2), hold, 0.5, reps=200)
    check("edge exactly equal to cost does NOT pass (strict >)", r["lower_gt_cost"] is False, str(r))
    check("grid labels: 0.1 and 0.5 sides", r["lower_gt_grid"]["0.1"] is True and r["lower_gt_grid"]["0.5"] is False, str(r["lower_gt_grid"]))
    r = C.score_bucket(train_rows(-0.2), hold, 0.07, reps=200)
    check("negative training mean flips direction: gain is the negated hold-out return",
          r["direction"] == -1 and abs(r["mean_gain_pct"] + 0.5) < 1e-12 and r["lower_gt_cost"] is False, str(r))
    check("always-long and always-short benchmarks are reported", abs(r["long_base_mean_pct"] - 0.5) < 1e-12 and abs(r["short_base_mean_pct"] + 0.5) < 1e-12)
    r = C.score_bucket(train_rows(0.2, n=29), hold, 0.07, reps=200)
    check("under 30 training rows: abstain, no direction", r.get("abstain") == "train_n_under_30" and "direction" not in r)
    r = C.score_bucket(train_rows(0.2), hold_rows(0.5, months=9), 0.07, reps=200)
    check("9 clusters: counts only, no edge", r.get("counts_only") is True and "conservative_edge_pct" not in r, str(r))
    r = C.score_bucket(train_rows(0.2), hold_rows(0.5, months=12, per=2), 0.07, reps=200)
    check("24 rows over 12 clusters: counts only (n gate)", r.get("counts_only") is True and r["n"] == 24, str(r))
    hold = hold_rows(0.5) + [("2026-12-30", 0, 12, None)]
    r = C.score_bucket(train_rows(0.2), hold, 0.07, reps=200)
    check("unmatured row is counted and not scored", r["unmatured"] == 1 and r["n"] == 48)
    # noisy gains: the conservative edge sits below the mean
    noisy = [(d, w, m, 0.5 + (0.4 if i % 2 else -0.4)) for i, (d, w, m, _) in enumerate(hold_rows(0.5))]
    r = C.score_bucket(train_rows(0.2), noisy, 0.07, reps=300)
    check("noisy gains: conservative edge below the mean", r["conservative_edge_pct"] < r["mean_gain_pct"] - 0.01, str(r))


def test_triangles():
    series = {"A": [("2026-01-%02d" % d, 2.0) for d in range(1, 29)],
              "B": [("2026-01-%02d" % d, 3.0) for d in range(1, 29)],
              "C": [("2026-01-%02d" % d, 6.0) for d in range(1, 29)]}
    r = C.triangle_resid(series, "C", [("A", 1), ("B", 1)])
    check("identity triangle: residual is zero on every date", len(r) == 28 and all(abs(v) < 1e-12 for _, v in r))
    series["C"] = [("2026-01-%02d" % d, 6.0 * (1.01 if d == 5 else 1.0)) for d in range(1, 29)]
    r = dict(C.triangle_resid(series, "C", [("A", 1), ("B", 1)]))
    check("a 1% direct-vs-path gap shows as 100 x log(1.01)", abs(r["2026-01-05"] - math.log(1.01) * 100) < 1e-12 and abs(r["2026-01-06"]) < 1e-12)
    series["D"] = [("2026-01-%02d" % d, 1.5) for d in range(1, 29)]
    r = C.triangle_resid(series, "D", [("B", 1), ("A", -1)])
    check("a divide leg uses the inverse", all(abs(v) < 1e-12 for _, v in r) and len(r) == 28)
    series["E"] = [("2026-01-%02d" % d, 9.0) for d in range(2, 29)]
    check("only dates present in all three series are used", len(C.triangle_resid(series, "E", [("A", 1), ("B", 1)])) == 27)
    resid = [("2025-06-%02d" % (1 + i % 28), 0.2) for i in range(40)] + [("2026-%02d-%02d" % (1 + i % 12, 1 + i // 12), 0.5) for i in range(48)]
    t = C.score_triangle(resid, 0.2, reps=200)
    check("triangle: cycle cost is 1.5 x the class round trip, strict > rule",
          abs(t["cycle_cost_pct"] - 0.3) < 1e-12 and t["lower_gt_cost"] is True and abs(t["conservative_edge_pct"] - 0.5) < 1e-12, str(t))
    t = C.score_triangle(resid, 0.4, reps=200)
    check("a cycle cost of 0.6 exceeds the 0.5 edge", t["lower_gt_cost"] is False, str(t))


def test_constants():
    check("registered costs and bootstrap constants", C.COST_RT == {"major": 0.07, "egp": 0.2} and C.D.REPS == 5000 and C.D.SEED == 20261125)
    check("no hold-out date in the training split of slot rows", C.HOLDOUT_START == "2026-01-01")
    rc = C.main(["--data", "/nonexistent", "--asof", "2026-11-28", "--out-json", "/tmp/x.json", "--reps", "10"])
    check("non-registered reps refused", rc == 2)


def main():
    test_slots()
    test_score_bucket()
    test_triangles()
    test_constants()
    print("test_score_fx_conversion: %d passed, %d failed" % (CHECKS["pass"], CHECKS["fail"]))
    sys.exit(1 if CHECKS["fail"] else 0)


if __name__ == "__main__":
    main()
