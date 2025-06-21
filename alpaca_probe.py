from zoneinfo import ZoneInfo
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import time

import pandas as pd

from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from alpaca.trading.client import TradingClient

import tbsecrets


API_KEY: str = tbsecrets.ALPACA_SECRETS["api_key"]
SECRET_KEY: str = tbsecrets.ALPACA_SECRETS["secret_key"]
# trade_client = TradingClient(API_KEY, SECRET_KEY)

symbols = ["GM", "INTC", "SMCI", "WMT", "F", "TGT", "HPQ", "BBY", "SKX"]
stock_historical_data_client = StockHistoricalDataClient(API_KEY, SECRET_KEY, raw_data=False)
zone = ZoneInfo("America/New_York")
dt = datetime(year=2025, month=6, day=19, hour=9, minute=30)
start = dt - relativedelta(years=6, months=10)
end = dt
print(f"[{symbols}] {start} -> {end}")
req = StockBarsRequest(
    symbol_or_symbols=symbols,
    timeframe=TimeFrame(amount=4, unit=TimeFrameUnit.Hour),
    start=start,
    end=end
)

t: float = time.time()
bars = stock_historical_data_client.get_stock_bars(req)
diff: float = time.time() - t
print(f"Took {diff:.4f}s to gather bars")

# Reset index to make it a regular column
df = bars.df.copy()
df.reset_index(inplace=True)
# Modify the timestamp column
df["timestamp"] = df["timestamp"].apply(
    lambda x: datetime.fromisoformat(str(x)).astimezone(zone)
)
# Set it back as (part of) the index
df = df.set_index(["symbol", "timestamp"])
df.to_csv("test.csv")
print(">", len(df))
