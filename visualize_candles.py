from datetime import datetime
import time
import http.server, json, math, os, socketserver, sys, webbrowser

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

def candle_csv_to_json(csv_path: str, ticker: str, target_path: str) -> None:
    sf: Stockframe = Stockframe.from_csv(csv_path, ticker=ticker, mult=1, timespan=Timespan.HOUR)
    candles: list[Candle] = []
    for i in range(0, len(sf)):
        candles.append(sf.row_to_candle(i))

    output: dict = {
        "symbol": ticker,
        "data": []
    }
    for cnd in candles:
        tmp = {
            "timestamp": str(cnd.timestamp),
            "open": cnd.open,
            "high": cnd.high,
            "low": cnd.low,
            "close": cnd.close,
            "volume": cnd.volume
        }
        output["data"].append(tmp)

    with open(target_path, "w") as f:
        json.dump(output, f, indent=4)

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
            d: dict = {
                "timeStr": str(dt),
                # This needs to be in milliseconds
                "time": int(dt.timestamp() * 1000),
            }
            v: float = values[i]
            if not math.isnan(v):
                d["value"] = v

            tmp["data"].append(d)

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
    ohlcv_path: str = "charts/ohlcv.json"
    candle_csv_to_json(fname, ticker, ohlcv_path)
    print(f"[INFO] Exported ohlcv data: '{ohlcv_path}'")

    indicator_list: list = [
        {
            "indicator": Indicator(kind="ema", part=["close"], period=5),
            "render_params": {
                "overlay": True,
                "color": "#80deea",
            },
        },
        {
            "indicator": Indicator(kind="ema", part=["close"], period=20),
            "render_params": {
                "overlay": True,
                "color": "#b39ddb"
            }
        },
        {
            "indicator": Indicator(kind="rsi", part=["close"], period=15),
            "render_params": {
                "overlay": False,
                "color": "#2962ff",
            }
        }
    ]

    # Calculate and save necessary indicators
    ind_path: str = "charts/inds.json"
    calc_save_indicators(fname, ticker, indicator_list, ind_path)
    print(f"[INFO] Exported indicator data: '{ind_path}'")

    diff: float = time.time() - start_time
    print(f"Took {diff:.3}s copy over the ohlcv and indicator data.")

    # start_server(DEFAULT_PORT)

if __name__ == "__main__":
    main()
