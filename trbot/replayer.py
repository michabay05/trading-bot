from datetime import datetime, timedelta
import time

from .candles import Timespan
from .stockframe import Stockframe

class CandleReplayer:
    def __init__(self,
        sf: Stockframe, start_ind: int = 0, end_ind: int = -1, sleep: bool = False,
        sleep_time: float = 0.5
    ) -> None:
        self._start: int = start_ind
        self._end: int = end_ind if start_ind < end_ind else sf.size
        self._index: int = self._start

        self._dates: list[datetime] = sf.datetime_series
        assert sf.size == len(self._dates)

        # If sleep is enabled, minimum sleep time is 0.25 seconds
        self._real_sleep_time: float = max(0.25, sleep_time)
        self._should_sleep: bool = sleep

        self._original_mult: int = sf.mult
        self._steps_per_s: int = max(self._original_mult // 2, 1)
        self._step_unit: Timespan = sf.timespan

        self._start_time: datetime = self._dates[self._index]
        self._time: datetime = self._start_time

    @property
    def start_time(self) -> datetime:
        return self._start_time

    @property
    def current_time(self) -> datetime:
        return self._time

    @property
    def seconds_to_sleep(self) -> float:
        return self._real_sleep_time

    def step_time(self):
        """ Increment timer in seconds """
        self._time += timedelta(
            # seconds=self._sleep_time_in_s * self._steps_per_s * self._step_unit.to_seconds()
            seconds=self._steps_per_s * self._step_unit.to_seconds()
        )
        if self._should_sleep:
            time.sleep(self.seconds_to_sleep)

    def is_candle_available(self) -> bool:
        if self._index >= self._end:
            return False

        # Once this method is called, a candle is assumed to be consumed
        # and the next candle is now not ready
        next_time: datetime = self._dates[self._index]
        if self._time >= next_time:
            self._index += 1
            return True

        return False
