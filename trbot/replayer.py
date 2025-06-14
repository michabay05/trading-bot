from datetime import datetime, timedelta

from . import candles
from .candles import Candle
from .stockframe import Stockframe

class CandleReplayer:
    # NOTE: (REAL_TIME) ÷ (TIME_FACTOR) = (REPLAY_TIME)
    # DEFAULT_TIME_FACTOR = 2 hour (120 minutes) -> 1 second (7200x speedup)
    DEFAULT_TIME_FACTOR: int = 7200

    def __init__(self, sf: Stockframe, time_factor: float = DEFAULT_TIME_FACTOR, start_ind: int = 0) -> None:
        self._dates: list[str] = sf.df["Date"].to_list()
        assert sf.size == len(self._dates)

        self.time_factor: float = time_factor
        self._index: int = start_ind

        start_dt_str: str = self._dates[self._index]
        self._start_time: datetime = datetime.strptime(start_dt_str, "%Y-%m-%d %H:%M:%S")
        self._time: datetime = self._start_time

        self._is_ready: bool = True

    @property
    def start_time(self) -> datetime:
        return self._start_time

    @property
    def current_time(self) -> datetime:
        return self._time

    def update_time(self, dt_in_sec: float):
        """ Increment timer in seconds """

        if self._index + 1 >= len(self._dates):
            # There are no more candles to make available
            self._is_ready = False
            return

        dt_str: str = self._dates[self._index]
        next_time: datetime = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        if self._time >= next_time:
            self._is_ready = True

        self._time += timedelta(seconds=dt_in_sec * self.DEFAULT_TIME_FACTOR)
        self._time = self._time.replace(second=0, microsecond=0)

    def is_candle_available(self) -> bool:
        if not self._is_ready or self._index >= len(self._dates):
            return False

        # Once this method is called, a candle is assumed to be consumed
        # and the next candle is now not ready
        self._index += 1
        self._is_ready = False
        return True
