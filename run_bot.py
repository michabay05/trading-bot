import json, os, time
from datetime import datetime, timedelta

from trbot import candles
from trbot.bot import TradingBot
from trbot.candles import Candle, CandleOption, Timespan
from trbot.market import CandleReplayer, Market
from trbot.portfolio import Portfolio, Position
from trbot.stockframe import StockFrame


# with open("API_KEY.secret", "r") as f:
#     API_KEY: str = f.read().strip()


# ===================== CANDLE REPLAYER =====================
sf: StockFrame = StockFrame.from_filepath("trout/ohlcv-GM-1hour.csv")
replayer: CandleReplayer = CandleReplayer(sf)

t: float = time.time()
dt: float = 0.0
while True:
    current: float = time.time()
    dt = current - t

    replayer.update_time(dt)
    print(replayer.get_current_time())

    cnd: Candle | None = replayer.grab_next_candle()
    if cnd is not None:
        # Process info here
        print(cnd)

    time.sleep(1)
    t = current


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
