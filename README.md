# Algorithmic Trading Bot

> [!WARNING]
> The trading bot is still a **work in progress**. Take heed.

## Quickstart
Before running these commands, remember to install `talib` on your system (not the python package, but the c library).
```bash
$ python -m venv .venv
$ source .venv/bin/activate
$ pip install -r requirements.txt
$ python run_bot.py
```
---
Visualize candles and indicators (run this command after setting up virtual environment)
```bash
$ python visualize_candles.py GM
```

## Features
- Historical data downloader
- Candle replayer (with a modifiable replay time factor)
- A variety of indicators such as SMA, EMA, RSI
- Strategy implementation system
- Backtesting
- Take profit and stop losses

## Resource used
- [areed1192/python-trading-robot](https://github.com/areed1192/python-trading-robot.git)
- [tradingview/lightweight-charts](https://github.com/tradingview/lightweight-charts.git)
- [lightweight-charts-python](https://github.com/louisnw01/lightweight-charts-python.git)
- [alpacahq/alpaca-py](https://github.com/alpacahq/alpaca-py/)
