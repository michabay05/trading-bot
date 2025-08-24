from typing import Literal
from datetime import datetime, timedelta
from uuid import UUID

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
    TBOrder, TBOrderAmountKind, Portfolio,
    TBMarketReq, TBOrderReq, TBOrderState, Position,
)


class LiveBroker:
    def __init__(self, acct_name: str, symbols: list[str], paper: bool = True) -> None:
        api_key, secret_key = util.alpaca_keys(acct_name)
        self._trade_client: TradingClient = TradingClient(
            api_key, secret_key, paper=paper, raw_data=False
        )

        # Set account configurations
        acct_config = self._trade_client.get_account_configurations()
        assert isinstance(acct_config, AccountConfiguration), f"acct_config is not of type AccountConfiguration; it is {type(acct_config)}"
        acct_config.fractional_trading = True
        acct_config.pdt_check = PDTCheck.BOTH
        self._trade_client.set_account_configurations(acct_config)

        self._req_history: list[TBOrderReq] = []
        self._portfolio: Portfolio = Portfolio()
        self.sync_portfolio()

        self._symbols: list[str] = symbols.copy()
        self._long_symbols: list[str] = []
        self._short_symbols: list[str] = []

        # If set to true, take profit and stop loss orders are sent to the
        # remote broker. When set to false, market orders are manually sent to
        # the local broker once the thresholds have been passed.
        self._auto_exit: bool = False

    def sync_portfolio(self):
        # Sync w/ remote's available cash
        acct = self._trade_client.get_account()
        if not isinstance(acct, TradeAccount):
            raise TypeError(f"account was of type {type(acct)} instead of TradeAccount")

        cash: str | None = acct.cash
        if cash is None:
            raise ValueError("`account.cash: str | None` was None.")

        new_pft: Portfolio = Portfolio(initial_capital=float(cash))

        # Sync w/ remote's open positions
        open_positions = self._trade_client.get_all_positions()
        if not isinstance(open_positions, list):
            raise TypeError(f"open_position was of type {type(acct)} instead of list[Position]")

        positions: dict[str, Position] = {}
        for pos in open_positions:
            d = {
                "symbol": pos.symbol,
                "quantity": float(pos.qty),
                "side": pos.side,
            }
            positions[d["symbol"]] = Position(**d)

        new_pft.replace_all_positions(positions)
        self._portfolio = new_pft

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

    def add_order_req(self, order: TBMarketReq) -> None:
        self._req_history.append(order)

    def check_exits(self, symbol: str, close_price: float) -> TBMarketReq | None:
        if self._auto_exit:
            return None

        for req in self._req_history:
            if req.completed or req.symbol != symbol:
                continue

            # If no (tp) and no (sl), then no additional follow up is needed
            if req.take_profit is None and req.stop_loss is None:
                req.completed = True
                continue

            # Handle take profit
            if req.take_profit is not None:
                if req.is_long():
                    tp_passed = close_price >= req.take_profit.tp_limit
                else:
                    tp_passed = close_price <= req.take_profit.tp_limit

                if tp_passed:
                    dt_str = str(datetime.now())
                    req.take_profit.purchase_price = close_price
                    req.take_profit.purchase_dt = dt_str
                    req.completed = True
                    return TBMarketReq(
                        symbol=symbol,
                        side=req.side.opposite(),
                        requested_qty=req.requested_qty,
                        requested_dt=dt_str,
                        intent=req.take_profit.intent
                    )

            # Handle stop loss
            if req.stop_loss is not None:
                if req.is_long():
                    sl_passed = close_price <= req.stop_loss.sl_limit
                else:
                    sl_passed = close_price >= req.stop_loss.sl_limit

                if sl_passed:
                    dt_str = str(datetime.now())
                    req.stop_loss.purchase_price = close_price
                    req.stop_loss.purchase_dt = dt_str
                    req.completed = True
                    return TBMarketReq(
                        symbol=symbol,
                        side=req.side.opposite(),
                        requested_qty=req.requested_qty,
                        requested_dt=dt_str,
                        intent=req.stop_loss.intent
                    )

    def execute_open_order(self, ord_req: TBMarketReq, data_feed: TBDataFeed) -> None:
        if (
            (ord_req.symbol in self._long_symbols and not ord_req.is_long()) or
            (ord_req.symbol in self._short_symbols and ord_req.is_long())
        ):
            # If this is true, then order is going against the stock's daily direction
            # classification.
            log.warn(f"DENIED: {ord_req.symbol} is going against its daily direction label (long or short)")
            return

        tp = None
        sl = None
        ord_class: OrderClass = OrderClass.SIMPLE
        if self._auto_exit:
            if ord_req.take_profit is not None:
                tp = TakeProfitRequest(limit_price=round(ord_req.take_profit.tp_limit, 2))
            if ord_req.stop_loss is not None:
                sl = StopLossRequest(stop_price=round(ord_req.stop_loss.sl_limit, 2))

            if tp is not None or sl is not None:
                ord_class: OrderClass = OrderClass.BRACKET

        latest_price_per_share: float = data_feed.get_latest_price(ord_req.symbol)
        order_value: float = ord_req.requested_qty.to_notional(latest_price_per_share)
        req = MarketOrderRequest(
            symbol=ord_req.symbol,
            notional=round(order_value, 2),
            side=OrderSide.BUY if ord_req.is_long() else OrderSide.SELL,
            type=OrderType.MARKET,
            time_in_force=TimeInForce.DAY,
            order_class=ord_class,
            take_profit=tp,
            stop_loss=sl,
        )

        if order_value <= self._portfolio.cash:
            submitted_order = self._trade_client.submit_order(req)
            self._dir_label_symbol(ord_req.symbol, "long" if ord_req.is_long() else "short")
            assert isinstance(submitted_order, Order), f"submitted_order is not of type Order; it is {type(submitted_order)}"
            if submitted_order.status == OrderStatus.FILLED:
                ord_req.status = TBOrderState.FILLED

            # self._portfolio.add_to_history(submitted_order)
        else:
            ord_req.status = TBOrderState.INSUFF_FUNDS

    def execute_close_order(self, ord_req: TBMarketReq, data_feed: TBDataFeed) -> None:
        latest_price = data_feed.get_latest_price(ord_req.symbol)
        submitted_order = self._trade_client.close_position(
            ord_req.symbol,
            close_options=ClosePositionRequest(
                qty=str(ord_req.requested_qty.to_shares(latest_price))
            )
        )
        assert isinstance(submitted_order, Order), f"submitted_order is not of type Order; it is {type(submitted_order)}"
        # self._portfolio.add_to_history(submitted_order)

    def _dir_label_symbol(self, symbol: str, dir: Literal["long", "short"]) -> None:
        assert dir in ["long", "short"], f"Unknown direction label: {dir}"
        assert symbol in self._symbols, f"Symbol({symbol}) is not in symbol list({self._symbols})"

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

    def _on_update_event(self, data: dict) -> None:
        # Source: https://docs.alpaca.markets/docs/websocket-streaming#common-events
        match data["event"]:
            case "fill":
                log.debug("Event: FILL")
                symbol = data["order"]["symbol"]
                id = data["order"]["id"]
                timestamp: datetime = datetime.fromisoformat(data["timestamp"])

                self._portfolio.positions[symbol].created_by = UUID(id)
                self._portfolio.positions[symbol].earliest_close = (
                    timestamp + timedelta(days=1)
                )
            case _:
                raise ValueError(f"Unknown update: {data['event']}")
