from datetime import datetime
import csv, enum, json, requests, time

import pandas as pd
from . import candles
from .stockframe import StockFrame
from .candles import Candle, CandleOption, Timespan



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
        start_unix: int = candles.datetime_to_timestamp(opt.start)
        end_unix: int = candles.datetime_to_timestamp(opt.end)

        cnds: list[Candle] = []
        # Approximate maximum limit of candles returned request
        MAX_CANDLES_PER_REQ: int = 1150

        # Total milliseconds range of all the candles
        MS_PER_REQ: int = MAX_CANDLES_PER_REQ * opt.mult * opt.timespan.to_ms()

        curr_start: int = start_unix
        while curr_start < end_unix:
            curr_end: int = min(curr_start + MS_PER_REQ, end_unix)

            opt.start = candles.timestamp_to_datetime(curr_start)
            opt.end = candles.timestamp_to_datetime(curr_end)
            batch = self.get_candles(opt)
            cnds.extend(batch)

            print(f"Query complete: {opt.start} to {opt.end}")
            print(f"len(candles) = {len(cnds)}\n----------")

            # Update starting point to progress forward
            curr_start = curr_end

        return cnds

    def get_candles(self, opt: CandleOption) -> list[Candle]:
        start_unix: int = candles.datetime_to_timestamp(opt.start)
        end_unix: int = candles.datetime_to_timestamp(opt.end)

        target_url = (
            f"{TradingBot.BASE_URL}/v2/aggs/ticker/{opt.ticker}"
            f"/range/{opt.mult}/{opt.timespan}"
            f"/{start_unix}/{end_unix}?apiKey={self.api_key}"
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
                cnds.append(candle)

            if root2.get("next_url", None):
                print("--------")
                print(root2["next_url"])
                print("TODO: More values to collect")
                print("--------")
                raise Exception("Fix TODO here")

        return cnds
