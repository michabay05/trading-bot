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
from alpaca.data.requests import StockBarsRequest, StockLatestTradeRequest
from alpaca.data.timeframe import TimeFrame

from . import log, util
from .stockframe import MultStockFrame
from .candles import Candle, Timespan


class TBDataFeed(ABC):
    @abstractmethod
    def set_candle_callback(self, callback: Callable[[str, Candle], Awaitable[None]]) -> None:
        pass

    @abstractmethod
    def get_latest_price(self, symbol: str) -> float:
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

class YahooDataFeed(TBDataFeed):
    def __init__(self, symbols: list[str]) -> None:
        self._symbols: list[str] = symbols
        self._prices: dict[str, list[float]] = {}
        for symbol in self._symbols:
            self._prices[symbol] = []

        self._cnd_dict: dict = {}
        self._candles: list[Candle] = []

        self._ws: yf.WebSocket = yf.WebSocket()

        self._t: datetime = datetime.now(tz=util.MY_TIMEZONE)
        self._first: bool = True

        self._candle_callback: Callable[[str, Candle], Awaitable[None]] | None = None

    def set_candle_callback(self, callback: Callable[[str, Candle], Awaitable[None]]) -> None:
        self._candle_callback = callback

    def get_latest_price(self, symbol: str) -> float:
        return self._prices[symbol][-1]

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

        self._prices[output["symbol"]].append(output["price"])
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


class AlpacaDataFeed(TBDataFeed):
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

    def get_latest_price(self, symbol: str) -> float:
        sltr = StockLatestTradeRequest(symbol_or_symbols=symbol)
        output = self._hist_data_stream.get_stock_latest_trade(sltr)
        return output[symbol].price

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
# x1 = adf.get_historical(["AAPL", "SPY"], Timespan.HOUR, datetime(2025, 7, 13, 9, 30))
# print("\n\n------------------------------------------------------------------------\n\n")
# ydf = YahooDataFeed(["AAPL", "SPY"])
# x2 = ydf.get_historical(["AAPL", "SPY"], Timespan.HOUR, datetime(2025, 7, 13, 9, 30))
# print(x2.get_symbol("AAPL"))
