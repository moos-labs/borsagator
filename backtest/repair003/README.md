# REPAIR-003: ORAS.CA cell 3 (cutoff 2023-12-29), Mubasher-only re-run

Why: Yahoo ORAS.CA is a dead feed (279 bars frozen at 71.05). This cell is re-run on the Mubasher series only. No Yahoo bar enters the run.

Data: `mubasher_oras_chartdata_raw.json`, one pull of
`https://english.mubasher.info/api/v1/tadawuly/companyPrices/chartData?symbol=ORAS&country=EG&from=2019-01-02` (needs a `Mozilla/5.0` User-Agent). 1915 bars, 2019-01-03 to 2026-11-26. sha256 8e303811774349c304a965ba65ea1eedef255c3bab905e93dad5b532218ad18f.

Re-run (runners at the registry pins; venvs per runner):
```
MUBASHER_RAW=$PWD/backtest/repair003/mubasher_oras_chartdata_raw.json \
PYTHONPATH=$PWD/backtest/repair003 HF_HOME=<hf cache> KRONOS_SRC=<kronos>/kronos_src \
python3 scripts/backtest.py --cutoff 2023-12-29 --ticker ORAS.CA --out-root <out> \
  --kronos-runner <kronos> --pandas-ta-runner <pandas-ta> --talib-runner <talib> \
  --kronos-python <vk>/bin/python --pandas-ta-python <vp>/bin/python --talib-python <vt>/bin/python \
  --borsagator-root . --repeat-kronos
python3 scripts/backtest_score.py --captures <out> --out <score>
```
`PYTHONPATH` must point at a directory containing `sitecustomize.py`: copy `mubasher_shim_sitecustomize.py` to `sitecustomize.py` there. The shim serves ORAS.CA Yahoo-chart-shaped JSON from the Mubasher file and raises on every other Yahoo URL (so ^EGX30 fails and the index-baseline entrant is absent). It reports an empty, verified events feed: the Mubasher ca/ORAS.json shows no action effective in the realised window (next dividend effective 2024-02-18).

Pins: kronos 6964de99501d6fb855f253150f9421635d820c36, pandas-ta cddf15f3b7fd601eac85cf37a6385996e2b4ed10, talib d41956ca272c430c58c49a743eacc43fcbebc8e4.

Caveats: Mubasher closes may be raw or dividend-adjusted (unknown); no index series; the shim lives outside the pinned runner repos; Kronos ran on CPU (the repeat run showed no diffs).
