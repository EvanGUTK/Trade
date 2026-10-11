"""Trade MCP server: the only surface through which any AI touches the simulator.

See docs/adr/0002-mcp-only-ai-boundary.md and docs/adr/0003-paper-money-only.md.
"""

DEFAULT_PORT = 8788
"""Streamable-HTTP port (docs/ARCHITECTURE.md §9); override with TRADE_MCP_PORT."""
