from dataclasses import dataclass, field
from abc import abstractmethod
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from typing import Callable, Any, Literal
from zoneinfo import ZoneInfo
import time

import numpy as np
from numpy.typing import NDArray
import talib
import matplotlib.pyplot as plt
from alpaca.data.models.bars import Bar

from trbot.candles import Candle, Timespan
from .broker import HistoricalBroker, LiveBroker
from .replayer import CandleReplayer
from .portfolio import OrderIntent, OrderDir, Portfolio, MarketOrder, StopLossTrigger, TakeProfitTrigger
from .stockframe import Stockframe


IndValues = NDArray[np.float64]

IndicatorKind = Literal["sma", "ema", "rsi", "atr"]
CandlePart = Literal["close", "low", "high"]

ALL_SYMBOLS = [
    "AAPL", "ABNB", "BBY", "DASH", "DELL", "EBAY", "F", "GE", "GOOG", "HIMS",
    "HPQ", "INTC", "LOGI", "NIO", "NVDA", "NVDY", "PANW", "PEP", "PLTR", "QCOM",
    "ROST", "SHOP", "SMCI", "SPY", "TGT", "WMT", "XLF"
]


class Indicator:
    def __init__(self,
        kind: IndicatorKind,
        part: list[CandlePart], params: dict[str, Any] = {}
    ) -> None:
        self._kind: str = kind
        self._func: Callable = Indicator._ta_func_from_kind(self._kind)
        self._parts: list[CandlePart] = part
        if "timeperiod" not in params.keys():
            raise KeyError(f"Missing key 'timeperiod' for talib func parameters.\nparams = {params}")
        self._params: dict[str, Any] = params

    @property
    def period(self) -> int:
        return self._params["timeperiod"]

    def compute_values(self, cnds: list[Candle]) -> IndValues:
        assert len(cnds) >= self.period
        data: dict[str, IndValues] = {}
        sliced_cnds: list[Candle] = cnds[-self.period:]
        for part in self._parts:
            vals: list[float] = []
            match part:
                case "close":
                    vals = [cnd.close for cnd in sliced_cnds]
                case "low":
                    vals = [cnd.low for cnd in sliced_cnds]
                case "high":
                    vals = [cnd.high for cnd in sliced_cnds]
                case _:
                    raise ValueError(f"Unknown part of a candle: {self._parts}")

            data[part] = np.array(vals, dtype=np.float64)

        values: IndValues = self._func(**data, **self._params)
        return values

    def name(self) -> str:
        return f"{self._kind}_{self.period}"

    @staticmethod
    def _ta_func_from_kind(kind: str) -> Callable:
        match kind:
            case "sma":
                return talib.SMA
            case "ema":
                return talib.EMA
            case "rsi":
                return talib.RSI
            case "atr":
                return talib.ATR
            case _:
                raise ValueError(f"Unknown kind of indicator: {kind}")


@dataclass
class _LiveData:
    live_cnds: list[Candle] = field(default_factory=list)
    live_timespan: Timespan = Timespan.MINUTE
    agg_cnds: list[Candle] = field(default_factory=list)
    agg_timespan: Timespan = Timespan.HOUR
    agg_inds: dict[str, IndValues] = field(default_factory=dict)

    def add_live(self, cnd: Candle) -> None:
        self.live_cnds.append(cnd)

    def add_agg(self, cnd: Candle) -> None:
        self.agg_cnds.append(cnd)

    def update_indicator(self, name: str, values: IndValues) -> None:
        self.agg_inds[name] = values


