"""Tests for benchmarks/disclosure_price_study.py: fixed synthetic
inputs, run under `unittest discover -s scripts` and standalone."""
import contextlib
import importlib.util
import io
import json
import math
import os
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "disclosure_price_study", os.path.join(
        HERE, "..", "benchmarks", "disclosure_price_study.py"))
S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)

CHECKS = {"pass": 0, "fail": 0}


def check(name, ok, detail=""):
    if ok:
        CHECKS["pass"] += 1
    else:
        CHECKS["fail"] += 1
        print("FAIL", name, detail)


def dates(n, start=(2020, 1, 1)):
    import datetime as dt
    d = dt.date(*start)
    out = []
    while len(out) < n:
        out.append(d.isoformat())
        d += dt.timedelta(days=1)
    return out


def series(n, jump_at=None, jump=0.0):
    """Daily returns alternate +1% / -1% (sigma fixed); an optional
    one-off log jump at index jump_at."""
    ds = dates(n)
    c, out = 100.0, []
    for i, d in enumerate(ds):
        r = 0.01 if i % 2 == 0 else -0.01
        if i == jump_at:
            r += jump
        c *= math.exp(r)
        out.append((d, c))
    return out


def test_load_prices_drops_volume_zero():
    with tempfile.TemporaryDirectory() as t:
        p = os.path.join(t, "x.csv")
        open(p, "w").write(
            "Date,Open,High,Low,Close,Volume\n"
            "2020-01-01,1,1,1,1.0,0.0\n"
            "2020-01-02,1,1,1,2.0,10.0\n"
            "2020-01-03,1,1,1,3.0,5.0\n")
        r = S.load_prices(p)
        check("volume-0 bar is not a session",
              r == [("2020-01-02", 2.0), ("2020-01-03", 3.0)], r)


def test_base_and_ratio():
    s = series(120, jump_at=90, jump=0.20)
    i = S.base_index(s, s[90][0])
    check("base is the last session strictly before the announcement",
          i == 89 and s[i][0] < s[90][0], i)
    check("base before the first bar is None",
          S.base_index(s, "2019-01-01") is None)
    st = S.window_stats(s, i)
    check("h=1 ratio includes the announcement-day jump",
          st[1] > 10, st)
    quiet = S.window_stats(s, 70)
    check("quiet window ratio is small and finite",
          0 <= quiet[1] < 1.5 and all(math.isfinite(v)
                                     for v in quiet.values()), quiet)
    check("short history gives None", S.window_stats(s, 30) is None)
    check("short forward window gives None",
          S.window_stats(s, 110) is None)


def test_event_rows_drops_and_ca():
    s = series(150, jump_at=90, jump=0.20)
    prices = {"AAA": s, "BBB": None}
    ev = [{"ticker": "AAA.CA", "announcement_date": s[90][0],
           "profit_direction": "up", "type": "annual"},
          {"ticker": "BBB.CA", "announcement_date": s[90][0],
           "profit_direction": "up", "type": "annual"},
          {"ticker": "AAA.CA", "announcement_date": s[5][0],
           "profit_direction": "down", "type": "interim"}]
    kept, drop = S.event_rows(ev, prices, {"AAA": []})
    check("one kept, one no price file, one short history",
          len(kept) == 1 and drop["no_price_file"] == 1
          and drop["short_history_or_window"] == 1, (kept, drop))
    inside = {"AAA": [s[95][0]]}
    kept2, drop2 = S.event_rows(ev[:1], prices, inside)
    check("capital action inside the 21-session window drops the event",
          not kept2 and drop2["capital_action_in_window"] == 1, drop2)
    outside = {"AAA": [s[140][0]]}
    kept3, _d = S.event_rows(ev[:1], prices, outside)
    check("capital action after the window keeps the event",
          len(kept3) == 1)
    kept4, d4 = S.event_rows(ev[:1], prices, {"AAA": None})
    check("missing capital-action file keeps and counts",
          len(kept4) == 1 and d4["no_ca_file_kept"] == 1, d4)


def test_control_skips_event_windows():
    s = series(200, jump_at=90, jump=0.20)
    ev = [{"ticker": "AAA.CA", "announcement_date": s[90][0]}]
    ctrl = S.control_rows(ev, {"AAA": s}, {"AAA": []})
    bases = [r["ann"] for r in ctrl]
    check("first window starts at the 60th session",
          bases[0] == s[60][0], bases[:3])
    check("the clashing window (81..102) is skipped, the next kept",
          s[81][0] not in bases and bases[1] == s[102][0], bases[:3])
    clash = [b for b in bases if s[90][0] > b >= s[69][0]]
    check("no control window holds the announcement date",
          not clash, clash)


