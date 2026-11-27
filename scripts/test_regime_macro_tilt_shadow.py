"""Tests for benchmarks/regime_macro_tilt_shadow.py: fixed synthetic inputs."""
import csv
import json
import importlib.util
import os
import sys
import subprocess
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


SRC = {"source_url": "https://example.test/mpc", "source_name": "t"}


def dec(date, bps, **kw):
    d = {"published_date": date, "change_bps": bps}
    d.update(SRC)
    d.update(kw)
    return d


def test_regime():
    d = [dec("2026-02-12", -100), dec("2026-05-21", 0), dec("2026-10-29", 100)]
    check("none before first", R.regime_from_decisions(d, "2026-02-11") is None)
    check("same day NOT eligible (date-only decision)", R.regime_from_decisions(d, "2026-02-12") is None)
    check("next day eligible: easing", R.regime_from_decisions(d, "2026-02-13") == "easing")
    check("hold", R.regime_from_decisions(d, "2026-05-22") == "hold")
    check("tightening", R.regime_from_decisions(d, "2026-11-12") == "tightening")
    check("tightening day-of still hold", R.regime_from_decisions(d, "2026-10-29") == "hold")
    check("unordered input", R.regime_from_decisions(list(reversed(d)), "2026-11-12") == "tightening")


def test_unusable_decisions():
    inf, nan = float("inf"), float("nan")
    for name, bad in (("nan", dec("2026-01-01", nan)), ("inf", dec("2026-01-01", inf)), ("-inf", dec("2026-01-01", -inf)),
                      ("string", dec("2026-01-01", "100")), ("none", dec("2026-01-01", None)), ("bool", dec("2026-01-01", True)),
                      ("no url", dec("2026-01-01", 100, source_url="")), ("no name", dec("2026-01-01", 100, source_name=" ")),
                      ("missing url", {"published_date": "2026-01-01", "change_bps": 100, "source_name": "t"}),
                      ("no date", dec("", 100))):
        check("unusable: " + name, not R.usable_decision(bad), bad)
        check("not a regime: " + name, R.regime_from_decisions([bad], "2026-06-01") is None, name)
    for name, bd in (("feb 30", "2026-02-30"), ("month 13", "2026-13-01"), ("not zero padded", "2026-2-3"), ("slashes", "2026/02/03"),
                     ("time suffix", "2026-02-03T00:00"), ("spaces", " 2026-02-03"), ("year 2 digits", "26-02-03"),
                     ("non-leap feb 29", "2025-02-29"), ("text", "tomorrow"), ("compact", "20260203"), ("iso week", "2026-W05-3")):
        check("invalid date unusable: " + name, not R.usable_decision(dec(bd, 100)), bd)
    check("leap day usable", R.usable_decision(dec("2024-02-29", 100)))
    check("non-string date unusable", not R.usable_decision(dec(20260203, 100)))
    check("good is usable", R.usable_decision(dec("2026-01-01", 0)) and R.usable_decision(dec("2026-01-01", 12.5)))
    # an unusable later decision does not mask the earlier usable one
    check("bad later decision ignored", R.regime_from_decisions([dec("2026-01-01", 100), dec("2026-02-01", float("nan"))], "2026-06-01") == "tightening")
    p = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    json.dump([dec("2026-01-01", 100), dec("2026-02-01", None), {"published_date": "2026-03-01", "change_bps": 0},
               dec("2026-02-30", 100)], p)
    p.close()
    ok, rej = R.load_decisions(p.name)
    os.remove(p.name)
    check("load_decisions counts rejected (incl. 2026-02-30)", len(ok) == 1 and rej == 3, (ok, rej))
    h = subprocess.run([sys.executable, os.path.join(HERE, "..", "benchmarks", "regime_macro_tilt_shadow.py"), "--help"], capture_output=True, text=True).stdout
    check("help documents all four fields", all(k in h for k in ("published_date", "change_bps", "source_url", "source_name")), h)


