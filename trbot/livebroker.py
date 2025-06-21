from alpaca.trading.requests import LimitOrderRequest, MarketOrderRequest
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import (
    AssetExchange,
    AssetStatus,
    OrderClass,
    OrderSide,
    OrderType,
    QueryOrderStatus,
    TimeInForce,
)

import tbsecrets


API_KEY: str = tbsecrets.ALPACA_SECRETS["api_key"]
SECRET_KEY: str = tbsecrets.ALPACA_SECRETS["secret_key"]

trade_client: TradingClient = TradingClient(api_key=API_KEY, secret_key=SECRET_KEY, paper=True)

symbol: str = "INTC"
req = MarketOrderRequest(
    symbol=symbol,
    qty=3,
    side=OrderSide.BUY,
    type=OrderType.MARKET,
    time_in_force=TimeInForce.GTC,
)
LimitOrderRequest(

)
res = trade_client.submit_order(req)
