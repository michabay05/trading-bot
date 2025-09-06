from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Callable

from alpaca.data import RawData
from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.data.live.stock import StockDataStream
from alpaca.data.models.bars import Bar
from alpaca.data.models import BarSet
from alpaca.data.requests import StockBarsRequest, StockLatestTradeRequest
from alpaca.trading.stream import TradingStream
from alpaca.data.timeframe import TimeFrame
import numpy as np

from . import log, util
from .candles import Candle, Timespan
from .stockframe import MultStockFrame


class TBDataFeed(ABC):
    @abstractmethod
    def get_latest_price(self, symbol: str) -> float:
        pass

    @abstractmethod
    async def start_live(self) -> None:
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
    def __init__(self, symbols: list[str], acct_name: str, callback: Callable[[str, Candle], None]) -> None:
        self._symbols: list[str] = symbols
        api_key, secret_key = util.alpaca_keys(acct_name)
        self._live_stream: StockDataStream = StockDataStream(
            api_key, secret_key, raw_data=False
        )
        self._hist_data_stream: StockHistoricalDataClient = StockHistoricalDataClient(
            api_key, secret_key, raw_data=False
        )

        self._conn_alive: bool = False
        self._candle_callback: Callable[[str, Candle], None] = callback

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

    async def start_live(self) -> None:
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
    def __init__(self, acct_name: str, callback: Callable[[dict], None], paper: bool = True) -> None:
        api_key, secret_key = util.alpaca_keys(acct_name)
        self._update_stream: TradingStream = TradingStream(
            api_key, secret_key, paper=paper, raw_data=False
        )

        self._update_callback: Callable[[dict], None] = callback
        self._conn_alive: bool = False

    async def _ws_callback(self, data: dict) -> None:
        if self._update_callback is not None:
            self._update_callback(data)

    async def start_live(self) -> None:
        self._update_stream.subscribe_trade_updates(self._ws_callback)

        self._conn_alive = True
        self._update_stream.run()

    def end_live(self) -> None:
        self._update_stream.stop()
        self._conn_alive = False


class RandomDataFeed(TBDataFeed):
    def __init__(self, callback: Callable[[Candle], None], long_tendency: float = 0.5,
        initial_price: float = 100, atr: float = 0.5, seed: int | None = None
    ):
        self._long_tendency: float = long_tendency
        self._initial_price: float = initial_price
        self._atr: float = atr
        self._atr_deviation: float = 0.2 * self._atr
        self._seed: int | None = seed
        self._rng = np.random.RandomState(self._seed)

        self._candles: list[Candle] = []
        # This is just an arbitrary date. The more important thing is that there is
        # a date here. The actual date does not matter.
        self._start_date: datetime = datetime(2025, 9, 1, 9, 30)
        self._time_step: timedelta = Timespan.MINUTE.as_timedelta(mult=1)
        
        self._update_callback: Callable[[Candle], None] = callback

    def _gen_new_candle(self) -> Candle:
        cnd_count = len(self._candles)
        atr = self._rng.uniform(self._atr - self._atr_deviation, self._atr + self._atr_deviation)
        open_ = self._initial_price if cnd_count == 0 else self._candles[-1].close
        high = max(open_, self._rng.uniform(open_, open_ + atr))
        low = min(self._rng.uniform(open_ - atr, open_), open_)

        if self._rng.random() < self._long_tendency:
            # Create a long candle
            close = self._rng.uniform(open_, high)
        else:
            # Create a short candle
            close = self._rng.uniform(low, open_)
        
        # As of right now, the volume does not really matter so i'll just set to something random
        volume = self._rng.randint(1000, 12345)

        return Candle(
            timestamp=self._start_date + cnd_count * self._time_step,
            open=open_,
            high=high,
            low=low,
            close=close,
            volume=volume
        )

    def get_latest_price(self, symbol: str) -> float:
        # log.warn(f"RDF: symbol({symbol}) is not used in get_latest_price()")

        cnd = self._gen_new_candle()
        self._candles.append(cnd)
        return cnd.close

    async def start_live(self) -> None:
        log.error("Random data feed can not start live data feed; it does not have that feature.")
        raise NotImplementedError()

    def end_live(self) -> None:
        log.error("Random data feed can not end live data feed; it does not have that feature.")
        raise NotImplementedError()

    def get_historical(self,
        symbols: list[str], timespan: Timespan, start: datetime,  mult: int = 1, end: datetime = datetime.now(),
    ) -> MultStockFrame:
        log.warn("RandomDataFeed does not have a time-based history; it does not have that feature yet")
        raise NotImplementedError()

