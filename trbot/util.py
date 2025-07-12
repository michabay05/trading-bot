from typing import Iterator, Literal
from zoneinfo import ZoneInfo
from datetime import datetime
from dateutil.relativedelta import relativedelta
import time

import pandas as pd
from alpaca.data.models import BarSet
from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

from tbsecrets import ALPACA_SECRETS
from candles import Candle, Timespan


ALL_SYMBOLS: list[str] = [
    "AAPL", "ABNB", "BBY", "DASH", "DELL", "EBAY", "F", "GE", "GOOG", "HIMS",
    "HPQ", "INTC", "LOGI", "NIO", "NVDA", "NVDY", "PANW", "PEP", "PLTR", "QCOM",
    "ROST", "SHOP", "SMCI", "SPY", "TGT", "WMT", "XLF"
]

MY_TIMEZONE = ZoneInfo("America/New_York")

def alpaca_keys(index: int = 0) -> tuple[str, str]:
    """ Access my keys from alpaca """
    return (ALPACA_SECRETS[index]["api_key"], ALPACA_SECRETS[index]["secret_key"])

def alpaca_get_historical(symbols: list[str], api_key: str, secret_key: str, start: datetime,
    end: datetime, mult: int = 1, timespan: Timespan = Timespan.HOUR
) -> pd.DataFrame:
    stock_historical_data_client = StockHistoricalDataClient(api_key, secret_key, raw_data=False)
    print(f"[{symbols}] {start} -> {end}")

    # Convert from my timespan to alpaca's time frame
    timeframe = TimeFrameUnit.Hour
    match timespan:
        case Timespan.HOUR:
            timeframe = TimeFrameUnit.Hour
        case Timespan.MINUTE:
            timeframe = TimeFrameUnit.Minute
        case _:
            raise ValueError(f"Unknown timespan: {timespan.value}")

    req = StockBarsRequest(
        symbol_or_symbols=symbols,
        timeframe=TimeFrame(amount=mult, unit=timeframe),
        start=start,
        end=end
    )

    df: pd.DataFrame = pd.DataFrame()
    t: float = time.time()
    bars = stock_historical_data_client.get_stock_bars(req)
    if not isinstance(bars, BarSet):
        raise TypeError(f"bars is of type {type(bars)} instead of BarSet.")

    diff: float = time.time() - t
    print(f"Took {diff:.4f}s to gather bars")

    # Reset index to make it a regular column
    df = bars.df.copy()
    df.reset_index(inplace=True)
    # Modify the timestamp column
    df["timestamp"] = df["timestamp"].apply(
        lambda x: datetime.fromisoformat(str(x)).astimezone(MY_TIMEZONE)
    )
    # Set it back as (part of) the index
    df.set_index(["symbol", "timestamp"], inplace=True)

    return df

def alpaca_df_to_individual(alpaca_df: pd.DataFrame) -> Iterator[tuple[str, pd.DataFrame]]:
    alpaca_df.reset_index(inplace=True)
    symbols: set[str] = set(alpaca_df["symbol"])

    for symbol in sorted(symbols):
        sliced_df = alpaca_df[alpaca_df["symbol"] == symbol].copy()
        if not isinstance(sliced_df, pd.DataFrame):
            raise TypeError(f"sliced_df is of type {type(sliced_df)} instead of pd.DataFrame")

        del sliced_df["trade_count"]
        del sliced_df["vwap"]
        sliced_df.drop("symbol", axis=1, inplace=True)
        yield symbol, sliced_df

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

