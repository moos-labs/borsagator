#!/usr/bin/env python3
"""Tests for benchmarks/replay_aci_conformal.py (INS-IMPROVE-006 B).
Standalone, stdlib only.
"""
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


sys.path.insert(0, os.path.join(ROOT, "benchmarks"))
sys.path.insert(0, HERE)
spec = importlib.util.spec_from_file_location(
    "aci", os.path.join(ROOT, "benchmarks", "replay_aci_conformal.py"))
C = importlib.util.module_from_spec(spec)
sys.modules["aci"] = C
spec.loader.exec_module(C)


def row(real, a, t="A", h="week", cell=1, sig=0.02):
    return {"ticker": t, "as_of": a, "horizon": h, "real": real,
            "naive_half": 5.0, "mult": 1.0, "v2_sigma": sig,
            "cell": cell}


def half(h="week", sig=0.02):
    return C.R.half_pct(sig, h, C.ens_mod.V2_BAND_K[h], 1.0)


def test_constants():
    check("v2 pinned", C.ens_mod.V2_BAND_K == {
        "day": 1.15, "week": 1.28, "month": 1.20})
    check("params", (C.ALPHA, C.GAMMA, C.MATURITY_DAYS, C.MIN_HIST)
          == (0.20, 0.05, 35, 12))
    check("clean cells", C.CLEAN_MIN_CELL == 91)


def test_quantile():
    check("short history is v2", C.conformal_q([5.0] * 5, 0.2) == 1.0)
    sc = [i / 20.0 for i in range(1, 21)]
    q = C.conformal_q(sc, 0.2)
    check("conformal index", abs(q - 0.85) < 1e-9, q)
    check("cap at max", C.conformal_q(sc, 0.001) == 1.0)


def test_score():
    r = row(half() * 0.5, "2025-01-01")
    check("score is ratio", abs(C.score_of(r) - 0.5) < 1e-9)


def test_no_lookahead():
    hist = [row(half() * 0.5, "2025-01-0%d" % (i + 1), t="T%d" % i)
            for i in range(9)]
    hist += [row(half() * 0.5, "2025-02-01", t="T%d" % i)
             for i in range(9)]
    # target 2025-02-20 is only 19 days after 2025-02-01: not eligible
    q_early, _ = C.q_for("2025-02-20", hist)
    check("maturity guard keeps q at v2 with <12 eligible",
          q_early == 1.0, q_early)
    q_late, _ = C.q_for("2025-04-01", hist)
    check("matured history applies", abs(q_late - 0.5) < 1e-9, q_late)
    future = hist + [row(half() * 9.0, "2025-06-01", t="Z")]
    q2, _ = C.q_for("2025-04-01", future)
    check("later rows never leak", abs(q2 - q_late) < 1e-12)


def test_alpha_moves():
    hist = []
    for k, a in enumerate(("2025-01-01", "2025-03-01", "2025-05-01")):
        hist += [row(half() * 3.0, a, t="T%d" % i) for i in range(12)]
    _q, alpha = C.q_for("2025-09-01", hist)
    check("misses lower alpha level", alpha < C.ALPHA, alpha)
    check("alpha clipped", C.ALPHA_MIN <= alpha <= C.ALPHA_MAX)


def test_score_rows():
    hist = [row(half() * 0.5, "2025-01-0%d" % (i + 1), t="T%d" % i,
                cell=1) for i in range(9)]
    hist += [row(half() * 0.5, "2025-02-01", t="T%d" % i, cell=1)
             for i in range(9)]
    tgt = [row(half() * 0.7, "2025-06-01", t="X", cell=95)]
    pairs = C.score_rows(hist + tgt, lambda r: r["cell"] >= 91)
    check("only target scored", len(pairs) == 1)
    p = pairs[0]
    check("narrowed band misses the 0.7 move", not p["in_ch"]
          and p["in_v2"])


def test_refusal():
    rc = C.main(["score", "--captures", "/nonexistent", "--min-cell", "73"])
    check("refuses seen cells", rc == 2)


def test_unnumbered_and_json():
    import contextlib
    import io
    import json
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        cap = os.path.join(d, "2025-11-14", "TST")
        os.makedirs(os.path.join(cap, "digest"))
        for fn in ("manifest.json", "realised.json"):
            open(os.path.join(cap, fn), "w").write("{}")
        open(os.path.join(cap, "digest", "ensemble.json"), "w").write("{}")
        out = os.path.join(d, "o.json")
        buf = io.StringIO()
        check("unnumbered capture is findable by find_captures",
              C.A.find_captures([d], 48) != [])
        with contextlib.redirect_stdout(buf):
            rc = C.main(["score", "--captures", d, "--min-cell", "48",
                         "--descriptive", "--reps", "50", "--json", out])
        data = json.load(open(out))
        check("descriptive run exits 0", rc == 0)
        check("unnumbered capture dropped from scoring",
              all(data["results"][h]["n"] == 0 for h in ("day", "week", "month")))
        check("descriptive json carries no verdict",
              "verdict" not in data and data["descriptive"] is True)
        with contextlib.redirect_stdout(buf):
            C.main(["score", "--captures", d, "--reps", "50",
                    "--json", out])
        check("clean json carries a verdict",
              "verdict" in json.load(open(out)))


def main():
    for fn in (test_constants, test_quantile, test_score,
               test_no_lookahead, test_alpha_moves, test_score_rows,
               test_refusal, test_unnumbered_and_json):
        fn()
    print("test_aci_conformal: %d passed, %d failed"
          % (CHECKS["pass"], CHECKS["fail"]))
    sys.exit(1 if CHECKS["fail"] else 0)


if __name__ == "__main__":
    main()
