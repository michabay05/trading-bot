import pandas as pd
import numpy as np
from numpy.typing import NDArray

from . import candles
from .candles import Candle, Timespan


class Stockframe:
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

        self._df: pd.DataFrame = pd.DataFrame(
            data,
            columns=["Date", "Open", "High", "Low", "Close", "Volume"] # type: ignore
        )
        self.ticker: str = ticker
        self.mult: int = mult
        self.timespan: Timespan = timespan

    @classmethod
    def from_csv(cls, filepath: str) -> 'Stockframe':
        info: dict = candles.candle_info_from_path(filepath)

        sf = cls(cnds=[], ticker=info["ticker"], mult=info["mult"], timespan=info["timespan"])
        sf._df = pd.read_csv(filepath)
        return sf

    def save_to_csv(self, outdir: str):
        self._df.to_csv(
            candles.candles_outpath(outdir, self.ticker, self.mult, self.timespan),
            index=False
        )

    @property
    def df(self):
        return self._df

    @property
    def size(self) -> int:
        return len(self._df)

    @property
    def close_series(self) -> NDArray[np.float64]:
        return self._df["Close"].to_numpy()

    @property
    def high_series(self) -> NDArray[np.float64]:
        return self._df["High"].to_numpy()

    @property
    def low_series(self) -> NDArray[np.float64]:
        return self._df["Low"].to_numpy()

    @property
    def date_series(self) -> list[str]:
        return self._df["Date"].to_list()
