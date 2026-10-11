"""Indicator helpers. Pure functions over integer micro-unit series.

Return ``Fraction`` rather than ``float`` so that two runs over the same bars
compare identically on every machine. Convert at the edge if you must display.
"""

from __future__ import annotations

from collections.abc import Sequence
from fractions import Fraction


def sma(values: Sequence[int], n: int) -> Fraction:
    """Simple moving average of the last ``n`` values.

    Raises ``ValueError`` when fewer than ``n`` values are available; callers
    should wait for the warm-up period rather than trade on a partial window.
    """
    if n <= 0:
        raise ValueError("window must be positive")
    if len(values) < n:
        raise ValueError(f"need {n} values, have {len(values)}")
    window = values[-n:]
    return Fraction(sum(window), n)
