"""Tests for benchmarks/sentiment_vote.py: fixed synthetic inputs."""
import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "sentiment_vote", os.path.join(HERE, "..", "benchmarks", "sentiment_vote.py"))
V = importlib.util.module_from_spec(spec)
spec.loader.exec_module(V)

CHECKS = {"pass": 0, "fail": 0}


def check(name, ok, detail=""):
    if ok:
        CHECKS["pass"] += 1
    else:
        CHECKS["fail"] += 1
        print("FAIL", name, detail)


def row(asof, tk, h, s, real, status="matured", gap=None):
    return {"as_of": asof, "ticker": tk, "horizon": h, "families": {"sentiment": s},
            "status": status, "dividend_gap": gap, "realized_direction": real}


def test_eligible_and_sign():
    ok = row("d1", "A", "day", 0.5, "up")
    check("elig base", V.eligible(ok))
    check("elig pending", not V.eligible(row("d1", "A", "day", 0.5, "up", status="pending")))
    check("elig invalid", not V.eligible(row("d1", "A", "day", 0.5, "up", status="invalid")))
    check("elig gap", not V.eligible(row("d1", "A", "day", 0.5, "up", gap=True)))
    check("elig month", not V.eligible(row("d1", "A", "month", 0.5, "up")))
    check("elig zero", not V.eligible(row("d1", "A", "day", 0, "up")))
    check("elig flat real", not V.eligible(row("d1", "A", "day", 0.5, "flat")))
    nos = {"as_of": "d1", "ticker": "A", "horizon": "day", "families": {}, "status": "matured",
           "dividend_gap": None, "realized_direction": "up"}
    check("elig no sentiment", not V.eligible(nos))
    votes = V.sign_votes([ok, row("d1", "B", "day", -0.2, "up"), row("d1", "C", "week", -0.1, "down")])
    check("sign agree", votes == [("d1", "day", True), ("d1", "day", False), ("d1", "week", True)], votes)
    big = V.sign_votes([row("d1", "A", "day", 0.01, "up"), row("d1", "B", "day", 0.9, "up")])
    check("no magnitude weight", big == [("d1", "day", True), ("d1", "day", True)])


def test_rank_votes():
    rows = [row("d1", "T%d" % i, "day", s, r) for i, (s, r) in enumerate(
        [(0.1, "down"), (0.2, "up"), (0.3, "down"), (0.4, "up"), (0.5, "up"), (0.6, "up")])]
    v = V.rank_votes(rows)
    # n=6, k=2: bottom 0.1,0.2 vote down; top 0.5,0.6 vote up
    check("rank votes", v == [("d1", "day", True), ("d1", "day", False), ("d1", "day", True), ("d1", "day", True)], v)
    check("rank needs 6", V.rank_votes(rows[:5]) == [])
    # universe ignores maturity, scoring needs it
    rows2 = [dict(r) for r in rows]
    rows2[5]["status"] = "pending"
    v2 = V.rank_votes(rows2)
    check("rank universe incl pending", len(v2) == 3, v2)
    rows3 = [dict(r) for r in rows]
    rows3[0]["status"] = "invalid"
    check("rank drops invalid from universe", V.rank_votes(rows3) == [], "n=5 left")
    # tie order by ticker
    tie = [row("d1", "B%d" % i, "day", 0.5, "up") for i in range(3)] + [row("d1", "A%d" % i, "day", 0.5, "down") for i in range(3)]
    tv = V.rank_votes(tie)
    check("rank tie by ticker", tv == [("d1", "day", True), ("d1", "day", True), ("d1", "day", True), ("d1", "day", True)], tv)
    mid = V.rank_votes([row("d1", "T%d" % i, "day", i + 1, "up") for i in range(9)])
    check("rank abstain middle", len(mid) == 6, len(mid))


