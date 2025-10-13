from enum import Enum
from dataclasses import asdict, dataclass
from datetime import datetime
import enum
import json
from uuid import UUID

from alpaca.trading.enums import PositionIntent, PositionSide

from .log import bot_log as b_log

class TBOrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"

class TBOrderDir(Enum):
    LONG = "long"
    SHORT = "short"

    def opposite(self) -> 'TBOrderDir':
        match self:
            case TBOrderDir.LONG:
                return TBOrderDir.SHORT
            case TBOrderDir.SHORT:
                return TBOrderDir.LONG

    @classmethod
    def from_alpaca(cls, side: PositionSide) -> 'TBOrderDir':
        match side:
            case PositionSide.LONG:
                return TBOrderDir.LONG
            case PositionSide.SHORT:
                return TBOrderDir.SHORT


class TBOrderStatus(Enum):
    FILLED = "filled"
    WORKING = "working"
    INSUFF_FUNDS = "insufficient funds"


@dataclass
class Position:
    symbol: str
    quantity: float
    side: TBOrderDir
    alpaca_id: UUID
    unrealized_pl: float | None = None
    unrealized_plpc: float | None = None
    market_value: float | None = None
    # The earliest possible time to close a position (following PDT)
    earliest_close: datetime | None = None

    @classmethod
    def from_dict(cls, pos_dict: dict) -> 'Position':
        if isinstance(pos_dict["side"], str):
            pos_dict["side"] = TBOrderDir(pos_dict["side"])

        return cls(**pos_dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["side"] = self.side.value
        d["alpaca_id"] = str(self.alpaca_id)
        d["earliest_close"] = str(self.earliest_close)
        return d

    def clone(self) -> 'Position':
        return Position(**self.to_dict())


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
            "kind": ord_amount.kind.value
        }


@dataclass
class TBOrderReq:
    symbol: str
    side: TBOrderDir
    requested_qty: TBOrderAmount
    requested_dt: str
    intent: TBIntent
    type: TBOrderType
    status: TBOrderStatus = TBOrderStatus.WORKING
    filled_qty: float | None = None
    filled_dt: datetime | None = None
    take_profit: TakeProfitTrigger | None = None
    stop_loss: StopLossTrigger | None = None
    completed: bool = False
    alpaca_id: UUID | None = None
    # Flag for the broker to remind itself that it should not focus on this order
    stop_checking: bool = False

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


class Portfolio:
    def __init__(self, cash: float = 1000.0) -> None:
        self._cash: float = cash
        # Stores currently all the bot's positions
        self._positions: dict[str, Position] = {}

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

    def __repr__(self) -> str:
        return json.dumps(Portfolio.to_dict(self), indent=4)

    def save_as_json(self, filepath: str) -> None:
        with open(filepath, "w") as f:
            json.dump(Portfolio.to_dict(self), f, indent=4)

    def init_from_json(self, _filepath: str) -> None:
        raise NotImplementedError()

    @staticmethod
    def to_dict(pft: 'Portfolio') -> dict:
        return {
            "cash": pft.cash,
            "positions": {
                symbol: Position.to_dict(position)
                for symbol, position in pft.positions.items()
            },
        }

    def in_position(self, symbol: str) -> bool:
        return symbol in self._positions.keys()

    def set_earliest_close(self, symbol: str, earliest_close_dt: datetime | None) -> None:
        if not self.in_position(symbol):
            b_log.warn(f"Could not set earliest close because there is no open position for {symbol}")
            return

        self._positions[symbol].earliest_close = earliest_close_dt
