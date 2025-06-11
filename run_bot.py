import json, os, time
from datetime import datetime, timedelta

import talib

from trbot import broker, candles
from trbot.bot import TradingBot
from trbot.candles import Candle, CandleOption, Timespan
from trbot.portfolio import Portfolio, Order, OrderType
from trbot.stockframe import Stockframe
from trbot.strategy import Strategy


# ===================== STRATEGY =====================
# class MyStrategy(Strategy):
#     def setup(self) -> None:
#         close = self.data.close
#         self.fast_ma = self.TA_EMA(close, period=8)
#         self.slow_ma = self.TA_EMA(close, period=21)

#     def on_candle(self) -> None:
#         price: float = self.data.close[-1]
#         if self.crossover(self.fast_ma, self.slow_ma):
#             # Go long
#             pass
#         elif self.crossover(self.slow_ma, self.fast_ma):
#             # Go short
#             pass

# sf: Stockframe = Stockframe.from_filepath("trout/ohlcv-GM-1hour.csv")
# mys = MyStrategy(sf)
# mys.setup()

# ===================== BROKER AND ORDER =====================
pft: Portfolio = Portfolio(initial_capital=10_000)
symb: str = "GM"
order: Order = Order(
    symbol=symb,
    order_type=OrderType.MARKET,
    quantity=2.0,
    purchase_price=36.10,
    purchase_dt="2025-02-12 10:21:43"
)
broker.execute_order(order, pft)

order = Order(
    symbol=symb,
    order_type=OrderType.MARKET,
    quantity=-1.0,
    purchase_price=35.95,
    purchase_dt="2025-02-12 12:32:18"
)
broker.execute_order(order, pft)

order = Order(
    symbol=symb,
    order_type=OrderType.MARKET,
    quantity=-3.0,
    purchase_price=35.62,
    purchase_dt="2025-02-12 14:26:03"
)
broker.execute_order(order, pft)

order = Order(
    symbol=symb,
    order_type=OrderType.MARKET,
    quantity=5.0,
    purchase_price=36.23,
    purchase_dt="2025-02-12 15:32:43"
)
broker.execute_order(order, pft)

print(pft)

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
