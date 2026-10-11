from __future__ import annotations

import pytest
from mcp import Client
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import CallToolResult

from trade_mcp.server import SERVER_NAME, create_server

EXPECTED_HEALTH = {"status": "ok", "gateway": "unreachable"}


async def test_health_is_the_only_tool_and_its_schemas_are_closed() -> None:
    tools = await create_server().list_tools()
    assert [tool.name for tool in tools] == ["health"]
    (tool,) = tools
    assert tool.input_schema["type"] == "object"
    assert tool.input_schema["additionalProperties"] is False
    assert tool.output_schema is not None
    assert tool.output_schema["additionalProperties"] is False
    assert tool.annotations is not None
    assert tool.annotations.read_only_hint is True
    assert tool.annotations.destructive_hint is False
    assert tool.description is not None
    assert "Read-only" in tool.description


async def test_health_is_callable_in_process() -> None:
    result = await create_server().call_tool("health", {})
    assert isinstance(result, CallToolResult)
    assert result.is_error is False
    assert result.structured_content == EXPECTED_HEALTH


async def test_health_rejects_unknown_arguments() -> None:
    with pytest.raises(ToolError, match="extra"):
        await create_server().call_tool("health", {"live_trading": True})


async def test_health_over_an_in_memory_client_session() -> None:
    server = create_server()
    assert server.name == SERVER_NAME
    async with Client(server) as client:
        listed = await client.list_tools()
        assert [tool.name for tool in listed.tools] == ["health"]
        result = await client.call_tool("health", {})
    assert result.is_error is False
    assert result.structured_content == EXPECTED_HEALTH
