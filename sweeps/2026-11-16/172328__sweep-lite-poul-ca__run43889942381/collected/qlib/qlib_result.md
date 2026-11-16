# Qlib pilot result — LightGBM + Alpha158 (qlib benchmark)

- Generated (UTC): 2026-11-16T17:04:43.271223+00:00
- Total wall time: 83.1s
- Overall exit code: 0

## Setup

- Python: 3.11.18
- pyqlib: 0.9.6
- lightgbm: 4.7.0
- pandas: 2.2.3
- numpy: 1.26.4
- mlflow: 2.22.5
- Workflow config: `scripts/workflow_config_lightgbm_Alpha158.yaml` (vendored from microsoft/qlib `examples/benchmarks/LightGBM/`)
- Market / instruments: **csi300** (config `market: csi300`), benchmark **SH000300**, region **cn**
- Segments: train 2008-01-01..2014-12-31, valid 2015-01-01..2016-12-31, test 2017-01-01..2020-08-01; backtest 2017-01-01..2020-08-01, TopkDropoutStrategy topk=50 n_drop=5

## Data

- Route used: official: python -m qlib.run.get_data qlib_data --region cn
- Data dir: `/home/runner/.qlib/qlib_data/cn_data`
- Calendar: 1999-11-10 .. 2020-09-25 (4943 trading days, calendars/day.txt)
- Instruments: csi300.txt rows=820, all.txt rows=3875, feature dirs=3875

## Recorder metrics (quoted verbatim from mlflow metric files)

| experiment | run | metric | value | source file |
|---|---|---|---|---|
| workflow | ba647e2d | 1day.excess_return_with_cost.annualized_return | 0.08065424981584694 | `/home/runner/work/qlib-runner/qlib-runner/qlib_run/mlruns/815553957004772421/ba647e2df2df4dc7bcda9184c75c63e4/metrics/1day.excess_return_with_cost.annualized_return` |
| workflow | ba647e2d | 1day.excess_return_with_cost.information_ratio | 0.9144858856010738 | `/home/runner/work/qlib-runner/qlib-runner/qlib_run/mlruns/815553957004772421/ba647e2df2df4dc7bcda9184c75c63e4/metrics/1day.excess_return_with_cost.information_ratio` |
| workflow | ba647e2d | 1day.excess_return_with_cost.max_drawdown | -0.08608280684938441 | `/home/runner/work/qlib-runner/qlib-runner/qlib_run/mlruns/815553957004772421/ba647e2df2df4dc7bcda9184c75c63e4/metrics/1day.excess_return_with_cost.max_drawdown` |
| workflow | ba647e2d | 1day.excess_return_with_cost.mean | 0.00033888340258759217 | `/home/runner/work/qlib-runner/qlib-runner/qlib_run/mlruns/815553957004772421/ba647e2df2df4dc7bcda9184c75c63e4/metrics/1day.excess_return_with_cost.mean` |
| workflow | ba647e2d | 1day.excess_return_with_cost.std | 0.0057169154684739145 | `/home/runner/work/qlib-runner/qlib-runner/qlib_run/mlruns/815553957004772421/ba647e2df2df4dc7bcda9184c75c63e4/metrics/1day.excess_return_with_cost.std` |
| workflow | ba647e2d | 1day.excess_return_without_cost.annualized_return | 0.12602897949315695 | `/home/runner/work/qlib-runner/qlib-runner/qlib_run/mlruns/815553957004772421/ba647e2df2df4dc7bcda9184c75c63e4/metrics/1day.excess_return_without_cost.annualized_return` |
| workflow | ba647e2d | 1day.excess_return_without_cost.information_ratio | 1.4285742844475489 | `/home/runner/work/qlib-runner/qlib-runner/qlib_run/mlruns/815553957004772421/ba647e2df2df4dc7bcda9184c75c63e4/metrics/1day.excess_return_without_cost.information_ratio` |
| workflow | ba647e2d | 1day.excess_return_without_cost.max_drawdown | -0.07230960299230565 | `/home/runner/work/qlib-runner/qlib-runner/qlib_run/mlruns/815553957004772421/ba647e2df2df4dc7bcda9184c75c63e4/metrics/1day.excess_return_without_cost.max_drawdown` |
| workflow | ba647e2d | 1day.excess_return_without_cost.mean | 0.000529533527282172 | `/home/runner/work/qlib-runner/qlib-runner/qlib_run/mlruns/815553957004772421/ba647e2df2df4dc7bcda9184c75c63e4/metrics/1day.excess_return_without_cost.mean` |
| workflow | ba647e2d | 1day.excess_return_without_cost.std | 0.005718460332956042 | `/home/runner/work/qlib-runner/qlib-runner/qlib_run/mlruns/815553957004772421/ba647e2df2df4dc7bcda9184c75c63e4/metrics/1day.excess_return_without_cost.std` |
| workflow | ba647e2d | 1day.ffr | 1.0 | `/home/runner/work/qlib-runner/qlib-runner/qlib_run/mlruns/815553957004772421/ba647e2df2df4dc7bcda9184c75c63e4/metrics/1day.ffr` |
| workflow | ba647e2d | 1day.pa | 0.0 | `/home/runner/work/qlib-runner/qlib-runner/qlib_run/mlruns/815553957004772421/ba647e2df2df4dc7bcda9184c75c63e4/metrics/1day.pa` |
| workflow | ba647e2d | 1day.pos | 0.0 | `/home/runner/work/qlib-runner/qlib-runner/qlib_run/mlruns/815553957004772421/ba647e2df2df4dc7bcda9184c75c63e4/metrics/1day.pos` |
| workflow | ba647e2d | IC | 0.04680587323833807 | `/home/runner/work/qlib-runner/qlib-runner/qlib_run/mlruns/815553957004772421/ba647e2df2df4dc7bcda9184c75c63e4/metrics/IC` |
| workflow | ba647e2d | ICIR | 0.3815683918932705 | `/home/runner/work/qlib-runner/qlib-runner/qlib_run/mlruns/815553957004772421/ba647e2df2df4dc7bcda9184c75c63e4/metrics/ICIR` |
| workflow | ba647e2d | Rank IC | 0.049049290457489736 | `/home/runner/work/qlib-runner/qlib-runner/qlib_run/mlruns/815553957004772421/ba647e2df2df4dc7bcda9184c75c63e4/metrics/Rank IC` |
| workflow | ba647e2d | Rank ICIR | 0.406748756941287 | `/home/runner/work/qlib-runner/qlib-runner/qlib_run/mlruns/815553957004772421/ba647e2df2df4dc7bcda9184c75c63e4/metrics/Rank ICIR` |
| workflow | ba647e2d | l2.train | 0.9645443274938363 | `/home/runner/work/qlib-runner/qlib-runner/qlib_run/mlruns/815553957004772421/ba647e2df2df4dc7bcda9184c75c63e4/metrics/l2.train` |
| workflow | ba647e2d | l2.valid | 0.9950544899629332 | `/home/runner/work/qlib-runner/qlib-runner/qlib_run/mlruns/815553957004772421/ba647e2df2df4dc7bcda9184c75c63e4/metrics/l2.valid` |

