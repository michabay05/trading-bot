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
- [ ] (feat) Send email to notify of a trading signal
    - At some point, the bot itself will be able to execute trades (not sure how at the moment though).
- [ ] (feat) Add id system for orders and portfolio (seems like a good idea)
- [ ] (feat) Research and develop list of tickers for bot to trade
- [ ] (feat) Add a limit order
- [ ] (feat) Add stop order
- [ ] (feat) Bring back MACD and BBANDS indicators
- [ ] (feat) Implement indicator warm up
- [ ] (fix) Check close position logic
- [ ] (refactor) Handle edge case where position has zero quantity
    - Remove it from the list of positions
- [ ] (refactor) Change candle csv naming scheme to match that of the portfolios
- [ ] (feat) Plot P/L of portfolio - probably using matplotlib
- [ ] (refactor) Ditch lightweight charts and use the same thing 'backtesting.py' uses
    - I think it uses bokeh: [CandleStick plotting](https://docs.bokeh.org/en/latest/docs/examples/topics/timeseries/candlestick.html)
- [ ] (feat) Add market holidays to market open or closed functionality
- [ ] (feat) Add time in force for orders (DAY or Good-til-Cancelled)
- [ ] (feat) Add the notion of a trade and also FYI:
    - Trade = A completed buy-sell transaction pair
    - Position = Current market exposure (open trades)

---

# v0.6
- [x] (refactor) Fix the timescale issue on lightweight charts
    - It looks like a timezone issue
- [x] (refactor) Change broker from a list of functions to a class with methods
- [ ] (feat) Add take-profit and stop-loss
    - [x] Take profit
    - [x] Stop loss
- [x] (feat) Implement checking when market is open or closed
- [x] (feat) Add ability to buy based on portfolio's capital percentage
- [x] (refactor) Change the structure of the `Order` to use `@dataclass`
- [x] (refactor) Completely restructure the way orders are created
    - Instead of one order type, there should be one parent order type that contains all the necessary information.
      However, the user will only interact with its children (MarketOrder, LimitOrder, etc.)
- [x] (refactor) Remove `bot.py`
    - `run_bot.py` does everything I want `bot.py` to do
- [x] (feat) Setup script to automatically visualize candles and indicators
- [x] (refactor) The horizontal axis of the candle visualizer should be human-readable
    - Instead of unix timestamps, it should be human-readable date string
- [x] Experiment with alpaca-py
    - Experimenting and probing has been moved over to `alpaca-probe` branch

## v0.5
- [x] (refactor) Change Strategy to StrategyTester
    - There should be a distinction between a strategy implementation and tester
- [x] (fix) When new candle is available, it waits until the next time step to make it available
- [x] (feat) Add ability to close position
- [x] (fix) Check capital before executing order
- [x] (feat) When closing a position, keep track of P/L and P/L percentage of portfolio
- [x] (refactor) When saving to json, save P/L and P/L percentage
- [x] (feat) Implement backtest simple EMA-based strat

## v0.4
- [x] (feat) Add ability to buy or sell while developing a strategy
- [x] (feat) Implement a basic MA w/ buying and selling
- [x] (refactor) Rename 'Market' to 'Broker'
    - Broker makes a lot more sense for what I'm looking for
- [x] (fix) When executing an order, the position list must also be updated
- [x] (fix) Handle index out of bounds issue inside the crossover function
- [x] (refactor) CandleReplayer should have no knowledge of candles
- [x] (refactor) Removed MACD and BBANDS indicators

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
