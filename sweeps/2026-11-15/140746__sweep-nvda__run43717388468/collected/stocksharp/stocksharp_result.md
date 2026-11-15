# StockSharp pilot result

- Route taken: alternative route — minimal console project on the free StockSharp NuGet packages (see README.md for why the samples-repo route is not used directly).
- Project: `src/StockSharpPilot` (Program.cs + SmaStrategy.cs, the SMA strategy from StockSharp's own history-testing sample).
- Engine: `HistoryEmulationConnector` (StockSharp.Algo.Testing) over the free `StockSharp.Samples.HistoryData` package, located at runtime via `StockSharp.Configuration.Paths` (the same mechanism the project's samples use).
- Packages pinned: StockSharp.Algo 5.0.220, StockSharp.BusinessEntities 5.0.208, StockSharp.Messages 5.0.214, StockSharp.Configuration 5.0.210, StockSharp.Samples.HistoryData 5.0.0 — the last wave targeting net6.0 (2025-07-04), restorable by the mandated .NET 8 SDK. Current StockSharp packages (5.0.230+) target net10.0 only.

## Build result: succeeded

## Run result: backtest completed (exit code 0)

History data path: /home/runner/.nuget/packages/stocksharp.samples.historydata/5.0.0/HistoryData
Security: SBER@TQBR
Period: 04/01/2020 - 04/30/2020

Headline figures (verbatim from the program output):

```
=== Backtest completed ===

Total trades: 246
Net profit: -1.27
Max drawdown: 23.42

Final portfolio value: 1000

Statistics:
  MaxProfit: 17.87
  MaxProfitDate: 04/15/2020 16:22:00 +03:00
  MaxDrawdown: 23.42
  MaxDrawdownDate: 04/22/2020 10:16:00 +03:00
  MaxRelativeDrawdown: 1.78125
  MaxDrawdownPercent: 131.05763850027979854504756575
  Return: 11.211428571428571428571428571
  NetProfit: -1.27
  NetProfitPercent: -0.127
  RecoveryFactor: -0.0542271562766865926558497011
  Commission: 735.63
  SharpeRatio: -0.0556326783513879762541860175
  SortinoRatio: -0.0545825119397712236482177874
  CalmarRatio: -0.0542271562766865926558497011
  SterlingRatio: -0.3349450549450549450549450549
  AverageDrawdown: 3.7916666666666666666666666667
  WinningTrades: 69
  AverageWinTrade: 1.1456521739130434782608695652
  LossingTrades: 166
  AverageLossTrade: -0.4838554216867469879518072289
  PerMonthTrade: 246
  PerDayTrade: 11.714285714285714285714285719
  RoundtripCount: 235
  AverageTradeProfit: -0.005404255319148936170212766
  TradeCount: 246
  ProfitFactor: 0.984188247011952191235059761
  Expectancy: -0.0054273504273504273504273504
  MaxLongPosition: 1
  MaxShortPosition: -3
  MaxLatencyRegistration: 00:00:00
  MinLatencyRegistration: 00:00:00
  MaxLatencyCancellation: 00:00:00
  MinLatencyCancellation: 00:00:00
  OrderCount: 233
  OrderErrorCount: 0
  OrderInsufficientFundErrorCount: 0
```