## Portfolio risk analysis (port_analysis, qlib's own tables)

Source: `/home/runner/work/qlib-runner/qlib-runner/qlib_run/mlruns/815553957004772421/ba647e2df2df4dc7bcda9184c75c63e4/artifacts/portfolio_analysis/port_analysis_1day.pkl`

|  | risk |
|---|---|
| ('excess_return_without_cost', 'mean') | 0.000529533527282172 |
| ('excess_return_without_cost', 'std') | 0.005718460332956042 |
| ('excess_return_without_cost', 'annualized_return') | 0.12602897949315695 |
| ('excess_return_without_cost', 'information_ratio') | 1.4285742844475489 |
| ('excess_return_without_cost', 'max_drawdown') | -0.07230960299230565 |
| ('excess_return_with_cost', 'mean') | 0.00033888340258759217 |
| ('excess_return_with_cost', 'std') | 0.0057169154684739145 |
| ('excess_return_with_cost', 'annualized_return') | 0.08065424981584694 |
| ('excess_return_with_cost', 'information_ratio') | 0.9144858856010738 |
| ('excess_return_with_cost', 'max_drawdown') | -0.08608280684938441 |


## Recorder artifacts

- `/home/runner/work/qlib-runner/qlib-runner/qlib_run/mlruns/815553957004772421/ba647e2df2df4dc7bcda9184c75c63e4/artifacts/code_cached.txt` (0 bytes)
- `/home/runner/work/qlib-runner/qlib-runner/qlib_run/mlruns/815553957004772421/ba647e2df2df4dc7bcda9184c75c63e4/artifacts/code_diff.txt` (0 bytes)
- `/home/runner/work/qlib-runner/qlib-runner/qlib_run/mlruns/815553957004772421/ba647e2df2df4dc7bcda9184c75c63e4/artifacts/code_status.txt` (239 bytes)
- `/home/runner/work/qlib-runner/qlib-runner/qlib_run/mlruns/815553957004772421/ba647e2df2df4dc7bcda9184c75c63e4/artifacts/config` (155947 bytes)
- `/home/runner/work/qlib-runner/qlib-runner/qlib_run/mlruns/815553957004772421/ba647e2df2df4dc7bcda9184c75c63e4/artifacts/dataset` (9968 bytes)
- `/home/runner/work/qlib-runner/qlib-runner/qlib_run/mlruns/815553957004772421/ba647e2df2df4dc7bcda9184c75c63e4/artifacts/label.pkl` (2123259 bytes)
- `/home/runner/work/qlib-runner/qlib-runner/qlib_run/mlruns/815553957004772421/ba647e2df2df4dc7bcda9184c75c63e4/artifacts/params.pkl` (144733 bytes)
- `/home/runner/work/qlib-runner/qlib-runner/qlib_run/mlruns/815553957004772421/ba647e2df2df4dc7bcda9184c75c63e4/artifacts/portfolio_analysis/indicator_analysis_1day.pkl` (662 bytes)
- `/home/runner/work/qlib-runner/qlib-runner/qlib_run/mlruns/815553957004772421/ba647e2df2df4dc7bcda9184c75c63e4/artifacts/portfolio_analysis/indicators_normal_1day.pkl` (49877 bytes)
- `/home/runner/work/qlib-runner/qlib-runner/qlib_run/mlruns/815553957004772421/ba647e2df2df4dc7bcda9184c75c63e4/artifacts/portfolio_analysis/indicators_normal_1day_obj.pkl` (8698903 bytes)
- `/home/runner/work/qlib-runner/qlib-runner/qlib_run/mlruns/815553957004772421/ba647e2df2df4dc7bcda9184c75c63e4/artifacts/portfolio_analysis/port_analysis_1day.pkl` (1090 bytes)
- `/home/runner/work/qlib-runner/qlib-runner/qlib_run/mlruns/815553957004772421/ba647e2df2df4dc7bcda9184c75c63e4/artifacts/portfolio_analysis/positions_normal_1day.pkl` (3443320 bytes)
- `/home/runner/work/qlib-runner/qlib-runner/qlib_run/mlruns/815553957004772421/ba647e2df2df4dc7bcda9184c75c63e4/artifacts/portfolio_analysis/report_normal_1day.pkl` (71190 bytes)
- `/home/runner/work/qlib-runner/qlib-runner/qlib_run/mlruns/815553957004772421/ba647e2df2df4dc7bcda9184c75c63e4/artifacts/pred.pkl` (3168458 bytes)
  (pred.pkl converted to pred.csv: (261300, 1) rows/cols)
