#!/usr/bin/env python3
"""Adoption-test scorer for the #594 ensemble recalibration.

Scores the FROZEN v2 band parameters against the retired v1
parameters on scored backtest cell captures (cells 48+ by default,
the cells the v2 freeze never saw) and prints the #594 adoption
verdict.

Metric: RangeSkill_h = 1 - mean(IS_ens) / mean(IS_naive), where IS is
the Winkler interval score at 80% (alpha 0.2) and naive is the
range 0 +/- 1.2816 x sigma60 x sqrt(sessions_h). Realised moves,
dividend adjustment, split invalidation and the naive range all come
from scripts/backtest_score.py (score_capture), so this scorer and
the #436 scorer cannot disagree on what a cell realised.

Params compared (both re-derived from each capture's own inputs, so
the answer does not depend on which formula wrote ensemble.json):
  v2  frozen: centre 0, half = V2_BAND_K[h] x sigma60 x sqrt(sessions)
      x RISK_MULT (scripts/ensemble.py). Band calibration (#593) is
      NOT applied: this scores the frozen parameters.
  v1  retired: centre = expected_move(kmove, net, vol_h) (0.6 Kronos
      + 0.4 net x 1.28 vol_h), half = max(1.28 vol_h, Kronos band)
      x RISK_MULT x (1 + 0.5 x disagree), v1 weights. Evaluated on
      the same session horizons (1/5/21) as v2, so the comparison
      isolates the parameters, not the #666 horizon fix.

Confidence interval: BLOCK bootstrap by ticker. Whole tickers are
resampled with replacement and every row of a drawn ticker comes
along, so the overlapping windows of one ticker never count as
independent draws (a by-cell bootstrap on ~6 tickers is too narrow,
#594 review). Percentile 95% CI, fixed seed.

Adoption criterion: adopt a tilt only if its RangeSkill CI lower
bound > 0. Fewer than MIN_ROWS rows or MIN_TICKERS tickers in a
horizon is reported as INSUFFICIENT, never as a pass or a fail:
a block bootstrap over one or two tickers has no meaningful CI.

Usage:
  python3 benchmarks/score_adoption_594.py --captures DIR [DIR ...]
      [--min-cell 48] [--reps 5000] [--seed 20261125] [--json OUT]
DIR is searched recursively for <cutoff>/<TICKER>/ capture dirs that
hold manifest.json, digest/ensemble.json and realised.json (the
archive branch's worker-runs/*/backtest/ trees).
"""
import argparse
import json
import math
import os
import random
import re
import shutil
import sys
import tempfile

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import backtest_score as bs  # noqa: E402
import ensemble as ens_mod  # noqa: E402

HORIZONS = ("day", "week", "month")
SESSIONS = {"day": 1, "week": 5, "month": 21}
MIN_ROWS = 30
MIN_TICKERS = 5
CI_LEVEL = 0.95
DEFAULT_SEED = 20261125
DEFAULT_REPS = 5000
# Retired v1 family weights (scripts/ensemble.py before #665).
V1_W = {
    "price-forecast": {"day": .45, "week": .40, "month": .30},
    "technicals":     {"day": .30, "week": .20, "month": .10},
    "sentiment":      {"day": .15, "week": .15, "month": .05},
    "agent":          {"day": .10, "week": .20, "month": .30},
    "fundamentals":   {"day": .00, "week": .00, "month": .25},
}
CRITERION = ("Adopt a tilt only if its RangeSkill CI lower bound > 0 "
             "(block bootstrap by ticker, 95%).")


def fnum(v):
    return bs.fnum(v)


# ---------------------------------------------------------------- params
def _sigma60(ens):
    s = fnum(ens.get("sigma60_daily"))
    return s if s is not None else fnum(ens.get("sigma_daily"))


def v2_horizons(ens):
    """Frozen v2 ranges from the capture's sigma60 and risk level."""
    sigma60 = _sigma60(ens)
    if not sigma60:
        return {}
    mult = ens_mod.RISK_MULT.get((ens.get("risk") or {}).get("level"), 1.0)
    out = {}
    for h in HORIZONS:
        half = (ens_mod.V2_BAND_K[h] * sigma60
                * math.sqrt(SESSIONS[h]) * mult) * 100
        out[h] = {"expected_move_pct": 0.0, "range_low_pct": -half,
                  "range_high_pct": half, "direction": "flat",
                  "trading_sessions": SESSIONS[h]}
    return out


