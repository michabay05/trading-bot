import json
import csv
import requests
import time
from datetime import datetime
from typing import List, Optional

BASE_URL = "https://api.polygon.io"

class Candle:
    def __init__(self, open_: float, high: float, low: float, close: float, volume: float, timestamp: int):
        self.open = open_
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume
        self.timestamp = timestamp

    def __str__(self):
        timestamp = timestamp_to_datetime(self.timestamp)
        return f"Candle {{\n   open: {self.open:.2f}\n   high: {self.high:.2f}\n   low: {self.low:.2f}\n   close: {self.close:.2f}\n   volume: {self.volume:.1f}\n   timestamp: {timestamp}\n}}"

    def series_val(self, series: str) -> float:
        if series == "open":
            return self.open
        elif series == "close":
            return self.close
        elif series == "low":
            return self.low
        elif series == "high":
            return self.high
        else:
            raise ValueError("Invalid series type")

class CandleResponse:
    def __init__(self, ticker: str, query_count: int, results_count: int, status: str, results: List[Candle], next_url: Optional[str] = None):
        self.ticker = ticker
        self.query_count = query_count
        self.results_count = results_count
        self.status = status
        self.results = results
        self.next_url = next_url

class IndicatorValues:
    def __init__(self, timestamp: int, value: float):
        self.timestamp = timestamp
        self.value = value

    def __str__(self):
        return f"IndicatorValues {{\n    timestamp: {timestamp_to_datetime(self.timestamp)}\n    value: {self.value:.2f}\n}}"

class CandleOption:
    def __init__(self, start: str, end: str, mult: int, timespan: str, ticker: str):
        self.start = start
        self.end = end
        self.mult = mult
        self.timespan = timespan
        self.ticker = ticker

    def __str__(self):
        return f"CandleOption {{\n   start: {self.start}\n   end: {self.end}\n   mult: {self.mult}\n   timespan: {self.timespan}\n}}"

class IndicatorOption:
    def __init__(self, timestamp: int, timestamp_filter: str, timespan: str, window: int, series_type: str, ticker: str, limit: int):
        self.timestamp = timestamp
        self.timestamp_filter = timestamp_filter
        self.timespan = timespan
        self.window = window
        self.series_type = series_type
        self.ticker = ticker
        self.limit = limit

def http_get_v2(target_url: str) -> bytes:
    resp = requests.get(target_url)
    resp.raise_for_status()
    return resp.content

def get_candles(api_key: str, stock_ticker: str, opt: CandleOption) -> List[Candle]:
    start_unix = datetime_to_timestamp(opt.start)
    end_unix = datetime_to_timestamp(opt.end)

    target_url = f"{BASE_URL}/v2/aggs/ticker/{stock_ticker}/range/{opt.mult}/{opt.timespan}/{start_unix}/{end_unix}?apiKey={api_key}"


    data = http_get_v2(target_url)
    root = json.loads(data)

    candles = []
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

    next_url = root.get("next_url")
    if next_url:
        data = http_get_v2(f"{next_url}?apiKey={api_key}")
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

        if root2.get("next_url"):
            print("--------")
            print(root2["next_url"])
            print("TODO: More values to collect")
            print("--------")
            raise Exception("Fix TODO here")

    return candles

def get_indicator(api_key: str, kind: str, opt: IndicatorOption) -> List[IndicatorValues]:
    filter_str = f".{opt.timestamp_filter}" if opt.timestamp_filter != "eq" else ""

    target_url = f"{BASE_URL}/v1/indicators/{kind}/{opt.ticker}?timestamp{filter_str}={opt.timestamp}&timespan={opt.timespan}&series_type={opt.series_type}&window={opt.window}&limit={opt.limit}&apiKey={api_key}"

    data = http_get_v2(target_url)
    root = json.loads(data)

    values = []
    for val in root["results"]["values"]:
        values.append(IndicatorValues(val["timestamp"], val["value"]))
    return values

def get_historical_candles(api_key: str, opt: CandleOption) -> List[Candle]:
    start_unix = datetime_to_timestamp(opt.start)
    end_unix = datetime_to_timestamp(opt.end)

    QUERY_LIMIT = 1150
    candles = []
    CANDLES_PER_REQ = QUERY_LIMIT * opt.mult
    MINS_PER_REQ = CANDLES_PER_REQ
    MS_PER_REQ = MINS_PER_REQ * 60 * 1000

    curr_start = start_unix
    request_count = 0

    while curr_start < end_unix:
        curr_end = min(curr_start + MS_PER_REQ, end_unix)

        opt.start = timestamp_to_datetime(curr_start)
        opt.end = timestamp_to_datetime(curr_end)
        batch = get_candles(api_key, opt.ticker, opt)
        candles.extend(batch)

        print(f"Query complete: {opt.start} to {opt.end}")
        print(f"len(candles) = {len(candles)}")

        curr_start = curr_end
        request_count += 1

        if request_count % 4 == 0:
            delay = 20
            print(f"Waiting {delay} seconds before next request...")
            time.sleep(delay)

    return candles

