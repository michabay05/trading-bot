# TODOs
A list of all the TODOs needed to be completed before each release

## Questions to research
- Why are there are differences in the data between polygon.io, webull, and tradingview?
- Research better sources for live market data streaming (list here)
    - Interactive brokers
    - Alpaca
    - Alphavantage
- Research a trading platform that would allow the bot to make automated trading decision
    - Webull (their API does not work anymore)
    - Robinhood
    - Interactive brokers
- Pattern Day Trading??

## Future versions
- [ ] (feat) Factor risk tolerance into strategy
- [ ] (feat) Setup script to automatically visualize candles and indicators
- [ ] (feat) Calculate portfolio's market value
- [ ] (feat) Calculate profitability based on portfolio and order history via various metrics
- [ ] (feat) Send email to notify of a trading signal
    - At some point, the bot itself will be able to execute trades (not sure how at the moment though).
- [ ] (feat) Add id system for orders and portfolio (seems like a good idea)
- [ ] (feat) Add more technical indicators, as needed
- [ ] (feat) Research and develop list of tickers for bot to trade
- [ ] (feat) Add stop order
- [ ] (feat) Add ability to buy based on portfolio's capital percentage
- [ ] (feat) Add strategy tester
    - There should be a distinction between a strategy implementation and tester
- [ ] (feat) Integrate strategy into bot's decision making
- [ ] (feat) Implement checking when market is open or closed

## v0.4
- [ ] (feat) Add ability to buy or sell while developing a strategy
- [x] (refactor) Rename 'Market' to 'Broker'
    - Broker makes a lot more sense for what I'm looking for
- [x] (fix) When executing an order, the position list must also be updated
- [x] (fix) Handle index out of bounds issue inside the crossover function
- [ ] (feat) Add a limit order
- [ ] (feat) Add take-profit and stop-loss

## v0.3
- [x] (feat) Find a way to turn strategy into code
- [x] (feat) Implement a basic moving average crossover strategy
- [x] (feat) Calculate the following indicators (using the stockframe and the `TA-lib` library)
    - SMA
    - EMA
    - RSI
    - MACD
    - BBANDS
- [x] (refactor) Remove all attribute access without `@property` decorator and add properties with this decorator

## v0.2
- [x] (refactor) Improve request error handling
- [x] (feat) Have bot handle and maintain a portfolio
- [x] (feat) Create a mechanism to have a persistent portfolio between runs
    - [x] Save portfolio status on program end
    - [x] Import portfolio status on program start
- [x] (feat) Introduce the notion of a market who will responsible for the following:
    - [x] Providing all the market data like candles
    - [x] Making requests to provide the data
    - [x] Validating order requests and updating the order status
- [x] (feat) Add market orders
- [x] (feat) Simulate real time using replayer instead giving the next candle after a certain delay
    - This affects how the bot perceives weekends and market holidays

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
