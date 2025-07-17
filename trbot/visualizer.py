from datetime import datetime
import json, math, os, time

from . import log
from .strategy import IndValues, Indicator
from .candles import Candle, Timespan
from .stockframe import Stockframe


def _candle_csv_to_json(csv_path: str, ticker: str) -> list[dict]:
    sf: Stockframe = Stockframe.from_csv(csv_path, ticker=ticker, mult=1, timespan=Timespan.HOUR)
    candles: list[Candle] = []
    for i in range(0, len(sf)):
        candles.append(sf.row_to_candle(i))

    output: list[dict] = []
    for cnd in candles:
        tmp = {
            "timestamp": str(cnd.timestamp),
            "open": cnd.open,
            "high": cnd.high,
            "low": cnd.low,
            "close": cnd.close,
            "volume": cnd.volume
        }
        output.append(tmp)

    return output

def _calc_save_indicators(csv_path: str, ticker: str, indicator_list: list) -> list[dict]:
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

    return output

def _export_data(symbol: str, csv_path: str, indicator_list: list[dict]) -> dict:
    candles: list[dict] = _candle_csv_to_json(csv_path, symbol)

    # Calculate and save necessary indicators
    indicators: list[dict] = _calc_save_indicators(csv_path, symbol, indicator_list)
    print(f"[INFO] Computed necessary indicator data")

    return {
        "candles": candles,
        "indicators": indicators
    }

def main() -> None:
    log.info(f"Current working directory: '{os.getcwd()}'")
    start_time: float = time.time()
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

    all_symbols: list[str] = ["SPY", "AAPL", "GE", "HPQ", "EBAY", "XLF"]

    EXPORT_DIR: str = "./charts-v2/public/"
    successful_symbols: list[str] = []
    failed_symbols: list[str] = []
    for symbol in all_symbols:
        csv_path: str = f"./trout/ohlcv-1hr/{symbol}.csv"
        if not os.path.exists(csv_path):
            print(f"[ERROR] File does not exist: {csv_path}")
            failed_symbols.append(symbol)
            continue

        print(f"[INFO] Found aggregate csv: '{csv_path}'")

        output_json: dict = _export_data(symbol, csv_path, indicator_list)
        output_path: str = f"{EXPORT_DIR}/{symbol}.json"
        with open(output_path, "w") as f:
            json.dump(output_json, f, indent=4)

        print(f"[INFO] Exported all data for {symbol} at '{output_path}'")
        print(f"[INFO] ---------------")
        successful_symbols.append(symbol)

    info_path: str = f"{EXPORT_DIR}/info.json"
    with open(info_path, "w") as f:
        tmp = {
            "symbols": successful_symbols
        }
        json.dump(tmp, f, indent=4)
    print(f"[INFO] Exported a list of all successfully exported symbols at {info_path}.")

    diff: float = time.time() - start_time
    print(f"[INFO] Successfully exported data for {len(successful_symbols)} symbols: {diff:.3}s")
    if len(failed_symbols) > 0:
        print(f"[INFO] Failed to export {len(failed_symbols)} symbols: {failed_symbols}")


if __name__ == "__main__":
    main()
