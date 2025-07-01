import time
from trbot.candles import Timespan
from trbot.stockframe import Stockframe
from trbot.strategy import StrategyTester
import visualize_candles as vs_cd


# ===================== STRATEGY =====================
class MyStrategy(StrategyTester):
    def setup(self) -> None:
        close = self._sf.close_series
        high = self._sf.high_series
        low = self._sf.low_series
        self.fast_ma = self.TA_EMA(close, period=100)
        self.slow_ma = self.TA_EMA(close, period=200)
        self.atr = self.TA_ATR(high, low, close, period=14)

        self.rr_ratio = 10

    def calc_tp_sl(self, last_atr: float, long: bool) -> tuple[float, float]:
        sl: float = 0.0
        tp: float = 0.0
        diff: float = last_atr
        if long:
            sl = self.last_close - diff
            tp = self.last_close + (self.rr_ratio * diff)
        else:
            sl = self.last_close + diff
            tp = self.last_close - (self.rr_ratio * diff)

        return (tp, sl)

    def on_candle(self) -> None:
        last_atr = self.last_ind_value(self.atr)
        sz: float = 0.1
        tp: float
        sl: float
        if self.ind_crossover(self.fast_ma, self.slow_ma):
            (tp, sl) = self.calc_tp_sl(last_atr, long=True)
            # sl = self.last_close - 5*last_atr
            # tp = self.last_close + 10*last_atr
            self.market_buy(size=sz, tp_limit=tp, sl_limit=sl)

        if self.ind_crossover(self.slow_ma, self.fast_ma):
            (tp, sl) = self.calc_tp_sl(last_atr, long=False)
            # sl = self.last_close + 5*last_atr
            # tp = self.last_close - 10*last_atr
            self.market_sell(size=sz, tp_limit=tp, sl_limit=sl)


start_time: float = time.time()
# tickers: list[str] = vs_cd.valid_tickers("trout/aggs")[0]
tickers: list[str] = ["GOOG"]
sum: float = 0.0
for t in tickers:
    sf: Stockframe = Stockframe.from_csv(f"ohlcv-1hr/{t}.csv", t, 1, Timespan.HOUR)
    mys = MyStrategy(sf)
    try:
        output = mys.run()
        print(f"{t}: {output["pl"]}")
        sum += output["pl"]
    finally:
        mys.export_portfolio("trout/pfts")
        mys.plot_pl(filepath="overall_pl.png")

print("----------------------")
print(f"Total: {sum}")
diff: float = time.time() - start_time
print(f"Took {diff:.3f}s to backtest {len(tickers)} symbols")



# ===================== HISTORICAL CANDLES =====================
# for ticker in [
#     "WMT", "INTC", "HPQ", "NKE", "GM", "TGT", "BBY", "SMCI", "SKX", "UAA", "PUMSY", "F", "HMC",
#     "KR", "M", "LNVGY", "KHC", "GIS", "BYND", "GAP"
# ]:
#     opt: CandleOption = CandleOption(
#         ticker=ticker,
#         start="2023-06-15 10:00:00",
#         end="2025-06-13 16:00:00",
#         mult=4,
#         timespan=Timespan.HOUR
#     )
#     cnds: list[Candle] = broker.get_historical_candles(opt)
#     sf: Stockframe = Stockframe(cnds, opt.ticker, opt.mult, opt.timespan)
#     sf.to_csv("trout/aggs")

#     print(f"Completed downloading for {ticker}")
#     print("-----------------------")
