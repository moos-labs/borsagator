#!/usr/bin/env python3
"""Controls for the #283 paired A/B EGX diagnostic harness.

Run directly:  python3 scripts/test_diag_egx_ab_283.py
Stdlib only, no network, no browser: classification / verdict /
launch-config / record-shape logic is exercised against the script's
own SIMULATED fixtures (clearly labelled, never live EGX captures).
The dry-run leg runner is exercised through the real script as a
subprocess against its local stub server: where playwright is
absent (this VM) the script must fail cleanly with a named
playwright-missing message and write NO record that could pass
as a probe result; where playwright exists the legs run for real
and both must classify the stub results page as "results".

Harness-first: FAILS on pristine main (scripts/diag_egx_ab.py
does not exist — ImportError) and PASSES on the fixed tree. The
classification tests are the sharp edge: the observed 511-char
EGX_Error body MUST classify as "egx-error", never "results" or
"empty" — a classifier that size-gates first would fail here.
"""
import json
import os
import subprocess
import sys
import tempfile
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import diag_egx_ab as D

PASSED = 0


def check(name, cond):
    global PASSED
    assert cond, name
    PASSED += 1
    print("pass: %s" % name)


def test_classify_results():
    html = D.fixture_results_page()
    check("classify: simulated results page -> results",
          D.classify_page(200, D.DIAG_URL, html, "Board meeting") ==
          "results")


def test_classify_egx_error_511():
    html = D.fixture_error_page()
    check("fixture: simulated EGX_Error body is exactly 511 chars",
          len(html) == 511)
    url = ("https://www.egx.com.eg/ar/EGX_Error.aspx"
           "?aspxerrorpath=/ar/NewsSearch.aspx")
    check("classify: 511-char EGX_Error body -> egx-error, not "
          "results/empty",
          D.classify_page(200, url, html, "Error") == "egx-error")
    check("classify: EGX_Error detected from body alone (URL lost)",
          D.classify_page(200, "https://www.egx.com.eg/ar/x",
                          html, "Error") == "egx-error")


def test_classify_forbidden_challenge_empty():
    check("classify: 403 -> forbidden",
          D.classify_page(403, D.DIAG_URL,
                          D.fixture_forbidden_page(), "403") ==
          "forbidden")
    check("classify: TSPD shell -> challenge",
          D.classify_page(200, D.DIAG_URL,
                          D.fixture_challenge_page(), "verify") ==
          "challenge")
    check("classify: empty body -> empty",
          D.classify_page(200, D.DIAG_URL,
                          D.fixture_empty_page(), "") == "empty")
    check("classify: no response -> no-response",
          D.classify_page(None, D.DIAG_URL, "", "") == "no-response")


def test_classify_nav_error():
    check("nav error: ERR_CONNECTION_RESET -> reset",
          D.classify_nav_error(
              "TimeoutError: Page.goto: net::ERR_CONNECTION_RESET "
              "at https://www.egx.com.eg/") == "reset")
    check("nav error: timeout text -> timeout",
          D.classify_nav_error("Timeout 90000ms exceeded") ==
          "timeout")
    check("nav error: other failure -> navigation-error",
          D.classify_nav_error("Error: net::ERR_NAME_NOT_RESOLVED") ==
          "navigation-error")


def test_verdicts():
    def legs(a, b, a2=None):
        out = [{"leg": "A", "classification": a},
               {"leg": "B", "classification": b}]
        if a2 is not None:
            out.append({"leg": "A", "classification": a2})
        return out
    v, _ = D.derive_verdict(legs("results", "reset", "results"))
    check("verdict: A results + B reset -> config-dependent",
          v == "config-dependent")
    v, _ = D.derive_verdict(legs("reset", "reset", "reset"))
    check("verdict: both reset -> shared-access-problem",
          v == "shared-access-problem")
    v, _ = D.derive_verdict(legs("results", "results", "results"))
    check("verdict: both respond -> not-reproduced",
          v == "not-reproduced")
    v, _ = D.derive_verdict(legs("results", "reset", "egx-error"))
    check("verdict: repeated A legs disagree -> inconclusive",
          v == "inconclusive")
    v, _ = D.derive_verdict(legs("egx-error", "reset"))
    check("verdict: A error-page + B reset -> inconclusive",
          v == "inconclusive")
    v, _ = D.derive_verdict([{"leg": "A", "classification": "reset"}])
    check("verdict: missing B leg -> inconclusive",
          v == "inconclusive")


