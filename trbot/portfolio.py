from enum import Enum
from dataclasses import asdict, dataclass
from datetime import datetime
import enum
import json, os
from uuid import UUID

from alpaca.trading.enums import OrderSide, OrderStatus, OrderType, PositionIntent
from alpaca.trading.models import Order


class TBOrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"

class TBOrderDir(Enum):
    LONG = "long"
    SHORT = "short"

    def opposite(self) -> 'TBOrderDir':
        if self == TBOrderDir.LONG:
            return TBOrderDir.SHORT
        elif self == TBOrderDir.SHORT:
            return TBOrderDir.LONG
        else:
            raise ValueError(f"Unknown side: {self.value}")


class TBOrderState(Enum):
    FILLED = "filled"
    WORKING = "working"
    INSUFF_FUNDS = "insufficient funds"


@dataclass
class Position:
    symbol: str
    quantity: float
    side: TBOrderDir
    created_by: UUID | None = None
    # @PDT: the earliest possible time to close a position
    earliest_close: datetime | None = None

    def close(self) -> None:
        pass

    def to_dict(self) -> dict:
        d = asdict(self)
        d["side"] = self.side.value
        return d


class TBIntent(Enum):
    BUY_TO_OPEN = "buy_to_open"
    SELL_TO_OPEN = "sell_to_open"
    BUY_TO_CLOSE = "buy_to_close"
    SELL_TO_CLOSE = "sell_to_close"

    def opp_close(self) -> 'TBIntent':
        if self == TBIntent.BUY_TO_OPEN:
            return TBIntent.SELL_TO_CLOSE
        elif self == TBIntent.SELL_TO_OPEN:
            return TBIntent.BUY_TO_CLOSE
        else:
            raise ValueError(f"There is no opposite close for {self.value}")

    @staticmethod
    def from_alpaca(ord_type: PositionIntent) -> 'TBIntent':
        match ord_type:
            case PositionIntent.BUY_TO_OPEN:
                return TBIntent.BUY_TO_OPEN
            case PositionIntent.BUY_TO_CLOSE:
                return TBIntent.BUY_TO_CLOSE
            case PositionIntent.SELL_TO_OPEN:
                return TBIntent.SELL_TO_OPEN
            case PositionIntent.SELL_TO_CLOSE:
                return TBIntent.SELL_TO_CLOSE


@dataclass
class TakeProfitTrigger:
    intent: TBIntent
    tp_limit: float
    purchase_price: float | None = None
    purchase_dt: str | None = None

    @staticmethod
    def to_dict(tpr: 'TakeProfitTrigger | None') -> dict:
        if tpr is not None:
            return {
                "intent": tpr.intent,
                "tp_limit": tpr.tp_limit,
                "purchase_price": tpr.purchase_dt,
                "purchase_dt": tpr.purchase_dt
            }
        else:
            return {}


@dataclass
class StopLossTrigger:
    intent: TBIntent
    sl_limit: float
    purchase_price: float | None = None
    purchase_dt: str | None = None

    @staticmethod
    def to_dict(slr: 'StopLossTrigger | None') -> dict:
        if slr is not None:
            return {
                "intent": slr.intent,
                "sl_limit": slr.sl_limit,
                "purchase_price": slr.purchase_price,
                "purchase_dt": slr.purchase_dt
            }
        else:
            return {}


class TBOrderAmountKind(enum.Enum):
    # Absolute: amount of shares to buy
    SHARES = "shares"
    # Absolute: amount of shares to buy in dollars
    NOTIONAL = "notional"

