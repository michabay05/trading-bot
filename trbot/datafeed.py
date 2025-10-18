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

    def start_live(self) -> None:
        log.debug("Starting data stream...")

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

        self._conn_alive: bool = False

    def _ws_callback(self, data: dict) -> None:
        # Source: https://docs.alpaca.markets/docs/websocket-streaming#common-events

        # This method needs to be reworked before being used.
        log.warn("May not be a good idea to use this...")

        match data["event"]:
            case "fill":
                pass
            case _:
                log.warn(f"Unknown event type: {data["event"]}")

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
