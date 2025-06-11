from datetime import datetime, timedelta

from . import candles
from .candles import Candle
from .stockframe import Stockframe

class CandleReplayer:
    # NOTE: (REAL_TIME) ÷ (TIME_FACTOR) = (REPLAY_TIME)
    # DEFAULT_TIME_FACTOR = 0.25 hour (15 minutes) -> 1 second (900x speedup)
    DEFAULT_TIME_FACTOR: int = 900

    def __init__(self, sf: Stockframe, time_factor: float = DEFAULT_TIME_FACTOR) -> None:
        self._sf: Stockframe = sf

        self.time_factor: float = time_factor
        self._index: int = 0

        start_dt_str: str = self._sf.df["Date"].iloc[self._index]
        self._start_time: datetime = datetime.strptime(start_dt_str, "%Y-%m-%d %H:%M:%S")
        self._time: datetime = self._start_time

        self._is_ready: bool = True

    @property
    def stockframe(self):
        return self._sf

    @property
    def current_time(self) -> datetime:
        return self._time

    @property
    def last_price(self) -> float:
        """ Returns the last close price """
        return self._sf.df["Close"].iloc[self._index - 1]

    def update_time(self, dt_in_sec: float):
        """ Increment timer in seconds """

        if self._index + 1 >= self.candle_count():
            # There are no more candles to make available
            self._is_ready = False
            return

        dt_str: str = self._sf.df["Date"].iloc[self._index]
        next_time: datetime = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        if self._time >= next_time:
            self._is_ready = True

        self._time += timedelta(seconds=dt_in_sec * self.DEFAULT_TIME_FACTOR)
        self._time = self._time.replace(second=0, microsecond=0)

    def grab_next_candle(self) -> Candle | None:
        if not self._is_ready or self._index >= self.candle_count():
            return None

        # Once candle is used, next candle is now not ready
        self._is_ready = False
        row = self._sf.df.iloc[self._index]

        # Extract values from the Series and convert to appropriate types
        candle = Candle(
            open_=float(row["Open"]),
            high=float(row["High"]),
            low=float(row["Low"]),
            close=float(row["Close"]),
            volume=float(row["Volume"]),
            timestamp=candles.datetime_to_timestamp(row["Date"])
        )

        self._index += 1
        return candle

    def candle_count(self) -> int:
        return len(self._sf.df)
