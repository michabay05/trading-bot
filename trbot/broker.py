from abc import ABC, abstractmethod
from datetime import datetime
from zoneinfo import ZoneInfo
import json, sys, time

from alpaca.data import RawData
from alpaca.data.live.stock import StockDataStream
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, OrderStatus, OrderType, QueryOrderStatus, TimeInForce
from alpaca.trading.models import Clock, TradeAccount
from alpaca.data.models import BarSet
from alpaca.trading.requests import ClosePositionRequest, GetOrdersRequest, MarketOrderRequest, StopLossRequest, TakeProfitRequest
from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
import requests
import pandas as pd

from trbot import util

from . import candles, tbsecrets, log
from .tbsecrets import ALPACA_SECRETS
from .candles import Candle, CandleOption, Timespan
from .portfolio import OrderDir, TBOrder, Portfolio, MarketOrder, OrderState, Position


class InsufficientFundsError(Exception):
    pass


class Broker(ABC):
    ## ============= PROPERTIES USED IN THESE ABSTRACT CLASS (BELOW) ============= ##
    @property
    @abstractmethod
    def portfolio(self) -> Portfolio:
        pass
    ## ============= PROPERTIES USED IN THESE ABSTRACT CLASS (ABOVE) ============= ##

    @abstractmethod
    def execute_open_order(self, order: MarketOrder, last_close: float, curr_dt_str: str) -> None:
        pass

    @abstractmethod
    def execute_close_order(self, order: MarketOrder, last_close: float) -> None:
        pass


