"""Process configuration for the Trader, read from the environment.

Field names map to environment variables case-insensitively (pydantic-settings):
``ANTHROPIC_API_KEY``, ``TRADER_MODEL``, ``TRADE_DATA_DIR``. Keys live in ``.env``
(gitignored); ``make trader-run`` passes it with ``uv run --env-file``. Nothing
here reads ``.env`` directly, so tests see only what they set.
"""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from trade_trader import DEFAULT_MODEL

_DATE_SUFFIX = re.compile(r"-\d{8}$")


class TraderSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", frozen=True)

    anthropic_api_key: SecretStr | None = None
    """The Trader's own key. ``None`` is allowed so that tests and dry runs never need one."""

    trader_model: str = DEFAULT_MODEL
    """Exact model id (root CLAUDE.md §7). Date-suffixed ids are rejected."""

    trade_data_dir: Path = Path("data")
    """Runtime data root (docs/ARCHITECTURE.md §9). The Makefile defaults it to ``<repo>/data``."""

    @field_validator("trader_model")
    @classmethod
    def _model_id(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("TRADER_MODEL must not be empty")
        if _DATE_SUFFIX.search(value):
            raise ValueError("TRADER_MODEL must not carry a date suffix (root CLAUDE.md §7)")
        return value

    @property
    def memory_dir(self) -> Path:
        """Root of the memory tool's filesystem backend: ``<TRADE_DATA_DIR>/trader/memory``."""
        return self.trade_data_dir / "trader" / "memory"

    @property
    def has_api_key(self) -> bool:
        return self.anthropic_api_key is not None and bool(
            self.anthropic_api_key.get_secret_value()
        )
