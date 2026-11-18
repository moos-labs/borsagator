#!/usr/bin/env python3
"""Unit tests for issue #155: nonfinite ensemble values bypass
coercion and break the model.

Before the fix, the raw ``ensemble`` section was copied verbatim
into the model (line ~1632 ``"ensemble": ensemble``), along with
``price`` / ``family_scores`` / ``horizons`` / ``risk`` extracted
from it -- but the loader turns NaN / Infinity into ``_NonFinite``
sentinels, and ``dump_model`` calls ``json.dumps(...,
allow_nan=False)`` with no normalisation pass, so a ``_NonFinite``
sentinel raised ``TypeError`` ("Object of type _NonFinite is not
JSON serializable") and the whole model was lost, with no coercion
flag. Reproduced by Ins with ``sigma_daily=NaN``.

The fix nulls each non-finite value in the ensemble right after
load (``_null_nonfinite``), recording a ``coercion_failed`` entry
with its dotted field path, so every section derived from the
ensemble is clean before construction.

Stdlib only, no network, no fixtures. Run:
    python3 scripts/test_compile_model_155.py
Exit 0 only when every test passes.
"""
import json
import math
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)

import compile_model  # noqa: E402

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


def test_null_sentinel_nested_with_path():
    # Sentinels at every depth are nulled, each with its dotted
    # field path recorded; finite siblings survive untouched.
    failed = []
    obj = {"sigma_daily": compile_model._NonFinite("NaN"),
           "base_price": 8.02,
           "risk": {"value": compile_model._NonFinite("Infinity"),
                    "events": [{"p": compile_model._NonFinite("NaN")},
                               {"p": 0.25}]},
           "tags": ["a", compile_model._NonFinite("-Infinity")]}
    out = compile_model._null_nonfinite(obj, "ensemble", failed)
    assert out["sigma_daily"] is None
    assert out["base_price"] == 8.02
    assert out["risk"]["value"] is None
    assert out["risk"]["events"][0]["p"] is None
    assert out["risk"]["events"][1]["p"] == 0.25
    assert out["tags"] == ["a", None]
    paths = sorted(e["field"] for e in failed)
    assert paths == ["ensemble.risk.events[0].p",
                     "ensemble.risk.value",
                     "ensemble.sigma_daily",
                     "ensemble.tags[1]"], paths
    assert all(e["tool"] == "ensemble" and
               e["reason"] == "non-finite value" for e in failed)
    assert {e["field"]: e["raw_value"] for e in failed} == {
        "ensemble.sigma_daily": "NaN",
        "ensemble.risk.value": "Infinity",
        "ensemble.risk.events[0].p": "NaN",
        "ensemble.tags[1]": "-Infinity"}


def test_null_plain_nonfinite_float():
    # A real float NaN / Infinity (not a sentinel) is nulled too.
    failed = []
    out = compile_model._null_nonfinite(
        {"a": float("nan"), "b": float("inf"), "c": 1.5},
        "ensemble", failed)
    assert out == {"a": None, "b": None, "c": 1.5}
    assert sorted(e["field"] for e in failed) == [
        "ensemble.a", "ensemble.b"]


def test_null_finite_values_untouched():
    # Finite numbers, strings, None and bools pass through; no
    # entries are recorded -- the fix must not over-null.
    failed = []
    obj = {"a": 0, "b": -3.5, "c": "NaN", "d": None, "e": True,
           "f": [1, "x", False], "g": {}}
    out = compile_model._null_nonfinite(obj, "ensemble", failed)
    assert out == obj and failed == []
    assert compile_model._null_nonfinite(42, "ensemble", failed) == 42
    assert compile_model._null_nonfinite("s", "ensemble",
                                         failed) == "s"
    assert failed == []


def _sweep_dir(ensemble):
    """Minimal sweep dir: a non-sweep-shape job (no planned-tool
    requirement), no tool results, an ensemble.json written with
    bare NaN / Infinity tokens (json.dump default allow_nan)."""
    tmp = tempfile.mkdtemp(prefix="test155-")
    digest = {"job": "run yahooquery POUL.CA market=EGX",
              "ticker": "POUL.CA", "date": "2026-11-18",
              "started": "2026-11-18T06:00:00Z",
              "finished": "2026-11-18T07:00:00Z", "results": []}
    with open(os.path.join(tmp, "digest.json"), "w") as handle:
        json.dump(digest, handle)
    if ensemble is not None:
        with open(os.path.join(tmp, "ensemble.json"), "w") as handle:
            json.dump(ensemble, handle)
    return tmp


