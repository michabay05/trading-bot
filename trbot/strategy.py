from abc import ABCMeta, abstractmethod
import math

import numpy as np
from numpy.typing import NDArray
import talib

from .broker import Broker
from .stockframe import Stockframe
from .replayer import CandleReplayer
from .portfolio import OrderIntent, OrderSide, Portfolio, MarketOrder, StopLossRequest, TakeProfitRequest


IndValues = NDArray[np.float64]
TripleIndValues = tuple[IndValues, IndValues, IndValues]

class StrategyTester(metaclass=ABCMeta):
    def __init__(self,
        sf: Stockframe, start_ind: int = 0, end_ind: int = -1, sleep: bool = False
    ) -> None:
        self._portfolio: Portfolio = Portfolio()
        self._broker: Broker = Broker()
        self._indicators: dict[str, IndValues] = {}
        self._sf: Stockframe = sf

        assert start_ind != end_ind
        assert end_ind <= sf.size
        self._start: int = start_ind
        self._end: int = end_ind if start_ind < end_ind else sf.size
        self._index: int = self._start

        self._sleep: bool = sleep
        self._repl: CandleReplayer = CandleReplayer(self._sf, start_ind=self._start, sleep=self._sleep)

    @property
    def last_close(self) -> float:
        return self._sf.close_series[self._index-1]

    def series_slice(self, series: NDArray[np.float64]) -> NDArray[np.float64]:
        return series[self._start:self._index]

    def last_ind_value(self, ind_key: str) -> float:
        return self._indicators[ind_key][self._index-1]

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
            if self._sleep:
                # Notify user of progress
                print(f"[{self._index}] {self._repl.current_time}")

            # TODO: Check up on any orders that have a take profit or stop loss
            self._broker.order_checkup(self._portfolio, self.last_close, self.curr_dt_str)

            if self._repl.is_candle_available():
                self.get_next_candle()
                self.on_candle()

            self._repl.step_time()

        return {
            "pl": self._portfolio.pl
        }

    def market_buy(self,
        size: float, tp_limit: float | None = None, sl_limit: float | None = None
    ) -> None:
        assert size > 0, "Negative size provided. (size > 0)"

        qty: float = 0.0
        if size < 1.0:
            # In essence, buy as much shares as possible with this amount:
            #   >> size * portfolio.capital
            pct: float = size
            max_ord_value: float = pct * self._portfolio.capital
            qty = math.floor(max_ord_value / self.last_close)
        else:
            qty = int(size)

        mkt_ord: MarketOrder = MarketOrder(
            symbol=self._sf.ticker,
            side=OrderSide.BUY,
            quantity=qty,
            requested_price=self.last_close,
            requested_dt=self.curr_dt_str,
            intent=OrderIntent.BUY_TO_OPEN
        )
        if tp_limit is not None:
            mkt_ord.take_profit = TakeProfitRequest(tp_limit=tp_limit)
        if sl_limit is not None:
            mkt_ord.stop_loss = StopLossRequest(sl_limit=sl_limit)

        self._broker.execute_open_order(mkt_ord, self._portfolio, self.last_close, self.curr_dt_str)

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

    def TA_ATR(self,
        high: NDArray[np.float64], low: NDArray[np.float64], close: NDArray[np.float64],
        period: int = 14
    ) -> str:
        key: str = f"ATR_{period}"
        if not key in self._indicators.keys():
            values: IndValues = talib.ATR(high, low, close, timeperiod=period)
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
