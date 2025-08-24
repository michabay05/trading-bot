# TODOs
A list of all the TODOs needed to be completed before each release

## Questions to research
- Why are there are differences in the data between polygon.io, webull, and tradingview?
- Research better sources for live market data streaming (list here)
    - Interactive brokers
    - Alpaca (current choice)
    - Alphavantage
- Research a trading platform that would allow the bot to make automated trading decision
    - Webull (their API does not work anymore)
    - Alpaca (current choice)
    - Robinhood
    - Interactive brokers
- Pattern Day Trading??
    - Definition: "A pattern day trader (PDT) is a regulatory designation for those traders or
      investors who execute four or more day trades over the span of five business days using a
      margin account. The number of day trades must constitute more than 6% of the margin account's
      total trade activity during that five-business-day window."
- Research "A fluid stop loss candlestick structure"

## Future versions
- [ ] (feat) Factor risk tolerance into strategy
- [ ] (feat) Send email to notify of a trading signal
    - At some point, the bot itself will be able to execute trades (not sure how at the moment though).
- [ ] (feat) Add a limit order
- [ ] (feat) Add stop order
- [ ] (feat) Bring back MACD and BBANDS indicators
- [ ] (refactor) Handle edge case where position has zero quantity
    - Remove it from the list of positions
- [ ] (refactor) Change candle csv naming scheme to match that of the portfolios
- [ ] (feat) Add time in force for orders (DAY or Good-til-Cancelled)
- [ ] (feat) Resize charts upon window resize
- [ ] (feat) Implement commissions setting for Broker
- [ ] (fix) Deal with timezones when importing stockframe data from csv
- [ ] (refactor) the broker inside the strategy should handle everything related to orders and their execution
- [ ] (feat) Add legend for the following items on the candle chart:
    - [ ] Symbol
    - [ ] Indicators (also pass in function arguments as seen here: `talib.EMA(close, timeperiod=50)`)
    - [Legend example from Lightweight Charts](https://tradingview.github.io/lightweight-charts/tutorials/how_to/legends#examples)
- [ ] (feat) Consider replacing my custom backtester with either one of these python libraries
    - `backtesting.py`
    - `vectorbt`
- [ ] (refactor) Update the indicator system in the candle visualizer to use the `Indicator` type
- [ ] (rsch) Experiment with yahoo finance data
- [ ] (feat) Extract data stream into its own data source system
    - This setup makes it easier to use add Yahoo finance data at some point
- [ ] (feat) Setup a script that can automatically detect new commits from github and update this bot on market close
- [ ] (fix) Handle missing candle values
    - As it stands, if the bot was stopped for some reason at 10:25 and is restarted at 13:25, there will be a 3-hour gap in the data.
- [ ] (feat) Add configurable candle generator with these parameters
    - [ ] Random movement
    - [ ] Candles w/ tendency to go up (>50% chance of going up)
    - [ ] Candles w/ tendency to go down (>50% chance of going down)
- [ ] (feat) Add more tests based on the random candle generator
- [ ] (feat) Create an additional script to make sense of all the logs and portfolio saved as files.

---

## v0.11
Currently, the laws pertaining to PDT are something I am forced to bother myself with.

- [x] (feat) Added distinction between absolute shares, absolute notional amounts, and relative portfolio percentage
- [x] (refactor) Move blacklisting from `strategy.py` to `broker.py`
- [x] (fix) Ensure that tp limits are at least a penny more/less than the market price
- [x] (fix) Ensure that sl limits are at least a penny less/more than the market price
- [ ] (feat) Implement a way to limit the frequency with which the bot trades (buys and sells, and vice versa)
    - This is purely to comply with the PDT rules. The way it currently works is as intended (for the future).
- [x] (fix) Handle API related errors which prevent hourly update from taking place for other stocks
    - The hourly update ceases the moment an error or exception is triggered.
- [x] (fix) Adjust new timespan detection system
- [x] (rsch) Look into alpaca's `TradingStream` and what updates it could provide
    - It provides various events I could subscribe to like `new`, `fill`
- [x] (fix) Added immediate creation of important output directories on startup
    - If the repo was just cloned, the important directories inside `trout` won't be created
      automatically causing an OSError because those directories are not created by default.
- [x] (refactor) Manually execute take profit and stop losses
- [ ] (refactor) Compare local vs remote version of portfolio
- [x] (feat) Add the notion of a trade and also FYI:
    - Trade = A completed buy-sell transaction pair
    - Position = Current market exposure (open trades)

## v0.10
- [x] (feat) Add Yahoo as an official data source
    - [x] Convert price points to a single minute candle
    - [x] Provide callback when a single minute candle is aggregated
- [x] (refactor) Extract alpaca data stream from broker to its own thing
- [x] (refactor) Reimplement the existing strategy system to use the new datafeed system
- [x] (refactor) Restructure stockframe such that it can adapt to a single or multiple symbols
    - This ended up being two different objects one for a single symbol and the other for multiple
- [x] (refactor) Standardized dataframe structure between multiple data sources
- [x] (refactor) Remove all the old code related to my historical backtester
    - [x] Polygon-io stuff
    - [x] Candle replayer
    - [x] Strategy tester
    - [x] Historical broker
- [x] (refactor) Add notion of amount of cash into strategy system
    - No money = Don't send order
- [x] (feat) Export portfolio on market close
    - This will eventually be used to compute daily performance metrics.
- [x] (feat) Add a second bot that uses Yahoo Finance as a data source
- [x] (feat) Consider replacing my custom backtester with either one of these python libraries
    - `backtesting.py`
    - `vectorbt` (Chosen as replacement)
- [x] (fix) Logging error (it overwrote `logs.txt` instead of appending to it)
- [x] (refactor) Add blacklisting of stocks for a single day trade
- [ ] (feat) Implement the following strategies using the chosen backtesting library
    - [ ] Trend following system
    - [ ] Mean reversion

## v0.9
- [x] (fix) Instead of replacing `NaN` with `0.0` for indicators during their warmup time, use `WhiteSpaceData` in lightweight charts
- [x] (rsch) Understand what 'PDT' means...exactly
    - Research PDT using these sources
        - [FINRA's official definition of PDT](https://www.finra.org/investors/investing/investment-products/stocks/day-trading)
        - [Alpaca's FAQ about PDT](https://alpaca.markets/support/pattern-day-trading-protection)
        - [Alpaca's docs about PDT protection](https://docs.alpaca.markets/docs/user-protection)
- [x] (feat) Add market holidays to market open or closed functionality
    - This is accomplished through alpaca's `next open` and `next close` functionality
- [x] (rsch) Develop list of tickers for bot to trade
- [x] (feat) Export data gathered throughout the market data
- [x] (refactor) Rewrite candle visualizer better with correct typescript stuff
    - The lack of types is driving me insane.
    - In the next version, `charts-v2` will officially replaced by the old `charts`.
- [x] (feat) Introduce ability to change symbol without having to re-export new values
- [x] (feat) Integrate `visualize candles` into `trbot` as `visualizer`.
- [x] (fix) Handle errors related to export daily (on_market_close) data
    - `ERROR: Folder 'trout/logs/...' already exists`
- [x] (fix) Handle errors related to export live data ... live
    - [x] `ERROR: Object '...' is not JSON serializable`
- [x] (refactor) Implement my own custom logging system that accomplishes the following:
    - [x] Both printing and saving to a file w/ config to enable or disable it
        - 'file' can mean sys.stdout or a regular file
    - [x] Colored output w/ config to enable or disable it
    - [x] Various modes: error, warning, info, debug w/ config to set minimum level

## v0.8
- [x] (feat) Handle warmup for live trading
- [x] (fix) Restructure indicator value storage mechanism
    - The old system was based on the historical backtester, which caused the live strategy to miss
      trading opportunities.
- [x] (feat | fix) Live data parsing
    - Instead of appending to a dataframe, append to a list. Adding the candles to a dataframe will
      happen on market close.
- [x] (feat) Implement aggregation of candle data (specifically 1min to 1hr)
- [x] (feat) Sync local portfolio with remote portfolio for live paper trading
    - [x] Cash
    - [x] Open orders
    - [x] Open positions
- [x] Sync positions every time a position is a LONG or SHORT order is created
- [x] (feat) Add ability to update historical candle csv
- [x] (feat) Implement the following:
    - [x] (feat) Add functions that run on market open and market close
    - [x] On market open, run the following:
        - [x] Setup indicators used in strategy
        - [x] Load into memory the necessary historical candle csv
    - [x] On market close, run the following
        - [x] (feat) Brings historical data up to date
        - [x] (feat) Find out the next market open time and sleep until then
- [x] (feat) Using alpaca's next open, make the bot sleep until the next market open
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
- [x] (feat) Develop a candle replayer (with modifiable replay time factor)
