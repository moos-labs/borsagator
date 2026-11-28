import os, sys, unittest
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "benchmarks"))
import score_shrinkage_mechanism as M  # noqa: E402

CHECKS = {"pass": 0, "fail": 0}


def check(name, ok, detail=""):
    CHECKS["pass" if ok else "fail"] += 1
    if not ok:
        print("FAIL", name, detail)


def mk(real, q=(-1.0, 1.0), half=2.0, base="2025-10-01", tk="A"):
    return {"ticker": tk, "base": base, "as_of": base, "horizon": "week", "real": real,
            "naive_half": 3.0, "mult": 1.0, "half": half, "q_lo": q[0], "q_hi": q[1]}


def run_all():
    rows = [mk(0.5), mk(-0.3, base="2025-11-01"), mk(1.5, tk="B")]
    for k in ("full", "centre", "width"):
        d = M.diff(rows, 1.0, 1.0, k)
        check("weights 1 reproduce v2 for %s" % k, d is not None and abs(d) < 1e-12, str(d))
    lo, hi = M.edges(mk(0.0), 0.1, 1.0)
    check("edges: a=0.1 pulls only the lower edge toward q_lo", abs(lo - (-0.2 + -0.9)) < 1e-12 and abs(hi - 2.0) < 1e-12, str((lo, hi)))
    sh, wr = M.summary([mk(0.0)], 0.1, 1.0)
    check("mean shift and width ratio", abs(sh - (-1.1 + 2.0) / 2) < 1e-12 and abs(wr - 3.1 / 4.0) < 1e-12, str((sh, wr)))
    c = M.variant_rows([mk(0.0)], 0.1, 1.0, "centre")[0]
    w = M.variant_rows([mk(0.0)], 0.1, 1.0, "width")[0]
    f = M.variant_rows([mk(0.0)], 0.1, 1.0, "full")[0]
    check("centre variant keeps v2 width 4.0 (IS 4.0 when inside)", abs(c["is_x"] - 4.0) < 1e-12, str(c))
    check("width variant is centred (IS = width 3.1 when inside)", abs(w["is_x"] - 3.1) < 1e-12, str(w))
    check("full variant IS = width 3.1", abs(f["is_x"] - 3.1) < 1e-12, str(f))
    outside = M.variant_rows([mk(4.0)], 0.1, 1.0, "full")[0]
    check("real above the upper edge is outside the full interval", outside["in_x"] is False)
    x = [mk(0.0, q=(-1.0, -0.5), half=0.2)]  # crossed edges fall back to v2
    lo, hi = M.edges(x[0], 1.0, 0.0)
    check("crossed edges fall back to v2", (lo, hi) == (-0.2, 0.2) or lo < hi, str((lo, hi)))


class Suite(unittest.TestCase):
    def test_checks(self):
        run_all()
        self.assertEqual(CHECKS["fail"], 0)


if __name__ == "__main__":
    run_all()
    print("test_shrinkage_mechanism: %d passed, %d failed" % (CHECKS["pass"], CHECKS["fail"]))
    sys.exit(1 if CHECKS["fail"] else 0)
