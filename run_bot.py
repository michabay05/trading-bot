import time
from datetime import datetime

from trbot import candles
from trbot.bot import TradingBot
from trbot.stockframe import CandleReplayer, StockFrame


filepath: str = "candles/ohlcv-AAPL-5minute.csv"
sf: StockFrame = StockFrame.from_filepath(filepath)
replayer = CandleReplayer(sf)
print("New candle every 5 seconds...")

t: float = time.time()
dt: float = 0.0
while True:
    current = time.time()
    dt = current - t
    replayer.update_time(dt)
    cnd = replayer.grab_next_candle()
    if cnd is not None:
        print(cnd)

    time.sleep(1/60)
    t = current
