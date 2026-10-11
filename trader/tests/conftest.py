from __future__ import annotations

import pytest

TRADER_ENV = ("ANTHROPIC_API_KEY", "TRADER_MODEL", "TRADE_DATA_DIR")


@pytest.fixture(autouse=True)
def _clean_trader_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests must not see the developer's shell: no key, no model override, no data dir."""
    for name in TRADER_ENV:
        monkeypatch.delenv(name, raising=False)
