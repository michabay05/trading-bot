import json, os, time
from datetime import datetime, timedelta

import talib

from trbot import broker, candles
from trbot.bot import TradingBot
from trbot.candles import Candle, CandleOption, Timespan
from trbot.portfolio import Portfolio, Order, OrderType
from trbot.replayer import CandleReplayer
from trbot.stockframe import Stockframe
from trbot.strategy import Strategy


# ===================== STRATEGY =====================
class MyStrategy(Strategy):
    def setup(self) -> None:
        close = self._sf.close
        self.fast_ma = self.TA_EMA(close, period=8)
        self.slow_ma = self.TA_EMA(close, period=21)

    def on_candle(self) -> Order | None:
        if self.ind_crossover(self.fast_ma, self.slow_ma):
            return self.buy(1)

        if self.ind_crossover(self.slow_ma, self.fast_ma):
            return self.sell(1)

        return None

sf: Stockframe = Stockframe.from_csv("trout/aggs/MODIFIED_ohlcv-GM-4hour.csv")
mys = MyStrategy(sf)
mys.run()

# # ===================== CANDLE REPLAYER =====================
# sf: Stockframe = Stockframe.from_filepath("trout/ohlcv-GM-1hour.csv")
# replayer: CandleReplayer = CandleReplayer(sf)

# t: float = time.time()
# dt: float = 0.0
# while True:
#     current: float = time.time()
#     dt = current - t

#     replayer.update_time(dt)
#     print(replayer.current_time)

#     cnd: Candle | None = replayer.grab_next_candle()
#     if cnd is not None:
#         # Process info here
#         print(cnd)

#     time.sleep(1)
#     t = current


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
