from datetime import datetime
import os

from trbot.strategy import Indicator, LiveStrategy
from trbot.portfolio import TBMarketReq, TBOrderAmount
from trbot import log, util

class TrendFollowingStrat(LiveStrategy):
    def setup(self) -> None:
        self.fast_ma: str = self.add_indicator(
            Indicator(kind="ema", part=["close"], period=5)
        )
        self.slow_ma: str = self.add_indicator(
            Indicator(kind="ema", part=["close"], period=35)
        )
        self.atr: str = self.add_indicator(
            Indicator(kind="atr", part=["high", "low", "close"], period=14)
        )

    def calc_tp_sl(self, last_close: float, last_atr: float, long: bool,
        rr_ratio: int = 2
    ) -> tuple[float, float]:
        sl: float = 0.0
        tp: float = 0.0
        diff: float = 2 * last_atr
        if long:
            sl = last_close - diff
            tp = last_close + (rr_ratio * diff)
        else:
            sl = last_close + diff
            tp = last_close - (rr_ratio * diff)

        return (tp, sl)

    def on_candle(self, symbol: str) -> TBMarketReq | None:
        # If there's an open position with the current symbol, then do . . .
        position = self.get_position(symbol)
        if position is not None:
            pass

        last_atr = self.last_ind_value(symbol, self.atr)
        price = self.current_price(symbol)
        sz: TBOrderAmount = TBOrderAmount.cash_pct(0.3, self.available_cash)

        if self.ind_crossover(symbol, self.fast_ma, self.slow_ma):
            (tp, sl) = self.calc_tp_sl(price, last_atr, long=True)
            log.debug(f"{symbol}: Going long...\n\n")
            return self.market_buy(symbol, size=sz, tp_limit=tp, sl_limit=sl)
        elif self.ind_crossover(symbol, self.slow_ma, self.fast_ma):
            (tp, sl) = self.calc_tp_sl(price, last_atr, long=False)
            log.debug(f"{symbol}: Going short...\n\n")
            return self.market_sell(symbol, size=sz, tp_limit=tp, sl_limit=sl)


symbols: list[str] = [
    "GE", "HPQ", "EBAY", "XLF", "GE", "GOOG", "SPY", "AAPL",
    "PEP", "LOGI", "INTC", "TGT", "WMT", "NIO", "HIMS", "AMZN"
]

ls = TrendFollowingStrat(
    acct_name="Alpaca Bot 03",
    symbols=symbols.copy(), paper=True
)

try:
    ls.start_loop()
except KeyboardInterrupt:
    log.error("Received keyboard interrupt, ctrl-c...")
    log.info("Shutting down")
    ls.shutdown()
    log.info("Complete ... Goodbye!")