class LiveBroker:
    def __init__(self) -> None:
        api_key: str = ALPACA_SECRETS[1]["api_key"]
        secret_key: str = ALPACA_SECRETS[1]["secret_key"]
        self._data_stream: StockDataStream = StockDataStream(api_key, secret_key)
        self._trade_client: TradingClient = TradingClient(api_key, secret_key)
        self._stock_historical_data_client = StockHistoricalDataClient(
            api_key, secret_key, raw_data=False
        )
        self._portfolio: Portfolio = Portfolio()
        self.sync_portfolio()

    def sync_portfolio(self):
        # Sync w/ remote's available cash
        acct = self._trade_client.get_account()
        if not isinstance(acct, TradeAccount):
            raise TypeError(f"account was of type {type(acct)} instead of TradeAccount")

        cash: str | None = acct.cash
        if cash is None:
            raise ValueError("`account.cash: str | None` was None.")

        self._portfolio.cash = float(cash)

        # Sync w/ remote's open orders
        open_orders = self._trade_client.get_orders(filter=GetOrdersRequest(status=QueryOrderStatus.OPEN))
        if not isinstance(open_orders, list):
            raise TypeError(f"open_orders was of type {type(open_orders)} instead of list[Order]")

        orders = []
        for ord in open_orders:
            # TODO: Add more details here. alpaca differentiates between `Order` and `OrderRequest`
            #       My order class models the OrderRequest class rather than the `Order`
            d = {
                "symbol": ord.symbol,
                "side": OrderDir.LONG if ord.side == OrderSide.BUY else OrderDir.SHORT,
                "status": OrderState.FILLED if ord.status == OrderStatus.FILLED else OrderState.WORKING,
                "requested_qty": ord.qty,
                "purchase_dt": ord.filled_at,
                "purchase_qty": ord.filled_qty,
            }
            orders.append(TBOrder(**d))

        # Sync w/ remote's open positions
        open_positions = self._trade_client.get_all_positions()
        if not isinstance(open_positions, list):
            raise TypeError(f"open_position was of type {type(acct)} instead of list[Position]")

        positions: dict[str, Position] = {}
        for pos in open_positions:
            d = {
                "symbol": pos.symbol,
                "quantity": float(pos.qty),
                "price": pos.current_price,
                "side": pos.side,
            }
            positions[d["symbol"]] = Position(**d)

        self._portfolio.positions = positions

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

    def execute_open_order(self, order: MarketOrder) -> None:
        tp = None
        sl = None
        if order.take_profit is not None:
            tp = TakeProfitRequest(limit_price=order.take_profit.tp_limit)
        if order.stop_loss is not None:
            sl = StopLossRequest(stop_price=order.stop_loss.sl_limit)

        req = MarketOrderRequest(
            symbol=order.symbol,
            qty=order.requested_qty,
            side=OrderSide.BUY if order.is_long() else OrderSide.SELL,
            type=OrderType.MARKET,
            time_in_force=TimeInForce.DAY,
            take_profit=tp,
            stop_loss=sl,
        )
        _ = self._trade_client.submit_order(req)

    def execute_close_order(self, order: MarketOrder, last_close: float) -> None:
        self._trade_client.close_position(
            order.symbol,
            close_options=ClosePositionRequest(qty=str(order.requested_qty))
        )

    # NOTE: this could take a while, depending the time range supplied
    def export_historical_candles(self,
        symbols: list[str], start: datetime, end: datetime = datetime.now()
    ) -> None:
        req = StockBarsRequest(
            symbol_or_symbols=symbols,
            timeframe=TimeFrame(amount=1, unit=TimeFrameUnit.Hour),
            start=start,
            end=end
        )

        df: pd.DataFrame = pd.DataFrame()
        try:
            bars: BarSet | RawData = self._stock_historical_data_client.get_stock_bars(req)
            if not isinstance(bars, BarSet):
                raise TypeError(f"Expected `bars` to be of type BarSet, got {type(bars)}")

            df = bars.df.copy()
        except Exception as e:
            print(e)

        # Reset index to make it a regular column
        df.reset_index(inplace=True)
        log.debug(f"{df.columns}")
        # Modify the timestamp column
        df["timestamp"] = df["timestamp"].apply(
            lambda x: datetime.fromisoformat(str(x)).astimezone(util.MY_TIMEZONE)
        )

        uniq_symbols: set[str] = set(df["symbol"])
        for symbol in uniq_symbols:
            # sf = Stockframe.from_csv(f"ohlcv-1hr/{symbol}.csv", symbol, mult=1, timespan=Timespan.HOUR)
            sliced_df = df[df["symbol"] == symbol].copy()
            sliced_df.drop("symbol", axis=1, inplace=True)
            # new_df = pd.concat([sf.df, sliced_df], ignore_index=True)
            del sliced_df["trade_count"]
            del sliced_df["vwap"]

            sliced_df.to_csv(f"trout/ohlcv-1hr/{symbol}.csv", index=False)


