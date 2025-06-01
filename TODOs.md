# TODOs
A list of all the TODOs needed to be completed before each release

## Future versions
- [ ] (feat) Calculating indicators - via pandas dataframe
    - [indicators.py from areed1192/python-trading-robot](https://github.com/areed1192/python-trading-robot/blob/master/pyrobot/indicators.py)
- [ ] (feat) Have bot handle and maintain a portfolio
- [ ] (feat) Handle various types of trades
    - [ ] Market order
    - [ ] Limit order
- [ ] (feat) Simulate pre-market, market, post-market times using replayer
- [ ] (feat) Handle risk tolerance

# v0.2
- [ ] (feat) Create a mechanism to have a persistent portfolio between runs
    - [ ] Save portfolio status on program end
    - [ ] Import portfolio status on program start

## v0.1
- [x] (feature) Download historical data for any ticker and any other option
- [x] (Bot) Gather historical data on these tickers on 1 hour
    - [x] GM
    - [x] HPQ
    - [x] INTC
    - [x] NKE
    - [x] WMT
- [x] (fix) Remove duplicate candles when paginating downloaded historical data
- [x] (refactor) Store candles as a pandas dataframe
- [x] (Replayer) Develop a candle replayer (with modifiable replay time factor)
- [x] (Me) Research better sources for live market data streaming (list here)
    - Interactive brokers
    - Alpaca
    - Alphavantage

## Questions
- [ ] Understand why there are differences between polygon.io, webull, and tradingview data
