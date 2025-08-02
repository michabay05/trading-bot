from typing import Literal

from alpaca.trading.client import TradingClient
from alpaca.trading.enums import (
    OrderClass, OrderSide, OrderType, PDTCheck, QueryOrderStatus, TimeInForce, OrderStatus
)
from alpaca.trading.models import AccountConfiguration, Clock, Order, TradeAccount
from alpaca.trading.requests import (
    ClosePositionRequest, GetOrdersRequest, MarketOrderRequest,
    StopLossRequest, TakeProfitRequest
)

from . import log, util
from .datafeed import TBDataFeed
from .portfolio import (
    OrderIntent, TBOrderAmountKind, TBOrderDir, TBOrder, Portfolio, TBMarketOrder, TBOrderState, Position,
    TBOrderType
)


class LiveBroker:
    def __init__(self, acct_name: str, symbols: list[str], paper: bool = True) -> None:
        api_key, secret_key = util.alpaca_keys(acct_name)
        self._trade_client: TradingClient = TradingClient(api_key, secret_key, paper=paper)

        acct_config = self._trade_client.get_account_configurations()
        assert isinstance(acct_config, AccountConfiguration)
        acct_config.fractional_trading = True
        acct_config.pdt_check = PDTCheck.BOTH
        self._trade_client.set_account_configurations(acct_config)

        self._portfolio: Portfolio = Portfolio()
        self.sync_portfolio()

        self._symbols: list[str] = symbols.copy()
        self._long_symbols: list[str] = []
        self._short_symbols: list[str] = []

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
            tmp_dict = {
                "symbol": ord.symbol,
                "side": TBOrderDir.LONG if ord.side == OrderSide.BUY else TBOrderDir.SHORT,
                "requested_qty": ord.qty,
                "requested_dt": ord.created_at,
                "intent": OrderIntent(ord.position_intent),
                "type": TBOrderType(ord.order_type),
                "status": TBOrderState.FILLED if ord.status == OrderStatus.FILLED else TBOrderState.WORKING,
                "purchase_dt": ord.filled_at,
                "purchase_qty": ord.filled_qty,
            }
            orders.append(TBOrder(**tmp_dict))

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

    def execute_open_order(self, order: TBMarketOrder, data_feed: TBDataFeed) -> None:
        if (
            (order.symbol in self._long_symbols and not order.is_long()) or
            (order.symbol in self._short_symbols and order.is_long())
        ):
            # If this is true, then order is going against the stock's daily direction
            # classification.
            log.warn(f"{order.symbol} is going against its daily direction label (long or short)")
            return

        tp = None
        sl = None
        if order.take_profit is not None:
            tp = TakeProfitRequest(limit_price=round(order.take_profit.tp_limit, 2))
        if order.stop_loss is not None:
            sl = StopLossRequest(stop_price=round(order.stop_loss.sl_limit, 2))

        if tp is not None or sl is not None:
            ord_class: OrderClass = OrderClass.BRACKET
        else:
            ord_class: OrderClass = OrderClass.SIMPLE

        order_value: float = 0.0
        match order.requested_qty.kind:
            case TBOrderAmountKind.SHARES:
                order_value = order.requested_qty.amount * data_feed.get_latest_price(order.symbol)
            case TBOrderAmountKind.NOTIONAL:
                order_value = order.requested_qty.amount
            case TBOrderAmountKind.CASH_PCT:
                order_value = self._portfolio.cash * order.requested_qty.amount

        req = MarketOrderRequest(
            symbol=order.symbol,
            notional=order.requested_qty,
            side=OrderSide.BUY if order.is_long() else OrderSide.SELL,
            type=OrderType.MARKET,
            time_in_force=TimeInForce.DAY,
            order_class=ord_class,
            take_profit=tp,
            stop_loss=sl,
        )

        if order_value <= self._portfolio.cash:
            submitted_order = self._trade_client.submit_order(req)
            self._dir_label_symbol(order.symbol, "long" if order.is_long() else "short")
            assert isinstance(submitted_order, Order)
            if submitted_order.status == OrderStatus.FILLED:
                order.status = TBOrderState.FILLED
        else:
            order.status = TBOrderState.INSUFF_FUNDS

        self._portfolio.add_orders(order)

    def execute_close_order(self, order: TBMarketOrder) -> None:
        self._trade_client.close_position(
            order.symbol,
            close_options=ClosePositionRequest(qty=str(order.requested_qty))
        )
        self._portfolio.add_orders(order)

    def _dir_label_symbol(self, symbol: str, dir: Literal["long", "short"]) -> None:
        assert dir in ["long", "short"]
        assert symbol in self._symbols

        self._symbols.remove(symbol)
        match dir:
            case "long":
                self._long_symbols.append(symbol)
            case "short":
                self._short_symbols.append(symbol)
            case _:
                raise ValueError(f"Unknown direction label for '{symbol}'")

    def reset_symbols(self, symbols: list[str]) -> None:
        self._symbols = symbols.copy()
        self._long_symbols.clear()
        self._short_symbols.clear()