def test_exact_ratio_scaling_and_control_ca():
    s = series(200, jump_at=73, jump=0.30)
    b = 70
    sig = 0.01 * math.sqrt(60.0 / 59.0)
    st = S.window_stats(s, b)
    for h in (1, 5, 21):
        mv = abs(math.log(s[b + h][1] / s[b][1]))
        check("ratio h=%d is |move| / (sigma sqrt(h))" % h,
              abs(st[h] - mv / (sig * math.sqrt(h))) < 1e-9,
              (st[h], mv / (sig * math.sqrt(h))))
    ev = [{"ticker": "AAA.CA", "announcement_date": "2099-01-01"}]
    free = S.control_rows(ev, {"AAA": s}, {"AAA": []})
    with_ca = S.control_rows(ev, {"AAA": s}, {"AAA": [s[65][0]]})
    check("a capital action inside a control window removes it",
          len(with_ca) < len(free)
          and s[60][0] not in [r["ann"] for r in with_ca],
          (len(free), len(with_ca)))


def test_summary_and_boot():
    rows = [{"ann": "d%d" % (i % 4), "ratios": {1: 0.5 + 0.1 * i,
                                               5: 1.5, 21: 0.2}}
            for i in range(8)]
    check("median", S.med([3, 1, 2]) == 2 and S.med([]) is None)
    check("in-band share counts ratio <= Z80",
          S.cov([1.0, 1.3, 0.1, 2.0]) == 0.5)
    b1 = S.boot(rows, 1)
    b2 = S.boot(rows, 1)
    check("bootstrap is deterministic for the fixed seed", b1 == b2)
    check("clusters counted by announcement date",
          b1["clusters"] == 4, b1)
    check("interval is ordered",
          b1["median_ci"][0] <= b1["median_ci"][1])
    check("empty rows give None", S.boot([], 1) is None)


def test_build_split_and_render_no_verdict():
    s = series(200, jump_at=90, jump=0.20)
    ev = [{"ticker": "AAA.CA", "announcement_date": s[90][0],
           "profit_direction": "up", "type": "annual"},
          {"ticker": "AAA.CA", "announcement_date": s[120][0],
           "profit_direction": "down", "type": "interim"}]
    rep = S.build(ev, {"AAA": s}, {"AAA": []})
    check("splits by direction and type",
          {"all", "dir=up", "dir=down", "type=annual",
           "type=interim"} <= set(rep["events"]), list(rep["events"]))
    check("split sizes",
          rep["events"]["dir=up"]["1"]["n"] == 1
          and rep["events"]["all"]["1"]["n"] == 2)
    txt = S.render(rep)
    low = (txt + json.dumps(rep)).lower()
    check("no verdict or keep wording in text or json",
          "verdict" not in low and "keep" not in low, txt[:200])
    check("states descriptive only", txt.startswith("DESCRIPTIVE ONLY"))


def test_cli_and_loader():
    s = series(200, jump_at=90, jump=0.20)
    with tempfile.TemporaryDirectory() as t:
        pd_, cd = os.path.join(t, "p"), os.path.join(t, "c")
        os.makedirs(pd_)
        os.makedirs(cd)
        with open(os.path.join(pd_, "aaa.csv"), "w") as f:
            f.write("Date,Open,High,Low,Close,Volume\n")
            for d, c in s:
                f.write("%s,%s,%s,%s,%s,100\n" % (d, c, c, c, c))
        json.dump([{"effectiveDate": "05 May 2020"}],
                  open(os.path.join(cd, "AAA.json"), "w"))
        ec = os.path.join(t, "e.csv")
        open(ec, "w").write(
            "ticker,announcement_date,period_end,type,profit_direction,"
            "announce_time,mubasher_id\n"
            "AAA.CA,%s,x,annual,up,10:00,1\n"
            "ETEL.CA,2025-02-27,x,annual,up,10:00,2\n" % s[90][0])
        out = os.path.join(t, "o.json")
        with contextlib.redirect_stdout(io.StringIO()):
            rc = S.main(["--events", ec, "--prices", pd_, "--ca", cd,
                         "--json", out])
        rep = json.load(open(out))
        check("cli writes json; ETEL 2025-02-27 cleared out",
              rc == 0 and rep["design"]["events_in"] == 1, rep["design"])
        check("long date parse", S.parse_long_date("05 May 2020")
              == "2020-05-05" and S.parse_long_date("x") is None)


def run_all():
    for fn in (test_load_prices_drops_volume_zero, test_base_and_ratio,
               test_event_rows_drops_and_ca,
               test_control_skips_event_windows,
               test_exact_ratio_scaling_and_control_ca,
               test_summary_and_boot,
               test_build_split_and_render_no_verdict,
               test_cli_and_loader):
        fn()


class Suite(unittest.TestCase):
    """Runs the checks under `unittest discover -s scripts`."""

    def test_checks(self):
        CHECKS["pass"] = CHECKS["fail"] = 0
        run_all()
        self.assertEqual(CHECKS["fail"], 0)
        self.assertGreater(CHECKS["pass"], 0)


def main():
    run_all()
    print("test_disclosure_price_study: %d passed, %d failed"
          % (CHECKS["pass"], CHECKS["fail"]))
    sys.exit(1 if CHECKS["fail"] else 0)


if __name__ == "__main__":
    main()