def export_candles(candles: List[Candle], opt: CandleOption) -> None:
    rows = []
    rows.append(["", "date", "open", "high", "low", "close", "volume"])

    for i, c in enumerate(candles):
        date = timestamp_to_datetime(c.timestamp)
        row = [i, date, f"{c.open:.4f}", f"{c.high:.4f}", f"{c.low:.4f}", f"{c.close:.4f}", f"{c.volume:.0f}"]
        rows.append(row)

    start_unix = datetime_to_timestamp(opt.start)
    end_unix = datetime_to_timestamp(opt.end)

    start_dt = datetime.fromtimestamp(start_unix/1000)
    end_dt = datetime.fromtimestamp(end_unix/1000)

    outpath = f"ohlcv-{start_dt.strftime('%b%y')}-{end_dt.strftime('%b%y')}-{opt.mult}{opt.timespan}-{opt.ticker}.csv"

    with open(outpath, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(rows)

def import_candles(filepath: str) -> List[Candle]:
    candles = []

    with open(filepath) as f:
        reader = csv.reader(f)
        next(reader) # Skip header

        for row in reader:
            unix_timestamp = datetime_to_timestamp(row[1])
            open_ = float(row[2])
            high = float(row[3])
            low = float(row[4])
            close = float(row[5])
            volume = float(row[6])

            candle = Candle(open_, high, low, close, volume, unix_timestamp)
            candles.append(candle)

    return candles

def highest_candle(candles: List[Candle], series: str, n: int) -> int:
    max_val = float('-inf')
    max_ind = -1

    for i in range(len(candles) - n, len(candles)):
        val = candles[i].series_val(series)
        if val > max_val:
            max_ind = i
            max_val = val

    return max_ind

def timestamp_to_datetime(timestamp: int) -> str:
    dt = datetime.fromtimestamp(timestamp/1000)
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def datetime_to_timestamp(dt_str: str) -> int:
    dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
    return int(dt.timestamp() * 1000)

def candle_equal(a: Candle, b: Candle) -> bool:
    return (a.open == b.open and
            a.high == b.high and
            a.low == b.low and
            a.close == b.close and
            a.volume == b.volume and
            a.timestamp == b.timestamp)

def slice_candle_list(candles: List[Candle], start: str, end: str) -> List[Candle]:
    if not candles:
        return []

    start_ts = datetime_to_timestamp(start)
    end_ts = datetime_to_timestamp(end)

    if start_ts > end_ts:
        raise ValueError("Start timestamp cannot be after end timestamp")

    result = []
    for candle in candles:
        if start_ts <= candle.timestamp < end_ts:
            result.append(candle)

    return result

def find_closest_candle(candles: List[Candle], dt_str: str) -> int:
    unix_ts = datetime_to_timestamp(dt_str)

    prev_ind = -1
    for i, candle in enumerate(candles):
        if unix_ts <= candle.timestamp:
            return prev_ind
        prev_ind = i

    raise ValueError(f"Failed to find candle with matching date of {dt_str}")

def find_closest_indicator(ind_vals: List[IndicatorValues], candle: Candle) -> int:
    prev_ind = -1
    for i, vals in enumerate(ind_vals):
        if vals.timestamp <= candle.timestamp:
            return prev_ind
        prev_ind = i

    dt_str = timestamp_to_datetime(candle.timestamp)
    raise ValueError(f"Failed to find indicator with matching date of {dt_str}")

def main():
    with open("API_KEY.secret") as f:
        API_KEY = f.read().strip()

    filepath = "ohlcv-INTL-Jan24-Apr25-5minute.csv"

    candles = import_candles(filepath)
    print(f"[INFO] Imported candles from '{filepath}'")

    ticker = "INTL"
    capital = 1000.0
    dt_str = "2025-04-24 10:15:00"
    print("[INFO] Timestamp: " + dt_str)

    ind = find_closest_candle(candles, dt_str)
    prev_c = candles[ind]
    print(f"candles[{ind}]: {prev_c}")

    unix_ts = datetime_to_timestamp(dt_str)
    ind_opt = IndicatorOption(
        timestamp=unix_ts,
        timestamp_filter="lte",
        timespan="minute",
        window=5,
        series_type="close",
        ticker=ticker,
        limit=5
    )

    indicators = get_indicator(API_KEY, "rsi", ind_opt)
    print(f"len(indicators) = {len(indicators)}")

    for i, iv in enumerate(indicators):
        print(f"indicators[{i}] = {iv}")

    num_shares = 4.0
    total_price = num_shares * prev_c.close
    capital -= total_price

    print(f"[INFO] Capital: {capital:.2f}")

if __name__ == "__main__":
    main()