- `/home/runner/work/qlib-runner/qlib-runner/qlib_run/mlruns/815553957004772421/ba647e2df2df4dc7bcda9184c75c63e4/artifacts/sig_analysis/ic.pkl` (21834 bytes)
- `/home/runner/work/qlib-runner/qlib-runner/qlib_run/mlruns/815553957004772421/ba647e2df2df4dc7bcda9184c75c63e4/artifacts/sig_analysis/ric.pkl` (21834 bytes)
- `/home/runner/work/qlib-runner/qlib-runner/qlib_run/mlruns/815553957004772421/ba647e2df2df4dc7bcda9184c75c63e4/artifacts/task` (1427 bytes)

## Files copied into results/

- port_analysis_1day.csv
- port_analysis_1day.pkl
- report_normal_1day.csv
- pred.csv

## Full pilot log

```
# Qlib pilot run
Started (UTC): 2026-11-16T17:03:20.148354+00:00
Python: 3.11.18
pyqlib: 0.9.6
lightgbm: 4.7.0
pandas: 2.2.3
numpy: 1.26.4
mlflow: 2.22.5

## Stage 1: data download
$ /opt/hostedtoolcache/Python/3.11.18/x64/bin/python -m qlib.cli.data qlib_data --target_dir /home/runner/.qlib/qlib_data/cn_data --region cn
  -> exit 1 in 0.7s
  data check after qlib.cli.data: ok=False calendar=None..None (0 days), csi300=None, feature_dirs=0
$ /opt/hostedtoolcache/Python/3.11.18/x64/bin/python -m qlib.run.get_data qlib_data --target_dir /home/runner/.qlib/qlib_data/cn_data --region cn
  -> exit 0 in 7.8s
  data check after qlib.run.get_data: ok=True calendar=1999-11-10..2020-09-25 (4943 days), csi300=820, feature_dirs=3875
Data route used: official: python -m qlib.run.get_data qlib_data --region cn
Data dir: /home/runner/.qlib/qlib_data/cn_data
Calendar: 1999-11-10 .. 2020-09-25 (4943 trading days)
Instruments: csi300.txt=820, all.txt=3875, feature dirs=3875

## Stage 2: qrun LightGBM + Alpha158
qrun output is also tee'd to /home/runner/work/qlib-runner/qlib-runner/qlib_run/qrun_stdout.txt
qrun exit 0 in 74.0s

## Stage 3: recorder / mlflow extraction
mlruns dirs found: ['/home/runner/work/qlib-runner/qlib-runner/qlib_run/mlruns']
metrics found: 19; artifact files found: 17
```
