#!/usr/bin/env python3
"""Unit tests for issue #170: the Report Model's Sharia evaluation
section (compile_model.build_sharia_section + the sharia_standards
job parameter).

Stdlib only, no network. Fixture verdict tables are produced by
the REAL Sharia engine (issue #168) from hand-computed snapshots,
so the tables are schema-faithful; every expected number below is
derived in comments from the fixture inputs, not copied from the
engine's output.

Hand-computed fixture maths (POUL.CA, FY2025):

AAOIFI snapshot -- total_revenue 100,000,000;
non_compliant_revenue 2,000,000; interest_bearing_debt
400,000,000; interest_bearing_assets 100,000,000;
avg_market_value_36m 2,000,000,000; shares_outstanding
1,789,351,397:
  income ratio  = 2,000,000 / 100,000,000      = 0.02  (<= 0.05 pass)
  debt ratio    = 400,000,000 / 2,000,000,000  = 0.20  (<= 0.30 pass)
  assets ratio  = 100,000,000 / 2,000,000,000  = 0.05  (<= 0.30 pass)
  purification ratio    = 0.02 (> 0, so the verdict is
                          compliant-with-purification)
  purification per share = 2,000,000 / 1,789,351,397
                          = 0.001118 (6dp)

EGX33 snapshot -- same revenue figures; interest_bearing_debt
300,000,000; interest_bearing_assets 200,000,000;
cash_and_liquid_assets 600,000,000; total_assets 1,200,000,000;
avg_market_value_review_period 900,000,000:
  denominator   = max(1,200,000,000, 900,000,000) = 1,200,000,000
  income ratio  = 0.02                            (<= 0.05 pass)
  borrowing     = 300,000,000 / 1,200,000,000 = 0.25 (<= 0.33 pass)
  investments   = 200,000,000 / 1,200,000,000 = 0.166667 (pass)
  liquid assets = 600,000,000 / 1,200,000,000 = 0.50 (<= 0.70 pass)
  verdict compliant; EGX33 defines NO purification rule, so it is
  excluded from the average and the exclusion is shown.

Average over [AAOIFI, EGX33] = 0.02 (AAOIFI alone defines one).
Average over two defining standards 0.02 and 0.05 = 0.035.

Run: python3 scripts/test_compile_model_sharia.py
Exit 0 only when every test passes.
"""
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)

import compile_model  # noqa: E402
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


# ---------------------------------------------------------------- fixtures

PERIOD = {"label": "FY2025", "start": "2025-01-01",
          "end": "2025-12-31"}

AAOIFI_SNAPSHOT = {
    "ticker": "POUL.CA",
    "statement_period": PERIOD,
    "screening_date": "2026-11-17",
    "activity": {"classification": "permissible",
                 "evidence_source": "test fixture"},
    "financials": {"total_revenue": 100_000_000,
                   "non_compliant_revenue": 2_000_000,
                   "interest_bearing_debt": 400_000_000,
                   "interest_bearing_assets": 100_000_000,
                   "shares_outstanding": 1_789_351_397},
    "market": {"avg_market_value_36m": 2_000_000_000},
    "dividends": [],
}

EGX33_SNAPSHOT = {
    "ticker": "POUL.CA",
    "statement_period": PERIOD,
    "screening_date": "2026-11-17",
    "activity": {"classification": "permissible",
                 "evidence_source": "test fixture"},
    "financials": {"total_revenue": 100_000_000,
                   "non_compliant_revenue": 2_000_000,
                   "interest_bearing_debt": 300_000_000,
                   "interest_bearing_assets": 200_000_000,
                   "cash_and_liquid_assets": 600_000_000,
                   "total_assets": 1_200_000_000,
                   "shares_outstanding": 1_789_351_397},
    "market": {"avg_market_value_review_period": 900_000_000},
    "dividends": [],
}


def write_table(repo_root, snapshot, standard):
    ruleset = se.load_ruleset(standard)
    table = se.screen_table([snapshot], ruleset,
                            generated_at="2026-11-17T00:00:00Z")
    path = os.path.join(repo_root, "sharia",
                        f"verdicts-{standard.lower()}.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(table, fh, ensure_ascii=False, indent=2,
                  sort_keys=True)
    return table


