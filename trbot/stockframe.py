from datetime import datetime

import pandas as pd

from . import util
from .candles import Candle, Timespan

class SingleStockFrame:
    def __init__(self,
        symbol: str, timespan: Timespan, df: pd.DataFrame = pd.DataFrame()
    ) -> None:
        self._df: pd.DataFrame = df
        self._symbol: str = symbol
        self._timespan: Timespan = timespan

    @classmethod
    def from_parts(cls,
        symbol: str, timespan: Timespan, cnds: list[Candle]
    ) -> 'SingleStockFrame':
        df_cols: dict[str, list] = {
            "timestamp": [],
            "open": [],
            "high": [],
            "low": [],
            "close": [],
            "volume": [],
        }
        for c in cnds:
            df_cols["timestamp"].append(c.timestamp)
            df_cols["open"].append(c.open)
            df_cols["high"].append(c.high)
            df_cols["low"].append(c.low)
            df_cols["close"].append(c.close)
            df_cols["volume"].append(c.volume)

        return cls(symbol, timespan, pd.DataFrame.from_dict(df_cols))

    @classmethod
    def from_csv(cls, symbol: str, timespan: Timespan, csv_path: str) -> 'SingleStockFrame':
        df = pd.read_csv(csv_path, index_col=False)
        df["timestamp"] = df["timestamp"].apply(
            lambda x: datetime.fromisoformat(str(x)).astimezone(util.MY_TIMEZONE)
        )
        return cls(symbol, timespan, df)

    def row_to_candle(self, i: int) -> Candle:
        row: pd.Series = self._df.iloc[i]
        return Candle(**row.to_dict())

    def save_to_csv(self, out_path: str, index: bool = False) -> None:
        self._df.to_csv(out_path, index=index)

    def __repr__(self) -> str:
        output: str = f"Symbol: {self._symbol}\n"
        output += f"Timespan: {self._timespan}\n"
        output += str(self._df)
        return output

    def __len__(self) -> int:
        return len(self._df)


class MultStockFrame:
    def __init__(self, timespan: Timespan, df: pd.DataFrame = pd.DataFrame()) -> None:
        self._df: pd.DataFrame = df
        self._symbols: set[str] = set(self._df["symbols"])
        self._timespan: Timespan = timespan

    @classmethod
    def from_yf(cls, timespan: Timespan, yf_df: pd.DataFrame) -> 'MultStockFrame':
        # Transform to long format: Date and Ticker as columns, single-level headers
        df = yf_df.stack(future_stack=True, level=0).rename_axis(["timestamp", "symbols"])
        # Remove the 'Price' name from the columns index
        df.columns.name = None

        if isinstance(df, pd.Series):
            raise TypeError(f"df is of type {type(df)} instead of pd.DataFrame")

        df.sort_values(["symbols", "timestamp"], inplace=True)
        df.reset_index(inplace=True)
        df["timestamp"] = df["timestamp"].apply(
            lambda x: datetime.fromisoformat(str(x)).astimezone(util.MY_TIMEZONE)
        )

        df.rename(columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        }, inplace=True)

        return cls(timespan, df)

    @classmethod
    def from_alpaca(cls, timespan: Timespan, alpaca_df: pd.DataFrame) -> 'MultStockFrame':
        # Reset index to make it a regular column
        df = alpaca_df.reset_index()
        df.rename(columns={"symbol": "symbols"}, inplace=True)
        # Modify the timestamp column
        df["timestamp"] = df["timestamp"].apply(
            lambda x: datetime.fromisoformat(str(x)).astimezone(util.MY_TIMEZONE)
        )
        if "trade_count" in df.columns:
            del df["trade_count"]
        if "vwap" in df.columns:
            del df["vwap"]

        return cls(timespan, df)

    def get_symbol(self, symbol: str) -> SingleStockFrame:
        if not symbol in self._symbols:
            raise KeyError(f"Could not find '{symbol}' in dataframe")

        symbol_df = self._df[self._df["symbols"] == symbol].copy()
        assert isinstance(symbol_df, pd.DataFrame)
        symbol_df.drop("symbols", axis=1, inplace=True)

        return SingleStockFrame(symbol, self._timespan, symbol_df)

    def __repr__(self) -> str:
        output: str = f"Symbol: {self._symbols}\n"
        output += f"Timespan: {self._timespan}\n"
        output += str(self._df)
        return output

    def __len__(self) -> int:
        return len(self._df)
