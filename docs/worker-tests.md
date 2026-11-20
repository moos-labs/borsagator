# Worker tests

## Running the suite

Script-style tests run directly (exit 0 = all pass, stdlib only, no
network unless the file says otherwise):

```sh
python3 worker/test_worker_149.py
python3 worker/test_worker_147.py
python3 scripts/test_worker_digest_issue_157.py
```

The `unittest`-style files (`worker/test_attachment_capture_279.py`,
`worker/test_pdf_verify_wire_308.py`,
`worker/test_egx_harvest_isin.py`,
`worker/test_egx_harvest_iso_date.py`) run as scripts do nothing --
run them with `unittest` from inside `worker/`:

```sh
cd worker && python3 -m unittest test_attachment_capture_279 \
    test_pdf_verify_wire_308 test_egx_harvest_isin \
    test_egx_harvest_iso_date
```

(or `python3 -m pytest worker/test_attachment_capture_279.py -q`
where pytest is installed). Note: `python3 -m unittest
worker.test_attachment_capture_279` from the repo root does NOT work
-- importing the `worker` package first shadows `worker.py`, so
`worker.now` and friends are missing. That is a pre-existing
invocation quirk, unrelated to #388.

## Scratch dirs and /tmp (#388)

Every worker test creates its scratch area through
`worker/_test_tmp.py` (`_test_tmp.mkdtemp(...)`), which registers
each dir for removal at interpreter exit (`atexit`). Cleanup runs on
clean exit, on `sys.exit` and on unhandled exceptions alike, even
when the test fails, so a full suite run leaves no residue behind.
Nested dirs created inside a tracked dir (`tempfile.mkdtemp(dir=_TMP)`)
need no separate registration: removing the parent removes them.

Debugging a failing test: set `GATOR_TEST_KEEP_TMP=1` to skip the
cleanup and inspect the scratch dir afterwards:

```sh
GATOR_TEST_KEEP_TMP=1 python3 worker/test_worker_149.py
```

## Small tmpfs

On machines where `/tmp` is a small tmpfs, `tempfile` honours
`TMPDIR`, so the suite can be pointed at real disk instead:

```sh
mkdir -p .tmp && TMPDIR=$PWD/.tmp python3 worker/test_worker_149.py
```

## Cleaning up stale scratch from older runs

Runs predating #388 never cleaned up. Remove their leftovers with:

```sh
rm -rf /tmp/test148-* /tmp/test149-* /tmp/test160-* \
    /tmp/gator*-test-* /tmp/wdi157-*
```
