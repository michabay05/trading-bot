import operator
import pandas as pd

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
            columns=["date", "open", "high", "low", "close", "volume"] # type: ignore
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


class CandleReplayer:
    # NOTE: (REAL_TIME) ÷ (TIME_FACTOR) = (REPLAY_TIME)
    # DEFAULT_TIME_FACTOR = 1 min -> 1 second (60x speedup)
    DEFAULT_TIME_FACTOR = 60

    def __init__(self, sf: StockFrame, time_factor: float = DEFAULT_TIME_FACTOR) -> None:
        self.sf: StockFrame = sf
        self.time_factor: float = time_factor
        # this timer has units of seconds
        self.timer: float = 0.0
        self.is_ready: bool = False
        self.index: int = 0

    def delay_time(self) -> float:
        """ Returns time to delay in SECONDS """
        return self.sf.mult * self.sf.timespan.to_seconds() / self.time_factor

    def update_time(self, dt_in_sec: float):
        """ Increment timer in seconds """
        if self.timer >= self.delay_time():
            self.timer = 0.0
            self.is_ready = True
        else:
            self.timer += dt_in_sec

    def grab_next_candle(self) -> Candle | None:
        if not self.is_ready or self.index >= self.candle_count():
            return None

        self.is_ready = False
        row = self.sf.df.iloc[self.index]

        # Extract values from the Series and convert to appropriate types
        candle = Candle(
            open_=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=float(row["volume"]),
            timestamp=candles.datetime_to_timestamp(row["date"])
        )

        self.index += 1
        return candle

    def candle_count(self) -> int:
        return len(self.sf.df)
