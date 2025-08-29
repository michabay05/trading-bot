from dataclasses import dataclass, field, asdict
from abc import abstractmethod
import datetime as dt
from dateutil.relativedelta import relativedelta
from typing import Any, Literal
import json, time, os, shutil

import numpy as np
from numpy.typing import NDArray
import talib

from . import util, log
from .broker import LiveBroker
from .candles import Candle, Timespan
from .datafeed import AlpacaDataFeed, TBDataFeed, YahooDataFeed
from .portfolio import (
    TBIntent, TBOrderDir, TBMarketReq, TBOrderAmount,
    StopLossTrigger, TakeProfitTrigger
)
from .stockframe import SingleStockFrame


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
    def __init__(self,
        acct_name: str, data_source: Literal["alpaca", "yahoo"], symbols: list[str], paper: bool
    ) -> None:
        self._symbols: list[str] = symbols
        self._live_data: dict[str, _LiveData] = {}
        for sym in self._symbols:
            self._live_data[sym] = _LiveData()

        self._broker: LiveBroker = LiveBroker(acct_name, self._symbols, paper=paper)
        self._data_feed: TBDataFeed
        if data_source == "alpaca":
            self._data_feed = AlpacaDataFeed(self._symbols, acct_name)
        else:
            self._data_feed = YahooDataFeed(self._symbols)
        self._data_feed.set_candle_callback(self._on_new_candle)

        self._conn_alive: bool = False

        self._indicators: set[Indicator] = set()
        self._max_period: int = 0

        now = dt.datetime.now(tz=util.MY_TIMEZONE)
        self._last_update: dt.datetime = now
        self._next_close: dt.datetime = now
        # `new_interval` amount of seconds, a new timespan will have been declared
        self._new_interval_min: int = 15
        self._new_timespan_interval: int = self._new_interval_min * 60

    # NOTE: For live trading, instead of using last_close, use curr_price
    # NOTE: Use `self.current_price()` instead
    def last_close(self, symbol: str) -> float:
        return self._live_data[symbol].agg_cnds[-1].close

    def current_price(self, symbol: str) -> float:
        return self._data_feed.get_latest_price(symbol)

    @property
    def curr_dt_str(self) -> str:
        return self._time.strftime("%Y-%m-%d %H:%M:%S")

    @property
    def available_cash(self) -> float:
        return self._broker.portfolio.cash

    def last_ind_value(self, symbol: str, ind_name: str) -> float:
        return self._live_data[symbol].agg_inds[ind_name][-1]

    def _init_all_live_data(self) -> None:
        assert self._max_period > 0, f"Max period can not be negative"
        log.debug(f"Max period: {self._max_period}")
        log.debug(f"Loading data of {self._max_period + 5} candles...")

        # TODO: come here and adjust the start date depending on if the program
        # started running on a Monday or not. On a Monday, you should go upto 4 or 5
        # days backwards.
        end = dt.datetime.now()
        start = end - dt.timedelta(days=4)
        log.debug(f"Date range: {str(start)}...{str(end)}")

        msf = self._data_feed.get_historical(
            self._symbols, Timespan.MINUTE, start, mult=1, end=end
        )

        for symbol in msf.symbols:
            log.debug(f"    Symbol: {symbol}")
            ld = self._live_data[symbol]
            # path = f"trout/ohlcv-1hr/{symbol}.csv"
            # ssf = SingleStockFrame.from_csv(symbol, Timespan.HOUR, path)
            ssf = msf.get_symbol(symbol)
            print(len(ssf))
            n: int = len(ssf) - (self._max_period + 5)
            # Populate enough historical candles so that the indicators can produce values
            # on market open (not be in their warmup phase)
            for i in range(n, len(ssf)):
                cnd: Candle = ssf.row_to_candle(i)
                ld.add_agg(cnd)

            # Actually, calculate the indicator values based on the candles loaded into memory
            for ind in self._indicators:
                ld.set_indicator(ind.name(), ind.compute_from_candles(ld.agg_cnds))

    def _on_market_open(self) -> None:
        # Bring historical data up to date
        start = dt.datetime.now() - relativedelta(months=1)

        # Export the most recent data fetched from the data feed
        msf = self._data_feed.get_historical(self._symbols, Timespan.HOUR, start)
        for symbol in msf._symbols:
            ssf = msf.get_symbol(symbol)
            ssf.save_to_csv(f"trout/ohlcv-1hr/{symbol}.csv")

        log.debug(f"Historicals up to date (from {str(start)} to now)")

        self.setup()
        log.info("Indicators setup")
        self._init_all_live_data()
        log.info("Live data initialized")

        log.info(f"Symbols: {self._symbols}")
        log.info(f"Cash: ${self._broker._portfolio.cash:.2f}")

        # Update current hour variable
        self._time = dt.datetime.now(tz=util.MY_TIMEZONE)
        self._last_update = self._time

    def export_info(self) -> None:
        date_str: str = dt.datetime.now(tz=util.MY_TIMEZONE).strftime("%Y_%m_%d")
        dir: str = f"trout/logs/{date_str}/"
        if os.path.exists(dir):
            assert os.path.isdir(dir), f"Provided path ({dir}) must be a directory"
            shutil.rmtree(dir)

        os.makedirs(dir)
        for symbol, ld in self._live_data.items():
            ssf: SingleStockFrame = SingleStockFrame.from_parts(
                symbol, ld.live_timespan, ld.live_cnds
            )
            ssf.save_to_csv(f"{dir}/live-{symbol}-{ld.live_timespan.value}.csv")
            ssf: SingleStockFrame = SingleStockFrame.from_parts(
                symbol, ld.agg_timespan, ld.agg_cnds
            )
            ssf.save_to_csv(f"{dir}/agg-{symbol}-{ld.agg_timespan.value}.csv")

        # Export the state of the portfolio
        self._broker.portfolio.save_to_json(f"{dir}/portfolio.json")
        
        # Export the broker's temporary information
        self._broker.export_info()

    def _on_market_close(self, next_open: dt.datetime) -> None:
        # Export all info pertaining to how the day went today
        try:
            self.export_info()
        except Exception as e:
            log.error(f"Failed to export portfolio: {repr(e)} ({str(e)})")

        now = dt.datetime.now(tz=util.MY_TIMEZONE)
        # Wake up every 30 minutes and then sleep
        while now < next_open:
            log.info(f"Current time: {now}")
            diff = next_open - now
            sleep_time = min(diff.total_seconds(), 30 * 60)
            log.info(f"Sleeping for {sleep_time:.4f} seconds...")
            time.sleep(sleep_time)
            now = dt.datetime.now(tz=util.MY_TIMEZONE)

    def start_loop(self) -> None:
        status: dict = self._broker.get_market_status()
        self._next_close = status["next_close"]
        if status["is_open"]:
            # Market is currently open
            now = dt.datetime.now(tz=util.MY_TIMEZONE)
            time_til_divisible = now.timestamp() % self._new_timespan_interval
            time_til_divisible = self._new_timespan_interval - time_til_divisible
            # If current time is not divisible by the new interval,
            # (like interval=15min, then divisible = xx:00, xx:15, xx:30, xx:45))
            # then wait until the current time is divisible
            if time_til_divisible != 0.0:
                log.info(
                    f"Waiting for {time_til_divisible:.4f} more seconds "
                    "until time is divisible by interval"
                )
                time.sleep(time_til_divisible)
        else:
            # Market is currently closed
            self._on_market_close(status["next_open"])

        while True:
            self._on_market_open()

            log.debug("Starting data stream...")
            self._data_feed.start_live()

            status = self._broker.get_market_status()
            self._next_close = status["next_close"]
            self._on_market_close(status["next_open"])

    def _on_new_candle(self, symbol: str, cnd: Candle) -> None:
        ld = self._live_data[symbol]
        ld.add_live(cnd)
        log.debug(f"[{symbol:4}] Minute: {cnd}")

        # Manual exits
        order: TBMarketReq | None = self._broker.check_exits(symbol, cnd.close)
        if order is not None:
            self._broker.sync_portfolio()
            assert order.is_to_close(), "Local broker's exit orders must be with the intention to close"
            self._broker.execute_close_order(order, self._data_feed)
            log.debug(f"Submitted order: {order}")
            self._broker.add_order_req(order)

        now = dt.datetime.now(tz=util.MY_TIMEZONE)
        if (now - self._last_update).total_seconds() >= self._new_timespan_interval:
            self._last_update = now
            log.info("Detected new timespan...")

            for symbol in self._symbols:
                try:
                    self.new_timespan_update(symbol)
                except Exception as e:
                    log.error(f"Timespan update error: {repr(e)} ({str(e)})")
                log.debug("------------------")

 
        # Used for live data visualizing
        update_live_aggregates(self._live_data)

        if now > self._next_close:
            # Market is closed
            self._data_feed.end_live()

    def new_timespan_update(self, symbol: str) -> None:
        log.info(f"New timespan update for {symbol}...")
        
        # Reset long and short direction labels if enough time has passed.
        # "enough time" is defined by the attribute inside the broker
        self._broker.check_if_labels_should_reset(symbol)

        symbol_ld = self._live_data[symbol]
        # On new target-timespan, do the following ...
        # ... aggregate the minute candles into a single target-timespan candle, ...

        # TODO: refactor timespan to include a time multiple like 15 mins
        ssf = SingleStockFrame.from_parts(symbol, symbol_ld.live_timespan, symbol_ld.live_cnds)
        # ssf._df["timestamp"] = ssf._df["timestamp"].apply(
        #     lambda x: dt.datetime.fromisoformat(str(x)).astimezone(util.MY_TIMEZONE)
        # )
        ssf._df.set_index("timestamp", inplace=True)
        df = ssf._df.resample("15min", label="left", closed="left").aggregate({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum"
        })
        ssf._df = df.dropna() # type: ignore

        agg_cnd: Candle = ssf.row_to_candle(-1)
        symbol_ld.add_agg(agg_cnd)
        log.debug(f"\n\n{symbol:4}: {agg_cnd}\n\n")

        # ... recalculate the indicator values, ...
        log.debug("Indicator values: [")
        for ind in self._indicators:
            values = ind.compute_from_candles(symbol_ld.agg_cnds)
            name = ind.name()
            symbol_ld.set_indicator(name, values)
            log.debug(f"    {name}: {values[-1]}")

        log.debug("]")

        # ... and apply strategy on the new target-timespan candle
        order: TBMarketReq | None = self.on_candle(symbol)
        if order is not None:
            self._broker.sync_portfolio()
            self._broker.execute_open_order(order, self._data_feed)
            log.debug(f"Submitted order: {order}")
            self._broker.add_order_req(order)
        else:
            log.debug(f"No order")

    @abstractmethod
    def setup(self) -> None:
        """ Called once to setup strategy """
        pass

    @abstractmethod
    def on_candle(self, symbol: str) -> TBMarketReq | None:
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
        size: TBOrderAmount, tp_limit: float | None = None, sl_limit: float | None = None
    ) -> TBMarketReq:
        assert size.amount > 0, "Negative size provided. (size > 0)"
        assert symbol in self._symbols, f"Provided ({symbol}) is not in list of symbols ({self._symbols})"

        if tp_limit is not None and sl_limit is not None:
            assert 0.0 < sl_limit < tp_limit, (
                f"$0.00 < SL(${tp_limit:.3f}) < TP(${sl_limit:.3f})"
            )

        mkt_ord: TBMarketReq = TBMarketReq(
            symbol=symbol,
            side=TBOrderDir.LONG,
            requested_qty=size,
            requested_dt=self.curr_dt_str,
            intent=TBIntent.BUY_TO_OPEN
        )

        curr_price = self._data_feed.get_latest_price(symbol)
        if tp_limit is not None:
            mkt_ord.take_profit = TakeProfitTrigger(
                tp_limit=max(tp_limit, curr_price + 0.01),
                intent=mkt_ord.intent.opp_close()
            )
        if sl_limit is not None:
            mkt_ord.stop_loss = StopLossTrigger(
                sl_limit=min(sl_limit, curr_price - 0.01),
                intent=mkt_ord.intent.opp_close()
            )

        return mkt_ord

    def market_sell(self, symbol: str,
        size: TBOrderAmount, tp_limit: float | None = None, sl_limit: float | None = None
    ) -> TBMarketReq:
        assert size.amount > 0, "Negative size provided. (size > 0)"
        assert symbol in self._symbols, f"Provided ({symbol}) is not in list of symbols ({self._symbols})"

        if tp_limit is not None and sl_limit is not None:
            assert 0.0 < tp_limit < sl_limit, (
                f"TP(${tp_limit:.3f}) < SL(${sl_limit:.3f})"
            )

        mkt_ord: TBMarketReq = TBMarketReq(
            symbol=symbol,
            side=TBOrderDir.SHORT,
            requested_qty=size,
            requested_dt=self.curr_dt_str,
            intent=TBIntent.SELL_TO_OPEN
        )

        curr_price = self._data_feed.get_latest_price(symbol)
        if tp_limit is not None:
            mkt_ord.take_profit = TakeProfitTrigger(
                tp_limit=min(tp_limit, curr_price - 0.01),
                intent=mkt_ord.intent.opp_close()
            )
        if sl_limit is not None:
            mkt_ord.stop_loss = StopLossTrigger(
                sl_limit=max(sl_limit, curr_price + 0.01),
                intent=mkt_ord.intent.opp_close()
            )

        return mkt_ord

    def _crossover(self, val1: list[float] | IndValues, val2: list[float] | IndValues) -> bool:
        if len(val1) >= 2 and len(val2) >= 2:
            return val1[-2] < val2[-2] and val1[-1] > val2[-1]
        else:
            raise ValueError("Both lists should have at least 2 elements")


def update_live_aggregates(live_datas: dict[str, _LiveData]) -> None:
    export_dir: str = f"./charts-v2/public"
    output: dict = {}

    now: dt.datetime = dt.datetime.now(tz=util.MY_TIMEZONE)
    todays_open: dt.datetime = dt.datetime(
        year=now.year, month=now.month, day=now.month, hour=9, minute=30,
        tzinfo=util.MY_TIMEZONE
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
