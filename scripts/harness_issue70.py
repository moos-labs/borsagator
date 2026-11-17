#!/usr/bin/env python3
"""Issue #70 harness -- Delta module: what changed since your last
sweep of this ticker.

Usage: python3 harness_issue70.py <repo-path> <archive-path>
  repo-path:    checkout of moos-labs/borsagator (the tree under test)
  archive-path: checkout of the archive branch (real sweep dirs --
                 the golden pairs are read from it, never from
                 Actions logs or artifacts)

Exit 0 = all checks pass, 1 = any check fails. On the pristine tree
(no scripts/delta.py) the harness FAILS: the module is absent, and
the naive-diff control (raw deltas of Pair A with no decomposition)
also fails the Pair A assertions -- proving the assertions
discriminate. On the fixed tree every case passes.

Golden values below were re-derived from the live archive at
implementation time (archive HEAD 97f06ba); where they differ from
the flat/deep scoping docs the live value is asserted and the drift
is named in the check detail.
"""

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

FAILS = []

A16 = "sweeps/2026-11-16"
A15 = "sweeps/2026-11-15"
A13 = "sweeps/2026-11-13"

PAIR_A_PREV = f"{A16}/085806__sweep-lite-poul-ca__run43829283730"
PAIR_A_CUR = f"{A16}/141124__sweep-lite-poul-ca__run43875894633"
PAIR_B_PREV = f"{A16}/050559__sweep-lite-poul-ca-market-egx__run43805931446"
PAIR_C1_PREV = f"{A15}/074752__sweep-lite-poul-ca__run43688673389"
PAIR_C1_CUR = f"{A15}/140509__sweep-lite-poul-ca-market-egx__run43720903619"
PAIR_C2_PREV = f"{A13}/095050__sweep-lite-poul-ca-market-egx__run43402572619"
PAIR_C2_CUR = f"{A15}/141558__sweep-lite-poul-ca-market-egx__run43721738392"
TRIPWIRE_CUR = f"{A15}/132459__sweep-lite-poul-ca-market-egx__run43717383224"
WORKER_DIR = ("worker-runs/2026-11-17/"
              "020416__run-news-disclosure-poul-ca__w5-news-egx-002")

# Model path (#68 Report Models): the three golden pairs whose sweeps
# both carry a report-model.json (schema borsagator-report-model/1).
MODEL_PAIRS = [
    ("Pair A", PAIR_A_PREV, PAIR_A_CUR),
    ("Pair C1", PAIR_C1_PREV, PAIR_C1_CUR),
    ("Pair C2", PAIR_C2_PREV, PAIR_C2_CUR),
]
MODEL_SCHEMA = "borsagator-report-model/1"
# The ledger pin every golden model carries (archive 647fdfbc).
PIN_COUNTS = {"dividend_adjusted": 0, "excluded_flagged": 4,
              "forecasts": 63, "invalid": 3, "matured": 9,
              "pending": 51, "sweeps": 44,
              "sweeps_with_ensemble": 23}
PIN_SHA = ("0b4830e811c0cf2348c5beb67e77ef916152ca9e564a815505a5ddeb"
           "4b602a4c")


def check(name, ok, detail=""):
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" +
          (f" -- {detail}" if detail else ""))
    if not ok:
        FAILS.append(name)


def approx(a, b, tol=0.011):
    return a is not None and b is not None and abs(a - b) <= tol