class LiveStrategy:
    def __init__(self) -> None:
        self._broker: LiveBroker = LiveBroker()
        self.symbols: list[str] = ["SPY", "AAPL", "GE", "HPQ"]
        self._live_data: dict[str, _LiveData] = {}
        for sym in self.symbols:
            self._live_data[sym] = _LiveData()
        self._conn_alive: bool = False

        self._indicators: set[Indicator] = set()
        self._max_period: int = 0

        self._time: datetime = datetime.now()
        self._current_hour: int = self._time.hour

    @property
    def broker(self) -> LiveBroker:
        return self._broker

    @property
    def portfolio(self) -> Portfolio:
        return self.broker.portfolio

    def last_close(self, symbol: str) -> float:
        return self._live_data[symbol].live_cnds[-1].close

    @property
    def curr_dt_str(self) -> str:
        return self._time.strftime("%Y-%m-%d %H:%M:%S")

    def last_ind_value(self, symbol: str, ind_name: str) -> float:
        return self._live_data[symbol].agg_inds[ind_name][-1]

    def _init_all_live_data(self) -> None:
        assert self._max_period > 0

        print(f"Max period: {self._max_period}")
        for symbol in self.symbols:
            ld = self._live_data[symbol]
            path = f"ohlcv-1hr/{symbol}.csv"
            sf = Stockframe.from_csv(path, symbol, mult=1, timespan=Timespan.HOUR)
            n: int = len(sf) - self._max_period
            for i in range(n, len(sf)):
                cnd: Candle = sf.row_to_candle(i)
                ld.add_agg(cnd)

    def _on_market_open(self) -> None:
        self.setup()
        self._init_all_live_data()

        if not self._conn_alive:
            self._conn_alive = True
            self.broker._data_stream.run()

    def _on_market_close(self) -> None:
        if self._conn_alive:
            self.broker._data_stream.stop()
            self._conn_alive = False

        # Bring historical data up to date
        start = datetime.now() - relativedelta(months=1)
        self.broker.export_historical_candles(ALL_SYMBOLS, start)

        zone: ZoneInfo = ZoneInfo("America/New_York")
        status: dict = self.broker.get_market_status()
        next_open: datetime = status["next_open"]
        diff = (next_open - datetime.now(tz=zone)) + timedelta(seconds=5)
        print(f"Next market open: {next_open}")
        print(f"Sleeping for {str(diff)}...")
        time.sleep(diff.total_seconds())

        self.start()

    def start(self) -> None:
        self.broker._data_stream.subscribe_bars(
            self._stock_data_stream_handler, *self.symbols
        )

        status: dict = self.broker.get_market_status()
        if status["is_open"]:
            # Market is currently open
            self._on_market_open()
        else:
            # Market is currently closed
            self._on_market_close()

    async def _stock_data_stream_handler(self, bar: Bar | dict) -> None:
        if isinstance(bar, dict):
            # I have no idea what is inside this dict
            raise ValueError(f"data is of type {type(bar)}, expected type `Bar`")

        if not self.broker.get_market_status()["is_open"]:
            # Market is closed
            self._on_market_close()

        def _bar_to_candle(bar: Bar) -> Candle:
            return Candle(
                timestamp=bar.timestamp,
                open=bar.open,
                high=bar.high,
                low=bar.low,
                close=bar.close,
                volume=bar.volume,
            )

        cnd: Candle = _bar_to_candle(bar)
        print("Minute:", cnd)

        ld: _LiveData = self._live_data[bar.symbol]
        ld.add_live(cnd)

        self._time = datetime.now()
        if self._time.hour > self._current_hour:
            self._current_hour = self._time.hour

            # On new target-timespan, do the following ...
            # ... aggregate the minute candles into a single target-timespan candle, ...
            hour_cnd: Candle = self._aggregate_min_cnds(bar.symbol)
            ld.add_agg(hour_cnd)
            print(f"\n\nHour: {hour_cnd}\n\n")

            # ... recalculate the indicator values, ...
            for ind in self._indicators:
                ld.update_indicator(ind.name(), ind.compute_values(ld.agg_cnds))

            # ... and apply strategy on the new target-timespan candle
            order: MarketOrder | None = self.on_candle()
            if order is not None:
                self.broker.sync_portfolio()
                self.broker.execute_open_order(order, self.last_close(bar.symbol), self.curr_dt_str)

    @abstractmethod
    def setup(self) -> None:
        """ Called once to setup strategy """
        pass

    @abstractmethod
    def on_candle(self) -> MarketOrder | None:
        """ Called on each new candle """
        pass

    def add_indicator(self, indicator: Indicator) -> str:
        self._indicators.add(indicator)
        # Find the maximum period among all the indicators added to this strategy
        self._max_period = max(self._max_period, indicator.period)
        return indicator.name()

    def ind_crossover(self, symbol: str, val1: str | float, val2: str | float) -> bool:
        ld: _LiveData = self._live_data[symbol]

        s1: list[float] | IndValues = (
            [ val1, val1 ] if isinstance(val1, float)
            # else self.series_slice(self._indicators[val1])
            else ld.agg_inds[str(val1)]
        )
        s2: list[float] | IndValues = (
            [ val2, val2 ] if isinstance(val2, float)
            else ld.agg_inds[str(val1)]
        )

        try:
            return self._crossover(s1, s2)
        except ValueError:
            return False

    def market_buy(self, symbol: str,
        size: float, tp_limit: float | None = None, sl_limit: float | None = None
    ) -> MarketOrder:
        assert size > 0, "Negative size provided. (size > 0)"
        assert symbol in self.symbols, f"Provided ({symbol}) is not in list of symbols ({self.symbols})"

        last_close: float = self.last_close(symbol)
        if tp_limit is not None and sl_limit is not None:
            assert 0.0 < sl_limit < last_close < tp_limit, (
                f"$0.00 < SL(${tp_limit:.3f}) < Price(${last_close:.3f}) < TP(${sl_limit:.3f})"
            )

        mkt_ord: MarketOrder = MarketOrder(
            symbol=symbol,
            side=OrderDir.LONG,
            requested_qty=size,
            requested_price=last_close,
            requested_dt=self.curr_dt_str,
            intent=OrderIntent.BUY_TO_OPEN
        )
        if tp_limit is not None:
            mkt_ord.take_profit = TakeProfitTrigger(
                tp_limit=tp_limit,
                intent=mkt_ord.intent.opp_close()
            )
        if sl_limit is not None:
            mkt_ord.stop_loss = StopLossTrigger(
                sl_limit=sl_limit,
                intent=mkt_ord.intent.opp_close()
            )

        return mkt_ord

    def market_sell(self, symbol: str,
        size: float, tp_limit: float | None = None, sl_limit: float | None = None
    ) -> MarketOrder:
        assert size > 0, "Negative size provided. (size > 0)"
        assert symbol in self.symbols, f"Provided ({symbol}) is not in list of symbols ({self.symbols})"

        last_close: float = self.last_close(symbol)
        if tp_limit is not None and sl_limit is not None:
            assert 0.0 < tp_limit < last_close < sl_limit, (
                f"TP(${tp_limit:.3f}) < Price(${last_close:.3f}) < SL(${sl_limit:.3f})"
            )

        mkt_ord: MarketOrder = MarketOrder(
            symbol=symbol,
            side=OrderDir.SHORT,
            requested_qty=size,
            requested_price=last_close,
            requested_dt=self.curr_dt_str,
            intent=OrderIntent.SELL_TO_OPEN
        )
        if tp_limit is not None:
            mkt_ord.take_profit = TakeProfitTrigger(
                tp_limit=tp_limit,
                intent=mkt_ord.intent.opp_close()
            )
        if sl_limit is not None:
            mkt_ord.stop_loss = StopLossTrigger(
                sl_limit=sl_limit,
                intent=mkt_ord.intent.opp_close()
            )

        return mkt_ord

    def _aggregate_min_cnds(self, symbol: str) -> Candle:
        """ Aggregate minute candles into a single candle w/ the target timespan """
        ld: _LiveData = self._live_data[symbol]
        now = datetime.now(tz=ZoneInfo("America/New_York"))
        start_ts = now - timedelta(hours=1)
        end = now

        # Find starting index
        start_ind: int = 0
        while start_ind < len(ld.live_cnds):
            cnd: Candle = ld.live_cnds[start_ind]
            if cnd.timestamp.hour >= start_ts.hour:
                break

            start_ind += 1

        start_cnd: Candle = ld.live_cnds[start_ind]
        hour_cnd: Candle = Candle(
            timestamp=start_ts,
            open=start_cnd.open,
            high=start_cnd.high,
            low=start_cnd.low,
            close=start_cnd.close,
            volume=start_cnd.volume
        )
        i: int = start_ind + 1
        while i < len(ld.live_cnds):
            cnd: Candle = ld.live_cnds[i]
            if cnd.timestamp > end:
                break

            hour_cnd.high = max(hour_cnd.high, cnd.high)
            hour_cnd.low = min(hour_cnd.low, cnd.low)
            hour_cnd.volume += cnd.volume
            i += 1

        return hour_cnd

    def _crossover(self, val1: list[float] | IndValues, val2: list[float] | IndValues) -> bool:
        if len(val1) >= 2 and len(val2) >= 2:
            return val1[-2] < val2[-2] and val1[-1] > val2[-1]
        else:
            raise ValueError("Both lists should have at least 2 elements")


