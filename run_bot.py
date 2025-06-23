import time
from trbot.stockframe import Stockframe
from trbot.strategy import StrategyTester
import visualize_candles as vs_cd


# ===================== STRATEGY =====================
class MyStrategy(StrategyTester):
    def setup(self) -> None:
        close = self._sf.close_series
        high = self._sf.high_series
        low = self._sf.low_series
        self.fast_ma = self.TA_EMA(close, period=50)
        self.slow_ma = self.TA_EMA(close, period=100)
        self.atr = self.TA_ATR(high, low, close, period=14)

    def on_candle(self) -> None:
        last_atr = self.last_ind_value(self.atr)
        sz = 0.25
        if self.ind_crossover(self.fast_ma, self.slow_ma):
            self.market_buy(
                size=sz,
                tp_limit=self.last_close + 10*last_atr,
                sl_limit=self.last_close - 5*last_atr
            )
        if self.ind_crossover(self.slow_ma, self.fast_ma):
            self.market_sell(
                size=sz,
                tp_limit=self.last_close - 10*last_atr,
                sl_limit=self.last_close + 5*last_atr
            )


start_time: float = time.time()
tickers: list[str] = vs_cd.valid_tickers("trout/aggs")[0]
# tickers: list[str] = ["GM"]
sum: float = 0.0
for t in tickers:
    sf: Stockframe = Stockframe.from_csv(f"trout/aggs/ohlcv-{t}-4hour.csv")
    mys = MyStrategy(sf)
    try:
        output = mys.run()
        print(f"{t}: {output["pl"]}")
        sum += output["pl"]
    finally:
        mys.export_portfolio("trout/pfts")

print("----------------------")
print(f"Total: {sum}")
diff: float = time.time() - start_time
print(f"Took {diff:.3f}s to backtest {len(tickers)} symbols")

# ===================== HISTORICAL CANDLES =====================
# for ticker in [
#     "WMT", "INTC", "HPQ", "NKE", "GM", "TGT", "BBY", "SMCI", "SKX", "UAA", "PUMSY", "F", "HMC",
#     "KR", "M", "LNVGY", "KHC", "GIS", "BYND", "GAP"
# ]:
#     opt: CandleOption = CandleOption(
#         ticker=ticker,
#         start="2023-06-15 10:00:00",
#         end="2025-06-13 16:00:00",
#         mult=4,
#         timespan=Timespan.HOUR
#     )
#     cnds: list[Candle] = broker.get_historical_candles(opt)
#     sf: Stockframe = Stockframe(cnds, opt.ticker, opt.mult, opt.timespan)
#     sf.to_csv("trout/aggs")

#     print(f"Completed downloading for {ticker}")
#     print("-----------------------")
