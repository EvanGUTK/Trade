from __future__ import annotations

import pytest

from trade_mcp import DEFAULT_PORT
from trade_mcp.__main__ import build_parser, resolve_port


def test_port_defaults_and_env_override() -> None:
    assert resolve_port({}) == DEFAULT_PORT == 8788
    assert resolve_port({"TRADE_MCP_PORT": ""}) == DEFAULT_PORT
    assert resolve_port({"TRADE_MCP_PORT": "9001"}) == 9001
    with pytest.raises(ValueError, match="integer"):
        resolve_port({"TRADE_MCP_PORT": "eight"})
    with pytest.raises(ValueError, match="range"):
        resolve_port({"TRADE_MCP_PORT": "70000"})


def test_parser_defaults_to_stdio_and_loopback() -> None:
    args = build_parser(env={}).parse_args([])
    assert args.transport == "stdio"
    assert args.host == "127.0.0.1"
    assert args.port == DEFAULT_PORT
    args = build_parser(env={"TRADE_MCP_PORT": "9001"}).parse_args(
        ["--transport", "streamable-http"]
    )
    assert args.transport == "streamable-http"
    assert args.port == 9001
