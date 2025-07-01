from datetime import datetime
import pandas as pd
import numpy as np
from numpy.typing import NDArray

from . import candles
from .candles import Candle, Timespan


class Stockframe:
    def __init__(self, ticker: str, mult: int, timespan: Timespan):
        self._df: pd.DataFrame = pd.DataFrame(
            columns=["datetime", "open", "high", "low", "close", "volume"], # type: ignore
        )
        self._formatted_dts: list[datetime] = []
        self.symbol: str = ticker
        self.mult: int = mult
        self.timespan: Timespan = timespan

    @classmethod
    def from_parts(cls, cnds: list[Candle], ticker: str, mult: int, timespan: Timespan) -> None:
        data: list[list[str]] = []
        for c in cnds:
            data.append([
                f"{c.datetime}",
                f"{c.open:.4f}",
                f"{c.high:.4f}",
                f"{c.low:.4f}",
                f"{c.close:.4f}",
                f"{c.volume:.4f}"
            ])

        sf = cls(ticker, mult, timespan)
        sf._df = pd.DataFrame(
            data,
            columns=["datetime", "open", "high", "low", "close", "volume"], # type: ignore
        )
        sf.parse_datetime("datetime")


    @classmethod
    def from_csv(cls, filepath: str, ticker: str, mult: int, timespan: Timespan) -> 'Stockframe':
        sf = cls(ticker=ticker, mult=mult, timespan=timespan)
        sf._df = pd.read_csv(filepath)
        if "timestamp" in sf._df.columns:
            sf._df.rename(columns={"timestamp": "datetime"}, inplace=True)

        sf.parse_datetime("datetime")
        return sf

    def __repr__(self) -> str:
        output = f"{self.symbol} on {self.mult} {self.timespan.value} interval\n"
        output += f"{self._df}"
        return output

    def parse_datetime(self, col_name: str) -> None:
        self._formatted_dts: list[datetime] = []
        for dt_str in self._df[col_name]:
            self._formatted_dts.append(datetime.fromisoformat(dt_str))

    def save_to_csv(self, outdir: str) -> None:
        self._df.to_csv(
            candles.candles_outpath(outdir, self.symbol, self.mult, self.timespan),
            index=False
        )

    def append_candle(self, cnd: Candle) -> None:
        # columns=["datetime", "open", "high", "low", "close", "volume"],
        self._df.loc[len(self._df)] = [
            cnd.datetime,
            cnd.open,
            cnd.high,
            cnd.low,
            cnd.close,
            cnd.volume,
        ]

    @property
    def df(self):
        return self._df

    @property
    def size(self) -> int:
        return len(self._df)

    @property
    def close_series(self) -> NDArray[np.float64]:
        return self._df["close"].to_numpy()

    @property
    def high_series(self) -> NDArray[np.float64]:
        return self._df["high"].to_numpy()

    @property
    def low_series(self) -> NDArray[np.float64]:
        return self._df["low"].to_numpy()

    @property
    def datetime_series(self) -> list[datetime]:
        return self._formatted_dts