def v1_horizons(ens, kronos_path, base):
    """Retired v1 ranges. kronos_path is [(close, high, low)] from
    the capture's forecast.csv (session-indexed)."""
    sigma = fnum(ens.get("sigma_daily"))
    if not sigma or not base:
        return {}
    risk = ens.get("risk") or {}
    mult = ens_mod.RISK_MULT.get(risk.get("level"), 1.0)
    price_mult = fnum(risk.get("price_mult"))
    price_mult = 1.0 if price_mult is None else price_mult
    fam = {k: fnum(v) for k, v in (ens.get("family_scores") or {}).items()
           if k != "price-forecast"}
    out = {}
    for h in HORIZONS:
        bar = SESSIONS[h]
        vol_h = sigma * math.sqrt(bar)
        ka = None
        if kronos_path:
            c, hi, lo = kronos_path[min(bar, len(kronos_path)) - 1]
            ka = {"move": c / base - 1.0,
                  "band": max((hi - lo) / 2.0 / base, 0.004)}
        scores, weights = {}, {}
        for f, s in list(fam.items()) + [
                ("price-forecast",
                 None if not ka else
                 max(-1.0, min(1.0, ka["move"] / (2.0 * vol_h)))
                 if vol_h > 0 else 0.0)]:
            if s is None or V1_W[f][h] == 0:
                continue
            scores[f] = s
            weights[f] = V1_W[f][h] * (price_mult
                                       if f == "price-forecast" else 1.0)
        if not scores:
            continue
        wsum = sum(weights.values())
        net = sum(scores[f] * weights[f] for f in scores) / wsum
        var = sum(weights[f] * (scores[f] - net) ** 2
                  for f in scores) / wsum
        disagree = math.sqrt(var)
        kmove = ka["move"] if ka else 0.0
        expected = ens_mod.expected_move(kmove, net, vol_h)
        half = (max(1.28 * vol_h, ka["band"] if ka else 0.0)
                * mult * (1 + .5 * disagree))
        out[h] = {"expected_move_pct": expected * 100,
                  "range_low_pct": (expected - half) * 100,
                  "range_high_pct": (expected + half) * 100,
                  "direction": "up" if expected > .0075 else
                  "down" if expected < -.0075 else "flat",
                  "trading_sessions": bar}
    return out


# ------------------------------------------------------------ captures
def cell_number(path):
    # "cell<N>" must stand alone: not preceded or followed by another
    # letter or digit, so "notcell91" is unnumbered while the real
    # archive names (...-cell2-r2, ...-cell47) still match. The last
    # match wins.
    m = re.findall(r"(?<![A-Za-z0-9])cell(\d+)(?![A-Za-z0-9])", path)
    return int(m[-1]) if m else None


