"""Fixed synthetic checks for scripts/score_fx_descriptive.py."""
import csv
import math
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import score_fx_descriptive as S  # noqa: E402

PASS = FAIL = 0


def check(name, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
    else:
        FAIL += 1
        print("FAIL", name, detail)


def write(path, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "high", "low", "close", "volume", "adjclose"])
        for d, c in rows:
            w.writerow([d, "", "", "" if c is None else c, "", ""])


def run():
    check("winkler inside = width; below adds 10 x distance; above adds 10 x distance; edges inside",
          S.winkler(0.5, -1, 1) == 2 and abs(S.winkler(-1.5, -1, 1) - 7.0) < 1e-12
          and abs(S.winkler(1.2, -1, 1) - 4.0) < 1e-12 and S.winkler(1, -1, 1) == 2 and S.winkler(-1, -1, 1) == 2)
    check("next_monday: Sat 2023-01-07 and Sun 2023-01-08 -> 2023-01-09; Monday is itself",
          S.next_monday("2023-01-07") == "2023-01-09" and S.next_monday("2023-01-08") == "2023-01-09"
          and S.next_monday("2023-01-09") == "2023-01-09")
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "x.csv")
        write(p, [("2023-01-06", 1.0), ("2023-01-07", 9.0), ("2023-01-08", 9.0), ("2023-01-09", 2.0),
                  ("2023-01-14", 9.0), ("2023-01-16", None), ("2025-12-31", 3.0), ("2026-01-01", 99.0), ("2026-01-05", 99.0)])
        sess, cnt = S.load_sessions(p)
        check("weekend bars merge into Monday (Monday close used), orphan weekend bar counted, null close skipped, hold-out dropped at load",
              sess == [("2023-01-06", 1.0), ("2023-01-09", 2.0), ("2025-12-31", 3.0)]
              and cnt == {"weekend_bars_merged": 2, "weekend_bars_dropped_no_monday": 1, "holdout_rows_dropped_at_load": 2}, str((sess, cnt)))
        write(p, [("2018-12-31", 5.0), ("2019-01-01", 1.0)])
        check("rows before the training start are not loaded", S.load_sessions(p)[0] == [("2019-01-01", 1.0)])
    closes = [1.0 * (1.01 ** i) * (1 if i % 2 else 1.001) for i in range(200)]
    sess = [("d%03d" % i, c) for i, c in enumerate(closes)]
    rows, ex = S.build_rows(sess, 5, False, False)
    # cutoffs at 60, 65, ..., last with i+5 < 200 -> 60..190 step 5 => 27 rows... i+5<200 => i<=194 -> 60..190 = 27
    check("non-overlapping cutoffs every h sessions from index 60, matured only", len(rows) == 27 and rows[0]["cutoff"] == "d060"
          and rows[1]["cutoff"] == "d065" and rows[-1]["cutoff"] == "d190", str((len(rows), rows[0]["cutoff"], rows[-1]["cutoff"])))
    check("realised move is log(close[i+h]/close[i]) in pp", abs(rows[0]["real"] - math.log(closes[65] / closes[60]) * 100) < 1e-12)
    # exact band maths on one row
    r = [{"cutoff": "2023-01-02", "cluster": "2023-01", "real": 3.0, "sigma": 0.01}]
    cl = S.score(r, "day")
    half_v, half_n = 1.15 * 0.01 * 100, 1.2816 * 0.01 * 100
    check("score: v2 half 1.15 x sigma x 100 and naive half 1.2816 x sigma x 100; miss penalised 10 x distance",
          abs(cl[0][1] - (2 * half_v + 10 * (3.0 - half_v))) < 1e-9 and abs(cl[0][2] - (2 * half_n + 10 * (3.0 - half_n))) < 1e-9
          and cl[0][3] == 0 and cl[0][4] == 0)
    cl2 = S.score([{"cutoff": "a", "cluster": "m1", "real": 0.5, "sigma": 0.01}, {"cutoff": "b", "cluster": "m2", "real": -0.2, "sigma": 0.01}], "week")
    st = S.stats(cl2)
    check("stats: n, clusters, coverage and RangeSkill from the cluster sums", st["n"] == 2 and st["clusters"] == 2
          and st["coverage_v2"] == 1.0 and st["share_up"] == 0.5 and abs(st["rw_mean_abs_move_pp"] - 0.35) < 1e-12
          and abs(st["range_skill_v2_vs_naive"] - (1 - (1.28 / 1.2816))) < 1e-9, str(st))
    b1, b2 = S.boot(cl2, reps=200), S.boot(cl2, reps=200)
    check("bootstrap is deterministic for the fixed seed and brackets the point estimate order", b1 == b2
          and b1["range_skill_ci95"][0] <= b1["range_skill_ci95"][1])
    # jump flags: flat series with one jump
    flat = [1.0 + 0.0001 * (i % 3) for i in range(100)]
    flat[80] = 1.5
    fl = S.jump_flags(flat)
    check("jump flag marks only the jump bar (the day after the jump is a reversal, also flagged), none before", fl[80] and not any(fl[:80]))
    # EGP regime filter: sessions before 2024-03-07 and 2024-03-06 are not used
    es = [("2024-03-0%d" % k, 30.0) for k in (4, 5, 6)] + [("2024-03-07", 49.0)]
    check("EGP rows: nothing before the float and no 2024-03-06 survive", S.build_rows(es, 1, True, False)[0] == [])
    # hold-out rows cannot change the output
    with tempfile.TemporaryDirectory() as d:
        base = [("2025-%02d-%02d" % (m, dd), 1.1 + 0.001 * (m * 31 + dd) + 0.0003 * ((m + dd) % 4)) for m in range(1, 13) for dd in (1, 2, 3, 4, 5, 8, 9, 10, 11, 12, 15, 16, 17, 18, 19, 22, 23, 24, 25, 26) ]
        base = [x for x in base if __import__("datetime").date.fromisoformat(x[0]).weekday() < 5]
        for name in ("EURUSD", "USDJPY", "USDEGP"):
            write(os.path.join(d, name + ".csv"), base)
        a = S.run(d, reps=50)
        write(os.path.join(d, "EURUSD.csv"), base + [("2026-02-02", 500.0), ("2026-02-03", 1.0)])
        b = S.run(d, reps=50)
        check("hold-out rows (2026 dates) do not change any number", a["cells"]["EURUSD"]["horizons"] == b["cells"]["EURUSD"]["horizons"]
              and b["cells"]["EURUSD"]["load_counts"]["holdout_rows_dropped_at_load"] == 2)
        md = S.render(a).lower()
        check("rendered output carries no verdict word", not any(w in md for w in ("pass", "fail", "keep", "adopt", "reject")))
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    rc = run()
    print("test_score_fx_descriptive: %d passed, %d failed" % (PASS, FAIL))
    sys.exit(rc)
