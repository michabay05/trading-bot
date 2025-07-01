from enum import Enum
from dataclasses import dataclass, asdict, field
import json, os


class Position:
    def __init__(self, symbol: str, quantity: float, price: float) -> None:
        self.symbol: str = symbol
        self.quantity: float = quantity
        self.price: float = price

    def market_value(self) -> float:
        return self.quantity * self.price

    def close(self) -> None:
        pass

    @staticmethod
    def to_dict(pst: 'Position') -> dict:
        return {
            "quantity": pst.quantity,
            "price": pst.price,
        }


class OrderType(Enum):
    MARKET = "market"

class OrderSide(Enum):
    LONG = "long"
    SHORT = "short"

    def opposite(self) -> 'OrderSide':
        if self == OrderSide.LONG:
            return OrderSide.SHORT
        elif self == OrderSide.SHORT:
            return OrderSide.LONG
        else:
            raise ValueError(f"Unknown side: {self.value}")

class OrderStatus(Enum):
    FILLED = "filled"
    EXPIRED = "expired"
    WORKING = "working"

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

@dataclass
class _Order:
    symbol: str
    quantity: float
    side: OrderSide
    requested_price: float
    requested_dt: str
    intent: OrderIntent
    type: OrderType
    id: int = field(init=False)
    status: OrderStatus = OrderStatus.WORKING
    purchase_dt: str | None = None
    purchase_price: float | None = None
    take_profit: TakeProfitTrigger | None = None
    stop_loss: StopLossTrigger | None = None

    def __post_init__(self):
        global ORDER_ID_COUNTER
        # Use object.__setattr__ to bypass our custom __setattr__ during init
        # object.__setattr__(self, 'id', ORDER_ID_COUNTER)
        self.id = ORDER_ID_COUNTER
        ORDER_ID_COUNTER += 1
        # Flag used for partial immutability (used in __setattr__())
        self._initialized: bool = True

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
        return self.side == OrderSide.LONG

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
        return json.dumps(_Order.to_dict(self), indent=4)

    @staticmethod
    def to_dict(ord: '_Order') -> dict:
        d = asdict(ord)
        d["side"] = ord.side.value
        d["type"] = ord.type.value
        d["status"] = ord.status.value
        d["intent"] = ord.intent.value
        d["take_profit"] = TakeProfitTrigger.to_dict(ord.take_profit)
        d["stop_loss"] = StopLossTrigger.to_dict(ord.stop_loss)
        return d

@dataclass
class MarketOrder(_Order):
    type: OrderType = OrderType.MARKET


class Portfolio:
    def __init__(self, initial_capital: float = 1000.0) -> None:
        self._initial_capital: float = initial_capital
        self._capital: float = self._initial_capital
        self._positions: dict[str, Position] = {}
        self._orders: list[_Order] = []
        self._pl: float = 0.0
        self._capital_pct: float = 0.0

        self.update_pl()

    @property
    def pl(self) -> float:
        return self._pl

    @property
    def pl_pct(self) -> float:
        return self._capital_pct

    @property
    def capital(self) -> float:
        return self._capital

    @capital.setter
    def capital(self, value: float) -> None:
        self._capital = value

    @property
    def positions(self) -> dict[str, Position]:
        return self._positions

    @property
    def orders(self) -> list[_Order]:
        return self._orders

    def add_orders(self, order: _Order) -> None:
        self._orders.append(order)

    def __repr__(self) -> str:
        return json.dumps(Portfolio.to_dict(self), indent=4)

    def find_order_by_id(self, id: int) -> _Order | None:
        for ord in self._orders:
            if ord.id == id:
                return ord

        return None

    def save_to_json(self, filepath: str) -> None:
        with open(filepath, "w") as f:
            json.dump(Portfolio.to_dict(self), f, indent=4)

    def init_from_json(self, filepath: str) -> None:
        if not os.path.exists(filepath):
            print(f"[ERROR] Unable to find '{filepath}'")
            return

        with open(filepath, "r") as f:
            root = json.load(f)
            self._capital = float(root["capital"])
            psts: dict[str, Position] = {}
            for k, v in root["positions"].items():
                psts[k] = Position(
                    symbol=k,
                    quantity=float(v["quantity"]),
                    price=float(v["price"]),
                )

            ords: list[_Order] = []
            for ord in root["orders"]:
                ords.append(_Order(**ord))

        self._positions = psts
        self._orders = ords
        self.update_pl()

    @staticmethod
    def to_dict(pft: 'Portfolio') -> dict:
        return {
            "capital": pft.capital,
            "pl": pft.pl,
            "capital_pct": pft._capital_pct,
            "position_count": len(pft.positions),
            "orders_count": len(pft.orders),
            "positions": {
                symbol: Position.to_dict(position)
                for symbol, position in pft.positions.items()
            },
            "orders": [ _Order.to_dict(ord) for ord in pft.orders ]
        }

    def update_pl(self):
        pst_total: float = 0.0
        for pst in self.positions.values():
            pst_total += abs(pst.market_value())

        self._pl = (self._capital + pst_total) - self._initial_capital
        self._capital_pct = 100.0 * (self._capital / self._initial_capital)