def _ensemble(**overrides):
    base = {"ticker": "POUL.CA", "base_price": 8.02,
            "base_date": "2026-11-18",
            "base_source": "consensus median",
            "sigma_daily": 0.012,
            "family_scores": {"price": 0.5},
            "horizons": {"week": {"expected_move_pct": 1.5,
                                  "range_low_pct": -2.0,
                                  "range_high_pct": 2.0}},
            "risk": {"note": "x", "value": 0.3},
            "corporate_actions": []}
    base.update(overrides)
    return base


def test_sigma_daily_nan_compiles():
    # The proof bar: an ensemble with sigma_daily=NaN compiles to
    # a model with that field nulled + flagged, instead of raising.
    # On unmodified main this raises TypeError in dump_model.
    tmp = _sweep_dir(_ensemble(sigma_daily=float("nan")))
    try:
        model = compile_model.compile_sweep(tmp)
        assert model["ensemble"]["sigma_daily"] is None, \
            model["ensemble"]
        assert model["price"]["sigma_daily"] is None, model["price"]
        flagged = [e["field"] for e in model["coercion_failed"]]
        assert "ensemble.sigma_daily" in flagged, flagged
        out_path = os.path.join(tmp, "report-model.json")
        compile_model.dump_model(model, out_path)
        with open(out_path, encoding="utf-8") as handle:
            strict = json.load(
                handle,
                parse_constant=lambda c: (_ for _ in ()).throw(
                    ValueError(f"non-finite {c!r} in model")))
        assert strict["ensemble"]["sigma_daily"] is None
        assert strict["price"]["sigma_daily"] is None
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_nested_risk_nonfinite_nulled():
    # Non-finite values nested inside risk (dict + list) are
    # nulled with paths; finite siblings keep their values.
    ens = _ensemble(risk={"note": "x", "value": float("inf"),
                          "events": [{"p": float("nan")},
                                     {"p": 0.25}]})
    tmp = _sweep_dir(ens)
    try:
        model = compile_model.compile_sweep(tmp)
        assert model["risk"] == {"note": "x", "value": None,
                                 "events": [{"p": None},
                                            {"p": 0.25}]}, model["risk"]
        assert model["ensemble"]["risk"] == model["risk"]
        flagged = sorted(e["field"] for e in model["coercion_failed"])
        assert flagged == ["ensemble.risk.events[0].p",
                           "ensemble.risk.value"], flagged
        out_path = os.path.join(tmp, "report-model.json")
        compile_model.dump_model(model, out_path)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_clean_ensemble_unchanged():
    # An ensemble with no non-finite value compiles exactly as
    # before: no ensemble coercion entries, values intact.
    tmp = _sweep_dir(_ensemble())
    try:
        model = compile_model.compile_sweep(tmp)
        assert model["ensemble"]["sigma_daily"] == 0.012
        assert model["price"]["sigma_daily"] == 0.012
        assert model["risk"] == {"note": "x", "value": 0.3}
        assert [e for e in model["coercion_failed"]
                if e.get("tool") == "ensemble"] == []
        out_path = os.path.join(tmp, "report-model.json")
        compile_model.dump_model(model, out_path)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_no_ensemble_still_works():
    # No ensemble.json at all (non-sweep-shape job): the fix must
    # not touch the absent-ensemble path.
    tmp = _sweep_dir(None)
    try:
        model = compile_model.compile_sweep(tmp)
        assert model["ensemble"] is None
        assert model["coercion_failed"] == []
        out_path = os.path.join(tmp, "report-model.json")
        compile_model.dump_model(model, out_path)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    for name, fn in [
            ("null_sentinel_nested_with_path",
             test_null_sentinel_nested_with_path),
            ("null_plain_nonfinite_float",
             test_null_plain_nonfinite_float),
            ("null_finite_values_untouched",
             test_null_finite_values_untouched),
            ("sigma_daily_nan_compiles", test_sigma_daily_nan_compiles),
            ("nested_risk_nonfinite_nulled",
             test_nested_risk_nonfinite_nulled),
            ("clean_ensemble_unchanged", test_clean_ensemble_unchanged),
            ("no_ensemble_still_works", test_no_ensemble_still_works)]:
        check(name, fn)
    failed = [r for r in RESULTS if not r[1]]
    print(f"test_compile_model_155: "
          f"{len(RESULTS) - len(failed)}/{len(RESULTS)} passed")
    sys.exit(1 if failed else 0)
