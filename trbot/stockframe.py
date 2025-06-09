import enum
from typing import Callable, Tuple

import numpy as np
from numpy.typing import NDArray
import pandas as pd
import talib
from talib import MA_Type
from abc import ABCMeta, abstractmethod

from . import candles
from .candles import Candle, CandleOption, Timespan


class StockFrame:
    def __init__(self, cnds: list[Candle], ticker: str, mult: int, timespan: Timespan) -> None:
        data: list[list[str]] = []
        for c in cnds:
            data.append([
                candles.timestamp_to_datetime(c.timestamp),
                f"{c.open:.4f}",
                f"{c.high:.4f}",
                f"{c.low:.4f}",
                f"{c.close:.4f}",
                f"{c.volume:.4f}"
            ])

        self.df: pd.DataFrame = pd.DataFrame(
            data,
            columns=["Date", "Open", "High", "Low", "Close", "Volume"] # type: ignore
        )
        self.ticker: str = ticker
        self.mult: int = mult
        self.timespan: Timespan = timespan

    @classmethod
    def from_filepath(cls, filepath: str) -> 'StockFrame':
        info: dict = candles.candle_info_from_path(filepath)

        sf = cls(cnds=[], ticker=info["ticker"], mult=info["mult"], timespan=info["timespan"])
        sf.df = pd.read_csv(filepath)
        return sf

    def to_csv(self, outdir: str):
        self.df.to_csv(
            candles.candles_outpath("candles", self.ticker, self.mult, self.timespan),
            index=False
        )

    @property
    def close(self) -> NDArray[np.float64]:
        return self.df["Close"].to_numpy()

IndValues = NDArray[np.float64]
TripleIndValues = Tuple[IndValues, IndValues, IndValues]

class Strategy(metaclass=ABCMeta):
    def __init__(self, sf: StockFrame):
        self.data: StockFrame = sf
        self._indicators = {}

    @abstractmethod
    def setup(self) -> None:
        """ Called once """
        pass

    @abstractmethod
    def on_next_candle(self) -> None:
        """ Called on each candle """
        pass

    def crossover(self, val1: np.float64 | np.ndarray, val2: np.float64 | np.ndarray) -> bool:
        # TODO: Handle index out of bounds issue
        if isinstance(val1, np.ndarray) and isinstance(val2, np.ndarray):
            return val1[-2] < val2[-2] and val1[-1] > val2[-1]
        elif isinstance(val1, np.float64) and isinstance(val2, np.ndarray):
            return val1 < val2[-2] and val1 > val2[-1]
        elif isinstance(val1, np.ndarray) and isinstance(val2, np.float64):
            return val1[-2] < val2 and val1[-1] > val2
        else:
            raise TypeError(f"Unknown type -> series1: {type(val1)}, series2: {type(val2)}")

    def sma(self, data: IndValues, period: int = 30) -> IndValues:
        key: str = f"SMA_{period}"
        if key in self._indicators.keys():
            return self._indicators[key]
        else:
            values: IndValues = talib.SMA(data, timeperiod=period)
            self._indicators[key] = values
            return values

    def ema(self, data: IndValues, period: int = 30) -> IndValues:
        key: str = f"EMA_{period}"
        if key in self._indicators.keys():
            return self._indicators[key]
        else:
            values: IndValues = talib.EMA(data, timeperiod=period)
            self._indicators[key] = values
            return values

    def rsi(self, data: IndValues, period: int = 14) -> IndValues:
        key: str = f"RSI_{period}"
        if key in self._indicators.keys():
            return self._indicators[key]
        else:
            values: IndValues = talib.RSI(data, timeperiod=period)
            self._indicators[key] = values
            return values

    def macd(self,
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

    def bbands(
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