def test_counts():
    d = [dec("2026-10-29", 100)]
    led = [{"as_of": "2026-10-28", "horizon": "day"}, {"as_of": "2026-10-29", "horizon": "day"},
           {"as_of": "2026-11-12", "horizon": "day"}, {"as_of": "2026-11-12", "horizon": "week"},
           {"as_of": "2026-11-13", "horizon": "day"}]
    c = R.counts(led, d)
    check("totals (same-day row has no regime)", c["n_captures"] == 5 and c["n_with_regime"] == 3 and c["n_without_regime"] == 2, c)
    cell = c["by_regime_horizon"]["tightening|day"]
    check("day cell rows and dates", cell["n"] == 2 and cell["n_cutoff_dates"] == 2, cell)
    check("week cell", c["by_regime_horizon"]["tightening|week"] == {"n": 1, "n_cutoff_dates": 1})
    check("no macro series -> no regime", R.counts(led, [])["n_with_regime"] == 0)
    check("no verdict keys", not any(w in repr(c) for w in ("verdict", "keep", "p_value")))

PINNED_SERIES = [
    ("2022-03-21", 100), ("2022-05-19", 200), ("2022-06-23", 0), ("2022-08-18", 0), ("2022-09-22", 0), ("2022-10-27", 200),
    ("2022-12-22", 300), ("2023-02-02", 0), ("2023-03-30", 200), ("2023-05-18", 0), ("2023-06-22", 0), ("2023-08-03", 100),
    ("2023-09-21", 0), ("2023-11-02", 0), ("2023-12-21", 0), ("2024-02-01", 200), ("2024-03-06", 600), ("2024-05-23", 0),
    ("2024-07-18", 0), ("2024-09-05", 0), ("2024-10-17", 0), ("2024-11-21", 0), ("2024-12-26", 0), ("2025-02-20", 0),
    ("2025-04-17", -225), ("2025-05-22", -100), ("2025-07-10", 0), ("2025-08-28", -200), ("2025-10-02", -100),
    ("2025-11-20", 0), ("2025-12-25", -100), ("2026-02-12", -100), ("2026-04-02", 0), ("2026-05-21", 0), ("2026-07-09", 0),
    ("2026-08-20", 0), ("2026-09-24", 0), ("2026-10-29", 100)]


def test_collected_series():
    """Pins the committed CBE decision series (a data file, read as-is): 2022-08-18 and 2023-02-02 holds are present,
    the other 36 rows are unchanged, and only Feb 2023 changes a regime classification (tightening -> hold)."""
    path = os.path.join(HERE, "..", "evaluation", "macro_series", "cbe_decisions.json")
    ok, rej = R.load_decisions(path)
    check("series: all usable, none rejected", rej == 0 and len(ok) == 38, (len(ok), rej))
    check("series: exact dates and bps, chronological", [(d["published_date"], d["change_bps"]) for d in ok] == PINNED_SERIES)
    check("series: Feb 2023 date -> hold", R.regime_from_decisions(ok, "2023-02-03") == "hold" and R.regime_from_decisions(ok, "2023-03-30") == "hold")
    check("series: after 2023-03-30 -> tightening", R.regime_from_decisions(ok, "2023-03-31") == "tightening")
    check("series: 2023-02-02 day-of still tightening (date-only)", R.regime_from_decisions(ok, "2023-02-02") == "tightening")
    check("series: Aug 2022 hold date", R.regime_from_decisions(ok, "2022-08-19") == "hold")
    without = [d for d in ok if d["published_date"] != "2023-02-02"]
    check("series: without the Feb 2023 row the gap is tightening (the defect)", R.regime_from_decisions(without, "2023-03-01") == "tightening")
    check("series: Aug 18 is a completeness fix, no regime change", R.regime_from_decisions([d for d in ok if d["published_date"] != "2022-08-18"], "2022-09-01") == R.regime_from_decisions(ok, "2022-09-01") == "hold")
    check("series: sources present", all(d["source_url"].startswith("https://") and d["source_name"] for d in ok))


def run_all():
    for fn in (test_load_rows, test_point_in_time, test_regime, test_unusable_decisions, test_counts, test_collected_series):
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
