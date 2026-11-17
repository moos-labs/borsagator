#!/usr/bin/env python3
"""Unit tests for issue #150: compile_model _is_secret_key misses
camelCase / concatenated credential keys.

The pre-fix test splits the upper-cased key on non-alphanumerics
and tests whole parts, so ``apiKey`` -> ``APIKEY``,
``accessToken`` -> ``ACCESSTOKEN``, ``clientSecret`` ->
``CLIENTSECRET`` and ``secretKey`` -> ``SECRETKEY`` match nothing
and pass through the R-12 redaction into the archived (public)
report-model.json. The fix tests substrings instead.

Stdlib only, no network, no fixtures. Run:
    python3 scripts/test_compile_model_secret.py
Exit 0 only when every test passes.
"""
import os
import sys

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


def assert_flagged(key):
    assert compile_model._is_secret_key(key) is True, \
        f"{key!r} should be flagged as a secret key"


def assert_kept(key):
    assert compile_model._is_secret_key(key) is False, \
        f"{key!r} should NOT be flagged as a secret key"


# --- #150: camelCase / concatenated credential spellings --------

def test_camelcase_flagged():
    for key in ("apiKey", "accessToken", "clientSecret", "secretKey"):
        assert_flagged(key)


def test_concatenated_variants_flagged():
    for key in ("myApiKey", "refreshToken", "dbPassword",
                "user_password", "api_key", "API_KEY",
                "access_token", "client_secret"):
        assert_flagged(key)


def test_known_names_still_flagged():
    for key in ("COHERE_API_KEY", "SIMFIN_API_KEY", "FMP_API_KEY",
                "GATOR_BUS_URL", "GH_TOKEN",
                "BORSAGATOR_APP_PRIVATE_KEY"):
        assert_flagged(key)


# --- bare-KEY exemption: these are tool metrics, not credentials -

def test_bare_key_exemption_kept():
    for key in ("total_return_stat_key", "monkey", "key", "donkey",
                "stat_key"):
        assert_kept(key)


def test_ordinary_metrics_kept():
    for key in ("sharpe", "close", "returns", "volume",
                "n_sessions", "sigma_daily", "ticker"):
        assert_kept(key)


# --- end to end through coerce_metrics (the R-12 drop path) -----

def test_coerce_metrics_drops_camelcase():
    dropped = []
    failed = []
    out = compile_model.coerce_metrics(
        {"apiKey": "fake-value",
         "accessToken": "fake-value",
         "clientSecret": "fake-value",
         "secretKey": "fake-value",
         "COHERE_API_KEY": "fake-value",
         "total_return_stat_key": "kept",
         "monkey": "kept",
         "sharpe": 1.5},
        "finbert", failed, dropped)
    for key in ("apiKey", "accessToken", "clientSecret",
                "secretKey", "COHERE_API_KEY"):
        assert key not in out, f"{key} leaked into coerced metrics"
    assert out.get("total_return_stat_key") == "kept"
    assert out.get("monkey") == "kept"
    assert out.get("sharpe") == 1.5
    assert {"tool": "finbert", "field": "apiKey"} in dropped
    assert {"tool": "finbert", "field": "accessToken"} in dropped
    assert {"tool": "finbert", "field": "clientSecret"} in dropped
    assert {"tool": "finbert", "field": "secretKey"} in dropped
    assert not failed


def main():
    check("camelCase credential keys are flagged", test_camelcase_flagged)
    check("concatenated/underscore variants are flagged",
          test_concatenated_variants_flagged)
    check("known secret names are still flagged",
          test_known_names_still_flagged)
    check("bare-KEY exemption keys are kept",
          test_bare_key_exemption_kept)
    check("ordinary metric keys are kept", test_ordinary_metrics_kept)
    check("coerce_metrics drops camelCase keys, keeps exemptions",
          test_coerce_metrics_drops_camelcase)
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    print(f"\ntest_compile_model_secret: {passed}/{len(RESULTS)} passed")
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
