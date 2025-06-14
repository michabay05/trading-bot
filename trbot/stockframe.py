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

        self.df: pd.DataFrame = pd.DataFrame(
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
        sf.df = pd.read_csv(filepath)
        return sf

    def save_to_csv(self, outdir: str):
        self.df.to_csv(
            candles.candles_outpath(outdir, self.ticker, self.mult, self.timespan),
            index=False
        )

    @property
    def size(self) -> int:
        return len(self.df)

    @property
    def close(self) -> NDArray[np.float64]:
        return self.df["Close"].to_numpy()
