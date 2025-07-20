from abc import ABC, abstractmethod
from datetime import datetime
from typing import Awaitable, Callable

import yfinance as yf
import pandas as pd
from alpaca.data import RawData
from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.data.live.stock import StockDataStream
from alpaca.data.models.bars import Bar
from alpaca.data.models import BarSet
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

from . import log, util
from .stockframe_v2 import MultStockFrame
from .candles import Candle, Timespan


class DataFeed(ABC):
    @abstractmethod
    def set_candle_callback(self, callback: Callable[[str, Candle], Awaitable[None]]) -> None:
        pass

    @abstractmethod
    def start_live(self) -> None:
        pass

    @abstractmethod
    def end_live(self) -> None:
        pass

    @abstractmethod
    def get_historical(self,
        symbols: list[str], timespan: Timespan, start: datetime, end: datetime = datetime.now(),
    ) -> MultStockFrame:
        pass


# Disable logging
# - https://stackoverflow.com/questions/8391411/how-to-block-calls-to-print

class YahooDataFeed(DataFeed):
    def __init__(self, symbols: list[str]) -> None:
        self._symbols: list[str] = symbols
        self._candles: list[Candle] = []
        self._cnd_dict: dict = {}

        self._ws: yf.WebSocket = yf.WebSocket()

        self._t: datetime = datetime.now(tz=util.MY_TIMEZONE)
        self._first: bool = True

        self._candle_callback: Callable[[str, Candle], Awaitable[None]] | None = None

    def set_candle_callback(self, callback: Callable[[str, Candle], Awaitable[None]]) -> None:
        self._candle_callback = callback

    def ws_callback(self, msg: dict):
        output: dict = {
            "symbol": msg["id"],
            "timestamp": datetime.fromtimestamp(int(msg["time"]) / 1000)
                .astimezone(tz=util.MY_TIMEZONE),
            "price": msg["price"]
        }
        if self._first or output["timestamp"].minute > self._t.minute:
            if not self._first:
                if self._candle_callback is not None:
                    cnd: Candle = Candle(**self._cnd_dict, volume=-1.0)
                    self._candles.append(cnd)
                    self._candle_callback(output["symbol"], cnd)
            else:
                self._first = False

            self._cnd_dict = {
                "timestamp": output["timestamp"],
                "open": output["price"],
                "high": output["price"],
                "low": output["price"],
                "close": output["price"],
            }
            self._t = datetime.now(tz=util.MY_TIMEZONE)
        else:
            self._cnd_dict["high"] = max(output["price"], self._cnd_dict["high"])
            self._cnd_dict["low"] = min(output["price"], self._cnd_dict["low"])
            self._cnd_dict["close"] = output["price"]

        log.debug(f"Received message: {output}")

    def start_live(self) -> None:
        self._ws.subscribe(self._symbols)
        self._ws.listen(self.ws_callback)

    def end_live(self) -> None:
        self._ws.close()

    def get_historical(self,
        symbols: list[str], timespan: Timespan, start: datetime, end: datetime = datetime.now()
    ) -> MultStockFrame:
        log.warn("YahooDataFeed.get_historical(): parameter `end` is not used")
        log.debug(f"{timespan.as_yf()}")
        df = yf.download(
            symbols, group_by="ticker", prepost=True, period="1mo", interval=timespan.as_yf(),
            start=start
        )
        if df is None:
            raise TypeError(f"df is of type {type(df)} instead of pd.DataFrame")

        return MultStockFrame.from_yf(symbols, timespan, df)


