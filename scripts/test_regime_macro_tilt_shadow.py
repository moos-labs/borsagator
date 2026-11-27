"""Tests for benchmarks/regime_macro_tilt_shadow.py: fixed synthetic inputs."""
import csv
import importlib.util
import os
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "regime_macro_tilt_shadow", os.path.join(HERE, "..", "benchmarks", "regime_macro_tilt_shadow.py"))
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)
CHECKS = {"pass": 0, "fail": 0}


def check(name, ok, detail=""):
    if ok:
        CHECKS["pass"] += 1
    else:
        CHECKS["fail"] += 1
        print("FAIL", name, detail)


def write_csv(rows):
    f = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, newline="")
    w = csv.DictWriter(f, fieldnames=list(R.REQUIRED))
    w.writeheader()
    for r in rows:
        w.writerow(r)
    f.close()
    return f.name


GOOD = {"value": "20.0", "observed_date": "2026-10-29", "published_date": "2026-10-29",
        "source_url": "https://example.test/x", "source_name": "t"}


def test_load_rows():
    bad = [dict(GOOD, **{k: ""}) for k in R.REQUIRED]
    p = write_csv([GOOD] + bad + [dict(GOOD, value="abc"), dict(GOOD, value="nan"), dict(GOOD, value="inf")])
    rows, rej = R.load_rows(p)
    os.remove(p)
    check("one good row kept", len(rows) == 1 and rows[0]["value"] == 20.0, rows)
    check("each missing field rejected, bad values rejected", rej == len(R.REQUIRED) + 3, rej)


def test_point_in_time():
    rows = [{"value": 1.0, "observed_date": "2026-01-01", "published_date": "2026-01-10"},
            {"value": 2.0, "observed_date": "2026-02-01", "published_date": "2026-02-10"}]
    check("before first publication", R.point_in_time(rows, "2026-01-09") is None)
    check("published same day usable", R.point_in_time(rows, "2026-01-10")["value"] == 1.0)
    check("second not yet published", R.point_in_time(rows, "2026-02-09")["value"] == 1.0)
    check("second published", R.point_in_time(rows, "2026-02-10")["value"] == 2.0)


def test_regime():
    d = [{"published_date": "2026-02-12", "change_bps": -100}, {"published_date": "2026-05-21", "change_bps": 0},
         {"published_date": "2026-10-29", "change_bps": 100}]
    check("none before first", R.regime_from_decisions(d, "2026-02-11") is None)
    check("easing on the day", R.regime_from_decisions(d, "2026-02-12") == "easing")
    check("hold", R.regime_from_decisions(d, "2026-05-21") == "hold")
    check("tightening", R.regime_from_decisions(d, "2026-11-12") == "tightening")
    check("day before tightening still hold", R.regime_from_decisions(d, "2026-10-28") == "hold")
    check("unordered input", R.regime_from_decisions(list(reversed(d)), "2026-11-12") == "tightening")


def test_counts():
    d = [{"published_date": "2026-10-29", "change_bps": 100}]
    led = [{"as_of": "2026-10-28", "horizon": "day"}, {"as_of": "2026-11-12", "horizon": "day"},
           {"as_of": "2026-11-12", "horizon": "week"}, {"as_of": "2026-11-13", "horizon": "day"}]
    c = R.counts(led, d)
    check("totals", c["n_captures"] == 4 and c["n_with_regime"] == 3 and c["n_without_regime"] == 1, c)
    cell = c["by_regime_horizon"]["tightening|day"]
    check("day cell rows and dates", cell["n"] == 2 and cell["n_cutoff_dates"] == 2, cell)
    check("week cell", c["by_regime_horizon"]["tightening|week"] == {"n": 1, "n_cutoff_dates": 1})
    check("no macro series -> no regime", R.counts(led, [])["n_with_regime"] == 0)
    check("no verdict keys", not any(w in repr(c) for w in ("verdict", "keep", "p_value")))


def run_all():
    for fn in (test_load_rows, test_point_in_time, test_regime, test_counts):
        fn()


class Suite(unittest.TestCase):
    def test_checks(self):
        CHECKS["pass"] = CHECKS["fail"] = 0
        run_all()
        self.assertEqual(CHECKS["fail"], 0)
        self.assertGreater(CHECKS["pass"], 0)


def main():
    run_all()
    print("test_regime_macro_tilt_shadow: %d passed, %d failed" % (CHECKS["pass"], CHECKS["fail"]))
    sys.exit(1 if CHECKS["fail"] else 0)


if __name__ == "__main__":
    main()
