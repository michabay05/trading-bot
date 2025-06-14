from datetime import datetime, timedelta
import json, sys, time

import requests

from . import candles
from .candles import Candle, CandleOption, Timespan
from .portfolio import Portfolio, Order, OrderStatus, OrderType, Position


_BASE_URL: str = "https://api.polygon.io"
_API_KEY_FILEPATH: str = "./API_KEY.secret"
_API_KEY: str = ""
_REQ_PER_MIN: int = 4
_REQUEST_TIMES: list[datetime] = []

def is_market_open() -> bool:
    return True

def market_order(symbol: str, quantity: float, dt_str: str | None = None) -> Order:
    start = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S") if dt_str is not None else datetime.now()
    dt: str = (start + timedelta(seconds=1)).strftime("%Y-%m-%d %H:%M:%S")
    purchase_price: float = _get_quote(symbol, dt)

    return Order(
        symbol=symbol,
        order_type=OrderType.MARKET,
        quantity=quantity,
        purchase_price=purchase_price,
        purchase_dt=dt
    )

def execute_order(order: Order, portfolio: Portfolio) -> None:
    if not is_market_open():
        # if market not open, then status won't be executed. that will happen once the market reopens
        order.status = OrderStatus.WORKING
        return

    capital: float = portfolio.capital
    if order.abs_value() <= capital:
        # Subtract order from total and update portfolio's positions
        portfolio.capital = capital - order.abs_value()
        # Update order status
        order.status = OrderStatus.FILLED
        portfolio.add_order(order)
    else:
        # Order cancelled due to insufficient funds (Update order status)
        order.status = OrderStatus.CANCELLED
        portfolio.add_order(order)

    # Update portfolio position
    if order.symbol in portfolio.positions.keys():
        # Position already exists
        pst: Position = portfolio.positions[order.symbol]
        new_value = pst.market_value() + order.value()
        pst.price = order.purchase_price
        pst.quantity = new_value / order.purchase_price
    else:
        # New position was justed created
        portfolio.positions[order.symbol] = Position(order.quantity, order.purchase_price)

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

def _get_quote(symbol: str, dt_str: str | None = None) -> float:
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
    # Init API_KEY if not done already
    if len(_API_KEY) == 0:
        _init_api_key()

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

def _init_api_key() -> None:
    global _API_KEY
    with open(_API_KEY_FILEPATH, "r") as f:
        _API_KEY = f.read().strip()