def load_delta_module(repo):
    path = os.path.join(repo, "scripts", "delta.py")
    if not os.path.exists(path):
        return None
    spec = importlib.util.spec_from_file_location("borsagator_delta",
                                                  path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ------------------------------------------------- model-path helpers

def strip_calibration(d):
    """Deep copy of a delta with the ledger-pin-carrying fields
    removed: the whole calibration section, the weights section's
    ledger_counts, and the raw path's "ledger counts not carried"
    suffix on the weights note.

    The model path is REQUIRED to differ from the raw path exactly
    here: the raw ensembles carry no ledger counts (counts None),
    while the model carries the pinned counts -- that is the point
    of the model path (re-proof 2026-11-17: "the delta simply never
    looks at it"). A converter that reproduced the raw calibration
    section byte-for-byte would have to discard the pin, i.e. it
    would repeat the non-consumption the re-proof caught. So the
    model-path bar is: byte-identical everywhere EXCEPT these
    fields, which are asserted separately (calibration_failures)
    against the exact pinned values.
    """
    import copy
    out = copy.deepcopy(d)
    sec = out.get("sections") or {}
    sec.pop("calibration", None)
    weights = sec.get("weights") or {}
    weights.pop("ledger_counts", None)
    note = weights.get("note") or ""
    weights["note"] = note.replace(
        "; ledger counts not carried by raw ensembles "
        "(see #68 ledger_pin)", "")
    return out


def calibration_failures(d, d_raw, expect_129):
    """Assertions on the model path's calibration section: the exact
    pinned counts, and the weights fields equal to the raw path's
    (minus the raw path's "ledger counts not carried" suffix -- the
    model path has the pin, so it carries no such suffix). Returns
    the list of failed assertion names (empty = pass).

    Note the weights expectations are deliberately relative to the
    raw path, not absolute: Pair A pins the weights file
    (0b4830e8... both sides, source ledger -> ledger, unchanged),
    but Pairs C1/C2 predate applied_weights (#93/#94): their
    ensembles carry no applied_weights at all, so the file SHA is
    None on both sides and the source moves (builtin -> ledger on
    C1, absent -> ledger on C2) -- "weights changed" is the correct
    model-path answer there, and the converter reproduces it
    exactly. Asserting the Pair A pin on C1/C2 would be asserting
    the wrong history.
    """
    bad = []
    sec = (d or {}).get("sections") or {}
    raw_sec = (d_raw or {}).get("sections") or {}
    cal = sec.get("calibration") or {}
    counts = cal.get("ledger_counts") or {}
    for key, value in PIN_COUNTS.items():
        entry = counts.get(key) or {}
        if entry.get("from") != value or entry.get("to") != value:
            bad.append(f"ledger count {key} pinned {value} both sides")
    if set(counts) != set(PIN_COUNTS):
        bad.append("ledger counts carry exactly the pinned keys")
    if cal.get("ledger_counts_source") != (
            "report-model ledger_pin (borsagator-report-model/1)"):
        bad.append("ledger_counts_source names the report-model pin")
    weights = sec.get("weights") or {}
    raw_weights = raw_sec.get("weights") or {}
    sha = weights.get("weights_file_sha256") or {}
    raw_sha = raw_weights.get("weights_file_sha256") or {}
    if sha.get("from") != raw_sha.get("from") \
            or sha.get("to") != raw_sha.get("to"):
        bad.append("weights_file_sha256 matches the raw path "
                   f"({raw_sha})")
    if weights.get("weights_source") != raw_weights.get("weights_source"):
        bad.append("weights_source matches the raw path")
    wcounts = weights.get("ledger_counts") or {}
    if (wcounts.get("from") or {}).get("matured") != 9 or \
            (wcounts.get("to") or {}).get("matured") != 9:
        bad.append("weights ledger_counts carry the pin (matured 9)")
    note = cal.get("note") or ""
    if expect_129:
        if "#129" not in note:
            bad.append("calibration note flags unadjusted ledger rows "
                       "(#129) on the ex-date pair")
    else:
        if "#129" in note or "not carried" in note:
            bad.append("calibration note carries no #129 flag and no "
                       "'not carried' suffix off the ex-date window")
    expected_note = (raw_weights.get("note") or "").replace(
        "; ledger counts not carried by raw ensembles "
        "(see #68 ledger_pin)", "")
    if (weights.get("note") or "") != expected_note:
        bad.append("weights note matches the raw path's note minus "
                   "its 'not carried' suffix")
    return bad


# ------------------------------------------------------- Pair A assertions

def pair_a_failures(d):
    """Assertions from scoping section 7.1, against a delta dict.
    Returns the list of failed assertion names (empty = pass)."""
    bad = []
    sec = (d or {}).get("sections") or {}
    price = sec.get("price") or {}
    delta = price.get("delta") or {}
    if not approx(delta.get("base_pct"), -19.80):
        bad.append("price raw -19.80%")
    if not approx(delta.get("mechanical_pct"), -23.69):
        bad.append("price mechanical -23.69%")
    if not approx(delta.get("residual_pct"), 3.89):
        bad.append("price residual +3.89% (headline, not raw)")
    if not price.get("flagged"):
        bad.append("price flagged")
    egx = (price.get("price_series_last") or {}).get(
        "egx-data/egxpy_poul.csv") or {}
    if not approx((egx.get("from") or {}).get("last_close"), 10.0):
        bad.append("egx prev close 10.00")
    if not approx((egx.get("to") or {}).get("last_close"), 8.02):
        bad.append("egx cur close 8.02")
    if not approx((egx.get("from") or {}).get("last_volume"), 32750060.0):
        bad.append("egx prev volume 32,750,060")
    if not approx((egx.get("to") or {}).get("last_volume"), 32041362.0):
        bad.append("egx cur volume 32,041,362")
    if not approx(egx.get("volume_delta_pct"), -2.16):
        bad.append("egx volume delta -2.16%")
    if not (price.get("witness_stale") or {}).get("cur", {}).get("stale"):
        bad.append("witness staleness flagged (common 2026-11-12 vs "
                   "base 2026-11-16, status 'agree')")
    day = (sec.get("horizons") or {}).get("day") or {}
    if not approx((day.get("expected_move_pct") or {}).get("delta_pp"),
                  16.46):
        bad.append("day delta +16.46 pp")
    if not day.get("ex_date_decomposed"):
        bad.append("day ex_date_decomposed")
    if not approx(day.get("mechanical_pp"), -23.69):
        bad.append("day mechanical_pp -23.69")
    if not approx((day.get("implied_target_price") or {}).get("from"),
                  10.225):
        bad.append("day implied target prev 10.225")
    if not approx((day.get("implied_target_price") or {}).get("to"),
                  9.5205):
        bad.append("day implied target cur 9.5205")
    week = (sec.get("horizons") or {}).get("week") or {}
    month = (sec.get("horizons") or {}).get("month") or {}
    if not approx((week.get("expected_move_pct") or {}).get("delta_pp"),
                  17.36):
        bad.append("week delta +17.36 pp")
    if not approx((month.get("expected_move_pct") or {}).get("delta_pp"),
                  17.91):
        bad.append("month delta +17.91 pp")
    if not (week.get("direction_flip") and month.get("direction_flip")):
        bad.append("week+month direction flips recorded")
    pf = (sec.get("family_scores") or {}).get("price-forecast") or {}
    if not pf.get("flip"):
        bad.append("price-forecast flip")
    if pf.get("cause") != "ex-date base change":
        bad.append("price-forecast flip cause is ex-date base change")
    if not approx(pf.get("delta"), 0.617):
        bad.append("price-forecast delta +0.617")
    sent = (sec.get("family_scores") or {}).get("sentiment") or {}
    if sent.get("flagged"):
        bad.append("sentiment -0.015 NOT flagged (below 0.10)")
    if not approx(sent.get("delta"), -0.015):
        bad.append("sentiment delta -0.015")
    tech = (sec.get("family_scores") or {}).get("technicals") or {}
    fund = (sec.get("family_scores") or {}).get("fundamentals") or {}
    if tech.get("changed") or fund.get("changed"):
        bad.append("technicals/fundamentals unchanged")
    agent = (sec.get("family_scores") or {}).get("agent") or {}
    if agent.get("from") is not None or agent.get("to") is not None:
        bad.append("agent null on both sides is 'no data', never 0")
    ex = d.get("ex_date") or {}
    if not ex.get("in_window"):
        bad.append("ex-date in window")
    if ex.get("mechanical_pct") is None or not approx(
            ex.get("mechanical_pct"), -23.69):
        bad.append("ex mechanical_pct -23.69")
    if ex.get("kronos_rescaled"):
        bad.append("kronos_rescaled false (rescale did not apply)")
    if "#130" not in (ex.get("flag") or ""):
        bad.append("ex flag links #130")
    ca = sec.get("corporate_actions") or {}
    if ca.get("changed"):
        bad.append("corporate actions unchanged (dedup-aware)")
    if len(ca.get("added", [])) or len(ca.get("removed", [])):
        bad.append("corporate actions no added/removed")
    weights = sec.get("weights") or {}
    if weights.get("changed"):
        bad.append("weights unchanged")
    risk = sec.get("risk") or {}
    if (risk.get("level") or {}).get("from") != "shock" or \
            (risk.get("level") or {}).get("to") != "shock":
        bad.append("risk level shock -> shock")
    # Live archive: 085806 has 5 events, 141124 has 3 (the deep
    # scoping's "5 events both sides" is wrong -- 2 removed).
    if len(risk.get("events_removed", [])) != 2:
        bad.append("risk events removed == 2 (live count, not 0)")
    if len(risk.get("events_added", [])) != 0:
        bad.append("risk events added == 0")
    news = (sec.get("news") or {}).get("news") or {}
    if (news.get("news_count") or {}).get("from") != 22 or \
            (news.get("news_count") or {}).get("to") != 22:
        bad.append("news count 22 -> 22")
    if len(news.get("added", [])) != 2 or len(news.get("removed", [])) != 2:
        bad.append("news added == 2 / removed == 2 (after re-keying)")
    if len(news.get("rekeyed", [])) != 1:
        bad.append("news rekeyed == 1 (same title+date, key type moved)")
    if news.get("unchanged") != 19:
        bad.append("news unchanged == 19")
    disc = (sec.get("news") or {}).get("disclosures") or {}
    if disc.get("unchanged") != 11 or disc.get("changed"):
        bad.append("disclosures 11 -> 11 unchanged")
    tools = sec.get("tools") or {}
    status = tools.get("status_changed", [])
    if not any(s.get("tool") == "finbert-tone" for s in status):
        bad.append("tools: finbert-tone failure -> success recorded")
    if (d.get("pair_invalid") is not None
            or d.get("first_sweep") or d.get("delta_unavailable")):
        bad.append("pair is a normal paired delta (not invalid / "
                   "first / unavailable)")
    return bad


def naive_pair_a():
    """A naive diff of Pair A: raw deltas only, no decomposition, no
    ex-date handling, no re-keying, no witness flag. The harness
    asserts the Pair A checks FAIL on this -- proving they
    discriminate."""
    return {
        "delta_version": 1, "ticker": "POUL.CA",
        "current_sweep": "sweeps/2026-11-16/141124__x",
        "previous_sweep": "sweeps/2026-11-16/085806__x",
        "pair_rule": "same ticker + same job shape + most recent",
        "pair_invalid": None, "shape_warning": None,
        "sections": {
            "price": {"changed": True, "flagged": True,
                      "delta": {"base_pct": -19.8,
                                "mechanical_pct": None,
                                "residual_pct": None},
                      "price_series_last": {},
                      "witness_stale": {"cur": {"stale": False}}},
            "horizons": {
                "day": {"changed": True,
                        "expected_move_pct": {"from": 2.25, "to": 18.71,
                                              "delta_pp": 16.46},
                        "ex_date_decomposed": False,
                        "mechanical_pp": None,
                        "implied_target_price": {}},
                "week": {"changed": True,
                         "expected_move_pct": {"from": -0.63,
                                               "to": 16.73,
                                               "delta_pp": 17.36},
                         "direction_flip": True},
                "month": {"changed": True,
                          "expected_move_pct": {"from": -1.55,
                                                "to": 16.36,
                                                "delta_pp": 17.91},
                          "direction_flip": True}},
            "family_scores": {
                "price-forecast": {"from": -0.222, "to": 0.395,
                                   "delta": 0.617, "flip": True,
                                   "cause": None},
                "sentiment": {"from": -0.086, "to": -0.101,
                              "delta": -0.015, "flagged": False},
                "technicals": {"from": 0.297, "to": 0.297,
                               "changed": False},
                "fundamentals": {"from": 0.4, "to": 0.4,
                                 "changed": False},
                "agent": {"from": None, "to": None}},
            "weights": {"changed": False},
            "corporate_actions": {"changed": False, "added": [],
                                  "removed": []},
            "risk": {"changed": False,
                     "level": {"from": "shock", "to": "shock"},
                     "events_added": [], "events_removed": []},
            "news": {"news": {"news_count": {"from": 22, "to": 22},
                              "added": [{}, {}, {}], "removed": [{}, {}, {}],
                              "rekeyed": [], "unchanged": 19},
                     "disclosures": {"unchanged": 11, "changed": False}},
            "tools": {"status_changed": []},
        },
        "ex_date": {"in_window": False, "ex_date": None,
                    "mechanical_pct": None, "kronos_rescaled": False,
                    "flag": None},
        "first_sweep": False,
    }


# ------------------------------------------------------------- fake trees

def _copy_sweep_minimal(src, dst):
    """Copy the files the delta adapter reads: digest, ensemble,
    manifest, registry, egx-data CSV, news-disclosure feed."""
    os.makedirs(dst, exist_ok=True)
    for name in ("digest.json", "ensemble.json", "manifest.json",
                 "registry.json"):
        path = os.path.join(src, name)
        if os.path.exists(path):
            shutil.copy2(path, os.path.join(dst, name))
    for sub in ("collected/egx-data", "collected/news-disclosure"):
        src_dir = os.path.join(src, sub)
        if os.path.isdir(src_dir):
            shutil.copytree(src_dir, os.path.join(dst, sub))


def _set_finished(path, finished):
    digest_path = os.path.join(path, "digest.json")
    doc = json.load(open(digest_path))
    doc["finished"] = finished
    json.dump(doc, open(digest_path, "w"), indent=2)


def _set_job(path, job):
    digest_path = os.path.join(path, "digest.json")
    doc = json.load(open(digest_path))
    doc["job"] = job
    json.dump(doc, open(digest_path, "w"), indent=2)


# ------------------------------------------------------------------- main

def main():
    if len(sys.argv) < 3:
        print("usage: harness_issue70.py <repo-path> <archive-path>")
        return 2
    repo, archive = sys.argv[1], sys.argv[2]

    # -- naive control (needs no delta.py): must FAIL Pair A checks.
    naive_bad = pair_a_failures(naive_pair_a())
    check("naive diff of Pair A FAILS the decomposition assertions",
          len(naive_bad) >= 5,
          f"{len(naive_bad)} failing assertions "
          f"({', '.join(naive_bad[:4])})")

    mod = load_delta_module(repo)
    check("scripts/delta.py exists and imports (pristine control)",
          mod is not None,
          "absent -- this is the pristine tree" if mod is None else "")
    if mod is None:
        print(f"\n{len(FAILS)} FAILING -- pristine tree, as expected")
        return 1
    delta = mod

    def pair(prev, cur):
        return delta.delta_pair(os.path.join(archive, prev),
                                os.path.join(archive, cur))

    # -- 1. Pair A golden (ex-date), via the shipped CLI path too.
    d_a = pair(PAIR_A_PREV, PAIR_A_CUR)
    bad = pair_a_failures(d_a)
    check("Pair A golden: decomposed ex-date delta", not bad,
          "; ".join(bad) if bad else "all section 7.1 assertions hold")
    out_json = os.path.join(tempfile.gettempdir(), "h70-pairA.json")
    proc = subprocess.run(
        [sys.executable, os.path.join(repo, "scripts", "delta.py"),
         os.path.join(archive, PAIR_A_PREV),
         os.path.join(archive, PAIR_A_CUR), "--out", out_json],
        capture_output=True, text=True, timeout=120)
    check("delta.py CLI exits 0 on Pair A", proc.returncode == 0,
          proc.stderr.strip()[:200])
    cli = json.load(open(out_json)) if proc.returncode == 0 else {}
    check("CLI output matches in-process delta (byte-identical JSON)",
          json.dumps(cli, sort_keys=True) ==
          json.dumps(d_a, sort_keys=True))
    md_path = out_json[:-5] + ".md"
    check("MD twin written beside the JSON",
          os.path.exists(md_path))
    md_text = open(md_path).read() if os.path.exists(md_path) else ""
    check("MD twin carries the ex-date note, no imperative wording",
          "ex-date" in md_text and not re.search(
              r"\b(buy|sell|hold)\b", md_text, re.I))
    check("delta JSON carries no buy/sell/hold wording (#77 gate)",
          not re.search(r"\b(buy|sell|hold)\b",
                        json.dumps(d_a, ensure_ascii=False), re.I))

    # -- 2. Pair B: resolver must not pair across job shapes.
    check("job shapes differ: sweep-lite vs sweep-lite market=EGX",
          delta.normalize_job_shape("sweep-lite POUL.CA market=EGX")
          != delta.normalize_job_shape("sweep-lite POUL.CA"))
    previous, status, note = delta.resolve_pair(
        archive, "POUL.CA", "sweep-lite POUL.CA",
        os.path.join(archive, PAIR_A_CUR))
    check("resolver picks 085806 for 141124 (not 050559, not 065405)",
          status == "paired" and previous is not None
          and os.path.basename(previous).startswith("085806"),
          f"status={status} previous={previous}")
    d_b = pair(PAIR_B_PREV, PAIR_A_CUR)
    check("explicit cross-shape pair diffs but carries shape_warning",
          d_b.get("shape_warning") is not None
          and "market=EGX" in (d_b.get("shape_warning") or ""))

    # -- 3. Pair C (flat scoping, re-derived from the live archive).
    d_c1 = pair(PAIR_C1_PREV, PAIR_C1_CUR)
    sec = d_c1["sections"]
    day = sec["horizons"]["day"]["expected_move_pct"]
    sent = sec["family_scores"]["sentiment"]
    egx = sec["price"]["price_series_last"]["egx-data/egxpy_poul.csv"]
    check("Pair C1 074752->140509: day +1.22 -> +1.21",
          approx(day["from"], 1.22) and approx(day["to"], 1.21))
    check("Pair C1: sentiment 0.026 -> 0.003",
          approx(sent["from"], 0.026) and approx(sent["to"], 0.003))
    check("Pair C1: egx 10.15 -> 10.00, volume 18.3M -> 32.8M",
          approx(egx["from"]["last_close"], 10.15)
          and approx(egx["to"]["last_close"], 10.0)
          and approx(egx["from"]["last_volume"], 18277604.0)
          and approx(egx["to"]["last_volume"], 32750060.0))
    check("Pair C1 is cross-shape: shape_warning present, and the "
          "resolver would not pair it",
          d_c1.get("shape_warning") is not None)
    previous_c1, status_c1, _ = delta.resolve_pair(
        archive, "POUL.CA", "sweep-lite POUL.CA market=EGX",
        os.path.join(archive, PAIR_C1_CUR))
    check("resolver for 140509 (market=EGX) picks 132459, not 074752",
          status_c1 == "paired" and previous_c1 is not None
          and os.path.basename(previous_c1).startswith("132459"),
          f"status={status_c1} previous={previous_c1}")
    d_c2 = pair(PAIR_C2_PREV, PAIR_C2_CUR)
    sec2 = d_c2["sections"]
    sent2 = sec2["family_scores"]["sentiment"]
    check("Pair C2 095050->141558: sentiment -0.199 -> -0.004",
          approx(sent2["from"], -0.199) and approx(sent2["to"], -0.004))
    check("Pair C2: weights_source absent -> ledger",
          (sec2["weights"]["weights_source"]["from"] is None)
          and sec2["weights"]["weights_source"]["to"] == "ledger")
    check("Pair C2: corporate_actions null -> 2 undated blocks: "
          "dedup-aware, NOT a new dividend (see #92)",
          sec2["corporate_actions"]["changed"] is False
          and sec2["corporate_actions"]["added"] == []
          and sec2["corporate_actions"]["removed"] == []
          and sec2["corporate_actions"]["undated_blocks"]["to"] == 2
          and "#92" in sec2["corporate_actions"]["note"])
    disc2 = sec2["news"]["disclosures"]
    check("Pair C2: disclosures 6 -> 2, latest went backwards "
          "(12 Nov -> 28 Oct) as context, not as the diff",
          (disc2["disclosures_count"]["from"] == 6)
          and (disc2["disclosures_count"]["to"] == 2)
          and (disc2["latest_date"]["from_iso"] or "").startswith(
              "2026-11-12")
          and (disc2["latest_date"]["to_iso"] or "").startswith(
              "2026-10-28"))
    check("Pair C2: risk events 0 -> 2",
          len(sec2["risk"]["events_added"]) == 2)
    # Tripwire: 074752 -> 132459 (COMI leak) is pair_invalid.
    d_trip = pair(PAIR_C1_PREV, TRIPWIRE_CUR)
    problems = (d_trip.get("pair_invalid") or {}).get("problems", [])
    tools_hit = {p["field"].split(":")[-1] for p in problems}
    check("tripwire pair 074752->132459 yields pair_invalid",
          d_trip.get("pair_invalid") is not None
          and {"yahooquery", "egx-data", "financedatabase",
               "news-disclosure"} <= tools_hit,
          f"problems={problems}")
    check("tripwire reads envelope summary.ticker only (metrics "
          "ticker AAPL on backtest tools does not false-fire)",
          pair(PAIR_A_PREV, PAIR_A_CUR).get("pair_invalid") is None)

    # -- 4. First sweep (fake archive root, one sweep only).
    tmp = tempfile.mkdtemp(prefix="h70-")
    try:
        fake = os.path.join(tmp, "archive")
        only = os.path.join(fake, "sweeps", "2026-11-16",
                            os.path.basename(PAIR_A_CUR))
        _copy_sweep_minimal(os.path.join(archive, PAIR_A_CUR), only)
        previous, status, note = delta.resolve_pair(
            fake, "POUL.CA", "sweep-lite POUL.CA", only)
        check("first sweep: resolver reports first_sweep",
              status == "first_sweep" and previous is None, note)
        first = delta.first_sweep_delta(delta.load_sweep_view(only))
        check("first_sweep output: all sections 'no previous sweep'",
              first.get("first_sweep") is True
              and all((s or {}).get("changed") is None
                      for s in first["sections"].values()))

        # -- 5. Worker sweep as the latest same-shape sweep.
        fake2 = os.path.join(tmp, "archive2")
        worker = os.path.join(
            fake2, "worker-runs", "2026-11-17",
            os.path.basename(WORKER_DIR))
        shutil.copytree(os.path.join(archive, WORKER_DIR), worker)
        cur2 = os.path.join(fake2, "sweeps", "2026-11-17",
                            "030000__run-news-disclosure-poul-ca__fake")
        _copy_sweep_minimal(os.path.join(archive, PAIR_A_CUR), cur2)
        _set_job(cur2, "run news-disclosure POUL.CA")
        _set_finished(cur2, "2026-11-17T03:00:00+00:00")
        previous, status, note = delta.resolve_pair(
            fake2, "POUL.CA", "run news-disclosure POUL.CA", cur2)
        check("worker sweep latest: resolver reports delta_unavailable",
              status == "delta_unavailable" and previous is None, note)
        d_w = delta.delta_pair(worker, cur2)
        check("worker sweep as explicit previous side: "
              "delta_unavailable, exit-0 shape",
              d_w.get("delta_unavailable") is not None
              and "#67" in d_w["delta_unavailable"])
        d_w2 = delta.delta_pair(cur2, worker)
        check("worker sweep as current side: delta_unavailable",
              d_w2.get("delta_unavailable") is not None)

        # -- 6. Missing ensemble: skipped in resolution, skip recorded.
        fake3 = os.path.join(tmp, "archive3")
        earlier = os.path.join(fake3, "sweeps", "2026-11-16",
                               os.path.basename(PAIR_A_PREV))
        _copy_sweep_minimal(os.path.join(archive, PAIR_A_PREV), earlier)
        later = os.path.join(fake3, "sweeps", "2026-11-16",
                             "120000__sweep-lite-poul-ca__fake-noens")
        _copy_sweep_minimal(os.path.join(archive, PAIR_A_CUR), later)
        os.remove(os.path.join(later, "ensemble.json"))
        _set_finished(later, "2026-11-16T12:00:00+00:00")
        cur3 = os.path.join(fake3, "sweeps", "2026-11-16",
                            "160000__sweep-lite-poul-ca__fake-cur")
        _copy_sweep_minimal(os.path.join(archive, PAIR_A_CUR), cur3)
        _set_finished(cur3, "2026-11-16T16:00:00+00:00")
        previous, status, note = delta.resolve_pair(
            fake3, "POUL.CA", "sweep-lite POUL.CA", cur3)
        check("ensemble-less sweep skipped in resolution, skip recorded",
              status == "paired" and previous is not None
              and os.path.basename(previous).startswith("085806")
              and "skipped" in note and "120000" in note,
              f"status={status} note={note}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # -- 7. Null handling (synthetic views, no archive needed).
    prev_view = {"ticker": "POUL.CA", "job_shape": "sweep-lite POUL.CA",
                 "ensemble": {"base_price": 10.0, "base_date": "2026-11-15",
                              "family_scores": {"agent": None,
                                                "price-forecast": None},
                              "horizons": {}, "risk": {},
                              "corporate_actions": []},
                 "digest": {"results": []}, "price_series_last": [],
                 "news_items": [], "disclosure_items": [],
                 "news_meta": {}, "ledger_pin": {"counts": None,
                                                 "eligible": {}},
                 "tripwire": []}
    cur_view = dict(prev_view)
    cur_view["ensemble"] = {"base_price": 10.0, "base_date": "2026-11-15",
                            "family_scores": {"agent": None,
                                              "price-forecast": 0.3},
                            "horizons": {}, "risk": {},
                            "corporate_actions": []}
    d_null = delta.compute_delta(prev_view, cur_view)
    pf = d_null["sections"]["family_scores"]["price-forecast"]
    check("null -> value is a flagged shape change, never a flip "
          "from 0",
          pf["flagged"] is True and pf["flip"] is False
          and pf["from"] is None)
    check("agent null on both sides stays 'no data'",
          d_null["sections"]["family_scores"]["agent"]["from"] is None)

    # -- 8. Determinism: re-delta Pair A -> byte-identical JSON.
    again = pair(PAIR_A_PREV, PAIR_A_CUR)
    check("re-delta Pair A is byte-identical",
          json.dumps(again, sort_keys=True)
          == json.dumps(d_a, sort_keys=True))

    # -- 9. Model path: the six golden pairs through model_to_view.
    # The converter is the missing piece from the 2026-11-17
    # re-proof: the raw-path harness passed with all six
    # report-model.json files deleted, because the delta never read
    # them. These checks fail on any tree without model_to_view,
    # and fail (not pass vacuously) when the models are removed.
    has_converter = all(
        callable(getattr(delta, name, None)) for name in
        ("model_to_view", "load_model_view", "delta_pair_models"))
    check("model_to_view + load_model_view + delta_pair_models exist",
          has_converter,
          "absent -- the model path is not implemented on this tree"
          if not has_converter else "")
    if has_converter:
        def mpair(prev, cur):
            return delta.delta_pair_models(
                os.path.join(archive, prev), os.path.join(archive, cur))

        for label, prev, cur in MODEL_PAIRS:
            d_raw = pair(prev, cur)
            try:
                d_model = mpair(prev, cur)
            except Exception as exc:  # noqa: BLE001 - harness reports it
                check(f"model path {label}: converter runs",
                      False, f"raised {type(exc).__name__}: {exc}")
                continue
            check(f"model path {label}: converter runs", True)
            same = (json.dumps(strip_calibration(d_model),
                               sort_keys=True)
                    == json.dumps(strip_calibration(d_raw),
                                  sort_keys=True))
            check(f"model path {label}: delta matches the raw path "
                  f"everywhere except the ledger-pin fields",
                  same,
                  "differs outside calibration/weights-ledger_counts"
                  if not same else "byte-identical outside the pin")
            bad = calibration_failures(d_model, d_raw,
                                       label == "Pair A")
            check(f"model path {label}: calibration carries the "
                  f"pinned counts (63/9/51/3, dividend_adjusted 0)",
                  not bad, "; ".join(bad) if bad else "pin exact")
            if label == "Pair A":
                bad_a = pair_a_failures(d_model)
                check("model path Pair A: the section 7.1 assertions "
                      "hold on the model path too",
                      not bad_a, "; ".join(bad_a) if bad_a else
                      "all section 7.1 assertions hold")

        # Levels ride the view (for #69 / D2); the converter must
        # read them off the model, not re-derive them.
        view_141124 = delta.load_model_view(
            os.path.join(archive, PAIR_A_CUR))
        levels = view_141124.get("levels") or {}
        check("model view carries levels: 141124 support 7.1346 / "
              "resistance 11.5881",
              approx(levels.get("support"), 7.1346)
              and approx(levels.get("resistance"), 11.5881),
              f"levels={levels}")
        view_085806 = delta.load_model_view(
            os.path.join(archive, PAIR_A_PREV))
        levels_prev = view_085806.get("levels") or {}
        check("model view carries levels: 085806 support 9.117 / "
              "resistance 10.758",
              approx(levels_prev.get("support"), 9.117)
              and approx(levels_prev.get("resistance"), 10.758),
              f"levels={levels_prev}")

        # CLI --model path on Pair A, byte-identical to in-process.
        out_model = os.path.join(tempfile.gettempdir(), "h70-pairA-model.json")
        proc_m = subprocess.run(
            [sys.executable, os.path.join(repo, "scripts", "delta.py"),
             "--model",
             os.path.join(archive, PAIR_A_PREV),
             os.path.join(archive, PAIR_A_CUR), "--out", out_model],
            capture_output=True, text=True, timeout=120)
        check("delta.py --model CLI exits 0 on Pair A",
              proc_m.returncode == 0, proc_m.stderr.strip()[:200])
        cli_model = (json.load(open(out_model))
                     if proc_m.returncode == 0 else {})
        check("CLI --model output matches in-process model delta "
              "(byte-identical JSON)",
              json.dumps(cli_model, sort_keys=True)
              == json.dumps(mpair(PAIR_A_PREV, PAIR_A_CUR),
                            sort_keys=True))

        # Guards: wrong schema refused; a missing model refused
        # (never a silent fall-back to the raw path).
        try:
            delta.model_to_view({"schema": "borsagator-report-model/9",
                                 "ticker": "POUL.CA"})
            check("model_to_view refuses a non-/1 schema", False,
                  "accepted a foreign schema")
        except Exception:  # noqa: BLE001 - the refusal is the pass
            check("model_to_view refuses a non-/1 schema", True)
        tmp2 = tempfile.mkdtemp(prefix="h70-model-")
        try:
            no_model = os.path.join(tmp2, "sweep")
            _copy_sweep_minimal(os.path.join(archive, PAIR_A_CUR),
                                no_model)
            try:
                delta.load_model_view(no_model)
                check("load_model_view refuses a sweep with no "
                      "report-model.json", False,
                      "loaded a view with no model")
            except Exception:  # noqa: BLE001 - the refusal is the pass
                check("load_model_view refuses a sweep with no "
                      "report-model.json", True)

            # Negative control: the stripped archive (all six models
            # deleted). The model path MUST fail here -- and the raw
            # path must still pass, proving the raw path cannot see
            # the models and the model section is the discriminator.
            stripped = os.path.join(tmp2, "stripped")
            for rel in (PAIR_A_PREV, PAIR_A_CUR, PAIR_C1_PREV,
                        PAIR_C1_CUR, PAIR_C2_PREV, PAIR_C2_CUR):
                _copy_sweep_minimal(os.path.join(archive, rel),
                                    os.path.join(stripped, rel))
            try:
                delta.delta_pair_models(
                    os.path.join(stripped, PAIR_A_PREV),
                    os.path.join(stripped, PAIR_A_CUR))
                check("stripped archive: model path FAILS with the "
                      "models removed", False,
                      "model delta succeeded with no models present")
            except Exception as exc:  # noqa: BLE001 - failure is pass
                check("stripped archive: model path FAILS with the "
                      "models removed", True,
                      f"{type(exc).__name__}: {exc}")
            d_raw_stripped = delta.delta_pair(
                os.path.join(stripped, PAIR_A_PREV),
                os.path.join(stripped, PAIR_A_CUR))
            check("stripped archive: raw path still passes (it never "
                  "read the models -- the model section is what "
                  "catches this)",
                  not pair_a_failures(d_raw_stripped),
                  "; ".join(pair_a_failures(d_raw_stripped)))
            proc_s = subprocess.run(
                [sys.executable,
                 os.path.join(repo, "scripts", "delta.py"), "--model",
                 os.path.join(stripped, PAIR_A_PREV),
                 os.path.join(stripped, PAIR_A_CUR)],
                capture_output=True, text=True, timeout=120)
            check("stripped archive: delta.py --model CLI exits "
                  "non-zero", proc_s.returncode != 0,
                  f"exit {proc_s.returncode}")
        finally:
            shutil.rmtree(tmp2, ignore_errors=True)

    print()
    if FAILS:
        print(f"{len(FAILS)} FAILING: {', '.join(FAILS)}")
        return 1
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
