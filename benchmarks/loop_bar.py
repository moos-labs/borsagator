#!/usr/bin/env python3
"""Loop-bar keep rule shared by the round 85 shadow challengers.

On untouched cells (>= 91) only. Per horizon: RangeSkill (vs naive)
cutoff-clustered 95% CI lower bound > 0, AND the cutoff-clustered 95%
coverage CI overlaps [0.75, 0.85] with width <= 0.15 (coverage_ci_ok in
replay_band_candidates.py), AND at least MIN_CLUSTERS cutoff clusters.
Fewer clusters on any horizon: counts only, no KEEP and no REJECT.
Input: the dict returned by replay_band_candidates.evaluate().
"""
import os
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))
import replay_band_candidates as R  # noqa: E402

HORIZONS = R.HORIZONS
MIN_CLUSTERS = 10


def loop_bar_verdict(res):
    """Return (verdict, reasons): KEEP, REJECT or COUNTS ONLY."""
    short = [h for h in HORIZONS if res[h]["cutoffs"] < MIN_CLUSTERS]
    if short:
        return "COUNTS ONLY", ["%s has %d cutoff clusters, need %d" % (
            h, res[h]["cutoffs"], MIN_CLUSTERS) for h in short]
    bad = []
    for h in HORIZONS:
        c = res[h]
        lo = c["ch_ci_cutoff"][0] if c["ch_ci_cutoff"] else None
        if lo is None or not lo > 0:
            bad.append("%s RangeSkill CI lower bound %s is not > 0" % (h, R._f(lo)))
        if not R.coverage_ci_ok(c["ch_cov_ci_cutoff"]):
            bad.append(R.coverage_ci_reason(h, c["ch_cov_ci_cutoff"], c["ch"]["coverage"]))
    return ("REJECT" if bad else "KEEP"), bad
