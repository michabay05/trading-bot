from enum import Enum


class AssetType(Enum):
    EQUITY = "equity"

class Position:
    def __init__(self, symbol: str, timestamp: str, quantity: float, purchase_price: float,
        asset_type: AssetType = AssetType.EQUITY
    ) -> None:
        self.symbol: str = symbol
        self.timestamp: str = timestamp
        self.quantity: float = quantity
        self.purchase_price: float = purchase_price
        self.asset_type: AssetType = asset_type


class OrderType(Enum):
    MARKET = "market"

class OrderSide(Enum):
    LONG = "long"
    SHORT = "short"

class OrderStatus(Enum):
    CANCELLED = "cancelled"
    FILLED = "filled"
    EXPIRED = "expired"
    WORKING = "working"


class Trade:
    def __init__(
        self, symbol: str, order_type: OrderType, quantity: float, side: OrderSide, price: float
    ):
        self.symbol: str = symbol
        self.order_type: OrderType = order_type
        self.status: OrderStatus = OrderStatus.WORKING
        self.side: OrderSide = side
        self.quantity: float = quantity
        self.price: float = price


class Portfolio:
    def __init__(self, initial_capital: float = 1000.0, risk_tolerance: float = 0.0) -> None:
        self.capital: float = initial_capital
        self.profit_loss: float = 0.0
        # TODO: seems to redundant to store symbol in portfolio and key of dictionary
        self.positions: dict[str, Position] = {}
        self.risk_tolerance: float = risk_tolerance
        self.trades: list[Trade] = []

    def market_value(self) -> float:
        value: float = 0.0
        for pos in self.positions.values():
            value += pos.quantity * pos.purchase_price

        return value
