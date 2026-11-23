#!/usr/bin/env python3
"""Regression tests for the panel-evaluation compliance fixes
(2026-11-23 expert panel, Antigravity risk/code audit).

The auditor's code findings that contradict the product's OWN
framing decisions, fixed as defects:

1. The Arabic short disclaimer called the outputs «التوصيات»
   ("the recommendations") -- the regulated word the English
   disclaimer disclaims. It now reads «النتائج الحسابية»
   ("the computational results"), and no disclaimer string may
   carry «التوصيات» again.
2. The shipped report model copied the profile's explicit
   action / buy_below / sell_above into the exported JSON (the
   "Copy model JSON" payload). Those keys are stripped at the
   compile boundary; recommend.py's internal profile store is
   unchanged.
3. Notes the compiler itself flagged as advice-worded
   (recommendation-notes-carry-advice-wording) were rendered
   anyway. They are now withheld from the shipped model; the
   flag still records that it happened.
4. The report's Sharia section carries the NOT A FATWA banner
   (EN + AR: screening results per the selected standard; no
   Sharia Board certification), and a stored row with an
   unresolved ratio leg (value None) ships as "indeterminate",
   never as a determinate verdict by default.
5. The generated public benchmark markdown anonymises the
   competitor screeners (Source A/B/C/...); the JSON report --
   the internal record -- keeps the real source ids.

Stdlib only, no network. Run:
    python3 scripts/test_panel_eval_fixes.py
Exit 0 only when every test passes.
"""
import json
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)

import compile_model  # noqa: E402
import sharia_benchmark as sb  # noqa: E402
import sharia_engine as se  # noqa: E402

RESULTS = []


def check(name, fn):
    try:
        fn()
    except Exception as e:
        RESULTS.append((name, False, f"{type(e).__name__}: {e}"))
        print(f"FAIL {name}: {type(e).__name__}: {e}")
        return
    RESULTS.append((name, True, ""))
    print(f"PASS {name}")


# ------------------------------------------------------------- fix 1

def test_ar_disclaimer_no_recommendations_word():
    table = json.load(open(os.path.join(
        SCRIPTS, "render_i18n.json"), encoding="utf-8"))
    for key in ("disclaimer.short", "disclaimer.long"):
        ar = table[key]["ar"]
        assert "التوصيات" not in ar, (key, ar)
    short_ar = table["disclaimer.short"]["ar"]
    assert "النتائج الحسابية محسوبة" in short_ar, short_ar
    # The English source text is untouched.
    assert table["disclaimer.short"]["en"].startswith(
        "Borsagator is not an investment adviser")


# ------------------------------------------------------- fixes 2 + 3

def _sweep_and_profiles(notes):
    """Minimal sweep (digest + ensemble) plus a profiles dir whose
    recommendation matches the sweep on as_of/base_price, carrying
    the advice fields and the given notes."""
    tmp = tempfile.mkdtemp(prefix="test-panel-eval-")
    digest = {"job": "run yahooquery POUL.CA market=EGX",
              "ticker": "POUL.CA", "date": "2026-11-18",
              "started": "2026-11-18T06:00:00Z",
              "finished": "2026-11-18T07:00:00Z", "results": []}
    with open(os.path.join(tmp, "digest.json"), "w") as handle:
        json.dump(digest, handle)
    ensemble = {"ticker": "POUL.CA", "base_price": 8.02,
                "base_date": "2026-11-18",
                "base_source": "consensus median",
                "sigma_daily": 0.012,
                "family_scores": {"price": 0.5},
                "horizons": {"week": {"expected_move_pct": 1.5,
                                      "range_low_pct": -2.0,
                                      "range_high_pct": 2.0}},
                "risk": {"note": "x", "value": 0.3},
                "corporate_actions": []}
    with open(os.path.join(tmp, "ensemble.json"), "w") as handle:
        json.dump(ensemble, handle)
    profiles = os.path.join(tmp, "profiles")
    os.makedirs(profiles)
    rec = {"ticker": "POUL.CA", "as_of": "2026-11-18",
           "archive_commit": "archive-commit-test",
           "base_price": 8.02, "reference_price": 8.02,
           "action": "buy", "buy_below": 7.13, "sell_above": 11.59,
           "expected_week_pct": 16.73, "nudge_pct": 0.0,
           "expected_week_adj_pct": 16.73, "confidence": 0.3,
           "risk": "shock", "weights_source": "ledger",
           "notes": notes}
    with open(os.path.join(profiles, "POUL.CA.recommendation.json"),
              "w") as handle:
        json.dump(rec, handle)
    return tmp, profiles


