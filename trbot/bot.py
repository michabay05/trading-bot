from datetime import datetime
import csv, json, requests, time
import utils


class Candle:
    def __init__(self, open_: float, high: float, low: float, close: float, volume: float, timestamp: int):
        self.open = open_
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume
        self.timestamp = timestamp

    def __repr__(self) -> str:
        timestamp = utils.timestamp_to_datetime(self.timestamp)
        return f"Candle {{\n   open: {self.open:.2f}\n   high: {self.high:.2f}\n   low: {self.low:.2f}\n   close: {self.close:.2f}\n   volume: {self.volume:.1f}\n   timestamp: {timestamp}\n}}"

    def __eq__(self, other) -> bool:
        return (self.open == other.open and
                self.high == other.high and
                self.low == other.low and
                self.close == other.close and
                self.volume == other.volume and
                self.timestamp == other.timestamp)


class CandleOption:
    def __init__(self, ticker: str, start: str, end: str, mult: int, timespan: str):
        self.ticker = ticker
        self.start = start
        self.end = end
        self.mult = mult
        self.timespan = timespan

    def __repr__(self) -> str:
        return f"CandleOption {{\n   ticker: {self.ticker}\n   start: {self.start}\n   end: {self.end}\n   mult: {self.mult}\n   timespan: {self.timespan}\n}}"


class TradingBot:
    BASE_URL: str = "https://api.polygon.io"

    def __init__(self, API_KEY: str, rate_limit_per_min: int = 4, out_dir: str = "candles") -> None:
        # TODO: add portfolio
        self.api_key: str = API_KEY
        self.req_per_min: int = rate_limit_per_min
        self.request_times: list[datetime] = []
        self.out_dir: str = out_dir

    def _make_request(self, url: str) -> bytes:
        """ Make HTTP requests while respecting rate limit """
        dt_now = datetime.now()
        # Rate limiting: ensure we don't exceed the specified requests per minute
        if len(self.request_times) >= self.req_per_min:
            nth = self.req_per_min
            nth_time = self.request_times[-nth]
            time_since_nth_request = (dt_now - nth_time).total_seconds()
            if time_since_nth_request < 60:
                # Wait until time since nth request is < 60
                delay = 60.00 - time_since_nth_request
                print(f"Waiting {delay:.3f} seconds before next request...")
                time.sleep(delay)

        # Update request time list
        self.request_times.append(dt_now)

        resp = requests.get(url)

        # TODO: handle too many request error better
        resp.raise_for_status()
        return resp.content

    def get_historical_candles(self, opt: CandleOption) -> list[Candle]:
        """ Get historical candles for a certain stock as specified in the options """
        start_unix: int = utils.datetime_to_timestamp(opt.start)
        end_unix: int = utils.datetime_to_timestamp(opt.end)

        candles: list[Candle] = []
        # Approximate maximum limit of candles returned request
        MAX_CANDLES_PER_REQ: int = 1150

        def to_ms(mult: int, timespan: str) -> int:
            if timespan == "hour":
                return mult * 60 * 60 * 1000
            elif timespan == "minute":
                return mult * 60 * 1000
            else:
                raise Exception(f"Unknown timespan: {timespan}")

        # Total milliseconds range of all the candles
        MS_PER_REQ: int = MAX_CANDLES_PER_REQ * to_ms(opt.mult, opt.timespan)

        curr_start: int = start_unix
        while curr_start < end_unix:
            curr_end: int = min(curr_start + MS_PER_REQ, end_unix)

            opt.start = utils.timestamp_to_datetime(curr_start)
            opt.end = utils.timestamp_to_datetime(curr_end)
            batch = self.get_candles(opt)
            candles.extend(batch)

            print(f"Query complete: {opt.start} to {opt.end}")
            print(f"len(candles) = {len(candles)}\n----------")

            # Update starting point to progress forward
            curr_start = curr_end

        return candles

    def get_candles(self, opt: CandleOption) -> list[Candle]:
        start_unix: int = utils.datetime_to_timestamp(opt.start)
        end_unix: int = utils.datetime_to_timestamp(opt.end)

        target_url = (
            f"{TradingBot.BASE_URL}/v2/aggs/ticker/{opt.ticker}"
            f"/range/{opt.mult}/{opt.timespan}"
            f"/{start_unix}/{end_unix}?apiKey={self.api_key}"
        )

        data: bytes = self._make_request(target_url)
        root = json.loads(data)

        candles: list[Candle] = []
        for result in root.get("results", []):
            candle = Candle(
                result["o"],
                result["h"],
                result["l"],
                result["c"],
                result["v"],
                result["t"]
            )
            candles.append(candle)

        next_url = root.get("next_url", None)
        if next_url:
            data = self._make_request(f"{next_url}?apiKey={self.api_key}")
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
                candles.append(candle)

            if root2.get("next_url", None):
                print("--------")
                print(root2["next_url"])
                print("TODO: More values to collect")
                print("--------")
                raise Exception("Fix TODO here")

        return candles

    def import_candles(self, filepath: str) -> list[Candle]:
        candles: list[Candle] = []

        with open(filepath) as f:
            reader = csv.reader(f)
            next(reader) # Skip header

            for row in reader:
                unix_timestamp = utils.datetime_to_timestamp(row[1])
                open_ = float(row[2])
                high = float(row[3])
                low = float(row[4])
                close = float(row[5])
                volume = float(row[6])

                candle = Candle(open_, high, low, close, volume, unix_timestamp)
                candles.append(candle)

        return candles

    def export_candles(self, candles: list[Candle], opt: CandleOption) -> None:
        """ Export list of candles into a CSV file """

        rows: list[list[str]] = []
        rows.append(["date", "open", "high", "low", "close", "volume"])

        for i, c in enumerate(candles):
            date: str = utils.timestamp_to_datetime(c.timestamp)
            row: list[str] = [
                date, f"{c.open:.4f}", f"{c.high:.4f}", f"{c.low:.4f}",
                f"{c.close:.4f}", f"{c.volume:.0f}"
            ]
            rows.append(row)

        outpath: str = f"{self.out_dir}/ohlcv-{opt.ticker}-{opt.mult}{opt.timespan}.csv"

        with open(outpath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(rows)

        print(f"Exported successfully to {outpath}")
