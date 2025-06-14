from abc import ABCMeta, abstractmethod
import time

import numpy as np
from numpy.typing import NDArray
import talib
from talib._ta_lib import MA_Type

from . import broker
from .candles import Candle
from .stockframe import Stockframe
from .replayer import CandleReplayer
from .portfolio import Portfolio, Order, OrderType


IndValues = NDArray[np.float64]
TripleIndValues = tuple[IndValues, IndValues, IndValues]

class Strategy(metaclass=ABCMeta):
    def __init__(self, sf: Stockframe):
        self._portfolio: Portfolio = Portfolio()
        self._indicators: dict[str, IndValues] = {}
        self._sf: Stockframe = sf
        self._start: int = 0
        self._repl: CandleReplayer = CandleReplayer(self._sf, start_ind=self._start)
        self._ind: int = self._start

    @property
    def last_close(self) -> float:
        return self._sf.close[self._ind-1]

    def series_slice(self, series: NDArray[np.float64]) -> NDArray[np.float64]:
        return series[self._start:self._ind]

    @property
    def curr_time_str(self) -> str:
        return self._repl.current_time.strftime("%Y-%m-%d %H:%M:%S")

    def get_next_candle(self):
        self._ind += 1

    @abstractmethod
    def setup(self) -> None:
        """ Called once """
        pass

    @abstractmethod
    def on_candle(self) -> Order | None:
        """ Called on each candle """
        pass

    def run(self) -> None:
        self.setup()

        t: float = time.time()
        dt: float = 0.0
        while self._ind < self._sf.size:
            current: float = time.time()
            dt = current - t

            self._repl.update_time(dt)

            if self._repl.is_candle_available():
                print(f"{self._repl.current_time} -> New Candle")
                self.get_next_candle()
                order: Order | None = self.on_candle()
                if order is not None:
                    broker.execute_order(order, self._portfolio)
                    print(order)
            else:
                print(self._repl.current_time)

            time.sleep(1)
            t = current

    def buy(self, size: int) -> Order:
        return Order(
            symbol=self._sf.ticker,
            order_type=OrderType.MARKET,
            quantity=float(size),
            purchase_price=self.last_close,
            purchase_dt=self.curr_time_str
        )

    def sell(self, size: int) -> Order:
        return Order(
            symbol=self._sf.ticker,
            order_type=OrderType.MARKET,
            quantity=float(size) * -1.0,
            purchase_price=self.last_close,
            purchase_dt=self.curr_time_str
        )

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
            print(f">> {s1[-4:]}")
            print(f">> {s2[-4:]}")
        except IndexError:
            print(f">> {s1}")
            print(f">> {s2}")

        try:
            return _crossover(s1, s2)
        except ValueError as v_err:
            print(f"[ERROR] {str(v_err)}")
            return False

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
