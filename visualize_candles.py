from datetime import datetime
import time
from time import timezone
import http.server, json, math, os, shutil, socketserver, sys, webbrowser

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

    # sf.df.rename(
    #     columns={
    #         "Date": "time", "Open": "open", "High": "high", "Low": "low", "Close": "close",
    #         "Volume": "volume"
    #     },
    #     inplace=True
    # )
    sf.df.to_json(target_path, orient="records", indent=4)

def calc_save_indicators(csv_path: str, ticker: str, target_path: str) -> None:
    sf: Stockframe = Stockframe.from_csv(csv_path, ticker=ticker, mult=1, timespan=Timespan.HOUR)
    df: pd.DataFrame = pd.DataFrame()
    data: NDArray[np.float64] = sf.close_series
    dates: list[str] = sf.datetime_series
    df["datetime"] = dates

    # Calculate indicator values
    output = {}
    for name, args in INDICATORS.items():
        func = args[0]
        params = args[1]
        vals = func(data, **params)
        assert len(vals) == len(dates)
        df[name] = vals
        # df.to_json(target_path, orient="records", indent=4)
        output[name] = []
        for row in df.itertuples(index=False):
            # unix_timestamp = int(datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S").timestamp())
            # unix_timestamp = int(datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S").timestamp())
            # v = row[1] if not math.isnan(row[1]) else None
            if not math.isnan(row[1]):
                output[name].append({"time": row[0], "value": row[1]})
            else:
                output[name].append({"time": row[0], "value": 0.0})

        # Remove column when done
        del df[name]

    with open(target_path, "w") as f:
        json.dump(output, f, indent=4)


DEFAULT_PORT: int = 8080
INDICATORS: dict = {
    "EMA_1": [talib.EMA, {"timeperiod": 50}],
    "EMA_2": [talib.EMA, {"timeperiod": 100}]
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