def write_sweep(sweep_dir):
    os.makedirs(sweep_dir, exist_ok=True)
    digest = {
        "ticker": "POUL.CA",
        "job": "run yahooquery POUL.CA",
        "date": "2026-11-17",
        "started": "2026-11-17T06:15:00Z",
        "finished": "2026-11-17T06:16:00Z",
        "results": [{"tool": "yahooquery", "status": "no-summary",
                     "detail": "fixture row"}],
    }
    with open(os.path.join(sweep_dir, "digest.json"), "w",
              encoding="utf-8") as fh:
        json.dump(digest, fh)


def fixture_env():
    """(tmp, repo_root, sweep_dir, profiles_dir) with engine-made
    AAOIFI + EGX33 tables for the hand-computed POUL snapshots."""
    tmp = tempfile.mkdtemp(prefix="cm-sharia-")
    repo_root = os.path.join(tmp, "repo")
    sweep_dir = os.path.join(tmp, "sweep")
    profiles_dir = os.path.join(tmp, "profiles")
    os.makedirs(repo_root)
    os.makedirs(profiles_dir)
    write_table(repo_root, AAOIFI_SNAPSHOT, "AAOIFI")
    write_table(repo_root, EGX33_SNAPSHOT, "EGX33")
    write_sweep(sweep_dir)
    return tmp, repo_root, sweep_dir, profiles_dir


def compile_fixture(repo_root, sweep_dir, profiles_dir, standards):
    return compile_model.compile_sweep(
        sweep_dir, repo_root=repo_root, profiles_dir=profiles_dir,
        sharia_standards=standards)


def entry(section, standard):
    for e in section["standards"]:
        if e["standard"] == standard:
            return e
    raise AssertionError(f"no entry for {standard}")


def ratio(entry_, rid):
    for r in entry_["ratios"]:
        if r["id"] == rid:
            return r
    raise AssertionError(f"no ratio {rid}")


# ---------------------------------------------------------------- tests

def test_section_both_standards():
    _tmp, repo, sweep, profiles = fixture_env()
    model = compile_fixture(repo, sweep, profiles,
                            ["AAOIFI", "EGX33"])
    section = model["sharia"]
    assert section["selection"] == "parameter"
    assert section["requested"] == ["AAOIFI", "EGX33"]
    assert section["verdicts"] == {
        "AAOIFI": "compliant-with-purification",
        "EGX33": "compliant"}

    aaoifi = entry(section, "AAOIFI")
    assert aaoifi["name_en"] and "AAOIFI" in aaoifi["name_en"]
    assert aaoifi["name_ar"]
    assert aaoifi["ruleset_version"] == "1.0.0"
    assert aaoifi["statement_period"]["label"] == "FY2025"
    assert aaoifi["denominator_variant"] == "avg36m"
    assert ratio(aaoifi, "non_compliant_income")["value"] == 0.02
    assert ratio(aaoifi, "non_compliant_income")["passed"] is True
    assert ratio(aaoifi, "interest_bearing_debt")["value"] == 0.2
    assert ratio(aaoifi, "interest_bearing_assets")["value"] == 0.05
    assert aaoifi["purification"]["ratio"] == 0.02
    assert aaoifi["purification"]["per_share"] == 0.001118

    egx33 = entry(section, "EGX33")
    assert egx33["denominator_variant"] is None
    assert ratio(egx33, "interest_bearing_borrowing")["value"] == 0.25
    assert ratio(egx33, "interest_bearing_investments")["value"] \
        == 0.166667
    assert ratio(egx33, "liquid_assets")["value"] == 0.5
    assert egx33["purification"]["defined"] is False

    avg = section["average_purification"]
    assert avg["value"] == 0.02
    assert avg["included"] == [{"standard": "AAOIFI", "ratio": 0.02}]
    assert avg["excluded"] == [{
        "standard": "EGX33",
        "reason": "standard defines no purification rule"}]
    # compliant vs compliant-with-purification are different
    # verdicts: the disagreement flag must be set.
    assert section["disagreement"] is True


