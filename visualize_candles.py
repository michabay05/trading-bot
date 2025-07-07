from datetime import datetime
import time
import http.server, json, math, os, socketserver, sys, webbrowser

import numpy as np
from numpy.typing import NDArray
import pandas as pd

from trbot import candles
from trbot.strategy import IndValues, Indicator
from trbot.candles import Candle, Timespan
from trbot.stockframe import Stockframe

def start_server(port: int) -> None:
    url: str = ""
    with socketserver.TCPServer(("", port), http.server.SimpleHTTPRequestHandler) as httpd:
        httpd.allow_reuse_address = True
        print(f"Server running at localhost:{port}")
        url = f"http://localhost:{port}/charts/"
        webbrowser.open(url)
        httpd.serve_forever()


def usage(program_name: str) -> None:
    print(f"Usage: {program_name} <SYMBOL>")

def valid_tickers(search_dir: str) -> tuple[list[str], list[str]]:
    tickers = []
    filenames = []
    for filename in os.listdir(search_dir):
        fpath: str = os.path.join(search_dir, filename)
        info: dict = candles.candle_info_from_path(fpath)
        tickers.append(info["ticker"])
        filenames.append(fpath)

    return (tickers, filenames)

def candle_csv_to_json(csv_path: str, ticker: str, target_path: str) -> None:
    sf: Stockframe = Stockframe.from_csv(csv_path, ticker=ticker, mult=1, timespan=Timespan.HOUR)
    sf.df.to_json(target_path, orient="records", indent=4, date_format="iso")

def calc_save_indicators(csv_path: str, ticker: str, indicator_list: list, target_path: str) -> None:
    sf: Stockframe = Stockframe.from_csv(csv_path, ticker=ticker, mult=1, timespan=Timespan.HOUR)
    dates: list[datetime] = sf.timestamp_series
    candles: list[Candle] = []
    for i in range(0, len(sf)):
        candles.append(sf.row_to_candle(i))

    # Calculate indicator values
    output: list[dict] = []
    for it in indicator_list:
        indicator: Indicator = it["indicator"]
        values: IndValues = indicator.compute_from_candles(candles)
        assert len(dates) == len(values), f"(dates.len = {len(dates)}) != (values.len = {len(values)})"
        n: int = len(dates)

        tmp = {
            "name": indicator.name(),
            **it["render_params"],
            "data": []
        }
        for i in range(0, n):
            dt: datetime = dates[i]
            v = values[i]
            if math.isnan(v):
                v = 0.0
            tmp["data"].append({"time": str(dt), "value": v})

        output.append(tmp)


    with open(target_path, "w") as f:
        json.dump(output, f, indent=4)

def main() -> None:
    print(f"[INFO] Currently in '{os.getcwd()}'")

    program_name: str = sys.argv[0]
    ticker: str = ""
    if len(sys.argv) > 1:
        ticker = sys.argv[1]
    else:
        usage(program_name)
        print("[ERROR] Please provide a valid ticker")
        sys.exit(1)

    fname: str = f"./ohlcv-1hr/{ticker}.csv"
    if not os.path.exists(fname):
        print(f"[ERROR] File does not exist: {fname}")
        sys.exit(1)

    print(f"[INFO] Found aggregate csv: '{fname}'")

    start_time: float = time.time()
    # Copy necessary candle csv over to 'charts/' as a json
    candle_csv_to_json(fname, ticker, "charts/ohlcv.json")

    indicator_list: list = [
        {
            "indicator": Indicator(kind="sma", part=["close"], period=5),
            "render_params": {"seriesType": "line", "overlay": True},
        },
        {
            "indicator": Indicator(kind="ema", part=["close"], period=20),
            "render_params": {"seriesType": "line", "overlay": True}
        },
        {
            "indicator": Indicator(kind="rsi", part=["close"], period=15),
            "render_params": {"seriesType": "baseline", "overlay": False}
        }
    ]

    # Calculate and save necessary indicators
    calc_save_indicators(fname, ticker, indicator_list, "charts/inds.json")
    diff: float = time.time() - start_time
    print(f"Took {diff:.3}s copy over the ohlcv and indicator data.")

    # start_server(DEFAULT_PORT)

if __name__ == "__main__":
    main()
