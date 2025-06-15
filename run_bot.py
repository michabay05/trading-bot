import json, os, time
from datetime import datetime, timedelta

import talib

from trbot import broker, candles
from trbot.bot import TradingBot
from trbot.candles import Candle, CandleOption, Timespan
from trbot.portfolio import Portfolio, Order, OrderType
from trbot.replayer import CandleReplayer
from trbot.stockframe import Stockframe
from trbot.strategy import StrategyTester


# ===================== STRATEGY =====================
class MyStrategy(StrategyTester):
    def setup(self) -> None:
        close = self._sf.close
        self.fast_ma = self.TA_EMA(close, period=8)
        self.slow_ma = self.TA_EMA(close, period=21)

    def on_candle(self) -> None:
        if self.ind_crossover(self.fast_ma, self.slow_ma):
            self.close_position()
            self.buy(1)

        if self.ind_crossover(self.slow_ma, self.fast_ma):
            self.close_position()
            self.sell(1)

tickers = []
dir: str = "trout/aggs"
for filename in os.listdir(dir):
    fpath: str = os.path.join(dir, filename)
    info: dict = candles.candle_info_from_path(fpath)
    tickers.append(info["ticker"])

sum: float = 0.0
for t in tickers:
    sf: Stockframe = Stockframe.from_csv(f"trout/aggs/ohlcv-{t}-4hour.csv")
    mys = MyStrategy(sf)
    # mys.run()
    sum += mys.run()
    mys.export_portfolio("trout/pfts")

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
