#!/usr/bin/env python3
"""Tests for scripts/gdelt_gkg_filter.py (INS-DATA-002 item 2, G3 pilot).
Standalone, stdlib only, synthetic GKG rows, no network."""
import csv
import importlib.util
import json
import os
import sys
import tempfile
import zipfile

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CHECKS = {"pass": 0, "fail": 0}


def check(name, ok, detail=""):
    CHECKS["pass" if ok else "fail"] += 1
    if not ok:
        print("FAIL %s %s" % (name, detail))


def load(name, fn):
    spec = importlib.util.spec_from_file_location(
        name, os.path.join(ROOT, "scripts", fn))
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


G = load("gkg_t", "gdelt_gkg_filter.py")

ALIASES_CSV = os.path.join(ROOT, "evaluation", "gdelt_alias_table.csv")


def gkg_line(rec="20240515000000-T1", date="20240515000000",
             source="dostor.org", url="https://www.dostor.org/1",
             orgs="Telecom Egypt,123", themes="ECON_STOCKMARKET",
             tone="1.27,2.22,0.95,3.17,1.5,0.5,400", ncols=26):
    cols = [""] * ncols
    off = 1 if ncols >= 27 else 0
    cols[0], cols[1], cols[2 + off], cols[3 + off] = rec, date, source, url
    cols[6 + off], cols[13 + off], cols[14 + off] = themes, orgs, tone
    return "\t".join(cols)


def loaded():
    return G.load_aliases(ALIASES_CSV)


def test_alias_table_loads():
    items, blocks, pre = loaded()
    tickers = {t for _, ts in items for t in ts}
    check("38 tickers", len(tickers) == 38, str(len(tickers)))
    check("every alias nonempty", all(a.strip() for a, _ in items))
    check("prefilter hits normalized line",
          pre(G.norm("x Telecom Egypt y")) and not pre(G.norm("x Vodafone y")))
    check("blocks lowercase-normalized",
          all(b == b.lower() for bs in blocks.values() for b in bs))
    check("PHDC block present",
          "club palm hills" in blocks.get("PHDC", set()), str(blocks.get("PHDC")))


def test_match_orgs_real():
    items, blocks, _ = loaded()
    ts, ent = G.match_orgs("Telecom Egypt,10;Vodafone Egypt,55", items, blocks)
    check("ETEL matched", ts == {"ETEL"}, str(ts))
    check("entry captured", ent == ["Telecom Egypt"], str(ent))
    ts, ent = G.match_orgs("Talaat Moustafa Group Holdings,3", items, blocks)
    check("TMGH via alt", ts == {"TMGH"}, str(ts))
    ts, _ = G.match_orgs("Commercial International Bank,7", items, blocks)
    check("COMI via bank alias", ts == {"COMI"}, str(ts))
    ts, _ = G.match_orgs("السويدي اليكتريك,9", items, blocks)
    check("no unverified arabic alias for SWDY (not in universe)", ts == set(), str(ts))
    ts, _ = G.match_orgs("المصرية للاتصالات,9", items, blocks)
    check("ETEL via verified arabic", ts == {"ETEL"}, str(ts))


def test_match_orgs_blocks_and_noise():
    items, blocks, _ = loaded()
    ts, _ = G.match_orgs("Club Palm Hills,20", items, blocks)
    check("Club Palm Hills blocked for PHDC", ts == set(), str(ts))
    ts, _ = G.match_orgs("Palm Hills Developments,20", items, blocks)
    check("Palm Hills Developments matches PHDC", ts == {"PHDC"}, str(ts))
    ts, _ = G.match_orgs("Negotiations Commercial International,4", items, blocks)
    check("no COMI on bare 'Commercial International'", ts == set(), str(ts))
    ts, _ = G.match_orgs("Telecom Egypt Confidence,4", items, blocks)
    check("Telecom Egypt Confidence blocked for ETEL", ts == set(), str(ts))
    ts, _ = G.match_orgs("Egyptian Exchange,4", items, blocks)
    check("Egyptian Exchange (the bourse) matches nothing", ts == set(), str(ts))


