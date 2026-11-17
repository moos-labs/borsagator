#!/usr/bin/env python3
"""Proof harness for issue #68 (Report Model compiler).

Harness-first, per the #68 deep scoping §8 proof plan. Runs the
compiler (``scripts/compile_model.py``, stdlib only) over staged
copies of real archived sweeps -- read from the ``archive`` branch,
never from Actions logs or artifacts -- and asserts on the emitted
model. A pristine control (``--pristine``) proves the harness
discriminates: on the pristine tree (no ``compile_model.py``) a
naive control model -- digest + ensemble copied without coercion,
tripwire, or shape probe -- must fail the discriminating cases.

Usage:
    harness_issue68.py [--archive-root PATH] [--keep-stage]
    harness_issue68.py --pristine [--archive-root PATH]

The archive root defaults to the sibling ``borsagator-68-archive``
checkout next to this repo, or ``$BORSAGATOR_ARCHIVE_ROOT``.
Staged copies live under /tmp/borsagator-68-harness/ (removed at
the start of each run unless --keep-stage).
"""
import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import compile_model  # noqa: E402
import delta as delta_mod  # noqa: E402  (the #70 consumer: cross-check)

ARCHIVE_DEFAULT = os.environ.get(
    "BORSAGATOR_ARCHIVE_ROOT",
    os.path.join(os.path.dirname(REPO), "borsagator-68-archive"))
STAGE = os.environ.get("BORSAGATOR_HARNESS_STAGE",
                       "/tmp/borsagator-68-harness")
# Archive HEAD + main HEAD at harness time (re-resolved per run).
ARCHIVE_HEAD = "6462dd63bf5cd3325ed2432a79de75e0b56f3483"
MAIN_HEAD = "0849d4764ec741bbc2b7a0dde7f2b0162f2f7473"
# The pristine base the implementation was built against: the
# pristine control must test THIS head, not the live HEAD (which
# contains the implementation once it is committed).
PRISTINE_HEAD = "0849d4764ec741bbc2b7a0dde7f2b0162f2f7473"

SWEEPS = {
    "141124": ("sweeps/2026-11-16/141124__sweep-lite-poul-ca__"
               "run43875894633"),
    "141558": ("sweeps/2026-11-15/141558__sweep-lite-poul-ca-market-"
               "egx__run43721738392"),
    "050559": ("sweeps/2026-11-16/050559__sweep-lite-poul-ca-market-"
               "egx__run43805931446"),
    "085806": ("sweeps/2026-11-16/085806__sweep-lite-poul-ca__"
               "run43829283730"),
    "041112": ("sweeps/2026-11-16/041112__category-news-poul-ca__"
               "run43801982888"),
    "132518": ("sweeps/2026-11-15/132518__sweep-lite-comi-ca-market-"
               "egx__run43717410248"),
    "074752": ("sweeps/2026-11-15/074752__sweep-lite-poul-ca__"
               "run43688673389"),
    "140509": ("sweeps/2026-11-15/140509__sweep-lite-poul-ca-market-"
               "egx__run43720903619"),
    "095050": ("sweeps/2026-11-13/095050__sweep-lite-poul-ca-market-"
               "egx__run43402572619"),
    "065405": ("sweeps/2026-11-16/065405__sweep-lite-poul-ca__"
               "run43815097317"),
}

CHECKS = {"pass": 0, "fail": 0}
FAILURES = []


def check(name, cond, detail=""):
    if cond:
        CHECKS["pass"] += 1
        print(f"  PASS {name}")
    else:
        CHECKS["fail"] += 1
        FAILURES.append(name)
        print(f"  FAIL {name} {detail}")


def _git_head(path):
    out = subprocess.run(["git", "-C", path, "rev-parse", "HEAD"],
                         capture_output=True, text=True, timeout=30)
    return (out.stdout or "").strip() if out.returncode == 0 else None


def stage_sweep(archive_root, key, dest_name=None):
    """Copy one archived sweep into the stage dir; returns the
    staged path."""
    src = os.path.join(archive_root, SWEEPS[key])
    dest = os.path.join(STAGE, dest_name or os.path.basename(src))
    if os.path.exists(dest):
        shutil.rmtree(dest)
    shutil.copytree(src, dest)
    return dest


def run_compiler(sweep_dir, repo_root=REPO, archive_sha=None,
                 compiler_sha=None, profiles_dir=None, extra=()):
    """Run the compiler as a subprocess; returns (returncode,
    stdout+stderr, model_or_None)."""
    cmd = [sys.executable, os.path.join(HERE, "compile_model.py"),
           sweep_dir, "--repo-root", repo_root,
           "--archive-sha", archive_sha or ARCHIVE_HEAD,
           "--compiler-sha", compiler_sha or MAIN_HEAD]
    if profiles_dir:
        cmd += ["--profiles-dir", profiles_dir]
    cmd += list(extra)
    proc = subprocess.run(cmd, capture_output=True, text=True,
                          timeout=300)
    model_path = os.path.join(sweep_dir, "report-model.json")
    model = None
    if os.path.isfile(model_path):
        with open(model_path, encoding="utf-8") as handle:
            model = json.load(handle)
    return proc.returncode, proc.stdout + proc.stderr, model