class TBOrderAmount:
    # NOTE: Do not use `__init__()` directly. Use the other class methods
    def __init__(self, amount: float, kind: TBOrderAmountKind) -> None:
        self._amount: float = amount
        self._kind: TBOrderAmountKind = kind

    @classmethod
    def shares(cls, shares: float) -> "TBOrderAmount":
        assert 0.0 < shares, f"Share error: 0.0 shares < {shares} shares"
        return cls(shares, TBOrderAmountKind.SHARES)

    @classmethod
    def notional(cls, notional: float) -> "TBOrderAmount":
        assert 0.0 < notional, f"Notional error: $0.0 < ${notional}"
        return cls(notional, TBOrderAmountKind.NOTIONAL)

    @classmethod
    def cash_pct(cls, pct: float, avaiable_cash: float) -> "TBOrderAmount":
        assert 0 < pct < 1, f"Cash percentage error: 0.0 < {pct} < 1.0"
        assert 0 < avaiable_cash, f"Amount of avaiable cash: 0.0 < {avaiable_cash}"
        return cls(pct * avaiable_cash, TBOrderAmountKind.NOTIONAL)

    @property
    def amount(self) -> float:
        return self._amount

    @property
    def kind(self) -> TBOrderAmountKind:
        return self._kind

    def to_shares(self, latest_price_per_share: float) -> float:
        match self._kind:
            case TBOrderAmountKind.SHARES:
                return self.amount
            case TBOrderAmountKind.NOTIONAL:
                return self.amount / latest_price_per_share

    def to_notional(self, latest_price_per_share: float) -> float:
        match self._kind:
            case TBOrderAmountKind.SHARES:
                return self.amount * latest_price_per_share
            case TBOrderAmountKind.NOTIONAL:
                return self.amount

    @staticmethod
    def to_dict(ord_amount: 'TBOrderAmount') -> dict:
        return {
            "amount": ord_amount.amount,
            "kind": ord_amount.kind
        }


# =============================================================================
#             --- Distinction between TBOrderReq and TBOrder ---
# TBOrderReq is meant to be used by LiveBroker to keep track of all the order
# requests that have been sent by the bot. LiveBroker will also keep a list of
# all "TBOrderReq"s initiated by the bot.
#
# On other hand, TBOrder is meant to be used by Portfolio to keep track of all
# orders that have already been submitted to the remote broker. Portfolio will
# also keep a list of "TBOrder"s.
#
# Simply put,
#   >> list[TBOrderReq] -> Broker && list[TBOrder] -> Portfolio
#   >> request (TBOrderReq) vs actual instance of the order (TBOrder)
# =============================================================================

@dataclass
class TBOrderReq:
    symbol: str
    side: TBOrderDir
    requested_qty: TBOrderAmount
    requested_dt: str
    intent: TBIntent
    type: TBOrderType
    status: TBOrderState = TBOrderState.WORKING
    filled_qty: float | None = None
    filled_dt: str | None = None
    take_profit: TakeProfitTrigger | None = None
    stop_loss: StopLossTrigger | None = None
    completed: bool = False

    def is_long(self) -> bool:
        return self.side == TBOrderDir.LONG

    def is_to_open(self) -> bool:
        return (
            self.intent == TBIntent.BUY_TO_OPEN or
            self.intent == TBIntent.SELL_TO_OPEN
        )

    def is_to_close(self) -> bool:
        return (
            self.intent == TBIntent.BUY_TO_CLOSE or
            self.intent == TBIntent.SELL_TO_CLOSE
        )

    def __repr__(self) -> str:
        return json.dumps(TBOrderReq.to_dict(self), indent=4)

    @staticmethod
    def to_dict(ord: 'TBOrderReq') -> dict:
        d = asdict(ord)
        d["side"] = ord.side.value
        d["requested_qty"] = TBOrderAmount.to_dict(ord.requested_qty)
        d["intent"] = ord.intent.value
        d["type"] = ord.type.value
        d["status"] = ord.status.value
        d["take_profit"] = TakeProfitTrigger.to_dict(ord.take_profit)
        d["stop_loss"] = StopLossTrigger.to_dict(ord.stop_loss)
        return d

@dataclass
class TBMarketReq(TBOrderReq):
    type: TBOrderType = TBOrderType.MARKET


