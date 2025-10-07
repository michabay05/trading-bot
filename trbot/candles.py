from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum

from alpaca.data.timeframe import TimeFrameUnit
import numpy as np

from .util import MY_TIMEZONE

@dataclass
class Candle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

    def __post_init__(self):
        self.timestamp = self.timestamp.astimezone(tz=MY_TIMEZONE)

    def __repr__(self) -> str:
        return str(self.to_dict())

    def to_dict(self) -> dict:
        output = asdict(self)
        # Format the datetime object a bit better
        output["timestamp"] = str(self.timestamp)
        return output

    def __eq__(self, other) -> bool:
        eps: float = 1e-4
        return (self.open   - other.open <= eps and
                self.high   - other.high <= eps and
                self.low    - other.low <= eps and
                self.close  - other.close <= eps and
                self.volume == other.volume and
                self.timestamp == other.timestamp)


class Timespan(Enum):
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"

    def to_seconds(self) -> int:
        match self:
            case Timespan.DAY:
                # (1 day) * (24hr/day) * (60min/hr) * (60s/min)
                return 24 * 60 * 60
            case Timespan.HOUR:
                # (1 hour) * (60min/hr) * (60s/min)
                return 60 * 60
            case Timespan.MINUTE:
                # (1 minute) * (60s/min)
                return 60

    def to_ms(self) -> int:
        return self.to_seconds() * 1000

    def as_alpaca(self) -> str:
        match self:
            case Timespan.DAY:
                return TimeFrameUnit.Day
            case Timespan.HOUR:
                return TimeFrameUnit.Hour
            case Timespan.MINUTE:
                return TimeFrameUnit.Minute

    def as_yf(self, mult: int = 1) -> str:
        timespan_ltr: str = ""
        match self:
            case Timespan.DAY:
                timespan_ltr = "d"
            case Timespan.HOUR:
                timespan_ltr = "h"
            case Timespan.MINUTE:
                timespan_ltr = "m"

        return f"{mult}{timespan_ltr}"

    def as_str(self, mult: int = 1) -> str:
        timespan_ltr: str = ""
        match self:
            case Timespan.DAY:
                timespan_ltr = "day"
            case Timespan.HOUR:
                timespan_ltr = "hr"
            case Timespan.MINUTE:
                timespan_ltr = "min"

        return f"{mult}{timespan_ltr}"

    def as_timedelta(self, mult: int) -> timedelta:
        match self:
            case Timespan.DAY:
                return timedelta(days=mult)
            case Timespan.HOUR:
                return timedelta(hours=mult)
            case Timespan.MINUTE:
                return timedelta(minutes=mult)

    def __str__(self):
        return self.value

