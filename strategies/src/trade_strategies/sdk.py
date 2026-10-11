"""Strategy SDK: wire models and the ``Strategy`` / ``Context`` protocols.

Units follow docs/ARCHITECTURE.md §3 exactly: every money amount is an ``int`` in
micro-dollars (1 USD = 1_000_000) and every quantity is an ``int`` in micro-shares.
Timestamps are timezone-aware UTC ``datetime`` values that serialize to RFC 3339.
No floats cross this boundary, so a backtest is reproducible bit for bit.

Wire field names (``o``, ``h``, ``l``, ``c``, ``v``, ``type``) are aliases; Python
code uses the long names (``bar.close``, ``order.order_type``). Models accept
either spelling and always serialize with the wire spelling.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Final, Literal, Protocol, Self, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MICRO: Final = 1_000_000
"""Micro-units per whole unit: 1 USD = 1_000_000 micro-dollars, 1 share = 1_000_000 micro-shares."""

Side = Literal["buy", "sell"]
OrderType = Literal["market", "limit", "stop"]
TimeInForce = Literal["day", "gtc"]
Timeframe = Literal["1m", "5m", "1d"]


def to_micro(value: Decimal | int | str) -> int:
    """Convert a decimal amount (dollars or shares) to exact micro-units.

    Floats are deliberately not accepted: ``to_micro("101.25")`` is exact,
    ``to_micro(101.25)`` would not be.
    """
    scaled = Decimal(value) * MICRO
    if scaled != scaled.to_integral_value():
        raise ValueError(f"{value!r} has more than six decimal places")
    return int(scaled)


def from_micro(value: int) -> Decimal:
    """Convert micro-units back to a ``Decimal`` for display or logging only."""
    return Decimal(value) / MICRO


def _require_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware (UTC)")
    return value.astimezone(UTC)


class _Wire(BaseModel):
    """Base for every model that crosses the gateway boundary."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        validate_by_name=True,
        validate_by_alias=True,
        serialize_by_alias=True,
    )


class Bar(_Wire):
    """One OHLCV bar. Prices in micro-dollars, volume in micro-shares."""

    symbol: str = Field(min_length=1)
    t: datetime
    open: int = Field(alias="o", gt=0)
    high: int = Field(alias="h", gt=0)
    low: int = Field(alias="l", gt=0)
    close: int = Field(alias="c", gt=0)
    volume: int = Field(alias="v", ge=0)

    @field_validator("t")
    @classmethod
    def _utc(cls, value: datetime) -> datetime:
        return _require_utc(value)

    @model_validator(mode="after")
    def _range_contains_open_and_close(self) -> Self:
        lo, hi = min(self.open, self.close), max(self.open, self.close)
        if not (self.low <= lo and hi <= self.high):
            raise ValueError("bar low/high must bracket open and close")
        return self


class Order(_Wire):
    """An order request as the gateway's ``POST /sessions/{id}/orders`` expects it."""

    client_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    side: Side
    qty_micro: int = Field(gt=0)
    order_type: OrderType = Field(default="market", alias="type")
    limit_micro: int | None = Field(default=None, gt=0)
    stop_micro: int | None = Field(default=None, gt=0)
    tif: TimeInForce = "day"

    @model_validator(mode="after")
    def _prices_match_type(self) -> Self:
        match self.order_type:
            case "market":
                if self.limit_micro is not None or self.stop_micro is not None:
                    raise ValueError("market orders carry no limit or stop price")
            case "limit":
                if self.limit_micro is None:
                    raise ValueError("limit orders require limit_micro")
            case "stop":
                if self.stop_micro is None:
                    raise ValueError("stop orders require stop_micro")
        return self


class Fill(_Wire):
    """An engine ``fill`` event, as the runner delivers it to ``Strategy.on_fill``."""

    order_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    side: Side
    qty_micro: int = Field(gt=0)
    price_micro: int = Field(gt=0)
    commission_micro: int = Field(ge=0)
    t: datetime

    @field_validator("t")
    @classmethod
    def _utc(cls, value: datetime) -> datetime:
        return _require_utc(value)


class Position(_Wire):
    """One line of the portfolio. ``qty_micro`` is negative when short."""

    symbol: str = Field(min_length=1)
    qty_micro: int
    avg_cost_micro: int = Field(ge=0)
    mark_micro: int = Field(ge=0)
    unrealized_micro: int


class Portfolio(_Wire):
    """The engine's ``Portfolio`` type (docs/ARCHITECTURE.md §3)."""

    cash_micro: int
    equity_micro: int
    realized_micro: int
    positions: tuple[Position, ...] = ()

    def position(self, symbol: str) -> Position | None:
        """The open position for ``symbol``, or ``None`` when flat."""
        return next((p for p in self.positions if p.symbol == symbol), None)

    def qty(self, symbol: str) -> int:
        """Signed micro-share quantity held in ``symbol`` (0 when flat)."""
        position = self.position(symbol)
        return 0 if position is None else position.qty_micro


@runtime_checkable
class Context(Protocol):
    """What a strategy may do. The runner provides the only real implementation.

    ``buy`` and ``sell`` return the ``client_id`` of the submitted order; the
    matching ``Fill`` (or a reject) arrives later through ``Strategy.on_fill``.
    """

    @property
    def portfolio(self) -> Portfolio: ...

    def buy(
        self,
        symbol: str,
        qty_micro: int,
        *,
        order_type: OrderType = "market",
        limit_micro: int | None = None,
        stop_micro: int | None = None,
        tif: TimeInForce = "day",
    ) -> str: ...

    def sell(
        self,
        symbol: str,
        qty_micro: int,
        *,
        order_type: OrderType = "market",
        limit_micro: int | None = None,
        stop_micro: int | None = None,
        tif: TimeInForce = "day",
    ) -> str: ...

    def history(self, n: int, symbol: str | None = None) -> list[Bar]:
        """The last ``n`` bars for ``symbol`` (default: the first symbol), oldest first."""
        ...

    def log(self, message: str) -> None:
        """Append a line to the run log shown on the strategy's kanban card."""
        ...


@runtime_checkable
class Strategy(Protocol):
    """The interface every strategy implements (docs/ARCHITECTURE.md §5).

    Instances must be deterministic given the bars they receive and the seed the
    runner hands them: no wall clock, no randomness outside ``random.Random(seed)``,
    no I/O other than the ``Context``.
    """

    name: str
    version: str
    symbols: list[str]
    timeframe: Timeframe

    def on_start(self, ctx: Context) -> None: ...

    def on_bar(self, ctx: Context, bar: Bar) -> None: ...

    def on_fill(self, ctx: Context, fill: Fill) -> None: ...

    def on_stop(self, ctx: Context) -> None: ...