def test_default_selection_all_implemented():
    _tmp, repo, sweep, profiles = fixture_env()
    model = compile_fixture(repo, sweep, profiles, None)
    section = model["sharia"]
    assert section["selection"] == "default-all-implemented"
    assert section["requested"] is None
    assert [e["standard"] for e in section["standards"]] == \
        se.available_standards()
    assert set(section["verdicts"]) == {
        "AAOIFI", "DJIM", "EGX33", "FTSE", "ISLAMICLY", "MSCI",
        "MSCI_M", "SP_SHARIAH"}
    # The fixture repo carries tables only for AAOIFI + EGX33;
    # the packs added by issue #169 render insufficient-data
    # (missing table), never a silent skip.
    for std in ("DJIM", "FTSE", "ISLAMICLY", "MSCI", "MSCI_M",
                "SP_SHARIAH"):
        assert section["verdicts"][std] == "insufficient-data"


def test_subset_selection_egx33_only():
    _tmp, repo, sweep, profiles = fixture_env()
    model = compile_fixture(repo, sweep, profiles, ["EGX33"])
    section = model["sharia"]
    assert [e["standard"] for e in section["standards"]] == ["EGX33"]
    avg = section["average_purification"]
    # No selected standard defines a purification rule: the
    # average is null and the exclusion is shown, never hidden.
    assert avg["value"] is None
    assert avg["included"] == []
    assert avg["excluded"] == [{
        "standard": "EGX33",
        "reason": "standard defines no purification rule"}]
    assert section["disagreement"] is False


def test_unknown_standard_refused():
    _tmp, repo, sweep, profiles = fixture_env()
    # An unimplemented standard id must refuse the compile
    # exactly like any unknown id. (DJIM stood in for one until
    # issue #169 pinned it from S&P DJI's own methodology.)
    for bad in (["AAOIFI", "UNIMPLEMENTED"], ["nope"], []):
        try:
            compile_fixture(repo, sweep, profiles, bad)
        except compile_model.CompileError as exc:
            assert "sharia" in str(exc).lower()
        else:
            raise AssertionError(f"{bad} did not refuse the compile")
    # Case-insensitive ids are accepted and normalised.
    model = compile_fixture(repo, sweep, profiles, ["aaoifi"])
    assert model["sharia"]["verdicts"] == {
        "AAOIFI": "compliant-with-purification"}


def test_insufficient_data_real_tables():
    # The repo's own stored tables: POUL.CA currently carries only
    # shares outstanding + a dividend event, so both standards must
    # render insufficient-data with the missing inputs named.
    tmp = tempfile.mkdtemp(prefix="cm-sharia-real-")
    sweep = os.path.join(tmp, "sweep")
    profiles = os.path.join(tmp, "profiles")
    os.makedirs(profiles)
    write_sweep(sweep)
    model = compile_model.compile_sweep(
        sweep, repo_root=ROOT, profiles_dir=profiles,
        sharia_standards=["AAOIFI", "EGX33"])
    section = model["sharia"]
    assert section["verdicts"] == {
        "AAOIFI": "insufficient-data", "EGX33": "insufficient-data"}
    aaoifi = entry(section, "AAOIFI")
    assert "total_revenue" in aaoifi["missing_inputs"]
    assert "interest_bearing_debt" in aaoifi["missing_inputs"]
    assert aaoifi["purification"]["defined"] is True
    assert aaoifi["purification"]["ratio"] is None
    avg = section["average_purification"]
    assert avg["value"] is None and avg["included"] == []
    reasons = {e["standard"]: e["reason"] for e in avg["excluded"]}
    assert reasons["AAOIFI"] == \
        "purification ratio unavailable (insufficient-data)"
    assert reasons["EGX33"] == "standard defines no purification rule"
    # Two insufficient-data entries are an absence of verdicts,
    # not a disagreement.
    assert section["disagreement"] is False
    assert "sharia-insufficient-data: AAOIFI" in model["flags"]


