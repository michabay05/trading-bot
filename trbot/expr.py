from datetime import datetime
from zoneinfo import ZoneInfo

from .candles import Timespan
from .datafeed import AlpacaDataFeed
from .util import MY_TIMEZONE


datafeed = AlpacaDataFeed(symbols=["AAPL"], acct_name="Bot 03")
zi = ZoneInfo("America/New_York")
end = datetime(2025, 7, 24, 15, 00, tzinfo=zi)
start = datetime(2025, 7, 23, 9, 30, tzinfo=zi)
print(f"start = {str(start)}")
print(f"  end = {str(end)}")

msf = datafeed.get_historical(["AAPL"], Timespan.MINUTE, start, end)
df = msf.get_symbol("AAPL")._df
df.to_csv("./AAPL_orig.csv", index=False)

df["timestamp"] = df["timestamp"].apply(
    lambda x: datetime.fromisoformat(str(x)).astimezone(MY_TIMEZONE)
)
df.set_index("timestamp", inplace=True)
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
