from dataclasses import asdict, dataclass
from zoneinfo import ZoneInfo
from datetime import datetime
from enum import Enum

from trbot import util


@dataclass
class Candle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

    def __post_init__(self):
        self.timestamp = self.timestamp.astimezone(tz=util.MY_TIMEZONE)

    def __repr__(self) -> str:
        return str(self.to_dict())

    def to_dict(self) -> dict:
        output = asdict(self)
        # Format the datetime object a bit better
        output["timestamp"] = str(self.timestamp)
        return output

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



