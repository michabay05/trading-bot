from abc import ABC, abstractmethod
from datetime import datetime
from zoneinfo import ZoneInfo
import json, sys, time

from alpaca.data import RawData
from alpaca.data.live.stock import StockDataStream
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, OrderStatus, OrderType, QueryOrderStatus, TimeInForce
from alpaca.trading.models import Clock, TradeAccount
from alpaca.data.models import BarSet
from alpaca.trading.requests import ClosePositionRequest, GetOrdersRequest, MarketOrderRequest, StopLossRequest, TakeProfitRequest
from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
import requests
import pandas as pd

from trbot import util

from . import candles, tbsecrets, log
from .tbsecrets import ALPACA_SECRETS
from .candles import Candle, CandleOption, Timespan
from .portfolio import OrderDir, TBOrder, Portfolio, MarketOrder, OrderState, Position


class InsufficientFundsError(Exception):
    pass


class Broker(ABC):
    ## ============= PROPERTIES USED IN THESE ABSTRACT CLASS (BELOW) ============= ##
    @property
    @abstractmethod
    def portfolio(self) -> Portfolio:
        pass
    ## ============= PROPERTIES USED IN THESE ABSTRACT CLASS (ABOVE) ============= ##

    @abstractmethod
    def execute_open_order(self, order: MarketOrder, last_close: float, curr_dt_str: str) -> None:
        pass

    @abstractmethod
    def execute_close_order(self, order: MarketOrder, last_close: float) -> None:
        pass


class LiveBroker:
    def __init__(self) -> None:
        api_key: str = ALPACA_SECRETS[1]["api_key"]
        secret_key: str = ALPACA_SECRETS[1]["secret_key"]
        self._data_stream: StockDataStream = StockDataStream(api_key, secret_key)
        self._trade_client: TradingClient = TradingClient(api_key, secret_key)
        self._stock_historical_data_client = StockHistoricalDataClient(
            api_key, secret_key, raw_data=False
        )
        self._portfolio: Portfolio = Portfolio()
        self.sync_portfolio()

    def sync_portfolio(self):
        # Sync w/ remote's available cash
        acct = self._trade_client.get_account()
        if not isinstance(acct, TradeAccount):
            raise TypeError(f"account was of type {type(acct)} instead of TradeAccount")

        cash: str | None = acct.cash
        if cash is None:
            raise ValueError("`account.cash: str | None` was None.")

        self._portfolio.cash = float(cash)

        # Sync w/ remote's open orders
        open_orders = self._trade_client.get_orders(filter=GetOrdersRequest(status=QueryOrderStatus.OPEN))
        if not isinstance(open_orders, list):
            raise TypeError(f"open_orders was of type {type(open_orders)} instead of list[Order]")

        orders = []
        for ord in open_orders:
            # TODO: Add more details here. alpaca differentiates between `Order` and `OrderRequest`
            #       My order class models the OrderRequest class rather than the `Order`
            d = {
                "symbol": ord.symbol,
                "side": OrderDir.LONG if ord.side == OrderSide.BUY else OrderDir.SHORT,
                "status": OrderState.FILLED if ord.status == OrderStatus.FILLED else OrderState.WORKING,
                "requested_qty": ord.qty,
                "purchase_dt": ord.filled_at,
                "purchase_qty": ord.filled_qty,
            }
            orders.append(TBOrder(**d))

        # Sync w/ remote's open positions
        open_positions = self._trade_client.get_all_positions()
        if not isinstance(open_positions, list):
            raise TypeError(f"open_position was of type {type(acct)} instead of list[Position]")

        positions: dict[str, Position] = {}
        for pos in open_positions:
            d = {
                "symbol": pos.symbol,
                "quantity": float(pos.qty),
                "price": pos.current_price,
                "side": pos.side,
            }
            positions[d["symbol"]] = Position(**d)

        self._portfolio.positions = positions

    @property
    def portfolio(self) -> Portfolio:
        return self._portfolio

    def get_market_status(self) -> dict:
        clock = self._trade_client.get_clock()

        if isinstance(clock, Clock):
            return {
                "is_open": clock.is_open,
                "next_open": clock.next_open,
                "next_close": clock.next_close
            }
        else:
            raise TypeError(f"`clock` was type `{type(clock)}` instead of `Clock`.")

    def execute_open_order(self, order: MarketOrder) -> None:
        tp = None
        sl = None
        if order.take_profit is not None:
            tp = TakeProfitRequest(limit_price=order.take_profit.tp_limit)
        if order.stop_loss is not None:
            sl = StopLossRequest(stop_price=order.stop_loss.sl_limit)

        req = MarketOrderRequest(
            symbol=order.symbol,
            qty=order.requested_qty,
            side=OrderSide.BUY if order.is_long() else OrderSide.SELL,
            type=OrderType.MARKET,
            time_in_force=TimeInForce.DAY,
            take_profit=tp,
            stop_loss=sl,
        )
        _ = self._trade_client.submit_order(req)

    def execute_close_order(self, order: MarketOrder, last_close: float) -> None:
        self._trade_client.close_position(
            order.symbol,
            close_options=ClosePositionRequest(qty=str(order.requested_qty))
        )

    # NOTE: this could take a while, depending the time range supplied
    def export_historical_candles(self,
        symbols: list[str], start: datetime, end: datetime = datetime.now()
    ) -> None:
        req = StockBarsRequest(
            symbol_or_symbols=symbols,
            timeframe=TimeFrame(amount=1, unit=TimeFrameUnit.Hour),
            start=start,
            end=end
        )

        df: pd.DataFrame = pd.DataFrame()
        try:
            bars: BarSet | RawData = self._stock_historical_data_client.get_stock_bars(req)
            if not isinstance(bars, BarSet):
                raise TypeError(f"Expected `bars` to be of type BarSet, got {type(bars)}")

            df = bars.df.copy()
        except Exception as e:
            print(e)

        # Reset index to make it a regular column
        df.reset_index(inplace=True)
        log.debug(f"{df.columns}")
        # Modify the timestamp column
        df["timestamp"] = df["timestamp"].apply(
            lambda x: datetime.fromisoformat(str(x)).astimezone(util.MY_TIMEZONE)
        )

        uniq_symbols: set[str] = set(df["symbol"])
        for symbol in uniq_symbols:
            # sf = Stockframe.from_csv(f"ohlcv-1hr/{symbol}.csv", symbol, mult=1, timespan=Timespan.HOUR)
            sliced_df = df[df["symbol"] == symbol].copy()
            sliced_df.drop("symbol", axis=1, inplace=True)
            # new_df = pd.concat([sf.df, sliced_df], ignore_index=True)
            del sliced_df["trade_count"]
            del sliced_df["vwap"]

            sliced_df.to_csv(f"trout/ohlcv-1hr/{symbol}.csv", index=False)

