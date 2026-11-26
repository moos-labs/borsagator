#!/usr/bin/env python3
"""Fixed synthetic checks for benchmarks/ci_audit.py."""
import importlib.util
import os
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CHECKS = {"pass": 0, "fail": 0}


def check(name, ok, detail=""):
    CHECKS["pass" if ok else "fail"] += 1
    if not ok:
        print("FAIL %s %s" % (name, detail))


def load():
    sys.path.insert(0, os.path.join(ROOT, "benchmarks"))
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    spec = importlib.util.spec_from_file_location(
        "ci_audit", os.path.join(ROOT, "benchmarks", "ci_audit.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


C = load()


def pr(as_of, naive, band, h="week", t="A"):
    return {"ticker": t, "as_of": as_of, "horizon": h, "in_ch": True,
            "is_naive": naive, "is_v2": band, "is_ch": band}


def uniform(k, naive=2.0, band=1.0):
    return [pr("c%02d" % i, naive, band) for i in range(k)]


def test_clusters_and_skill():
    cl = C.clusters(uniform(4), "v2")
    check("one cluster per as_of", len(cl) == 4)
    check("D and N per cluster", cl[0] == (1.0, 2.0), cl[0])
    check("skill = 1 - IS_band / IS_naive", abs(C.skill(cl) - 0.5) < 1e-12)
    check("empty gives None", C.skill([]) is None)


def test_existing_matches_boot():
    ps = []
    for i in range(8):
        ps.append(pr("c%d" % i, 2.0 + i % 3, 1.0 + (i % 2) * 1.5))
        ps.append(pr("c%d" % i, 1.0, 1.2, t="B"))
    cl = C.clusters(ps, "v2")
    got = C.existing_ci(cl, 400, 7)
    sk, _cov = C.R._boot(ps, "as_of", 400, 7)
    want = C.A.percentile_ci(sk)
    check("same draws as the keep rule's bootstrap",
          all(abs(a - b) < 1e-12 for a, b in zip(got, want)), (got, want))


def test_signflip_exact():
    cl = C.clusters(uniform(10), "v2")
    p, mode = C.signflip_p(cl, 1)
    check("all clusters positive: only the observed flip reaches it",
          mode == "exact" and abs(p - 1 / 1024.0) < 1e-12, (p, mode))
    check("passes at 0.025", p < 0.025)
    cl0 = C.clusters([pr("a", 2.0, 3.0), pr("b", 2.0, 1.0)], "v2")
    p0, _ = C.signflip_p(cl0, 1)
    check("symmetric +/- clusters: p = 1", abs(p0 - 1.0) < 1e-12
          or abs(p0 - 0.75) < 1e-12, p0)
    big = C.clusters(uniform(20), "v2")
    pm, mm = C.signflip_p(big, 3)
    check("more than 16 clusters uses Monte Carlo", mm == "monte-carlo"
          and pm < 0.001, (pm, mm))


def test_jackknife_and_wild():
    cl = C.clusters(uniform(6), "v2")
    jl, jh, mn, mx = C.jackknife_ci(cl)
    check("identical clusters: zero jackknife width",
          abs(jl - 0.5) < 1e-9 and abs(jh - 0.5) < 1e-9
          and abs(mn - mx) < 1e-12)
    wl, wh = C.wild_ci(cl, 300, 5)
    check("zero residuals: wild interval is the estimate",
          abs(wl - 0.5) < 1e-9 and abs(wh - 0.5) < 1e-9)
    mixed = C.clusters([pr("c%d" % i, 2.0, 1.0 if i % 2 else 3.0)
                        for i in range(8)], "v2")
    wl, wh = C.wild_ci(mixed, 500, 5)
    check("mixed clusters: wild interval brackets the estimate",
          wl < C.skill(mixed) < wh, (wl, wh))
    jl, jh, _a, _b = C.jackknife_ci(mixed)
    check("mixed clusters: jackknife interval brackets the estimate",
          jl < C.skill(mixed) < jh)


def test_audit_pairs():
    strong = []
    for h in C.HORIZONS:
        strong += [pr("c%02d" % i, 2.0, 1.0, h=h) for i in range(12)]
    res = C.audit_pairs(strong, "v2", reps=300, seed=1)
    c = res["day"]
    check("clear skill: every method passes, no change",
          c["existing"]["pass"] and c["jackknife"]["pass"]
          and c["signflip"]["pass"] and c["wild"]["pass"]
          and c["verdict_would_change_under"] == [], c)
    weak = []
    for h in C.HORIZONS:
        weak += [pr("c%02d" % i, 2.0, 2.0, h=h) for i in range(12)]
    res = C.audit_pairs(weak, "v2", reps=300, seed=1)
    c = res["week"]
    check("zero skill: no method passes",
          not (c["existing"]["pass"] or c["jackknife"]["pass"]
               or c["signflip"]["pass"] or c["wild"]["pass"]), c)


def test_main_empty():
    import contextlib
    import io
    import json
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "o.json")
        with contextlib.redirect_stdout(io.StringIO()):
            rc = C.main(["--captures", d, "--reps", "50", "--json", out])
        data = json.load(open(out))
        check("empty dir runs", rc == 0)
        check("descriptive, no verdict key",
              data["descriptive"] is True and "verdict" not in data)


def main():
    for fn in (test_clusters_and_skill, test_existing_matches_boot,
               test_signflip_exact, test_jackknife_and_wild,
               test_audit_pairs, test_main_empty):
        fn()
    print("test_ci_audit: %d passed, %d failed"
          % (CHECKS["pass"], CHECKS["fail"]))
    sys.exit(1 if CHECKS["fail"] else 0)


if __name__ == "__main__":
    main()
