"""Fixed synthetic checks for scripts/score_fx_holdout.py. Mutation-checked."""
import csv
import datetime
import math
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import score_fx_holdout as H  # noqa: E402
import score_fx_descriptive as D  # noqa: E402

PASS = FAIL = 0


def check(name, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
    else:
        FAIL += 1
        print("FAIL", name, detail)


def weekdays(start, end):
    d = datetime.date.fromisoformat(start)
    e = datetime.date.fromisoformat(end)
    while d <= e:
        if d.weekday() < 5:
            yield d.isoformat()
        d += datetime.timedelta(days=1)


def write(path, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "high", "low", "close", "volume", "adjclose"])
        for d, c in rows:
            w.writerow([d, "", "", c, "", ""])


def series(end, flat_from=None, drop=()):
    out, c = [], 1.0
    for i, d in enumerate(weekdays("2025-08-01", end)):
        if flat_from is None or d < flat_from:
            c *= 1.0 + (0.004 if i % 2 == 0 else -0.003) * (1 + (i % 7) / 7.0)
        if d not in drop:
            out.append((d, c))
    return out


def run_dir(end="2026-03-31", flat_from=None, asof="2026-04-01", drop_sar=()):
    d = tempfile.mkdtemp()
    base = series(end, flat_from)
    for n in ("EURUSD", "USDJPY", "USDEGP", "USDSAR", "USDAED"):
        write(os.path.join(d, n + ".csv"), base)
    write(os.path.join(d, "USDSAR.csv"), series(end, flat_from, drop_sar))
    for n in ("SAREGP_DERIVED", "AEDEGP_DERIVED"):
        write(os.path.join(d, n + ".csv"), base)
    return H.run(d, asof, reps=200), d