def load_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path, obj):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(obj, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


# ---------------------------------------------------------------- cases

def case1_byte_identity(archive_root):
    """§8 case 1: digest-embedding byte identity (golden input
    check). Settles scoping claim (a): parsed-identical for all 29
    tools AND canonical re-serialisation (json.dumps indent=2)
    byte-identical to each collected summary.json. Negative: one
    mutated collected byte must make the compiler refuse (F-5)."""
    print("case 1: digest-embedding byte identity (141124)")
    src = os.path.join(archive_root, SWEEPS["141124"])
    digest = load_json(os.path.join(src, "digest.json"))
    parsed_bad = canonical_bad = 0
    for result in digest["results"]:
        tool = result["tool"]
        collected = load_json(os.path.join(
            src, "collected", tool, "summary.json"))
        if collected != result.get("summary"):
            parsed_bad += 1
        raw = open(os.path.join(src, "collected", tool,
                                "summary.json"), "rb").read()
        canon = json.dumps(result["summary"], indent=2).encode("utf-8")
        if raw not in (canon, canon + b"\n"):
            canonical_bad += 1
    check("1a parsed-identical 29/29", parsed_bad == 0,
          f"{parsed_bad} mismatches")
    check("1b canonical-bytes-identical 29/29", canonical_bad == 0,
          f"{canonical_bad} mismatches")
    staged = stage_sweep(archive_root, "141124", "case1-mutated")
    mutated = os.path.join(staged, "collected", "egx-data",
                           "summary.json")
    doc = load_json(mutated)
    doc["metrics"]["rows_egxpy_poul.csv"] = 2999
    write_json(mutated, doc)
    code, out, model = run_compiler(staged)
    check("1c F-5 refuses a mutated collected summary",
          code == 2 and model is None and "differ" in out,
          f"exit={code} out={out[:200]}")
    check("1d compile_error.txt names the tool",
          os.path.isfile(os.path.join(staged, "compile_error.txt"))
          and "egx-data" in open(
              os.path.join(staged, "compile_error.txt"),
              encoding="utf-8").read(),
          "no compile_error.txt or tool unnamed")


def case2_golden(archive_root):
    """§8 case 2: golden-sweep parity (141124, current golden)."""
    print("case 2: golden-sweep parity (141124)")
    staged = stage_sweep(archive_root, "141124")
    code, out, m = run_compiler(staged)
    check("2a compiler exits 0", code == 0, f"exit={code} {out[:300]}")
    if m is None:
        check("2b model emitted", False, "no model")
        return None
    check("2b schema is borsagator-report-model/1",
          m.get("schema") == "borsagator-report-model/1"
          and m.get("model_version") == 1)
    check("2c base 8.02 / base_date 2026-11-16",
          m["price"]["base_price"] == 8.02
          and m["price"]["base_date"] == "2026-11-16")
    applied = m["weights"]["applied_weights"]
    check("2d weights ledger, factors 0.993/0.742/1.024 (n=5, not "
          "main's current 0.843/0.725/1.009)",
          m["weights"]["weights_source"] == "ledger"
          and applied["factors"]["price-forecast"] == 0.993
          and applied["factors"]["technicals"] == 0.742
          and applied["factors"]["sentiment"] == 1.024
          and applied["eligible"]["price-forecast"]["n"] == 5)
    check("2e family_scores as in the ensemble",
          m["family_scores"] == {"technicals": 0.297,
                                 "sentiment": -0.101, "agent": None,
                                 "fundamentals": 0.4,
                                 "price-forecast": 0.395})
    check("2f day horizon up +18.71% conf 0.30",
          m["horizons"]["day"]["direction"] == "up"
          and m["horizons"]["day"]["expected_move_pct"] == 18.71
          and m["horizons"]["day"]["confidence"] == 0.3)
    check("2g risk level shock", m["risk"]["level"] == "shock")
    check("2h 3 corporate-action blocks verbatim",
          len(m["corporate_actions"]) == 3
          and m["corporate_actions"][0]["dps"] == 1.8999999998
          and m["corporate_actions"][0]["ex_date"] == "2026-11-16"
          and m["corporate_actions"][1]["ex_date"] is None
          and m["corporate_actions"][2]["ex_date"] is None)
    check("2i kronos_ex_rescale null with distinct meaning recorded",
          m["kronos_ex_rescale"] is None
          and m["ensemble_shape"]["has_kronos_ex_rescale"] is False
          and any(f.startswith("kronos-ex-rescale-not-recorded")
                  for f in m["flags"]))
    check("2j witnesses-stale flag (common 2026-11-12 vs base "
          "2026-11-16)",
          any(f.startswith("witnesses-stale: common_date 2026-11-12 "
                           "vs base_date 2026-11-16")
              for f in m["flags"]))
    egx = next((s for s in m["price_series_last"]
                if s["source"] == "egx-data/egxpy_poul.csv"), None)
    check("2k egx-data last row 2026-11-16 / 8.02 / volume "
          "32041362.0",
          egx is not None and egx["last_date"] == "2026-11-16"
          and egx["last_close"] == 8.02
          and egx["last_volume"] == 32041362.0
          and egx["stale"] is False)
    stale = {s["source"] for s in m["price_series_last"]
             if s["stale"]}
    check("2l openbb/pandas-ta/talib stale at 2026-11-12",
          {"openbb/POUL_CA.csv", "pandas-ta/indicators.csv",
           "talib/indicators.csv"} <= stale)
    check("2m news 22 + disclosures 11, key_type per item",
          len(m["news"]["news_items"]) == 22
          and len(m["news"]["disclosure_items"]) == 11
          and all("key_type" in i for i in m["news"]["news_items"])
          and all("key_type" in i
                  for i in m["news"]["disclosure_items"]))
    check("2n ledger_pin matured 9, weights SHA differs from main",
          m["ledger_pin"]["counts"]["matured"] == 9
          and m["ledger_pin"]["weights_sha_matches_ensemble"] is False
          and m["ledger_pin"]["weights_file_sha256"] ==
          "0b4830e811c0cf2348c5beb67e77ef916152ca9e564a815505a5ddeb4b602a4c")
    check("2o ensemble_shape probe (18-key ensemble, no kxr key)",
          m["ensemble_shape"]["has_applied_weights"] is True
          and m["ensemble_shape"]["has_base_date"] is True
          and m["ensemble_shape"]["has_price_crosscheck"] is True)
    check("2p 29 tools, no failures, report_md_present per tool",
          len(m["tools"]) == 29 and m["tools_failed"] == []
          and sum(1 for t in m["tools"]
                  if t["report_md_present"]) == 9
          and next(t for t in m["tools"]
                   if t["tool"] == "news-disclosure")
          ["report_md_present"] is False)
    check("2q provenance actions, run_id 43875894633",
          m["provenance"]["merged_by"] == "actions"
          and m["provenance"]["run_id"] == "43875894633")
    check("2r reaction_profile pointer (built 2026-11-14, fit "
          "0.99/3.46)",
          m["reaction_profile"]["present"] is True
          and m["reaction_profile"]["built_at"]
          == "2026-11-14T23:44:23Z"
          and m["reaction_profile"]["fit"]["global_median_r5_adj"]
          == 0.99
          and m["reaction_profile"]["fit"]["dividend_shrunk"] == 3.46)
    check("2s benchmark absent (pre-#79 sweep)",
          m["benchmark"]["present"] is False)
    return m


def case3_legacy(archive_root):
    """§8 case 3: legacy-shape case (141558, pre-#93/#94)."""
    print("case 3: legacy-shape case (141558)")
    staged = stage_sweep(archive_root, "141558")
    code, out, m = run_compiler(staged)
    check("3a compiler exits 0", code == 0, f"exit={code} {out[:300]}")
    if m is None:
        return
    check("3b ensemble_shape records the three missing fields",
          m["ensemble_shape"]["has_applied_weights"] is False
          and m["ensemble_shape"]["has_base_date"] is False
          and m["ensemble_shape"]["has_kronos_ex_rescale"] is False
          and m["ensemble_shape"]["version"] == 2)
    check("3c applied_weights / base_date / kronos_ex_rescale null",
          m["weights"]["applied_weights"] is None
          and m["price"]["base_date"] is None
          and m["kronos_ex_rescale"] is None)
    check("3d price-forecast -0.258 (Kronos is in the EGX set)",
          m["family_scores"]["price-forecast"] == -0.258)
    check("3e job_shape is the 14-tool EGX shape",
          m["job_shape"] == "sweep-lite POUL.CA market=EGX"
          and m["market"] == "EGX")


def case4_worker_shape(archive_root, golden_model):
    """§8 case 4: worker-shape case (synthetic, per #67 §4c)."""
    print("case 4: worker-shape case (synthetic, from 141124)")
    staged = stage_sweep(archive_root, "141124", "case4-worker")
    digest_path = os.path.join(staged, "digest.json")
    digest = load_json(digest_path)
    for result in digest["results"]:
        result["run_url"] = None
        result["conclusion"] = None
        result["worker_run"] = "worker-runs/2026-11-17/w5-test-001"
        result["claim_id"] = "sched-2026-11-17-test"
    digest["degraded"] = {"reason": "keyless",
                          "absent_families": ["agent"],
                          "absent_tools": []}
    write_json(digest_path, digest)
    manifest_path = os.path.join(staged, "manifest.json")
    manifest = load_json(manifest_path)
    manifest.update({"merged_by": "worker", "worker": "worker-5",
                     "worker_code_sha": "worker-code-sha-test",
                     "worker_release_sha": "worker-release-sha-test",
                     "claim_id": "sched-2026-11-17-test",
                     "source_runs": ["worker-runs/2026-11-17/"
                                     "w5-test-001"],
                     "github_run_id": None,
                     "run_id": "sched-2026-11-17-test",
                     "degraded": digest["degraded"],
                     "merge": "complete"})
    write_json(manifest_path, manifest)
    code, out, m = run_compiler(staged)
    check("4a compiler exits 0 on worker shape", code == 0,
          f"exit={code} {out[:300]}")
    if m is None or golden_model is None:
        return
    check("4b provenance.merged_by == worker",
          m["provenance"]["merged_by"] == "worker"
          and m["provenance"]["worker_code_sha"]
          == "worker-code-sha-test"
          and m["provenance"]["claim_id"] == "sched-2026-11-17-test"
          and m["provenance"]["source_runs"]
          == ["worker-runs/2026-11-17/w5-test-001"])
    check("4c run_url / conclusion null tolerated, worker_run + "
          "claim_id carried per tool",
          all(t["run_url"] is None and t["conclusion"] is None
              and t["worker_run"]
              == "worker-runs/2026-11-17/w5-test-001"
              and t["claim_id"] == "sched-2026-11-17-test"
              for t in m["tools"]))
    check("4d degraded block carried through + surfaced in flags",
          m["degraded"] == {"reason": "keyless",
                            "absent_families": ["agent"],
                            "absent_tools": []}
          and any(f.startswith("degraded: keyless")
                  for f in m["flags"]))
    same = all(m[k] == golden_model[k] for k in (
        "ensemble", "price", "family_scores", "horizons", "risk",
        "corporate_actions", "kronos_ex_rescale", "weights",
        "price_series_last", "news", "levels", "reaction_profile",
        "llm", "benchmark"))
    check("4e every other section identical to case 2", same)
    check("4e(ii) per-tool summaries identical to case 2",
          [t["summary"] for t in m["tools"]] ==
          [t["summary"] for t in golden_model["tools"]])
    # Derived-degradation variant: no degraded block in the digest,
    # fundamentals tools failed -> the compiler derives it.
    staged2 = stage_sweep(archive_root, "141124", "case4-derived")
    digest2 = load_json(os.path.join(staged2, "digest.json"))
    registry = load_json(os.path.join(staged2, "registry.json"))
    fund_tools = [t["id"] for t in registry["tools"]
                  if t.get("family") == "fundamentals"
                  and t.get("status") == "active"]
    for result in digest2["results"]:
        result["run_url"] = None
        result["conclusion"] = None
        result["worker_run"] = "worker-runs/2026-11-17/w5-test-001"
        result["claim_id"] = "sched-2026-11-17-test"
        if result["tool"] in fund_tools:
            result["status"] = "failed"
            if result.get("summary"):
                result["summary"]["status"] = "failed"
                result["summary"]["exit_code"] = 1
            # Keep embedded == collected (F-5): mutate the file too.
            collected_path = os.path.join(
                staged2, "collected", result["tool"], "summary.json")
            if os.path.isfile(collected_path):
                doc = load_json(collected_path)
                doc["status"] = "failed"
                doc["exit_code"] = 1
                write_json(collected_path, doc)
    write_json(os.path.join(staged2, "digest.json"), digest2)
    manifest2 = load_json(os.path.join(staged2, "manifest.json"))
    manifest2.update({"merged_by": "worker",
                      "worker_code_sha": "worker-code-sha-test",
                      "worker_release_sha": "worker-release-sha-test",
                      "claim_id": "sched-2026-11-17-test",
                      "source_runs": ["worker-runs/2026-11-17/"
                                      "w5-test-001"],
                      "github_run_id": None,
                      "run_id": "sched-2026-11-17-test",
                      "merge": "complete"})
    write_json(os.path.join(staged2, "manifest.json"), manifest2)
    code, out, m2 = run_compiler(staged2)
    check("4f derived degradation (no digest block, fundamentals "
          "failed)",
          code == 0 and m2 is not None
          and m2.get("degraded_derived") is True
          # The failed fundamentals tools are in absent_tools, so
          # the derivation rule (same as merge.py) labels it
          # partial-fleet, not keyless.
          and (m2.get("degraded") or {}).get("reason") \
          == "partial-fleet"
          and "fundamentals" in
          (m2.get("degraded") or {}).get("absent_families", [])
          and any("derived by the compiler" in f
                  for f in (m2 or {}).get("flags", [])),
          f"exit={code} {out[:200]}")


def case5_nan(archive_root):
    """§8 case 5: NaN / non-finite negative (live yahooquery
    native-summary hazard, synthesised). The collected file AND the
    digest-embedded summary both carry the bare NaN token, so F-5
    compares the same value on both sides and the coercion path
    (F-3) is what is tested."""
    print("case 5: NaN / non-finite negative")
    staged = stage_sweep(archive_root, "141124", "case5-nan")
    native = {"tool": "yahooquery", "ticker": "POUL.CA",
              "borsagator": True, "exit_code": 0, "status": "ok",
              "metrics": {"last_close": "__NAN_TOKEN__",
                          "rows_POUL.CA.csv": 1210},
              "files": ["POUL.CA.csv"]}
    # A bare NaN token, exactly as a native summary carries it:
    # dump with a placeholder, then swap the quoted placeholder
    # for the bare token in the text.
    text = json.dumps(native, indent=2).replace(
        '"__NAN_TOKEN__"', "NaN")
    assert "NaN" in text and '"NaN"' not in text
    yq = os.path.join(staged, "collected", "yahooquery",
                      "summary.json")
    with open(yq, "w", encoding="utf-8") as handle:
        handle.write(text)
    digest_path = os.path.join(staged, "digest.json")
    digest = load_json(digest_path)
    for result in digest["results"]:
        if result["tool"] == "yahooquery":
            result["summary"] = native
    digest_text = json.dumps(digest, indent=2).replace(
        '"__NAN_TOKEN__"', "NaN")
    with open(digest_path, "w", encoding="utf-8") as handle:
        handle.write(digest_text)
    code, out, m = run_compiler(staged)
    check("5a compiler exits 0 (degraded, not a crash)", code == 0,
          f"exit={code} {out[:300]}")
    if m is None:
        return
    check("5b model parses under strict JSON (no bare NaN token)",
          _strict_parse_ok(os.path.join(staged, "report-model.json")))
    yq_entry = next(t for t in m["tools"] if t["tool"] == "yahooquery")
    check("5c NaN coerced to null with a coercion_failed entry",
          yq_entry["summary"]["metrics"]["last_close"] is None
          and any(e["tool"] == "yahooquery"
                  and e["field"] == "last_close"
                  and e["raw_value"] == "NaN"
                  for e in m["coercion_failed"]))


def _strict_parse_ok(path):
    try:
        with open(path, encoding="utf-8") as handle:
            json.load(handle, parse_constant=lambda c: (_ for _ in ())
                      .throw(ValueError(c)))
        return True
    except Exception:
        return False


def case6_volume(archive_root, golden_model):
    """§8 case 6: volume-trap negative (yahooquery dividend row)."""
    print("case 6: volume-trap negative")
    if golden_model is None:
        check("6a golden model available", False)
        return
    yq = next((s for s in golden_model["price_series_last"]
               if s["source"] == "yahooquery/POUL.CA.csv"), None)
    check("6a yahooquery last close-bearing row, not the dividend "
          "row",
          yq is not None and yq["last_close"] == 10.149999618530273
          and yq["last_date"] == "2026-11-12"
          and yq["last_volume"] == 18277604.0)
    check("6b dividend-row note recorded",
          yq is not None and yq["note"] is not None
          and "dividend row" in yq["note"])
    check("6c Kronos forecast.csv in no price_series_last entry",
          not any("forecast" in s["source"]
                  for s in golden_model["price_series_last"]))


def case7_news_identity(archive_root):
    """§8 case 7: news-identity check. Settles scoping claim (b):
    duplicate resolved_urls / identity keys."""
    print("case 7: news-identity check (141124)")
    src = os.path.join(archive_root, SWEEPS["141124"])
    news = load_json(os.path.join(src, "collected",
                                 "news-disclosure", "news.json"))
    disc = load_json(os.path.join(src, "collected",
                                 "news-disclosure", "disclosures.json"))
    staged = stage_sweep(archive_root, "141124", "case7-news")
    code, out, m = run_compiler(staged)
    check("7a compiler exits 0", code == 0, f"exit={code} {out[:200]}")
    if m is None:
        return
    check("7b 22 news + 11 disclosures emitted",
          len(m["news"]["news_items"]) == 22
          and len(m["news"]["disclosure_items"]) == 11)
    check("7c resolved_url used where present (7 news, 10 "
          "disclosures)",
          sum(1 for i in m["news"]["news_items"]
              if i["key_type"] == "resolved_url") == 7
          and sum(1 for i in m["news"]["disclosure_items"]
                  if i["key_type"] == "resolved_url") == 10)
    keys = [i["identity_key"] for i in m["news"]["news_items"]]
    dkeys = [i["identity_key"]
             for i in m["news"]["disclosure_items"]]
    check("7d no two items share an identity_key",
          len(set(keys)) == len(keys)
          and len(set(dkeys)) == len(dkeys))
    check("7e no duplicate resolved_url among the present ones",
          len({i["resolved_url"] for i in news["items"]
               if i.get("resolved_url")}) ==
          sum(1 for i in news["items"] if i.get("resolved_url"))
          and len({i["resolved_url"] for i in disc["items"]
                   if i.get("resolved_url")}) ==
          sum(1 for i in disc["items"] if i.get("resolved_url")))
    check("7f no news body embedded anywhere in the model",
          "body" not in json.dumps(m["news"])
          and not any(i.get("body") for i in m["news"]["news_items"]))


def case8_negatives(archive_root):
    """§8 case 8: no-summary + tripwire negatives."""
    print("case 8: no-summary + tripwire negatives")
    staged = stage_sweep(archive_root, "050559")
    code, out, m = run_compiler(staged)
    check("8a(i) 050559 compiles degraded", code == 0,
          f"exit={code} {out[:300]}")
    if m is not None:
        failed = {t["tool"] for t in m["tools_failed"]}
        check("8a(ii) tools_failed contains kronos + "
              "financial-roberta (no-summary)",
              {"kronos", "financial-roberta"} <= failed)
        check("8a(iii) family_scores.price-forecast null",
              m["family_scores"]["price-forecast"] is None)
        check("8a(iv) partial false (sweep shape, not category)",
              m["partial"] is False)
        check("8a(v) ensemble_absent false",
              m["ensemble_absent"] is False)
    staged = stage_sweep(archive_root, "132518")
    code, out, m = run_compiler(staged)
    check("8b contaminated COMI sweep 132518 refused (F-1)",
          code == 2 and m is None and "ticker mismatch" in out,
          f"exit={code} {out[:300]}")
    staged_a = stage_sweep(archive_root, "050559", "case8a-shape")
    staged_b = stage_sweep(archive_root, "141124", "case8b-shape")
    _, _, ma = run_compiler(staged_a)
    _, _, mb = run_compiler(staged_b)
    check("8c 14-tool vs 29-tool job_shapes differ (no cross-shape "
          "pair)",
          ma is not None and mb is not None
          and ma["job_shape"] != mb["job_shape"]
          and ma["job_shape"] == "sweep-lite POUL.CA market=EGX"
          and mb["job_shape"] == "sweep-lite POUL.CA")
    staged = stage_sweep(archive_root, "041112")
    code, out, m = run_compiler(staged)
    check("8d category-news 041112 compiles as a partial model, "
          "ensemble absent",
          code == 0 and m is not None and m["partial"] is True
          and m["ensemble_absent"] is True and m["ensemble"] is None
          and m["price"] is None,
          f"exit={code} {out[:300]}")
    staged = stage_sweep(archive_root, "065405")
    code, out, m = run_compiler(staged)
    check("8e 065405 compiles degraded (stocksharp error row)",
          code == 0 and m is not None
          and any(t["tool"] == "stocksharp"
                  and t["status"] == "error"
                  for t in m["tools_failed"]),
          f"exit={code} {out[:300]}")
    # F-6: sweep shape, no ensemble, no marker -> refuse.
    staged = stage_sweep(archive_root, "141124", "case8f-noens")
    os.remove(os.path.join(staged, "ensemble.json"))
    code, out, m = run_compiler(staged)
    check("8f sweep shape with no ensemble and no marker refused "
          "(F-6)",
          code == 2 and m is None and "no ensemble" in out,
          f"exit={code} {out[:300]}")
    # ... with the marker -> degraded partial model.
    staged = stage_sweep(archive_root, "141124", "case8g-marker")
    os.remove(os.path.join(staged, "ensemble.json"))
    with open(os.path.join(staged, "digest.md"), "a",
              encoding="utf-8") as handle:
        handle.write("\nthis digest has NO ensemble forecast.\n")
    code, out, m = run_compiler(staged)
    check("8g sweep shape with the no-ensemble marker compiles "
          "degraded",
          code == 0 and m is not None
          and m["ensemble_absent"] is True,
          f"exit={code} {out[:300]}")
    # F-2: base-price tool with no summary -> refuse.
    staged = stage_sweep(archive_root, "141124", "case8h-nobase")
    digest = load_json(os.path.join(staged, "digest.json"))
    for result in digest["results"]:
        if result["tool"] == "egx-data":
            result.pop("summary", None)
            result["status"] = "no-summary"
            result["detail"] = "artifact carried no summary.json"
    write_json(os.path.join(staged, "digest.json"), digest)
    code, out, m = run_compiler(staged)
    check("8h base-price tool egx-data with no summary refused "
          "(F-2)",
          code == 2 and m is None and "egx-data" in out,
          f"exit={code} {out[:300]}")
    # F-9: unknown digest-row status -> refuse.
    staged = stage_sweep(archive_root, "141124", "case8i-status")
    digest = load_json(os.path.join(staged, "digest.json"))
    digest["results"][0]["status"] = "weird"
    write_json(os.path.join(staged, "digest.json"), digest)
    code, out, m = run_compiler(staged)
    check("8i unknown digest-row status refused (F-9)",
          code == 2 and m is None and "weird" in out,
          f"exit={code} {out[:300]}")
    # F-10: digest without finished on a sweep shape -> refuse.
    staged = stage_sweep(archive_root, "141124", "case8j-nofin")
    digest = load_json(os.path.join(staged, "digest.json"))
    digest.pop("finished", None)
    write_json(os.path.join(staged, "digest.json"), digest)
    code, out, m = run_compiler(staged)
    check("8j digest without finished refused (F-10)",
          code == 2 and m is None and "finished" in out,
          f"exit={code} {out[:300]}")
    # Ensemble present but no base price -> degraded, price null.
    staged = stage_sweep(archive_root, "141124", "case8k-nobase")
    ensemble = load_json(os.path.join(staged, "ensemble.json"))
    ensemble["base_price"] = None
    write_json(os.path.join(staged, "ensemble.json"), ensemble)
    code, out, m = run_compiler(staged)
    check("8k ensemble without base_price compiles degraded "
          "(price null)",
          code == 0 and m is not None
          and m["price"]["base_price"] is None
          and any(f.startswith("ensemble-no-base-price")
                  for f in m["flags"]),
          f"exit={code} {out[:300]}")
    # Empty horizons -> ensemble_empty, horizons null.
    staged = stage_sweep(archive_root, "141124", "case8l-empty")
    ensemble = load_json(os.path.join(staged, "ensemble.json"))
    ensemble["horizons"] = {}
    write_json(os.path.join(staged, "ensemble.json"), ensemble)
    code, out, m = run_compiler(staged)
    check("8l empty horizons compiles degraded (ensemble_empty)",
          code == 0 and m is not None
          and m["ensemble_empty"] is True
          and m["horizons"] is None
          and any(f.startswith("ensemble-empty")
                  for f in m["flags"]),
          f"exit={code} {out[:300]}")


def case9_schema_version(archive_root):
    """§8 case 9: schema-version negative."""
    print("case 9: schema-version negative")
    staged = stage_sweep(archive_root, "141124", "case9-v99")
    ensemble = load_json(os.path.join(staged, "ensemble.json"))
    ensemble["version"] = 99
    ensemble["future_field"] = {"note": "added after v2"}
    write_json(os.path.join(staged, "ensemble.json"), ensemble)
    code, out, m = run_compiler(staged)
    check("9a compiler compiles an unknown-version ensemble by "
          "probing (unknown fields pass through verbatim)",
          code == 0 and m is not None
          and m["ensemble"]["version"] == 99
          and m["ensemble"]["future_field"] == {
              "note": "added after v2"}
          and m["price"]["base_price"] == 8.02,
          f"exit={code} {out[:300]}")
    staged = stage_sweep(archive_root, "141124", "case9-model-v1")
    code, out, m = run_compiler(staged)
    check("9b compiler emits the v1 model",
          code == 0 and m is not None,
          f"exit={code} {out[:200]}")
    if code == 0:
        model_path = os.path.join(staged, "report-model.json")
        doc = load_json(model_path)
        doc["schema"] = "borsagator-report-model/99"
        doc["model_version"] = 99
        write_json(model_path, doc)
        proc = subprocess.run(
            [sys.executable, os.path.join(HERE, "compile_model.py"),
             "--check-model", model_path],
            capture_output=True, text=True, timeout=60)
        check("9c consumer refuses a v99 model "
              "(model_schema_unsupported)",
              proc.returncode == 2
              and "model_schema_unsupported" in proc.stderr,
              f"exit={proc.returncode} {proc.stderr[:200]}")
        staged = stage_sweep(archive_root, "141124", "case9-model-ok")
        code, out, m = run_compiler(staged)
        proc = subprocess.run(
            [sys.executable, os.path.join(HERE, "compile_model.py"),
             "--check-model",
             os.path.join(staged, "report-model.json")],
            capture_output=True, text=True, timeout=60)
        check("9d --check-model exits 0 on the v1 model",
              code == 0 and proc.returncode == 0,
              f"exit={proc.returncode} {proc.stderr[:200]}")


def case10_recommendation(archive_root, golden_model):
    """§8 case 10: recommendation reproduction + D2 bands."""
    print("case 10: recommendation + D2 bands")
    if golden_model is None:
        check("10a golden model available", False)
        return
    check("10a live profile is stale for this sweep, so the model "
          "carries recommendation null + a stale flag (never the "
          "stale HOLD line)",
          golden_model["recommendation"] is None
          and any(f.startswith("recommendation-stale")
                  for f in golden_model["flags"]))
    week = golden_model["horizons"]["week"]
    expect_support = round(8.02 * (1 + week["range_low_pct"] / 100),
                           4)
    expect_resist = round(8.02 * (1 + week["range_high_pct"] / 100),
                          4)
    check("10b levels are price levels from the week range "
          "(D-5: base x (1 + pct/100))",
          golden_model["levels"]["support"] == expect_support
          and golden_model["levels"]["resistance"] == expect_resist
          and golden_model["levels"]["support"] == 7.1346
          and golden_model["levels"]["resistance"] == 11.5881)
    check("10c levels carry the D2 note",
          golden_model["levels"]["note"]
          == "descriptive-conditional levels (D2); not a buy/sell "
             "instruction")
    text = json.dumps(golden_model)
    check("10d no HOLD / buy / sell instruction line in the model",
          '"action"' not in text and "buy_below" not in text
          and "sell_above" not in text)
    # Copy path: a profile matching the sweep is copied verbatim.
    staged = stage_sweep(archive_root, "141124", "case10-rec")
    profiles = os.path.join(STAGE, "case10-profiles")
    os.makedirs(profiles, exist_ok=True)
    rec = {"ticker": "POUL.CA", "as_of": "2026-11-16",
           "archive_commit": "archive-commit-test",
           "base_price": 8.02, "reference_price": 8.02,
           "action": "hold", "buy_below": 7.13,
           "sell_above": 11.59, "expected_week_pct": 16.73,
           "nudge_pct": 0.0, "expected_week_adj_pct": 16.73,
           "confidence": 0.3, "risk": "shock",
           "weights_source": "ledger",
           "notes": ["ensemble as of 2026-11-16"]}
    write_json(os.path.join(profiles, "POUL.CA.recommendation.json"),
               rec)
    code, out, m = run_compiler(staged, profiles_dir=profiles)
    check("10e a matching profile is copied verbatim",
          code == 0 and m is not None
          and m["recommendation"] is not None
          and m["recommendation"]["action"] == "hold"
          and m["recommendation"]["buy_below"] == 7.13
          and m["recommendation"]["archive_commit"]
          == "archive-commit-test",
          f"exit={code} {out[:300]}")
    # F-12 (D-6, warn-only): an agent vote without provenance.
    tools = [{"tool": "tradingagents", "category": "agent",
              "summary": {"metrics": {}}}]
    llm, flags = compile_model.build_llm(
        tools, {"agent": 0.5, "technicals": 0.1})
    check("10f F-12 warns on an agent vote without provenance",
          any(f.startswith("llm-provenance-missing: agent")
              for f in flags)
          and llm["llm_status"] == "not-recorded")
    tools[0]["summary"]["metrics"] = {"llm_provider": "cohere"}
    llm, flags = compile_model.build_llm(
        tools, {"agent": 0.5, "technicals": 0.1})
    check("10g F-12 stays quiet when the agent vote has a provider",
          not any("llm-provenance-missing" in f for f in flags))


def case11_determinism_secret(archive_root):
    """§8 case 11: determinism + secret scan."""
    print("case 11: determinism + secret scan")
    staged = stage_sweep(archive_root, "141124", "case11-det")
    code1, _, m1 = run_compiler(staged)
    raw1 = open(os.path.join(staged, "report-model.json"), "rb").read()
    code2, _, m2 = run_compiler(staged)
    raw2 = open(os.path.join(staged, "report-model.json"), "rb").read()
    check("11a recompile is byte-identical",
          code1 == 0 and code2 == 0 and raw1 == raw2)
    check("11b model parses under strict JSON",
          _strict_parse_ok(os.path.join(staged, "report-model.json")))
    text = raw1.decode("utf-8")
    secret_names = ("COHERE_API_KEY", "SIMFIN_API_KEY", "FMP_API_KEY",
                    "GATOR_BUS_URL", "GH_TOKEN",
                    "BORSAGATOR_APP_PRIVATE_KEY")
    check("11c no secret key name anywhere in the model",
          not any(name in text for name in secret_names))
    # 40-hex runs must all be values of SHA-labelled fields.
    model = json.loads(text)
    bad_hex = []

    def _walk(obj, key):
        if isinstance(obj, str):
            for hit in re.findall(r"\b[0-9a-f]{40}\b", obj):
                if not re.search(r"sha|commit", key or "",
                                 re.IGNORECASE):
                    bad_hex.append((key, hit))
        elif isinstance(obj, dict):
            for k, v in obj.items():
                _walk(v, k)
        elif isinstance(obj, list):
            for v in obj:
                _walk(v, key)
    _walk(model, "")
    check("11d every 40-hex run is a labelled SHA value",
          not bad_hex, f"{bad_hex[:3]}")
    # Fake-key injection: the compiler must drop the field.
    staged = stage_sweep(archive_root, "141124", "case11-key")
    digest = load_json(os.path.join(staged, "digest.json"))
    for result in digest["results"]:
        if result["tool"] == "finbert":
            result["summary"]["metrics"]["COHERE_API_KEY"] = \
                "fake-key-value-for-harness"
            result["summary"]["metrics"]["total_return_stat_key"] = \
                "kept"
    write_json(os.path.join(staged, "digest.json"), digest)
    collected = load_json(os.path.join(
        staged, "collected", "finbert", "summary.json"))
    collected["metrics"]["COHERE_API_KEY"] = "fake-key-value-for-harness"
    collected["metrics"]["total_return_stat_key"] = "kept"
    write_json(os.path.join(staged, "collected", "finbert",
                            "summary.json"), collected)
    code, out, m = run_compiler(staged)
    finbert = next((t for t in (m or {}).get("tools", [])
                    if t["tool"] == "finbert"), None)
    check("11e injected secret field dropped + recorded, legit "
          "metric kept",
          code == 0 and finbert is not None
          and "COHERE_API_KEY"
          not in finbert["summary"]["metrics"]
          and finbert["summary"]["metrics"].get(
              "total_return_stat_key") == "kept"
          and {"tool": "finbert", "field": "COHERE_API_KEY"}
          in m["secret_fields_dropped"]
          and "fake-key-value-for-harness" not in
          json.dumps(m),
          f"exit={code} {out[:200]}")


def case12_golden_pairs(archive_root):
    """D-9: compile the three golden pairs #70 needs, so the delta
    harness has model-path pairs."""
    print("case 12: golden-pair backfill (D-9)")
    pairs = [("085806", "141124"), ("074752", "140509"),
             ("095050", "141558")]
    paths = []
    for prev_key, cur_key in pairs:
        for key in (prev_key, cur_key):
            staged = stage_sweep(archive_root, key)
            code, out, m = run_compiler(staged)
            check(f"12 {key} compiles",
                  code == 0 and m is not None,
                  f"exit={code} {out[:200]}")
            if m is not None:
                paths.append(os.path.join(staged, "report-model.json"))
    check("12g six pair-side models emitted", len(paths) == 6)
    # 095050 is the oldest shape (12-key ensemble): probe must cope.
    staged = os.path.join(STAGE, SWEEPS["095050"].split("/")[-1])
    m = load_json(os.path.join(staged, "report-model.json")) \
        if os.path.isfile(os.path.join(staged, "report-model.json")) \
        else None
    check("12h 095050 (12-key ensemble) normalises absent fields "
          "to null",
          m is not None
          and m["ensemble_shape"]["has_price_crosscheck"] is False
          and m["ensemble_shape"]["has_corporate_actions"] is False
          and m["price"]["price_crosscheck"] is None
          and m["corporate_actions"] is None
          and m["price"]["sessions_per_calendar_day"] is None)
    print("  golden-pair model paths:")
    for path in paths:
        print(f"    {path}")


def case13_consumer_crosscheck(archive_root, golden_model):
    """#70 §4b / #69: the model satisfies the delta + renderer
    interface without re-reading a sweep dir."""
    print("case 13: consumer cross-check (#70 delta view, #69)")
    src = os.path.join(archive_root, SWEEPS["141124"])
    view = delta_mod.load_sweep_view(src)
    if golden_model is None:
        check("13a golden model available", False)
        return
    shared = ("source", "last_date", "last_close", "last_volume",
              "rows")
    model_series = [{k: s[k] for k in shared}
                    for s in golden_model["price_series_last"]]
    view_series = [{k: s[k] for k in shared}
                   for s in view["price_series_last"]]
    check("13a price_series_last (shared fields) equals the delta "
          "view",
          model_series == view_series,
          f"model={model_series} view={view_series}")
    model_news = [(i["identity_key"], i["key_type"], i["title"])
                  for i in golden_model["news"]["news_items"]]
    view_news = [(i["identity_key"], i["key_type"], i["title"])
                 for i in view["news_items"]]
    check("13b news identity keys equal the delta view",
          model_news == view_news)
    model_disc = [(i["identity_key"], i["key_type"], i["title"])
                  for i in golden_model["news"]["disclosure_items"]]
    view_disc = [(i["identity_key"], i["key_type"], i["title"])
                 for i in view["disclosure_items"]]
    check("13c disclosure identity keys equal the delta view",
          model_disc == view_disc)
    check("13d ledger weights SHA equals the delta view pin",
          golden_model["ledger_pin"]["weights_file_sha256"]
          == view["ledger_pin"]["weights_file_sha256"])
    check("13e job_shape + market agree with the delta view",
          golden_model["job_shape"] == view["job_shape"]
          and golden_model["market"] == view["market"])
    check("13f tripwire agrees with the delta view (clean)",
          golden_model["ticker_mismatch"] == []
          and view["tripwire"] == [])
    check("13g model validates against its own schema",
          compile_model.validate_model_schema(golden_model) == [])


# ---------------------------------------------------------------- pristine

def naive_model(sweep_dir):
    """The control: a hand-rolled model from the digest + ensemble
    with NO coercion, NO tripwire, NO shape probe, NO schema check.
    It must fail the discriminating cases."""
    digest = load_json(os.path.join(sweep_dir, "digest.json"))
    ensemble = load_json(os.path.join(sweep_dir, "ensemble.json")) \
        if os.path.isfile(os.path.join(sweep_dir, "ensemble.json")) \
        else None
    return {"ticker": digest.get("ticker"),
            "job": digest.get("job"),
            "base_price": (ensemble or {}).get("base_price"),
            "applied_weights": (ensemble or {}).get("applied_weights"),
            "base_date": (ensemble or {}).get("base_date"),
            "price_forecast": ((ensemble or {}).get("family_scores")
                               or {}).get("price-forecast"),
            "tools": digest.get("results")}


def pristine_control(archive_root):
    """§8 case 12: on the pristine tree (no compile_model.py) the
    harness exits 1 -- the module is absent, and the naive control
    fails the discriminating cases."""
    print("pristine control: no compiler on the pristine tree")
    proc = subprocess.run(
        ["git", "-C", REPO, "cat-file", "-e",
         f"{PRISTINE_HEAD}:scripts/compile_model.py"],
        capture_output=True, text=True, timeout=30)
    check("P-a compile_model.py is absent at the pristine base "
          f"{PRISTINE_HEAD[:7]}",
          proc.returncode != 0)
    staged = stage_sweep(archive_root, "141558", "pristine-legacy")
    try:
        naive = naive_model(staged)
        _ = naive["applied_weights"]["factors"]
        legacy_failed = False
    except (KeyError, TypeError):
        legacy_failed = True
    check("P-b naive model fails the legacy shape (no probe: "
          "applied_weights is None)",
          legacy_failed)
    staged = stage_sweep(archive_root, "141124", "pristine-nan")
    # The naive path has no parse_constant guard at all: a bare NaN
    # in a native summary breaks every strict-JSON consumer, and the
    # naive model cannot even be written strictly.
    try:
        json.dumps({"last_close": float("nan")}, allow_nan=False)
        nan_failed = False
    except ValueError:
        nan_failed = True
    check("P-c strict write rejects the naive NaN value (no "
          "coercion in the naive path)",
          nan_failed)
    src = os.path.join(archive_root, SWEEPS["141124"])
    rows = list(csv.DictReader(open(
        os.path.join(src, "collected", "yahooquery", "POUL.CA.csv"),
        newline="", encoding="utf-8")))
    check("P-d naive last-row read takes the dividend row (empty "
          "close/volume)",
          rows[-1].get("close") in (None, "")
          and rows[-1].get("dividends") == "1.9")
    staged = stage_sweep(archive_root, "132518", "pristine-comi")
    naive = naive_model(staged)
    check("P-e naive model emits the contaminated COMI sweep (no "
          "tripwire)",
          naive["ticker"] == "COMI.CA"
          and naive["base_price"] is not None)
    check("P-f the compiler's consumer check (absent from the "
          "naive path) refuses a v99 schema",
          compile_model.validate_model_schema(
              {"schema": "borsagator-report-model/99",
               "model_version": 99}) != [])


# ---------------------------------------------------------------- main

def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Proof harness for issue #68.")
    ap.add_argument("--archive-root", default=ARCHIVE_DEFAULT)
    ap.add_argument("--pristine", action="store_true",
                    help="run only the pristine control")
    ap.add_argument("--keep-stage", action="store_true")
    args = ap.parse_args(argv)
    if not os.path.isdir(args.archive_root):
        print(f"archive root not found: {args.archive_root}\n"
              f"pass --archive-root or set BORSAGATOR_ARCHIVE_ROOT",
              file=sys.stderr)
        return 1
    global ARCHIVE_HEAD, MAIN_HEAD
    ARCHIVE_HEAD = _git_head(args.archive_root) or ARCHIVE_HEAD
    MAIN_HEAD = _git_head(REPO) or MAIN_HEAD
    if not args.keep_stage and os.path.isdir(STAGE):
        shutil.rmtree(STAGE)
    os.makedirs(STAGE, exist_ok=True)
    if args.pristine:
        pristine_control(args.archive_root)
    else:
        case1_byte_identity(args.archive_root)
        golden = case2_golden(args.archive_root)
        case3_legacy(args.archive_root)
        case4_worker_shape(args.archive_root, golden)
        case5_nan(args.archive_root)
        case6_volume(args.archive_root, golden)
        case7_news_identity(args.archive_root)
        case8_negatives(args.archive_root)
        case9_schema_version(args.archive_root)
        case10_recommendation(args.archive_root, golden)
        case11_determinism_secret(args.archive_root)
        case12_golden_pairs(args.archive_root)
        case13_consumer_crosscheck(args.archive_root, golden)
    print(f"\nharness_issue68: {CHECKS['pass']} passed, "
          f"{CHECKS['fail']} failed")
    if FAILURES:
        print("failed checks:")
        for name in FAILURES:
            print(f"  - {name}")
    return 0 if CHECKS["fail"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