def find_captures(roots, min_cell=None, max_cell=None, rejects=None):
    """Capture dirs under roots: <cutoff>/<TICKER>/ holding the three
    scoring inputs. One (cutoff, ticker) is one observation: when a
    cell was rerun, the lexically latest path wins, but a numbered path
    always beats an unnumbered one (an unnumbered capture is dropped by
    every scorer, so letting it win the dedup would lose the numbered
    observation). min_cell and max_cell (both optional, inclusive) are
    applied BEFORE the per-(cutoff, ticker) winner is chosen, so a
    capture outside the requested cells can never displace an eligible
    one (a cell-91 rerun must not hide the cell-48 observation of the
    same cutoff and ticker)."""
    found = {}
    for root in roots:
        for dp, dn, fn in os.walk(root):
            if ".tmp-" in dp or ".old-" in dp:
                continue
            if "manifest.json" in fn and not (
                    "realised.json" in fn and os.path.exists(os.path.join(
                        dp, "digest", "ensemble.json"))):
                # Incomplete capture: never selected. When the caller passes
                # a rejects list, record why so an exclusion report can list it.
                inum = cell_number(dp)
                # Only capture-shaped dirs (<cutoff>/<TICKER>): a run-level
                # manifest.json above them is not a capture.
                # and carrying at least one other capture input, so a
                # manifest-only dir (a run-level manifest) is not listed.
                has_other = ("realised.json" in fn or os.path.exists(
                    os.path.join(dp, "digest", "ensemble.json")))
                if (rejects is not None and inum is not None and has_other
                        and re.match(r"^\d{4}-\d{2}-\d{2}$", os.path.basename(os.path.dirname(dp)))
                        and (min_cell is None or inum >= min_cell)
                        and (max_cell is None or inum <= max_cell)):
                    miss = [n for n, ok in (
                        ("realised.json", "realised.json" in fn),
                        ("digest/ensemble.json", os.path.exists(os.path.join(
                            dp, "digest", "ensemble.json")))) if not ok]
                    rejects.append("incomplete capture %s: missing %s"
                                   % (dp, ", ".join(miss)))
            if ("manifest.json" in fn and "realised.json" in fn
                    and os.path.exists(os.path.join(
                        dp, "digest", "ensemble.json"))):
                cutoff = os.path.basename(os.path.dirname(dp))
                if not re.match(r"^\d{4}-\d{2}-\d{2}$", cutoff):
                    continue
                num = cell_number(dp)
                if min_cell is not None and num is not None \
                        and num < min_cell:
                    continue
                if max_cell is not None and num is not None \
                        and num > max_cell:
                    continue
                key = (cutoff, os.path.basename(dp).upper())
                rank = (num is not None, dp)
                if key not in found or rank > found[key][0]:
                    found[key] = (rank, dp)
    return [found[k][1] for k in sorted(found)]


def _stage(capture, variant, tmp):
    """Copy a capture (only the scoring inputs) to tmp/<variant>/
    <cutoff>/<ticker> with ensemble.json horizons replaced by the
    variant's. Returns (staged dir, gaps)."""
    ticker = os.path.basename(capture)
    cutoff = os.path.basename(os.path.dirname(capture))
    dst = os.path.join(tmp, variant, cutoff, ticker)
    os.makedirs(os.path.join(dst, "digest"))
    os.makedirs(os.path.join(dst, "collected", "kronos"))
    for rel in ("manifest.json", "realised.json"):
        shutil.copy(os.path.join(capture, rel), os.path.join(dst, rel))
    kf = os.path.join(capture, "collected", "kronos", "forecast.csv")
    if os.path.exists(kf):
        shutil.copy(kf, os.path.join(dst, "collected", "kronos"))
    ens = bs.load_json(os.path.join(capture, "digest", "ensemble.json"))
    kpath, _ = bs.read_kronos_path(kf)
    base = fnum(ens.get("base_price"))
    hz = (v2_horizons(ens) if variant == "v2"
          else v1_horizons(ens, kpath, base))
    new = dict(ens)
    new["horizons"] = hz
    with open(os.path.join(dst, "digest", "ensemble.json"), "w",
              encoding="utf-8") as f:
        json.dump(new, f)
    return dst


def _relevant_gaps(gaps):
    """Gaps that bear on the ensemble / naive-range rows scored here.
    The tilt and index entrants are not part of this test."""
    out = []
    for g in gaps:
        if "tilt-technicals" in g or "index-baseline" in g:
            continue
        out.append(re.sub(r"^\S*adopt594-[^/]+/v\d/", "", g))
    return out


def score_rows(captures):
    """Matured, non-gap-flagged rows per variant, joined with the
    naive-range interval score of the same capture and horizon.
    Returns (pairs, gaps): pairs = list of dicts."""
    gaps, rows = [], {"v1": {}, "v2": {}}
    naive = {}
    tmp = tempfile.mkdtemp(prefix="adopt594-")
    try:
        for cap in captures:
            for variant in ("v1", "v2"):
                try:
                    d = _stage(cap, variant, tmp)
                    r, g = bs.score_capture(d)
                except Exception as e:  # one bad cell never aborts
                    gaps.append("%s: %s scoring failed: %s"
                                % (cap, variant, e))
                    continue
                if variant == "v2":  # one report per cell, not per variant
                    gaps.extend(_relevant_gaps(g))
                for row in r:
                    if row.get("status") != "matured" \
                            or row.get("dividend_gap"):
                        continue
                    key = (row["ticker"], row["as_of"], row["horizon"])
                    if row["entrant"] == "2-family-ensemble":
                        rows[variant][key] = row
                    elif row["entrant"] == "naive-range" \
                            and variant == "v2":
                        naive[key] = row
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    pairs = []
    for key in sorted(set(rows["v1"]) & set(rows["v2"]) & set(naive)):
        out = {"ticker": key[0], "as_of": key[1], "horizon": key[2]}
        for name, row in (("v1", rows["v1"][key]),
                          ("v2", rows["v2"][key]),
                          ("naive", naive[key])):
            if row.get("range_low_pct") is None:
                break
            out["is_" + name] = bs.winkler_is(
                row["realized_move_pct"], row["range_low_pct"],
                row["range_high_pct"])
            out["in_" + name] = bool(row.get("in_range"))
        else:
            pairs.append(out)
    return pairs, gaps


