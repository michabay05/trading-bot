import time
from datetime import datetime

from trbot import candles
from trbot.bot import TradingBot
from trbot.candles import Candle, CandleOption, Timespan
from trbot.stockframe import CandleReplayer, StockFrame


# ===================== SMA Testing =====================
# filepath: str = "candles/ohlcv-AAPL-5minute.csv"
# sf: StockFrame = StockFrame.from_filepath(filepath)

# window: int = 8
# sf.df[f"SMA_{window}"] = sf.df["close"].rolling(window=window).mean()
# sf.df[f"EMA_{window}"] = sf.df["close"].ewm(span=window).mean()
# print(sf.df)

# ===================== HISTORICAL CANDLES =====================
with open("API_KEY.secret", "r") as f:
    API_KEY: str = f.read().strip()

my_bot = TradingBot(api_key=API_KEY)

# for ticker in ["WMT", "INTC", "HPQ", "NKE", "GM"]:
for ticker in ["WMT"]:
    opt = CandleOption(
        ticker=ticker,
        start="2024-01-01 10:00:00",
        end="2025-05-23 15:00:00",
        mult=4,
        timespan=Timespan.HOUR
    )
    cnds: list[Candle] = my_bot.get_historical_candles(opt)
    sf = StockFrame(cnds, opt.ticker, opt.mult, opt.timespan)
    sf.to_csv("candles")

# ===================== REPLAYER =====================
# replayer = CandleReplayer(sf)
# print("New candle every 5 seconds...")

# t: float = time.time()
# dt: float = 0.0
# while True:
#     current = time.time()
#     dt = current - t
#     replayer.update_time(dt)
#     cnd = replayer.grab_next_candle()
#     if cnd is not None:
#         print(cnd)

#     time.sleep(1/60)
#     t = current
