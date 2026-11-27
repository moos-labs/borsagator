"""Tests for benchmarks/disclosure_pit_check.py: fixed synthetic inputs."""
import importlib.util
import os
import sys
import unittest

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "disclosure_pit_check", os.path.join(HERE, "..", "benchmarks", "disclosure_pit_check.py"))
P = importlib.util.module_from_spec(spec)
spec.loader.exec_module(P)
CHECKS = {"pass": 0, "fail": 0}


def check(name, ok, detail=""):
    CHECKS["pass" if ok else "fail"] += 1
    if not ok:
        print("FAIL: %s %s" % (name, detail))


def test_all():
    C = "2025-01-02"  # Thursday; week window ends Thursday 2025-01-09
    check("window end week", str(P.window_end(C, 5)) == "2025-01-09")
    check("flags inside window", P.classify("2024-12-30", "2025-01-08", C, "week") == (True, "flags"))
    check("forward on window end flags", P.classify("2024-12-30", "2025-01-09", C, "week")[0])
    check("forward after window end does not", not P.classify("2024-12-30", "2025-01-10", C, "week")[0])
    check("forward on cutoff day does not", not P.classify("2024-12-30", C, C, "week")[0])
    check("announced day before cutoff is usable", P.classify("2025-01-01", "2025-01-08", C, "week")[0])
    check("announced on cutoff day is not usable", P.classify("2025-01-02", "2025-01-08", C, "week")[0] is False)
    check("announced after cutoff is not usable", not P.classify("2025-01-03", "2025-01-08", C, "week")[0])
    check("candidate never flags", P.classify("2024-12-30", "2025-01-08", C, "week", verified=False) == (False, "not verified"))
    check("stale never flags", P.classify("2024-12-30", "2025-01-08", C, "week", stale=True) == (False, "stale"))
    check("missing announced", P.classify(None, "2025-01-08", C, "week") == (False, "missing announced"))
    check("missing forward", P.classify("2024-12-30", None, C, "week") == (False, "missing forward date"))
    check("day horizon is one session", P.classify("2024-12-30", "2025-01-05", C, "day")[0]
          and not P.classify("2024-12-30", "2025-01-06", C, "day")[0])
    check("month horizon is 21 sessions", P.classify("2024-12-01", "2025-02-02", C, "month")[0] and not P.classify("2024-12-01", "2025-02-03", C, "month")[0])
    check("time part ignored", P.classify("2024-12-30T23:59:00", "2025-01-08T00:00:00", C + "T09:00:00", "week")[0])


def run_all():
    test_all()


class Suite(unittest.TestCase):
    def test_checks(self):
        CHECKS["pass"] = CHECKS["fail"] = 0
        run_all()
        self.assertEqual(CHECKS["fail"], 0)
        self.assertGreater(CHECKS["pass"], 0)


def main():
    CHECKS["pass"] = CHECKS["fail"] = 0
    run_all()
    print("test_disclosure_pit_check: %d passed, %d failed" % (CHECKS["pass"], CHECKS["fail"]))
    return 1 if CHECKS["fail"] else 0


if __name__ == "__main__":
    sys.exit(main())
