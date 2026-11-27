"""Counts-only check of the round-74 section-3 bias definition on ledger captures.

Descriptive. No scoring, no band replay, no keep rule, no verdict. Prints counts only.
Definition (docs/round74_macro_event_bias_definitions.md, accepted by Moos in round 75):
  AAR_sum(h) = sum of index AAR(o) for o in [max(c+1,-2), min(c+S_h,2)], c = cutoff offset
  cap        = 0.25 x W_h, W_h = frozen v2 half-width = (range_high_pct - range_low_pct) / 2 (pct points)
  bias       = sign(AAR_sum) x min(|AAR_sum|, cap)
  point in time: scheduled events use the full window; special events only for c >= 0;
                 budget events count as scheduled only if published before the capture; no
                 publication date is on file, so budget is treated as special (c >= 0).
  AAR per event type comes only from events of the same type whose window ends before this
  event's window starts (expanding, no look-ahead). No prior events -> bias 0 (counted).
  Overlap (capture in several windows): the term with the largest |AAR_sum| is kept, then capped.
Release rule: default 'before' (session 0 = the event date's session).
"""
import argparse
import importlib.util
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("macro_event_study", os.path.join(HERE, "macro_event_study.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

CAP_FRAC = 0.25
SCHEDULED = {"cbe_scheduled"}


def half_width(row):
    return (row["range_high_pct"] - row["range_low_pct"]) / 2.0


def cutoff_index(dates, as_of):
    """Index of the last return date <= as_of (the capture's cutoff session), or None."""
    k = None
    for i, d in enumerate(dates):
        if d <= as_of:
            k = i
        else:
            break
    return k


def prior_aar(evs, k, offsets=M.OFFSETS):
    """Mean AAR by offset over same-type events whose window (s0+2) ends before evs[k]'s window (s0-2)."""
    me = evs[k]
    if me["s0"] is None:
        return None
    pool = [x for j, x in enumerate(evs) if j != k and x["ab"] is not None and x["event"]["type"] == me["event"]["type"]
            and x["s0"] + 2 < me["s0"] - 2]
    if not pool:
        return None
    return {o: sum(x["ab"][o] for x in pool) / len(pool) for o in offsets}


def capture_bias(row, c_idx, evs, aars):
    """Return (bias_pct, info) for one ledger row. bias in percent points; info for the counts."""
    S = row["sessions"]
    best = None
    for k, x in enumerate(evs):
        if x["s0"] is None:
            continue
        c = c_idx - x["s0"]
        if not -2 <= c <= 2:
            continue
        typ = x["event"]["type"]
        if typ not in SCHEDULED and c < 0:
            continue                      # extraordinary: not knowable before session 0
        aar = aars[k]
        if aar is None:
            cand = (0.0, typ, True)
        else:
            lo, hi = max(c + 1, -2), min(c + S, 2)
            tot = sum(aar[o] for o in range(lo, hi + 1)) * 100.0 if lo <= hi else 0.0
            cand = (tot, typ, False)
        if best is None or abs(cand[0]) > abs(best[0]):
            best = cand
    if best is None:
        return None
    tot, typ, noaar = best
    cap = CAP_FRAC * half_width(row)
    capped = abs(tot) > cap
    bias = (1 if tot > 0 else -1 if tot < 0 else 0) * min(abs(tot), cap)
    return bias, {"type": typ, "capped": capped, "no_prior": noaar}


def run(series, events, rows, rule="before"):
    evs = M.event_abnormals(series, events, rule)
    dates = [d for d, _ in M.log_returns(series)]
    aars = [prior_aar(evs, k) for k in range(len(evs))]
    out = {"n_captures": len(rows), "n_in_window": 0, "n_capped": 0, "n_no_prior_aar": 0,
           "by_type_horizon": {}}
    for row in rows:
        ci = cutoff_index(dates, row["as_of"])
        if ci is None:
            continue
        res = capture_bias(row, ci, evs, aars)
        if res is None:
            continue
        bias, info = res
        out["n_in_window"] += 1
        out["n_capped"] += info["capped"]
        out["n_no_prior_aar"] += info["no_prior"]
        key = "%s|%s" % (info["type"], row["horizon"])
        cell = out["by_type_horizon"].setdefault(key, {"n": 0, "n_capped": 0, "n_bias_pos": 0, "n_bias_neg": 0, "n_bias_zero": 0})
        cell["n"] += 1
        cell["n_capped"] += info["capped"]
        cell["n_bias_pos" if bias > 0 else "n_bias_neg" if bias < 0 else "n_bias_zero"] += 1
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--series", default="evaluation/index_regime/EGX30_mubasher_close.csv")
    ap.add_argument("--calendar", default="evaluation/macro_event/calendar_primary.json")
    ap.add_argument("--ledger", default="ledger/ledger.json")
    ap.add_argument("--release-rule", choices=["before", "page_time", "after"], default="before")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    cal = json.load(open(a.calendar))
    rows = json.load(open(a.ledger))["forecasts_detail"]
    res = {"definition": "docs/round74_macro_event_bias_definitions.md", "release_rule": a.release_rule,
           "cap": "0.25 x frozen v2 half-width", "counts": run(M.load_series(a.series), cal["events"], rows, a.release_rule)}
    txt = json.dumps(res, indent=1)
    if a.json:
        open(a.json, "w").write(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()
