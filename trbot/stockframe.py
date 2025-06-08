import numpy as np
import pandas as pd
import talib
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

    def get_column(self, column_head: str) -> np.ndarray:
        if column_head in self.df.columns:
            return self.df[column_head].to_numpy()
        else:
            raise Exception(f"Unknown column_head: {column_head}")

class Strategy(metaclass=ABCMeta):
    def __init__(self, sf: StockFrame):
        self._data: StockFrame = sf
        self._indicators: list[float] = []

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

    @abstractmethod
    def setup(self):
        pass

    @abstractmethod
    def on_next_candle(self):
        pass