def _fake_table(standard, verdict, ratio_value):
    row = {
        "ticker": "POUL.CA",
        "standard": standard,
        "ruleset_version": "9.9",
        "engine_version": "1.0.0",
        "verdict": verdict,
        "screening_date": "2026-11-17",
        "statement_period": PERIOD,
        "parameters": {},
        "activity": {"classification": "permissible",
                     "evidence_source": "unit fixture"},
        "ratios": [],
        "purification": {"defined": ratio_value is not _UNDEFINED,
                         "ratio": ratio_value
                         if ratio_value is not _UNDEFINED else None,
                         "per_share": None},
        "missing_inputs": [],
        "framing_en": se.FRAMING_EN,
        "framing_ar": se.FRAMING_AR,
    }
    return {"standard": {"id": standard, "name_en": standard,
                         "name_ar": standard,
                         "ruleset_version": "9.9"},
            "engine_version": "1.0.0",
            "generated_at": "2026-11-17T00:00:00Z",
            "rows": [row]}


class _Undefined:
    pass


_UNDEFINED = _Undefined()


def test_average_two_defining_standards():
    tables = {"STD_A": _fake_table("STD_A", "compliant", 0.02),
              "STD_B": _fake_table("STD_B", "non-compliant", 0.05)}
    section, _flags = compile_model.build_sharia_section(
        "POUL.CA", ["STD_A", "STD_B"], ["STD_A", "STD_B"], tables,
        se)
    # (0.02 + 0.05) / 2 = 0.035, hand-computed.
    assert section["average_purification"]["value"] == 0.035
    assert section["average_purification"]["excluded"] == []
    assert section["disagreement"] is True
    tables = {"STD_A": _fake_table("STD_A", "insufficient-data",
                                   _UNDEFINED),
              "STD_B": _fake_table("STD_B", "insufficient-data",
                                   _UNDEFINED)}
    section, _flags = compile_model.build_sharia_section(
        "POUL.CA", ["STD_A", "STD_B"], ["STD_A", "STD_B"], tables,
        se)
    assert section["disagreement"] is False
    assert section["average_purification"]["value"] is None


def test_missing_table_and_row_render_insufficient_data():
    _tmp, repo, sweep, profiles = fixture_env()
    # Remove the EGX33 table entirely, and compile a ticker the
    # AAOIFI table has no row for: both gaps must surface as
    # insufficient-data with the gap named, never a blank section.
    os.remove(os.path.join(repo, "sharia", "verdicts-egx33.json"))
    section, flags = compile_model.build_sharia_section(
        "XXXX.CA", ["AAOIFI", "EGX33"], ["AAOIFI", "EGX33"],
        {"AAOIFI": compile_model.load_sharia_table(repo, "AAOIFI"),
         "EGX33": None}, se)
    assert entry(section, "EGX33")["verdict"] == "insufficient-data"
    assert entry(section, "EGX33")["missing_inputs"] == [
        "stored verdict table sharia/verdicts-egx33.json"]
    assert entry(section, "AAOIFI")["missing_inputs"] == [
        "verdict row for XXXX.CA in sharia/verdicts-aaoifi.json"]
    assert "sharia-table-missing: EGX33" in flags
    assert "sharia-row-missing: AAOIFI XXXX.CA" in flags


def test_framing_bilingual_everywhere():
    _tmp, repo, sweep, profiles = fixture_env()
    model = compile_fixture(repo, sweep, profiles,
                            ["AAOIFI", "EGX33"])
    section = model["sharia"]
    assert section["framing_en"] == se.FRAMING_EN
    assert "not a fatwa" in section["framing_en"]
    assert section["framing_ar"] == se.FRAMING_AR
    assert "ليست فتوى" in section["framing_ar"]
    for e in section["standards"]:
        assert e["framing_en"] == se.FRAMING_EN
        assert e["framing_ar"] == se.FRAMING_AR
    avg = section["average_purification"]
    assert "Average purification ratio" in avg["label_en"]
    assert "متوسط نسبة التطهير" in avg["label_ar"]


