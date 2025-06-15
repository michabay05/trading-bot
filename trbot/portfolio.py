from enum import Enum
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

class OrderStatus(Enum):
    FILLED = "filled"
    EXPIRED = "expired"
    WORKING = "working"


class Order:
    def __init__(self, symbol: str, order_type: OrderType, quantity: float, purchase_price: float,
        purchase_dt: str, status: OrderStatus = OrderStatus.WORKING
    ):
        self.symbol: str = symbol
        self.type: OrderType = order_type
        self.status: OrderStatus = status
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
            "quantity": self.quantity,
            "purchase_price": self.purchase_price,
            "purchase_dt": self.purchase_dt,
        }


class Portfolio:
    def __init__(self, initial_capital: float = 1000.0) -> None:
        self._initial_capital: float = initial_capital
        self._capital: float = self._initial_capital
        self._positions: dict[str, Position] = {}
        self._orders: list[Order] = []
        self._pl: float = 0.0
        self._capital_pct: float = 0.0

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
    def orders(self) -> list[Order]:
        return self._orders

    def add_order(self, order: Order) -> None:
        self._orders.append(order)

    def __repr__(self) -> str:
        return json.dumps(Portfolio.to_dict(self), indent=4)

    def save_to_json(self, filepath: str) -> None:
        with open(filepath, "w") as f:
            json.dump(self, f, indent=4, default=Portfolio.to_dict)

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

            ords: list[Order] = []
            for ord in root["orders"]:
                ords.append(Order(
                    symbol=ord["symbol"],
                    order_type=OrderType(ord["type"]),
                    status=OrderStatus(ord["status"]),
                    quantity=ord["quantity"],
                    purchase_price=ord["purchase_price"],
                    purchase_dt=ord["purchase_dt"]
                ))

        self._positions = psts
        self._orders = ords
        self.update_pl()

    @staticmethod
    def to_dict(pft: 'Portfolio') -> dict:
        return {
            "capital": pft.capital,
            "pl": pft.pl,
            "capital_pct": pft._capital_pct,
            "positions": {
                symbol: Position.to_dict(position)
                for symbol, position in pft.positions.items()
            },
            "orders": [ Order.to_dict(ord) for ord in pft.orders ]
        }

    def update_pl(self):
        pst_total: float = 0.0
        for pst in self.positions.values():
            pst_total += abs(pst.market_value())

        self._pl = (self._capital + pst_total) - self._initial_capital
        self._capital_pct = 100.0 * (self._capital / self._initial_capital)
