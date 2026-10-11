"""``python -m trade_mcp`` — serve over stdio (default) or streamable HTTP."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Mapping, Sequence

from trade_mcp import DEFAULT_PORT
from trade_mcp.server import create_server

DEFAULT_HOST = "127.0.0.1"


def resolve_port(env: Mapping[str, str]) -> int:
    """``TRADE_MCP_PORT`` from the environment, else ``DEFAULT_PORT``."""
    raw = env.get("TRADE_MCP_PORT")
    if raw is None or raw.strip() == "":
        return DEFAULT_PORT
    try:
        port = int(raw)
    except ValueError as exc:
        raise ValueError(f"TRADE_MCP_PORT must be an integer, got {raw!r}") from exc
    if not 1 <= port <= 65535:
        raise ValueError(f"TRADE_MCP_PORT out of range: {port}")
    return port


def build_parser(env: Mapping[str, str] | None = None) -> argparse.ArgumentParser:
    env = os.environ if env is None else env
    parser = argparse.ArgumentParser(
        prog="python -m trade_mcp",
        description="Trade MCP server: paper-money simulator tools for any MCP client.",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default="stdio",
        help="stdio for Claude Code / claude.ai launches; streamable-http for a shared port "
        "(default: %(default)s)",
    )
    parser.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help="bind address for streamable-http; keep it loopback (default: %(default)s)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=resolve_port(env),
        help="port for streamable-http; defaults to $TRADE_MCP_PORT or %(default)s",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    server = create_server()
    if args.transport == "stdio":
        server.run(transport="stdio")
    else:
        server.run(transport="streamable-http", host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
