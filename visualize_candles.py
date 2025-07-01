from datetime import datetime
from typing import Callable
import time
import enum, http.server, json, math, os, socketserver, sys, webbrowser

import numpy as np
from numpy.typing import NDArray
import pandas as pd
import talib

from trbot import candles
from trbot.candles import Timespan
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
    sf.df.to_json(target_path, orient="records", indent=4)

def calc_save_indicators(csv_path: str, ticker: str, target_path: str) -> None:
    sf: Stockframe = Stockframe.from_csv(csv_path, ticker=ticker, mult=1, timespan=Timespan.HOUR)
    custom_df: pd.DataFrame = pd.DataFrame()
    data: NDArray[np.float64] = sf.close_series
    dates: list[datetime] = sf.timestamp
    custom_df["timestamp"] = dates

    # Calculate indicator values
    output: list[dict] = []
    for name, args in INDICATORS.items():
        # Call indicator function
        func: Callable = args[0]
        func_params: dict = args[1]
        vals = func(data, **func_params)
        # Check values are of expected length
        assert len(vals) == len(dates)
        # Append it to the dataframe on its own column
        custom_df[name] = vals

        render_params: dict = args[2]
        d = {
            "name": name,
            **render_params,
            "data": []
        }
        for row in custom_df.itertuples(index=False):
            dt: datetime = row[0]
            v: float = row[1]
            if math.isnan(v):
                v = 0.0
            d["data"].append({"time": str(dt), "value": v})

        output.append(d)
        # Remove column when done because the loop above only works with a dataframe that only
        # has a datetime and value column
        del custom_df[name]

    with open(target_path, "w") as f:
        json.dump(output, f, indent=4)


DEFAULT_PORT: int = 8080
# NOTE: all of these functions use the close data of the candles
INDICATORS: dict = {
    "EMA_1": [
        talib.EMA, {"timeperiod": 50}, {"seriesType": "line", "overlay": True}
    ],
    "EMA_2": [
        talib.EMA, {"timeperiod": 100}, {"seriesType": "line", "overlay": True}
    ],
    "RSI": [
        talib.RSI, {"timeperiod": 14}, {"seriesType": "baseline", "overlay": False}
    ]
}

def main():
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

    # Calculate and save necessary indicators
    calc_save_indicators(fname, ticker, "charts/inds.json")
    diff: float = time.time() - start_time
    print(f"Took {diff:.3}s copy over the ohlcv and indicator data.")

    # start_server(DEFAULT_PORT)

if __name__ == "__main__":
    main()
