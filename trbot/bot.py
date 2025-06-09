from datetime import datetime
import csv, enum, json, os, requests, time

import pandas as pd

from . import candles
from .candles import Candle, CandleOption, Timespan
from .portfolio import Order, OrderType, Portfolio, Position
from .stockframe import StockFrame


class TradingBot:
    BASE_URL: str = "https://api.polygon.io"

    def __init__(self, portfolio_filepath: str | None = None) -> None:
        self._portfolio: Portfolio = Portfolio()
        if portfolio_filepath is not None:
            self._init_portfolio(portfolio_filepath)

    def request_order(self, symbol: str, quantity: float, purchase_price: float, purchase_dt: str) -> Order:
        # Request the market for a MARKET order. if all checks out, the market grants the order
        return Order(
            symbol=symbol,
            order_type=OrderType.MARKET,
            quantity=quantity,
            purchase_price=purchase_price,
            purchase_dt=purchase_dt
        )

    def save_portfolio(self, filepath: str):
        with open(filepath, "w") as f:
            json.dump(self._portfolio, f, indent=4, default=Portfolio.to_dict)

    def _init_portfolio(self, filepath: str) -> None:
        if not os.path.exists(filepath):
            print(f"[ERROR] Unable to find '{filepath}'")
            return

        with open(filepath, "r") as f:
            root = json.load(f)
            self._portfolio.set_capital(float(root["capital"]))
            psts: dict[str, Position] = {}
            for k, v in root["positions"].items():
                pos = Position(
                    timestamp=v["timestamp"],
                    quantity=float(v["quantity"]),
                    purchase_price=float(v["purchase_price"]),
                )
                psts[k] = pos

        self._portfolio.set_positions(psts)
