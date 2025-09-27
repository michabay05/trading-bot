from typing import Literal
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import json, os

from alpaca.trading.client import TradingClient
from alpaca.trading.enums import (
    OrderClass, OrderSide, OrderType, PDTCheck, TimeInForce
)
from alpaca.trading.models import AccountConfiguration, Clock, Order, TradeAccount
from alpaca.trading.requests import (
    ClosePositionRequest, MarketOrderRequest,
    StopLossRequest, TakeProfitRequest
)

from . import log, util
from .datafeed import TBDataFeed
from .portfolio import Portfolio, TBMarketReq, TBOrderReq, TBOrderStatus, Position


@dataclass
class DirectionLabel:
    direction: Literal["long", "short"]
    created_at: datetime


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
        self._time_til_reset: timedelta = timedelta(days=1)

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

    def export_info(self) -> None:
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
        with open(self._broker_info_path, "w") as f:
            json.dump(output, f, indent=4)

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
        if not self._order_aligns_w_dir(ord_req, "open"):
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
        else:
            ord_req.status = TBOrderStatus.INSUFF_FUNDS

        self.add_order_req(ord_req)

    def execute_close_order(self, ord_req: TBMarketReq, data_feed: TBDataFeed) -> None:
        if not self._order_aligns_w_dir(ord_req, "close"):
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

    def _dir_label_symbol(self, symbol: str, dir: Literal["long", "short"]) -> None:
        assert dir in ["long", "short"], f"Unknown direction label: {dir}"
        assert symbol in self._symbols, f"Symbol({symbol}) is not in symbol list({self._symbols})"

        self._symbol_labels[symbol] = DirectionLabel(dir, datetime.now())

    def _order_aligns_w_dir(self, ord_req: TBMarketReq, action: str) -> bool:
        # If symbol is not in the labels, then it does not have a label
        # associated with it
        if ord_req.symbol not in self._symbol_labels.keys():
            return True
        
        # If this is true, then order is going against the stock's daily
        # direction classification.
        dir = self._symbol_labels[ord_req.symbol].direction
        if (
            (dir == "long" and not ord_req.is_long()) or
            (dir == "short" and ord_req.is_long())
        ):
            # If this is true, then order is going against the stock's daily direction
            # classification.
            log.warn(
                f"DENIED: {ord_req.symbol} is going against its daily "
                "direction label (long or short)"
            )
            log.warn(f"Order is long?: {ord_req.is_long()}; action = {action}")
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
