# Kaggle EGX30 index history (G4)

- Source: Kaggle dataset `theahmedrmdan/egx30-historical-ohlcv`, Apache 2.0
  (https://www.kaggle.com/datasets/theahmedrmdan/egx30-historical-ohlcv)
- Pulled 2026-11-26 ~22:57 Cairo via the unauthenticated download endpoint
  `https://www.kaggle.com/api/v1/datasets/download/theahmedrmdan/egx30-historical-ohlcv`
  (302 to a signed Google Cloud Storage URL; bundle id 9942668/15540953).
- File is verbatim from the ZIP (EGX30.csv). md5: zip 8ff9e54898525eb4a118705145d98d3a,
  csv b4d728ea0ddae9a5bc5ffd43a960d3bf.
- Verified contents: 6,828 lines incl. header `date,open,high,low,close,volume`
  (6,827 data rows). First row 1998-01-01 (O/H/L/C 1000.0, index base). Last row
  2026-04-02 O 46731.49 H 46734.07 L 46079.18 C 46399.0 V 544,812,765.
- Date format is `YYYY-MM-DD/00:00:00`. No out-of-order rows.
- Caveat: 144 dates appear twice (adjacent duplicate rows, e.g. 2020-09-17,
  2020-09-23, 2020-10-01); consumers should dedupe on date.
- Gap 2026-04-03 to present: covered by the daily snapshot cron (future design),
  not this file.