# ----------------------------------------------------------- statistics
def range_skill(pairs, name):
    """1 - mean IS(name) / mean IS(naive); None when undefined."""
    if not pairs:
        return None
    n = sum(p["is_naive"] for p in pairs)
    if n <= 0:
        return None
    return 1.0 - sum(p["is_" + name] for p in pairs) / n


def block_bootstrap(pairs, reps=DEFAULT_REPS, seed=DEFAULT_SEED,
                    by="ticker"):
    """Block bootstrap. Returns {name: [skill draws]} for v1, v2 and
    their difference (v2 - v1). `by` is the pair field whose values
    are resampled as whole blocks: "ticker" (default, the #594
    criterion) or "as_of" (cutoff blocks, INS-IMPROVE-001: rows that
    share a cutoff share market shocks, so a ticker bootstrap can be
    too narrow). Draws whose resample has an undefined skill are
    dropped (counted by the caller)."""
    by_t = {}
    for p in pairs:
        by_t.setdefault(p[by], []).append(p)
    tickers = sorted(by_t)
    rng = random.Random(seed)
    out = {"v1": [], "v2": [], "diff": []}
    if not tickers:
        return out
    for _ in range(reps):
        draw = []
        for _ in tickers:
            draw.extend(by_t[rng.choice(tickers)])
        s1, s2 = range_skill(draw, "v1"), range_skill(draw, "v2")
        if s1 is None or s2 is None:
            continue
        out["v1"].append(s1)
        out["v2"].append(s2)
        out["diff"].append(s2 - s1)
    return out


def coverage_bootstrap(pairs, name, reps=DEFAULT_REPS,
                       seed=DEFAULT_SEED, by="as_of"):
    """Block-bootstrap draws of the in-range rate of `name`
    (cutoff blocks by default). Empty list when there are no pairs."""
    by_t = {}
    for p in pairs:
        by_t.setdefault(p[by], []).append(p)
    keys = sorted(by_t)
    rng = random.Random(seed)
    out = []
    if not keys:
        return out
    for _ in range(reps):
        draw = []
        for _ in keys:
            draw.extend(by_t[rng.choice(keys)])
        out.append(sum(p["in_" + name] for p in draw) / len(draw))
    return out


def percentile_ci(draws, level=CI_LEVEL):
    if not draws:
        return None, None
    d = sorted(draws)
    a = (1 - level) / 2
    lo = d[int(a * len(d))]
    hi = d[min(len(d) - 1, int((1 - a) * len(d)))]
    return lo, hi


def verdict(n, n_tickers, ci_lo):
    if n < MIN_ROWS or n_tickers < MIN_TICKERS or ci_lo is None:
        return "INSUFFICIENT"
    return "ADOPT" if ci_lo > 0 else "DO NOT ADOPT"


