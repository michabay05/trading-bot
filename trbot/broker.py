from typing import Literal
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import json, os

from alpaca.trading.client import TradingClient
from alpaca.trading.enums import (
    OrderClass, OrderSide, OrderType, PDTCheck, TimeInForce,
    OrderStatus
)
from alpaca.trading.models import AccountConfiguration, Clock, Order, TradeAccount
from alpaca.trading.requests import (
    ClosePositionRequest, MarketOrderRequest,
    StopLossRequest, TakeProfitRequest
)

from . import log, util
from .datafeed import TBDataFeed
from .portfolio import Portfolio, TBMarketReq, TBOrderDir, TBOrderReq, TBOrderStatus, Position


@dataclass
class DirectionLabel:
    direction: Literal["long", "short"]
    created_at: datetime


class LiveBroker:
    def __init__(self, acct_name: str, symbols: list[str], paper: bool = True) -> None:
        self._acct_name = acct_name
        api_key, secret_key = util.alpaca_keys(self._acct_name)
        self._trade_client: TradingClient = TradingClient(
            api_key, secret_key, paper=paper, raw_data=False
        )

        # Set account configurations
        acct_config = {
            "fractional_trading": True,
            "no_shorting": False,
        }

        alpaca_acct_config = self._trade_client.get_account_configurations()
        assert isinstance(alpaca_acct_config, AccountConfiguration), f"acct_config is not of type AccountConfiguration; it is {type(alpaca_acct_config)}"
        alpaca_acct_config.fractional_trading = acct_config["fractional_trading"]
        alpaca_acct_config.no_shorting = acct_config["no_shorting"]
        alpaca_acct_config.pdt_check = PDTCheck.BOTH
        self._trade_client.set_account_configurations(alpaca_acct_config)

        self._req_history: list[TBOrderReq] = []
        self._portfolio: Portfolio = Portfolio()
        self.sync_portfolio()

        self._all_symbols: set[str] = set(symbols)
        self._symbols: set[str] = self._all_symbols.copy()
        self._symbol_labels: dict[str, DirectionLabel] = {}

        # If set to true, take profit and stop loss orders are sent to the
        # remote broker. When set to false, market orders are manually sent to
        # the local broker once the thresholds have been passed.
        self._auto_exit: bool = False

        # This dictates how long a symbol has to wait before being removed from
        # the direction label and re-added into the symbols list. Once a symbol
        # with no direction is either long or short, it will take
        # `self.time_til_reset` until it loses its label
        self._time_til_reset: datetime = datetime.now() + timedelta(days=1)

        self._broker_info_path: str = "broker_info.json"
        try:
            self.import_info()
        except json.JSONDecodeError:
            log.warn(f"Invalid broker info JSON found @ '{self._broker_info_path}'")

    def sync_portfolio(self):
        # Sync w/ remote's available cash
        acct = self._trade_client.get_account()
        if not isinstance(acct, TradeAccount):
            raise TypeError(f"account was of type {type(acct)} instead of TradeAccount")

        cash_str: str | None = acct.cash
        assert cash_str is not None, f"`account.cash: str | None` was None."
        cash = float(cash_str)
        assert cash > 0, f"account.cash(as_str: {cash_str}, as_float: {cash}) > $0.00"
        new_pft: Portfolio = Portfolio(initial_capital=cash)

        # Sync w/ remote's open positions
        open_positions = self._trade_client.get_all_positions()
        if not isinstance(open_positions, list):
            raise TypeError(f"open_position was of type {type(acct)} instead of list[Position]")

        positions: dict[str, Position] = {}
        for pos in open_positions:
            # Convert from `str | None` to `float | None`
            unrealized_pl = float(pos.unrealized_pl) if pos.unrealized_pl is not None else pos.unrealized_pl
            unrealized_plpc = float(pos.unrealized_plpc) if pos.unrealized_plpc is not None else pos.unrealized_plpc
            market_value = float(pos.market_value) if pos.market_value is not None else pos.market_value

            syncd_pos = Position(
                symbol=pos.symbol,
                quantity=float(pos.qty),
                side=TBOrderDir.from_alpaca(pos.side),
                alpaca_id=pos.asset_id,
                unrealized_pl=unrealized_pl,
                unrealized_plpc=unrealized_plpc,
                market_value=market_value
            )
            positions[syncd_pos.symbol] = syncd_pos

        new_pft.replace_all_positions(positions)
        self._portfolio = new_pft

    def import_info(self) -> None:
        if not os.path.exists(self._broker_info_path):
            log.warn(f"No broker information found at '{self._broker_info_path}'")
            return

        with open(self._broker_info_path, "r") as f:
            content = json.load(f)

        self._symbol_labels.clear()
        for symbol, lbl in content["symbol_labels"].items():
            self._symbol_labels[symbol] = DirectionLabel(**lbl)

        self._req_history.clear()
        for req in content["requests"]:
            self._req_history.append(TBOrderReq(**req))

    def export_info(self, out_dir: str) -> None:
        # This function exists purely to resolve the following issue:
        # When the program runs and executes trades, it comes up with certain
        # take profits and stop losses. However, when the program stops, then
        # it "forgets" the previously assigned take profit and stop loss thresholds
        # Exporting this information to a json file then reading them in on startup
        # should resolve this issue
        #
        # In addition, doing this method also allows for the direction labels to persist
        # across restarts.

        requests: list[dict] = []
        for req in self._req_history:
            requests.append(TBOrderReq.to_dict(req))

        symbol_labels: dict[str, dict] = {}
        for symbol, label in self._symbol_labels.items():
            symbol_labels[symbol] = asdict(label)

        output: dict = {
            "symbol_labels": symbol_labels,
            "requests": requests
        }
        with open(f"{out_dir}/{self._broker_info_path}", "w") as f:
            json.dump(output, f, indent=4)

        self._portfolio.save_as_json(f"{out_dir}/portfolio.json")

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

    def check_if_labels_should_reset(self, symbol) -> None:
        now = datetime.now()
        if symbol not in self._symbol_labels.keys():
            return

        label = self._symbol_labels[symbol]
        if now - label.created_at > self._time_til_reset:
            # Label can now be reset
            self._symbols.add(symbol)
            del self._symbol_labels[symbol]

    def update_status(self) -> None:
        # This method is intended to do the following:
        #   - Update the status of an order (WORKING, FILL, CANCELED, etc)
        #   - Update the `earliest_close` of all positions, as necessary

        for req in self._req_history:
            if req.status != TBOrderStatus.WORKING or req.stop_checking:
                # This method is only intested in orders with a status of WORKING
                continue

            if req.alpaca_id is None:
                log.warn(
                    f"Could not update the status of the order.\n{TBOrderReq.to_dict(req)}"
                )
                req.stop_checking = True
                continue

            remote_order = self._trade_client.get_order_by_id(req.alpaca_id)
            assert isinstance(remote_order, Order)
            if remote_order.status == OrderStatus.FILLED:
                req.status = TBOrderStatus.FILLED

                if (
                    remote_order.filled_qty is not None and
                    remote_order.filled_at is not None and
                    remote_order.filled_avg_price is not None
                ):
                    req.filled_qty = float(remote_order.filled_qty)
                    req.filled_dt = remote_order.filled_at
                    # Assign a label only after the order is filled
                    self._dir_label_symbol(req.symbol, "long" if req.is_long() else "short")

                    # Subtract the value of the order from the porfolio's cash
                    self._portfolio.cash -= float(remote_order.filled_avg_price) * float(remote_order.filled_qty)

                    # Calculate the earliest possible time where the position for this
                    # specific symbol is allowed (Only here to align with PDT rules)
                    self._portfolio.set_earliest_close(req.symbol, req.filled_dt)
                else:
                    log.error(f"Failed to update the status of order {{ id: {remote_order.id} }}")

        # Update the `earliest_close` attribute
        now = datetime.now()
        for symbol in self._portfolio.positions.keys():
            pos = self._portfolio.positions[symbol]
            if pos.earliest_close is not None and now >= pos.earliest_close:
                self._portfolio.set_earliest_close(symbol, None)
                self._dir_label_symbol(symbol, "none")

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
        if not self._order_aligns_w_dir(ord_req):
            # If this is true, then order is going against the stock's daily direction
            # classification.
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

        # Is requested order in our budget?
        if order_value <= self._portfolio.cash:
            submitted_order = self._trade_client.submit_order(req)
            assert isinstance(submitted_order, Order), f"submitted_order is not of type Order; it is {type(submitted_order)}"

            ord_req.alpaca_id = submitted_order.id
            # self._portfolio.add_to_history(submitted_order)
            self.add_order_req(ord_req)
        else:
            ord_req.status = TBOrderStatus.INSUFF_FUNDS
            log.warn(f"DENIED: Order not sent due to insufficient funds (req_val: {order_value} vs own_val: {self._portfolio.cash})")


    def execute_close_order(self, ord_req: TBMarketReq, data_feed: TBDataFeed) -> None:
        if not self._order_aligns_w_dir(ord_req):
            # If this is true, then order is going against the stock's daily direction
            # classification.
            return

        latest_price = data_feed.get_latest_price(ord_req.symbol)
        submitted_order = self._trade_client.close_position(
            ord_req.symbol,
            close_options=ClosePositionRequest(
                qty=str(ord_req.requested_qty.to_shares(latest_price))
            )
        )
        assert isinstance(submitted_order, Order), f"submitted_order is not of type Order; it is {type(submitted_order)}"
        # self._portfolio.add_to_history(submitted_order)

    def _dir_label_symbol(self, symbol: str, dir: Literal["long", "short", "none"]) -> None:
        assert dir in ["long", "short"], f"Unknown direction label: {dir}"
        assert symbol in self._symbols, f"Symbol({symbol}) is not in symbol list({self._symbols})"

        if dir == "none":
            del self._symbol_labels[symbol]
        else:
            self._symbol_labels[symbol] = DirectionLabel(dir, datetime.now())

    def _order_aligns_w_dir(self, ord_req: TBMarketReq) -> bool:
        # If symbol is not in the labels, then it does not have a label
        # associated with it
        if ord_req.symbol not in self._symbol_labels.keys():
            return True

        # If this is true, then order is going against the stock's daily
        # direction classification.
        direction = self._symbol_labels[ord_req.symbol].direction
        if (
            (direction == "long" and not ord_req.is_long()) or
            (direction == "short" and ord_req.is_long())
        ):
            # If this is true, then order is going against the stock's daily direction
            # classification.
            log.warn(
                f"DENIED: {ord_req.symbol} is going against its daily "
                f"direction label (WMT's direction: {direction}) && "
                f"Order is to close?: {ord_req.is_to_close()}"
            )

            return False

        return True

    def new_fill_event(self, ord_dict: dict) -> None:
        order = Order(**ord_dict)

        # Find order with matching alpaca order id
        for ord_req in self._req_history:
            if ord_req.alpaca_id == order.id:
                # Found order
                ord_req.status = TBOrderStatus.FILLED
                return
