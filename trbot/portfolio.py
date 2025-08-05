from enum import Enum
from dataclasses import asdict, dataclass, field
from datetime import datetime
import enum
import json, os
from uuid import UUID


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


class OrderIntent(Enum):
    BUY_TO_OPEN = "buy_to_open"
    SELL_TO_OPEN = "sell_to_open"
    BUY_TO_CLOSE = "buy_to_close"
    SELL_TO_CLOSE = "sell_to_close"

    def opp_close(self) -> 'OrderIntent':
        if self == OrderIntent.BUY_TO_OPEN:
            return OrderIntent.SELL_TO_CLOSE
        elif self == OrderIntent.SELL_TO_OPEN:
            return OrderIntent.BUY_TO_CLOSE
        else:
            raise ValueError(f"There is no opposite close for {self.value}")


@dataclass
class TakeProfitTrigger:
    intent: OrderIntent
    tp_limit: float
    purchase_price: float | None = None
    purchase_dt: str | None = None

    @staticmethod
    def to_dict(tpr: 'TakeProfitTrigger | None') -> dict:
        if tpr is not None:
            d = asdict(tpr)
            d["intent"] = tpr.intent.value
            return d
        else:
            return {}


@dataclass
class StopLossTrigger:
    intent: OrderIntent
    sl_limit: float
    purchase_price: float | None = None
    purchase_dt: str | None = None

    @staticmethod
    def to_dict(slr: 'StopLossTrigger | None') -> dict:
        if slr is not None:
            d = asdict(slr)
            d["intent"] = slr.intent.value
            return d
        else:
            return {}


ORDER_ID_COUNTER: int = 0

class TBOrderAmountKind(enum.Enum):
    # Absolute: amount of shares to buy
    SHARES = "shares"
    # Absolute: amount of shares to buy in dollars
    NOTIONAL = "notional"
    # Relative: Percentage of available cash in account
    CASH_PCT = "percentage"

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
    def cash_pct(cls, pct: float) -> "TBOrderAmount":
        assert 0 < pct < 1, f"Cash percentage error: 0.0 < {pct} < 1.0"
        return cls(pct, TBOrderAmountKind.CASH_PCT)

    @property
    def amount(self) -> float:
        return self._amount

    @property
    def kind(self) -> TBOrderAmountKind:
        return self._kind


@dataclass
class TBOrder:
    symbol: str
    side: TBOrderDir
    requested_qty: TBOrderAmount
    requested_dt: str
    intent: OrderIntent
    type: TBOrderType
    id: int = field(init=False)
    status: TBOrderState = TBOrderState.WORKING
    filled_qty: float | None = None
    filled_dt: str | None = None
    take_profit: TakeProfitTrigger | None = None
    stop_loss: StopLossTrigger | None = None

    def __setattr__(self, name: str, value) -> None:
        if not getattr(self, "_initialized", False):
            super().__setattr__(name, value)
            return

        # After initialization, enforce immutability
        mutable_fields = [
            "status", "take_profit", "stop_loss", "purchase_dt", "purchase_price"
        ]

        if name not in mutable_fields and name != '_initialized':
            raise AttributeError(f"Cannot modify immutable attribute: '{name}'")

        super().__setattr__(name, value)

    def is_long(self) -> bool:
        return self.side == TBOrderDir.LONG

    def is_to_open(self) -> bool:
        return (
            self.intent == OrderIntent.BUY_TO_OPEN or
            self.intent == OrderIntent.SELL_TO_OPEN
        )

    def is_to_close(self) -> bool:
        return (
            self.intent == OrderIntent.BUY_TO_CLOSE or
            self.intent == OrderIntent.SELL_TO_CLOSE
        )

    def __repr__(self) -> str:
        return json.dumps(TBOrder.to_dict(self), indent=4)

    @staticmethod
    def to_dict(ord: 'TBOrder') -> dict:
        d = asdict(ord)
        d["side"] = ord.side.value
        d["type"] = ord.type.value
        d["status"] = ord.status.value
        d["intent"] = ord.intent.value
        d["take_profit"] = TakeProfitTrigger.to_dict(ord.take_profit)
        d["stop_loss"] = StopLossTrigger.to_dict(ord.stop_loss)
        return d

@dataclass
class TBMarketOrder(TBOrder):
    type: TBOrderType = TBOrderType.MARKET


class Portfolio:
    def __init__(self, initial_capital: float = 1000.0) -> None:
        self._initial_capital: float = initial_capital
        self._cash: float = self._initial_capital
        # Stores currently open positions
        self._positions: dict[str, Position] = {}
        self._orders: list[TBOrder] = []
        self._pl: float = 0.0
        self._capital_pct: float = 0.0

    @property
    def pl(self) -> float:
        return self._pl

    @property
    def pl_pct(self) -> float:
        return self._capital_pct

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

    @property
    def orders(self) -> list[TBOrder]:
        return self._orders

    def add_orders(self, order: TBOrder) -> None:
        self._orders.append(order)

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
        self._orders = ords

    @staticmethod
    def to_dict(pft: 'Portfolio') -> dict:
        return {
            "capital": pft.cash,
            "pl": pft.pl,
            "capital_pct": pft._capital_pct,
            "position_count": len(pft.positions),
            "orders_count": len(pft.orders),
            "positions": {
                symbol: Position.to_dict(position)
                for symbol, position in pft.positions.items()
            },
            "orders": [ TBOrder.to_dict(ord) for ord in pft.orders ]
        }
