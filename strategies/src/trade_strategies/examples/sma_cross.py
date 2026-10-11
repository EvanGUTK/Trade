"""20/50 simple-moving-average crossover. The canonical example strategy.

Long-only. Buys a fixed quantity when the fast SMA crosses above the slow SMA,
sells it when the fast SMA crosses back below. Pure logic: no I/O, no clock,
no randomness, so every run over the same bars produces the same orders.
"""

from __future__ import annotations

from collections import deque

from trade_strategies.indicators import sma
from trade_strategies.sdk import MICRO, Bar, Context, Fill, Timeframe

type _Regime = str  # "above" | "below"


class SmaCross:
    name: str = "sma_cross"
    version: str = "0.1.0"
    symbols: list[str] = ["SPY"]  # noqa: RUF012 - deliberately shared, never mutated
    timeframe: Timeframe = "1d"

    def __init__(self, fast: int = 20, slow: int = 50, qty_micro: int = 10 * MICRO) -> None:
        if not 0 < fast < slow:
            raise ValueError("require 0 < fast < slow")
        if qty_micro <= 0:
            raise ValueError("qty_micro must be positive")
        self._fast = fast
        self._slow = slow
        self._qty_micro = qty_micro
        self._closes: deque[int] = deque(maxlen=slow)
        self._regime: _Regime | None = None

    def on_start(self, ctx: Context) -> None:
        ctx.log(f"{self.name} v{self.version}: fast={self._fast} slow={self._slow}")

    def on_bar(self, ctx: Context, bar: Bar) -> None:
        if bar.symbol != self.symbols[0]:
            return
        self._closes.append(bar.close)
        if len(self._closes) < self._slow:
            return  # warm-up

        closes = list(self._closes)
        regime: _Regime = "above" if sma(closes, self._fast) > sma(closes, self._slow) else "below"
        crossed = self._regime is not None and regime != self._regime
        self._regime = regime
        if not crossed:
            return

        held = ctx.portfolio.qty(bar.symbol)
        if regime == "above" and held <= 0:
            ctx.buy(bar.symbol, self._qty_micro)
        elif regime == "below" and held > 0:
            ctx.sell(bar.symbol, held)

    def on_fill(self, ctx: Context, fill: Fill) -> None:
        ctx.log(f"fill {fill.side} {fill.qty_micro} {fill.symbol} @ {fill.price_micro}")

    def on_stop(self, ctx: Context) -> None:
        ctx.log(f"{self.name}: stopped, equity={ctx.portfolio.equity_micro}")
