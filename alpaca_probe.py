from zoneinfo import ZoneInfo
from datetime import datetime, timedelta
from alpaca.data.enums import DataFeed
from dateutil.relativedelta import relativedelta

from alpaca.data.models.bars import Bar
from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, OrderType, TimeInForce
from alpaca.data.live.stock import StockDataStream

from trbot import tbsecrets


API_KEY: str = tbsecrets.ALPACA_SECRETS["api_key"]
SECRET_KEY: str = tbsecrets.ALPACA_SECRETS["secret_key"]

trade_client = TradingClient(API_KEY, SECRET_KEY)
acct = trade_client.get_account()
print(acct)

# df = pd.read_csv("test1.csv", index_col=["symbol", "timestamp"])
# print(df)

# df.reset_index(inplace=True)
# symbols: set[str] = set(df["symbol"])

# for symbol in symbols:
#     sliced_df = df[df["symbol"] == symbol].copy()
#     sliced_df.drop("symbol", axis=1, inplace=True)
#     sliced_df.to_csv(f"{symbol}.csv", index=False)

# sliced_df = df.loc["AAPL", :]
# print(sliced_df)
# =========================== Ex. 1 ===========================
# stock_historical_data_client = StockHistoricalDataClient(API_KEY, SECRET_KEY, raw_data=False)
# zone = ZoneInfo("America/New_York")
# dt = datetime(year=2025, month=6, day=24, hour=9, minute=30)
# start = dt - relativedelta(years=6, months=10)
# end = dt
# print(f"[{symbols}] {start} -> {end}")
# req = StockBarsRequest(
#     symbol_or_symbols=symbols,
#     timeframe=TimeFrame(amount=1, unit=TimeFrameUnit.Hour),
#     start=start,
#     end=end
# )

# df: pd.DataFrame = pd.DataFrame()
# try:
#     t: float = time.time()
#     bars = stock_historical_data_client.get_stock_bars(req)
#     diff: float = time.time() - t
#     print(f"Took {diff:.4f}s to gather bars")

#     # Reset index to make it a regular column
#     df = bars.df.copy()
#     df.reset_index(inplace=True)
#     # Modify the timestamp column
#     df["timestamp"] = df["timestamp"].apply(
#         lambda x: datetime.fromisoformat(str(x)).astimezone(zone)
#     )
#     # Set it back as (part of) the index
#     df = df.set_index(["symbol", "timestamp"])
# finally:
#     df.to_csv("test1.csv")
#     print(">", len(df))

# =========================== Ex. 2 ===========================
# trade_client = TradingClient(API_KEY, SECRET_KEY)
# req = MarketOrderRequest(
#     symbol = "AAPL",
#     qty = 1.4,
#     side = OrderSide.BUY,
#     type = OrderType.MARKET,
#     time_in_force = TimeInForce.DAY,
# )
# res = trade_client.submit_order(req)
# print(res)
