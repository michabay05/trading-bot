from datetime import datetime

import pandas as pd

from trbot import util
from trbot.candles import Candle, Timespan
from trbot.datafeed import AlpacaDataFeed


def test_multiple_aggs() -> None:
    api_key, secret_key = util.alpaca_keys(acct_name="Alpaca Bot")
    # Start: Thu, July 10, 2025 @ 13:00:00
    start = datetime(year=2025, month=7, day=10, hour=13, minute=00, tzinfo=util.MY_TIMEZONE)
    # End: Thu, July 10, 2025 @ 14:00:00
    end = datetime(year=2025, month=7, day=10, hour=14, minute=00, tzinfo=util.MY_TIMEZONE)
    # Now: Thu, July 10, 2025 @ 14:02:27
    now = datetime(
        year=2025, month=7, day=10, hour=14, minute=2, second=27, tzinfo=util.MY_TIMEZONE
    )
    symbols = util.ALL_SYMBOLS

    adf = AlpacaDataFeed(symbols, acct_name="Alpaca Bot")
    hour_msf = adf.get_historical(symbols, Timespan.HOUR, start=start, end=end)
    minute_msf = adf.get_historical(symbols, Timespan.MINUTE, start=start, end=end)

    # for m_symb, m_df in minute_iter:
    for symbol in symbols:
        print(f"Symbol: {symbol}")

        m_ssf = minute_msf.get_symbol(symbol)
        min_cnds: list[Candle] = []
        for i in range(len(m_ssf)):
            min_cnds.append(m_ssf.row_to_candle(i))
        # NOTE: The `end` value is also included in here; trim the last value
        min_cnds = min_cnds[:60]
        assert len(min_cnds) <= 60

        # Expected our candles
        h_ssf = hour_msf.get_symbol(symbol)
        hour_cnds: list[Candle] = []
        for i in range(len(h_ssf)):
            hour_cnds.append(h_ssf.row_to_candle(i))
        # NOTE: The `end` value is also included in here; trim the last value
        hour_cnds = hour_cnds[:1]
        assert len(hour_cnds) == 1

        agg_cnd: Candle = util.aggregate_cnds(
            min_cnds,
            now=now,
            small_timespan=Timespan.MINUTE,
            large_timespan=Timespan.HOUR
        )

        assert agg_cnd == hour_cnds[0], f"{agg_cnd} != {hour_cnds[0]}"