class HistoricalBroker:
    def __init__(self, allow_fractional: bool = False, commission: float = 0.0) -> None:
        self._allow_fractional: bool = allow_fractional
        self._commission: float = commission
        # Contains a list of orders that require checkups, which include orders with
        #  take profits and stop losses
        self._checkups: list[int] = []

    def is_market_open(self, dt_str: str) -> bool:
        dt: datetime = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        # Note: dt.weekday() -> 0-6 where [Monday = 0]
        return dt.weekday() < 5 and (9 <= dt.hour <= 16)

    def order_checkup(self, pft: Portfolio, last_close: float, curr_dt_str: str):
        completed_inds: set[int] = set()

        for index, id in enumerate(self._checkups):
            order = pft.find_order_by_id(id)
            if order is None:
                # Order with matching id has not been found
                continue

            if order.take_profit is not None:
                tp_limit: float = order.take_profit.tp_limit
                tp_crossed: bool = last_close >= tp_limit if order.is_long() else last_close <= tp_limit
                if tp_crossed:
                    tp_order: MarketOrder = MarketOrder(
                        symbol=order.symbol,
                        requested_qty=order.requested_qty,
                        side=order.side.opposite(),
                        requested_price=last_close,
                        requested_dt=curr_dt_str,
                        intent=order.take_profit.intent
                    )
                    self.execute_close_order(tp_order, pft, last_close)
                    assert tp_order.status != OrderState.FILLED
                    # Update info about when and at what price the take profit took place
                    order.take_profit.purchase_dt = curr_dt_str
                    order.take_profit.purchase_price = last_close
                    completed_inds.add(index)

            if order.stop_loss is not None:
                # raise NotImplementedError("stop losses are not implemented yet!")
                sl_limit: float = order.stop_loss.sl_limit
                sl_crossed: bool = last_close <= sl_limit if order.is_long() else last_close >= sl_limit
                if sl_crossed:
                    sl_order: MarketOrder = MarketOrder(
                        symbol=order.symbol,
                        requested_qty=order.requested_qty,
                        side=order.side.opposite(),
                        requested_price=last_close,
                        requested_dt=curr_dt_str,
                        intent=order.stop_loss.intent
                    )
                    self.execute_close_order(sl_order, pft, last_close)
                    assert sl_order.status != OrderState.FILLED
                    # Update info about when and at what price the take profit took place
                    order.stop_loss.purchase_dt = curr_dt_str
                    order.stop_loss.purchase_price = last_close
                    completed_inds.add(index)

        for i in sorted(completed_inds, reverse=True):
            del self._checkups[i]

    def _validate_quantity(self, size: float, last_close: float, portfolio: Portfolio) -> float:
        qty: float = 0.0
        if size < 1.0:
            # In essence, buy as much shares as possible with this amount:
            #   >> size * portfolio.capital
            pct: float = size
            order_value: float = pct * portfolio.cash
            qty = order_value / last_close
        else:
            qty = size

        return qty if self._allow_fractional else int(qty)

    def execute_open_order(self,
        order: MarketOrder, portfolio: Portfolio, last_close: float, curr_dt_str: str
    ) -> None:
        # NOTE: this method only handles orders with the intent of opening a position
        assert order.is_to_open()

        if order.status != OrderState.WORKING:
            # The order has been completed already
            return

        if not self.is_market_open(curr_dt_str):
            # if market not open, then status won't be executed. that will happen once the market reopens
            order.status = OrderState.WORKING
            return

        order.requested_qty = self._validate_quantity(order.requested_qty, last_close, portfolio)
        requested_value = order.requested_qty * order.requested_price
        if portfolio.cash < requested_value:
            # Order cancelled due to insufficient funds (Update order status)
            raise InsufficientFundsError(f"(Capital: ${portfolio.cash:.4f}, order total: ${requested_value})")

        # Subtract order from total and update portfolio's positions
        portfolio.cash = portfolio.cash - requested_value
        # Update order status
        order.status = OrderState.FILLED
        order.purchase_dt = curr_dt_str
        order.purchase_price = last_close
        portfolio.add_orders(order)

        # Update portfolio position
        if order.symbol in portfolio.positions.keys():
            # Position already exists
            pst: Position = portfolio.positions[order.symbol]
            new_value = pst.market_value() + requested_value
            pst.price = order.requested_price
            pst.quantity = new_value / order.requested_price
        else:
            # New position was justed created
            portfolio.positions[order.symbol] = Position(
                order.symbol, order.requested_qty, order.requested_price
            )

        if order.take_profit is not None:
            self._checkups.append(order.id)

    def execute_close_order(self, order: MarketOrder, portfolio: Portfolio, last_close: float) -> None:
        assert order.is_to_close()

        if not order.symbol in portfolio.positions.keys():
            # There is no position with this symbol to close
            return

        position: Position = portfolio.positions[order.symbol]
        portfolio.cash += position.quantity * last_close
        del portfolio.positions[order.symbol]

# ============================ POLYGON.IO-specific ============================
_BASE_URL: str = "https://api.polygon.io"
_API_KEY: str = tbsecrets.POLYGON_IO_SECRETS["api_key"]
_REQ_PER_MIN: int = 4
_REQUEST_TIMES: list[datetime] = []


