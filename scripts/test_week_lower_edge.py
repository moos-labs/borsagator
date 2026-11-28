import contextlib, io, json, os, sys, tempfile, unittest
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "benchmarks"))
import score_week_lower_edge as W  # noqa: E402

CHECKS = {"pass": 0, "fail": 0}


def check(name, ok, detail=""):
    CHECKS["pass" if ok else "fail"] += 1
    if not ok:
        print("FAIL", name, detail)


def mk(real=0.5, q=(-1.0, 1.0), half=2.0, rdate="2025-01-01", h="week", base="2024-12-01", tk="A"):
    return {"ticker": tk, "base": base, "as_of": base, "horizon": h, "real": real, "naive_half": 3.0,
            "mult": 1.0, "half": half, "q_lo": q[0], "q_hi": q[1], "rdate": rdate,
            "key": "%s %s %s" % (tk, base, h)}


def test_fit():
    ok = [mk() for _ in range(100)]
    n, ex, a = W.fit_a(ok)
    check("100 pooled covered fits", n == 100 and a is not None and not ex)
    n, ex, a = W.fit_a(ok[:99])
    check("99 pooled covered does not fit", n == 99 and a is None)
    mixed = [mk(h="day") for _ in range(40)] + [mk(h="week") for _ in range(30)] + [mk(h="month") for _ in range(30)]
    n, ex, a = W.fit_a(mixed)
    check("all horizons pooled into the count", n == 100 and a is not None)
    n, ex, a = W.fit_a(ok[:99] + [mk(rdate="2025-08-15")])
    check("freeze date itself excluded and listed", n == 99 and a is None and len(ex) == 1)
    # identical edges: every a ties -> larger a
    tie = [mk(real=0.0, q=(-2.0, 2.0), half=2.0) for _ in range(100)]
    check("ties go to the larger a", W.fit_a(tie)[2] == 1.0)
    # real always 0, tight baseline: a = 0 best
    tight = [mk(real=0.0, q=(-0.5, 0.5), half=2.0) for _ in range(100)]
    check("tight baseline lower edge gives a = 0", W.fit_a(tight)[2] == 0.0)
    check("b is fixed at 1: upper edge is the v2 edge", W.T.mix_edges(2.0, -1.0, 1.0, 0.3, 1.0)[1] == 2.0)


def test_maturity():
    caps = ["/x/c1/2026-01-01/A.CA", "/x/c1/2026-01-01/B.CA", "/x/c2/2026-02-01/A.CA", "/x/c2/2026-02-01/B.CA"]
    rows = [mk(base="2026-01-01", tk="A.CA"), mk(base="2026-01-01", tk="B.CA"), mk(base="2026-02-01", tk="A.CA")]
    mature, allc = W.mature_clusters(caps, rows)
    check("a cluster missing one intended row is not mature", mature == {"2026-01-01"} and allc == {"2026-01-01", "2026-02-01"}, str(mature))
    rows.append(mk(base="2026-02-01", tk="B.CA"))
    check("complete cluster counts", W.mature_clusters(caps, rows)[0] == {"2026-01-01", "2026-02-01"})


def test_score_counts_only_below_ten():
    saved = (W.load, )
    caps = ["/x/c/2026-0%d-01/A.CA" % i for i in range(1, 4)]
    rows = [mk(base="2026-0%d-01" % i, tk="A.CA") for i in range(1, 4)]
    W.load = lambda roots, lo, hi, d: (caps, rows, [])
    with tempfile.TemporaryDirectory() as d:
        af = os.path.join(d, "a.json")
        json.dump({"a": 0.1}, open(af, "w"))
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                rc = W.main(["score", "--captures", "x", "--ohlcv-dir", d, "--a-file", af])
        finally:
            W.load = saved[0]
    out = buf.getvalue()
    check("score with 3 mature clusters is counts only, no statistic", rc == 0 and "COUNTS ONLY: 3 fully mature clusters < 10" in out and "RangeSkill" not in out and "KEEP RULE" not in out, out)
    check("day and month are marked not KEEP-eligible", out.count("not KEEP-eligible") == 2)


def test_refusals():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        r1 = W.main(["fit", "--captures", "x", "--ohlcv-dir", "x", "--reps", "10"])
        r2 = W.main(["fit", "--captures", "x", "--ohlcv-dir", "x", "--seed", "3"])
    check("reps and seed refused", r1 == 2 and r2 == 2)


def run_all():
    for fn in (test_fit, test_maturity, test_score_counts_only_below_ten, test_refusals):
        fn()


class Suite(unittest.TestCase):
    def test_checks(self):
        run_all()
        self.assertEqual(CHECKS["fail"], 0)


if __name__ == "__main__":
    run_all()
    print("test_week_lower_edge: %d passed, %d failed" % (CHECKS["pass"], CHECKS["fail"]))
    sys.exit(1 if CHECKS["fail"] else 0)
