from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from trade_trader import DEFAULT_MODEL
from trade_trader.config import TraderSettings


def test_defaults_need_no_key() -> None:
    settings = TraderSettings()
    assert settings.anthropic_api_key is None
    assert settings.has_api_key is False
    assert settings.trader_model == DEFAULT_MODEL == "claude-opus-5-5"
    assert settings.memory_dir == Path("data") / "trader" / "memory"


def test_env_overrides_and_key_is_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-not-real")
    monkeypatch.setenv("TRADER_MODEL", "claude-opus-5-5")
    monkeypatch.setenv("TRADE_DATA_DIR", "/tmp/trade-data")
    settings = TraderSettings()
    assert settings.has_api_key is True
    assert settings.memory_dir == Path("/tmp/trade-data/trader/memory")
    assert "sk-ant" not in repr(settings)
    assert "sk-ant" not in str(settings.anthropic_api_key)


def test_date_suffixed_model_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRADER_MODEL", "claude-opus-5-5-20260401")
    with pytest.raises(ValidationError, match="date suffix"):
        TraderSettings()
    monkeypatch.setenv("TRADER_MODEL", "  ")
    with pytest.raises(ValidationError, match="empty"):
        TraderSettings()