# =======================
import plotly.graph_objects as go

cnd_data = {
    "timestamp": [],
    "open": [],
    "high": [],
    "low": [],
    "close": [],
}
def cb_func(cnd: Candle):
    log.error("This should not be called unless live feature is used...")

rdf = RandomDataFeed(cb_func, seed=None, long_tendency=.2)

for i in range(250):
    _ = rdf.get_latest_price("AAPL")

for cnd in rdf._candles:
    cnd_data["timestamp"].append(cnd.timestamp)
    cnd_data["open"].append(cnd.open)
    cnd_data["high"].append(cnd.high)
    cnd_data["low"].append(cnd.low)
    cnd_data["close"].append(cnd.close)

assert len(cnd_data["timestamp"]) > 10

fig = go.Figure(data=[go.Candlestick(x=cnd_data["timestamp"],
                open=cnd_data["open"],
                high=cnd_data["high"],
                low=cnd_data["low"],
                close=cnd_data["close"])])

fig.write_html("plotly.html")

# # Disable logging
# # - https://stackoverflow.com/questions/8391411/how-to-block-calls-to-print
# class YahooDataFeed(TBDataFeed):
#     def __init__(self, symbols: list[str]) -> None:
#         log.warn("Temporarily deprecated......")
#         self._symbols: list[str] = symbols

#         self._cnd_dict: dict[str, dict] = {}
#         self._first: dict[str, bool] = {}
#         self._prices: dict[str, list[float]] = {}
#         for symbol in self._symbols:
#             self._prices[symbol] = []
#             self._first[symbol] = True

#         self._candles: list[Candle] = []

#         self._ws: yf.WebSocket = yf.WebSocket()

#         self._t: datetime = datetime.now(tz=util.MY_TIMEZONE)

#         self._candle_callback: Callable[[str, Candle], None] | None = None

#     def set_candle_callback(self, callback: Callable[[str, Candle], None]) -> None:
#         self._candle_callback = callback

#     def get_latest_price(self, symbol: str) -> float:
#         return self._prices[symbol][-1]

#     def ws_callback(self, msg: dict):
#         timestamp = datetime.fromtimestamp(int(msg["time"]) / 1000).astimezone(tz=util.MY_TIMEZONE)
#         symbol = msg["id"]
#         price = msg["price"]
#         if self._first[symbol] or timestamp.minute > self._t.minute:
#             if not self._first[symbol]:
#                 if self._candle_callback is not None:
#                     cnd: Candle = Candle(**self._cnd_dict[symbol], volume=-1.0)
#                     self._candles.append(cnd)
#                     self._candle_callback(symbol, cnd)
#             else:
#                 self._first[symbol] = False

#             self._cnd_dict[symbol] = {
#                 "timestamp": timestamp,
#                 "open": price,
#                 "high": price,
#                 "low": price,
#                 "close": price,
#             }
#             self._t = datetime.now(tz=util.MY_TIMEZONE)
#         else:
#             self._cnd_dict[symbol]["high"] = max(price, self._cnd_dict[symbol]["high"])
#             self._cnd_dict[symbol]["low"] = min(price, self._cnd_dict[symbol]["low"])
#             self._cnd_dict[symbol]["close"] = price

#         self._prices[symbol].append(price)

#         log.debug(f"{symbol:4}: {{ {str(timestamp)}, {price:6} }}")

#     def start_live(self) -> None:
#         self._ws.subscribe(self._symbols)
#         self._ws.listen(self.ws_callback)

#     def end_live(self) -> None:
#         self._ws.close()

#     def get_historical(self,
#         symbols: list[str], timespan: Timespan, start: datetime,
#         mult: int = 1, end: datetime = datetime.now()
#     ) -> MultStockFrame:
#         log.debug(f"{timespan.as_yf()}")
#         df = yf.download(
#             symbols, group_by="ticker", prepost=True,
#             interval=timespan.as_yf(mult=mult),
#             start=start, end=end, auto_adjust=True
#         )
#         if df is None:
#             raise TypeError(f"df is of type {type(df)} instead of pd.DataFrame")

#         return MultStockFrame.from_yf(timespan, df)


