from datetime import datetime
from zoneinfo import ZoneInfo

from . import util
from .candles import Timespan
from .datafeed import AlpacaDataFeed


datafeed = AlpacaDataFeed(symbols=["AAPL"], acct_name="Bot 03")
zi = ZoneInfo("America/New_York")
end = datetime(2025, 7, 24, 15, 00, tzinfo=util.MY_TIMEZONE)
start = datetime(2025, 7, 23, 9, 30, tzinfo=util.MY_TIMEZONE)
print(f"start = {str(start)}")
print(f"  end = {str(end)}")

msf = datafeed.get_historical(["AAPL"], Timespan.MINUTE, start, mult=1, end=end)
df = msf.get_symbol("AAPL")._df
df.to_csv("./AAPL_orig.csv", index=False)

# df.set_index("timestamp", inplace=True)
resamp = df.resample("15min", label="left", closed="left").aggregate({
    "open": "first",
    "high": "max",
    "low": "min",
    "close": "last",
    "volume": "sum"
})
resamp.dropna(inplace=True)
resamp.to_csv("./AAPL_resamp.csv", index=True)
print(resamp)