@dataclass
class TBOrder:
    filled_at: datetime
    symbol: str
    filled_qty: float
    type: TBOrderType
    side: TBOrderDir
    amount: TBOrderAmount
    intent: TBIntent
    status: TBOrderState

    @classmethod
    def from_alpaca(cls, order: Order) -> 'TBOrder':
        assert order.filled_at is not None
        assert order.symbol is not None
        assert order.filled_qty is not None
        assert order.type is not None
        assert order.side is not None

        match order.type:
            case OrderType.MARKET:
                ord_type = TBOrderType.MARKET
            case _:
                raise ValueError(f"Unknown order type: {order.type}")

        match order.side:
            case OrderSide.BUY:
                ord_dir = TBOrderDir.LONG
            case OrderSide.SELL:
                ord_dir = TBOrderDir.SHORT
            case _:
                raise ValueError(f"Unknown order side: {order.side}")

        if order.qty is not None:
            amount = TBOrderAmount.shares(float(order.qty))
        else:
            assert order.notional is not None
            amount = TBOrderAmount.shares(float(order.notional))


        assert order.position_intent is not None
        intent = TBIntent.from_alpaca(order.position_intent)
        assert order.status == OrderStatus.FILLED

        return cls(
            filled_at=order.filled_at,
            symbol=order.symbol,
            filled_qty=float(order.filled_qty),
            type=ord_type,
            side=ord_dir,
            amount=amount,
            intent=intent,
            status=TBOrderState.FILLED
        )

    @staticmethod
    def to_dict(ord: 'TBOrder') -> dict:
        d = asdict(ord)
        d["filled_at"] = str(ord.filled_at)
        d["type"] = ord.type.value
        d["side"] = ord.side.value
        d["amount"] = TBOrderAmount.to_dict(ord.amount)
        d["intent"] = ord.intent.value
        d["status"] = ord.status.value
        return d


class Portfolio:
    def __init__(self, initial_capital: float = 1000.0) -> None:
        self._initial_capital: float = initial_capital
        self._cash: float = self._initial_capital
        # Stores currently open positions
        self._positions: dict[str, Position] = {}
        # Contains a record of all the orders that have been submitted to the broker
        self._history: list[TBOrder] = []

    @property
    def cash(self) -> float:
        return self._cash

    @cash.setter
    def cash(self, value: float) -> None:
        self._cash = value

    @property
    def positions(self) -> dict[str, Position]:
        return self._positions

    def replace_all_positions(self, new_positions: dict[str, Position]) -> None:
        self._positions = new_positions

    def update_history(self, new_history: list[TBOrder]) -> None:
        self._history = new_history

    def add_to_history(self, order: Order) -> None:
        self._history.append(TBOrder.from_alpaca(order))

    def __repr__(self) -> str:
        return json.dumps(Portfolio.to_dict(self), indent=4)

    def save_to_json(self, filepath: str) -> None:
        with open(filepath, "w") as f:
            json.dump(Portfolio.to_dict(self), f, indent=4)

    def init_from_json(self, filepath: str) -> None:
        if not os.path.exists(filepath):
            print(f"[ERROR] Unable to find '{filepath}'")
            return

        with open(filepath, "r") as f:
            root = json.load(f)
            self._cash = float(root["capital"])
            psts: dict[str, Position] = {}
            for k, v in root["positions"].items():
                psts[k] = Position(**v)

            ords: list[TBOrder] = []
            for ord in root["orders"]:
                ords.append(TBOrder(**ord))

        self._positions = psts
        self._history = ords

    @staticmethod
    def to_dict(pft: 'Portfolio') -> dict:
        return {
            "capital": pft.cash,
            "position_count": len(pft.positions),
            "orders_count": len(pft._history),
            "positions": {
                symbol: Position.to_dict(position)
                for symbol, position in pft.positions.items()
            },
            "order_history": [ TBOrder.to_dict(ord) for ord in pft._history ]
        }
