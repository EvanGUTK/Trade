from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from trade_strategies import MICRO, Bar, Context, Strategy
from trade_strategies.examples.sma_cross import SmaCross
from trade_strategies.testing import RecordingContext

START = datetime(2024, 1, 1, tzinfo=UTC)


def synthetic_series(symbol: str = "SPY") -> list[Bar]:
    """60 flat bars, 40 rising, 60 falling: exactly one up-cross then one down-cross."""
    prices = [100] * 60 + [100 + 3 * i for i in range(1, 41)] + [220 - 3 * i for i in range(1, 61)]
    bars: list[Bar] = []
    for i, dollars in enumerate(prices):
        px = dollars * MICRO
        bars.append(
            Bar(
                symbol=symbol,
                t=START + timedelta(days=i),
                open=px,
                high=px,
                low=px,
                close=px,
                volume=MICRO,
            )
        )
    return bars


def test_example_satisfies_the_protocols() -> None:
    assert isinstance(SmaCross(), Strategy)
    assert isinstance(RecordingContext(), Context)


def test_emits_a_buy_then_a_sell_on_the_synthetic_series() -> None:
    ctx = RecordingContext()
    ctx.run(SmaCross(), synthetic_series())

    assert [o.side for o in ctx.orders] == ["buy", "sell"]
    assert all(o.symbol == "SPY" and o.order_type == "market" for o in ctx.orders)
    assert ctx.orders[0].qty_micro == 10 * MICRO
    assert ctx.orders[1].qty_micro == 10 * MICRO
    assert ctx.portfolio.qty("SPY") == 0
    assert ctx.portfolio.realized_micro > 0
    assert len(ctx.fills) == 2
    assert any(log.startswith("fill buy") for log in ctx.logs)


def test_is_deterministic() -> None:
    first, second = RecordingContext(), RecordingContext()
    first.run(SmaCross(), synthetic_series())
    second.run(SmaCross(), synthetic_series())
    assert first.orders == second.orders
    assert first.portfolio == second.portfolio


def test_ignores_other_symbols_and_rejects_bad_windows() -> None:
    ctx = RecordingContext()
    ctx.run(SmaCross(), synthetic_series(symbol="QQQ"))
    assert ctx.orders == []
    with pytest.raises(ValueError, match="fast < slow"):
        SmaCross(fast=50, slow=20)


def test_history_returns_most_recent_bars_oldest_first() -> None:
    ctx = RecordingContext()
    bars = synthetic_series()[:5]
    for bar in bars:
        ctx.push(bar)
    assert ctx.history(3) == bars[-3:]
    assert ctx.history(0) == []
