from enum import Enum


class Position:
    def __init__(self, timestamp: str, quantity: float, purchase_price: float) -> None:
        self.quantity: float = quantity
        self.purchase_price: float = purchase_price

    @staticmethod
    def to_dict(pst: 'Position') -> dict:
        return {
            "quantity": f"{pst.quantity:.2f}",
            "purchase_price": f"{pst.purchase_price:.2f}",
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
        self._captial: float = initial_capital
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
