from trbot import broker
from trbot.candles import Candle, CandleOption, Timespan
from trbot.stockframe import Stockframe
from trbot.strategy import StrategyTester
import visualize_candles as vs_cd


# ===================== STRATEGY =====================
class MyStrategy(StrategyTester):
    def setup(self) -> None:
        close = self._sf.close_series
        self.fast_ma = self.TA_EMA(close, period=8)
        self.slow_ma = self.TA_EMA(close, period=21)

    def on_candle(self) -> None:
        if self.ind_crossover(self.fast_ma, self.slow_ma):
            self.close_position()
            self.market_buy(size=1, take_profit=40.00)


# tickers: list[str] = vs_cd.valid_tickers("trout/aggs")[0]
tickers: list[str] = ["GM"]
sum: float = 0.0
for t in tickers:
    sf: Stockframe = Stockframe.from_csv(f"trout/aggs/ohlcv-{t}-4hour.csv")
    # mys = MyStrategy(sf, start_ind=115, end_ind=139)
    mys = MyStrategy(sf)
    try:
        # mys.run()
        output = mys.run()
        print(f"{t}: {output["pl"]}")
        sum += output["pl"]
    finally:
        mys.export_portfolio("trout/pfts")

print("----------------------")
print(f"Total: {sum}")

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