def test_gate_and_boot():
    rows = []
    for i in range(29):
        rows += [row("d%02d" % i, "A", "day", 1.0, "up"), row("d%02d" % i, "A", "week", 1.0, "up")]
    by, both = V.gate_dates(rows)
    check("gate 29", both == 29 and len(by["day"]) == 29)
    res = V.score(rows)
    check("below gate counts only", not res["gate_reached"] and "sign_vote" not in res and "dates_with_both" in res)
    rows += [row("d29", "A", "day", 1.0, "up")]
    check("day only date not both", V.gate_dates(rows)[1] == 29)
    rows += [row("d29", "A", "week", 1.0, "up")]
    res = V.score(rows)
    check("gate 30", res["gate_reached"] and res["sign_vote"]["day"]["n_dates"] == 30)
    check("all agree passes", res["sign_vote"]["lower_gt_0.5_both"] is True)
    check("share 1", res["sign_vote"]["day"]["agree_share"] == 1.0)
    # half agree: lower bound below 0.5
    mixed = []
    for i in range(30):
        mixed += [row("d%02d" % i, "A", h, 1.0, "up" if i % 2 == 0 else "down") for h in ("day", "week")]
    rm = V.score(mixed)
    check("half agree fails", rm["sign_vote"]["lower_gt_0.5_both"] is False, rm["sign_vote"]["day"])
    lo, hi = V.boot_lower([("a", True), ("a", True), ("b", True)], draws=100)
    check("boot all true", lo == 1.0 and hi == 1.0)
    check("boot deterministic", V.boot_lower([("a", True), ("b", False)], 200) == V.boot_lower([("a", True), ("b", False)], 200))
    ml, mh = V.boot_lower([("a", True), ("b", False), ("c", True), ("d", False)], 300)
    check("boot resamples dates", ml < 0.5 < mh or ml < mh, (ml, mh))
    # n_dates leg: 29 dates with all agree cannot pass even if lower>0.5
    short = []
    for i in range(30):
        short.append(row("d%02d" % i, "A", "day", 1.0, "up"))
        if i < 29:
            short.append(row("d%02d" % i, "A", "week", 1.0, "up"))
    rs = V.score(short)
    check("week n_dates 29 fails leg", rs["gate_reached"] is False)


def test_pass_leg_and_seed():
    def mk(lo, nd):
        return {h: {"ci95": [lo, 1.0], "n_dates": nd} for h in V.HORIZONS}
    check("leg pass", V.pass_leg(mk(0.51, 30)))
    check("leg lower==0.5 fails", not V.pass_leg(mk(0.5, 30)))
    check("leg n_dates 29 fails", not V.pass_leg(mk(0.9, 29)))
    r = mk(0.9, 30)
    r["week"]["ci95"] = [None, None]
    check("leg none fails", not V.pass_leg(r))
    mixed = mk(0.9, 30)
    mixed["week"]["n_dates"] = 29
    check("leg one horizon short fails", not V.pass_leg(mixed))
    check("seed and draws", V.SEED == 69 and V.B_DRAWS == 2000 and V.GATE_DATES == 30)
    v = [("d%d" % i, (i + j) % 3 != 0) for i in range(40) for j in range(i % 4 + 1)]
    a69 = V.boot_lower(v)
    check("boot default seed is 69", a69 == V.boot_lower(v, V.B_DRAWS, 69))
    check("boot seed matters", a69 != V.boot_lower(v, V.B_DRAWS, 70), a69)
    # invalid row in the rank universe changes terciles
    base = [row("d1", "T%d" % i, "day", i + 1.0, "up") for i in range(6)]
    inv = base + [dict(row("d1", "Z", "day", -5.0, "down"), status="invalid")]
    check("invalid not in universe", V.rank_votes(inv) == V.rank_votes(base))
    b8 = [row("d1", "T%d" % i, "day", i + 1.0, "up") for i in range(8)]
    z = b8 + [row("d1", "Z", "day", 0.0, "down")]
    check("zero sentiment stays in rank universe", V.rank_votes(z) != V.rank_votes(b8))
    gap = base + [row("d1", "Z", "day", -5.0, "down", gap=True)]
    check("gap not in universe", V.rank_votes(gap) == V.rank_votes(base))


def test_cli():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "l.json")
        json.dump({"forecasts_detail": [row("d1", "A", "day", 1.0, "up")]}, open(p, "w"))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            V.main(["--ledger", p, "--json", os.path.join(d, "o.json")])
        txt = open(os.path.join(d, "o.json")).read().lower()
        check("cli gate counts", json.loads(txt)["dates_with_both"] == 0)
        check("no verdict word", not any(w in txt for w in ("verdict", "keep", "reject", "adopt")))


def run_all():
    for fn in (test_eligible_and_sign, test_rank_votes, test_gate_and_boot, test_pass_leg_and_seed, test_cli):
        fn()


class Suite(unittest.TestCase):
    def test_checks(self):
        CHECKS["pass"] = CHECKS["fail"] = 0
        run_all()
        self.assertEqual(CHECKS["fail"], 0)
        self.assertGreater(CHECKS["pass"], 0)


def main():
    run_all()
    print("test_sentiment_vote: %d passed, %d failed" % (CHECKS["pass"], CHECKS["fail"]))
    sys.exit(1 if CHECKS["fail"] else 0)


if __name__ == "__main__":
    main()
