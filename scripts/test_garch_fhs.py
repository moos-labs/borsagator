#!/usr/bin/env python3
"""Tests for benchmarks/replay_garch_fhs.py (INS-IMPROVE-006 D).
Standalone, stdlib only.
"""
import importlib.util
import math
import os
import random
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
    "gf", os.path.join(ROOT, "benchmarks", "replay_garch_fhs.py"))
G = importlib.util.module_from_spec(spec)
sys.modules["gf"] = G
spec.loader.exec_module(G)


def sim_garch(n, omega=2e-6, a=0.08, b=0.90, seed=1):
    rng = random.Random(seed)
    v, out = omega / (1 - a - b), []
    for _ in range(n):
        r = rng.gauss(0, 1) * math.sqrt(v)
        out.append(r)
        v = omega + a * r * r + b * v
    return out


def test_constants():
    check("v2 pinned", G.ens_mod.V2_BAND_K == {
        "day": 1.15, "week": 1.28, "month": 1.20})
    check("spec", (G.N_RET, G.MIN_RET, G.N_SIM, G.SEED)
          == (750, 400, 2000, 594))
    check("clean cells", G.CLEAN_MIN_CELL == 91)


def test_fit():
    r = sim_garch(750)
    p = G.fit_garch(r)
    check("fit returns params", p is not None)
    omega, a, b = p
    check("persistence high", 0.80 < a + b < 0.999, (a, b))
    check("short series is None", G.fit_garch(r[:100]) is None)


def test_fhs():
    r = sim_garch(750)
    d = G.fhs_band(r, 1)
    w = G.fhs_band(r, 5)
    m = G.fhs_band(r, 21)
    check("positive and growing with h", 0 < d < w < m, (d, w, m))
    check("roughly sqrt scaling", 1.5 < m / d < 8.0, (d, m))
    check("deterministic with seed", G.fhs_band(r, 5) == w)
    check("None when short", G.fhs_band(r[:100], 5) is None)


def test_score_rows():
    row = {"ticker": "A", "as_of": "d", "horizon": "week", "real": 1.0,
           "naive_half": 5.0, "mult": 1.0, "v2_sigma": 0.02,
           "fhs_half": 4.0}
    p = G.score_rows([row])[0]
    check("scored", p["in_ch"])
    check("excluded when no band",
          G.score_rows([dict(row, fhs_half=None)]) == [])


def test_screen_window_limit():
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        cap = os.path.join(d, "TST")
        os.makedirs(cap)
        r = sim_garch(1000, seed=3)
        px, rows = 10.0, ["date,close"]
        import datetime as dt
        day = dt.date(2020, 1, 1)
        for x in [0.0] + r:
            px *= math.exp(x)
            rows.append("%s,%f" % (day.isoformat(), px))
            day += dt.timedelta(days=1)
        with open(os.path.join(cap, "price.csv"), "w") as f:
            f.write("\n".join(rows))
        cl = G.read_closes(cap, "2023-12-28")
        check("read_closes honours base date",
              all(dd <= "2023-12-28" for dd, _ in cl))
        pairs = G.screen_pairs([cap])
        check("pairs built", len(pairs) > 0)
        check("no window after 2023-12-28",
              all(p["as_of"] <= "2023-12-28" for p in pairs))


def test_pooled():
    r1 = sim_garch(800, seed=11)
    r2 = [3.0 * x for x in sim_garch(800, seed=12)]
    ab = G.fit_pooled({"A": r1, "B": r2})
    check("pooled fit returns shared (a, b)", ab is not None
          and ab[0] + ab[1] < 0.999, ab)
    ab2 = G.fit_pooled({"A": r1, "B": [x * 2 for x in r2]})
    check("pooled dynamics invariant to per-ticker scale", ab == ab2,
          (ab, ab2))
    w1 = G.fhs_band_pooled(r1, 5, ab, n_sim=500)
    w2 = G.fhs_band_pooled([x * 2 for x in r1], 5, ab, n_sim=500)
    check("per-ticker scale carried by the band", 1.8 < w2 / w1 < 2.3,
          (w1, w2))
    check("short history excluded",
          G.fhs_band_pooled(r1[:100], 5, ab) is None
          and G.fit_pooled({"A": r1[:100]}) is None)


def test_pooled_screen_window_limit():
    import datetime as dt
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        for k, t in enumerate(("TST", "TSU")):
            cap = os.path.join(d, t)
            os.makedirs(cap)
            px, rows = 10.0, ["date,close"]
            day = dt.date(2019, 1, 1)
            for x in [0.0] + sim_garch(1800, seed=20 + k):
                px *= math.exp(x)
                rows.append("%s,%f" % (day.isoformat(), px))
                day += dt.timedelta(days=1)
            with open(os.path.join(cap, "price.csv"), "w") as f:
                f.write("\n".join(rows))
        pairs, ab = G.screen_pooled_pairs(
            [os.path.join(d, "TST"), os.path.join(d, "TSU")])
        check("pooled pairs built", len(pairs) > 0 and ab is not None)
        check("no window after 2023-12-28",
              all(p["as_of"] <= "2023-12-28" for p in pairs))
        check("screening starts after the pooled fit window",
              all(p["as_of"] >= G.POOL_SCREEN_START for p in pairs)
              and G.POOL_SCREEN_START > G.POOL_FIT_END)


def test_refusal():
    check("refuses seen cells", G.main(
        ["score", "--captures", "/nonexistent", "--min-cell", "73"]) == 2)


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
              G.A.find_captures([d], 48) != [])
        with contextlib.redirect_stdout(buf):
            rc = G.main(["score", "--captures", d, "--min-cell", "48",
                         "--descriptive", "--reps", "50", "--json", out])
        data = json.load(open(out))
        check("descriptive run exits 0", rc == 0)
        check("unnumbered capture dropped from scoring",
              all(data["results"][h]["n"] == 0 for h in ("day", "week", "month")))
        check("descriptive json carries no verdict",
              "verdict" not in data and data["descriptive"] is True)
        with contextlib.redirect_stdout(buf):
            G.main(["score", "--captures", d, "--reps", "50",
                    "--json", out])
        check("clean json carries a verdict",
              "verdict" in json.load(open(out)))


def main():
    for fn in (test_constants, test_fit, test_fhs, test_score_rows,
               test_screen_window_limit, test_pooled,
               test_pooled_screen_window_limit, test_refusal):
        fn()
    print("test_garch_fhs: %d passed, %d failed"
          % (CHECKS["pass"], CHECKS["fail"]))
    sys.exit(1 if CHECKS["fail"] else 0)


if __name__ == "__main__":
    main()
