from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from trade_strategies import MICRO, Bar, Order, Portfolio, Position, from_micro, to_micro

T0 = datetime(2024, 1, 2, 14, 30, tzinfo=UTC)


def test_micro_round_trip() -> None:
    assert to_micro("101.25") == 101_250_000
    assert to_micro(3) == 3 * MICRO
    assert from_micro(101_250_000) == Decimal("101.25")


def test_to_micro_rejects_sub_micro_precision() -> None:
    with pytest.raises(ValueError, match="six decimal"):
        to_micro("0.0000001")


def test_bar_accepts_wire_names_and_serializes_them() -> None:
    wire = {
        "symbol": "SPY",
        "t": "2024-01-02T14:30:00Z",
        "o": 100,
        "h": 110,
        "l": 90,
        "c": 105,
        "v": 7,
    }
    bar = Bar.model_validate(wire)
    assert bar.close == 105
    assert bar.t == T0
    assert bar.model_dump(mode="json") == wire


def test_bar_rejects_naive_timestamp_and_bad_range() -> None:
    naive = datetime(2024, 1, 2)
    with pytest.raises(ValidationError, match="timezone-aware"):
        Bar(symbol="SPY", t=naive, open=1, high=1, low=1, close=1, volume=0)
    with pytest.raises(ValidationError, match="bracket"):
        Bar(symbol="SPY", t=T0, open=100, high=101, low=99, close=150, volume=0)


def test_order_validation_by_type() -> None:
    market = Order(client_id="c1", symbol="SPY", side="buy", qty_micro=MICRO)
    assert market.model_dump()["type"] == "market"
    with pytest.raises(ValidationError, match="qty_micro"):
        Order(client_id="c1", symbol="SPY", side="buy", qty_micro=0)
    with pytest.raises(ValidationError, match="limit_micro"):
        Order(client_id="c1", symbol="SPY", side="buy", qty_micro=MICRO, order_type="limit")
    with pytest.raises(ValidationError, match="stop_micro"):
        Order(client_id="c1", symbol="SPY", side="sell", qty_micro=MICRO, order_type="stop")
    with pytest.raises(ValidationError, match="no limit or stop"):
        Order(client_id="c1", symbol="SPY", side="buy", qty_micro=MICRO, limit_micro=5)
    with pytest.raises(ValidationError, match="extra"):
        Order.model_validate(
            {"client_id": "c1", "symbol": "SPY", "side": "buy", "qty_micro": 1, "live": True}
        )


def test_portfolio_lookup() -> None:
    pos = Position(
        symbol="SPY", qty_micro=2 * MICRO, avg_cost_micro=100, mark_micro=110, unrealized_micro=20
    )
    portfolio = Portfolio(cash_micro=1, equity_micro=1, realized_micro=0, positions=(pos,))
    assert portfolio.qty("SPY") == 2 * MICRO
    assert portfolio.qty("QQQ") == 0
    assert portfolio.position("QQQ") is None
