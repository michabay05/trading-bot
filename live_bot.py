from trbot.broker import LiveBroker
from trbot.strategy import LiveStrategy

class MyLiveStrat(LiveStrategy):
    def setup(self) -> None:
        close = self.close_series
        high = self.high_series
        low = self.low_series

        self.fast_ma = self.TA_EMA(close, period=5)
        self.slow_ma = self.TA_EMA(close, period=10)
        self.atr = self.TA_ATR(high, low, close, period=14)

        self.start: bool = False
        self.max_warmup = 14
        if len(close) >= self.max_warmup:
            self.start = True

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
        if not self.start:
            print("Still in warm up phase")
            return

        last_atr = self.last_ind_value(self.atr)
        sz: float = 0.1
        if self.ind_crossover(self.fast_ma, self.slow_ma):
            (tp, sl) = self.calc_tp_sl(last_atr, long=True)
            # sl = self.last_close - 5*last_atr
            # tp = self.last_close + 10*last_atr
            self.market_buy(size=sz, tp_limit=tp, sl_limit=sl)
            print("Going long...\n\n")

        if self.ind_crossover(self.slow_ma, self.fast_ma):
            (tp, sl) = self.calc_tp_sl(last_atr, long=False)
            # sl = self.last_close + 5*last_atr
            # tp = self.last_close - 10*last_atr
            self.market_sell(size=sz, tp_limit=tp, sl_limit=sl)
            print("Going short...\n\n")


# ls = MyLiveStrat()
# try:
#     ls.run()
# finally:
#     ls.test()

from datetime import datetime
lb = LiveBroker()
st = datetime.fromisoformat("2025-06-24 09:00:00+00:00")
lb.get_historical_candles(["DELL"], start=st)
print(f"[DELL] {st} -> {datetime.now()}")
