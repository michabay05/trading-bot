from typing import Iterator
from zoneinfo import ZoneInfo
from datetime import datetime
import time

import pandas as pd
from alpaca.data.models import BarSet
from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

from .tbsecrets import ALPACA_SECRETS
from .candles import Candle, Timespan


ALL_SYMBOLS: list[str] = [
    "AAPL", "ABNB", "BBY", "DASH", "DELL", "EBAY", "F", "GE", "GOOG", "HIMS",
    "HPQ", "INTC", "LOGI", "NIO", "NVDA", "PANW", "PEP", "PLTR", "QCOM",
    "ROST", "SHOP", "SMCI", "SPY", "TGT", "WMT", "XLF"
]

MY_TIMEZONE = ZoneInfo("America/New_York")

def alpaca_keys(acct_name: str) -> tuple[str, str]:
    """ Access my keys from alpaca """
    return (ALPACA_SECRETS[acct_name]["api_key"], ALPACA_SECRETS[acct_name]["secret_key"])

def detect_new_timespan(timespan: Timespan, t: datetime, now: datetime) -> bool:
    match timespan:
        case Timespan.DAY:
            return now.day > t.day
        case Timespan.HOUR:
            return now.hour > t.hour
        case Timespan.MINUTE:
            return now.minute > t.minute

def aggregate_cnds(smaller_cnds: list[Candle], now: datetime,
    small_timespan: Timespan = Timespan.MINUTE, large_timespan: Timespan = Timespan.HOUR
) -> Candle:
    """ Aggregate smaller timespan candles into a single candle w/ a lager timespan """
    start_hour = now.hour - 1
    end_hour = now.hour
    # Find starting index
    start_ind: int = 0
    while start_ind < len(smaller_cnds):
        cnd: Candle = smaller_cnds[start_ind]
        if cnd.timestamp.hour >= start_hour:
            break

        start_ind += 1

    start_cnd: Candle = smaller_cnds[start_ind]
    agg_cnd: Candle = Candle(
        timestamp=datetime(
            now.year, now.month, now.day, start_hour,
            minute=00, second=00, tzinfo=MY_TIMEZONE
        ),
        open=start_cnd.open,
        high=start_cnd.high,
        low=start_cnd.low,
        close=start_cnd.close,
        volume=start_cnd.volume
    )
    i: int = start_ind + 1
    while i < len(smaller_cnds):
        cnd: Candle = smaller_cnds[i]
        if cnd.timestamp.hour >= end_hour:
            break

        agg_cnd.high = max(agg_cnd.high, cnd.high)
        agg_cnd.low = min(agg_cnd.low, cnd.low)
        agg_cnd.volume += cnd.volume
        agg_cnd.close = cnd.close
        i += 1

    return agg_cnd

