from abc import ABC, abstractmethod
from datetime import datetime
from typing import Callable

import yfinance as yf
from alpaca.data import RawData
from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.data.live.stock import StockDataStream
from alpaca.data.models.bars import Bar
from alpaca.data.models import BarSet
from alpaca.data.requests import StockBarsRequest, StockLatestTradeRequest
from alpaca.trading.stream import TradingStream
from alpaca.data.timeframe import TimeFrame

from . import log, util
from .candles import Candle, Timespan
from .stockframe import MultStockFrame


class TBDataFeed(ABC):
    @abstractmethod
    def set_candle_callback(self, callback: Callable[[str, Candle], None]) -> None:
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
        symbols: list[str], timespan: Timespan, start: datetime,  mult: int = 1, end: datetime = datetime.now(),
    ) -> MultStockFrame:
        pass


class AlpacaDataFeed(TBDataFeed):
    def __init__(self, symbols: list[str], acct_name: str) -> None:
        self._symbols: list[str] = symbols
        api_key, secret_key = util.alpaca_keys(acct_name)
        self._live_stream: StockDataStream = StockDataStream(
            api_key, secret_key, raw_data=False
        )
        self._hist_data_stream: StockHistoricalDataClient = StockHistoricalDataClient(
            api_key, secret_key, raw_data=False
        )

        self._conn_alive: bool = False
        self._candle_callback: Callable[[str, Candle], None] | None = None

    def set_candle_callback(self, callback: Callable[[str, Candle], None]) -> None:
        self._candle_callback = callback

    def get_latest_price(self, symbol: str) -> float:
        sltr = StockLatestTradeRequest(symbol_or_symbols=symbol)
        output = self._hist_data_stream.get_stock_latest_trade(sltr)
        return output[symbol].price

    async def ws_callback(self, bar: Bar | dict) -> None:
        if isinstance(bar, dict):
            # I have no idea what is inside this dict
            raise ValueError(f"data is of type {type(bar)}, expected type `Bar`")

        if self._candle_callback is not None:
            self._candle_callback(bar.symbol, Candle(
                timestamp=bar.timestamp.astimezone(tz=util.MY_TIMEZONE),
                open=bar.open,
                high=bar.high,
                low=bar.low,
                close=bar.close,
                volume=bar.volume,
            ))

    def start_live(self) -> None:
        self._live_stream.subscribe_bars(
            self.ws_callback, *self._symbols
        )

        self._conn_alive = True
        self._live_stream.run()

    def end_live(self) -> None:
        self._live_stream.stop()
        self._conn_alive = False

    def get_historical(self,
        symbols: list[str], timespan: Timespan, start: datetime,
        mult: int = 1, end: datetime = datetime.now(),
    ) -> MultStockFrame:
        # NOTE: this could take a while, depending the time range supplied
        req = StockBarsRequest(
            symbol_or_symbols=symbols,
            timeframe=TimeFrame(amount=mult, unit=timespan.as_alpaca()), # type: ignore
            start=start,
            end=end
        )

        bars: BarSet | RawData = self._hist_data_stream.get_stock_bars(req)
        if not isinstance(bars, BarSet):
            raise TypeError(f"Expected `bars` to be of type BarSet, got {type(bars)}")

        return MultStockFrame.from_alpaca(timespan, bars.df)


class AlpacaUpdateFeed:
    def __init__(self, acct_name: str, paper: bool = True) -> None:
        log.warn("Temporarily deprecated......")
        api_key, secret_key = util.alpaca_keys(acct_name)
        self._update_stream: TradingStream = TradingStream(
            api_key, secret_key, paper=paper, raw_data=False
        )

        self._update_callback: Callable[[dict], None] | None = None
        self._conn_alive: bool = False

    def set_update_callback(self, callback: Callable[[dict], None]) -> None:
        self._update_callback = callback

    async def _ws_callback(self, data: Callable) -> None:
        if self._update_callback is not None:
            self._update_callback(data) # type: ignore

    def start_live(self) -> None:
        self._update_stream.subscribe_trade_updates(self._ws_callback)

        self._conn_alive = True
        self._update_stream.run()

    def end_live(self) -> None:
        self._update_stream.stop()
        self._conn_alive = False


# Disable logging
# - https://stackoverflow.com/questions/8391411/how-to-block-calls-to-print
class YahooDataFeed(TBDataFeed):
    def __init__(self, symbols: list[str]) -> None:
        self._symbols: list[str] = symbols

        self._cnd_dict: dict[str, dict] = {}
        self._first: dict[str, bool] = {}
        self._prices: dict[str, list[float]] = {}
        for symbol in self._symbols:
            self._prices[symbol] = []
            self._first[symbol] = True

        self._candles: list[Candle] = []

        self._ws: yf.WebSocket = yf.WebSocket()

        self._t: datetime = datetime.now(tz=util.MY_TIMEZONE)

        self._candle_callback: Callable[[str, Candle], None] | None = None

    def set_candle_callback(self, callback: Callable[[str, Candle], None]) -> None:
        self._candle_callback = callback

    def get_latest_price(self, symbol: str) -> float:
        return self._prices[symbol][-1]

    def ws_callback(self, msg: dict):
        timestamp = datetime.fromtimestamp(int(msg["time"]) / 1000).astimezone(tz=util.MY_TIMEZONE)
        symbol = msg["id"]
        price = msg["price"]
        if self._first[symbol] or timestamp.minute > self._t.minute:
            if not self._first[symbol]:
                if self._candle_callback is not None:
                    cnd: Candle = Candle(**self._cnd_dict[symbol], volume=-1.0)
                    self._candles.append(cnd)
                    self._candle_callback(symbol, cnd)
            else:
                self._first[symbol] = False

            self._cnd_dict[symbol] = {
                "timestamp": timestamp,
                "open": price,
                "high": price,
                "low": price,
                "close": price,
            }
            self._t = datetime.now(tz=util.MY_TIMEZONE)
        else:
            self._cnd_dict[symbol]["high"] = max(price, self._cnd_dict[symbol]["high"])
            self._cnd_dict[symbol]["low"] = min(price, self._cnd_dict[symbol]["low"])
            self._cnd_dict[symbol]["close"] = price

        self._prices[symbol].append(price)

        log.debug(f"{symbol:4}: {{ {str(timestamp)}, {price:6} }}")

    def start_live(self) -> None:
        self._ws.subscribe(self._symbols)
        self._ws.listen(self.ws_callback)

    def end_live(self) -> None:
        self._ws.close()

    def get_historical(self,
        symbols: list[str], timespan: Timespan, start: datetime,
        mult: int = 1, end: datetime = datetime.now()
    ) -> MultStockFrame:
        log.debug(f"{timespan.as_yf()}")
        df = yf.download(
            symbols, group_by="ticker", prepost=True,
            interval=timespan.as_yf(mult=mult),
            start=start, end=end, auto_adjust=True
        )
        if df is None:
            raise TypeError(f"df is of type {type(df)} instead of pd.DataFrame")

        return MultStockFrame.from_yf(timespan, df)


