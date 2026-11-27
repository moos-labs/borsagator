"""Round 69 (a): sentiment direction vote scorer (stdlib). DESCRIPTIVE only.

Pre-registration: docs/round69_sentiment_vote_prereg.md (committed before this
scorer ran on any ledger row). No verdict word or key. Below the 30-date gate
the scorer prints counts only.
"""
import argparse
import json
import random

HORIZONS = ("day", "week")
GATE_DATES = 30
B_DRAWS = 2000
SEED = 69
MIN_RANK_DATE = 6


def _sent(f):
    return (f.get("families") or {}).get("sentiment")


def eligible(f):
    s = _sent(f)
    return (f.get("status") == "matured" and f.get("dividend_gap") is None
            and f.get("horizon") in HORIZONS and s not in (None, 0)
            and f.get("realized_direction") in ("up", "down"))


def sign_votes(rows):
    """[(as_of, horizon, agree)] for Arm 1."""
    out = []
    for f in rows:
        if eligible(f):
            vote = "up" if _sent(f) > 0 else "down"
            out.append((f["as_of"], f["horizon"], vote == f["realized_direction"]))
    return out


def rank_votes(rows):
    """[(as_of, horizon, agree)] for Arm 2: terciles within date+horizon."""
    groups = {}
    for f in rows:
        if (f.get("status") != "invalid" and f.get("dividend_gap") is None
                and f.get("horizon") in HORIZONS and _sent(f) is not None):
            groups.setdefault((f["as_of"], f["horizon"]), []).append(f)
    out = []
    for (d, h), g in sorted(groups.items()):
        n = len(g)
        if n < MIN_RANK_DATE:
            continue
        g = sorted(g, key=lambda f: (_sent(f), f["ticker"]))
        k = n // 3
        for side, sel in (("down", g[:k]), ("up", g[n - k:])):
            for f in sel:
                if (f.get("status") == "matured"
                        and f.get("realized_direction") in ("up", "down")):
                    out.append((d, h, side == f["realized_direction"]))
    return out


def gate_dates(rows):
    by = {h: set() for h in HORIZONS}
    for f in rows:
        if eligible(f):
            by[f["horizon"]].add(f["as_of"])
    return by, len(by["day"] & by["week"])


def boot_lower(votes, draws=B_DRAWS, seed=SEED):
    groups = {}
    for d, a in votes:
        groups.setdefault(d, []).append(a)
    keys = sorted(groups)
    if not keys:
        return None, None
    rng = random.Random(seed)
    vals = []
    for _ in range(draws):
        tot = n = 0
        for _k in keys:
            g = groups[rng.choice(keys)]
            tot += sum(g)
            n += len(g)
        if n:
            vals.append(tot / n)
    vals.sort()
    return vals[int(0.025 * (len(vals) - 1))], vals[int(round(0.975 * (len(vals) - 1)))]


def pass_leg(res):
    """Pre-registered leg: CI lower bound > 0.5 and n_dates >= 30, both horizons."""
    return all(res[h]["ci95"][0] is not None and res[h]["ci95"][0] > 0.5
               and res[h]["n_dates"] >= GATE_DATES for h in HORIZONS)


def score(rows):
    by, both = gate_dates(rows)
    out = {"dates_day": len(by["day"]), "dates_week": len(by["week"]),
           "dates_with_both": both, "gate_required": GATE_DATES,
           "gate_reached": both >= GATE_DATES}
    if not out["gate_reached"]:
        return out
    arms = {"sign_vote": sign_votes(rows), "rank_vote": rank_votes(rows)}
    for name, votes in arms.items():
        res = {}
        for h in HORIZONS:
            v = [(d, a) for d, hh, a in votes if hh == h]
            lo, hi = boot_lower(v)
            res[h] = {"n": len(v), "n_dates": len({d for d, _ in v}),
                      "agree": sum(a for _, a in v),
                      "agree_share": (sum(a for _, a in v) / len(v)) if v else None,
                      "ci95": [lo, hi]}
        res["lower_gt_0.5_both"] = pass_leg(res)
        out[name] = res
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ledger", default="ledger/ledger.json")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    res = score(json.load(open(a.ledger))["forecasts_detail"])
    txt = json.dumps(res, indent=1)
    if a.json:
        open(a.json, "w").write(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()