def evaluate(pairs, reps=DEFAULT_REPS, seed=DEFAULT_SEED):
    res = {}
    for h in HORIZONS:
        hp = [p for p in pairs if p["horizon"] == h]
        tick = {p["ticker"] for p in hp}
        draws = block_bootstrap(hp, reps, seed)
        cell = {"n": len(hp), "tickers": len(tick),
                "naive_is": (sum(p["is_naive"] for p in hp) / len(hp)
                             if hp else None)}
        for name in ("v1", "v2"):
            lo, hi = percentile_ci(draws[name])
            cell[name] = {
                "mean_is": (sum(p["is_" + name] for p in hp) / len(hp)
                            if hp else None),
                "coverage": (sum(p["in_" + name] for p in hp) / len(hp)
                             if hp else None),
                "range_skill": range_skill(hp, name),
                "ci": [lo, hi],
                "verdict": verdict(len(hp), len(tick), lo)}
        cdraws = block_bootstrap(hp, reps, seed, by="as_of")
        cell["cutoffs"] = len({p["as_of"] for p in hp})
        cell["cutoff_cluster"] = {}
        for name in ("v1", "v2"):
            clo, chi = percentile_ci(cdraws[name])
            vlo, vhi = percentile_ci(coverage_bootstrap(
                hp, name, reps, seed))
            cell["cutoff_cluster"][name] = {
                "skill_ci": [clo, chi], "coverage_ci": [vlo, vhi]}
        dlo, dhi = percentile_ci(cdraws["diff"])
        cell["cutoff_cluster"]["v2_minus_v1_ci"] = [dlo, dhi]
        lo, hi = percentile_ci(draws["diff"])
        cell["v2_minus_v1_skill"] = {
            "point": (None if not hp else
                      (range_skill(hp, "v2") or 0) -
                      (range_skill(hp, "v1") or 0)),
            "ci": [lo, hi], "draws": len(draws["diff"])}
        res[h] = cell
    return res


# --------------------------------------------------------------- output
def _f(v, nd=3):
    return "n/a" if v is None else ("%.*f" % (nd, v))


def render(res, n_captures, gaps):
    L = ["#594 adoption test: frozen v2 vs retired v1 (RangeSkill, "
         "Winkler 80%)",
         "captures scored: %d" % n_captures,
         "CI: block bootstrap by ticker, 95%%, percentile (cutoff-cluster "
         "CI shown alongside). "
         "INSUFFICIENT below %d rows or %d tickers." % (MIN_ROWS,
                                                        MIN_TICKERS),
         "", "ADOPTION CRITERION: " + CRITERION, ""]
    for h in HORIZONS:
        c = res[h]
        L.append("%s: n=%d rows, %d tickers, naive IS %s"
                 % (h, c["n"], c["tickers"], _f(c["naive_is"], 2)))
        for name, label in (("v2", "v2 (frozen)"), ("v1", "v1 (retired)")):
            x = c[name]
            L.append("  %-12s IS %s  coverage %s  RangeSkill %s  "
                     "CI [%s, %s]  -> %s"
                     % (label, _f(x["mean_is"], 2), _f(x["coverage"]),
                        _f(x["range_skill"]), _f(x["ci"][0]),
                        _f(x["ci"][1]), x["verdict"]))
        d = c["v2_minus_v1_skill"]
        L.append("  v2 minus v1 RangeSkill %s  CI [%s, %s]"
                 % (_f(d["point"]), _f(d["ci"][0]), _f(d["ci"][1])))
        cc = c["cutoff_cluster"]
        L.append("  cutoff-cluster CI (%d cutoffs; reported next to the "
                 "ticker CI, never replaces it):" % c["cutoffs"])
        for name, label in (("v2", "v2"), ("v1", "v1")):
            x = cc[name]
            L.append("    %s RangeSkill [%s, %s]  coverage [%s, %s]"
                     % (label, _f(x["skill_ci"][0]),
                        _f(x["skill_ci"][1]), _f(x["coverage_ci"][0]),
                        _f(x["coverage_ci"][1])))
        L.append("    v2 minus v1 [%s, %s]"
                 % (_f(cc["v2_minus_v1_ci"][0]),
                    _f(cc["v2_minus_v1_ci"][1])))
    L.append("")
    for g in gaps:
        L.append("gap: " + g)
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.
                                 RawDescriptionHelpFormatter)
    ap.add_argument("--captures", nargs="+", required=True)
    ap.add_argument("--min-cell", type=int, default=48)
    ap.add_argument("--reps", type=int, default=DEFAULT_REPS)
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--json", default=None, help="write results JSON")
    a = ap.parse_args(argv)
    caps = find_captures(a.captures, a.min_cell)
    pairs, gaps = score_rows(caps)
    res = evaluate(pairs, a.reps, a.seed)
    print(render(res, len(caps), gaps))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump({"criterion": CRITERION, "captures": len(caps),
                       "results": res, "gaps": gaps}, f, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
