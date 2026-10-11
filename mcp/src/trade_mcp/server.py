"""The Trade MCP server.

Built on the official ``mcp`` SDK (2.x), where the high-level server class is
``MCPServer`` (``FastMCP`` was its 1.x name). Every tool is registered through
``strict_tool`` so its input schema carries ``additionalProperties: false`` *and*
unknown arguments are rejected at call time, as docs/ARCHITECTURE.md §6 requires.

Phase 0 ships exactly one tool, ``health``, and no network access.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Final, Literal, cast

from mcp.server import MCPServer
from mcp.server.mcpserver.tools import Tool
from mcp.server.mcpserver.utilities.func_metadata import ArgModelBase
from mcp.types import ToolAnnotations
from pydantic import BaseModel, ConfigDict

SERVER_NAME: Final = "trade"
SERVER_VERSION: Final = "0.1.0"

INSTRUCTIONS: Final = """\
Trade is a paper-money trading simulator on real market data. Every session,
order, and fill here is simulated; nothing can reach a real brokerage.
Tools are named namespace.verb. Tools that change state say so in their
description; everything else is read-only. Inputs are validated strictly:
unknown fields are rejected.
"""


class Health(BaseModel):
    """Result of the ``health`` tool."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"]
    gateway: Literal["unreachable", "up", "down"]


def health() -> Health:
    """Liveness of this MCP server and, when known, of the gateway behind it.

    Read-only. Phase 0 never touches the network, so ``gateway`` is always
    ``"unreachable"``; Phase 2 proxies the gateway's ``GET /api/v1/health``.
    """
    return Health(status="ok", gateway="unreachable")


def strict_tool(
    fn: Callable[..., Any],
    *,
    name: str | None = None,
    read_only: bool,
    description: str | None = None,
) -> Tool:
    """Build a ``Tool`` whose input schema is closed (``additionalProperties: false``).

    The SDK generates the argument model from the function signature with
    pydantic's default ``extra="ignore"``; that would advertise an open schema and
    silently drop unknown keys. We tighten both halves: the published schema and
    the validation model. ``read_only`` becomes the MCP ``ToolAnnotations`` hints,
    the same **W** / read-only split as the tool table in docs/ARCHITECTURE.md §6.
    """
    tool = Tool.from_function(
        fn,
        name=name,
        description=description,
        annotations=ToolAnnotations(
            read_only_hint=read_only,
            destructive_hint=not read_only,
            idempotent_hint=read_only,
            open_world_hint=False,
        ),
    )
    base = tool.fn_metadata.arg_model
    closed = cast(
        "type[ArgModelBase]",
        type(f"{base.__name__}Closed", (base,), {"model_config": ConfigDict(extra="forbid")}),
    )
    tool.fn_metadata.arg_model = closed
    tool.parameters = {**tool.parameters, "additionalProperties": False}
    return tool


def build_tools() -> list[Tool]:
    """Every tool the server exposes, in a deterministic order."""
    return [
        strict_tool(health, read_only=True),
    ]


def create_server() -> MCPServer:
    """A fresh server instance. Cheap; tests build one per case."""
    return MCPServer(
        name=SERVER_NAME,
        instructions=INSTRUCTIONS,
        version=SERVER_VERSION,
        tools=build_tools(),
    )