def test_launch_configs_differ_as_documented():
    # Leg A carries the harvester's overrides verbatim; leg B
    # carries none. If someone "aligns" the two configs, this test
    # must fail — the difference IS the experiment.
    check("leg A: viewport 1366x768",
          D.LEG_A_VIEWPORT == {"width": 1366, "height": 768})
    check("leg A: timezone Africa/Cairo",
          D.LEG_A_TIMEZONE == "Africa/Cairo")
    check("leg A: AutomationControlled disabled",
          D.LEG_A_ARGS == ["--disable-blink-features="
                           "AutomationControlled"])
    check("leg A: Chrome/124 Windows UA",
          "Chrome/124.0.0.0" in D.LEG_A_USER_AGENT
          and "Windows NT 10.0" in D.LEG_A_USER_AGENT)
    check("leg A: locale ar-EG", D.LEG_A_LOCALE == "ar-EG")
    check("fixed URL is the POUL NewsSearch URL (ISIN + sec_id)",
          D.DIAG_URL == "https://www.egx.com.eg/ar/NewsSearch.aspx"
          "?com=&word=&from=19/08/2026&to=19/11/2026"
          "&isin=EGS02051C018&sec_id=20")
    check("leg configs differ: A has overrides, B has none "
          "(B is launch_persistent_context(profile, headless=True))",
          bool(D.LEG_A_VIEWPORT) and bool(D.LEG_A_ARGS))


def test_stub_server_serves_fixtures():
    srv, base = D.start_stub_server()
    try:
        with urllib.request.urlopen(base + "/ar/NewsSearch.aspx"
                                    "?com=&word=") as r:
            body = r.read().decode("utf-8")
        check("stub: NewsSearch path serves the results fixture",
              r.status == 200 and "NewsDetails.aspx" in body)
        with urllib.request.urlopen(
                base + "/ar/EGX_Error.aspx?aspxerrorpath=/ar/x") as r:
            err = r.read().decode("utf-8")
        check("stub: EGX_Error path serves the 511-char fixture",
              len(err) == 511)
    finally:
        srv.shutdown()


def test_dry_run_subprocess():
    """Run the REAL script --dry-run as a subprocess. Without
    playwright (this VM) it must exit non-zero, name playwright,
    and write NO record. With playwright it must write a record
    whose legs both classify the stub page as results."""
    tmp = tempfile.mkdtemp(prefix="diag-283-dry-")
    out = os.path.join(tmp, "out")
    proc = subprocess.run(
        [sys.executable, os.path.join(HERE, "diag_egx_ab.py"),
         "--dry-run", "--out-dir", out],
        capture_output=True, text=True, timeout=120)
    try:
        import playwright  # noqa: F401
        have_pw = True
    except ImportError:
        have_pw = False
    if not have_pw:
        check("dry-run without playwright: exits non-zero",
              proc.returncode != 0)
        check("dry-run without playwright: names playwright",
              "playwright" in (proc.stderr + proc.stdout).lower())
        check("dry-run without playwright: writes NO record",
              not os.path.exists(os.path.join(out,
                                              "diag-egx-ab.json")))
    else:
        check("dry-run with playwright: exits 0",
              proc.returncode == 0)
        rec = json.loads(open(os.path.join(
            out, "diag-egx-ab.json"), encoding="utf-8").read())
        check("dry-run with playwright: both legs classify the "
              "stub results page as results",
              [l["classification"] for l in rec["legs_records"]] ==
              ["results", "results", "results"])
        check("dry-run with playwright: verdict not-reproduced",
              rec["verdict"] == "not-reproduced")


def main():
    test_classify_results()
    test_classify_egx_error_511()
    test_classify_forbidden_challenge_empty()
    test_classify_nav_error()
    test_verdicts()
    test_launch_configs_differ_as_documented()
    test_stub_server_serves_fixtures()
    test_dry_run_subprocess()
    print("\n%d passed" % PASSED)
    return 0


if __name__ == "__main__":
    sys.exit(main())