def test_process_blob():
    items, blocks, pre = loaded()
    lines = "\n".join([
        gkg_line(rec="R1", orgs="Telecom Egypt,10"),
        gkg_line(rec="R2", orgs="Club Palm Hills,5", source="example.com",
                 url="https://example.com/a"),
        gkg_line(rec="R3", orgs="", source="almasryalyoum.com",
                 url="https://www.almasryalyoum.com/news/details/1"),
        gkg_line(rec="R4", orgs="Unrelated Corp,1", source="example.net",
                 url="https://example.net/b"),
        gkg_line(rec="R5", orgs="Telecom Egypt,9", source="elfagr.org",
                 url="https://www.elfagr.org/9", ncols=27),
        "too\tfew\tcolumns",
    ])
    rows = G.process_blob("20240515000000.gkg.csv.zip", "english",
                          lines.encode(), items, blocks, pre)
    by_id = {r["gkg_record_id"]: r for r in rows}
    check("R1 alias+both", by_id["R1"]["reason"] == "both"
          and by_id["R1"]["tickers"] == ["ETEL"], str(by_id.get("R1")))
    check("R2 blocked -> dropped", "R2" not in by_id)
    check("R3 eg_domain only, no tickers", by_id["R3"]["reason"] == "eg_domain"
          and by_id["R3"]["tickers"] == [], str(by_id.get("R3")))
    check("R4 noise dropped", "R4" not in by_id)
    check("malformed line skipped", len(rows) == 3, str(len(rows)))
    check("R5 translation layout (27 cols) parsed",
          by_id["R5"]["source"] == "elfagr.org"
          and by_id["R5"]["tickers"] == ["ETEL"]
          and by_id["R5"]["reason"] == "both", str(by_id.get("R5")))
    check("tone parsed", by_id["R1"]["tone"] == "1.27"
          and by_id["R1"]["word_count"] == "400")
    check("blob without needles skipped",
          G.process_blob("f", "english", gkg_line(
              rec="Z", orgs="Nope,1", source="x.io",
              url="https://x.io/").encode(), items, blocks, pre) == [])


def test_list_files_and_range():
    with tempfile.TemporaryDirectory() as d:
        mp = os.path.join(d, "masterfilelist.txt")
        with open(mp, "w") as f:
            f.write("100 md5a http://data.gdeltproject.org/gdeltv2/20240515090000.gkg.csv.zip\n")
            f.write("100 md5b http://data.gdeltproject.org/gdeltv2/20240515091500.gkg.csv.zip\n")
            f.write("100 md5c http://data.gdeltproject.org/gdeltv2/20240601000000.gkg.csv.zip\n")
            f.write("100 md5d http://data.gdeltproject.org/gdeltv2/20240515090000.events.csv.zip\n")
        files = G.list_files([(mp, "english")], "20240501000000", "20240531235959")
        check("only in-range gkg files", [u.rsplit('/',1)[-1] for u, _ in files] ==
              ["20240515090000.gkg.csv.zip", "20240515091500.gkg.csv.zip"], str(files))
        check("stream tag", all(s == "english" for _, s in files))


def test_restart_and_finalize():
    items, blocks, pre = loaded()
    with tempfile.TemporaryDirectory() as d:
        out = d
        blob = gkg_line(rec="R1", orgs="Telecom Egypt,10").encode()
        zpath = os.path.join(d, "z.zip")
        with zipfile.ZipFile(zpath, "w") as z:
            z.writestr("20240515000000.gkg.csv", blob.decode())
        with zipfile.ZipFile(zpath) as z:
            rows = G.process_blob("f", "english", z.read(z.namelist()[0]),
                                  items, blocks, pre)
        # duplicate lines (simulated reprocess after crash) dedupe in finalize
        with open(os.path.join(out, "matches.jsonl"), "w") as f:
            for r in rows + rows:
                f.write(json.dumps(r) + "\n")

        class A:
            pass
        a = A()
        a.out = out
        G.run_finalize(a)
        summary = list(csv.reader(open(os.path.join(out, "alias_hit_summary.csv"))))
        check("summary header", summary[0] == ["ticker", "org_entry", "rows",
                                               "ticker_distinct_days"])
        check("dedupe on finalize", summary[1][2] == "1", str(summary[1]))
        check("final output written",
              os.path.exists(os.path.join(out, "matches.parquet"))
              or os.path.exists(os.path.join(out, "matches.csv")))


def main():
    for fn in (test_alias_table_loads, test_match_orgs_real,
               test_match_orgs_blocks_and_noise, test_process_blob,
               test_list_files_and_range, test_restart_and_finalize):
        fn()
    print("test_gdelt_gkg_filter: %d passed, %d failed"
          % (CHECKS["pass"], CHECKS["fail"]))
    sys.exit(1 if CHECKS["fail"] else 0)


if __name__ == "__main__":
    main()
