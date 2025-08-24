from datetime import datetime, timedelta
import os

import pandas as pd

from trbot import strategy, util
from trbot.candles import Candle, Timespan
from trbot.datafeed import YahooDataFeed
from trbot.stockframe import MultStockFrame, SingleStockFrame


def test_multiple_aggs() -> None:
    live_csv_path = "tests/agg_test_data_live.csv"
    agg_csv_path = "tests/agg_test_data_agg.csv"
    if not (os.path.exists(live_csv_path) and os.path.exists(agg_csv_path)):
        today = datetime.now().date()
        end = datetime(
            year=today.year, month=today.month, day=today.day,
            hour=15, minute=00, second=00
        ).astimezone(util.MY_TIMEZONE)
        start = (end - timedelta(hours=5)).astimezone(util.MY_TIMEZONE)
        print(f"Start: {str(start)}")
        print(f"  End: {str(end)}")

        symbols = ["AAPL", "AMZN", "GOOG", "NKE", "TGT", "WMT", "GE"]

        ydf = YahooDataFeed(symbols)
        live_msf = ydf.get_historical(
            symbols, Timespan.MINUTE, start, mult=1, end=end
        )
        agg_msf = ydf.get_historical(
            symbols, Timespan.MINUTE, start, mult=15, end=end
        )
        live_msf.save_to_csv(live_csv_path)
        agg_msf.save_to_csv(agg_csv_path)
    else:
        live_msf = MultStockFrame.from_csv(Timespan.MINUTE, live_csv_path)
        agg_msf = MultStockFrame.from_csv(Timespan.MINUTE, agg_csv_path)

        symbols = live_msf._symbols


    for symbol in symbols:
        l_ssf = live_msf.get_symbol(symbol)
        expected_ssf = agg_msf.get_symbol(symbol)
        df = l_ssf._df.resample("15min", label="left", closed="left").aggregate({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum"
        })

        a_ssf = SingleStockFrame(symbol, Timespan.MINUTE, df)
        assert len(a_ssf) == len(expected_ssf)

        for i in range(len(a_ssf)):
            a_cnd = a_ssf.row_to_candle(i)
            expected_cnd = expected_ssf.row_to_candle(i)

            assert a_cnd == expected_cnd
        

