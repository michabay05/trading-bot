from datetime import datetime
from enum import Enum


class Candle:
    def __init__(self, open_: float, high: float, low: float, close: float, volume: float, timestamp: int):
        self.open: float = open_
        self.high: float = high
        self.low: float = low
        self.close: float = close
        self.volume: float = volume
        self.timestamp: int = timestamp

    def __repr__(self) -> str:
        timestamp = timestamp_to_datetime(self.timestamp)
        return (
            f"Candle {{\n   open: {self.open:.2f}\n   high: {self.high:.2f}\n"
            f"   low: {self.low:.2f}\n   close: {self.close:.2f}\n   volume: {self.volume:.1f}\n"
            f"   timestamp: {timestamp}\n}}"
        )

    def __eq__(self, other) -> bool:
        return (self.open == other.open and
                self.high == other.high and
                self.low == other.low and
                self.close == other.close and
                self.volume == other.volume and
                self.timestamp == other.timestamp)


class Timespan(Enum):
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"

    @staticmethod
    def from_str(name: str) -> 'Timespan':
        ts = Timespan[name]
        if ts:
            return ts
        else:
            raise KeyError(f"Unknown timespan: {name}")

    def to_seconds(self) -> int:
        if self == Timespan.DAY:
            # (1 day) * (24hr/day) * (60min/hr) * (60s/min)
            return 24 * 60 * 60
        elif self == Timespan.HOUR:
            # (1 hour) * (60min/hr) * (60s/min)
            return 60 * 60
        elif self == Timespan.MINUTE:
            # (1 minute) * (60s/min)
            return 60
        else:
            raise Exception(f"Unknown timespan: {self.name}")

    def to_ms(self) -> int:
        return self.to_seconds() * 1000

    def __str__(self):
        return self.value



class CandleOption:
    MAX_LIMIT: int = 50000

    def __init__(self, ticker: str, start: str, end: str, mult: int, timespan: Timespan,
        adjusted: bool = True, limit: int = MAX_LIMIT
    ) -> None:
        self.ticker: str = ticker
        self.start: str = start
        self.end: str = end
        self.mult: int = mult
        self.timespan: Timespan = timespan
        self.adjusted: bool = adjusted
        self.limit: int = limit

    def __repr__(self) -> str:
        return (
            f"CandleOption {{\n   ticker: {self.ticker}\n   start: {self.start}"
            f"\n   end: {self.end}\n   mult: {self.mult}\n   timespan: {self.timespan.name}\n}}"
            f"\n   limit: {self.limit}"
        )


def candles_outpath(out_dir: str, ticker: str, mult: int, timespan: Timespan) -> str:
    return f"{out_dir}/ohlcv-{ticker}-{mult}{timespan.value}.csv"

def candle_info_from_path(filepath: str) -> dict:
    # filepath format: {out_dir}/ohlcv-{TICKER}-{MULT}{TIMESPAN}.csv
    #        Example : candles/ohlcv-AAPL-5minute.csv

    # filepath = "candles/ohlcv-AAPL-5minute.csv"
    # path_no_ext = "candles/ohlcv-AAPL-5minute"
    path_no_ext: str = filepath[:-4]

    # parts = ["candles/ohlcv", "AAPL", "5minute"]
    parts: list[str] = path_no_ext.split('-')
    # ticker = "AAPL"
    ticker: str = parts[1]

    i: int = 0
    while i < len(parts[2]):
        if str.isdigit(parts[2][i]):
            i += 1
        else:
            break

    # mult = 5
    mult: int = int(parts[2][0:i])
    # timespan = Timespan.MINUTE
    timespan: Timespan = Timespan.from_str(parts[2][i:].upper())

    return {
        "ticker"  : ticker,
        "mult"    : mult,
        "timespan": timespan
    }

def timestamp_to_datetime(timestamp: int) -> str:
    dt = datetime.fromtimestamp(timestamp/1000)
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def datetime_to_timestamp(dt_str: str) -> int:
    dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
    return int(dt.timestamp() * 1000)
