from abc import ABCMeta, abstractmethod
import math, time

import numpy as np
from numpy.typing import NDArray
import talib
from talib._ta_lib import MA_Type

from . import broker
from .candles import Candle
from .stockframe import Stockframe
from .replayer import CandleReplayer
from .portfolio import OrderStatus, Portfolio, Order, OrderType, Position


IndValues = NDArray[np.float64]
TripleIndValues = tuple[IndValues, IndValues, IndValues]

class StrategyTester(metaclass=ABCMeta):
    def __init__(self,
        sf: Stockframe, start_ind: int = 0, end_ind: int = -1, sleep: bool = False
    ) -> None:
        self._portfolio: Portfolio = Portfolio()
        self._indicators: dict[str, IndValues] = {}
        self._sf: Stockframe = sf
        self._start: int = start_ind
        self._end: int = end_ind if start_ind < end_ind else sf.size
        self._sleep: bool = sleep
        self._repl: CandleReplayer = CandleReplayer(self._sf, start_ind=self._start, sleep=self._sleep)
        self._index: int = self._start

    @property
    def last_close(self) -> float:
        return self._sf.close_series[self._index-1]

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

    def run(self) -> dict:
        self.setup()

        while self._index < self._end:
            # if self._sleep:
            if True:
                # Notify user of progress
                n: int = len(self._portfolio.incomplete_orders)
                print(f"[{self._index}:{n}] {self._repl.current_time}")

            # Check up on any orders that have a take profit or stop loss
            completed_ord_inds: list[int] = []
            for i, order in enumerate(self._portfolio.incomplete_orders):
                if order.type == OrderType.TP:
                    tp_limit: float = order.issue_price
                    tp_cross: bool = self.last_close >= tp_limit if order.is_long() else self.last_close <= tp_limit
                    if tp_cross:
                        # When take profit is crossed, a sell market order is issued ...
                        tp_order: Order = Order(
                            symbol=order.symbol,
                            order_type=OrderType.MARKET,
                            quantity=order.quantity,
                            issue_price=self.last_close,
                            issue_dt=order.issue_dt,
                        )
                        broker.execute_market_order(tp_order, self._portfolio, self.curr_dt_str)
                        if order.status == OrderStatus.FILLED:
                            completed_ord_inds.append(i)

            for ind in reversed(completed_ord_inds):
                del self._portfolio.incomplete_orders[ind]

            if self._repl.is_candle_available():
                self.get_next_candle()
                self.on_candle()

            self._repl.step_time()

        return {
            "pl": self._portfolio.pl
        }

    def market_buy(self, size: float, take_profit: float | None = None) -> None:
        size = abs(size)
        qty: float = 0.0
        if size < 1.0:
            # In essence, buy as much shares as possible with this amount:
            #   > size * portfolio.capital
            pct: float = size
            max_ord_value: float = pct * self._portfolio.capital
            qty = math.floor(max_ord_value / self.last_close)
        else:
            qty = int(size)

        order: Order = Order(
            symbol=self._sf.ticker,
            order_type=OrderType.MARKET,
            quantity=qty,
            issue_price=self.last_close,
            issue_dt=self.curr_dt_str,
        )
        broker.execute_market_order(order, self._portfolio, self.curr_dt_str)

        if take_profit is not None:
            tp_order: Order = Order(
                symbol=self._sf.ticker,
                order_type=OrderType.TP,
                quantity=order.quantity * -1.0,
                issue_price=order.issue_price,
                issue_dt=order.issue_dt
            )
            self._portfolio.add_incomplete_order(tp_order)

    def market_sell(self, size: int) -> None:
        size = -abs(size)
        order: Order = Order(
            symbol=self._sf.ticker,
            order_type=OrderType.MARKET,
            quantity=size,
            issue_price=self.last_close,
            issue_dt=self.curr_dt_str
        )
        broker.execute_market_order(order, self._portfolio, self.curr_dt_str)

    def close_position(self) -> None:
        broker.close_position(self._portfolio, self._sf.ticker, self.last_close)

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
            return _crossover(s1, s2)
        except ValueError:
            return False

    def export_portfolio(self, outdir: str) -> None:
        self._portfolio.save_to_json(f"{outdir}/{self._sf.ticker}-portfolio.json")

    # =========================== INDICATORS ===========================
    def TA_SMA(self, data: IndValues, period: int = 30) -> str:
        key: str = f"SMA_{period}"
        if not key in self._indicators.keys():
            values: IndValues = talib.SMA(data, timeperiod=period)
            self._indicators[key] = values

        return key

    def TA_EMA(self, data: IndValues, period: int = 30) -> str:
        key: str = f"EMA_{period}"
        if not key in self._indicators.keys():
            values: IndValues = talib.EMA(data, timeperiod=period)
            self._indicators[key] = values

        return key

    def TA_RSI(self, data: IndValues, period: int = 14) -> str:
        key: str = f"RSI_{period}"
        if not key in self._indicators.keys():
            values: IndValues = talib.RSI(data, timeperiod=period)
            self._indicators[key] = values

        return key


def _crossover(val1: list[float] | IndValues, val2: list[float] | IndValues) -> bool:
    if len(val1) >= 2 and len(val2) >= 2:
        return val1[-2] < val2[-2] and val1[-1] > val2[-1]
    else:
        raise ValueError("Both lists should have at least 2 elements")
