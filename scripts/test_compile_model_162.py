#!/usr/bin/env python3
"""Unit tests for issue #162: ex_date_adjustment applies only the
first in-window action.

Before the fix, ex_date_adjustment returned the FIRST dated action
whose ex-date fell in (last_date, base_date]; if two distinct
actions fell in the window, only one was applied, so the
tripwire's price sanity check used a wrong adjustment -- a false
mismatch (flags a good sweep) or a false pass (misses a real gap).
The fix compounds EVERY in-window action: each mechanical_pct is
``-dps / base * 100`` against the same ensemble base (ensemble.py),
so two in-window actions drop the price by dps1 + dps2 off that
one base and the compounded fraction is the SUM of the fractions.

Stdlib only, no network, no fixtures. Run:
    python3 scripts/test_compile_model_162.py
Exit 0 only when every test passes.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)

import compile_model  # noqa: E402

RESULTS = []

LAST = "2026-11-10"
BASE = "2026-11-18"


def check(name, fn):
    try:
        fn()
    except Exception as e:
        RESULTS.append((name, False, f"{type(e).__name__}: {e}"))
        print(f"FAIL {name}: {type(e).__name__}: {e}")
        return
    RESULTS.append((name, True, ""))
    print(f"PASS {name}")


def approx(got, want, tol=1e-9):
    assert got is not None and abs(got - want) <= tol, \
        f"got {got!r}, want {want!r}"


def action(ex_date, mech):
    return {"type": "dividend", "dps": 1.0, "ex_date": ex_date,
            "mechanical_pct": mech}


def two_actions():
    # Two distinct dividends in the window: -19.00% and -5.00%
    # (dps 1.90 and 0.50 off a 10.00 base), ex-dates 12 and 16 Nov.
    return [action("2026-11-12", -19.0), action("2026-11-16", -5.0)]


def test_two_actions_compound():
    # -19% + -5% = -24% compounded, not the first action's -19%.
    approx(compile_model.ex_date_adjustment(LAST, BASE, two_actions()),
           -0.24)


def test_two_actions_order_independent():
    # Same actions, reversed list order: the sum must not depend on
    # disclosure-item order (the #131 order-independence rule).
    approx(compile_model.ex_date_adjustment(
        LAST, BASE, list(reversed(two_actions()))), -0.24)


def test_single_action_unchanged():
    # One in-window action behaves exactly as before the fix.
    approx(compile_model.ex_date_adjustment(
        LAST, BASE, [action("2026-11-12", -19.0)]), -0.19)
    approx(compile_model.ex_date_adjustment(
        LAST, BASE, [action("2026-11-16", -5.0)]), -0.05)


def test_no_in_window_action():
    # Ex-date on last_date (window is open on the left) or after
    # base_date: no adjustment.
    assert compile_model.ex_date_adjustment(
        LAST, BASE, [action("2026-11-10", -19.0)]) is None
    assert compile_model.ex_date_adjustment(
        LAST, BASE, [action("2026-11-19", -19.0)]) is None
    assert compile_model.ex_date_adjustment(LAST, BASE, []) is None
    assert compile_model.ex_date_adjustment(LAST, BASE, None) is None


def test_missing_dates():
    assert compile_model.ex_date_adjustment(None, BASE,
                                            two_actions()) is None
    assert compile_model.ex_date_adjustment(LAST, None,
                                            two_actions()) is None
    assert compile_model.ex_date_adjustment("", BASE,
                                            two_actions()) is None


def test_out_of_window_and_undated_skipped():
    # Only in-window actions compound; an out-of-window action and
    # undated / mech-less actions are ignored.
    actions = [action("2026-11-05", -19.0),  # before the window
               action("2026-11-12", -19.0),
               action("2026-11-16", -5.0),
               {"type": "dividend", "dps": 1.0, "ex_date": None,
                "mechanical_pct": -50.0},
               {"type": "dividend", "dps": 1.0, "ex_date": "2026-11-14",
                "mechanical_pct": None}]
    approx(compile_model.ex_date_adjustment(LAST, BASE, actions), -0.24)


def test_unparseable_in_window_fails_closed():
    # An unparseable mechanical_pct on any in-window action returns
    # None (fail closed, as before): the tripwire then compares the
    # unadjusted close and can only false-flag, never false-pass.
    actions = [action("2026-11-12", -19.0),
               action("2026-11-16", "not-a-number")]
    assert compile_model.ex_date_adjustment(LAST, BASE, actions) is None


def test_unparseable_out_of_window_ignored():
    # An unparseable mech OUTSIDE the window must not poison the
    # valid in-window action.
    actions = [action("2026-11-05", "not-a-number"),
               action("2026-11-12", -19.0)]
    approx(compile_model.ex_date_adjustment(LAST, BASE, actions), -0.19)


def _tripwire(base_price, mechs):
    digest = {"ticker": "POUL.CA"}
    ensemble = {"ticker": "POUL.CA", "base_price": base_price,
                "base_date": BASE,
                "corporate_actions": [
                    action("2026-11-12", mechs[0]),
                    action("2026-11-16", mechs[1])]}
    series = [{"source": "egx-data/ohlc", "last_close": 10.0,
               "last_date": LAST}]
    return compile_model.tripwire(digest, ensemble, series,
                                  "egx-data/poul-ohlc.csv")


def test_tripwire_two_actions_no_false_mismatch():
    # Two -25% actions: true post-ex level 10.00 x 0.50 = 5.00.
    # With only the first applied the check is 10.00 x 0.75 = 7.50
    # vs base 5.00 -- a 50% gap, a false mismatch on a good sweep.
    problems = _tripwire(5.00, [-25.0, -25.0])
    assert problems == [], f"unexpected tripwire problems: {problems}"


def test_tripwire_two_actions_no_false_pass():
    # Same two actions, base 7.50: that is exactly the first-action
    # level, so the old code passed a real 33% gap. The compounded
    # check (5.00 vs 7.50) must flag it.
    problems = _tripwire(7.50, [-25.0, -25.0])
    assert len(problems) == 1, f"expected 1 problem: {problems}"
    assert problems[0]["field"] == "price_series_last"


def test_tripwire_single_action_unchanged():
    # One -19% action, base 8.10: clean before and after the fix.
    digest = {"ticker": "POUL.CA"}
    ensemble = {"ticker": "POUL.CA", "base_price": 8.10,
                "base_date": BASE,
                "corporate_actions": [action("2026-11-12", -19.0)]}
    series = [{"source": "egx-data/ohlc", "last_close": 10.0,
               "last_date": LAST}]
    problems = compile_model.tripwire(digest, ensemble, series,
                                      "egx-data/poul-ohlc.csv")
    assert problems == [], f"unexpected tripwire problems: {problems}"


if __name__ == "__main__":
    for name, fn in [
            ("two_actions_compound", test_two_actions_compound),
            ("two_actions_order_independent",
             test_two_actions_order_independent),
            ("single_action_unchanged", test_single_action_unchanged),
            ("no_in_window_action", test_no_in_window_action),
            ("missing_dates", test_missing_dates),
            ("out_of_window_and_undated_skipped",
             test_out_of_window_and_undated_skipped),
            ("unparseable_in_window_fails_closed",
             test_unparseable_in_window_fails_closed),
            ("unparseable_out_of_window_ignored",
             test_unparseable_out_of_window_ignored),
            ("tripwire_two_actions_no_false_mismatch",
             test_tripwire_two_actions_no_false_mismatch),
            ("tripwire_two_actions_no_false_pass",
             test_tripwire_two_actions_no_false_pass),
            ("tripwire_single_action_unchanged",
             test_tripwire_single_action_unchanged)]:
        check(name, fn)
    failed = [r for r in RESULTS if not r[1]]
    print(f"{len(RESULTS) - len(failed)}/{len(RESULTS)} passed")
    sys.exit(1 if failed else 0)
