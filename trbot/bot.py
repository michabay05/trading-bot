from datetime import datetime
import csv, enum, json, requests, time

import pandas as pd


from . import candles
from .candles import Candle, CandleOption, Timespan
from .portfolio import Order, OrderType, Portfolio, Position
from .stockframe import Stockframe
from .strategy import Strategy


class TradingBot:
    BASE_URL: str = "https://api.polygon.io"

    def __init__(self, portfolio_filepath: str | None = None) -> None:
        self._portfolio: Portfolio = Portfolio()
        if portfolio_filepath is not None:
            self._init_portfolio(portfolio_filepath)
