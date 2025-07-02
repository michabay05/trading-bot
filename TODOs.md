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
- [ ] (rsch) Develop list of tickers for bot to trade
- [ ] (feat) Add a limit order
- [ ] (feat) Add stop order
- [ ] (feat) Bring back MACD and BBANDS indicators
- [ ] (feat) Implement indicator warm up
- [ ] (refactor) Handle edge case where position has zero quantity
    - Remove it from the list of positions
- [ ] (refactor) Change candle csv naming scheme to match that of the portfolios
- [ ] (feat) Add market holidays to market open or closed functionality
- [ ] (feat) Add time in force for orders (DAY or Good-til-Cancelled)
- [ ] (feat) Add the notion of a trade and also FYI:
    - Trade = A completed buy-sell transaction pair
    - Position = Current market exposure (open trades)
- [ ] (feat) Resize charts upon window resize
- [ ] (feat) Add PDT protection
- [ ] (feat) Implement commissions setting for Broker
- [ ] (fix) Deal with timezones when importing stockframe data from csv
- [ ] (refactor) the broker inside the strategy should handle everything related to orders and their execution
- [ ] (feat) Add legend for the following items on the candle chart:
    - [ ] Symbol
    - [ ] Indicators (also pass in function arguments as seen here: `talib.EMA(close, timeperiod=50)`)
    - [Legend example from Lightweight Charts](https://tradingview.github.io/lightweight-charts/tutorials/how_to/legends#examples)
- [ ] (fix) Instead of replacing `NaN` with `0.0` for indicators during their warmup time, use `WhiteSpaceData` in lightweight charts

---

## v0.8
- [ ] (feat) Handle warmup for live trading
- [x] (feat) Implement aggregation of dataframe, (specifically 1min to 1hr)
- [ ] (feat) Sync local portfolio with remote portfolio for live paper trading
    - [ ] Cash
    - [ ] Open positions
    - [ ] Closed positions
- [x] (feat) Add ability to update historical candle csv
- [ ] (feat) Implement the following:
    - [ ] (feat) Add functions that run on market open and market close
    - [ ] On market open, run the following:
        - [ ] Load into memory the necessary historical candle csv
        - [ ] Sync portfolio
    - [ ] On market close, run the following
        - [ ] (feat) Add daily hourly candles to the existing list of historical candles
        - [ ] (feat) Find out the next market open time
        - [ ] Sync portfolio
- [ ] (feat) Take advantage of next open and next close from alpaca's Trading clock
    - Then, I would only have to ping alpaca once a day on market open instead on every new minute bar

## v0.7
- [x] (feat) Add rendering for non-overlayed indicators like RSI, MACD
- [x] (feat) Add volume at the bottom of the main chart
- [x] (rsch) Continue experimenting with Alpaca
- [x] (feat) Add ability to consume live data
- [x] (feat) Create a live bot and run a basic strategy on it
    - [x] (feat) Add a live broker
    - [x] (feat) Add a live strategy (analagous to `StrategyTester`)
- [x] (refactor) Refactored `Candle` and `CandleOption` to use `@dataclass`
- [x] (fix) Repair replayer as it does not progress forward in some cases
    - For instance, when the time multiplier is < 1, then it progress at a rate of 0 steps per sec.
- [x] (feat) Get ~7 years worth of data using Alpaca for 30+ stocks
- [x] (feat) Implement fractional trading setting for Broker
- [x] (feat) Plot P/L of portfolio - probably using matplotlib
- [x] (refactor) Rewrite chart visualizer in typescript
- [x] (feat) Add RSI rendering into candle visualizer

## v0.6
- [x] (refactor) Fix the timescale issue on lightweight charts
    - It looks like a timezone issue
- [x] (refactor) Change broker from a list of functions to a class with methods
- [x] (feat) Add take-profit and stop-loss
    - [x] Take profit
    - [x] Stop loss
- [x] (feat) Add id system for orders and portfolio (seems like a good idea)
- [x] (feat) Implement checking when market is open or closed
- [x] (feat) Add ability to buy based on portfolio's capital percentage
- [x] (refactor) Change the structure of the `Order` to use `@dataclass`
- [x] (refactor) Completely restructure the way orders are created
    - Instead of one order type, there should be one parent order type that contains all the necessary
      information. However, the user will only interact with its children (MarketOrder, LimitOrder, etc.)
- [x] (refactor) Remove `bot.py`
    - `run_bot.py` does everything I want `bot.py` to do
- [x] (feat) Setup script to automatically visualize candles and indicators
- [x] (refactor) The horizontal axis of the candle visualizer should be human-readable
    - Instead of unix timestamps, it should be human-readable date string
- [x] (rsch) Experiment with alpaca-py
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
