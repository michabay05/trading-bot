from dataclasses import dataclass, field, asdict
from abc import abstractmethod
from datetime import datetime
from dateutil.relativedelta import relativedelta
from typing import Any, Literal
import json, time, os, shutil

import numpy as np
from numpy.typing import NDArray
import talib
import matplotlib.pyplot as plt
from alpaca.data.models.bars import Bar

from . import util, log
from .candles import Candle, Timespan
from .broker import HistoricalBroker, LiveBroker
from .replayer import CandleReplayer
from .portfolio import (
    OrderIntent, OrderDir, Portfolio, MarketOrder,
    StopLossTrigger, TakeProfitTrigger
)
from .stockframe import Stockframe


IndValues = NDArray[np.float64]

IndicatorKind = Literal["sma", "ema", "rsi", "atr"]
CandlePart = Literal["close", "low", "high"]


class Indicator:
    def __init__(self,
        kind: IndicatorKind, part: list[CandlePart], period: int
    ) -> None:
        self._kind: str = kind
        self._parts: list[CandlePart] = part
        self._params: dict[str, Any] = { "timeperiod": period }

    def __repr__(self) -> str:
        return f"Indicator({self._kind}, {self._parts}, params={self._params})"

    @property
    def period(self) -> int:
        return self._params["timeperiod"]

    def compute_from_candles(self, cnds: list[Candle]) -> IndValues:
        assert len(cnds) >= self.period, f"{len(cnds)} >= {self.period}: false"
        candle_chunks: dict[str, IndValues] = {}
        for part in self._parts:
            vals: list[float] = []
            match part:
                case "close":
                    vals = [cnd.close for cnd in cnds]
                case "low":
                    vals = [cnd.low for cnd in cnds]
                case "high":
                    vals = [cnd.high for cnd in cnds]
                case _:
                    raise ValueError(f"Unknown part of a candle: {part}")

            candle_chunks[part] = np.array(vals, dtype=np.float64)

        return self.call_ta_func(candle_chunks)

    def name(self) -> str:
        return f"{self._kind}_{self.period}"

    def call_ta_func(self, cnd_chunks: dict) -> IndValues:
        match self._kind:
            case "sma":
                return talib.SMA(
                    cnd_chunks[self._parts[0]], timeperiod=self.period
                )
            case "ema":
                return talib.EMA(
                    cnd_chunks[self._parts[0]], timeperiod=self.period
                )
            case "rsi":
                return talib.RSI(
                    cnd_chunks[self._parts[0]], timeperiod=self.period
                )
            case "atr":
                return talib.ATR(
                    high=cnd_chunks["high"],
                    low=cnd_chunks["low"],
                    close=cnd_chunks["close"],
                    timeperiod=self.period
                )
            case _:
                raise ValueError(f"Unknown kind of indicator: {self._kind}")


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

    def set_indicator(self, name: str, values: IndValues) -> None:
        self.agg_inds[name] = values

    def to_dict(self) -> dict:
        tmp = asdict(self)
        tmp["live_timespan"] = self.live_timespan.value
        tmp["agg_timespan"] = self.agg_timespan.value
        return tmp