class AlpacaDataFeed(DataFeed):
    def __init__(self, symbols: list[str], acct_name: str) -> None:
        self._symbols: list[str] = symbols
        api_key, secret_key = util.alpaca_keys(acct_name)
        self._live_data_stream: StockDataStream = StockDataStream(api_key, secret_key)
        self._hist_data_stream = StockHistoricalDataClient(
            api_key, secret_key, raw_data=False
        )

        self._conn_alive: bool = False
        self._candle_callback: Callable[[str, Candle], Awaitable[None]] | None = None

    def set_candle_callback(self, callback: Callable[[str, Candle], Awaitable[None]]) -> None:
        self._candle_callback = callback

    async def ws_callback(self, bar: Bar | dict) -> None:
        if isinstance(bar, dict):
            # I have no idea what is inside this dict
            raise ValueError(f"data is of type {type(bar)}, expected type `Bar`")

        cnd: Candle = Candle(
            timestamp=bar.timestamp.astimezone(tz=util.MY_TIMEZONE),
            open=bar.open,
            high=bar.high,
            low=bar.low,
            close=bar.close,
            volume=bar.volume,
        )
        if self._candle_callback is not None:
            self._candle_callback(bar.symbol, cnd)

    def start_live(self) -> None:
        self._live_data_stream.subscribe_bars(
            self.ws_callback, *self._symbols
        )

        self._conn_alive = True
        self._live_data_stream.run()

    def end_live(self) -> None:
        self._live_data_stream.stop()
        self._conn_alive = False

    def get_historical(self,
        symbols: list[str], timespan: Timespan, start: datetime, end: datetime = datetime.now(),
    ) -> MultStockFrame:
        # NOTE: this could take a while, depending the time range supplied
        req = StockBarsRequest(
            symbol_or_symbols=symbols,
            timeframe=TimeFrame(amount=1, unit=timespan.as_alpaca()), # type: ignore
            start=start,
            end=end
        )

        bars: BarSet | RawData = self._hist_data_stream.get_stock_bars(req)
        if not isinstance(bars, BarSet):
            raise TypeError(f"Expected `bars` to be of type BarSet, got {type(bars)}")

        return MultStockFrame.from_alpaca(symbols, timespan, bars.df)


adf = AlpacaDataFeed(["AAPL", "SPY"], "YF Bot")
x1 = adf.get_historical(["AAPL", "SPY"], Timespan.HOUR, datetime(2025, 7, 13, 9, 30))
print(x1.get_symbol("AAPL"))
print("\n\n------------------------------------------------------------------------\n\n")
ydf = YahooDataFeed(["AAPL", "SPY"])
x2 = ydf.get_historical(["AAPL", "SPY"], Timespan.HOUR, datetime(2025, 7, 13, 9, 30))
print(x2.get_symbol("AAPL"))

# ydf = YahooDataFeed(["AAPL"])
# # ydf.get_historical_candles(["AAPL", "SPY"])
# try:
#     ydf.start_live()
# finally:
#     log.error("Ending...")
#     ydf.end_live()
#     log.info("Good bye")

## ================= SLICING BIG DATAFRAME ================= ##
# df = pd.read_csv("output.csv")
# zone = ZoneInfo("America/New_York")
#
# for ticker in tickers:
#     sliced_df = df[df["Ticker"] == ticker].copy()
#     sliced_df.drop("Ticker", axis=1, inplace=True)
#     # Date,Open,High,Low,Close,Volume
#     sliced_df.rename(columns={
#         "Date":   "timestamp",
#         "Open":   "open",
#         "High":   "high",
#         "Low":    "low",
#         "Close":  "close",
#         "Volume": "volume"
#     }, inplace=True) # type: ignore
#     sliced_df["timestamp"] = sliced_df["timestamp"].apply(
#         lambda x: datetime.fromisoformat(str(x)).astimezone(zone)
#     )
#     path: str = f"separated/{ticker}.csv"
#     sliced_df.to_csv(path, index=False)
#     print(path)

## ================= LIVE EXAMPLE ================= ##
# # define your message callback
# def message_handler(msg):
#     output = {
#         "id": msg["id"],
#         "price": msg["price"],
#         "time": str(
#             datetime.fromtimestamp(int(msg["time"]) / 1000)
#                 .astimezone(tz=ZoneInfo("America/New_York"))
#         )
#     }
#     print("Received message:", output)

# symbols = ["DELL"]
# async_ = True
# if async_:
#     async def main():
#         async with yf.AsyncWebSocket() as ws:
#             await ws.subscribe(symbols)
#             await ws.listen(message_handler)
#     asyncio.run(main())
# else:
#     with yf.WebSocket() as ws:
#         ws.subscribe(symbols)
#         ws.listen(message_handler)
