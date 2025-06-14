from enum import Enum
import json, os


class Position:
    def __init__(self, quantity: float, price: float) -> None:
        self.quantity: float = quantity
        self.price: float = price

    def market_value(self) -> float:
        return self.quantity * self.price

    @staticmethod
    def to_dict(pst: 'Position') -> dict:
        return {
            "quantity": f"{pst.quantity:.2f}",
            "price": f"{pst.price:.2f}",
        }


class OrderType(Enum):
    MARKET = "market"

class OrderStatus(Enum):
    CANCELLED = "cancelled"
    FILLED = "filled"
    EXPIRED = "expired"
    WORKING = "working"


class Order:
    def __init__(self, symbol: str, order_type: OrderType, quantity: float, purchase_price: float,
        purchase_dt: str
    ):
        self.symbol: str = symbol
        self.type: OrderType = order_type
        self.status: OrderStatus = OrderStatus.WORKING
        self.quantity: float = quantity
        self.purchase_price: float = purchase_price
        self.purchase_dt: str = purchase_dt

    def __repr__(self) -> str:
        return (
            f"Order {{\n"
            f"    symbol: {self.symbol}\n"
            f"    type: {self.type.value}\n"
            f"    status: {self.status.value}\n"
            f"    quantity: {self.quantity}\n"
            f"    purchase_price: {self.purchase_price}\n"
            f"    purchase_dt: {self.purchase_dt}\n"
            f"}}"
        )

    def value(self) -> float:
        return self.quantity * self.purchase_price

    def abs_value(self) -> float:
        return abs(self.value())

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "type": self.type.value,
            "status": self.status.value,
            "quantity": f"{self.quantity:.2f}",
            "purchase_price": f"{self.purchase_price:.2f}",
            "purchase_dt": self.purchase_dt,
        }


class Portfolio:
    def __init__(self, initial_capital: float = 1000.0) -> None:
        self._capital: float = initial_capital
        self._positions: dict[str, Position] = {}
        self._orders: list[Order] = []

    @property
    def capital(self) -> float:
        return self._capital

    @capital.setter
    def capital(self, value: float) -> None:
        self._capital = value

    @property
    def positions(self) -> dict[str, Position]:
        return self._positions

    @positions.setter
    def positions(self, value: dict[str, Position]) -> None:
        self._positions = value

    @property
    def orders(self) -> list[Order]:
        return self._orders

    def add_order(self, order: Order) -> None:
        self._orders.append(order)

    def __repr__(self) -> str:
        return json.dumps(Portfolio.to_dict(self), indent=4)

    @staticmethod
    def to_dict(pft: 'Portfolio') -> dict:
        return {
            "capital": f"{pft.capital:.2f}",
            "positions": {
                symbol: Position.to_dict(position)
                for symbol, position in pft.positions.items()
            },
            "orders": [ Order.to_dict(ord) for ord in pft.orders ]
        }

    def save_to_json(self, filepath: str) -> None:
        with open(filepath, "w") as f:
            json.dump(self, f, indent=4, default=Portfolio.to_dict)

    def _init_from_json(self, filepath: str) -> None:
        if not os.path.exists(filepath):
            print(f"[ERROR] Unable to find '{filepath}'")
            return

        with open(filepath, "r") as f:
            root = json.load(f)
            self.capital = float(root["capital"])
            psts: dict[str, Position] = {}
            for k, v in root["positions"].items():
                pos = Position(
                    quantity=float(v["quantity"]),
                    price=float(v["purchase_price"]),
                )
                psts[k] = pos

        self.positions = psts
