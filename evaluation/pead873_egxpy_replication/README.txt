OHLC paths for variance-ratio tests. Source: borsagator archive branch, read 2026-11-27.
yahoo/<T>_CA.csv: date,high,low,close,volume,adjclose. NO open (Yahoo open = prior close on ~98% of bars). Close NOT adjusted for bonus shares (egxpy is). 
egxpy/<t>.csv: Date,Open,High,Low,Close,Volume from the latest egx-data run per ticker (3000 daily bars, to about 2026-11-18/25). Bonus-adjusted; Open also equals prior close on ex-days.
Known: the two feeds disagree on day-to-day returns by >1% on 13-16% of bars in 2016, 2022, 2023 (see round C). Name the source in any result; do not splice.
Use log returns on close within one source only. POUL, CIRA, GOUR, OLFI: egxpy only. ABUK, ESRS: neither.
