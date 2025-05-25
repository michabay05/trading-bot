import pandas as pd

from . import candles
from .candles import Candle, Timespan


class StockFrame:
    def __init__(self, ticker: str, mult: int, timespan: Timespan, pd_df: pd.DataFrame = pd.DataFrame()) -> None:
        self.df: pd.DataFrame = pd_df
        self.ticker: str = ticker
        self.mult: int = mult
        self.timespan: Timespan = timespan

    @classmethod
    def from_filepath(cls, filepath: str) -> 'StockFrame':
        info: dict = candles.candle_info_from_path(filepath)

        return cls(
            pd_df=pd.read_csv(filepath),
            ticker=info["ticker"],
            mult=info["mult"],
            timespan=info["timespan"]
        )

    def add_candle(self, candle: Candle) -> None:
        self.df["date"] = candles.timestamp_to_datetime(candle.timestamp)
        self.df["open"] = candle.open
        self.df["high"] = candle.high
        self.df["low"] = candle.low
        self.df["close"] = candle.close
        self.df["volume"] = candle.volume

    def add_candles(self, candles: list[Candle]) -> None:
        for candle in candles:
            self.add_candle(candle)


class CandleReplayer:
    def __init__(self, sf: StockFrame, time_factor: float = 1000.0) -> None:
        self.sf: StockFrame = sf
        self.time_factor: float = time_factor
