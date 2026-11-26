#!/usr/bin/env python3
"""Tests for benchmarks/replay_rolling_conformal.py (INS-IMPROVE-007
item 4). Standalone, stdlib only, fixed synthetic inputs.
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
    "rc", os.path.join(ROOT, "benchmarks", "replay_rolling_conformal.py"))
C = importlib.util.module_from_spec(spec)
sys.modules["rc"] = C
spec.loader.exec_module(C)


def row(real, a, t="A", h="week", cell=1, sig=0.02):
    return {"ticker": t, "as_of": a, "horizon": h, "real": real,
            "naive_half": 5.0, "mult": 1.0, "v2_sigma": sig, "cell": cell}


def half(h="week", sig=0.02):
    return C.R.half_pct(sig, h, C.ens_mod.V2_BAND_K[h], 1.0)


DATES = ["2025-01-01", "2025-02-15", "2025-04-01", "2025-05-16",
         "2025-07-01", "2025-08-15", "2025-10-01", "2025-11-15"]


def test_constants():
    check("v2 pinned", C.ens_mod.V2_BAND_K == {
        "day": 1.15, "week": 1.28, "month": 1.20})
    check("params", (C.LEVEL, C.WINDOW, C.MIN_HIST, C.MATURITY_DAYS)
          == (0.80, 6, 4, 35))
    check("clean cells", C.CLEAN_MIN_CELL == 91)
    check("keep rule is the shared one", C.keep_verdict is C.V.keep_verdict)


def test_quantile():
    check("short history is v2", C.conformal_q([5.0] * 3) == 1.0)
    check("index ceil((n+1)*0.8): n=4 -> largest",
          C.conformal_q([0.1, 0.2, 0.3, 0.4]) == 0.4)
    sc = [i / 10.0 for i in range(1, 10)]
    check("n=9 -> 8th smallest", abs(C.conformal_q(sc) - 0.8) < 1e-9)


def test_per_ticker_and_trailing():
    hist = [row(half() * 0.5, d, t="A") for d in DATES[:5]]
    hist += [row(half() * 3.0, d, t="B") for d in DATES[:5]]
    qa, na = C.q_for("A", "week", "2025-11-15", hist)
    qb, nb = C.q_for("B", "week", "2025-11-15", hist)
    check("ticker A uses only A", abs(qa - 0.5) < 1e-9 and na == 5, (qa, na))
    check("ticker B uses only B", abs(qb - 3.0) < 1e-9 and nb == 5, (qb, nb))
    # trailing window keeps the last 6 cutoffs only
    old = [row(half() * 9.0, "2024-0%d-01" % i, t="A") for i in range(1, 4)]
    new = [row(half() * 0.5, d, t="A") for d in DATES[:7]]
    q, n = C.q_for("A", "week", "2026-01-15", old + new)
    check("window drops old cutoffs", abs(q - 0.5) < 1e-9 and n == 6, (q, n))


def test_no_lookahead_and_maturity():
    hist = [row(half() * 0.5, d, t="A") for d in DATES[:5]]
    q0, n0 = C.q_for("A", "week", "2025-08-15", hist)
    # target 2025-08-15: eligible cutoffs <= 2025-07-11 -> first 5 dates
    check("matured rows count", n0 == 5, n0)
    q1, n1 = C.q_for("A", "week", "2025-07-20", hist)
    check("guard excludes 2025-07-01 (19 d old)", n1 == 4, n1)
    leak = hist + [row(half() * 9.0, "2026-06-01", t="A")]
    q2, n2 = C.q_for("A", "week", "2025-08-15", leak)
    check("later rows never leak", q2 == q0 and n2 == n0)


def test_score_rows():
    rows = [row(half() * 0.5, d, t="A", cell=i + 1)
            for i, d in enumerate(DATES)]
    rows.append(row(half() * 0.5, "2025-12-31", t="A", cell=60))
    p = C.score_rows(rows, lambda r: r["cell"] == 60)
    check("one target pair", len(p) == 1)
    check("recalibrated band narrows", abs(p[0]["q"] - 0.5) < 1e-9, p[0]["q"])
    check("move at 0.5 x v2 half stays inside the 0.5 band edge",
          p[0]["in_ch"] is True and p[0]["in_v2"] is True)
    wide = rows[:-1] + [row(half() * 0.7, "2025-12-31", t="A", cell=60)]
    p2 = C.score_rows(wide, lambda r: r["cell"] == 60)[0]
    check("move at 0.7 x half: outside RC band, inside v2",
          p2["in_ch"] is False and p2["in_v2"] is True)
    check("no sigma excluded", C.score_rows(
        [row(1.0, "2025-12-31", sig=None)], lambda r: True) == [])


def test_refusal():
    check("refuses seen cells", C.main(
        ["score", "--captures", "/nonexistent", "--min-cell", "73"]) == 2)
    check("descriptive refuses holdout cells", C.main(
        ["score", "--captures", "/nonexistent", "--min-cell", "48",
         "--max-cell", "95", "--descriptive"]) == 2)


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
              all(data["results"][h]["n"] == 0
                  for h in ("day", "week", "month")))
        check("descriptive json carries no verdict",
              "verdict" not in data and data["descriptive"] is True)
        with contextlib.redirect_stdout(buf):
            C.main(["score", "--captures", d, "--reps", "50",
                    "--json", out])
        check("clean json carries a verdict",
              "verdict" in json.load(open(out)))


def main():
    for fn in (test_constants, test_quantile, test_per_ticker_and_trailing,
               test_no_lookahead_and_maturity, test_score_rows,
               test_refusal, test_unnumbered_and_json):
        fn()
    print("test_rolling_conformal: %d passed, %d failed"
          % (CHECKS["pass"], CHECKS["fail"]))
    sys.exit(1 if CHECKS["fail"] else 0)


if __name__ == "__main__":
    main()