def test_schema_unchanged_additive_block():
    # Historical v1 exception (issue #170), BOUNDED by #280: the
    # sharia block was added under v1 without a bump. A v1 model
    # carrying it still validates -- but the exception is frozen,
    # not a general override: the current compiler emits v2, and
    # no further field may be added to v1 silently (strict D-7
    # from v2 on; see scripts/report_model.py).
    _tmp, repo, sweep, profiles = fixture_env()
    model = compile_fixture(repo, sweep, profiles, ["AAOIFI"])
    assert model["schema"] == "borsagator-report-model/2"
    assert model["model_version"] == 2
    assert compile_model.validate_model_schema(model) == []
    # Frozen v1 + sharia still validates (the bounded exception):
    # the same model relabelled (1, /1) without the v2-only block.
    v1 = dict(model)
    v1["schema"] = "borsagator-report-model/1"
    v1["model_version"] = 1
    del v1["disclosure_events"]
    assert compile_model.validate_model_schema(v1) == []


def test_view_carries_section():
    import delta
    _tmp, repo, sweep, profiles = fixture_env()
    model = compile_fixture(repo, sweep, profiles,
                            ["AAOIFI", "EGX33"])
    view = delta.model_to_view(model)
    assert view["sharia"] == model["sharia"]
    assert view["sharia"]["verdicts"]["AAOIFI"] == \
        "compliant-with-purification"


def test_cli_end_to_end():
    _tmp, repo, sweep, profiles = fixture_env()
    out_path = os.path.join(_tmp, "report-model.json")
    proc = subprocess.run(
        [sys.executable, os.path.join(SCRIPTS, "compile_model.py"),
         sweep, "--repo-root", repo, "--profiles-dir", profiles,
         "--sharia-standards", "AAOIFI,EGX33", "--out", out_path],
        capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stderr
    with open(out_path, encoding="utf-8") as fh:
        model = json.load(fh)
    assert model["sharia"]["verdicts"]["EGX33"] == "compliant"
    # An unknown standard refuses via the CLI too: exit 2 and a
    # compile_error.txt next to the would-be model.
    proc = subprocess.run(
        [sys.executable, os.path.join(SCRIPTS, "compile_model.py"),
         sweep, "--repo-root", repo, "--profiles-dir", profiles,
         "--sharia-standards", "FOO", "--out", out_path],
        capture_output=True, text=True, timeout=60)
    assert proc.returncode == 2
    assert "unknown sharia standard" in proc.stderr
    with open(os.path.join(_tmp, "compile_error.txt"),
              encoding="utf-8") as fh:
        assert "unknown sharia standard" in fh.read()


def main():
    check("section renders both standards with ratio tables and "
          "the labelled average (EGX33 excluded, shown)",
          test_section_both_standards)
    check("no selection covers all implemented standards",
          test_default_selection_all_implemented)
    check("subset selection: EGX33 only, average null with the "
          "exclusion shown", test_subset_selection_egx33_only)
    check("unknown / unimplemented standard refuses the compile; "
          "ids are case-insensitive", test_unknown_standard_refused)
    check("real stored tables render insufficient-data with the "
          "missing inputs named",
          test_insufficient_data_real_tables)
    check("average spans two defining standards (0.02, 0.05 -> "
          "0.035); disagreement only on determinate verdicts",
          test_average_two_defining_standards)
    check("missing table / missing row render insufficient-data "
          "with the gap named",
          test_missing_table_and_row_render_insufficient_data)
    check("not-a-fatwa framing present in Arabic and English, "
          "section-wide and per standard",
          test_framing_bilingual_everywhere)
    check("v2 emission; frozen v1+sharia still validates (bounded "
          "additive exception)", test_schema_unchanged_additive_block)
    check("delta.model_to_view carries the section for the "
          "renderer", test_view_carries_section)
    check("CLI: --sharia-standards compiles; an unknown standard "
          "exits 2 with compile_error.txt", test_cli_end_to_end)
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    print(f"\ntest_compile_model_sharia: {passed}/{len(RESULTS)} "
          f"passed")
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