def test_shipped_model_has_no_advice_fields():
    tmp, profiles = _sweep_and_profiles(["ensemble as of 2026-11-18"])
    try:
        model = compile_model.compile_sweep(tmp, profiles_dir=profiles)
        rec = model["recommendation"]
        assert rec is not None, model["flags"]
        for key in ("action", "buy_below", "sell_above"):
            assert key not in rec, (key, rec)
        # The rest of the profile still copies through.
        assert rec["expected_week_pct"] == 16.73
        assert rec["reference_price"] == 8.02
        assert rec["notes"] == ["ensemble as of 2026-11-18"]
        # And the serialised payload (what "Copy model JSON"
        # hands the reader) is clean too.
        text = json.dumps(model)
        assert '"action": "buy"' not in text
        assert "buy_below" not in text and "sell_above" not in text
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_advice_worded_notes_withheld():
    advice = "risk overlay = shock: action forced to HOLD"
    clean = "ensemble as of 2026-11-18"
    tmp, profiles = _sweep_and_profiles([advice, clean])
    try:
        model = compile_model.compile_sweep(tmp, profiles_dir=profiles)
        rec = model["recommendation"]
        assert rec["notes"] == [clean], rec["notes"]
        assert "recommendation-notes-carry-advice-wording" \
            in model["flags"], model["flags"]
        assert advice not in json.dumps(model)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_clean_notes_raise_no_flag():
    tmp, profiles = _sweep_and_profiles(["ensemble as of 2026-11-18"])
    try:
        model = compile_model.compile_sweep(tmp, profiles_dir=profiles)
        assert "recommendation-notes-carry-advice-wording" \
            not in model["flags"], model["flags"]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ------------------------------------------------------------- fix 4

def _fake_table(verdict, ratios):
    row = {"ticker": "POUL.CA", "standard": "AAOIFI",
           "ruleset_version": "9.9", "engine_version": "1.0.0",
           "verdict": verdict, "screening_date": "2026-11-17",
           "statement_period": {"start": "2026-01-01",
                                "end": "2026-09-30"},
           "parameters": {},
           "activity": {"classification": "permissible",
                        "evidence_source": "unit fixture"},
           "ratios": ratios,
           "purification": {"defined": False, "ratio": None,
                            "per_share": None},
           "missing_inputs": [],
           "framing_en": se.FRAMING_EN, "framing_ar": se.FRAMING_AR}
    return {"standard": {"id": "AAOIFI", "name_en": "AAOIFI",
                         "name_ar": "AAOIFI",
                         "ruleset_version": "9.9"},
            "engine_version": "1.0.0",
            "generated_at": "2026-11-17T00:00:00Z",
            "rows": [row]}


def _ratio(rid, value):
    return {"id": rid, "label_en": rid, "label_ar": rid,
            "numerator_field": "x", "numerator": 1, "denominator": 2,
            "denominator_base": "y", "value": value,
            "threshold": 0.3, "comparison": "le",
            "passed": (value <= 0.3) if value is not None else None,
            "missing": [] if value is not None else ["deposits"],
            "error": None}


def test_sharia_section_banner():
    tables = {"AAOIFI": _fake_table("compliant", [_ratio("debt", 0.2)])}
    section, _flags = compile_model.build_sharia_section(
        "POUL.CA", ["AAOIFI"], ["AAOIFI"], tables, se)
    assert section["banner_en"] == se.BANNER_EN
    assert "NOT A FATWA" in section["banner_en"]
    assert "no Sharia Board certification" in section["banner_en"]
    assert section["banner_ar"] == se.BANNER_AR
    assert "ليست فتوى" in section["banner_ar"]


