from datetime import datetime

import pandas as pd

from trbot import util
from trbot.candles import Candle, Timespan


def test_multiple_aggs() -> None:
    api_key, secret_key = util.alpaca_keys()
    # Start: Thu, July 10, 2025 @ 13:00:00
    start = datetime(year=2025, month=7, day=10, hour=13, minute=00, tzinfo=util.MY_TIMEZONE)
    # End: Thu, July 10, 2025 @ 14:00:00
    end = datetime(year=2025, month=7, day=10, hour=14, minute=00, tzinfo=util.MY_TIMEZONE)
    # Now: Thu, July 10, 2025 @ 14:02:27
    now = datetime(
        year=2025, month=7, day=10, hour=14, minute=2, second=27, tzinfo=util.MY_TIMEZONE
    )
    symbols = util.ALL_SYMBOLS
    hour_dfs: pd.DataFrame = util.alpaca_get_historical(
        symbols=symbols,
        api_key=api_key,
        secret_key=secret_key,
        start=start,
        end=end,
        mult=1,
        timespan=Timespan.HOUR
    )
    minute_dfs: pd.DataFrame = util.alpaca_get_historical(
        symbols=symbols,
        api_key=api_key,
        secret_key=secret_key,
        start=start,
        end=end,
        mult=1,
        timespan=Timespan.MINUTE
    )

    minute_iter = util.alpaca_df_to_individual(minute_dfs)
    hour_iter = util.alpaca_df_to_individual(hour_dfs)

    for m_symb, m_df in minute_iter:
        h_symb, h_df = next(hour_iter)
        assert m_symb == h_symb
        print(f"Symbol: {h_symb}")

        min_cnds: list[Candle] = []
        for i in range(0, len(m_df)):
            row: pd.Series = m_df.iloc[i]
            min_cnds.append(Candle(**row.to_dict()))

        # NOTE: The `end` value is also included in here; trim the last value
        min_cnds = min_cnds[:60]
        assert len(min_cnds) <= 60

        # Expected our candles
        hour_cnds: list[Candle] = []
        for i in range(0, len(h_df)):
            row: pd.Series = h_df.iloc[i]
            hour_cnds.append(Candle(**row.to_dict()))
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

