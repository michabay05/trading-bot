from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
from numpy.typing import NDArray
import pandas as pd
import talib
import matplotlib.pyplot as plt
from alpaca.data.models.bars import Bar

from trbot.candles import Candle, Timespan
from .broker import Broker, HistoricalBroker, LiveBroker
from .replayer import CandleReplayer
from .portfolio import OrderIntent, OrderSide, Portfolio, MarketOrder, StopLossTrigger, TakeProfitTrigger
from .stockframe import Stockframe


IndValues = NDArray[np.float64]
TripleIndValues = tuple[IndValues, IndValues, IndValues]


class TBStrategy(ABC):
    ## ============= PROPERTIES USED IN THESE ABSTRACT METHOD (BELOW) ============= ##
    @property
    @abstractmethod
    def symbol(self) -> str:
        pass

    @property
    @abstractmethod
    def indicators(self) -> dict[str, IndValues]:
        pass

    @property
    @abstractmethod
    def broker(self) -> Broker:
        pass

    @property
    @abstractmethod
    def portfolio(self) -> Portfolio:
        pass
    ## ============= PROPERTIES USED IN THESE ABSTRACT METHOD (ABOVE) ============= ##

    @abstractmethod
    def setup(self) -> None:
        """ Called once """
        pass

    @abstractmethod
    def on_candle(self) -> None:
        """ Called on each candle """
        pass

    @property
    @abstractmethod
    def close_series(self) -> IndValues:
        pass

    @property
    @abstractmethod
    def high_series(self) -> IndValues:
        pass

    @property
    @abstractmethod
    def low_series(self) -> IndValues:
        pass

    def last_ind_value(self, ind_key: str) -> float:
        return self.indicators[ind_key][-1]

    @property
    def last_close(self) -> float:
        return self.close_series[-1]

    @property
    @abstractmethod
    def curr_dt_str(self) -> str:
        pass

    @abstractmethod
    def run(self) -> None:
        pass

    def market_buy(self,
        size: float, tp_limit: float | None = None, sl_limit: float | None = None
    ) -> None:
        assert size > 0, "Negative size provided. (size > 0)"
        if tp_limit is not None and sl_limit is not None:
            assert 0.0 < sl_limit < self.last_close < tp_limit, (
                f"$0.00 < SL(${tp_limit:.3f}) < Price(${self.last_close:.3f}) < TP(${sl_limit:.3f})"
            )

        mkt_ord: MarketOrder = MarketOrder(
            symbol=self.symbol,
            side=OrderSide.LONG,
            quantity=size,
            requested_price=self.last_close,
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

        self.broker.execute_open_order(mkt_ord, self.last_close, self.curr_dt_str)

    def market_sell(self,
        size: float, tp_limit: float | None = None, sl_limit: float | None = None
    ) -> None:
        assert size > 0, "Negative size provided. (size > 0)"
        if tp_limit is not None and sl_limit is not None:
            assert 0.0 < tp_limit < self.last_close < sl_limit, (
                f"TP(${tp_limit:.3f}) < Price(${self.last_close:.3f}) < SL(${sl_limit:.3f}), {self.symbol}"
            )

        mkt_ord: MarketOrder = MarketOrder(
            symbol=self.symbol,
            side=OrderSide.SHORT,
            quantity=size,
            requested_price=self.last_close,
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

        self.broker.execute_open_order(mkt_ord, self.last_close, self.curr_dt_str)

    def TA_SMA(self, data: IndValues, period: int = 30) -> str:
        key: str = f"SMA_{period}"
        if not key in self.indicators.keys():
            values: IndValues = talib.SMA(data, timeperiod=period)
            self.indicators[key] = values

        return key

    def TA_EMA(self, data: IndValues, period: int = 30) -> str:
        key: str = f"EMA_{period}"
        if not key in self.indicators.keys():
            values: IndValues = talib.EMA(data, timeperiod=period)
            self.indicators[key] = values

        return key

    def TA_ATR(self,
        high: NDArray[np.float64], low: NDArray[np.float64], close: NDArray[np.float64],
        period: int = 14
    ) -> str:
        key: str = f"ATR_{period}"
        if not key in self.indicators.keys():
            values: IndValues = talib.ATR(high, low, close, timeperiod=period)
            self.indicators[key] = values

        return key

    def TA_RSI(self, data: IndValues, period: int = 14) -> str:
        key: str = f"RSI_{period}"
        if not key in self.indicators.keys():
            values: IndValues = talib.RSI(data, timeperiod=period)
            self.indicators[key] = values

        return key

    def ind_crossover(self, val1: str | float, val2: str | float) -> bool:
        s1: list[float] | IndValues = (
            [ val1, val1 ] if isinstance(val1, float)
            else self.series_slice(self._indicators[val1])  # type: ignore
        )
        s2: list[float] | IndValues = (
            [ val2, val2 ] if isinstance(val2, float)
            else self.series_slice(self._indicators[val2])  # type: ignore
        )

        try:
            return self._crossover(s1, s2)
        except ValueError:
            return False

    def _crossover(self, val1: list[float] | IndValues, val2: list[float] | IndValues) -> bool:
        if len(val1) >= 2 and len(val2) >= 2:
            return val1[-2] < val2[-2] and val1[-1] > val2[-1]
        else:
            raise ValueError("Both lists should have at least 2 elements")


class StrategyTester(TBStrategy):
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
        dates = self._sf.timestamp

        plt.rcParams['date.converter'] = 'concise'
        _, ax = plt.subplots(figsize=(8, 6), layout='constrained')
        ax.plot(dates, self._pl_values) # type: ignore
        if filepath is None:
            plt.show()
        else:
            plt.savefig(filepath)

    def export_portfolio(self, outdir: str) -> None:
        self._portfolio.save_to_json(f"{outdir}/{self._sf.symbol}-portfolio.json")


class LiveStrategy(TBStrategy):
    def __init__(self) -> None:
        self._broker: LiveBroker = LiveBroker()
        self._symbol: str = "DELL"
        self._minute_sf: Stockframe = Stockframe(
            self._symbol, mult=1, timespan=Timespan.MINUTE
        )
        self._minute_sf._df.set_index("timestamp", inplace=True)
        self._hour_sf: Stockframe = Stockframe(self._symbol, mult=1, timespan=Timespan.HOUR)
        self._indicators: dict[str, IndValues] = {}

        self._time: datetime = datetime.now()

    @property
    def symbol(self) -> str:
        return self._symbol

    @property
    def indicators(self) -> dict[str, IndValues]:
        return self._indicators

    @property
    def broker(self) -> LiveBroker:
        return self._broker

    @property
    def last_candle(self) -> Candle:
        return LiveStrategy._df_row_to_candle(self._minute_sf.df, -1)

    @property
    def portfolio(self) -> Portfolio:
        return self.broker.portfolio

    @property
    def curr_dt_str(self) -> str:
        return self.last_candle.timestamp.strftime("%Y-%m-%d %H:%M:%S")

    def run(self) -> None:
        self.broker._data_stream.subscribe_bars(
            self._stock_data_stream_handler, *[self.symbol]
        )
        self.broker._data_stream.run()

    async def _stock_data_stream_handler(self, data: Bar | dict) -> None:
        if isinstance(data, dict):
            raise ValueError(f"I have no idea what is inside this dict: {data}")

        cnd = self._bar_to_candle(data)
        self._minute_sf.append_candle(cnd)

        self.setup()
        self.on_candle()
        print(cnd)

        self._time = datetime.now()
        # TODO: Change this from check the minute to checking the current hour vs the last updated hour
        if self._time.minute == 00:
            # Full hour
            self.aggregate_hourly()

        if not self._broker.is_market_open():
            self.broker._data_stream.stop()

    @staticmethod
    def _df_row_to_candle(df: pd.DataFrame, i: int) -> Candle:
        row = df.iloc[i]
        return Candle(**row.to_dict())

    def aggregate_hourly(self) -> None:
        """ Using the ~1minute stockframe, update the 1 hour stockframe"""
        sf: Stockframe = self._minute_sf
        now = datetime.now(tz=ZoneInfo("America/New_York"))
        start_ts = now - timedelta(hours=1)
        end = now

        # Find starting index
        start_ind: int = 0
        while start_ind < len(sf):
            cnd: Candle = LiveStrategy._df_row_to_candle(sf.df, start_ind)
            if cnd.timestamp.hour >= start_ts.hour:
                break

            start_ind += 1

        start_cnd: Candle = LiveStrategy._df_row_to_candle(sf.df, start_ind)
        hour_cnd: Candle = Candle(
            timestamp=start_ts,
            open=start_cnd.open,
            high=start_cnd.high,
            low=start_cnd.low,
            close=start_cnd.close,
            volume=start_cnd.volume
        )
        i: int = start_ind + 1
        while i < len(sf):
            row = sf.df.iloc[i]
            cnd: Candle = Candle(**row.to_dict())
            if cnd.timestamp > end:
                break

            hour_cnd.high = max(hour_cnd.high, cnd.high)
            hour_cnd.low = min(hour_cnd.low, cnd.low)
            hour_cnd.volume += cnd.volume
            i += 1

        self._hour_sf.append_candle(hour_cnd)

    def test(self) -> None:
        self._minute_sf._df.to_csv("DELL_minute.csv", index=False)
        self._hour_sf._df.to_csv("DELL_hour.csv", index=False)

    @abstractmethod
    def setup(self) -> None:
        """ Called once """
        pass

    @abstractmethod
    def on_candle(self) -> None:
        """ Called on each candle """
        pass

    def series_slice(self, series: NDArray[np.float64]) -> NDArray[np.float64]:
        return series[:-1]

    @property
    def close_series(self) -> IndValues:
        return self._hour_sf.close_series

    @property
    def high_series(self) -> IndValues:
        return self._hour_sf.high_series

    @property
    def low_series(self) -> IndValues:
        return self._hour_sf.low_series

    def _bar_to_candle(self, bar: Bar) -> Candle:
        return Candle(
            timestamp=bar.timestamp,
            open=bar.open,
            high=bar.high,
            low=bar.low,
            close=bar.close,
            volume=bar.volume,
        )