def get_historical_candles(opt: CandleOption) -> list[Candle]:
    """ Get historical candles for a certain stock as specified in the options """
    start_unix: int = candles.datetime_to_timestamp(opt.start)
    end_unix: int = candles.datetime_to_timestamp(opt.end)

    cnds: list[Candle] = []
    # Approximate maximum limit of candles returned request
    MAX_CANDLES_PER_REQ: int = 1150

    # Total milliseconds range of all the candles
    MS_PER_REQ: int = MAX_CANDLES_PER_REQ * opt.mult * opt.timespan.to_ms()

    curr_start: int = start_unix
    start_time: float = time.time()
    while curr_start <= end_unix:
        curr_end: int = min(curr_start + MS_PER_REQ, end_unix)

        opt.start = candles.timestamp_to_datetime(curr_start)
        opt.end = candles.timestamp_to_datetime(curr_end)
        batch = _get_candles(opt)
        cnds.extend(batch)

        print(f"Query complete: {opt.start} to {opt.end}")
        print(f"len(candles) = {len(cnds)}\n----------")

        curr_start = curr_end + opt.mult * opt.timespan.to_ms()

    diff: float = time.time() - start_time
    print(f"Completed in {diff:.3} seconds.")

    return cnds

def _get_live_quote(symbol: str, dt_str: str | None = None) -> float: # type: ignore
    dt: datetime = datetime.now()
    if dt_str is not None:
        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")

    start_dt = dt.strftime("%Y-%m-%d %H:%M:%S")
    opt = CandleOption(
        ticker=symbol,
        start=start_dt,
        end=start_dt,
        mult=1,
        timespan=Timespan.MINUTE
    )
    candles: list[Candle] = _get_candles(opt)
    assert len(candles) == 1, "ERROR: there should only be one candle here for a quote request"

    return candles[0].close

def _get_candles(opt: CandleOption) -> list[Candle]:
    start_unix: int = candles.datetime_to_timestamp(opt.start)
    end_unix: int = candles.datetime_to_timestamp(opt.end)

    target_url = (
        f"{_BASE_URL}/v2/aggs/ticker/{opt.ticker}"
        f"/range/{opt.mult}/{opt.timespan.value}/{start_unix}/{end_unix}"
        f"?adjusted={str(opt.adjusted).lower()}&limit={opt.limit}&apiKey={_API_KEY}"
    )

    data: bytes = _make_request(target_url)
    root = json.loads(data)

    cnds: list[Candle] = []
    for result in root.get("results", []):
        candle = Candle(
            result["o"],
            result["h"],
            result["l"],
            result["c"],
            result["v"],
            result["t"]
        )
        cnds.append(candle)

    next_url = root.get("next_url", None)
    while next_url is not None:
        data = _make_request(f"{next_url}&apiKey={_API_KEY}")
        root2 = json.loads(data)
        for result in root2.get("results", []):
            candle = Candle(
                result["o"],
                result["h"],
                result["l"],
                result["c"],
                result["v"],
                result["t"]
            )
            cnds.append(candle)

        next_url = root2.get("next_url", None)

    return cnds

def _make_request(url: str) -> bytes:
    """ Make HTTP requests while respecting rate limit """
    dt_now = datetime.now()
    # Rate limiting: ensure we don't exceed the specified requests per minute
    if len(_REQUEST_TIMES) >= _REQ_PER_MIN:
        nth = _REQ_PER_MIN
        nth_time = _REQUEST_TIMES[-nth]
        time_since_nth_request = (dt_now - nth_time).total_seconds()
        # Wait until time since nth request is more than a minute
        if time_since_nth_request < 60:
            delay = 60.00 - time_since_nth_request
            print(f"Waiting {delay:.3f} seconds before next request...")
            time.sleep(delay)

    # Update request time list
    _REQUEST_TIMES.append(dt_now)

    resp = requests.get(url)
    if not resp.ok:
        print(f"[{resp.status_code}] ERROR: {resp.json()}")
        sys.exit(1)

    return resp.content
