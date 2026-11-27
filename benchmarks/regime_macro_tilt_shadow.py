"""Round 78: regime macro tilt shadow scaffold (stdlib). DESCRIPTIVE, counts only.

Design and pre-registration: docs/round78_regime_macro_tilt_design.md.
No verdict word or key. No statistic is computed here: this scaffold validates
macro rows (every value sourced, point in time) and reports counts of captures
that would have a usable regime. Frozen v2 values and scripts/ensemble.py are
never touched.
"""
import argparse
import csv
import json
import math

REQUIRED = ("value", "observed_date", "published_date", "source_url", "source_name")
REGIME_LABELS = ("tightening", "easing", "hold")


def load_rows(path):
    """Return (rows, n_rejected). A row is rejected when a required field is empty or the value is not finite."""
    rows, rejected = [], 0
    for r in csv.DictReader(open(path)):
        if any(not (r.get(k) or "").strip() for k in REQUIRED):
            rejected += 1
            continue
        try:
            v = float(r["value"])
        except ValueError:
            rejected += 1
            continue
        if not math.isfinite(v):
            rejected += 1
            continue
        rows.append({"value": v, "observed_date": r["observed_date"], "published_date": r["published_date"],
                     "source_url": r["source_url"], "source_name": r["source_name"]})
    return rows, rejected


def point_in_time(rows, as_of):
    """Latest row (by observed_date, then published_date) whose published_date <= as_of; None if none."""
    ok = [r for r in rows if r["published_date"] <= as_of]
    if not ok:
        return None
    return max(ok, key=lambda r: (r["observed_date"], r["published_date"]))


def usable_decision(d):
    """A decision is usable only with a finite numeric change_bps (not bool, not NaN/Inf) and a source."""
    c = d.get("change_bps")
    if isinstance(c, bool) or not isinstance(c, (int, float)) or not math.isfinite(c):
        return False
    return all(isinstance(d.get(k), str) and d.get(k).strip() for k in ("published_date", "source_url", "source_name"))


def load_decisions(path):
    """Return (usable decisions, n_rejected) from a JSON list."""
    raw = json.load(open(path))
    ok = [d for d in raw if usable_decision(d)]
    return ok, len(raw) - len(ok)


def regime_from_decisions(decisions, as_of):
    """decisions: list of dicts {published_date, change_bps, source_url, source_name}.
    Decisions are date-only (release time unknown), so one counts only from the NEXT session:
    eligible when published_date is strictly before as_of. Unusable decisions are ignored."""
    ok = [d for d in decisions if usable_decision(d) and d["published_date"] < as_of]
    if not ok:
        return None
    last = max(ok, key=lambda d: d["published_date"])
    c = last["change_bps"]
    return "tightening" if c > 0 else "easing" if c < 0 else "hold"


def counts(ledger_rows, decisions):
    out = {"n_captures": len(ledger_rows), "n_with_regime": 0, "n_without_regime": 0, "by_regime_horizon": {}}
    for row in ledger_rows:
        reg = regime_from_decisions(decisions, row["as_of"])
        if reg is None:
            out["n_without_regime"] += 1
            continue
        out["n_with_regime"] += 1
        cell = out["by_regime_horizon"].setdefault("%s|%s" % (reg, row["horizon"]), {"n": 0, "dates": set()})
        cell["n"] += 1
        cell["dates"].add(row["as_of"])
    for cell in out["by_regime_horizon"].values():
        cell["n_cutoff_dates"] = len(cell.pop("dates"))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ledger", default="ledger/ledger.json")
    ap.add_argument("--decisions", help="JSON list of {published_date, change_bps}; absent = no macro series")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    rows = json.load(open(a.ledger))["forecasts_detail"]
    decisions, n_rej = load_decisions(a.decisions) if a.decisions else ([], 0)
    res = {"n_decisions_rejected": n_rej, "design": "docs/round78_regime_macro_tilt_design.md", "macro_series": "present" if decisions else "none",
           "counts": counts(rows, decisions)}
    txt = json.dumps(res, indent=1)
    if a.json:
        open(a.json, "w").write(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()