def test_all():
    check("zero-move interval score is 10 x |real|", H.zero_is(0.5) == 5.0 and H.zero_is(-0.25) == 2.5 and H.zero_is(0) == 0)
    # partial day dropped: a bar dated on/after asof is removed, an earlier one is kept
    d = tempfile.mkdtemp()
    p = os.path.join(d, "x.csv")
    write(p, [("2026-03-26", 1.0), ("2026-03-27", 1.1), ("2026-03-30", 1.2)])
    s, c = H.load_all(p, "2026-03-30")
    check("partial-day bar (date == asof) dropped, earlier bars kept", [x[0] for x in s] == ["2026-03-26", "2026-03-27"] and c["partial_day_sessions_dropped"] == 1, str((s, c)))
    s2, _ = H.load_all(p, "2026-03-31")
    check("asof after the last bar drops nothing", len(s2) == 3)
    # rows: first cutoff is the first session >= HOLDOUT_START; cutoffs every h sessions; immature flagged
    sess = series("2026-03-31")
    rows, dropped = H.build_rows(sess, 5, False, False)
    dates = [x[0] for x in sess]
    i0 = next(k for k, x in enumerate(dates) if x >= "2026-01-01")
    check("first cutoff is the first session on/after 2026-01-01 (Jan 1 is a Thursday)", rows[0]["cutoff"] == dates[i0] == "2026-01-01", rows[0]["cutoff"])
    check("cutoffs step by 5 sessions", [r["cutoff"] for r in rows[:3]] == [dates[i0], dates[i0 + 5], dates[i0 + 10]])
    check("no cutoff before the hold-out start", all(r["cutoff"] >= "2026-01-01" for r in rows))
    check("last cutoffs without a realised close are intended, not matured",
          rows[-1]["matured"] is False and rows[-1]["real"] is None and sum(not r["matured"] for r in rows) == 1, str([(r["cutoff"], r["matured"]) for r in rows[-3:]]))
    check("matured boundary: i+h == last index is matured (week)", all(r["matured"] for r in rows[:-1]))
    rows1, _ = H.build_rows(sess, 1, False, False)
    check("day: only the final session lacks a realised close", sum(not r["matured"] for r in rows1) == 1 and rows1[-1]["cutoff"] == dates[-1])
    mc = H.mature_clusters(rows1)
    check("a cluster with an unrealised intended row is not mature; others are", "2026-03" not in mc and {"2026-01", "2026-02"} <= mc, str(mc))
    # frozen bands and scoring
    H.fill(rows1, "day")
    r = rows1[0]
    check("v2 half = 1.15 x sigma x 100, naive half = 1.2816 x sigma x 100 (day)",
          abs(r["half_v2"] - 1.15 * r["sigma"] * 100) < 1e-9 and abs(r["half_naive"] - 1.2816 * r["sigma"] * 100) < 1e-9)
    H.fill(rows1[:6], "month")
    check("month half scales with sqrt(21)", abs(rows1[0]["half_v2"] - 1.20 * rows1[0]["sigma"] * math.sqrt(21) * 100) < 1e-9)
    # full run: gate passes on a noisy series, numbers present, cross-rate counts beside the cross rows
    res, _d = run_dir()
    check("gate passes: every zero-move skill is negative", not res["gate"]["stop_positive_skill"] and all(g["range_skill_zero_move_vs_naive"] < 0 for g in res["gate"]["zero_move"]) and len(res["gate"]["zero_move"]) > 0)
    day = res["cells"]["EURUSD"]["horizons"]["day/all_rows"]
    check("under 10 mature clusters (Jan-Mar = 2 of 3) the cell is counts only, no skill or CI", day["counts_only"] is True and "range_skill_v2_vs_naive" not in day and "range_skill_ci95" not in day, str(day))
    check("rows list carries every row with cell and maturity flag", any(x["cell"] == "EURUSD" and not x["matured"] for x in res["rows"]))
    cc = res["cells"]["SAREGP_DERIVED"]["cross_rate_counts"]
    check("cross-rate counts: full overlap, nothing dropped", cc["dropped_total"] == 0 and cc["overlap_rate_common_over_union"] == 1.0 and cc["common_dates_kept"] > 50, str(cc))
    res2, _ = run_dir(drop_sar=("2026-01-14", "2026-02-03"))
    cc2 = res2["cells"]["SAREGP_DERIVED"]["cross_rate_counts"]
    check("two dates missing in USDSAR: 2 dropped (usdegp only), overlap = common/union",
          cc2["dropped_usdegp_only"] == 2 and cc2["dropped_usdsar_only"] == 0 and cc2["dropped_total"] == 2
          and abs(cc2["overlap_rate_common_over_union"] - cc2["common_dates_kept"] / (cc2["common_dates_kept"] + 2)) < 1e-12, str(cc2))
    # falsification: flat hold-out (real = 0) gives the zero band a perfect score -> STOP, no v2 numbers
    res3, _ = run_dir(flat_from="2026-01-01")
    check("zero-move gate fires on a leakage-like series and stops before any v2 number",
          res3["gate"]["stop_positive_skill"] is True and all("range_skill_v2_vs_naive" not in h for c in res3["cells"].values() for h in c["horizons"].values()) and res3["rows"] == [])
    out_json, out_md = os.path.join(tempfile.mkdtemp(), "o.json"), os.path.join(tempfile.mkdtemp(), "o.md")
    d3 = _d
    rc = H.main(["--data", d3, "--asof", "2026-04-01", "--out-json", out_json, "--out-md", out_md])
    check("main returns 0 on a passing gate", rc == 0 and os.path.exists(out_json))
    check("main refuses non-registered reps", H.main(["--data", d3, "--asof", "2026-04-01", "--out-json", out_json, "--out-md", out_md, "--reps", "10"]) == 2)
    check("gate fires on any positive skill, not on zero or negative", H.gate_positive(1e-9) and not H.gate_positive(0.0) and not H.gate_positive(-0.2))
    # call-site pin: clusters whose zero band scores marginally BETTER than naive must fire the gate
    cl_pos = [[10, 5.0, 10.0, 8, 8, 9.99]]      # zero IS 9.99 < naive 10 -> skill +0.001
    cl_neg = [[10, 5.0, 10.0, 8, 8, 10.01]]     # zero IS 10.01 > naive 10 -> skill -0.001
    cl_eq = [[10, 5.0, 10.0, 8, 8, 10.0]]
    check("zero_move_check fires at +0.001, not at 0 or -0.001 (threshold pinned at the call site)",
          H.zero_move_check(cl_pos)[1] is True and H.zero_move_check(cl_neg)[1] is False and H.zero_move_check(cl_eq)[1] is False,
          str((H.zero_move_check(cl_pos), H.zero_move_check(cl_neg), H.zero_move_check(cl_eq))))
    res4, _ = run_dir(end="2026-11-27", asof="2026-11-28")
    e_day = res4["cells"]["EURUSD"]["horizons"]["day/all_rows"]
    e_mon = res4["cells"]["EURUSD"]["horizons"]["month/all_rows"]
    check("10 mature clusters: statistics present with keep-rule conditions", e_day["clusters"] == 10 and e_day["counts_only"] is False
          and "range_skill_ci95" in e_day and set(e_day["keep_rule_conditions"]) == {"range_skill_ge_0.10", "coverage_ci_overlaps_0.75_0.85", "n_ge_30", "clusters_ge_10"}, str(e_day))
    check("9 mature clusters: counts only", e_mon["clusters"] == 9 and e_mon["counts_only"] is True and "range_skill_v2_vs_naive" not in e_mon, str(e_mon))
    # keep rule conditions
    s = {"range_skill_v2_vs_naive": 0.10, "coverage_v2_ci95": [0.85, 0.9], "n": 30, "clusters": 10}
    check("keep boundaries inclusive: skill 0.10, cov CI edge 0.85, n 30, clusters 10", H.keep_block(s)["all_met"])
    for k, v in (("range_skill_v2_vs_naive", 0.0999), ("coverage_v2_ci95", [0.851, 0.9]), ("n", 29), ("clusters", 9)):
        check("keep fails when %s just misses" % k, not H.keep_block(dict(s, **{k: v}))["all_met"])
    check("coverage CI below the band edge: overlap at 0.75 is inclusive", H.keep_block(dict(s, coverage_v2_ci95=[0.6, 0.75]))["conditions"]["coverage_ci_overlaps_0.75_0.85"])


if __name__ == "__main__":
    test_all()
    print("test_score_fx_holdout: %d passed, %d failed" % (PASS, FAIL))
    sys.exit(1 if FAIL else 0)
