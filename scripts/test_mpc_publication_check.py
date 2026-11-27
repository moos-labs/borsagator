"""Tests for benchmarks/mpc_publication_check.py: fixed synthetic inputs."""
import importlib.util
import json
import os
import sys
import unittest

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "mpc_publication_check", os.path.join(HERE, "..", "benchmarks", "mpc_publication_check.py"))
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)
CHECKS = {"pass": 0, "fail": 0}


def check(name, ok, detail=""):
    CHECKS["pass" if ok else "fail"] += 1
    if not ok:
        print("FAIL: %s %s" % (name, detail))


PUB = {"years": {"2030": {"dates": ["2030-02-07", "2030-03-28"], "first_public_on_or_before": "2029-12-20"}},
       "cancelled": [{"date": "2030-03-28", "announced": "2030-03-20"}],
       "special": [{"date": "2030-03-06", "announced": "2030-03-06"}]}


def test_known_dates():
    check("not known on the publication day", M.known_dates("2029-12-20", PUB) == set())
    check("known the day after", M.known_dates("2029-12-21", PUB) == {"2030-02-07", "2030-03-28"})
    check("cancelled date removed after announcement day", "2030-03-28" not in M.known_dates("2030-03-21", PUB))
    check("cancelled date still known on announcement day", "2030-03-28" in M.known_dates("2030-03-20", PUB))
    check("special not known on its own day", "2030-03-06" not in M.known_dates("2030-03-06", PUB))
    check("special known the day after", "2030-03-06" in M.known_dates("2030-03-07", PUB))


def test_flags_and_compare():
    check("window end week", str(M.window_end("2025-01-02", 5)) == "2025-01-09")
    check("flag inside", M.flag("2025-01-02", "week", ["2025-01-09"]))
    check("flag on cutoff day excluded", not M.flag("2025-01-09", "week", ["2025-01-09"]))
    check("flag after window end excluded", not M.flag("2025-01-02", "week", ["2025-01-10"]))
    rows = M.compare(["2030-02-01"], ["2030-02-07"], PUB)
    mo = [r for r in rows if r["horizon"] == "month"][0]
    check("known schedule, same flag", mo["series_flag"] and mo["published_flag"] and not mo["changes"])
    rows = M.compare(["2029-12-15"], ["2030-01-10"], PUB)
    mo = [r for r in rows if r["horizon"] == "month"][0]
    check("series flag but date not yet public changes", mo["series_flag"] and not mo["published_flag"] and mo["changes"])
    check("three horizons per cutoff", len(rows) == 3)


def test_discover():
    fake = ["/x/backtest/2024-06-30/ABC.CA-cell5", "/x/backtest/2024-07-31/DEF.CA", "/x/a/2024-08-31/GH-cell7"]
    find = lambda roots, mc: fake
    cell = lambda p: 1 if "cell" in p else None
    check("only numbered cells give cutoffs", M.discover_cutoffs(["x"], find, cell) == ["2024-06-30", "2024-08-31"])
    check("cutoff_of picks the date part", M.cutoff_of("/a/2025-01-02/T") == "2025-01-02" and M.cutoff_of("/a/b") is None)


def test_shipped_json():
    pub = json.load(open(M.PUB))
    for y, v in pub["years"].items():
        check("year %s has 8 dates in that year" % y, len(v["dates"]) == 8 and all(d.startswith(y) for d in v["dates"]))
        check("year %s publication before first date" % y, v["first_public_on_or_before"] < v["dates"][0])
    check("cancelled and special listed", pub["cancelled"][0]["date"] == "2024-03-28" and pub["special"][0]["date"] == "2024-03-06")


def run_all():
    for fn in (test_known_dates, test_flags_and_compare, test_discover, test_shipped_json):
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
    print("test_mpc_publication_check: %d passed, %d failed" % (CHECKS["pass"], CHECKS["fail"]))
    return 1 if CHECKS["fail"] else 0


if __name__ == "__main__":
    sys.exit(main())
