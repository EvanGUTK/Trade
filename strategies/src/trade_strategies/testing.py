"""An in-memory ``Context`` for unit-testing strategy logic.

``RecordingContext`` is *not* the engine. It fills every order instantly at the
last close of the symbol, charges no commission, applies no slippage, rejects
nothing, and supports long positions only. Use it to assert *which* orders a
strategy emits on a known series; use a backtest session for anything about money.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from trade_strategies.sdk import (
    MICRO,
    Bar,
    Fill,
    Order,
    OrderType,
    Portfolio,
    Position,
    Side,
    Strategy,
    TimeInForce,
)


class RecordingContext:
    def __init__(self, cash_micro: int = 100_000 * MICRO) -> None:
        self._cash = cash_micro
        self._realized = 0
        self._qty: dict[str, int] = defaultdict(int)
        self._avg_cost: dict[str, int] = defaultdict(int)
        self._bars: dict[str, list[Bar]] = defaultdict(list)
        self._default_symbol: str | None = None
        self._pending: list[Fill] = []
        self._seq = 0
        self.orders: list[Order] = []
        self.fills: list[Fill] = []
        self.logs: list[str] = []

    # -- driving -------------------------------------------------------------

    def run(self, strategy: Strategy, bars: Iterable[Bar]) -> None:
        """Drive ``strategy`` through ``bars``: start, each bar (then its fills), stop."""
        self._default_symbol = strategy.symbols[0]
        strategy.on_start(self)
        for bar in bars:
            self.push(bar)
            strategy.on_bar(self, bar)
            while self._pending:
                strategy.on_fill(self, self._pending.pop(0))
        strategy.on_stop(self)

    def push(self, bar: Bar) -> None:
        """Record a bar so ``history`` and ``portfolio`` marks see it."""
        self._bars[bar.symbol].append(bar)
        if self._default_symbol is None:
            self._default_symbol = bar.symbol

    # -- Context -------------------------------------------------------------

    @property
    def portfolio(self) -> Portfolio:
        positions: list[Position] = []
        equity = self._cash
        for symbol, qty in self._qty.items():
            if qty == 0:
                continue
            mark = self._last_close(symbol)
            value = qty * mark // MICRO
            equity += value
            positions.append(
                Position(
                    symbol=symbol,
                    qty_micro=qty,
                    avg_cost_micro=self._avg_cost[symbol],
                    mark_micro=mark,
                    unrealized_micro=value - qty * self._avg_cost[symbol] // MICRO,
                )
            )
        return Portfolio(
            cash_micro=self._cash,
            equity_micro=equity,
            realized_micro=self._realized,
            positions=tuple(positions),
        )

    def buy(
        self,
        symbol: str,
        qty_micro: int,
        *,
        order_type: OrderType = "market",
        limit_micro: int | None = None,
        stop_micro: int | None = None,
        tif: TimeInForce = "day",
    ) -> str:
        return self._submit("buy", symbol, qty_micro, order_type, limit_micro, stop_micro, tif)

    def sell(
        self,
        symbol: str,
        qty_micro: int,
        *,
        order_type: OrderType = "market",
        limit_micro: int | None = None,
        stop_micro: int | None = None,
        tif: TimeInForce = "day",
    ) -> str:
        return self._submit("sell", symbol, qty_micro, order_type, limit_micro, stop_micro, tif)

    def history(self, n: int, symbol: str | None = None) -> list[Bar]:
        key = symbol or self._default_symbol
        if key is None:
            return []
        return self._bars[key][-n:] if n > 0 else []

    def log(self, message: str) -> None:
        self.logs.append(message)

    # -- internals -----------------------------------------------------------

    def _last_close(self, symbol: str) -> int:
        bars = self._bars[symbol]
        if not bars:
            raise ValueError(f"no bars seen for {symbol}")
        return bars[-1].close

    def _submit(
        self,
        side: Side,
        symbol: str,
        qty_micro: int,
        order_type: OrderType,
        limit_micro: int | None,
        stop_micro: int | None,
        tif: TimeInForce,
    ) -> str:
        self._seq += 1
        client_id = f"rec-{self._seq}"
        order = Order(
            client_id=client_id,
            symbol=symbol,
            side=side,
            qty_micro=qty_micro,
            order_type=order_type,
            limit_micro=limit_micro,
            stop_micro=stop_micro,
            tif=tif,
        )
        self.orders.append(order)
        price = self._last_close(symbol)
        self._apply(side, symbol, qty_micro, price)
        fill = Fill(
            order_id=client_id,
            symbol=symbol,
            side=side,
            qty_micro=qty_micro,
            price_micro=price,
            commission_micro=0,
            t=self._bars[symbol][-1].t,
        )
        self.fills.append(fill)
        self._pending.append(fill)
        return client_id

    def _apply(self, side: Side, symbol: str, qty_micro: int, price_micro: int) -> None:
        notional = qty_micro * price_micro // MICRO
        held = self._qty[symbol]
        if side == "buy":
            self._avg_cost[symbol] = (held * self._avg_cost[symbol] + qty_micro * price_micro) // (
                held + qty_micro
            )
            self._qty[symbol] = held + qty_micro
            self._cash -= notional
        else:
            if qty_micro > held:
                raise ValueError("RecordingContext supports long positions only")
            self._realized += qty_micro * (price_micro - self._avg_cost[symbol]) // MICRO
            self._qty[symbol] = held - qty_micro
            self._cash += notional
