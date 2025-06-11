from abc import ABCMeta, abstractmethod
import numpy as np
from numpy.typing import NDArray
from typing import Tuple

import talib
from talib._ta_lib import MA_Type

from . import broker
from .stockframe import Stockframe
from .replayer import CandleReplayer
from .portfolio import Portfolio, Order, OrderType


IndValues = NDArray[np.float64]
TripleIndValues = Tuple[IndValues, IndValues, IndValues]

class Strategy(metaclass=ABCMeta):
    def __init__(self, sf: Stockframe):
        self.replayer: CandleReplayer = CandleReplayer(sf)
        self.portfolio: Portfolio = Portfolio()
        self._indicators = {}

    @property
    def data(self) -> Stockframe:
        return self.replayer.stockframe

    @property
    def current_price(self) -> float:
        return self.replayer.last_price

    @abstractmethod
    def setup(self) -> None:
        """ Called once """
        pass

    @abstractmethod
    def on_candle(self) -> None:
        """ Called on each candle """
        pass

    def buy(self, size: int) -> None:
        order: Order = Order(
            symbol=self.data.ticker,
            order_type=OrderType.MARKET,
            quantity=float(size),
            purchase_price=self.current_price,
            purchase_dt=self.replayer.current_time.strftime("%Y-%m-%d %H:%M:%S")
        )

        broker.execute_order(order, self.portfolio)

    def sell(self, size: int) -> None:
        order: Order = Order(
            symbol=self.data.ticker,
            order_type=OrderType.MARKET,
            quantity=float(size) * -1.0,
            purchase_price=self.current_price,
            purchase_dt=self.replayer.current_time.strftime("%Y-%m-%d %H:%M:%S")
        )

        broker.execute_order(order, self.portfolio)

    def crossover(self,
        val1: np.float64 | NDArray[np.float64], val2: np.float64 | NDArray[np.float64]
    ) -> bool:
        if isinstance(val1, np.ndarray) and isinstance(val2, np.ndarray):
            if len(val1) >= 2 and len(val2) >= 2:
                return val1[-2] < val2[-2] and val1[-1] > val2[-1]
            else:
                raise ValueError("Both lists should have at least 2 elements")
        elif isinstance(val1, np.float64) and isinstance(val2, np.ndarray):
            if len(val2) >= 2:
                return val1 < val2[-2] and val1 > val2[-1]
            else:
                raise ValueError("The second list should have at least 2 elements")
        elif isinstance(val1, np.ndarray) and isinstance(val2, np.float64):
            if len(val1) >= 2:
                return val1[-2] < val2 and val1[-1] > val2
            else:
                raise ValueError("The first list should have at least 2 elements")
        else:
            raise TypeError(f"Unknown type -> series1: {type(val1)}, series2: {type(val2)}")

    def TA_SMA(self, data: IndValues, period: int = 30) -> IndValues:
        key: str = f"SMA_{period}"
        if key in self._indicators.keys():
            return self._indicators[key]
        else:
            values: IndValues = talib.SMA(data, timeperiod=period)
            self._indicators[key] = values
            return values

    def TA_EMA(self, data: IndValues, period: int = 30) -> IndValues:
        key: str = f"EMA_{period}"
        if key in self._indicators.keys():
            return self._indicators[key]
        else:
            values: IndValues = talib.EMA(data, timeperiod=period)
            self._indicators[key] = values
            return values

    def TA_RSI(self, data: IndValues, period: int = 14) -> IndValues:
        key: str = f"RSI_{period}"
        if key in self._indicators.keys():
            return self._indicators[key]
        else:
            values: IndValues = talib.RSI(data, timeperiod=period)
            self._indicators[key] = values
            return values

    def TA_MACD(self,
        data: IndValues, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9
    ) -> TripleIndValues:
        key: str = f"MACD_fp{fast_period}_sp{slow_period}_signal{signal_period}"
        if key in self._indicators.keys():
            return self._indicators[key]
        else:
            values: TripleIndValues = talib.MACD(
                data,
                fastperiod=fast_period,
                slowperiod=slow_period,
                signalperiod=signal_period
            )
            self._indicators[key] = values
            return values

    def TA_BBANDS(
        self,
        data: IndValues, period: int = 14, stddevup: float = 2, stddevdn: float = 2,
        use_sma: bool = True
    ) -> TripleIndValues:
        key: str = f"BBANDS_p{period}_sdup{stddevup}_sddn{stddevdn}"
        if key in self._indicators.keys():
            return self._indicators[key]
        else:
            values: TripleIndValues = talib.BBANDS(
                data,
                timeperiod=period,
                nbdevup=stddevup,
                nbdevdn=stddevdn,
                matype=MA_Type.SMA if use_sma else MA_Type.EMA,
            )
            self._indicators[key] = values
            return values
