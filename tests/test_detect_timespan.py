from datetime import datetime, timedelta
import random

from trbot import util
from trbot.candles import Timespan

def test_detect_timespan():
    start = datetime(2025, 7, 24, 9, 30, tzinfo=util.MY_TIMEZONE)
    t = start
    now = start
    end = datetime(2025, 7, 24, 16, 00, tzinfo=util.MY_TIMEZONE)
    count: int = 0

    rnd = random.Random()

    while t < end:
        # dmin = rnd.uniform(1, 3)
        # now += timedelta(minutes=dmin)
        now += timedelta(minutes=rnd.uniform(1, 3))

        if util.detect_new_timespan(Timespan.HOUR, t.hour, now):
            t = now
            # print(f"New hour: {t}")
            count += 1

    assert count == (end.hour - start.hour)


test_detect_timespan()
