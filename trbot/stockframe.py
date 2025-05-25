import pandas as pd
import utils
from bot import Candle


class StockFrame:
    def __init__(self, filepath: str | None = None) -> None:
        self.df: pd.DataFrame = pd.read_csv(filepath) if filepath else pd.DataFrame()

    def add_candle(self, candle: Candle) -> None:
        self.df["date"] = utils.timestamp_to_datetime(candle.timestamp)
        self.df["open"] = candle.open
        self.df["high"] = candle.high
        self.df["low"] = candle.low
        self.df["close"] = candle.close
        self.df["volume"] = candle.volume

    def add_candles(self, candles: list[Candle]) -> None:
        for candle in candles:
            self.add_candle(candle)
