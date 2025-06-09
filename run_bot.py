import json, os, time
from datetime import datetime, timedelta

import talib

from trbot import candles
from trbot.bot import TradingBot
from trbot.candles import Candle, CandleOption, Timespan
from trbot.market import CandleReplayer, Market
from trbot.portfolio import Portfolio, Position
from trbot.stockframe import Stockframe, Strategy


# with open("API_KEY.secret", "r") as f:
#     API_KEY: str = f.read().strip()

class MyStrategy(Strategy):
    def setup(self) -> None:
        self._close = self.data.close
        self.fast_ma = self.TA_SMA(self._close, period=8)
        self.slow_ma = self.TA_SMA(self._close, period=21)

    def on_candle(self) -> None:
        price: float = self._close[-1]
        if self.crossover(self.fast_ma, self.slow_ma):
            # Go long
            pass
        elif self.crossover(self.slow_ma, self.fast_ma):
            # Go short
            pass

sf: Stockframe = Stockframe.from_filepath("trout/ohlcv-GM-1hour.csv")
mys = MyStrategy(sf)
mys.setup()


# ===================== CANDLE REPLAYER =====================
# sf: StockFrame = StockFrame.from_filepath("trout/ohlcv-GM-1hour.csv")
# replayer: CandleReplayer = CandleReplayer(sf)

# t: float = time.time()
# dt: float = 0.0
# while True:
#     current: float = time.time()
#     dt = current - t

#     replayer.update_time(dt)
#     print(replayer.get_current_time())

#     cnd: Candle | None = replayer.grab_next_candle()
#     if cnd is not None:
#         # Process info here
#         print(cnd)

#     time.sleep(1)
#     t = current


# ===================== HISTORICAL CANDLES =====================
# with open("API_KEY.secret", "r") as f:
#     API_KEY: str = f.read().strip()

# my_bot = TradingBot(api_key=API_KEY)

# for ticker in ["WMT", "INTC", "HPQ", "NKE", "GM"]:
#     opt = CandleOption(
#         ticker=ticker,
#         start="2024-01-01 10:00:00",
#         end="2025-05-23 15:00:00",
#         mult=4,
#         timespan=Timespan.HOUR
#     )
#     cnds: list[Candle] = my_bot.get_historical_candles(opt)
#     sf = StockFrame(cnds, opt.ticker, opt.mult, opt.timespan)
#     sf.to_csv("candles")
