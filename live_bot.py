from datetime import datetime
import os

from trbot.strategy import Indicator, LiveStrategy
from trbot.portfolio import TBMarketOrder, TBOrderAmount
from trbot import log, util

class TrendFollowingStrat(LiveStrategy):
    def setup(self) -> None:
        self.fast_ma = self.add_indicator(
            Indicator(kind="ema", part=["close"], period=5)
        )
        self.slow_ma = self.add_indicator(
            Indicator(kind="ema", part=["close"], period=35)
        )
        self.atr = self.add_indicator(
            Indicator(kind="atr", part=["high", "low", "close"], period=14)
        )

    def calc_tp_sl(self, last_close: float, last_atr: float, long: bool,
        rr_ratio: int = 10
    ) -> tuple[float, float]:
        sl: float = 0.0
        tp: float = 0.0
        diff: float = last_atr
        if long:
            sl = last_close - diff
            tp = last_close + (rr_ratio * diff)
        else:
            sl = last_close + diff
            tp = last_close - (rr_ratio * diff)

        return (tp, sl)

    def on_candle(self, symbol: str) -> TBMarketOrder | None:
        last_atr = self.last_ind_value(symbol, self.atr)
        price = self.current_price(symbol)
        sz: TBOrderAmount = TBOrderAmount.cash_pct(0.3)

        if self.ind_crossover(symbol, self.fast_ma, self.slow_ma):
            (tp, sl) = self.calc_tp_sl(price, last_atr, long=True)
            # sl = self.last_close - 5*last_atr
            # tp = self.last_close + 10*last_atr
            log.debug(f"{symbol}: Going long...\n\n")
            return self.market_buy(symbol, size=sz, tp_limit=tp, sl_limit=sl)
        elif self.ind_crossover(symbol, self.slow_ma, self.fast_ma):
            (tp, sl) = self.calc_tp_sl(price, last_atr, long=False)
            # sl = self.last_close + 5*last_atr
            # tp = self.last_close - 10*last_atr
            log.debug(f"{symbol}: Going short...\n\n")
            return self.market_sell(symbol, size=sz, tp_limit=tp, sl_limit=sl)


dir = "trout"
for subdir in [ "aggs", "logs", "ohlcv-1hr", "pfts" ]:
    os.makedirs(f"{dir}/{subdir}", exist_ok=True)

dt_str = datetime.now(tz=util.MY_TIMEZONE).strftime("%Y_%m_%d")
log.init(
    log_output_dir=f"trout/logs/{dt_str}"
)

symbols: list[str] = [
    "GE", "HPQ", "EBAY", "XLF", "GE", "GOOG", "SPY", "AAPL",
    "PEP", "LOGI", "INTC", "TGT", "WMT", "NIO", "HIMS", "AMZN"
]

ls = TrendFollowingStrat(
    acct_name="Alpaca Bot", data_source="alpaca",
    symbols=symbols.copy()
)
try:
    ls.start()
except KeyboardInterrupt:
    log.error("Received keyboard interrupt, ctrl-c...")

