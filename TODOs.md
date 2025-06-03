# TODOs
A list of all the TODOs needed to be completed before each release

## Questions to research
- Why are there are differences in the data between polygon.io, webull, and tradingview?
- Research better sources for live market data streaming (list here)
    - Interactive brokers
    - Alpaca
    - Alphavantage

## Future versions
- [ ] (feat) Calculating indicators - via pandas dataframe
    - [indicators.py from areed1192/python-trading-robot](https://github.com/areed1192/python-trading-robot/blob/master/pyrobot/indicators.py)
- [ ] (feat) Simulate pre-market, market, post-market times using replayer
- [ ] (feat) Find a way to turn strategy into code
- [ ] (feat) Factor risk tolerance into strategy
- [ ] (feat) Setup script to automatically visualize candles and indicators
- [ ] (feat) Calculate portfolio's market value
- [ ] (feat) Calculate profitability based on portfolio and order history via various metrics
- [ ] (feat) Handle more kinds of orders (limit, stop, etc.)
- [ ] (feat) Add take-profit and stop-loss
- [ ] (feat) Send email to notify of a trading signal
    - At some point, the bot itself will be able to execute trades (not sure how at the moment though)

## v0.2
- [x] (refactor) Improve request error handling
- [x] (feat) Have bot handle and maintain a portfolio
- [x] (feat) Create a mechanism to have a persistent portfolio between runs
    - [x] Save portfolio status on program end
    - [x] Import portfolio status on program start
- [ ] (feat) Introduce the notion of a market who will responsible for the following:
    - Providing all the market data like candles
    - Making requests to provide the data
    - Validating order requests and updating the order status
- [ ] (feat) Add market orders

## v0.1
- [x] (feature) Download historical data for any ticker and any other option
- [x] (task) Gather historical data on these tickers on 1 hour
    - [x] GM
    - [x] HPQ
    - [x] INTC
    - [x] NKE
    - [x] WMT
- [x] (fix) Remove duplicate candles when paginating downloaded historical data
- [x] (refactor) Store candles as a pandas dataframe
- [x] (Replayer) Develop a candle replayer (with modifiable replay time factor)