class LiveStrategy:
    def __init__(self) -> None:
        self._broker: LiveBroker = LiveBroker()
        self.symbols: list[str] = [
            "GE", "HPQ", "EBAY", "XLF", "GE", "GOOG", "SPY", "AAPL",
            "PEP", "LOGI", "INTC", "TGT", "WMT", "NIO", "HIMS"
        ]
        self._live_data: dict[str, _LiveData] = {}
        for sym in self.symbols:
            self._live_data[sym] = _LiveData()
        self._conn_alive: bool = False

        self._indicators: set[Indicator] = set()
        self._max_period: int = 0

        self._time = datetime.now(tz=util.MY_TIMEZONE)
        self._current_hour: int = self._time.hour
        self._next_close: datetime = self._time

    def last_close(self, symbol: str) -> float:
        return self._live_data[symbol].agg_cnds[-1].close

    @property
    def curr_dt_str(self) -> str:
        return self._time.strftime("%Y-%m-%d %H:%M:%S")

    def last_ind_value(self, symbol: str, ind_name: str) -> float:
        return self._live_data[symbol].agg_inds[ind_name][-1]

    def _init_all_live_data(self) -> None:
        assert self._max_period > 0

        log.debug(f"Max period: {self._max_period}")
        log.debug(f"Loading data of {self._max_period + 5} candles...")
        for symbol in self.symbols:
            log.debug(f"    Symbol: {symbol}")
            ld = self._live_data[symbol]
            path = f"trout/ohlcv-1hr/{symbol}.csv"
            sf = Stockframe.from_csv(path, symbol, mult=1, timespan=Timespan.HOUR)
            n: int = len(sf) - (self._max_period + 5)
            # Populate enough historical candles so that the indicators can produce values
            # on market open (not be in their warmup phase)
            for i in range(n, len(sf)):
                cnd: Candle = sf.row_to_candle(i)
                ld.add_agg(cnd)

            # Actually, calculate the indicator values based on the candles loaded into memory
            for ind in self._indicators:
                ld.set_indicator(ind.name(), ind.compute_from_candles(ld.agg_cnds))

    def _on_market_open(self) -> None:
        # Bring historical data up to date
        start = datetime.now() - relativedelta(months=1)
        self._broker.export_historical_candles(util.ALL_SYMBOLS, start)
        log.debug(f"Historicals up to date (from {str(start)} to now)")

        self.setup()
        log.info("Indicators setup")
        self._init_all_live_data()
        log.info("Live data initialized")
        log.debug("Live data: [")
        for symbol, ld in self._live_data.items():
            log.debug(f"    {symbol}: {ld.to_dict()}")
        log.debug("]")

        log.info(f"Symbols: {self.symbols}")
        log.info(f"Cash: ${self._broker._portfolio.cash:.2f}")

        if not self._conn_alive:
            self._conn_alive = True
            log.debug("Starting data stream...")
            self._broker._data_stream.run()

        self.start()

    def export_gathered_live_data(self) -> None:
        date_str: str = datetime.now(tz=util.MY_TIMEZONE).strftime("%Y_%m_%d")
        dir: str = f"trout/logs/{date_str}/"
        if os.path.exists(dir):
            assert os.path.isdir(dir)
            shutil.rmtree(dir)

        os.mkdir(dir)
        for symbol, ld in self._live_data.items():
            sf: Stockframe = Stockframe.from_parts(
                ld.live_cnds, symbol, mult=1, timespan=ld.live_timespan
            )
            sf.df.to_csv(f"{dir}/live-{symbol}-{ld.live_timespan.value}.csv", index=False)
            sf = Stockframe.from_parts(
                ld.agg_cnds, symbol, mult=1, timespan=ld.agg_timespan
            )
            sf.df.to_csv(f"{dir}/agg-{symbol}-{ld.agg_timespan.value}.csv", index=False)

    def _on_market_close(self) -> None:
        if self._conn_alive:
            self._broker._data_stream.stop()
            self._conn_alive = False

        # Export live and aggregated candles gathered throughout trading hours
        status: dict = self._broker.get_market_status()
        next_open: datetime = status["next_open"]
        t = datetime.now(tz=util.MY_TIMEZONE)
        # Wake up every 30 minutes and then sleep
        while t < next_open:
            log.info(f"Current time: {t}")
            diff = next_open - t
            sleep_time = min(diff.total_seconds(), 30 * 60)
            log.info(f"Sleeping for {sleep_time} seconds...")
            time.sleep(sleep_time)
            t = datetime.now(tz=util.MY_TIMEZONE)

        self.start()

    def start(self) -> None:
        self._broker._data_stream.subscribe_bars(
            self._stock_data_stream_handler, *self.symbols
        )

        status: dict = self._broker.get_market_status()
        self._next_close = status["next_close"]
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

        cnd: Candle = Candle(
            timestamp=bar.timestamp.astimezone(tz=util.MY_TIMEZONE),
            open=bar.open,
            high=bar.high,
            low=bar.low,
            close=bar.close,
            volume=bar.volume,
        )
        self._live_data[bar.symbol].add_live(cnd)
        log.debug(f"[{bar.symbol:4}] Minute: {cnd}")

        self._time = datetime.now(tz=util.MY_TIMEZONE)
        if cnd.timestamp.hour > self._current_hour:
            self._current_hour = cnd.timestamp.hour

            for symbol in self.symbols:
                log.info(f"Hourly update for {symbol}...")
                symbol_ld = self._live_data[symbol]
                # On new target-timespan, do the following ...
                # ... aggregate the minute candles into a single target-timespan candle, ...
                hour_cnd: Candle = util.aggregate_cnds(symbol_ld.live_cnds, self._time)
                symbol_ld.add_agg(hour_cnd)
                log.debug(f"\n\n{symbol:4}: {hour_cnd}\n\n")

                # ... recalculate the indicator values, ...
                log.debug("Indicator values: [")
                for ind in self._indicators:
                    values = ind.compute_from_candles(symbol_ld.agg_cnds)
                    name = ind.name()
                    symbol_ld.set_indicator(name, values)
                    log.debug(f"    {name}: {values[-1]}")

                log.debug("]")

                # ... and apply strategy on the new target-timespan candle
                order: MarketOrder | None = self.on_candle(symbol)
                if order is not None:
                    self._broker.sync_portfolio()
                    self._broker.execute_open_order(order)
                    log.debug(f"Submitted order: {order}")
                else:
                    log.debug(f"No order")

                log.debug("------------------")

 
        update_live_aggregates(self._live_data)

        if self._time >= self._next_close:
            # Market is closed
            self._on_market_close()

    @abstractmethod
    def setup(self) -> None:
        """ Called once to setup strategy """
        pass

    @abstractmethod
    def on_candle(self, symbol: str) -> MarketOrder | None:
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
            else ld.agg_inds[str(val2)]
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

        if tp_limit is not None and sl_limit is not None:
            assert 0.0 < sl_limit < tp_limit, (
                f"$0.00 < SL(${tp_limit:.3f}) < TP(${sl_limit:.3f})"
            )

        mkt_ord: MarketOrder = MarketOrder(
            symbol=symbol,
            side=OrderDir.LONG,
            requested_qty=size,
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

        if tp_limit is not None and sl_limit is not None:
            assert 0.0 < tp_limit < sl_limit, (
                f"TP(${tp_limit:.3f}) < SL(${sl_limit:.3f})"
            )

        mkt_ord: MarketOrder = MarketOrder(
            symbol=symbol,
            side=OrderDir.SHORT,
            requested_qty=size,
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


def update_live_aggregates(live_datas: dict[str, _LiveData]) -> None:
    export_dir: str = f"./charts-v2/public"
    output: dict = {}

    now: datetime = datetime.now(tz=util.MY_TIMEZONE)
    todays_open: datetime = datetime(
        year=now.year, month=now.month, day=now.month, hour=9, minute=30
    )

    for symbol, live_data in live_datas.items():
        agg_cnds: list[dict] = []
        count: int = 0
        for agc in live_data.agg_cnds:
            if agc.timestamp >= todays_open:
                agg_cnds.append(agc.to_dict())
            else:
                count += 1

        agg_inds: dict[str, list[float]] = {}
        for ind_name, ind_values in live_data.agg_inds.items():
            agg_inds[ind_name] = ind_values.tolist()[count:]

        output[symbol] = {
            "new_candles": agg_cnds,
            "new_indicators": agg_inds
        }

    with open(f"{export_dir}/updates.json", "w") as f:
        json.dump(output, f, indent=4)

