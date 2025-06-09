from datetime import datetime, timedelta
import json, requests, sys, time

from . import candles
from .candles import Candle, CandleOption, Timespan
from .portfolio import Order, OrderStatus, OrderType, Portfolio
from .stockframe import Stockframe


class Market:
    BASE_URL: str = "https://api.polygon.io"

    def __init__(self, api_key: str, rate_limit_per_min: int = 4) -> None:
        self._api_key: str = api_key
        self._req_per_min: int = rate_limit_per_min
        self._request_times: list[datetime] = []

    def is_open(self) -> bool:
        raise Exception("TODO: implement Market.is_open()")

    def market_order(self, symbol: str, quantity: float, dt_str: str | None = None) -> Order:
        start = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S") if dt_str is not None else datetime.now()
        dt: str = (start + timedelta(seconds=1)).strftime("%Y-%m-%d %H:%M:%S")
        purchase_price: float = self.get_quote(symbol, dt)

        return Order(
            symbol=symbol,
            order_type=OrderType.MARKET,
            quantity=quantity,
            purchase_price=purchase_price,
            purchase_dt=dt
        )

    def execute_order(self, order: Order, portfolio: Portfolio):
        if not self.is_open():
            # if market not open, then status won't be executed. that will happen once the market reopens
            return OrderStatus.WORKING

        order_total: float = order.quantity * order.purchase_price
        capital: float = portfolio.get_capital()
        if order_total <= capital:
            # Subtract order from total and update portfolio's positions
            portfolio.set_capital(capital - order_total)

            # Update order status
            order.status = OrderStatus.FILLED
            portfolio.add_order(order)
        else:
            # Order cancelled due to insufficient funds (Update order status)
            order.status = OrderStatus.CANCELLED
            portfolio.add_order(order)

    def get_quote(self, symbol: str, dt_str: str | None = None) -> float:
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
        candles: list[Candle] = self._get_candles(opt)
        assert len(candles) == 1, "ERROR: there should only be one candle here for a quote request"

        return candles[0].close

    def get_historical_candles(self, opt: CandleOption) -> list[Candle]:
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
            batch = self._get_candles(opt)
            cnds.extend(batch)

            print(f"Query complete: {opt.start} to {opt.end}")
            print(f"len(candles) = {len(cnds)}\n----------")

            curr_start = curr_end + opt.mult * opt.timespan.to_ms()

        diff: float = time.time() - start_time
        print(f"Completed in {diff:.3} seconds.")

        return cnds

    def _get_candles(self, opt: CandleOption) -> list[Candle]:
        start_unix: int = candles.datetime_to_timestamp(opt.start)
        end_unix: int = candles.datetime_to_timestamp(opt.end)

        target_url = (
            f"{Market.BASE_URL}/v2/aggs/ticker/{opt.ticker}"
            f"/range/{opt.mult}/{opt.timespan.value}/{start_unix}/{end_unix}"
            f"?adjusted={str(opt.adjusted).lower()}&limit={opt.limit}&apiKey={self._api_key}"
        )

        data: bytes = self._make_request(target_url)
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
            data = self._make_request(f"{next_url}&apiKey={self._api_key}")
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

    def _make_request(self, url: str) -> bytes:
        """ Make HTTP requests while respecting rate limit """
        dt_now = datetime.now()
        # Rate limiting: ensure we don't exceed the specified requests per minute
        if len(self._request_times) >= self._req_per_min:
            nth = self._req_per_min
            nth_time = self._request_times[-nth]
            time_since_nth_request = (dt_now - nth_time).total_seconds()
            if time_since_nth_request < 60:
                # Wait until time since nth request is < 60
                delay = 60.00 - time_since_nth_request
                print(f"Waiting {delay:.3f} seconds before next request...")
                time.sleep(delay)

        # Update request time list
        self._request_times.append(dt_now)

        resp = requests.get(url)
        if not resp.ok:
            print(f"[{resp.status_code}] ERROR: {resp.json()["message"]}")
            sys.exit(1)

        return resp.content


class CandleReplayer:
    # NOTE: (REAL_TIME) ÷ (TIME_FACTOR) = (REPLAY_TIME)
    # DEFAULT_TIME_FACTOR = 0.25 hour (15 minutes) -> 1 second (900x speedup)
    DEFAULT_TIME_FACTOR: int = 900

    def __init__(self, sf: Stockframe, time_factor: float = DEFAULT_TIME_FACTOR) -> None:
        self.sf: Stockframe = sf

        self.time_factor: float = time_factor
        self.index: int = 0

        start_dt_str: str = self.sf.df["Date"].iloc[self.index]
        self.start_time: datetime = datetime.strptime(start_dt_str, "%Y-%m-%d %H:%M:%S")
        self.time: datetime = self.start_time

        self.is_ready: bool = True

    def get_current_time(self) -> datetime:
        return self.time

    def update_time(self, dt_in_sec: float):
        """ Increment timer in seconds """

        if self.index + 1 >= self.candle_count():
            # There are no more candles to make available
            self.is_ready = False
            return

        dt_str: str = self.sf.df["Date"].iloc[self.index]
        next_time: datetime = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        if self.time >= next_time:
            self.is_ready = True

        self.time += timedelta(seconds=dt_in_sec * self.DEFAULT_TIME_FACTOR)
        self.time = self.time.replace(second=0, microsecond=0)

    def grab_next_candle(self) -> Candle | None:
        if not self.is_ready or self.index >= self.candle_count():
            return None

        # Once candle is used, next candle is now not ready
        self.is_ready = False
        row = self.sf.df.iloc[self.index]

        # Extract values from the Series and convert to appropriate types
        candle = Candle(
            open_=float(row["Open"]),
            high=float(row["High"]),
            low=float(row["Low"]),
            close=float(row["Close"]),
            volume=float(row["Volume"]),
            timestamp=candles.datetime_to_timestamp(row["Date"])
        )

        self.index += 1
        return candle

    def candle_count(self) -> int:
        return len(self.sf.df)