class StrategyTester:
    def __init__(self,
        sf: Stockframe, start_ind: int = 0, end_ind: int = -1, sleep: bool = False,
    ) -> None:
        self._portfolio: Portfolio = Portfolio()
        self._broker: HistoricalBroker = HistoricalBroker()
        self._indicators: dict[str, IndValues] = {}
        self._sf: Stockframe = sf

        assert start_ind != end_ind
        assert end_ind <= len(sf)
        self._start: int = start_ind
        self._end: int = end_ind if start_ind < end_ind else len(sf)
        self._index: int = self._start

        self._sleep: bool = sleep
        self._repl: CandleReplayer = CandleReplayer(self._sf, start_ind=self._start, sleep=self._sleep)

        # P/L metrics
        self._pl_values: list[float] = []

    def series_slice(self, series: NDArray[np.float64]) -> NDArray[np.float64]:
        return series[self._start:self._index]

    @property
    def last_close(self) -> float:
        return self._sf.close_series[-1]

    @property
    def curr_dt_str(self) -> str:
        return self._repl.current_time.strftime("%Y-%m-%d %H:%M:%S")

    def get_next_candle(self) -> None:
        self._index += 1

    @abstractmethod
    def setup(self) -> None:
        """ Called once """
        pass

    @abstractmethod
    def on_candle(self) -> None:
        """ Called on each candle """
        pass

    def run(self) -> None:
        self.setup()

        while self._index < self._end:
            if self._sleep:
                # Notify user of progress
                print(f"[{self._index}] {self._repl.current_time}")

            # TODO: Check up on any orders that have a take profit or stop loss
            self._broker.order_checkup(self._portfolio, self.last_close, self.curr_dt_str)
            self._portfolio.update_pl()

            if self._repl.is_candle_available():
                self.get_next_candle()
                self.on_candle()
                self._pl_values.append(self._portfolio.pl)

            self._repl.step_time()

    def plot_pl(self, filepath: str | None = None):
        dates = self._sf.timestamp_series

        plt.rcParams['date.converter'] = 'concise'
        _, ax = plt.subplots(figsize=(8, 6), layout='constrained')
        ax.plot(dates, self._pl_values) # type: ignore
        if filepath is None:
            plt.show()
        else:
            plt.savefig(filepath)

    def export_portfolio(self, outdir: str) -> None:
        self._portfolio.save_to_json(f"{outdir}/{self._sf.symbol}-portfolio.json")