def test_unresolved_leg_forces_indeterminate():
    # Stored verdict says compliant, but the deposits leg never
    # resolved (value None): the shipped entry must be
    # indeterminate, with the leg named -- not the stored verdict.
    tables = {"AAOIFI": _fake_table(
        "compliant", [_ratio("interest_bearing_assets", None),
                      _ratio("debt", 0.2)])}
    section, flags = compile_model.build_sharia_section(
        "POUL.CA", ["AAOIFI"], ["AAOIFI"], tables, se)
    entry = section["standards"][0]
    assert entry["verdict"] == "indeterminate", entry["verdict"]
    assert section["verdicts"]["AAOIFI"] == "indeterminate"
    assert "unresolved ratio leg: interest_bearing_assets" \
        in entry["missing_inputs"], entry["missing_inputs"]
    assert "sharia-verdict-indeterminate: AAOIFI" in flags, flags
    # An indeterminate entry is not a dissenting verdict.
    assert section["disagreement"] is False


def test_resolved_legs_keep_verdict():
    tables = {"AAOIFI": _fake_table(
        "compliant", [_ratio("interest_bearing_assets", 0.1),
                      _ratio("debt", 0.2)])}
    section, flags = compile_model.build_sharia_section(
        "POUL.CA", ["AAOIFI"], ["AAOIFI"], tables, se)
    assert section["standards"][0]["verdict"] == "compliant"
    assert not any(f.startswith("sharia-verdict-indeterminate")
                   for f in flags), flags


# ------------------------------------------------------------- fix 5

def test_public_benchmark_anonymised():
    report = {
        "report_date": "2026-11-23",
        "framing_en": "Screening result — not a fatwa.",
        "framing_ar": "نتيجة فحص — ليست فتوى.",
        "covered_universe": ["POUL.CA"],
        "engine_version": "1.0.0",
        "generated_at": "2026-11-23T00:00:00Z",
        "comparisons": [{
            "source_id": "musaffa", "standard": "AAOIFI",
            "source_status": "frozen", "determinate_pairs": 1,
            "agreement_pct": 100.0,
            "counts": {"our_insufficient_data": 0},
            "note": "Musaffa page snapshot.",
            "rows": [{"ticker": "POUL.CA", "ours": "compliant",
                      "theirs": "compliant", "theirs_raw": "HALAL",
                      "outcome": "agree",
                      "explanation": "Both sides determinate.",
                      "driver_hypothesis":
                          "Hypothesis: on Ostool's own published "
                          "percentages, x."}]}],
        "purification": {
            "stats": {"n_pairs": 0, "mean_abs_diff": None,
                      "max_abs_diff": None, "mean_rel_diff": None},
            "awaiting_our_inputs": [{
                "ticker": "POUL.CA", "source": "ostool",
                "published_pct": 5.5, "basis": "Ostool's column",
                "note": "recorded"}],
            "witnesses_unavailable": [
                {"source": "nour_borsa", "reason": "paywalled"}]},
        "method_notes": ["Faisal Securities PDF pending."],
    }
    md = sb.render_md(report)
    for name in ("Musaffa", "musaffa", "Ostool", "ostool", "Faisal",
                 "faisal", "nour_borsa", "Kashef", "kashef"):
        assert name not in md, (name, md)
    assert "Source A" in md and "Source C" in md
    # The internal record keeps the real ids untouched.
    assert report["comparisons"][0]["source_id"] == "musaffa"
    assert sb.PUBLIC_SOURCE_LABELS["ostool"] == "Source C"


def main():
    check("fix1: AR disclaimer carries no «التوصيات»",
          test_ar_disclaimer_no_recommendations_word)
    check("fix2: shipped model has no action/buy_below/sell_above",
          test_shipped_model_has_no_advice_fields)
    check("fix3: advice-worded notes withheld + flagged",
          test_advice_worded_notes_withheld)
    check("fix3: clean notes raise no flag",
          test_clean_notes_raise_no_flag)
    check("fix4: sharia section carries the NOT A FATWA banner",
          test_sharia_section_banner)
    check("fix4: unresolved ratio leg forces indeterminate",
          test_unresolved_leg_forces_indeterminate)
    check("fix4: resolved legs keep their verdict",
          test_resolved_legs_keep_verdict)
    check("fix5: public benchmark output anonymised",
          test_public_benchmark_anonymised)
    failed = [r for r in RESULTS if not r[1]]
    print(f"\ntest_panel_eval_fixes: {len(RESULTS) - len(failed)}/"
          f"{len(RESULTS)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
