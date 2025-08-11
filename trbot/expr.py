from datetime import datetime, timedelta

from .candles import Timespan
from .datafeed import AlpacaDataFeed
from .util import MY_TIMEZONE


datafeed = AlpacaDataFeed(symbols=["AAPL"], acct_name="Bot 03")
start = datetime.now() - timedelta(days=10)
msf = datafeed.get_historical(["AAPL"], Timespan.MINUTE, start)
df = msf.get_symbol("AAPL")._df
df.to_csv("./AAPL_orig.csv", index=False)

df["timestamp"] = df["timestamp"].apply(
    lambda x: datetime.fromisoformat(str(x)).astimezone(MY_TIMEZONE)
)
df.set_index("timestamp", inplace=True)
resamp = df.resample("1h", label="left").aggregate({
    "open": "first",
    "high": "max",
    "low": "min",
    "close": "last",
    "volume": "sum"
})
resamp.dropna(inplace=True)
resamp.to_csv("./AAPL_resamp.csv", index=True)
print(resamp)
